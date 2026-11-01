import pytest
import time
from httpx import AsyncClient
from app.services.wish_engine import WishEngineService, _WISH_STORE


@pytest.mark.asyncio
async def test_summon_wish_and_single_use(client: AsyncClient):
    # 1. Summon a Wish
    summon_res = await client.post("/api/v1/wishes/summon", json={
        "wish_type": "OPPORTUNITY_WISH",
        "customer_fictional_id": "cust_rahul_01",
        "customer_masked_mobile": "XXXXXX9901"
    })
    assert summon_res.status_code == 200
    wish_data = summon_res.json()
    token = wish_data["wish_token"]
    wish_id = wish_data["wish_id"]
    assert wish_data["state"] == "summoned"

    # 2. Access Wish via token -> Transitions to "opened"
    access_res = await client.get(f"/api/v1/wishes/{token}")
    assert access_res.status_code == 200
    assert access_res.json()["state"] == "opened"

    # 3. Simulate granting the wish
    _WISH_STORE[token].state = "granted"

    # 4. TEST SECURITY: Wish works once; subsequent access fails
    second_res = await client.get(f"/api/v1/wishes/{token}")
    assert second_res.status_code == 410
    assert "already been granted" in second_res.json()["detail"]


@pytest.mark.asyncio
async def test_expired_wish_rejected(client: AsyncClient):
    # Summon with 1s TTL
    summon_res = await client.post("/api/v1/wishes/summon", json={
        "wish_type": "SCHOLAR_WISH",
        "customer_fictional_id": "cust_amit_02",
        "ttl_seconds": 1
    })
    token = summon_res.json()["wish_token"]
    
    # Wait for expiry
    time.sleep(1.1)

    res = await client.get(f"/api/v1/wishes/{token}")
    assert res.status_code == 410
    assert "expired" in res.json()["detail"]


@pytest.mark.asyncio
async def test_bulk_csv_summon_creates_n_unique_links(client: AsyncClient):
    customers = [
        {"id": "cust_01", "mobile": "XXXXXX1111"},
        {"id": "cust_02", "mobile": "XXXXXX2222"},
        {"id": "cust_03", "mobile": "XXXXXX3333"},
        {"id": "cust_04", "mobile": "XXXXXX4444"},
        {"id": "cust_05", "mobile": "XXXXXX5555"}
    ]
    res = await client.post("/api/v1/wishes/bulk-summon", json={
        "wish_type": "FOUNDATION_WISH",
        "customers": customers
    })
    assert res.status_code == 200
    data = res.json()
    assert data["total_summoned"] == 5
    tokens = {w["wish_token"] for w in data["wishes"]}
    assert len(tokens) == 5  # Strictly unique links


@pytest.mark.asyncio
async def test_wish_ledger_contains_no_pii(client: AsyncClient):
    wish = WishEngineService.summon_wish(
        wish_type="GROWTH_WISH",
        customer_fictional_id="cust_ledger_01",
        customer_masked_mobile="XXXXXX8888",
        client_ip="192.168.1.100"
    )
    
    # Fetch ledger
    res = await client.get(f"/api/v1/wishes/{wish.wish_id}/ledger")
    assert res.status_code == 200
    entries = res.json()
    assert len(entries) >= 1
    for entry in entries:
        # Zero raw PII: IP must be hashed
        assert "192.168.1.100" not in entry["hashed_ip"]
        assert len(entry["hashed_ip"]) == 16
        assert entry["event"] in ["summoned", "opened", "granted"]


@pytest.mark.asyncio
async def test_scoped_agent_permissions_enforced(client: AsyncClient):
    wish = WishEngineService.summon_wish(
        wish_type="OPPORTUNITY_WISH",
        customer_fictional_id="cust_agent_01",
        customer_masked_mobile="XXXXXX7777"
    )

    # 1. Allowed action succeeds
    allowed_res = await client.post("/api/v1/wishes/agent-action", json={
        "wish_token": wish.wish_token,
        "action": "fetch_masked_fields"
    })
    assert allowed_res.status_code == 200
    assert allowed_res.json()["status"] == "ALLOWED"

    # 2. Unauthorized action (e.g. scraping or direct database alteration) fails with 403
    forbidden_res = await client.post("/api/v1/wishes/agent-action", json={
        "wish_token": wish.wish_token,
        "action": "scrape_third_party_digilocker"
    })
    assert forbidden_res.status_code == 403
    assert "outside Djinn scoped permissions" in forbidden_res.json()["detail"]
