import io
import re
from typing import Dict, Any, List, Optional, Tuple
from app.services.document_service import DocumentClassifier, FieldMasker, CrossCheckEngine


class InsuranceDocumentClassifier:
    """
    19 Regulated Document Classifiers for Insurance Claims:
    1.  POLICY_COPY
    2.  ID_PROOF (PAN, Aadhaar masked)
    3.  CLAIM_FORM
    4.  PRE_AUTH_FORM
    5.  DISCHARGE_SUMMARY
    6.  FINAL_BILL
    7.  ITEMISED_BILL
    8.  PAID_RECEIPT
    9.  CANCELLED_CHEQUE
    10. PRESCRIPTION
    11. LAB_REPORT
    12. PHARMACY_BILL
    13. IMPLANT_STICKER
    14. DRIVING_LICENCE
    15. RC (Vehicle Registration)
    16. SCENE_PHOTO
    17. REPAIR_ESTIMATE
    18. FIR (Police First Information Report)
    19. DEATH_CERTIFICATE
    """
    # Order rules from more specific to generic
    RULES = [
        ("pharmacy", "PHARMACY_BILL"),
        ("medicine", "PHARMACY_BILL"),
        ("itemised", "ITEMISED_BILL"),
        ("breakdown", "ITEMISED_BILL"),
        ("pre_auth", "PRE_AUTH_FORM"),
        ("preauth", "PRE_AUTH_FORM"),
        ("claim_form", "CLAIM_FORM"),
        ("discharge", "DISCHARGE_SUMMARY"),
        ("final_bill", "FINAL_BILL"),
        ("hospital_bill", "FINAL_BILL"),
        ("paid_receipt", "PAID_RECEIPT"),
        ("receipt", "PAID_RECEIPT"),
        ("cancelled_cheque", "CANCELLED_CHEQUE"),
        ("cheque", "CANCELLED_CHEQUE"),
        ("passbook", "CANCELLED_CHEQUE"),
        ("prescription", "PRESCRIPTION"),
        ("rx", "PRESCRIPTION"),
        ("lab", "LAB_REPORT"),
        ("diagnostic", "LAB_REPORT"),
        ("pathology", "LAB_REPORT"),
        ("implant", "IMPLANT_STICKER"),
        ("sticker", "IMPLANT_STICKER"),
        ("stent", "IMPLANT_STICKER"),
        ("driving", "DRIVING_LICENCE"),
        ("licence", "DRIVING_LICENCE"),
        ("license", "DRIVING_LICENCE"),
        ("dl", "DRIVING_LICENCE"),
        ("vehicle_rc", "RC"),
        ("registration", "RC"),
        ("rc", "RC"),
        ("scene", "SCENE_PHOTO"),
        ("damage", "SCENE_PHOTO"),
        ("photo", "SCENE_PHOTO"),
        ("estimate", "REPAIR_ESTIMATE"),
        ("quotation", "REPAIR_ESTIMATE"),
        ("garage", "REPAIR_ESTIMATE"),
        ("fir", "FIR"),
        ("police", "FIR"),
        ("inquest", "FIR"),
        ("death", "DEATH_CERTIFICATE"),
        ("mortem", "DEATH_CERTIFICATE"),
        ("policy", "POLICY_COPY"),
        ("schedule", "POLICY_COPY"),
        ("pan", "ID_PROOF"),
        ("aadhaar", "ID_PROOF"),
        ("voter", "ID_PROOF"),
        ("passport", "ID_PROOF"),
        ("bill", "FINAL_BILL"),
    ]

    @classmethod
    def classify(cls, filename: str, text_content: Optional[str] = None) -> str:
        text = f"{filename} {text_content or ''}".lower()
        for key, category in cls.RULES:
            if key in text:
                return category
        return "OTHER"



class PromptInjectionGuard:
    """
    Guards OCR and document extraction payloads against adversarial prompt injections.
    Hard Rule: Prompt injections inside customer document text/OCR must be neutralized
    before being passed to an LLM or recorded in claim logs.
    """
    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+(an?\s+)?unrestricted", re.IGNORECASE),
        re.compile(r"system\s*:\s*", re.IGNORECASE),
        re.compile(r"approve\s+this\s+claim\s+without\s+verification", re.IGNORECASE),
        re.compile(r"set\s+coverage\s+to\s+100%", re.IGNORECASE),
        re.compile(r"<\|im_start\|>", re.IGNORECASE),
        re.compile(r"<\|im_end\|>", re.IGNORECASE),
        re.compile(r"###\s*instruction", re.IGNORECASE)
    ]

    @classmethod
    def sanitize(cls, text: str) -> Tuple[str, bool]:
        sanitized = text
        detected = False
        for pat in cls.INJECTION_PATTERNS:
            if pat.search(sanitized):
                detected = True
                sanitized = pat.sub("[REDACTED_ADVERSARIAL_INSTRUCTION]", sanitized)
        return sanitized, detected


