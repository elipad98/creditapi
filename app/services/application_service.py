import os
import random
import logging
from datetime import datetime
from pathlib import Path

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.orm import Session

from app.core import ai_service, rules_engine
from app.core.config import get_settings
from app.models.models import Application, AuditLog, Blacklist, Document, ApplicationStatus
from app.schemas.schemas import ApplicationCreate

settings = get_settings()
logger   = logging.getLogger(__name__)


def _generate_credit_score() -> int:
    return int(random.triangular(300, 900, 620))


def _declared_address(app: Application) -> str:
    parts = [
        f"{app.street} {app.exterior_number}",
        f"Int. {app.interior_number}" if app.interior_number else "",
        app.neighborhood, app.city, app.state, f"C.P. {app.zip_code}",
    ]
    return ", ".join(p for p in parts if p)


def _add_audit(db: Session, app: Application, event: str,
               prev: str = None, new: str = None, details: dict = None):
    db.add(AuditLog(
        application_id=app.id,
        event=event,
        previous_status=prev,
        new_status=new,
        details=details,
    ))


def create_application(db: Session, data: ApplicationCreate) -> Application:
    is_blacklisted = db.query(Blacklist).filter(
        (Blacklist.rfc == data.rfc) | (Blacklist.curp == data.curp)
    ).first() is not None

    app = Application(**data.model_dump(), is_blacklisted=is_blacklisted)
    db.add(app)
    db.flush()
    _add_audit(db, app, "application_created",
               new=ApplicationStatus.PENDING,
               details={"requested_amount": data.requested_amount})
    db.commit()
    db.refresh(app)
    logger.info(f"[Service] Solicitud #{app.id} creada para {app.full_name}")
    return app


def upload_document(
    db: Session,
    app: Application,
    file: UploadFile,
    document_type: str,
    background_tasks: BackgroundTasks,
) -> Document:
    upload_dir = Path(settings.upload_dir) / str(app.id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{document_type}_{file.filename}"
    file_path = upload_dir / safe_name
    content   = file.file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    mime_type = file.content_type or "application/octet-stream"

    doc = Document(
        application_id=app.id,
        document_type=document_type,
        filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=mime_type,
        ai_processed=False,
    )
    db.add(doc)

    prev_status = app.status
    app.status  = ApplicationStatus.UNDER_REVIEW
    _add_audit(db, app, "document_uploaded",
               prev=prev_status, new=app.status,
               details={"filename": file.filename, "document_type": document_type})
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(_process_document_bg, doc.id, app.id)
    logger.info(f"[Service] Documento #{doc.id} guardado → procesando en background")
    return doc


def _process_document_bg(doc_id: int, app_id: int):
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        app = db.get(Application, app_id)
        if not doc or not app:
            return

        logger.info(f"[BG] Iniciando procesamiento doc #{doc_id} — app #{app_id}")

        extraction = ai_service.extract_document_info(doc.file_path)
        doc.ai_raw_response   = extraction.get("raw_response", "")
        doc.extraction_method = extraction.get("extraction_method")
        doc.ocr_text_chars    = extraction.get("ocr_text_chars")

        if extraction.get("success"):
            doc.extracted_name          = extraction.get("name")
            doc.extracted_address       = extraction.get("address")
            doc.extracted_validity_date = extraction.get("validity_date")

            logger.info(
                f"[BG] Extraído — nombre: {doc.extracted_name} | "
                f"método: {doc.extraction_method} | chars OCR: {doc.ocr_text_chars}"
            )

            if doc.document_type == "proof_of_address" and doc.extracted_address:
                declared = _declared_address(app)
                match    = ai_service.validate_address_match(declared, doc.extracted_address)
                doc.address_match_score   = match["match_score"]
                doc.address_match_details = match["details"]
                logger.info(
                    f"[BG] Dirección match_score: {match['match_score']:.2f} — "
                    f"{'OK' if match['is_match'] else 'NO coincide'}"
                )
        else:
            logger.warning(f"[BG] Extracción fallida: {extraction.get('error')}")

        doc.ai_processed = True
        db.flush()

        address_score = doc.address_match_score if doc.document_type == "proof_of_address" else None
        _evaluate_and_update(db, app, address_score_override=address_score)
        db.commit()
        logger.info(f"[BG] App #{app_id} procesada → {app.status}")

    except Exception as e:
        db.rollback()
        logger.error(f"[BG] Error procesando doc #{doc_id}: {e}", exc_info=True)
    finally:
        db.close()


def _evaluate_and_update(db: Session, app: Application, address_score_override=None):
    score = _generate_credit_score()
    app.credit_score = score

    if address_score_override is not None:
        address_score = address_score_override
        logger.info(f"[Eval] address_match_score desde doc actual: {address_score}")
    else:
        address_score = None
        db.expire(app, ["documents"])   
        for doc in app.documents:
            if doc.document_type == "proof_of_address" and doc.address_match_score is not None:
                address_score = doc.address_match_score
                break
        logger.info(f"[Eval] address_match_score desde BD: {address_score}")

    result = rules_engine.evaluate_application(
        credit_score=score,
        monthly_income=app.monthly_income,
        banking_seniority_months=app.banking_seniority_months,
        is_blacklisted=app.is_blacklisted,
        current_debts=app.current_debts,
        requested_amount=app.requested_amount,
        requested_term_months=app.requested_term_months,
        address_match_score=address_score,
    )

    prev_status              = app.status
    app.decision             = "approved" if result.approved else "rejected"
    app.status               = ApplicationStatus.APPROVED if result.approved else ApplicationStatus.REJECTED
    app.decision_explanation = result.explanation
    app.rules_result         = result.to_dict()
    app.reviewed_at          = datetime.utcnow()

    _add_audit(db, app, "application_evaluated",
               prev=prev_status, new=app.status,
               details={
                   "credit_score": score,
                   "approved": result.approved,
                   "rejection_reason": result.rejection_reason,
                   "address_match_score": address_score,
               })


def re_evaluate(db: Session, app: Application) -> Application:
    _evaluate_and_update(db, app)
    db.commit()
    db.refresh(app)
    return app


def get_application(db: Session, app_id: int) -> Application | None:
    return db.get(Application, app_id)


def list_applications(db: Session, skip: int = 0, limit: int = 20) -> list[Application]:
    return db.query(Application).order_by(Application.created_at.desc()).offset(skip).limit(limit).all()


def get_audit_log(db: Session, app_id: int) -> list[AuditLog]:
    return db.query(AuditLog).filter(AuditLog.application_id == app_id)\
             .order_by(AuditLog.created_at.asc()).all()
