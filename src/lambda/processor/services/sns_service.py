"""SNS service — publish fire alerts to subscribers."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION, SEVERITY_THRESHOLDS, SNS_TOPIC_ARN

logger = logging.getLogger(__name__)

# ── TODO: set SNS_TOPIC_ARN in .env / Lambda environment variables ────────────
_sns = boto3.client("sns", region_name=AWS_REGION)


def _classify_severity(confidence: float) -> str:
    if confidence >= SEVERITY_THRESHOLDS["high"]:
        return "ALTA"
    if confidence >= SEVERITY_THRESHOLDS["medium"]:
        return "MEDIA"
    return "BAIXA"


def publish_alert(
    detection_id: str,
    class_name: str,
    confidence: float,
    latitude: float,
    longitude: float,
    state: str,
    image_key: str,
    extra: Dict[str, Any] | None = None,
) -> str:
    """Publish a fire alert to the SNS topic. Returns the SNS MessageId."""
    severity = _classify_severity(confidence)

    payload = {
        "detection_id": detection_id,
        "severity": severity,
        "type": class_name,
        "confidence": round(confidence, 4),
        "location": {"lat": latitude, "lon": longitude, "state": state},
        "image_key": image_key,
    }
    if extra:
        payload.update(extra)

    # SNS exige Subject ASCII (sem acentos/traços longos), até 100 chars e sem
    # quebras de linha — por isso usamos hífen comum em vez de em-dash.
    subject = f"[FireWatch] {severity} - {class_name.upper()} detectado em {state}"[:100]
    message = json.dumps(payload, ensure_ascii=False)

    try:
        response = _sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message,
            MessageAttributes={
                "severity": {"DataType": "String", "StringValue": severity},
                "class_name": {"DataType": "String", "StringValue": class_name},
                "state": {"DataType": "String", "StringValue": state},
            },
        )
        message_id = response["MessageId"]
        logger.info("Alert published: %s (MessageId=%s)", subject, message_id)
        return message_id
    except ClientError as exc:
        logger.error("SNS publish failed: %s", exc)
        raise
