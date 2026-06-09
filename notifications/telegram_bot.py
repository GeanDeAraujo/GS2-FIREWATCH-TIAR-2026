"""Telegram bot for Defesa Civil fire alerts."""
from __future__ import annotations

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ── TODO: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env ────────────────
# Create a bot: https://t.me/BotFather → /newbot
# Get chat_id: send a message to the bot, then call
#   https://api.telegram.org/bot<TOKEN>/getUpdates
# ─────────────────────────────────────────────────────────────────────────────

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_API_BASE = "https://api.telegram.org/bot"

SEVERITY_EMOJI = {"ALTA": "🔴", "MEDIA": "🟡", "BAIXA": "🟢"}


class TelegramAlertBot:
    def __init__(self, token: str = BOT_TOKEN, chat_id: str = CHAT_ID):
        if not token or not chat_id:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env"
            )
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"{TELEGRAM_API_BASE}{self.token}"

    def send_alert(
        self,
        detection_id: str,
        severity: str,
        class_name: str,
        confidence: float,
        latitude: float,
        longitude: float,
        state: str,
        image_key: Optional[str] = None,
    ) -> bool:
        """Send a formatted fire alert message to the configured Telegram chat."""
        emoji = SEVERITY_EMOJI.get(severity, "⚠️")
        maps_url = f"https://maps.google.com/?q={latitude},{longitude}"

        text = (
            f"{emoji} *[FireWatch] Alerta de Incêndio — {severity}*\n\n"
            f"📍 *Estado:* {state}\n"
            f"🔥 *Tipo:* {class_name.replace('_', ' ').title()}\n"
            f"📊 *Confiança:* {confidence * 100:.1f}%\n"
            f"🗺️ *Localização:* [{latitude:.4f}, {longitude:.4f}]({maps_url})\n"
            f"🆔 *ID:* `{detection_id}`"
        )

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            # Markdown (legado): tolera ., -, (, ), % sem escape, ao contrário do
            # MarkdownV2, que exigiria escapar esses caracteres e retornava 400.
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }

        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Telegram alert sent for detection %s", detection_id)
            return True
        except requests.RequestException as exc:
            logger.error("Failed to send Telegram alert: %s", exc)
            return False

    def send_location(self, latitude: float, longitude: float) -> bool:
        """Send a map pin to the Telegram chat."""
        try:
            response = requests.post(
                f"{self.base_url}/sendLocation",
                json={"chat_id": self.chat_id, "latitude": latitude, "longitude": longitude},
                timeout=10,
            )
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            logger.error("Failed to send Telegram location: %s", exc)
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = TelegramAlertBot()
    bot.send_alert(
        detection_id="test-001",
        severity="ALTA",
        class_name="foco_ativo",
        confidence=0.95,
        latitude=-3.4653,
        longitude=-62.2159,
        state="AM",
    )
