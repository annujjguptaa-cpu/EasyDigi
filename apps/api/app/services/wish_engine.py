import hashlib
import time
import uuid
import secrets
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class WishModel(BaseModel):
    wish_id: str
    wish_token: str
    wish_type: str  # FOUNDATION_WISH | SCHOLAR_WISH | OPPORTUNITY_WISH | GROWTH_WISH
    product_name: str
    customer_fictional_id: str
    customer_masked_mobile: str
    state: str  # summoned | opened | in_progress | granted | expired | revoked
    created_at: float
    expires_at: float
    allowed_actions: List[str]  # ['fetch_masked_fields', 'request_upload', 'share_package']


class WishLedgerEntry(BaseModel):
    entry_id: str
    wish_id: str
    event: str  # summoned | opened | consent_given | documents_fetched | gaps_filled | package_shared | departments_approved | granted | revoked
    actor: str  # BANK_ADMIN | CUSTOMER_PWA | DJINN_AGENT | DEPT_MAKER | DEPT_CHECKER
    timestamp: float
    outcome: str  # SUCCESS | PENDING | DENIED | REJECTED
    hashed_ip: str  # Zero PII: SHA-256 hash of client IP


# In-memory store for Wish management (simulating Redis / DB)
_WISH_STORE: Dict[str, WishModel] = {}
_WISH_LEDGER: List[WishLedgerEntry] = []


class WishEngineService:
    WISH_TYPE_DOC_MAP = {
        "FOUNDATION_WISH": ("Home Loan", ["PAN", "AADHAAR_MASKED", "SALARY_SLIP", "BANK_STATEMENT", "TITLE_DEED", "EC"]),
        "SCHOLAR_WISH": ("Education Loan", ["PAN", "AADHAAR_MASKED", "MARKSHEET", "SALARY_SLIP"]),
        "OPPORTUNITY_WISH": ("Personal Loan", ["PAN", "AADHAAR_MASKED", "SALARY_SLIP"]),
        "GROWTH_WISH": ("Business Loan", ["PAN", "AADHAAR_MASKED", "BANK_STATEMENT", "ITR", "FORM16"]),
    }

    @staticmethod
    def hash_ip(ip: str) -> str:
        """Never stores raw IP: stores irreversible SHA-256 salt digest"""
        return hashlib.sha256(f"salt_{ip}".encode()).hexdigest()[:16]

    @classmethod
    def summon_wish(
        cls,
        wish_type: str,
        customer_fictional_id: str,
        customer_masked_mobile: str,
        actor: str = "BANK_ADMIN",
        client_ip: str = "127.0.0.1",
        ttl_seconds: int = 86400  # 24h default expiry
    ) -> WishModel:
        if wish_type not in cls.WISH_TYPE_DOC_MAP:
            raise ValueError(f"Unknown Wish type: {wish_type}")

        product_name, _ = cls.WISH_TYPE_DOC_MAP[wish_type]
        wish_id = f"wish_{uuid.uuid4().hex[:12]}"
        wish_token = f"wsh_{secrets.token_urlsafe(24)}"
        now = time.time()

        wish = WishModel(
            wish_id=wish_id,
            wish_token=wish_token,
            wish_type=wish_type,
            product_name=product_name,
            customer_fictional_id=customer_fictional_id,
            customer_masked_mobile=customer_masked_mobile,
            state="summoned",
            created_at=now,
            expires_at=now + ttl_seconds,
            allowed_actions=["fetch_masked_fields", "request_upload", "share_package"]
        )

        _WISH_STORE[wish_token] = wish

        # Record in ledger
        cls.record_ledger_event(
            wish_id=wish_id,
            event="summoned",
            actor=actor,
            outcome="SUCCESS",
            client_ip=client_ip
        )

        return wish

    @classmethod
    def bulk_summon_wishes(
        cls,
        csv_records: List[Dict[str, str]],
        wish_type: str = "OPPORTUNITY_WISH",
        client_ip: str = "127.0.0.1"
    ) -> List[WishModel]:
        """Creates N unique wishes from bulk CSV (name, masked mobile)"""
        wishes = []
        for row in csv_records:
            cid = row.get("id") or f"cust_{uuid.uuid4().hex[:6]}"
            masked_mobile = row.get("mobile", "XXXXXX9901")
            wish = cls.summon_wish(
                wish_type=wish_type,
                customer_fictional_id=cid,
                customer_masked_mobile=masked_mobile,
                actor="BANK_ADMIN",
                client_ip=client_ip
            )
            wishes.append(wish)
        return wishes

    @classmethod
    def access_wish(cls, wish_token: str, client_ip: str = "127.0.0.1") -> WishModel:
        if wish_token not in _WISH_STORE:
            raise KeyError("Wish link does not exist or has already been consumed")

        wish = _WISH_STORE[wish_token]
        now = time.time()

        if now > wish.expires_at:
            wish.state = "expired"
            cls.record_ledger_event(wish.wish_id, "expired", "CUSTOMER_PWA", "DENIED", client_ip)
            raise ValueError("Wish link has expired (24h TTL exceeded)")

        if wish.state == "revoked":
            cls.record_ledger_event(wish.wish_id, "revoked", "CUSTOMER_PWA", "DENIED", client_ip)
            raise ValueError("Wish has been revoked by customer")

        if wish.state == "granted":
            raise ValueError("Wish link works once only and has already been granted")

        # Transition state
        if wish.state == "summoned":
            wish.state = "opened"
            cls.record_ledger_event(wish.wish_id, "opened", "CUSTOMER_PWA", "SUCCESS", client_ip)

        return wish

    @classmethod
    def record_ledger_event(
        cls,
        wish_id: str,
        event: str,
        actor: str,
        outcome: str,
        client_ip: str
    ) -> WishLedgerEntry:
        entry = WishLedgerEntry(
            entry_id=f"ledg_{uuid.uuid4().hex[:8]}",
            wish_id=wish_id,
            event=event,
            actor=actor,
            timestamp=time.time(),
            outcome=outcome,
            hashed_ip=cls.hash_ip(client_ip)
        )
        _WISH_LEDGER.append(entry)
        return entry

    @classmethod
    def get_ledger_for_wish(cls, wish_id: str) -> List[WishLedgerEntry]:
        return [entry for entry in _WISH_LEDGER if entry.wish_id == wish_id]

    @classmethod
    def execute_agent_action(
        cls,
        wish_token: str,
        action: str,
        client_ip: str = "127.0.0.1"
    ) -> Dict[str, Any]:
        """
        Enforces scoped Djinn agent permissions:
        Only allows actions in wish.allowed_actions.
        Hard Rule: Djinn agent must NOT scrape or automate DigiLocker or third-party sites.
        """
        wish = cls.access_wish(wish_token, client_ip)

        if action not in wish.allowed_actions:
            cls.record_ledger_event(
                wish.wish_id, f"unauthorized_action_{action}", "DJINN_AGENT", "DENIED", client_ip
            )
            raise PermissionError(
                f"Action '{action}' is outside Djinn scoped permissions: {wish.allowed_actions}"
            )

        cls.record_ledger_event(
            wish.wish_id, f"agent_action_{action}", "DJINN_AGENT", "SUCCESS", client_ip
        )
        return {"status": "ALLOWED", "action": action, "wish_id": wish.wish_id}
