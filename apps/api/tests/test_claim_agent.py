import pytest
from app.services.claim_agent_service import ClaimIntakeAgent, generate_claim_intake_link


def test_detect_claim_type_scenarios():
    agent = ClaimIntakeAgent()

    # Life death
    res_life = agent.detect_claim_type("My father passed away last week, need to intimate demise for nominee payout")
    assert res_life["detected_type"] == "life_death"
    assert res_life["tone"] == "compassionate"

    # Motor theft
    res_theft = agent.detect_claim_type("My car was stolen last night from outside my society")
    assert res_theft["detected_type"] == "motor_theft"

    # Motor accident
    res_motor = agent.detect_claim_type("Had an accident at the intersection, front bumper smashed")
    assert res_motor["detected_type"] == "motor_own_damage"

    # Health cashless
    res_cashless = agent.detect_claim_type("Need cashless approval for planned surgery tomorrow at Apollo hospital")
    assert res_cashless["detected_type"] == "health_cashless"


def test_get_required_documents_checklists():
    agent = ClaimIntakeAgent()

    motor_info = agent.get_required_documents("motor_own_damage")
    assert "DRIVING_LICENCE" in motor_info["required_documents"]
    assert "SCENE_PHOTO" in motor_info["required_documents"]
    assert "corner shots" in motor_info["scenario_guidance"]

    life_info = agent.get_required_documents("life_death")
    assert "DEATH_CERTIFICATE" in life_info["required_documents"]
    assert "condolences" in life_info["scenario_guidance"]


@pytest.mark.asyncio
async def test_claim_agent_chat_strips_aadhaar_guardrail():
    agent = ClaimIntakeAgent()

    res = await agent.process_chat(
        user_message="My Aadhaar number is 2345 6789 0123 please verify my claim",
        claim_type="health_reimbursement",
        received_docs=[]
    )
    assert res["action"] == "SECURITY_WARNING"
    assert "never paste your Aadhaar" in res["reply"]


@pytest.mark.asyncio
async def test_claim_agent_chat_consolidated_query():
    agent = ClaimIntakeAgent()

    # Partial docs received for health reimbursement
    res = await agent.process_chat(
        user_message="Here is my intimation details, what documents do I need to give?",
        claim_type="health_reimbursement",
        received_docs=["POLICY_COPY", "ID_PROOF"]
    )
    assert res["action"] == "DOCS_REQUESTED"
    assert "DISCHARGE_SUMMARY" in res["reply"]
    assert "FINAL_BILL" in res["reply"]
    # Check that it asks in a consolidated sentence
    assert "single consolidated step" in res["reply"] or "all remaining documents together in one step" in res["reply"]


def test_generate_claim_intake_link():
    link_info = generate_claim_intake_link("CLM-HLT-2024-8801", base_url="http://localhost:3001")
    assert link_info["claim_number"] == "CLM-HLT-2024-8801"
    assert "claim_" in link_info["token"]
    assert link_info["url"].startswith("http://localhost:3001/claim/claim_")
    assert link_info["expires_at"] is not None
