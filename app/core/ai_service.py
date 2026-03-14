import json
import re
import time
import asyncio
import logging
import base64
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.ocr_service import extract_text

settings = get_settings()
logger   = logging.getLogger(__name__)

OLLAMA_BASE_URL: str = settings.ollama_base_url
OLLAMA_MODEL:    str = settings.ollama_model
OLLAMA_TIMEOUT:  int = 180

_EXTRACTION_INSTRUCTIONS = """\
You are a data extraction assistant. Analyze the following text from a Mexican proof of address document.
Respond ONLY with a valid JSON object. No explanations, no markdown, no extra text.

Required structure (use null if data not found):
{
  "name": "full name of the account holder",
  "address": "full address: street, number, neighborhood, city, state, zip code",
  "validity_date": "document validity or issue date",
  "document_type": "type of document (electricity bill, phone bill, bank statement, etc.)",
  "issuer": "company or institution that issued the document"
}

DOCUMENT TEXT:
"""

_ADDRESS_INSTRUCTIONS = """\
You are an address comparison assistant. Compare these two addresses and determine if they refer to the same location.
Consider abbreviations (C.=Calle, Col.=Colonia, No.=Numero, etc.), format variations and minor typos.
Respond ONLY with a valid JSON object. No explanations, no markdown, no extra text.

Required structure:
{
  "match_score": 0.0,
  "is_match": false,
  "street_match": false,
  "neighborhood_match": false,
  "city_match": false,
  "state_match": false,
  "zip_match": false,
  "explanation": "brief explanation in Spanish",
  "normalized_declared": "normalized declared address",
  "normalized_extracted": "normalized extracted address"
}

DECLARED ADDRESS:
"""


def _build_extraction_prompt(text: str) -> str:
    return _EXTRACTION_INSTRUCTIONS + text


def _build_address_prompt(declared: str, extracted: str) -> str:
    return (
        _ADDRESS_INSTRUCTIONS
        + declared
        + "\n\nEXTRACTED ADDRESS FROM DOCUMENT:\n"
        + extracted
    )


async def _call_ollama_stream(messages: list) -> str:
    """
    Llama a Ollama con stream=True y acumula tokens hasta que el modelo
    indique 'done'. llama3.1 responde directo sin thinking mode.
    """
    import aiohttp

    payload = {
        "model":    OLLAMA_MODEL,
        "stream":   True,
        "options":  {
            "temperature": 0.1,
            "num_predict": 512,
            "num_ctx":     4096,
        },
        "messages": messages,
    }

    url    = f"{OLLAMA_BASE_URL}/api/chat"
    buffer = ""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=OLLAMA_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise ConnectionError(f"Ollama HTTP {resp.status}: {body}")

                async for raw_line in resp.content:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    msg    = chunk.get("message", {})
                    token  = msg.get("content", "") if isinstance(msg, dict) else ""
                    buffer += token

                    if chunk.get("done", False):
                        logger.info(
                            f"[Ollama] Stream completo — "
                            f"{chunk.get('eval_count', '?')} tokens"
                        )
                        break

    except aiohttp.ClientConnectorError as e:
        raise ConnectionError(
            f"No se puede conectar a Ollama en {OLLAMA_BASE_URL}. "
            f"¿Está corriendo?\nDetalle: {e}"
        )

    result = buffer.strip()
    logger.info(f"[Ollama] Respuesta (primeros 300 chars): {repr(result[:300])}")
    return result


