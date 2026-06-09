"""DynamoDB service — persist fire detection records."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from config import AWS_REGION, DYNAMODB_TABLE_NAME

logger = logging.getLogger(__name__)

# Records expire (DynamoDB TTL on "expires_at") this many days after insertion.
_TTL_DAYS = 90

# Teto de páginas (cada ≤ 1MB) por scan, para limitar RCU/latência em hot paths.
# Cobre a tabela inteira no volume da POC; evita varredura ilimitada se crescer.
_MAX_SCAN_PAGES = 20

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
    detection_id: str | None = None,
    timestamp: str | None = None,
    idempotent: bool = False,
) -> tuple:
    """Persist a single detection to DynamoDB. Returns (detection_id, timestamp, created).

    Pass deterministic ``detection_id``/``timestamp`` (e.g. derived from a
    satellite hotspot's coordinates + acquisition time) together with
    ``idempotent=True`` to make re-runs safe: the put becomes conditional on the
    key not already existing, so the scheduled re-processing of the same hotspot
    is a no-op instead of inserting a duplicate (and ``created=False`` lets the
    caller skip re-sending its alert). When omitted, a random UUID and the
    current time are used (YOLO image detections) and ``created`` is always True.
    """
    detection_id = detection_id or str(uuid.uuid4())
    now = timestamp or datetime.now(timezone.utc).isoformat()
    expires_at = int(
        (datetime.now(timezone.utc) + timedelta(days=_TTL_DAYS)).timestamp()
    )

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
        "expires_at": expires_at,
    }
    if extra:
        item.update(extra)

    put_kwargs: Dict[str, Any] = {"Item": item}
    if idempotent:
        put_kwargs["ConditionExpression"] = "attribute_not_exists(detection_id)"

    try:
        _table.put_item(**put_kwargs)
        logger.info("Saved detection %s (%s, conf=%.2f)", detection_id, class_name, confidence)
    except ClientError as exc:
        if idempotent and exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # Hotspot já registrado em ciclo anterior — idempotente, ignora.
            return detection_id, now, False
        logger.error("DynamoDB put_item failed: %s", exc)
        raise

    return detection_id, now, True


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


def _scan_all(max_pages: int = _MAX_SCAN_PAGES, **scan_kwargs) -> List[Dict[str, Any]]:
    """Scan paginado do DynamoDB, com teto de páginas para limitar custo/latência.

    DynamoDB aplica o ``Limit`` ao número de itens *avaliados* por página, antes
    do ``FilterExpression`` — então um único scan com Limit pode devolver bem
    menos itens do que existem. Aqui acumulamos páginas (cada uma ≤ 1MB) e
    deixamos a ordenação + truncamento para o chamador.

    ``max_pages`` limita o pior caso de RCU/latência em hot paths (a Lambda de API
    tem timeout de 30s): numa tabela enorme paramos cedo em vez de varrer tudo.
    Para o volume desta POC o teto cobre a tabela inteira; em produção o ideal é
    um GSI/agregação dedicada em vez de scan.
    """
    items: List[Dict[str, Any]] = []
    pages = 0
    while True:
        response = _table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        pages += 1
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return items
        if pages >= max_pages:
            logger.warning(
                "_scan_all atingiu o teto de %d páginas; resultado parcial (%d itens)",
                max_pages, len(items),
            )
            return items
        scan_kwargs["ExclusiveStartKey"] = last_key


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
        items = _scan_all(
            FilterExpression="#ts >= :cutoff",
            ExpressionAttributeNames={"#ts": "timestamp"},
            ExpressionAttributeValues={":cutoff": cutoff},
        )
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
        items = _scan_all(
            FilterExpression="#ts >= :cutoff AND class_name = :cls",
            ProjectionExpression="#st, confidence",
            ExpressionAttributeNames={"#ts": "timestamp", "#st": "state"},
            ExpressionAttributeValues={":cutoff": cutoff, ":cls": "foco_ativo"},
        )
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
        items = _scan_all(
            FilterExpression="alert_sent = :sent",
            ExpressionAttributeValues={":sent": True},
        )
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return items[:limit]
    except ClientError as exc:
        logger.error("DynamoDB alerts scan failed: %s", exc)
        raise
