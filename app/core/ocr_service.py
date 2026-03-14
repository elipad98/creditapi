import io
import logging
from enum import Enum
from pathlib import Path

from PIL import Image
from app.core.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()


class ExtractionMethod(str, Enum):
    PYMUPDF = "pymupdf"
    OCR     = "ocr_tesseract"
    FALLBACK  = "fallback_no_vision"


class ExtractionResult:
    def __init__(self, text: str, method: ExtractionMethod, page_count: int = 1):
        self.text       = text
        self.method     = method
        self.page_count = page_count
        self.char_count = len(text.strip())
        self.success    = self.char_count >= settings.ocr_min_chars

    def __repr__(self):
        return (
            f"ExtractionResult(method={self.method}, "
            f"chars={self.char_count}, success={self.success})"
        )

def _extract_with_pymupdf(file_path: str) -> ExtractionResult:
    """Extrae texto de PDFs con capa de texto seleccionable."""
    try:
        import fitz
        doc   = fitz.open(file_path)
        text  = "\n".join(page.get_text() for page in doc).strip()
        pages = len(doc)
        doc.close()
        result = ExtractionResult(text, ExtractionMethod.PYMUPDF, pages)
        logger.info(
            f"[OCR] pymupdf → {result.char_count} chars, {pages} págs — "
            f"{'OK' if result.success else 'insuficiente → Tesseract'}"
        )
        return result
    except Exception as e:
        logger.warning(f"[OCR] pymupdf falló: {e}")
        return ExtractionResult("", ExtractionMethod.PYMUPDF)


def _pdf_to_images(file_path: str, dpi: int = 300) -> list[Image.Image]:
    """Renderiza cada página del PDF como imagen PIL."""
    import fitz
    doc    = fitz.open(file_path)
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    images = [
        Image.open(io.BytesIO(page.get_pixmap(matrix=matrix).tobytes("png")))
        for page in doc
    ]
    doc.close()
    return images


def _extract_with_tesseract(file_path: str) -> ExtractionResult:
    """OCR con Tesseract. Funciona con PDFs escaneados e imágenes."""
    try:
        import pytesseract
        suffix = Path(file_path).suffix.lower()

        if suffix == ".pdf":
            images     = _pdf_to_images(file_path)
            pages_text = [pytesseract.image_to_string(img, lang="spa+eng") for img in images]
        else:
            pages_text = [pytesseract.image_to_string(Image.open(file_path), lang="spa+eng")]

        text   = "\n".join(pages_text).strip()
        result = ExtractionResult(text, ExtractionMethod.OCR, len(pages_text))
        logger.info(
            f"[OCR] Tesseract → {result.char_count} chars — "
            f"{'OK' if result.success else 'insuficiente → Sin visión disponible'}"
        )
        return result
    except Exception as e:
        logger.warning(f"[OCR] Tesseract falló: {e}")
        return ExtractionResult("", ExtractionMethod.OCR)


def extract_text(file_path: str) -> ExtractionResult:
    """
    Intenta extraer texto del documento usando la estrategia de menor costo:

    PDF  → pymupdf → si falla → Tesseract → si falla → sin visión (requiere modelo con visión)
    IMG  → Tesseract directamente → si falla → sin visión

    Cuando result.success=False y result.method=FALLBACK, el llamador
    (ai_service) no puede procesar el documento sin un modelo de visión.
    """
    suffix = Path(file_path).suffix.lower()
    logger.info(f"[OCR] Procesando: {Path(file_path).name} (tipo: {suffix})")

    if suffix == ".pdf":
        r = _extract_with_pymupdf(file_path)
        if r.success:
            return r
        r = _extract_with_tesseract(file_path)
        if r.success:
            return r
        logger.info("[OCR] Ambos métodos locales fallaron → Sin visión disponible")
        return ExtractionResult("", ExtractionMethod.FALLBACK)
    else:
        r = _extract_with_tesseract(file_path)
        if r.success:
            return r
        logger.info("[OCR] Tesseract insuficiente en imagen → Sin visión disponible")
        return ExtractionResult("", ExtractionMethod.FALLBACK)
