"""AWS Lambda entry point for FireWatch fire detection processor — pipeline híbrido.

Pipeline:
  - Arquivos CSV (raw/nasa_firms/*, raw/inpe/*): hotspots confirmados por satélite
    → inseridos direto no DynamoDB (sem YOLO, já validados pela NASA/INPE)
  - Arquivos de imagem (*.tif, *.jpg, *.png): processados com YOLO v8
    → detecções salvas no DynamoDB
"""
from __future__ import annotations

import csv
import io
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3

from config import AWS_BUCKET_NAME, AWS_REGION, YOLO_CONFIDENCE_THRESHOLD
from detector import FireDetector
from services.dynamodb_service import mark_alert_sent, save_detection
from services.s3_service import download_image, list_new_images
from services.sns_service import publish_alert

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_detector   = FireDetector()
_s3_client  = boto3.client("s3", region_name=AWS_REGION)

_VALID_STATES = {
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
    "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO",
}

# Limiar FRP (Fire Radiative Power) para classificar severidade via FIRMS
_FRP_HIGH   = 200.0   # MW — foco_ativo ALTA
_FRP_MEDIUM =  50.0   # MW — foco_ativo MEDIA
_FIRMS_CONF =  0.90   # confiança padrão para hotspots FIRMS confirmados


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info("FireWatch processor started | event_type=%s", event.get("source", "s3"))

    with tempfile.TemporaryDirectory() as tmp_dir:
        if "Records" in event:
            all_keys   = [r["s3"]["object"]["key"] for r in event.get("Records", [])
                          if r.get("eventSource") == "aws:s3"]
            csv_keys   = [k for k in all_keys if k.endswith(".csv")]
            image_keys = [k for k in all_keys if k.endswith((".tif",".tiff",".png",".jpg",".jpeg"))]
        else:
            csv_keys   = _list_s3_keys(prefix="raw/", suffixes=(".csv",))
            image_keys = list_new_images(prefix="raw/")

        firms_added = _process_firms_csvs(csv_keys)
        yolo_det, alerts_sent = _process_images(image_keys, tmp_dir)

    summary = {
        "firms_hotspots_added": firms_added,
        "images_processed": yolo_det,
        "alerts_sent": alerts_sent,
    }
    logger.info("Run complete: %s", summary)
    return {"statusCode": 200, "body": summary}


# ── Pipeline 1: FIRMS CSV → DynamoDB direto ──────────────────────────────────

def _process_firms_csvs(csv_keys: List[str]) -> int:
    """Converte hotspots FIRMS confirmados por satélite em detecções no DynamoDB."""
    total = 0
    for s3_key in csv_keys:
        if "nasa_firms" not in s3_key and "inpe" not in s3_key:
            continue
        try:
            obj    = _s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=s3_key)
            reader = csv.DictReader(io.StringIO(obj["Body"].read().decode()))
            fonte  = "NASA FIRMS" if "nasa_firms" in s3_key else "IBAMA/FIRMS"

            for row in reader:
                try:
                    lat = float(row["latitude"])
                    lon = float(row["longitude"])
                    frp = float(row.get("frp") or 0)
                    conf = min(0.99, _FIRMS_CONF + frp / 10000)

                    if frp >= _FRP_HIGH:
                        cls, sev = "foco_ativo", "ALTA"
                    elif frp >= _FRP_MEDIUM:
                        cls, sev = "foco_ativo", "MEDIA"
                    else:
                        cls, sev = "fumaca",     "BAIXA"

                    state = _lat_lon_to_state(lat, lon)

                    detection_id, ts = save_detection(
                        latitude=lat, longitude=lon,
                        class_name=cls, confidence=conf,
                        area_px=frp * 100,
                        image_key=s3_key, state=state,
                        extra={"fonte": fonte, "frp": str(frp), "severity": sev},
                    )

                    if conf >= YOLO_CONFIDENCE_THRESHOLD and frp >= _FRP_MEDIUM:
                        publish_alert(
                            detection_id=detection_id, class_name=cls,
                            confidence=conf, latitude=lat, longitude=lon,
                            state=state, image_key=s3_key,
                        )
                        mark_alert_sent(detection_id, ts)

                    total += 1
                    if total % 100 == 0:
                        logger.info("FIRMS: %d hotspots inseridos...", total)

                except (ValueError, KeyError):
                    pass

            logger.info("FIRMS CSV %s: %d hotspots processados", s3_key, total)
        except Exception as exc:
            logger.error("Erro no CSV %s: %s", s3_key, exc)

    return total


