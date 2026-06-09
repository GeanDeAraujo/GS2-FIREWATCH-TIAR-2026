"""
FireWatch YOLO v8 training script.

Before running:
  1. Populate datasets/firewatch/images/{train,val,test}/ with images
  2. Populate datasets/firewatch/labels/{train,val,test}/ with YOLO .txt annotations
  3. pip install -r requirements.txt

Label format (YOLO): <class_id> <cx> <cy> <w> <h>  (all values 0-1, relative)
  class 0 = foco_ativo
  class 1 = fumaca
  class 2 = area_queimada

Recommended datasets to download first (see download_datasets.py):
  - D-Fire: https://github.com/gaiasd/DFireDataset
  - FLAME: https://www.kaggle.com/datasets/phylake1337/fire-dataset
  - Roboflow Universe: search "fire smoke forest"
"""
import os
import argparse
import boto3
from pathlib import Path
from ultralytics import YOLO


def parse_args():
    p = argparse.ArgumentParser(description="Train FireWatch YOLO v8 model")
    p.add_argument("--base-model", default="yolov8n.pt",
                   help="Base YOLO model: yolov8n.pt (default, used by FireWatch) or yolov8s.pt (larger)")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--device", default="cpu",
                   help="'cpu', '0' for GPU 0, '0,1' for multi-GPU")
    p.add_argument("--upload-s3", action="store_true",
                   help="Upload best weights to S3 after training")
    p.add_argument("--s3-bucket", default=os.environ.get("AWS_BUCKET_NAME", ""),
                   help="S3 bucket name (reads AWS_BUCKET_NAME env var by default)")
    return p.parse_args()


def train(args):
    data_yaml = Path(__file__).parent / "data.yaml"
    if not data_yaml.exists():
        raise FileNotFoundError("data.yaml not found. Run from the training/ directory.")

    model = YOLO(args.base_model)

    results = model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        name="firewatch_v1",
        project="runs/train",
        patience=15,
        save=True,
        plots=True,
    )

    best_weights = Path("runs/train/firewatch_v1/weights/best.pt")
    print(f"\nTraining complete. Best weights: {best_weights}")
    map50 = results.results_dict.get("metrics/mAP50(B)")
    print(f"mAP50: {map50:.4f}" if isinstance(map50, (int, float)) else "mAP50: N/A")

    if args.upload_s3 and best_weights.exists():
        _upload_to_s3(best_weights, args.s3_bucket)

    return best_weights


def _upload_to_s3(weights_path: Path, bucket: str) -> None:
    if not bucket:
        print("WARNING: --s3-bucket not set, skipping S3 upload")
        return

    s3_key = "models/firewatch_yolov8.pt"
    print(f"\nUploading {weights_path} → s3://{bucket}/{s3_key}")
    s3 = boto3.client("s3")
    s3.upload_file(str(weights_path), bucket, s3_key)
    print(f"Model uploaded. Set YOLO_MODEL_S3_KEY={s3_key} in your .env")


if __name__ == "__main__":
    args = parse_args()
    train(args)
