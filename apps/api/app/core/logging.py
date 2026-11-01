import logging
import re
import sys
from typing import Any

# Regex patterns for sensitive identifiers
# Aadhaar (12 digits with optional spaces or dashes): match and mask first 8 digits
AADHAAR_PATTERN = re.compile(r'\b(?:\d[ -]?){8}(\d{4})\b')
# PAN format (5 letters, 4 digits, 1 letter)
PAN_PATTERN = re.compile(r'\b([A-Z]{5})(\d{4})([A-Z])\b')
# OTP patterns
OTP_PATTERN = re.compile(r'\b(?:otp|code|pin)\s*[:=]\s*(\d{4,8})\b', re.IGNORECASE)
# Authorization Bearer tokens / secret tokens
TOKEN_PATTERN = re.compile(r'(Bearer\s+)[A-Za-z0-9_\-\.]{15,}', re.IGNORECASE)
SECRET_KEY_PATTERN = re.compile(r'("(?:token|secret|password|access_token)"\s*:\s*")([^"]+)(")', re.IGNORECASE)


class MaskingLogFilter(logging.Filter):
    """
    Log filter that intercepts records and redacts any accidentally logged
    Aadhaar numbers (retains last 4 only), PANs, OTPs, Bearer tokens, or passwords.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.mask_value(v) for k, v in record.args.items()}
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(self.mask_value(v) for v in record.args)
        return True

    @classmethod
    def mask_text(cls, text: str) -> str:
        # Mask Aadhaar numbers to XXXXXXXX1234
        text = AADHAAR_PATTERN.sub(r'XXXXXXXX\1', text)
        # Mask PAN (keeps first 2 and last 1 char)
        text = PAN_PATTERN.sub(r'\1XXXX\3', text)
        # Mask OTPs
        text = OTP_PATTERN.sub(r'otp: [REDACTED_OTP]', text)
        # Mask Bearer tokens
        text = TOKEN_PATTERN.sub(r'\1[REDACTED_TOKEN]', text)
        # Mask secret JSON keys
        text = SECRET_KEY_PATTERN.sub(r'\1[REDACTED_SECRET]\3', text)
        return text

    @classmethod
    def mask_value(cls, val: Any) -> Any:
        if isinstance(val, str):
            return cls.mask_text(val)
        return val


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("docflow")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
        )
        handler.setFormatter(formatter)
        handler.addFilter(MaskingLogFilter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()
