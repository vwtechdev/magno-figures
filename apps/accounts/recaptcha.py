import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


def is_recaptcha_configured():
    return bool(settings.RECAPTCHA_SITE_KEY and settings.RECAPTCHA_SECRET_KEY)


def verify_recaptcha_token(token):
    """Validate a reCAPTCHA v2 token against Google's siteverify API.

    Returns True only when the response is successful. Fail-closed: any
    network or parsing error returns False. When no keys are configured
    (local dev/test), verification is skipped and True is returned.
    """
    if not is_recaptcha_configured():
        return True
    if not token:
        return False
    try:
        response = requests.post(
            VERIFY_URL,
            data={
                "secret": settings.RECAPTCHA_SECRET_KEY,
                "response": token,
            },
            timeout=settings.RECAPTCHA_TIMEOUT,
        )
        result = response.json()
    except Exception:
        logger.warning("recaptcha verification request failed")
        return False
    return bool(result.get("success"))
