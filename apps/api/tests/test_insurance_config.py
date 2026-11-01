import pytest
from pathlib import Path
from app.core.claim_types import load_claim_types_config, InsuranceConfig


def test_claim_types_config_schema():
    config = load_claim_types_config()
    assert isinstance(config, InsuranceConfig)
    assert len(config.claim_types) == 5

    expected_types = [
        "health_cashless",
        "health_reimbursement",
        "motor_own_damage",
        "motor_theft",
        "life_death",
    ]
    for c_type in expected_types:
        assert c_type in config.claim_types
        cfg = config.claim_types[c_type]
        assert cfg.name
        assert cfg.product_type in ["HEALTH", "MOTOR", "LIFE"]
        assert len(cfg.required_documents) > 0
        assert len(cfg.departments) > 0
        assert cfg.deadlines.settlement_days == 30


def test_health_cashless_config():
    config = load_claim_types_config()
    cashless = config.claim_types["health_cashless"]
    assert "POLICY_COPY" in cashless.required_documents
    assert "ID_PROOF" in cashless.required_documents
    assert cashless.deadlines.pre_auth_decision_hours == 1
    assert cashless.deadlines.final_auth_after_discharge_hours == 3


def test_motor_own_damage_config():
    config = load_claim_types_config()
    motor = config.claim_types["motor_own_damage"]
    assert "DRIVING_LICENCE" in motor.required_documents
    assert "SURVEYOR" in motor.departments
    assert motor.deadlines.surveyor_assignment_hours == 24
