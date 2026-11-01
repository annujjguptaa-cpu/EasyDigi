from pathlib import Path
from typing import Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


class DeadlinesConfig(BaseModel):
    intimation_hours: Optional[int] = None
    pre_auth_decision_hours: Optional[int] = None
    final_auth_after_discharge_hours: Optional[int] = None
    reimbursement_submission_days: Optional[int] = None
    additional_doc_request_days: Optional[int] = None
    motor_docs_days: Optional[int] = None
    surveyor_assignment_hours: Optional[int] = None
    survey_report_days: Optional[int] = None
    doc_submission_days: Optional[int] = None
    settlement_days: int = 30


class ClaimTypeConfig(BaseModel):
    name: str
    product_type: str
    required_documents: List[str]
    optional_documents: List[str] = Field(default_factory=list)
    departments: List[str]
    deadlines: DeadlinesConfig


class InsuranceConfig(BaseModel):
    claim_types: Dict[str, ClaimTypeConfig]


def load_claim_types_config(config_path: Optional[Path] = None) -> InsuranceConfig:
    if config_path is None:
        config_path = Path(__file__).parent / "claim_types.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)
    return InsuranceConfig.model_validate(raw_data)
