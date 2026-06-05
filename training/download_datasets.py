"""
Dataset downloader for FireWatch YOLO training.

Downloads and organizes public fire detection datasets into YOLO format.
Requires: pip install roboflow requests

Usage:
  python download_datasets.py --source dfire
  python download_datasets.py --source roboflow --rf-key YOUR_API_KEY
"""
import argparse
import os
import shutil
import zipfile
from pathlib import Path

import requests


DATASETS_DIR = Path(__file__).parent / "datasets" / "firewatch"


def download_dfire():
    """
    Download D-Fire dataset (fire + smoke, pre-annotated in YOLO format).
    Source: https://github.com/gaiasd/DFireDataset
    ~21K images, classes: fire, smoke → remap to foco_ativo=0, fumaca=1
    """
    print("Downloading D-Fire dataset...")
    url = "https://github.com/gaiasd/DFireDataset/archive/refs/heads/main.zip"
    zip_path = DATASETS_DIR / "dfire.zip"

    _download_file(url, zip_path)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(DATASETS_DIR / "dfire_raw")

    print("D-Fire downloaded. Run remap_dfire_labels() to convert class IDs.")
    zip_path.unlink()


def remap_dfire_labels(dfire_dir: Path = DATASETS_DIR / "dfire_raw"):
    """
    D-Fire uses: 0=fire, 1=smoke
    FireWatch uses: 0=foco_ativo, 1=fumaca, 2=area_queimada
    These are already aligned — just copy files.
    """
    for split in ["train", "valid", "test"]:
        src_img = dfire_dir / "DFireDataset-main" / split / "images"
        src_lbl = dfire_dir / "DFireDataset-main" / split / "labels"
        dst_split = "val" if split == "valid" else split

        if src_img.exists():
            shutil.copytree(src_img, DATASETS_DIR / "images" / dst_split, dirs_exist_ok=True)
        if src_lbl.exists():
            shutil.copytree(src_lbl, DATASETS_DIR / "labels" / dst_split, dirs_exist_ok=True)

    print("D-Fire labels remapped and copied to datasets/firewatch/")


def download_roboflow(api_key: str, workspace: str, project: str, version: int = 1):
    """
    Download a Roboflow dataset in YOLO format.
    Find fire datasets at: https://universe.roboflow.com/search?q=fire+smoke+forest
    """
    from roboflow import Roboflow  # type: ignore

    rf = Roboflow(api_key=api_key)
    proj = rf.workspace(workspace).project(project)
    dataset = proj.version(version).download("yolov8", location=str(DATASETS_DIR / "roboflow_raw"))
    print(f"Roboflow dataset downloaded to {dataset.location}")


def _download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  {pct:.1f}%", end="", flush=True)
    print()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=["dfire", "roboflow"], required=True)
    p.add_argument("--rf-key", help="Roboflow API key (for --source roboflow)")
    p.add_argument("--rf-workspace", default="", help="Roboflow workspace slug")
    p.add_argument("--rf-project", default="", help="Roboflow project slug")
    p.add_argument("--rf-version", type=int, default=1)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.source == "dfire":
        download_dfire()
        remap_dfire_labels()

    elif args.source == "roboflow":
        if not args.rf_key:
            raise SystemExit("--rf-key is required for Roboflow download")
        download_roboflow(args.rf_key, args.rf_workspace, args.rf_project, args.rf_version)
