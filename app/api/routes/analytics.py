from collections import Counter
from datetime import datetime, date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Application, ApplicationStatus
from app.schemas.schemas import DashboardStats

router = APIRouter(tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db)):
    """Estadísticas de negocio del sistema de crédito."""
    all_apps  = db.query(Application).all()
    today     = date.today()
    today_apps = [a for a in all_apps if a.created_at.date() == today]

    approved = [a for a in all_apps if a.status == ApplicationStatus.APPROVED]
    rejected = [a for a in all_apps if a.status == ApplicationStatus.REJECTED]
    pending  = [a for a in all_apps if a.status not in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED)]

    total = len(all_apps)
    approval_rate   = round(len(approved) / total * 100, 1) if total else 0.0
    rejection_rate  = round(len(rejected) / total * 100, 1) if total else 0.0

    rejection_reasons = [
        a.rules_result.get("rejection_reason")
        for a in rejected
        if a.rules_result and a.rules_result.get("rejection_reason")
    ]
    top_reason = Counter(rejection_reasons).most_common(1)[0][0] if rejection_reasons else None

    scores    = [a.credit_score for a in all_apps if a.credit_score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    return DashboardStats(
        total_today=len(today_apps),
        total_all_time=total,
        approved_count=len(approved),
        rejected_count=len(rejected),
        pending_count=len(pending),
        approval_rate_pct=approval_rate,
        rejection_rate_pct=rejection_rate,
        top_rejection_reason=top_reason,
        avg_credit_score=avg_score,
    )
