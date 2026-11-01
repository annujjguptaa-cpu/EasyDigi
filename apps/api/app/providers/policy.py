import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import select
from app.providers.base import PolicyProvider
from app.db.session import AsyncSessionLocal
from app.db.insurance_models import Policy, PolicyStatus
from app.core.logging import logger

SEED_INSURANCE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../seed_data/insurance")
)


class MockPolicyProvider(PolicyProvider):
    """
    Mock Policy Provider backed by database and seed data.
    Provides realistic policyholder verification and failure modes:
    - LAPSED_POLICY: Policy status is LAPSED or incident after expiry.
    - WRONG_HOLDER: Policy does not belong to claimant.
    - POLICY_NOT_FOUND: Unrecognized policy number.
    """

    async def get_policy(
        self,
        policy_number: str,
        holder_ref: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        # 1. First check in database
        async with AsyncSessionLocal() as session:
            query = select(Policy).where(Policy.number == policy_number)
            res = await session.execute(query)
            pol: Optional[Policy] = res.scalar_one_or_none()

            if pol:
                if holder_ref and pol.holder_id != holder_ref and pol.holder_name.lower() != holder_ref.lower():
                    logger.warning(f"Holder mismatch for policy {policy_number}: expected {holder_ref}, found {pol.holder_name}")
                    return None

                return {
                    "policy_number": pol.number,
                    "holder_name": pol.holder_name,
                    "holder_id": pol.holder_id,
                    "product_type": pol.product_type,
                    "start_date": pol.start_date.isoformat(),
                    "end_date": pol.end_date.isoformat(),
                    "sum_insured": pol.sum_insured,
                    "deductible": pol.deductible,
                    "co_pay_pct": pol.co_pay_pct,
                    "waiting_period_days": pol.waiting_period_days,
                    "status": pol.status.value,
                    "nominee_name": pol.nominee_name,
                    "nominee_relation": pol.nominee_relation,
                    "source": "DB"
                }

        # 2. Fallback to seed_data/insurance JSON files if db has not loaded yet
        if os.path.exists(SEED_INSURANCE_DIR):
            for folder in os.listdir(SEED_INSURANCE_DIR):
                meta_path = os.path.join(SEED_INSURANCE_DIR, folder, "metadata.json")
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    p_info = data.get("policy", {})
                    if p_info.get("policy_number") == policy_number:
                        if holder_ref and p_info.get("holder_id") != holder_ref and p_info.get("holder_name", "").lower() != holder_ref.lower():
                            return None
                        p_info["source"] = "SEED_FILE"
                        return p_info

        return None

    async def verify_policy_for_claim(
        self,
        policy_number: str,
        holder_name: str,
        incident_date: Any
    ) -> Dict[str, Any]:
        """
        Policy verification rules:
        1. Policy must exist (else POLICY_NOT_FOUND).
        2. Policyholder name must match (else WRONG_HOLDER).
        3. Policy must be ACTIVE (else LAPSED_POLICY).
        4. Incident date must be >= start_date and <= end_date (else INCIDENT_OUTSIDE_POLICY_PERIOD).
        """
        policy = await self.get_policy(policy_number)
        if not policy:
            return {
                "is_valid": False,
                "error_code": "POLICY_NOT_FOUND",
                "message": f"Policy '{policy_number}' could not be found."
            }

        # Validate holder
        pol_holder = policy.get("holder_name", "").strip().lower()
        claimed_holder = holder_name.strip().lower()
        if pol_holder != claimed_holder:
            return {
                "is_valid": False,
                "error_code": "WRONG_HOLDER",
                "message": f"Policy '{policy_number}' belongs to '{policy.get('holder_name')}', not '{holder_name}'.",
                "policy": policy
            }

        # Validate status
        if policy.get("status") != PolicyStatus.ACTIVE.value:
            return {
                "is_valid": False,
                "error_code": "LAPSED_POLICY",
                "message": f"Policy '{policy_number}' is {policy.get('status')} and not in active standing.",
                "policy": policy
            }

        # Validate dates
        if isinstance(incident_date, str):
            inc_dt = datetime.fromisoformat(incident_date)
        elif isinstance(incident_date, datetime):
            inc_dt = incident_date
        else:
            raise ValueError(f"Invalid incident_date type: {type(incident_date)}")

        start_dt = datetime.fromisoformat(policy["start_date"]) if isinstance(policy["start_date"], str) else policy["start_date"]
        end_dt = datetime.fromisoformat(policy["end_date"]) if isinstance(policy["end_date"], str) else policy["end_date"]

        if inc_dt < start_dt or inc_dt > end_dt:
            return {
                "is_valid": False,
                "error_code": "INCIDENT_OUTSIDE_POLICY_PERIOD",
                "message": f"Incident date {inc_dt.strftime('%Y-%m-%d')} is outside active policy period ({start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}).",
                "policy": policy
            }

        return {
            "is_valid": True,
            "error_code": None,
            "message": "Policy is active, belongs to claimant, and incident is within coverage period.",
            "policy": policy
        }


class InsurerApiProvider(PolicyProvider):
    """
    Production Insurer API Integration Stub.
    Connects to external Core Insurance Systems (Guidewire, Duck Creek, Tcs BaNCS).
    
    TODO: Insert production mTLS certs, OAuth2 client credentials, and standard
    IRDAI / Core Insurance API endpoints.
    """

    def __init__(
        self,
        api_base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ):
        self.api_base_url = api_base_url or "https://api.insurance-core.demo/v1"
        self.client_id = client_id
        self.client_secret = client_secret
        # TODO: Initialize mTLS context and encrypted JWT signing key

    async def get_policy(
        self,
        policy_number: str,
        holder_ref: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        # TODO: Make HTTPS GET /policies/{policy_number} with signed authorization header
        raise NotImplementedError("InsurerApiProvider requires certified production credentials")

    async def verify_policy_for_claim(
        self,
        policy_number: str,
        holder_name: str,
        incident_date: Any
    ) -> Dict[str, Any]:
        # TODO: Post to /claims/pre-verification endpoint of insurer gateway
        raise NotImplementedError("InsurerApiProvider requires certified production credentials")
