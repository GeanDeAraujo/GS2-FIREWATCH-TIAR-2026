"""
Baixa tiles MODIS Terra True Color do NASA GIBS centrados nos hotspots
de maior FRP (Fire Radiative Power) do NASA FIRMS.

Fluxo:
  1. Lê os CSVs de hotspots do S3 (coletados pelo nasa_firms.py)
  2. Seleciona os N focos com maior FRP (fogo mais intenso)
  3. Baixa tile RGB 512x512 do NASA GIBS para cada foco
  4. Salva no S3 com lat/lon embutido no key
     → Lambda processor detecta e roda YOLO

NASA GIBS: gratuito, sem autenticação
MODIS Terra TrueColor resolução ~250m/pixel no zoom 9
"""
import io
import csv
import math
import os
from datetime import date, timedelta
from typing import List, Tuple

import boto3
import requests

BUCKET    = os.environ.get("AWS_BUCKET_NAME", "firewatch-raw-images")
REGION    = os.environ.get("AWS_REGION", "sa-east-1")
GIBS_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
LAYER     = "MODIS_Terra_CorrectedReflectance_TrueColor"
ZOOM      = 9   # ~250m por pixel
TILE_W    = 256


def latlon_to_tile(lat: float, lon: float, zoom: int) -> Tuple[int, int]:
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_latlon(x: int, y: int, zoom: int) -> Tuple[float, float]:
    n = 2 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_r = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_r)
    return lat, lon


def load_hotspots_from_s3(s3, tile_date: str) -> List[dict]:
    hotspots = []
    sources = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"]
    for src in sources:
        key = f"raw/nasa_firms/{src}/{tile_date}/hotspots.csv"
        try:
            obj = s3.get_object(Bucket=BUCKET, Key=key)
            reader = csv.DictReader(io.StringIO(obj["Body"].read().decode()))
            for row in reader:
                try:
                    hotspots.append({
                        "lat": float(row["latitude"]),
                        "lon": float(row["longitude"]),
                        "frp": float(row["frp"]) if row.get("frp") else 0.0,
                        "source": src,
                    })
                except (ValueError, KeyError):
                    pass
            print(f"  {src}: {len([h for h in hotspots if h['source']==src])} hotspots carregados")
        except s3.exceptions.NoSuchKey:
            print(f"  {src}: CSV não encontrado (s3://{BUCKET}/{key})")
    return hotspots


def download_tile(tile_date: str, z: int, x: int, y: int) -> bytes:
    url = f"{GIBS_BASE}/{LAYER}/default/{tile_date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def upload_tile(s3, img_bytes: bytes, lat: float, lon: float,
                state: str, tile_date: str, idx: int) -> str:
    key = (f"raw/modis/{state}/{tile_date}/"
           f"lat_{lat:.4f}_lon_{lon:.4f}_frp{idx:02d}.jpg")
    s3.put_object(
        Bucket=BUCKET, Key=key,
        Body=img_bytes, ContentType="image/jpeg",
        Metadata={"lat": str(round(lat, 6)), "lon": str(round(lon, 6))},
    )
    return key


def lat_to_state(lat: float, lon: float) -> str:
    """Mapeamento simplificado de coordenadas → estado brasileiro."""
    if lat > 2:   return "RR"
    if lon < -60 and lat > -5: return "AM"
    if lon > -52 and lat > -5: return "PA"
    if lat < -15 and lon < -55: return "MT"
    if lat < -15 and lon > -55: return "GO"
    if lat < -20 and lon < -52: return "MS"
    if lat < -20: return "MG"
    return "BR"


def main(top_n: int = 15, tile_date: str = None):
    if tile_date is None:
        tile_date = (date.today() - timedelta(days=1)).isoformat()

    s3 = boto3.client("s3", region_name=REGION)
    print(f"Carregando hotspots FIRMS de {tile_date}...")
    hotspots = load_hotspots_from_s3(s3, tile_date)

    if not hotspots:
        print("Nenhum hotspot encontrado. Rode nasa_firms.py primeiro.")
        return

    # Seleciona os N com maior FRP
    top = sorted(hotspots, key=lambda h: h["frp"], reverse=True)[:top_n]
    print(f"\nBaixando {len(top)} tiles MODIS True Color do NASA GIBS...")

    uploaded = []
    session = requests.Session()
    for i, h in enumerate(top):
        lat, lon, frp = h["lat"], h["lon"], h["frp"]
        tx, ty = latlon_to_tile(lat, lon, ZOOM)
        center_lat, center_lon = tile_to_latlon(tx, ty, ZOOM)
        state = lat_to_state(lat, lon)

        try:
            img = download_tile(tile_date, ZOOM, tx, ty)
            key = upload_tile(s3, img, lat, lon, state, tile_date, i)
            print(f"  [{i+1:02d}] FRP={frp:6.1f}MW  ({lat:.2f},{lon:.2f})  {state}  → {key.split('/')[-1]}")
            uploaded.append(key)
        except Exception as e:
            print(f"  [{i+1:02d}] ERRO ({lat:.2f},{lon:.2f}): {e}")

    print(f"\n✓ {len(uploaded)} tiles enviados ao S3.")
    print("  Invoke o processor para rodar YOLO:")
    print("  aws lambda invoke --function-name firewatch-processor \\")
    print("    --region sa-east-1 --payload '{}' \\")
    print("    --cli-binary-format raw-in-base64-out /tmp/out.json")
    return uploaded


if __name__ == "__main__":
    main(top_n=15)
