"""API Gateway Lambda handler — serves /detections, /stats and /alerts."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from services.dynamodb_service import (
    get_recent_alerts,
    get_stats,
    scan_detections,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Content-Type": "application/json",
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    path = event.get("path", "")
    params = event.get("queryStringParameters") or {}

    try:
        if path == "/detections":
            return _handle_detections(params)
        if path == "/stats":
            return _handle_stats()
        if path == "/alerts":
            return _handle_alerts(params)

        return _response(404, {"error": f"Unknown path: {path}"})

    except Exception as exc:  # noqa: BLE001
        logger.error("API error on %s: %s", path, exc)
        return _response(500, {"error": "Internal server error"})


def _handle_detections(params: dict) -> dict:
    state = params.get("state")
    hours = int(params.get("hours", 24))
    limit = int(params.get("limit", 200))
    items = scan_detections(state=state, hours=hours, limit=limit)
    return _response(200, {"detections": items, "count": len(items)})


def _handle_stats() -> dict:
    stats = get_stats()
    return _response(200, stats)


def _handle_alerts(params: dict) -> dict:
    limit = int(params.get("limit", 20))
    items = get_recent_alerts(limit=limit)
    return _response(200, {"alerts": items, "count": len(items)})


def _response(status: int, body: Any) -> dict:
    return {
        "statusCode": status,
        "headers": _CORS_HEADERS,
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }
