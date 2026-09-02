import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

CORREIOS_COMPANY_NAME = "Correios"
SUPERFRETE_BASE_URLS = {
    True: "https://sandbox.superfrete.com/api/v0/calculator",
    False: "https://api.superfrete.com/api/v0/calculator",
}


def _api_url():
    return SUPERFRETE_BASE_URLS[bool(settings.SUPERFRETE_SANDBOX)]


def _mock_options():
    return [
        {"name": "PAC", "price": 29.90, "delivery_time": 7},
        {"name": "SEDEX", "price": 49.90, "delivery_time": 3},
    ]


def calculate_shipping(figure, destination_zip, origin_zip):
    token = settings.SUPERFRETE_TOKEN
    if not token:
        if settings.DEBUG:
            return _mock_options(), None
        return [], "Cálculo de frete indisponível no momento."
    if not origin_zip:
        return [], "CEP de origem não configurado."

    payload = {
        "from": {"postal_code": re.sub(r"\D", "", origin_zip)},
        "to": {"postal_code": re.sub(r"\D", "", destination_zip)},
        "package": {
            "height": str(figure.height_cm),
            "width": str(figure.width_cm),
            "length": str(figure.length_cm),
            "weight": str(figure.weight_kg),
        },
        "services": settings.SUPERFRETE_SERVICES,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": f"Superfrete ({settings.SUPERFRETE_USER_AGENT_EMAIL})",
        "accept": "application/json",
        "content-type": "application/json",
    }

    try:
        response = requests.post(_api_url(), json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.warning("SuperFrete API falhou: %s", exc)
        return [], "Não foi possível consultar o frete agora. Tente novamente."

    options = []
    for item in data:
        company = (item.get("company") or {}).get("name", "")
        if company != CORREIOS_COMPANY_NAME:
            continue
        if item.get("has_error"):
            continue
        options.append(
            {
                "name": item.get("name"),
                "price": float(item.get("price") or 0),
                "delivery_time": item.get("delivery_time"),
            }
        )

    options.sort(key=lambda o: o["price"])
    return options, None