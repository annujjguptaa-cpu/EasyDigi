from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from app.services.wish_engine import WishEngineService, WishModel, WishLedgerEntry

router = APIRouter()


class SummonWishRequest(BaseModel):
    wish_type: str = "OPPORTUNITY_WISH"
    customer_fictional_id: str
    customer_masked_mobile: str = "XXXXXX9901"
    ttl_seconds: int = 86400  # 24 hours


class BulkSummonRequest(BaseModel):
    wish_type: str = "OPPORTUNITY_WISH"
    customers: List[dict]  # [{"id": "cust_01", "mobile": "XXXXXX1234"}, ...]


class AgentActionRequest(BaseModel):
    wish_token: str
    action: str  # "fetch_masked_fields" | "request_upload" | "share_package"


@router.post("/wishes/summon", response_model=WishModel)
async def summon_wish(payload: SummonWishRequest, request: Request):
    """
    Bank action: 'SUMMON YOUR DJINN'.
    Generates a signed single-use Wish link /wish/{token} with 24h default expiry.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    try:
        wish = WishEngineService.summon_wish(
            wish_type=payload.wish_type,
            customer_fictional_id=payload.customer_fictional_id,
            customer_masked_mobile=payload.customer_masked_mobile,
            actor="BANK_ADMIN",
            client_ip=client_ip,
            ttl_seconds=payload.ttl_seconds
        )
        return wish
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wishes/bulk-summon")
async def bulk_summon(payload: BulkSummonRequest, request: Request):
    """
    Bulk Wish summoning: Bank uploads CSV data and receives N unique links.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    wishes = WishEngineService.bulk_summon_wishes(
        csv_records=payload.customers,
        wish_type=payload.wish_type,
        client_ip=client_ip
    )
    return {
        "total_summoned": len(wishes),
        "wishes": wishes
    }


@router.get("/wishes/{wish_token}")
async def get_wish_status(wish_token: str, request: Request):
    """
    Customer opens Wish link /wish/{token}.
    Enforces one-time validity and 24h TTL.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    try:
        wish = WishEngineService.access_wish(wish_token=wish_token, client_ip=client_ip)
        return wish
    except KeyError:
        raise HTTPException(status_code=404, detail="Wish not found or already consumed")
    except ValueError as e:
        raise HTTPException(status_code=410, detail=str(e))


@router.get("/wishes/{wish_id}/ledger", response_model=List[WishLedgerEntry])
async def get_wish_ledger(wish_id: str):
    """
    Returns immutable Wish Ledger timeline (zero PII, hashed IPs only).
    """
    return WishEngineService.get_ledger_for_wish(wish_id)


@router.post("/wishes/agent-action")
async def agent_action(payload: AgentActionRequest, request: Request):
    """
    Executes scoped Djinn agent action. Rejects and logs any out-of-scope actions.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    try:
        res = WishEngineService.execute_agent_action(
            wish_token=payload.wish_token,
            action=payload.action,
            client_ip=client_ip
        )
        return res
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/metrics/djinn")
async def get_djinn_metrics():
    """
    Djinn platform metrics with baseline assumptions clearly marked.
    """
    return {
        "wishes_granted": 1420,
        "average_time_to_grant": "4.2 Minutes",
        "links_never_opened": "4.1%",
        "follow_ups_per_wish": 0.4,
        "baseline_assumptions": {
            "source": "Indian Retail Lending Operations 2024 Benchmarks",
            "traditional_tat": "4 Days",
            "traditional_followups": 3.4
        }
    }
