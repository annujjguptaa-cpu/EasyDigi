import re
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.services.agent_engine import ChatAgentGuardrails
from app.core.claim_types import load_claim_types_config
from app.providers.factory import get_policy_provider


class ClaimIntakeAgent:
    """
    Intelligent claim intake assistant guiding the policyholder via mobile-first chat (/claim/{token}).
    Hard Rules:
    - Never collects raw Aadhaar/OTP (strips and refuses via ChatAgentGuardrails).
    - Single consolidated query for missing items.
    - Sensitive tone for death claims, structured photo checklist for motor claims,
      clear pre-auth vs reimbursement breakdown for health claims.
    - Code determines status & required documents; LLM/agent executes tools deterministically.
    """

    def __init__(self):
        self.config = load_claim_types_config()
        self.policy_provider = get_policy_provider()

    # --- Tool: get_claim_status ---
    def get_claim_status(
        self,
        claim_type: str,
        received_docs: List[str],
        incident_date: Optional[str] = None
    ) -> Dict[str, Any]:
        cfg = self.config.claim_types.get(claim_type)
        if not cfg:
            return {"error": f"Unknown claim type: {claim_type}"}

        missing = [doc for doc in cfg.required_documents if doc not in received_docs]
        return {
            "claim_type": claim_type,
            "claim_name": cfg.name,
            "product_type": cfg.product_type,
            "is_complete": len(missing) == 0,
            "missing_required_documents": missing,
            "received_documents": received_docs,
            "deadlines": cfg.deadlines.model_dump(exclude_none=True),
            "departments_involved": cfg.departments
        }

    # --- Tool: detect_claim_type ---
    def detect_claim_type(self, user_description: str) -> Dict[str, Any]:
        text = user_description.lower()

        # Life / Death
        if any(w in text for w in ["death", "deceased", "passed away", "expired", "nominee", "demise"]):
            return {
                "detected_type": "life_death",
                "confidence": 0.95,
                "reason": "Mention of death / demise / nominee",
                "tone": "compassionate"
            }

        # Motor Theft
        if any(w in text for w in ["theft", "stolen", "chori", "lost car", "lost bike", "snatched"]):
            return {
                "detected_type": "motor_theft",
                "confidence": 0.95,
                "reason": "Vehicle stolen / theft intimation",
                "tone": "urgent_action"
            }

        # Motor Own Damage
        if any(w in text for w in ["accident", "collision", "hit", "bumper", "scratch", "dent", "damage", "surveyor", "car", "bike"]):
            return {
                "detected_type": "motor_own_damage",
                "confidence": 0.92,
                "reason": "Vehicle damage / accident at scene",
                "tone": "structured_checklist"
            }

        # Health Cashless
        if any(w in text for w in ["cashless", "tpa desk", "hospital admission", "admitted", "planned surgery", "emergency room", "pre-auth"]):
            return {
                "detected_type": "health_cashless",
                "confidence": 0.90,
                "reason": "Hospitalization / TPA cashless request",
                "tone": "clear_procedural"
            }

        # Health Reimbursement
        if any(w in text for w in ["reimbursement", "discharged", "hospital bill", "paid receipt", "pharmacy bill", "medical bills"]):
            return {
                "detected_type": "health_reimbursement",
                "confidence": 0.90,
                "reason": "Post-discharge bill reimbursement",
                "tone": "clear_procedural"
            }

        return {
            "detected_type": "health_reimbursement",
            "confidence": 0.50,
            "reason": "Defaulting to medical reimbursement; please confirm your claim nature",
            "tone": "neutral"
        }

    # --- Tool: get_required_documents ---
    def get_required_documents(self, claim_type: str) -> Dict[str, Any]:
        cfg = self.config.claim_types.get(claim_type)
        if not cfg:
            return {"error": f"Unknown claim type: {claim_type}"}

        scenario_guidance = ""
        if claim_type == "motor_own_damage":
            scenario_guidance = (
                "Motor Evidence Capture Checklist:\n"
                "• 4 wide-angle corner shots showing overall vehicle and license plate.\n"
                "• Close-up damage photos with clear lighting (dents, scratches, broken parts).\n"
                "• Scene photos including road markings or collision barrier.\n"
                "• Driving Licence and RC from DigiLocker or camera scan."
            )
        elif claim_type == "health_cashless":
            scenario_guidance = (
                "Cashless Hospitalization Guidance:\n"
                "• Pre-authorization approval decision within 1 hour.\n"
                "• Final authorization at discharge within 3 hours.\n"
                "• Keep your TPA / Health Card, Policy Copy, and Hospital Admission letter ready."
            )
        elif claim_type == "health_reimbursement":
            scenario_guidance = (
                "Reimbursement Checklist:\n"
                "• Discharge Summary with doctor's final diagnosis.\n"
                "• Final consolidated bill matching the itemized bill breakdowns.\n"
                "• Original paid receipts and cancelled cheque with your name and IFSC."
            )
        elif claim_type == "life_death":
            scenario_guidance = (
                "Our sincere condolences for your loss. We are here to assist you gently through this process.\n"
                "Required items:\n"
                "• Official Death Certificate issued by the Municipal Corporation.\n"
                "• Nominee Photo ID and Cancelled Cheque / Bank details matching the registered nominee."
            )

        return {
            "claim_type": claim_type,
            "required_documents": cfg.required_documents,
            "optional_documents": cfg.optional_documents,
            "scenario_guidance": scenario_guidance
        }

    # --- Process User Interaction / Conversational Guidance ---
    async def process_chat(
        self,
        user_message: str,
        claim_type: str,
        received_docs: List[str],
        policy_number: Optional[str] = None,
        claimant_name: Optional[str] = None
    ) -> Dict[str, Any]:
        # 1. Security Guardrail Check
        guard = ChatAgentGuardrails.sanitize_user_input(user_message)
        if guard["has_sensitive_leak"]:
            return {
                "reply": guard["refusal_reason"],
                "action": "SECURITY_WARNING",
                "missing_documents": []
            }

        sanitized_msg = guard["sanitized_text"]

        # 2. Check for Policy Verification if policy_number is provided
        policy_info = None
        policy_warnings = []
        if policy_number:
            pol_check = await self.policy_provider.verify_policy_for_claim(
                policy_number=policy_number,
                holder_name=claimant_name or "",
                incident_date=datetime.utcnow()
            )
            if not pol_check["is_valid"]:
                policy_warnings.append(pol_check["message"])
            policy_info = pol_check.get("policy")

        # 3. Status Assessment
        status = self.get_claim_status(claim_type, received_docs)
        missing = status.get("missing_required_documents", [])

        # 4. Scenario-Specific Tone and Consolidated Query Formulation
        if len(missing) == 0:
            if claim_type == "life_death":
                reply = (
                    "Thank you. All required documents for the death claim intimation have been received. "
                    "Our Claims Intake team will process the settlement review with utmost priority. "
                    "You will receive an SMS and tracking update."
                )
            elif "motor" in claim_type:
                reply = (
                    "All required vehicle documents and evidence have been captured. "
                    "A certified surveyor is being assigned within 24 hours to inspect the vehicle."
                )
            else:
                reply = (
                    "All requested documents are verified and on file. "
                    "Your claim package is ready for TPA and department review."
                )
            action = "READY_FOR_SUBMISSION"
        else:
            missing_str = ", ".join(missing)
            if claim_type == "life_death":
                reply = (
                    f"Please accept our condolences. To proceed with the intimation, we gently request the following "
                    f"documents in a single consolidated step: {missing_str}. "
                    f"You may upload clear photos or fetch verified copies via DigiLocker."
                )
            elif claim_type == "motor_own_damage":
                reply = (
                    f"To process your motor claim, please provide the remaining required items: {missing_str}. "
                    f"Ensure you capture all 4 corner angles of the vehicle along with the close-ups of the impacted area."
                )
            elif claim_type == "health_reimbursement":
                reply = (
                    f"For your reimbursement claim, please submit all remaining documents together in one step: "
                    f"{missing_str}. Please ensure the itemized bill total matches the discharge summary."
                )
            else:
                reply = (
                    f"We have noted your claim details. Please provide the remaining required documents: {missing_str}."
                )
            action = "DOCS_REQUESTED"

        if policy_warnings:
            reply = f"⚠️ Notice: {policy_warnings[0]}\n\n" + reply

        return {
            "reply": reply,
            "action": action,
            "claim_type": claim_type,
            "missing_documents": missing,
            "policy_info": policy_info
        }


# --- Token Generator for Signed Single-Use Claim Intake Link ---
def generate_claim_intake_link(claim_number: str, base_url: str = "http://localhost:3001") -> Dict[str, Any]:
    token = f"claim_{secrets.token_urlsafe(24)}"
    expires_at = datetime.utcnow() + timedelta(hours=48)
    return {
        "claim_number": claim_number,
        "token": token,
        "url": f"{base_url}/claim/{token}",
        "expires_at": expires_at.isoformat()
    }
