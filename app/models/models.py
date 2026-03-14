import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class ApplicationStatus(str, enum.Enum):
    PENDING            = "pending"
    DOCUMENTS_REQUIRED = "documents_required"
    UNDER_REVIEW       = "under_review"
    APPROVED           = "approved"
    REJECTED           = "rejected"


class Gender(str, enum.Enum):
    MALE   = "male"
    FEMALE = "female"
    OTHER  = "other"


class DocumentType(str, enum.Enum):
    PROOF_OF_ADDRESS = "proof_of_address"
    ID               = "id"
    INCOME_PROOF     = "income_proof"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    full_name:   Mapped[str] = mapped_column(String(200))
    rfc:         Mapped[str] = mapped_column(String(13), index=True)
    curp:        Mapped[str] = mapped_column(String(18), index=True)
    email:       Mapped[str] = mapped_column(String(200))
    phone:       Mapped[str] = mapped_column(String(20))
    birth_date:  Mapped[datetime] = mapped_column(DateTime)
    gender:      Mapped[str] = mapped_column(String(20))
    nationality: Mapped[str] = mapped_column(String(100), default="Mexicana")

 
    street:          Mapped[str]           = mapped_column(String(300))
    exterior_number: Mapped[str]           = mapped_column(String(20))
    interior_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    neighborhood:    Mapped[str]           = mapped_column(String(200))
    city:            Mapped[str]           = mapped_column(String(200))
    state:           Mapped[str]           = mapped_column(String(100))
    zip_code:        Mapped[str]           = mapped_column(String(10))


    monthly_income:           Mapped[float]        = mapped_column(Float)
    monthly_expenses:         Mapped[float]        = mapped_column(Float, default=0.0)
    banking_seniority_months: Mapped[int]          = mapped_column(Integer, default=0)
    current_debts:            Mapped[float]        = mapped_column(Float, default=0.0)
    employment_type:          Mapped[str]          = mapped_column(String(100), default="employed")
    employer_name:            Mapped[Optional[str]]= mapped_column(String(200), nullable=True)

   
    requested_amount:      Mapped[float] = mapped_column(Float)
    requested_term_months: Mapped[int]   = mapped_column(Integer, default=12)

    status:               Mapped[str]             = mapped_column(String(30), default=ApplicationStatus.PENDING)
    credit_score:         Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    decision:             Mapped[Optional[str]]   = mapped_column(String(20), nullable=True)
    decision_explanation: Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    rules_result:         Mapped[Optional[dict]]  = mapped_column(JSON, nullable=True)
    is_blacklisted:       Mapped[bool]            = mapped_column(Boolean, default=False)

    created_at:  Mapped[datetime]           = mapped_column(DateTime, default=datetime.utcnow)
    updated_at:  Mapped[datetime]           = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    documents:  Mapped[list["Document"]] = relationship("Document",  back_populates="application", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog",  back_populates="application", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id:             Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("applications.id"), index=True)
    document_type:  Mapped[str] = mapped_column(String(50))
    filename:       Mapped[str] = mapped_column(String(300))
    file_path:      Mapped[str] = mapped_column(String(500))
    file_size:      Mapped[int] = mapped_column(Integer)
    mime_type:      Mapped[str] = mapped_column(String(100))

 
    extracted_name:          Mapped[Optional[str]]   = mapped_column(String(200), nullable=True)
    extracted_address:       Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    extracted_validity_date: Mapped[Optional[str]]   = mapped_column(String(100), nullable=True)
    extraction_method:       Mapped[Optional[str]]   = mapped_column(String(60), nullable=True)
    ocr_text_chars:          Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    address_match_score:     Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    address_match_details:   Mapped[Optional[dict]]  = mapped_column(JSON, nullable=True)
    ai_processed:            Mapped[bool]            = mapped_column(Boolean, default=False)
    ai_raw_response:         Mapped[Optional[str]]   = mapped_column(Text, nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    application: Mapped["Application"] = relationship("Application", back_populates="documents")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id:              Mapped[int]            = mapped_column(Integer, primary_key=True, index=True)
    application_id:  Mapped[int]            = mapped_column(Integer, ForeignKey("applications.id"), index=True)
    event:           Mapped[str]            = mapped_column(String(100))
    previous_status: Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    new_status:      Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    details:         Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at:      Mapped[datetime]       = mapped_column(DateTime, default=datetime.utcnow)

    application: Mapped["Application"] = relationship("Application", back_populates="audit_logs")


class Blacklist(Base):
    __tablename__ = "blacklist"

    id:       Mapped[int]           = mapped_column(Integer, primary_key=True, index=True)
    rfc:      Mapped[Optional[str]] = mapped_column(String(13), nullable=True, index=True)
    curp:     Mapped[Optional[str]] = mapped_column(String(18), nullable=True, index=True)
    reason:   Mapped[str]           = mapped_column(String(300))
    added_at: Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow)
