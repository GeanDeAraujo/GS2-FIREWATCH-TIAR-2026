"""
Gera dataset YOLO anotado a partir de imagens MODIS + hotspots FIRMS.

Estratégia de pseudo-labeling:
  - Cada tile MODIS (256×256px, zoom 9, ~300m/px) é uma imagem de treino
  - Para cada hotspot FIRMS confirmado DENTRO do tile, cria bounding box YOLO
  - Classe 0 (foco_ativo) para hotspots com FRP > 50 MW
  - Classe 1 (fumaca) para hotspots com FRP < 50 MW (fogo menor, mais fumaça visível)
  - BBox: 40×40 pixels (~12km) — suficiente para capturar pluma de fumaça

Uso:
  AWS_BUCKET_NAME=firewatch-raw-images AWS_REGION=sa-east-1 \
  python training/build_satellite_dataset.py
"""
import csv, io, math, os, random, shutil
from datetime import date, timedelta
from pathlib import Path
from typing import List, Tuple

import boto3
import requests

BUCKET    = os.environ.get("AWS_BUCKET_NAME", "firewatch-raw-images")
REGION    = os.environ.get("AWS_REGION", "sa-east-1")
FIRMS_KEY = os.environ.get("NASA_FIRMS_API_KEY", "")

GIBS_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
LAYER     = "MODIS_Terra_CorrectedReflectance_TrueColor"
ZOOM      = 9
TILE_PX   = 256
BBOX_PX   = 40   # pixels de bounding box (~12km no zoom 9)

DEST = Path(__file__).parent / "datasets" / "firewatch_satellite"
TRAIN_R, VAL_R = 0.75, 0.15   # restante = test


# ── Conversões geo ──────────────────────────────────────────────────────────

