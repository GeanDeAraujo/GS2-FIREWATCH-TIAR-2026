"""HTTP Webhook sender for IBAMA and other external systems."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

# ── TODO: set IBAMA_WEBHOOK_URL and IBAMA_API_KEY in .env ────────────────────
IBAMA_WEBHOOK_URL = os.environ.get("IBAMA_WEBHOOK_URL", "")
IBAMA_API_KEY = os.environ.get("IBAMA_API_KEY", "")


class WebhookSender:
    """Generic authenticated HTTP webhook sender."""

    def __init__(self, url: str, api_key: str, timeout: int = 15):
        if not url:
            raise ValueError("Webhook URL is not set")
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def send(self, payload: Dict[str, Any], retries: int = 3) -> bool:
        """POST *payload* as JSON to the configured webhook URL."""
        for attempt in range(1, retries + 1):
            try:
                response = self.session.post(
                    self.url,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                logger.info(
                    "Webhook delivered (attempt %d/%d) → %s  status=%d",
                    attempt, retries, self.url, response.status_code,
                )
                return True
            except requests.RequestException as exc:
                logger.warning("Webhook attempt %d/%d failed: %s", attempt, retries, exc)

        logger.error("All %d webhook attempts failed for %s", retries, self.url)
        return False


def send_ibama_alert(
    detection_id: str,
    severity: str,
    class_name: str,
    confidence: float,
    latitude: float,
    longitude: float,
    state: str,
    image_key: Optional[str] = None,
) -> bool:
    """Send a standardized fire alert to the IBAMA webhook."""
    if not IBAMA_WEBHOOK_URL:
        logger.error("IBAMA_WEBHOOK_URL is not configured in .env")
        return False

    sender = WebhookSender(url=IBAMA_WEBHOOK_URL, api_key=IBAMA_API_KEY)

    payload = {
        "source": "FireWatch",
        "detection_id": detection_id,
        "severity": severity,
        "type": class_name,
        "confidence": round(confidence, 4),
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "state": state,
        },
        "image_key": image_key,
    }

    return sender.send(payload)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = send_ibama_alert(
        detection_id="test-001",
        severity="ALTA",
        class_name="foco_ativo",
        confidence=0.95,
        latitude=-3.4653,
        longitude=-62.2159,
        state="AM",
    )
    print("Sent:", success)
