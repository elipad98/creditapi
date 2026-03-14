from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator
from app.models.models import ApplicationStatus, Gender, DocumentType


class ApplicationCreate(BaseModel):
    full_name:   str
    rfc:         str
    curp:        str
    email:       str
    phone:       str
    birth_date:  datetime
    gender:      Gender
    nationality: str = "Mexicana"

    street:          str
    exterior_number: str
    interior_number: Optional[str] = None
    neighborhood:    str
    city:            str
    state:           str
    zip_code:        str

    monthly_income:           float
    monthly_expenses:         float = 0.0
    banking_seniority_months: int   = 0
    current_debts:            float = 0.0
    employment_type:          str   = "employed"
    employer_name:            Optional[str] = None

    requested_amount:      float
    requested_term_months: int = 12

    @field_validator("rfc")
    @classmethod
    def validate_rfc(cls, v: str) -> str:
        v = v.upper().strip()
        if len(v) not in (12, 13):
            raise ValueError("RFC debe tener 12 o 13 caracteres")
        return v

    @field_validator("curp")
    @classmethod
    def validate_curp(cls, v: str) -> str:
        v = v.upper().strip()
        if len(v) != 18:
            raise ValueError("CURP debe tener 18 caracteres")
        return v


class DocumentOut(BaseModel):
    model_config = {"from_attributes": True}
    id:                      int
    document_type:           DocumentType
    filename:                str
    file_size:               int
    extracted_name:          Optional[str]
    extracted_address:       Optional[str]
    extracted_validity_date: Optional[str]
    extraction_method:       Optional[str]
    ocr_text_chars:          Optional[int]
    address_match_score:     Optional[float]
    ai_processed:            bool
    uploaded_at:             datetime


class ApplicationOut(BaseModel):
    model_config = {"from_attributes": True}
    id:           int
    full_name:    str
    rfc:          str
    curp:         str
    email:        str
    phone:        str
    birth_date:   datetime
    gender:       Gender
    nationality:  str
    street:       str
    exterior_number: str
    interior_number: Optional[str]
    neighborhood: str
    city:         str
    state:        str
    zip_code:     str
    monthly_income:           float
    monthly_expenses:         float
    banking_seniority_months: int
    current_debts:            float
    employment_type:          str
    employer_name:            Optional[str]
    requested_amount:         float
    requested_term_months:    int
    status:               ApplicationStatus
    credit_score:         Optional[int]
    decision:             Optional[str]
    decision_explanation: Optional[str]
    rules_result:         Optional[dict]
    is_blacklisted:       bool
    created_at:           datetime
    updated_at:           datetime
    reviewed_at:          Optional[datetime]
    documents:            list[DocumentOut] = []


class ApplicationListOut(BaseModel):
    model_config = {"from_attributes": True}
    id:               int
    full_name:        str
    rfc:              str
    status:           ApplicationStatus
    credit_score:     Optional[int]
    decision:         Optional[str]
    requested_amount: float
    created_at:       datetime


class DocumentUploadOut(BaseModel):
    model_config = {"from_attributes": True}
    id:                      int
    application_id:          int
    document_type:           DocumentType
    filename:                str
    file_size:               int
    ai_processed:            bool
    extracted_name:          Optional[str]
    extracted_address:       Optional[str]
    extracted_validity_date: Optional[str]
    extraction_method:       Optional[str]
    ocr_text_chars:          Optional[int]
    address_match_score:     Optional[float]
    address_match_details:   Optional[dict]
    uploaded_at:             datetime


class AuditLogOut(BaseModel):
    model_config = {"from_attributes": True}
    id:              int
    event:           str
    previous_status: Optional[str]
    new_status:      Optional[str]
    details:         Optional[dict]
    created_at:      datetime


class CreditScoreOut(BaseModel):
    score:    int
    range_min: int = 300
    range_max: int = 900
    category: str
    message:  str


class DashboardStats(BaseModel):
    total_today:          int
    total_all_time:       int
    approved_count:       int
    rejected_count:       int
    pending_count:        int
    approval_rate_pct:    float
    rejection_rate_pct:   float
    top_rejection_reason: Optional[str]
    avg_credit_score:     Optional[float]
