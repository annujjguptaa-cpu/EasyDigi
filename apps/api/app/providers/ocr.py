import re
from typing import Dict, Any
from app.providers.base import OCRProvider


class MockOCRProvider(OCRProvider):
    """
    Mock OCR Provider that simulates document parsing.
    Enforces Hard Rule: Masks all Aadhaar numbers to last 4 digits only.
    """
    async def extract_masked_fields(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        fname_lower = filename.lower()
        
        if "pan" in fname_lower:
            return {
                "doc_type": "PAN",
                "name": "Rahul Verma",
                "dob": "1992-05-14",
                "pan_masked": "ABCDE1234F",
                "status": "VERIFIED"
            }
        elif "aadhaar" in fname_lower:
            return {
                "doc_type": "AADHAAR_OFFLINE",
                "name": "Rahul Verma",
                "dob": "1992-05-14",
                "id_last4": "4321",  # Strictly last 4 digits only
                "status": "VERIFIED"
            }
        elif "salary" in fname_lower:
            return {
                "doc_type": "SALARY_SLIP",
                "employer_name": "Tech Innovations Pvt Ltd",
                "monthly_net_pay": 85000.0,
                "status": "VERIFIED"
            }
        elif "marksheet" in fname_lower or "degree" in fname_lower:
            return {
                "doc_type": "MARKSHEET",
                "degree_name": "Bachelor of Technology in Computer Science",
                "passing_year": 2014,
                "status": "VERIFIED"
            }
        
        return {
            "doc_type": "GENERIC",
            "name": "Applicant",
            "status": "UNRECOGNIZED"
        }
