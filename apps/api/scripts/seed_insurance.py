import asyncio
import json
import os
from datetime import datetime
from sqlalchemy import select
from app.db.session import AsyncSessionLocal, engine, Base
import app.db.models  # ensure registered
import app.db.insurance_models  # ensure registered
from app.db.insurance_models import (
    Policy, Claim, ClaimDocument, ClaimEvent, ClaimDeadline, CoverageResult,
    FraudFlag, ClaimTask, Settlement, PolicyStatus, ClaimStatus,
    InsuranceDepartment, DeadlineStatus, CoverageStatus
)
from app.core.logging import logger

SEED_INSURANCE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../seed_data/insurance")
)


async def seed_insurance_data():
    logger.info("Initializing insurance tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    scenario_dirs = [
        "policy_clean_health",
        "policy_reimburse_mismatch",
        "policy_motor_outside_period",
        "policy_motor_missing_fir",
        "policy_life_nominee_mismatch",
    ]

    async with AsyncSessionLocal() as session:
        for folder in scenario_dirs:
            meta_file = os.path.join(SEED_INSURANCE_DIR, folder, "metadata.json")
            if not os.path.exists(meta_file):
                logger.warning(f"Metadata file not found: {meta_file}")
                continue

            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            pol_data = data["policy"]
            claim_data = data["claim"]

            # 1. Upsert Policy
            res = await session.execute(
                select(Policy).where(Policy.number == pol_data["policy_number"])
            )
            policy = res.scalar_one_or_none()

            start_dt = datetime.fromisoformat(pol_data["start_date"])
            end_dt = datetime.fromisoformat(pol_data["end_date"])

            if not policy:
                policy = Policy(
                    number=pol_data["policy_number"],
                    holder_name=pol_data["holder_name"],
                    holder_id=pol_data["holder_id"],
                    product_type=pol_data["product_type"],
                    start_date=start_dt,
                    end_date=end_dt,
                    sum_insured=pol_data["sum_insured"],
                    deductible=pol_data.get("deductible", 0),
                    co_pay_pct=pol_data.get("co_pay_pct", 0.0),
                    waiting_period_days=pol_data.get("waiting_period_days", 0),
                    status=PolicyStatus[pol_data.get("status", "ACTIVE")],
                    nominee_name=pol_data.get("nominee_name"),
                    nominee_relation=pol_data.get("nominee_relation"),
                    metadata_json=data.get("expected_outcome", {})
                )
                session.add(policy)
                await session.flush()
                logger.info(f"Created policy: {policy.number} for {policy.holder_name}")

            # 2. Upsert Claim
            c_res = await session.execute(
                select(Claim).where(Claim.claim_number == claim_data["claim_number"])
            )
            claim = c_res.scalar_one_or_none()

            incident_dt = datetime.fromisoformat(claim_data["incident_date"])

            if not claim:
                claim = Claim(
                    claim_number=claim_data["claim_number"],
                    policy_id=policy.id,
                    type=claim_data["type"],
                    status=ClaimStatus.INTIMATED,
                    incident_date=incident_dt,
                    claimant_name=claim_data["claimant_name"],
                    claimant_phone=claim_data.get("claimant_phone"),
                    requested_amount=claim_data.get("requested_amount", 0)
                )
                session.add(claim)
                await session.flush()
                logger.info(f"Created claim: {claim.claim_number}")

                # 3. Create Documents
                for doc in data.get("documents", []):
                    claim_doc = ClaimDocument(
                        claim_id=claim.id,
                        doc_type=doc["doc_type"],
                        status=doc.get("status", "VERIFIED"),
                        encrypted_blob_ref=f"seed_data/insurance/{folder}/{doc['filename']}",
                        masked_fields=doc.get("masked_fields", {}),
                        ocr_confidence=0.98
                    )
                    session.add(claim_doc)

                # 4. Create Initial Event
                init_event = ClaimEvent(
                    claim_id=claim.id,
                    action="CLAIM_INTIMATED",
                    actor=claim_data["claimant_name"],
                    details={
                        "channel": "WEB_CONSENT_FLOW",
                        "scenario": data.get("scenario")
                    }
                )
                session.add(init_event)

                # 5. Populate Fraud Flags if any in expected_outcome
                for flag in data.get("expected_outcome", {}).get("flags", []):
                    fraud_flag = FraudFlag(
                        claim_id=claim.id,
                        flag_type=flag["flag_type"],
                        severity=flag.get("severity", "MEDIUM"),
                        evidence=flag.get("evidence", {})
                    )
                    session.add(fraud_flag)

        await session.commit()
        logger.info("Successfully seeded all 5 fictional insurance scenarios.")


if __name__ == "__main__":
    asyncio.run(seed_insurance_data())
