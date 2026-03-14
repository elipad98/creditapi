
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id",                      sa.Integer(),     primary_key=True),
        sa.Column("full_name",               sa.String(200),   nullable=False),
        sa.Column("rfc",                     sa.String(13),    nullable=False),
        sa.Column("curp",                    sa.String(18),    nullable=False),
        sa.Column("email",                   sa.String(200),   nullable=False),
        sa.Column("phone",                   sa.String(20),    nullable=False),
        sa.Column("birth_date",              sa.DateTime(),    nullable=False),
        sa.Column("gender",                  sa.String(20),    nullable=False),
        sa.Column("nationality",             sa.String(100),   nullable=False, server_default="Mexicana"),
        sa.Column("street",                  sa.String(300),   nullable=False),
        sa.Column("exterior_number",         sa.String(20),    nullable=False),
        sa.Column("interior_number",         sa.String(20),    nullable=True),
        sa.Column("neighborhood",            sa.String(200),   nullable=False),
        sa.Column("city",                    sa.String(200),   nullable=False),
        sa.Column("state",                   sa.String(100),   nullable=False),
        sa.Column("zip_code",                sa.String(10),    nullable=False),
        sa.Column("monthly_income",          sa.Float(),       nullable=False),
        sa.Column("monthly_expenses",        sa.Float(),       nullable=False, server_default="0"),
        sa.Column("banking_seniority_months",sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("current_debts",           sa.Float(),       nullable=False, server_default="0"),
        sa.Column("employment_type",         sa.String(100),   nullable=False, server_default="employed"),
        sa.Column("employer_name",           sa.String(200),   nullable=True),
        sa.Column("requested_amount",        sa.Float(),       nullable=False),
        sa.Column("requested_term_months",   sa.Integer(),     nullable=False, server_default="12"),
        sa.Column("status",                  sa.String(30),    nullable=False, server_default="pending"),
        sa.Column("credit_score",            sa.Integer(),     nullable=True),
        sa.Column("decision",                sa.String(20),    nullable=True),
        sa.Column("decision_explanation",    sa.Text(),        nullable=True),
        sa.Column("rules_result",            postgresql.JSON(), nullable=True),
        sa.Column("is_blacklisted",          sa.Boolean(),     nullable=False, server_default="false"),
        sa.Column("created_at",              sa.DateTime(),    nullable=False),
        sa.Column("updated_at",              sa.DateTime(),    nullable=False),
        sa.Column("reviewed_at",             sa.DateTime(),    nullable=True),
    )
    op.create_index("ix_applications_id",   "applications", ["id"])
    op.create_index("ix_applications_rfc",  "applications", ["rfc"])
    op.create_index("ix_applications_curp", "applications", ["curp"])

    op.create_table(
        "documents",
        sa.Column("id",                       sa.Integer(),     primary_key=True),
        sa.Column("application_id",           sa.Integer(),     sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("document_type",            sa.String(50),    nullable=False),
        sa.Column("filename",                 sa.String(300),   nullable=False),
        sa.Column("file_path",                sa.String(500),   nullable=False),
        sa.Column("file_size",                sa.Integer(),     nullable=False),
        sa.Column("mime_type",                sa.String(100),   nullable=False),
        sa.Column("extracted_name",           sa.String(200),   nullable=True),
        sa.Column("extracted_address",        sa.Text(),        nullable=True),
        sa.Column("extracted_validity_date",  sa.String(100),   nullable=True),
        sa.Column("extraction_method",        sa.String(60),    nullable=True),
        sa.Column("ocr_text_chars",           sa.Integer(),     nullable=True),
        sa.Column("address_match_score",      sa.Float(),       nullable=True),
        sa.Column("address_match_details",    postgresql.JSON(), nullable=True),
        sa.Column("ai_processed",             sa.Boolean(),     nullable=False, server_default="false"),
        sa.Column("ai_raw_response",          sa.Text(),        nullable=True),
        sa.Column("uploaded_at",              sa.DateTime(),    nullable=False),
    )
    op.create_index("ix_documents_id",             "documents", ["id"])
    op.create_index("ix_documents_application_id", "documents", ["application_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id",              sa.Integer(),      primary_key=True),
        sa.Column("application_id",  sa.Integer(),      sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("event",           sa.String(100),    nullable=False),
        sa.Column("previous_status", sa.String(50),     nullable=True),
        sa.Column("new_status",      sa.String(50),     nullable=True),
        sa.Column("details",         postgresql.JSON(), nullable=True),
        sa.Column("created_at",      sa.DateTime(),     nullable=False),
    )
    op.create_index("ix_audit_logs_id",             "audit_logs", ["id"])
    op.create_index("ix_audit_logs_application_id", "audit_logs", ["application_id"])

    op.create_table(
        "blacklist",
        sa.Column("id",       sa.Integer(),   primary_key=True),
        sa.Column("rfc",      sa.String(13),  nullable=True),
        sa.Column("curp",     sa.String(18),  nullable=True),
        sa.Column("reason",   sa.String(300), nullable=False),
        sa.Column("added_at", sa.DateTime(),  nullable=False),
    )
    op.create_index("ix_blacklist_id",   "blacklist", ["id"])
    op.create_index("ix_blacklist_rfc",  "blacklist", ["rfc"])
    op.create_index("ix_blacklist_curp", "blacklist", ["curp"])


def downgrade() -> None:
    op.drop_table("blacklist")
    op.drop_table("audit_logs")
    op.drop_table("documents")
    op.drop_table("applications")
