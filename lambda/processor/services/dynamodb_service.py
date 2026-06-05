"""DynamoDB service — persist fire detection records."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from config import AWS_REGION, DYNAMODB_TABLE_NAME

logger = logging.getLogger(__name__)

# ── TODO: set DYNAMODB_TABLE_NAME in .env / Lambda environment variables ──────
_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
_table = _dynamodb.Table(DYNAMODB_TABLE_NAME)


def save_detection(
    latitude: float,
    longitude: float,
    class_name: str,
    confidence: float,
    area_px: float,
    image_key: str,
    state: str = "UNKNOWN",
    extra: Dict[str, Any] | None = None,
) -> tuple:
    """Persist a single detection to DynamoDB. Returns (detection_id, timestamp)."""
    detection_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    item = {
        "detection_id": detection_id,
        "timestamp": now,
        "latitude": str(latitude),
        "longitude": str(longitude),
        "class_name": class_name,
        "confidence": str(round(confidence, 4)),
        "area_px": str(round(area_px, 2)),
        "image_key": image_key,
        "state": state,
        "alert_sent": False,
    }
    if extra:
        item.update(extra)

    try:
        _table.put_item(Item=item)
        logger.info("Saved detection %s (%s, conf=%.2f)", detection_id, class_name, confidence)
    except ClientError as exc:
        logger.error("DynamoDB put_item failed: %s", exc)
        raise

    return detection_id, now


def mark_alert_sent(detection_id: str, timestamp: str) -> None:
    """Update alert_sent flag after SNS publish."""
    try:
        _table.update_item(
            Key={"detection_id": detection_id, "timestamp": timestamp},
            UpdateExpression="SET alert_sent = :val",
            ExpressionAttributeValues={":val": True},
        )
    except ClientError as exc:
        logger.error("Failed to mark alert_sent for %s: %s", detection_id, exc)
        raise


def query_by_state(state: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Return recent detections for a given Brazilian state code (e.g. 'AM')."""
    try:
        response = _table.query(
            IndexName="state-timestamp-index",
            KeyConditionExpression=Key("state").eq(state),
            ScanIndexForward=False,
            Limit=limit,
        )
        return response.get("Items", [])
    except ClientError as exc:
        logger.error("DynamoDB query failed for state %s: %s", state, exc)
        raise


def scan_detections(
    state: str | None = None,
    hours: int = 24,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Return detections from the last N hours, optionally filtered by state."""
    from datetime import datetime, timedelta, timezone  # noqa: PLC0415

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    if state:
        try:
            response = _table.query(
                IndexName="state-timestamp-index",
                KeyConditionExpression=Key("state").eq(state) & Key("timestamp").gte(cutoff),
                ScanIndexForward=False,
                Limit=limit,
            )
            return response.get("Items", [])
        except ClientError as exc:
            logger.error("DynamoDB query failed: %s", exc)
            raise

    try:
        response = _table.scan(
            FilterExpression="#ts >= :cutoff",
            ExpressionAttributeNames={"#ts": "timestamp"},
            ExpressionAttributeValues={":cutoff": cutoff},
            Limit=limit,
        )
        items = response.get("Items", [])
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return items[:limit]
    except ClientError as exc:
        logger.error("DynamoDB scan failed: %s", exc)
        raise


def get_stats() -> Dict[str, Any]:
    """Return aggregate statistics: total focos, unique states, top state."""
    from datetime import datetime, timedelta, timezone  # noqa: PLC0415
    from collections import Counter  # noqa: PLC0415

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    try:
        response = _table.scan(
            FilterExpression="#ts >= :cutoff AND class_name = :cls",
            ProjectionExpression="#st, confidence",
            ExpressionAttributeNames={"#ts": "timestamp", "#st": "state"},
            ExpressionAttributeValues={":cutoff": cutoff, ":cls": "foco_ativo"},
        )
        items = response.get("Items", [])
        state_counts = Counter(i.get("state", "UNKNOWN") for i in items)
        top_state = state_counts.most_common(1)[0][0] if state_counts else "N/A"

        return {
            "total_focos": len(items),
            "top_state": top_state,
            "states_affected": len(state_counts),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except ClientError as exc:
        logger.error("DynamoDB stats scan failed: %s", exc)
        raise


def get_recent_alerts(limit: int = 20) -> List[Dict[str, Any]]:
    """Return the most recent sent alerts."""
    try:
        response = _table.scan(
            FilterExpression="alert_sent = :sent",
            ExpressionAttributeValues={":sent": True},
            Limit=limit * 3,  # over-fetch then sort client-side
        )
        items = response.get("Items", [])
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return items[:limit]
    except ClientError as exc:
        logger.error("DynamoDB alerts scan failed: %s", exc)
        raise