def _run_async(coro) -> str:
    """Ejecuta una corutina desde código síncrono de forma segura."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=OLLAMA_TIMEOUT)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _call_ollama_text(prompt: str) -> str:
    """Llamada de texto con streaming."""
    return _run_async(_call_ollama_stream([
        {"role": "user", "content": prompt}
    ]))


def _call_ollama_vision(prompt: str, image_b64: str) -> str:
    """llama3.1 no tiene visión — lanza error claro."""
    raise NotImplementedError(
        f"{OLLAMA_MODEL} no soporta visión. "
        "Para PDFs escaneados usa un modelo con visión: ollama pull llava"
    )

def _clean_json(text: str) -> str:
    text  = text.strip()
    text  = re.sub(r"^```json\s*", "", text)
    text  = re.sub(r"^```\s*",     "", text)
    text  = re.sub(r"\s*```$",     "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def _is_rate_limit_error(e: Exception) -> bool:
    return False

def extract_document_info(file_path: str) -> dict:
    """
    Extrae nombre, dirección y vigencia del comprobante via streaming.
    llama3.1 responde directo sin thinking mode — más rápido y predecible.
    """
    raw_text = ""
    try:
        ocr_result = extract_text(file_path)
        logger.info(f"[AI] OCR: {ocr_result}")

        if not ocr_result.success:
            logger.warning(
                f"[AI] OCR insuficiente ({ocr_result.char_count} chars). "
                f"{OLLAMA_MODEL} no tiene visión. "
                "Instala llava para PDFs escaneados: ollama pull llava"
            )
            return {
                "name": None, "address": None, "validity_date": None,
                "raw_response": "", "success": False,
                "extraction_method": "ocr_failed_no_vision",
                "ocr_text_chars": ocr_result.char_count,
                "error": f"{OLLAMA_MODEL} no soporta visión. OCR extrajo solo {ocr_result.char_count} chars.",
            }

        logger.info(
            f"[AI] {ocr_result.char_count} chars ({ocr_result.method}) "
            f"→ {OLLAMA_MODEL} (stream)"
        )
        start    = time.time()
        raw_text = _call_ollama_text(_build_extraction_prompt(ocr_result.text))
        elapsed  = round(time.time() - start, 2)

        logger.info(f"[Ollama] Respuesta en {elapsed}s — parseando JSON...")
        parsed = json.loads(_clean_json(raw_text))
        logger.info(f"[Ollama] OK — nombre: {parsed.get('name')}")

        return {
            "name":             parsed.get("name"),
            "address":          parsed.get("address"),
            "validity_date":    parsed.get("validity_date"),
            "document_type":    parsed.get("document_type"),
            "issuer":           parsed.get("issuer"),
            "raw_response":     raw_text,
            "extraction_method": f"ocr_then_text ({ocr_result.method})",
            "ocr_text_chars":   ocr_result.char_count,
            "success":          True,
        }

    except json.JSONDecodeError as e:
        logger.error(f"[Ollama] JSON parse error: {e}\nRaw: {repr(raw_text)}")
        return {
            "name": None, "address": None, "validity_date": None,
            "raw_response": raw_text, "success": False,
            "error": f"JSON parse error: {e}. Raw: {raw_text[:200]}",
        }
    except ConnectionError as e:
        logger.error(f"[Ollama] Conexión fallida: {e}")
        return {
            "name": None, "address": None, "validity_date": None,
            "raw_response": "", "success": False, "error": str(e),
        }
    except Exception as e:
        logger.error(f"[Ollama] Error: {e}", exc_info=True)
        return {
            "name": None, "address": None, "validity_date": None,
            "raw_response": raw_text, "success": False, "error": str(e),
        }


def validate_address_match(declared_address: str, extracted_address: Optional[str]) -> dict:
    """Compara semánticamente las dos direcciones via streaming."""
    if not extracted_address:
        return {
            "match_score": 0.0, "is_match": False,
            "explanation": "No se pudo extraer dirección del documento",
            "details": {},
        }

    raw_text = ""
    try:
        prompt = _build_address_prompt(declared_address, extracted_address)
        logger.info("[Ollama] Validando dirección (stream)...")
        start    = time.time()
        raw_text = _call_ollama_text(prompt)
        elapsed  = round(time.time() - start, 2)

        parsed = json.loads(_clean_json(raw_text))
        score  = float(parsed.get("match_score", 0.0))
        logger.info(f"[Ollama] Dirección OK en {elapsed}s — score: {score}")

        return {
            "match_score": score,
            "is_match":    bool(parsed.get("is_match", False)),
            "explanation": parsed.get("explanation", ""),
            "details": {
                "street_match":         parsed.get("street_match"),
                "neighborhood_match":   parsed.get("neighborhood_match"),
                "city_match":           parsed.get("city_match"),
                "state_match":          parsed.get("state_match"),
                "zip_match":            parsed.get("zip_match"),
                "normalized_declared":  parsed.get("normalized_declared"),
                "normalized_extracted": parsed.get("normalized_extracted"),
            },
        }

    except json.JSONDecodeError as e:
        logger.error(f"[Ollama] JSON parse error validación: {e}\nRaw: {repr(raw_text)}")
        return {
            "match_score": 0.0, "is_match": False,
            "explanation": f"Error parseando respuesta: {e}",
            "details": {},
        }
    except Exception as e:
        logger.error(f"[Ollama] Error validación: {e}")
        return {
            "match_score": 0.0, "is_match": False,
            "explanation": f"Error: {e}", "details": {},
        }