# ── Pipeline 2: Imagens → YOLO → DynamoDB ────────────────────────────────────

def _process_images(image_keys: List[str], tmp_dir: str) -> Tuple[int, int]:
    """Processa imagens com YOLO v8 e salva detecções no DynamoDB."""
    processed   = 0
    alerts_sent = 0

    for s3_key in image_keys:
        try:
            lat, lon = _get_coordinates(s3_key)
            state    = _extract_state_from_key(s3_key)

            local_path = download_image(s3_key, local_dir=tmp_dir)
            detections = _detector.detect(local_path)

            for det in detections:
                detection_id, ts = save_detection(
                    latitude=lat, longitude=lon,
                    class_name=det.class_name, confidence=det.confidence,
                    area_px=det.area_px, image_key=s3_key, state=state,
                    extra={"fonte": "YOLO v8n"},
                )

                if det.confidence >= YOLO_CONFIDENCE_THRESHOLD:
                    publish_alert(
                        detection_id=detection_id, class_name=det.class_name,
                        confidence=det.confidence, latitude=lat, longitude=lon,
                        state=state, image_key=s3_key,
                    )
                    mark_alert_sent(detection_id, ts)
                    alerts_sent += 1

            processed += 1
            logger.info("YOLO %s — %d detections", s3_key, len(detections))

        except Exception as exc:
            logger.error("Erro na imagem %s: %s", s3_key, exc)

    return processed, alerts_sent


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_coordinates(s3_key: str) -> Tuple[float, float]:
    try:
        head = _s3_client.head_object(Bucket=AWS_BUCKET_NAME, Key=s3_key)
        meta = head.get("Metadata", {})
        if "lat" in meta and "lon" in meta:
            return float(meta["lat"]), float(meta["lon"])
    except Exception:
        pass
    lat, lon = _parse_coords_from_key(s3_key)
    return (lat, lon) if lat is not None else (-14.235, -51.925)


def _parse_coords_from_key(s3_key: str) -> Tuple[Optional[float], Optional[float]]:
    import re
    m = re.search(r"lat_(-?\d+\.?\d*)_lon_(-?\d+\.?\d*)", s3_key)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def _extract_state_from_key(s3_key: str) -> str:
    parts = s3_key.split("/")
    if len(parts) >= 3 and parts[2].upper() in _VALID_STATES:
        return parts[2].upper()
    return "UNKNOWN"


def _list_s3_keys(prefix: str, suffixes: tuple) -> List[str]:
    """Lista chaves S3 com os sufixos dados."""
    paginator = _s3_client.get_paginator("list_objects_v2")
    keys: List[str] = []
    for page in paginator.paginate(Bucket=AWS_BUCKET_NAME, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(suffixes):
                keys.append(obj["Key"])
    return keys


def _lat_lon_to_state(lat: float, lon: float) -> str:
    if lat > 2:   return "RR"
    if lon < -60 and lat > -5: return "AM"
    if lon > -52 and lat > -2: return "AP"
    if lon > -50 and lat > -6: return "PA"
    if lat > -6  and lon > -45: return "MA"
    if lat < -15 and lon < -55: return "MT"
    if lat < -19 and lon < -52: return "MS"
    if lat < -28: return "RS"
    if lat < -23 and lon > -50: return "PR"
    return "BR"
