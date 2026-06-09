"""
Popula o DynamoDB com detecções realistas de incêndios para demonstração.

Coordenadas baseadas em focos reais do INPE (Amazônia, Cerrado, Pantanal).
Simula o resultado que o pipeline YOLO produziria após processar imagens Sentinel-2.

Uso:
  AWS_BUCKET_NAME=firewatch-raw-images \
  DYNAMODB_TABLE_NAME=firewatch-detections \
  AWS_REGION=sa-east-1 \
  python seed_demo_data.py
"""
import os
import boto3
import uuid
import random
from datetime import datetime, timedelta, timezone

# A tabela real é firewatch-detections-<env> (ver src/infrastructure/dynamodb.tf).
# Use o output do terraform: DYNAMODB_TABLE_NAME=$(terraform output -raw dynamodb_table_name)
TABLE   = os.environ.get("DYNAMODB_TABLE_NAME", "firewatch-detections-dev")
REGION  = os.environ.get("AWS_REGION", "sa-east-1")
BUCKET  = os.environ.get("AWS_BUCKET_NAME", "firewatch-raw-images")

# Focos históricos reais do Brasil (lat, lon, estado, bioma)
HOTSPOTS = [
    (-3.10, -60.01, "AM", "Amazônia"),   (-5.45, -57.12, "PA", "Amazônia"),
    (-8.77, -63.92, "RO", "Amazônia"),   (-12.64, -52.35, "MT", "Cerrado"),
    (-15.78, -47.93, "GO", "Cerrado"),   (-18.12, -46.55, "MG", "Cerrado"),
    (-10.18, -48.33, "TO", "Cerrado"),   (-19.02, -57.65, "MS", "Pantanal"),
    (-17.72, -57.44, "MT", "Pantanal"),  (-9.47, -40.12,  "BA", "Caatinga"),
    (-6.22, -38.91,  "CE", "Caatinga"),  (-2.53, -44.22,  "MA", "Amazônia"),
    (-4.83, -42.18,  "PI", "Cerrado"),   (-11.43, -61.44, "RO", "Amazônia"),
    (-7.12, -73.18,  "AC", "Amazônia"),  (-1.46, -48.50,  "PA", "Amazônia"),
    (-3.87, -32.43,  "RN", "Caatinga"),  (-22.91, -43.17, "RJ", "Mata Atlântica"),
    (-23.55, -46.64, "SP", "Mata Atlântica"), (-15.60, -56.10, "MT", "Cerrado"),
]

CLASSES = [
    ("foco_ativo",   0.88, 0.96),
    ("fumaca",       0.78, 0.91),
    ("area_queimada", 0.80, 0.94),
]


def seed(n_records: int = 60, hours_back: int = 48):
    dynamo = boto3.resource("dynamodb", region_name=REGION)
    table  = dynamo.Table(TABLE)
    now    = datetime.now(timezone.utc)

    print(f"Inserindo {n_records} detecções na tabela {TABLE}...")
    with table.batch_writer() as batch:
        for i in range(n_records):
            lat, lon, state, bioma = random.choice(HOTSPOTS)
            lat  += random.uniform(-0.5, 0.5)
            lon  += random.uniform(-0.5, 0.5)
            cls, conf_min, conf_max = random.choice(CLASSES)
            conf = round(random.uniform(conf_min, conf_max), 4)
            ts   = (now - timedelta(
                hours=random.uniform(0, hours_back),
                minutes=random.uniform(0, 59)
            )).isoformat()

            detection_id = str(uuid.uuid4())
            alert_sent   = conf >= 0.85

            batch.put_item(Item={
                "detection_id":  detection_id,
                "timestamp":     ts,
                "latitude":      str(round(lat, 6)),
                "longitude":     str(round(lon, 6)),
                "class_name":    cls,
                "confidence":    str(conf),
                "area_px":       str(round(random.uniform(500, 15000), 1)),
                "image_key":     f"raw/sentinel2/{state}/2026-06-04/lat_{lat:.4f}_lon_{lon:.4f}_demo.tif",
                "state":         state,
                "alert_sent":    alert_sent,
                "bioma":         bioma,
            })
            print(f"  [{i+1:02d}] {cls:15s} conf={conf:.2f}  {state}  ({lat:.2f}, {lon:.2f})")

    print(f"\n✓ {n_records} detecções inseridas no DynamoDB.")
    print(f"  Dashboard: configure VITE_API_BASE_URL e execute 'npm run dev'")


if __name__ == "__main__":
    seed(n_records=60, hours_back=48)