def latlon_to_tile(lat: float, lon: float, z: int) -> Tuple[int, int]:
    n = 2 ** z
    tx = int((lon + 180) / 360 * n)
    lat_r = math.radians(lat)
    ty = int((1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n)
    return tx, ty

def tile_origin_latlon(tx: int, ty: int, z: int) -> Tuple[float, float]:
    """Retorna lat/lon do canto NW do tile."""
    n = 2 ** z
    lon = tx / n * 360 - 180
    lat_r = math.atan(math.sinh(math.pi * (1 - 2 * ty / n)))
    return math.degrees(lat_r), lon

def latlon_to_pixel(lat: float, lon: float, tx: int, ty: int, z: int) -> Tuple[float, float]:
    """Pixel offset (col, row) de um ponto dentro do tile."""
    n = 2 ** z
    # coluna
    col = ((lon + 180) / 360 * n - tx) * TILE_PX
    # linha
    lat_r = math.radians(lat)
    merc_y = math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi
    tile_top = 1 - 2 * ty / n
    row = (tile_top - merc_y) / (2 / n) * TILE_PX
    return col, row

def pixel_to_yolo(col: float, row: float, bbox: int = BBOX_PX) -> Tuple[float, float, float, float]:
    """Converte centro de pixel para formato YOLO normalizado cx,cy,w,h."""
    cx = max(0, min(1, col / TILE_PX))
    cy = max(0, min(1, row / TILE_PX))
    w  = h = bbox / TILE_PX
    return cx, cy, w, h


# ── Carrega hotspots do S3 ──────────────────────────────────────────────────

def load_hotspots(s3, tile_date: str) -> List[dict]:
    hotspots = []
    for src in ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"]:
        key = f"raw/nasa_firms/{src}/{tile_date}/hotspots.csv"
        try:
            obj = s3.get_object(Bucket=BUCKET, Key=key)
            for row in csv.DictReader(io.StringIO(obj["Body"].read().decode())):
                try:
                    hotspots.append({
                        "lat": float(row["latitude"]),
                        "lon": float(row["longitude"]),
                        "frp": float(row.get("frp") or 0),
                        "src": src,
                    })
                except (ValueError, KeyError):
                    pass
        except Exception:
            pass
    return hotspots


# ── Build ───────────────────────────────────────────────────────────────────

def build(tile_date: str = None, min_frp: float = 10.0):
    if tile_date is None:
        tile_date = (date.today() - timedelta(days=1)).isoformat()

    s3 = boto3.client("s3", region_name=REGION)
    print(f"Carregando hotspots FIRMS de {tile_date}...")
    hotspots = load_hotspots(s3, tile_date)
    print(f"  {len(hotspots)} hotspots carregados")

    if not hotspots:
        print("Nenhum hotspot — rode nasa_firms.py primeiro")
        return

    # Filtra por FRP mínimo e agrupa por tile
    hotspots = [h for h in hotspots if h["frp"] >= min_frp]
    tile_map: dict[Tuple[int,int], List[dict]] = {}
    for h in hotspots:
        tx, ty = latlon_to_tile(h["lat"], h["lon"], ZOOM)
        tile_map.setdefault((tx, ty), []).append(h)

    # Seleciona tiles com mais hotspots (mais rico para treino)
    tiles_sorted = sorted(tile_map.items(), key=lambda x: len(x[1]), reverse=True)
    selected = tiles_sorted[:120]   # máx 120 tiles únicos
    print(f"  {len(selected)} tiles únicos selecionados")

    # Recria diretórios
    for split in ["train", "val", "test"]:
        for kind in ["images", "labels"]:
            d = DEST / kind / split
            if d.exists(): shutil.rmtree(d)
            d.mkdir(parents=True)

    n = len(selected)
    n_train = int(n * TRAIN_R)
    n_val   = int(n * VAL_R)
    random.shuffle(selected)
    splits = {
        "train": selected[:n_train],
        "val":   selected[n_train:n_train+n_val],
        "test":  selected[n_train+n_val:],
    }

    session = requests.Session()
    total_ok = 0
    for split, tiles in splits.items():
        for i, ((tx, ty), spots) in enumerate(tiles):
            url = f"{GIBS_BASE}/{LAYER}/default/{tile_date}/GoogleMapsCompatible_Level9/{ZOOM}/{ty}/{tx}.jpg"
            try:
                r = session.get(url, timeout=20)
                r.raise_for_status()
            except Exception as e:
                print(f"    SKIP tile ({tx},{ty}): {e}")
                continue

            stem = f"modis_{tile_date}_{tx}_{ty}"
            img_path = DEST / "images" / split / f"{stem}.jpg"
            lbl_path = DEST / "labels" / split / f"{stem}.txt"

            img_path.write_bytes(r.content)

            with open(lbl_path, "w") as lf:
                for h in spots:
                    col, row = latlon_to_pixel(h["lat"], h["lon"], tx, ty, ZOOM)
                    # valida que ponto está dentro do tile
                    if not (0 <= col <= TILE_PX and 0 <= row <= TILE_PX):
                        continue
                    cls = 0 if h["frp"] >= 50 else 1   # foco_ativo vs fumaca
                    cx, cy, w, hh = pixel_to_yolo(col, row)
                    lf.write(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {hh:.6f}\n")

            total_ok += 1

    print(f"\n✓ {total_ok} tiles com labels salvos em {DEST}")

    # Gera data.yaml para fine-tuning
    yaml_path = Path(__file__).parent / "data_satellite.yaml"
    yaml_path.write_text(
        f"path: {DEST.resolve()}\n"
        "train: images/train\n"
        "val:   images/val\n"
        "test:  images/test\n\n"
        "nc: 3\n"
        "names:\n"
        "  0: foco_ativo\n"
        "  1: fumaca\n"
        "  2: area_queimada\n"
    )
    print(f"data_satellite.yaml: {yaml_path}")
    return total_ok


if __name__ == "__main__":
    build(tile_date="2026-06-04", min_frp=10.0)
