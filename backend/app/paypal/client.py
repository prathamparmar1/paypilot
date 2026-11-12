import logging
import time
from decimal import Decimal

import httpx

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
_token = {"value": None, "exp": 0.0}


class PayPalError(Exception):
    def __init__(self, status: int, issue: str, message: str):
        super().__init__(message)
        self.status = status
        self.issue = issue
        self.message = message


def _raise(resp: httpx.Response):
    try:
        body = resp.json()
    except Exception:
        body = {}
    issue = ((body.get("details") or [{}])[0].get("issue")) or body.get("name") or "UNKNOWN"
    logger.error("PayPal error %s %s: %s", resp.status_code, issue, resp.text[:300])
    raise PayPalError(resp.status_code, issue, body.get("message", "PayPal request failed"))


def _access_token() -> str:
    if _token["value"] and time.time() < _token["exp"] - 60:
        return _token["value"]
    r = httpx.post(
        f"{settings.paypal_base_url}/v1/oauth2/token",
        auth=(settings.paypal_client_id, settings.paypal_client_secret),
        data={"grant_type": "client_credentials"},
        timeout=20,
    )
    if r.status_code != 200:
        _raise(r)
    data = r.json()
    _token["value"] = data["access_token"]
    _token["exp"] = time.time() + int(data.get("expires_in", 300))
    return _token["value"]


def _request(method: str, path: str, headers: dict | None = None, **kwargs) -> dict:
    h = {"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"}
    if headers:
        h.update(headers)
    r = httpx.request(method, f"{settings.paypal_base_url}{path}", headers=h, timeout=20, **kwargs)
    if r.status_code >= 400:
        _raise(r)
    return r.json()


def create_order(invoice_id, number: str, description: str, amount: Decimal, currency: str) -> dict:
    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": "default",
                "custom_id": str(invoice_id),
                "description": f"{number} - {description}"[:127],
                "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
            }
        ],
    }
    return _request("POST", "/v2/checkout/orders", json=body)


def get_order(order_id: str) -> dict:
    return _request("GET", f"/v2/checkout/orders/{order_id}")


def capture_order(order_id: str) -> dict:
    return _request(
        "POST",
        f"/v2/checkout/orders/{order_id}/capture",
        headers={"PayPal-Request-Id": f"capture-{order_id}"},
        json={},
    )


def verify_webhook(headers, event: dict) -> bool:
    body = {
        "auth_algo": headers.get("paypal-auth-algo"),
        "cert_url": headers.get("paypal-cert-url"),
        "transmission_id": headers.get("paypal-transmission-id"),
        "transmission_sig": headers.get("paypal-transmission-sig"),
        "transmission_time": headers.get("paypal-transmission-time"),
        "webhook_id": settings.paypal_webhook_id,
        "webhook_event": event,
    }
    if not all(body[k] for k in ("auth_algo", "cert_url", "transmission_id", "transmission_sig", "transmission_time")):
        return False
    try:
        res = _request("POST", "/v1/notifications/verify-webhook-signature", json=body)
    except PayPalError:
        return False
    return res.get("verification_status") == "SUCCESS"