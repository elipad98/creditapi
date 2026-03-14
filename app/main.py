import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import applications, analytics, ai_debug
from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger   = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="Credit Approval System",
    description="Sistema de aprobación crediticia con OCR + Ollama (LLM local)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(applications.router)
app.include_router(analytics.router)
app.include_router(ai_debug.router)


@app.on_event("startup")
async def startup():
    logger.info("=" * 55)
    logger.info("  Credit Approval System v2")
    logger.info(f"  Entorno   : {settings.environment}")
    logger.info(f"  Ollama    : {settings.ollama_base_url}")
    logger.info(f"  Modelo    : {settings.ollama_model}  (visión ✓)")
    logger.info(f"  OCR min   : {settings.ocr_min_chars} chars")
    logger.info(f"  Uploads   : {settings.upload_dir}")
    logger.info("=" * 55)


@app.get("/", tags=["health"])
def root():
    return {"service": "Credit Approval System", "version": "2.0.0", "docs": "/docs"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
