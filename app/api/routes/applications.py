import random
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import DocumentType
from app.schemas.schemas import (
    ApplicationCreate, ApplicationOut, ApplicationListOut,
    DocumentUploadOut, AuditLogOut, CreditScoreOut,
)
from app.services import application_service as svc

router = APIRouter(tags=["Solicitudes"])

ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/webp"}
MAX_FILE_SIZE      = 10 * 1024 * 1024  # 10 MB


@router.post("/applications", response_model=ApplicationOut, status_code=201)
def create_application(data: ApplicationCreate, db: Session = Depends(get_db)):
    """Crea una nueva solicitud de crédito."""
    return svc.create_application(db, data)


@router.get("/applications", response_model=list[ApplicationListOut])
def list_applications(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Lista todas las solicitudes."""
    return svc.list_applications(db, skip, limit)


@router.get("/applications/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db)):
    """Consulta el estado y detalle de una solicitud."""
    app = svc.get_application(db, app_id)
    if not app:
        raise HTTPException(404, f"Solicitud #{app_id} no encontrada")
    return app


@router.post("/applications/{app_id}/documents", response_model=DocumentUploadOut, status_code=201)
async def upload_document(
    app_id:          int,
    background_tasks: BackgroundTasks,
    document_type:   str      = Form(...),
    file:            UploadFile = File(...),
    db:              Session  = Depends(get_db),
):
    """
    Sube un comprobante de domicilio, INE u otro documento.
    El procesamiento OCR + IA se ejecuta en background automáticamente.
    """
    app = svc.get_application(db, app_id)
    if not app:
        raise HTTPException(404, f"Solicitud #{app_id} no encontrada")

    if document_type not in [d.value for d in DocumentType]:
        raise HTTPException(400, f"document_type inválido. Opciones: {[d.value for d in DocumentType]}")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"Tipo de archivo no permitido. Usa PDF, PNG, JPG o WEBP.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "El archivo supera el límite de 10 MB")
    await file.seek(0)

    doc = svc.upload_document(db, app, file, document_type, background_tasks)
    return doc


@router.post("/applications/{app_id}/evaluate", response_model=ApplicationOut)
def re_evaluate(app_id: int, db: Session = Depends(get_db)):
    """Re-evalúa la solicitud con un nuevo score crediticio."""
    app = svc.get_application(db, app_id)
    if not app:
        raise HTTPException(404, f"Solicitud #{app_id} no encontrada")
    return svc.re_evaluate(db, app)


@router.get("/applications/{app_id}/audit", response_model=list[AuditLogOut])
def get_audit(app_id: int, db: Session = Depends(get_db)):
    """Devuelve la trazabilidad completa de la solicitud."""
    app = svc.get_application(db, app_id)
    if not app:
        raise HTTPException(404, f"Solicitud #{app_id} no encontrada")
    return svc.get_audit_log(db, app_id)


@router.get("/scorecredito", response_model=CreditScoreOut)
def get_credit_score():
    """Genera un score crediticio de prueba (300–900)."""
    score = int(random.triangular(300, 900, 620))
    if score >= 750: cat, msg = "Excelente", "Perfil de bajo riesgo."
    elif score >= 650: cat, msg = "Bueno",   "Perfil aceptable, riesgo moderado-bajo."
    elif score >= 550: cat, msg = "Regular", "Perfil con riesgo moderado."
    elif score >= 450: cat, msg = "Malo",    "Perfil de alto riesgo."
    else:              cat, msg = "Muy malo","Perfil de muy alto riesgo."
    return CreditScoreOut(score=score, category=cat, message=msg)