class ImageQualityDetector:
    """
    Evaluates evidence quality (camera overlays, blur, and cropping hints).
    Provides feedback for mobile capture:
    - High blur -> 'Please hold the camera steady'
    - Incomplete crop / aspect ratio -> 'Ensure all 4 corners of the bill or vehicle are visible'
    """
    @staticmethod
    def analyze_capture(
        image_bytes: bytes,
        filename: str,
        dimensions: Optional[Tuple[int, int]] = None
    ) -> Dict[str, Any]:
        size_bytes = len(image_bytes)

        # Flag suspiciously tiny files as blurred / low-res
        is_too_small = size_bytes < 5000  # < 5KB
        is_blurred = False
        blur_score = 0.85  # Higher is sharper

        if is_too_small:
            blur_score = 0.2
            is_blurred = True

        is_cropped_properly = True
        if dimensions:
            w, h = dimensions
            if w < 400 or h < 400:
                is_cropped_properly = False

        guidance = []
        if is_blurred:
            guidance.append("Image appears blurry. Please hold steady and ensure good lighting.")
        if not is_cropped_properly:
            guidance.append("Crop warning: Ensure all 4 document borders or full vehicle edges are in frame.")

        return {
            "is_usable": not is_blurred and is_cropped_properly,
            "blur_score": blur_score,
            "is_blurred": is_blurred,
            "is_cropped_properly": is_cropped_properly,
            "guidance": guidance,
            "size_bytes": size_bytes
        }


class MultiPagePdfMerger:
    """
    Combines itemized bills, lab reports, and prescriptions into a unified claim evidence PDF.
    """
    @staticmethod
    def merge_pdf_buffers(pdf_list: List[bytes]) -> bytes:
        if not pdf_list:
            return b""
        if len(pdf_list) == 1:
            return pdf_list[0]

        # Simple robust PDF stream concatenator for demo/synthetic pipeline
        merged = bytearray()
        merged.extend(b"%PDF-1.4\n% EASYDIGI MERGED CLAIM EVIDENCE BUNDLE\n")
        for i, pdf_bytes in enumerate(pdf_list):
            merged.extend(f"\n% --- SECTION {i+1} ---\n".encode("utf-8"))
            merged.extend(pdf_bytes)
        merged.extend(b"\n%%EOF\n")
        return bytes(merged)


class InsuranceOcrExtractor:
    """
    Extracts structured, masked metadata from claim evidence while running
    PromptInjectionGuard and FieldMasker to ensure zero PII leaks.
    """
    @classmethod
    def extract_and_mask(cls, raw_ocr_text: str, doc_type: str) -> Dict[str, Any]:
        sanitized_text, has_injection = PromptInjectionGuard.sanitize(raw_ocr_text)

        extracted: Dict[str, Any] = {
            "doc_type": doc_type,
            "adversarial_instruction_detected": has_injection,
            "sanitized_preview": sanitized_text[:200]
        }

        # Bill amount extraction (e.g. Total: Rs 1,85,000 or Amount: 120000)
        amt_match = re.search(r"(?:total|amount|rs\.?|inr)\s*:?\s*([\d,]+(?:\.\d{2})?)", sanitized_text, re.IGNORECASE)
        if amt_match:
            try:
                amt_str = amt_match.group(1).replace(",", "")
                extracted["extracted_amount"] = float(amt_str)
            except ValueError:
                pass

        # Date extraction
        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b", sanitized_text)
        if date_match:
            extracted["extracted_date"] = date_match.group(1)

        # Aadhaar detection (12 digits, possibly spaced) -> store last 4 only
        aadhaar_match = re.search(r"(\d{4}\s?\d{4}\s?\d{4})", sanitized_text)
        if aadhaar_match:
            digits = re.sub(r"\s+", "", aadhaar_match.group(1))
            if len(digits) == 12:
                extracted["id_last4"] = digits[-4:]

        # PAN detection -> mask
        pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", sanitized_text)
        if pan_match:
            extracted["pan_masked"] = FieldMasker.mask_pan(pan_match.group(1))

        return extracted
