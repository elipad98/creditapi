import os
import time
import tempfile
import logging

from fastapi import APIRouter, UploadFile, File, Query
from app.core.config import get_settings
from app.core import ai_service
from app.core.ocr_service import extract_text

router   = APIRouter(prefix="/ai", tags=["AI diagnóstico"])
logger   = logging.getLogger(__name__)
settings = get_settings()


@router.get("/test")
def test_ollama_connection():
    """
    Prueba la conexión con Ollama local.
    Ollama en Windows corre automáticamente en background — no necesitas 'ollama serve'.
    """
    try:
        from app.core.ai_service import _call_ollama_text, OLLAMA_BASE_URL, OLLAMA_MODEL
        start    = time.time()
        response = _call_ollama_text('Responde solo con este JSON exacto: {"status": "ok", "message": "Ollama conectado"}')
        elapsed  = round(time.time() - start, 2)

        logger.info(f"[AI /test] Ollama OK en {elapsed}s")
        return {
            "status":          "ok",
            "message":         "Conexión con Ollama exitosa",
            "elapsed_seconds": elapsed,
            "model":           OLLAMA_MODEL,
            "ollama_url":      OLLAMA_BASE_URL,
            "raw_response":    response,
        }
    except ConnectionError as e:
        return {
            "status":  "error",
            "message": str(e),
            "hint":    "Verifica que Ollama esté corriendo en http://localhost:11434",
        }
    except Exception as e:
        return {
            "status":  "error",
            "message": str(e),
        }


@router.get("/models")
def list_ollama_models():
    """Lista los modelos disponibles en Ollama."""
    import urllib.request, json
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as resp:
            data   = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            return {"status": "ok", "models": models}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/test-ocr")
async def test_ocr_only(file: UploadFile = File(...)):
    """
    Prueba solo el OCR local (pymupdf → Tesseract), SIN llamar a Ollama.
    Muestra cuánto texto extrae antes de mandarlo al LLM.
    """
    content = await file.read()
    suffix  = os.path.splitext(file.filename)[1].lower() or ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        start   = time.time()
        result  = extract_text(tmp_path)
        elapsed = round(time.time() - start, 2)

        return {
            "filename":               file.filename,
            "file_size_bytes":        len(content),
            "elapsed_seconds":        elapsed,
            "method_used":            result.method,
            "char_count":             result.char_count,
            "ocr_successful":         result.success,
            "will_use_ollama_text":   result.success,
            "will_use_ollama_vision": not result.success,
            "extracted_text_preview": result.text[:500] if result.text else None,
        }
    finally:
        os.unlink(tmp_path)


@router.post("/test-document")
async def test_document_extraction(file: UploadFile = File(...)):
    """
    Flujo completo: OCR local → Ollama (texto o visión según el documento).
    Muestra qué método se usó y qué datos extrajo el modelo.
    """
    content = await file.read()
    suffix  = os.path.splitext(file.filename)[1].lower() or ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        start   = time.time()
        result  = ai_service.extract_document_info(tmp_path)
        elapsed = round(time.time() - start, 2)

        return {
            "status":              "ok" if result.get("success") else "error",
            "elapsed_seconds":     elapsed,
            "filename":            file.filename,
            "file_size_bytes":     len(content),
            "extraction_method":   result.get("extraction_method"),
            "ocr_chars_extracted": result.get("ocr_text_chars"),
            "extraction": {
                "name":          result.get("name"),
                "address":       result.get("address"),
                "validity_date": result.get("validity_date"),
                "document_type": result.get("document_type"),
                "issuer":        result.get("issuer"),
            },
            "ollama_raw_response": result.get("raw_response"),
            "error":               result.get("error"),
        }
    finally:
        os.unlink(tmp_path)


@router.post("/test-address-match")
def test_address_match(
    declared:  str = Query(..., description="Dirección declarada por el cliente"),
    extracted: str = Query(..., description="Dirección extraída del comprobante"),
):
    """Compara dos direcciones y devuelve el match_score del modelo."""
    start  = time.time()
    result = ai_service.validate_address_match(declared, extracted)
    return {
        "elapsed_seconds": round(time.time() - start, 2),
        "match_score":     result["match_score"],
        "is_match":        result["is_match"],
        "explanation":     result["explanation"],
        "details":         result["details"],
    }
