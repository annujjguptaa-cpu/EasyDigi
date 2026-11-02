"""
Prompt 7 — Deadline & Timeline Engine
======================================
Tracks every claim deadline (driven by YAML config) and produces a unified
event+deadline timeline for bank staff visibility.

SAMPLE DEADLINES (not real insurer SLAs — for demo only):
  - health intimation:        48 hours
  - cashless pre-auth:        1 hour
  - final auth after discharge: 3 hours
  - reimbursement doc submission: 15 days
  - motor doc submission:     15 days
  - motor survey report:      15 days
  - settlement:               30 days
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.insurance_models import (
    Claim, ClaimDeadline, ClaimEvent, DeadlineStatus,
)
from app.core.claim_types import load_claim_types_config


# ── Deadline definitions per claim type (SAMPLE CONFIG) ────────

DEADLINE_TEMPLATES: dict[str, list[dict]] = {
    "health_cashless": [
        {"type": "intimation",          "owner": "POLICYHOLDER",    "hours": 48},
        {"type": "pre_auth_decision",   "owner": "TPA",             "hours": 1},
        {"type": "final_auth",          "owner": "TPA",             "hours": 3},
        {"type": "settlement",          "owner": "CLAIMS_OFFICER",  "hours": 30 * 24},
    ],
    "health_reimbursement": [
        {"type": "intimation",          "owner": "POLICYHOLDER",    "hours": 48},
        {"type": "doc_submission",      "owner": "POLICYHOLDER",    "hours": 15 * 24},
        {"type": "settlement",          "owner": "CLAIMS_OFFICER",  "hours": 30 * 24},
    ],
    "motor_own_damage": [
        {"type": "intimation",          "owner": "POLICYHOLDER",    "hours": 48},
        {"type": "doc_submission",      "owner": "POLICYHOLDER",    "hours": 15 * 24},
        {"type": "survey_report",       "owner": "SURVEYOR",        "hours": 15 * 24},
        {"type": "settlement",          "owner": "CLAIMS_OFFICER",  "hours": 30 * 24},
    ],
    "motor_theft": [
        {"type": "intimation",          "owner": "POLICYHOLDER",    "hours": 48},
        {"type": "doc_submission",      "owner": "POLICYHOLDER",    "hours": 15 * 24},
        {"type": "survey_report",       "owner": "SURVEYOR",        "hours": 15 * 24},
        {"type": "settlement",          "owner": "CLAIMS_OFFICER",  "hours": 30 * 24},
    ],
    "life_death": [
        {"type": "intimation",          "owner": "NOMINEE",         "hours": 48},
        {"type": "doc_submission",      "owner": "NOMINEE",         "hours": 15 * 24},
        {"type": "settlement",          "owner": "CLAIMS_OFFICER",  "hours": 30 * 24},
    ],
}


# ── DeadlineEngine ─────────────────────────────────────────────

class DeadlineEngine:

    async def initialise_deadlines(
        self,
        claim_id: str,
        claim_type: str,
        intimation_at: Optional[datetime] = None,
    ) -> List[dict]:
        """
        Create ClaimDeadline rows for all deadlines applicable to the claim type.
        Idempotent — skips if deadlines already exist for this claim.
        """
        templates = DEADLINE_TEMPLATES.get(claim_type, [])
        base_time = intimation_at or datetime.now(timezone.utc)

        async with AsyncSessionLocal() as session:
            # Idempotency: check existing
            existing = await session.execute(
                select(ClaimDeadline).where(ClaimDeadline.claim_id == claim_id)
            )
            if existing.scalars().first():
                return []  # already initialised

            created = []
            for tmpl in templates:
                due_at = base_time + timedelta(hours=tmpl["hours"])
                deadline = ClaimDeadline(
                    claim_id=claim_id,
                    deadline_type=tmpl["type"],
                    owner=tmpl["owner"],
                    due_at=due_at,
                    status=DeadlineStatus.RUNNING,
                )
                session.add(deadline)
                created.append({
                    "deadline_type": tmpl["type"],
                    "owner": tmpl["owner"],
                    "due_at": due_at.isoformat(),
                    "status": "RUNNING",
                })
            await session.commit()

        return created

    async def check_deadline_status(self, claim_id: str) -> List[dict]:
        """
        Return deadline status for all deadlines of a claim.
        Status: RUNNING | AT_RISK (≤4h) | BREACHED (past due) | MET
        """
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(ClaimDeadline).where(ClaimDeadline.claim_id == claim_id)
            )
            deadlines = res.scalars().all()

        results = []
        for dl in deadlines:
            if dl.status == DeadlineStatus.MET:
                computed = "MET"
                hours_remaining = None
            else:
                # Ensure timezone-aware comparison
                due_at = dl.due_at
                if due_at.tzinfo is None:
                    due_at = due_at.replace(tzinfo=timezone.utc)
                diff = (due_at - now).total_seconds() / 3600
                hours_remaining = round(diff, 1)
                if diff < 0:
                    computed = "BREACHED"
                elif diff <= 4:
                    computed = "AT_RISK"
                else:
                    computed = "RUNNING"

            results.append({
                "deadline_type":    dl.deadline_type,
                "owner":            dl.owner,
                "due_at":           dl.due_at.isoformat(),
                "status":           computed,
                "hours_remaining":  hours_remaining,
            })
        return results

    async def mark_deadline_met(self, claim_id: str, deadline_type: str) -> bool:
        """Mark a specific deadline as MET and log a ClaimEvent."""
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(ClaimDeadline).where(
                    ClaimDeadline.claim_id == claim_id,
                    ClaimDeadline.deadline_type == deadline_type,
                )
            )
            deadline = res.scalar_one_or_none()
            if not deadline:
                return False
            deadline.status = DeadlineStatus.MET
            event = ClaimEvent(
                claim_id=claim_id,
                action="DEADLINE_MET",
                actor="system",
                details={"deadline_type": deadline_type},
            )
            session.add(event)
            await session.commit()
        return True

    async def get_timeline(self, claim_id: str) -> List[dict]:
        """
        Unified timeline: ClaimEvents + ClaimDeadlines merged and sorted by timestamp.
        """
        async with AsyncSessionLocal() as session:
            ev_res = await session.execute(
                select(ClaimEvent).where(ClaimEvent.claim_id == claim_id)
                .order_by(ClaimEvent.timestamp)
            )
            events = ev_res.scalars().all()

            dl_res = await session.execute(
                select(ClaimDeadline).where(ClaimDeadline.claim_id == claim_id)
            )
            deadlines = dl_res.scalars().all()

        timeline = []
        for ev in events:
            ts = ev.timestamp
            if ts and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            timeline.append({
                "timestamp": ts.isoformat() if ts else None,
                "type":      "EVENT",
                "label":     ev.action.replace("_", " ").title(),
                "actor":     ev.actor,
                "status":    None,
                "details":   ev.details or {},
            })

        now = datetime.now(timezone.utc)
        for dl in deadlines:
            due_at = dl.due_at
            if due_at and due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
            diff_h = (due_at - now).total_seconds() / 3600 if due_at else 0
            if dl.status == DeadlineStatus.MET:
                status = "MET"
            elif diff_h < 0:
                status = "BREACHED"
            elif diff_h <= 4:
                status = "AT_RISK"
            else:
                status = "RUNNING"

            timeline.append({
                "timestamp": due_at.isoformat() if due_at else None,
                "type":      "DEADLINE",
                "label":     dl.deadline_type.replace("_", " ").title(),
                "actor":     dl.owner,
                "status":    status,
                "details":   {"hours_remaining": round(diff_h, 1)},
            })

        timeline.sort(key=lambda x: x["timestamp"] or "")
        return timeline


deadline_engine = DeadlineEngine()
