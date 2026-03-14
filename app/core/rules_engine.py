from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RuleResult:
    rule_name: str
    passed:    bool
    value:     object
    threshold: object
    message:   str


@dataclass
class EvaluationResult:
    approved:         bool
    rules:            list[RuleResult] = field(default_factory=list)
    explanation:      str = ""
    rejection_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "rejection_reason": self.rejection_reason,
            "rules": [
                {"rule": r.rule_name, "passed": r.passed,
                 "value": r.value, "threshold": r.threshold, "message": r.message}
                for r in self.rules
            ],
        }


PRODUCT_RULES: dict[str, dict] = {
    "personal_loan": {
        "min_credit_score": 500,
        "min_monthly_income": 5000.0,
        "min_banking_seniority_months": 6,
        "max_debt_to_income_ratio": 0.4,
        "address_min_match": 0.6,
    },
    "credit_card": {
        "min_credit_score": 600,
        "min_monthly_income": 8000.0,
        "min_banking_seniority_months": 12,
        "max_debt_to_income_ratio": 0.35,
        "address_min_match": 0.7,
    },
    "sme_loan": {
        "min_credit_score": 550,
        "min_monthly_income": 20000.0,
        "min_banking_seniority_months": 24,
        "max_debt_to_income_ratio": 0.5,
        "address_min_match": 0.6,
    },
}


def evaluate_application(
    credit_score:              int,
    monthly_income:            float,
    banking_seniority_months:  int,
    is_blacklisted:            bool,
    current_debts:             float,
    requested_amount:          float,
    requested_term_months:     int,
    address_match_score:       Optional[float] = None,
    product_type:              str = "personal_loan",
) -> EvaluationResult:
    cfg = PRODUCT_RULES.get(product_type, PRODUCT_RULES["personal_loan"])

    monthly_payment = requested_amount / max(requested_term_months, 1)
    dti_ratio       = (current_debts + monthly_payment) / max(monthly_income, 1)

    rules = [
        RuleResult(
            "credit_score", credit_score >= cfg["min_credit_score"],
            credit_score, cfg["min_credit_score"],
            f"Score {credit_score} {'≥' if credit_score >= cfg['min_credit_score'] else '<'} mínimo {cfg['min_credit_score']}",
        ),
        RuleResult(
            "monthly_income", monthly_income >= cfg["min_monthly_income"],
            monthly_income, cfg["min_monthly_income"],
            f"Ingreso ${monthly_income:,.0f} {'≥' if monthly_income >= cfg['min_monthly_income'] else '<'} mínimo ${cfg['min_monthly_income']:,.0f}",
        ),
        RuleResult(
            "banking_seniority", banking_seniority_months >= cfg["min_banking_seniority_months"],
            banking_seniority_months, cfg["min_banking_seniority_months"],
            f"Antigüedad {banking_seniority_months} meses {'≥' if banking_seniority_months >= cfg['min_banking_seniority_months'] else '<'} mínimo {cfg['min_banking_seniority_months']}",
        ),
        RuleResult(
            "not_blacklisted", not is_blacklisted,
            is_blacklisted, False,
            "Cliente no en lista negra" if not is_blacklisted else "Cliente en lista negra",
        ),
        RuleResult(
            "address_valid",
            address_match_score is not None and address_match_score >= cfg["address_min_match"],
            address_match_score, cfg["address_min_match"],
            (
                "Comprobante no procesado — dirección no verificada" if address_match_score is None else
                f"Dirección coincide {address_match_score:.0%}" if address_match_score >= cfg["address_min_match"] else
                f"Dirección no coincide {address_match_score:.0%} < mínimo {cfg['address_min_match']:.0%}"
            ),
        ),
        RuleResult(
            "debt_to_income", dti_ratio <= cfg["max_debt_to_income_ratio"],
            round(dti_ratio, 3), cfg["max_debt_to_income_ratio"],
            f"DTI {dti_ratio:.0%} {'≤' if dti_ratio <= cfg['max_debt_to_income_ratio'] else '>'} máximo {cfg['max_debt_to_income_ratio']:.0%}",
        ),
    ]

    failed   = [r for r in rules if not r.passed]
    approved = not failed

    if approved:
        explanation      = f"APROBADA — Score: {credit_score}, Ingreso: ${monthly_income:,.0f} MXN"
        rejection_reason = None
    else:
        rejection_reason = failed[0].rule_name
        explanation      = "RECHAZADA — " + "; ".join(r.message for r in failed)

    return EvaluationResult(
        approved=approved, rules=rules,
        explanation=explanation, rejection_reason=rejection_reason,
    )
