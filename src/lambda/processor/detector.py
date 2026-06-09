"""YOLO v8 wrapper for fire/smoke/burned-area detection."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from config import DETECTION_CLASSES, YOLO_CONFIDENCE_THRESHOLD, YOLO_MODEL_PATH

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: list  # [x1, y1, x2, y2] normalized 0-1
    area_px: float = 0.0
    extra: dict = field(default_factory=dict)


class FireDetector:
    def __init__(self, model_path: str = YOLO_MODEL_PATH):
        self.model_path = model_path
        self.confidence_threshold = YOLO_CONFIDENCE_THRESHOLD
        self._model = None

    def _load_model(self):
        """Lazy-load YOLO model. Downloads from S3 to /tmp if not present locally."""
        if self._model is None:
            if not os.path.exists(self.model_path):
                self._download_model_from_s3()
            try:
                from ultralytics import YOLO  # noqa: PLC0415
                self._model = YOLO(self.model_path)
                logger.info("YOLO model loaded from %s", self.model_path)
            except Exception as exc:
                logger.error("Failed to load YOLO model: %s", exc)
                raise

    def _download_model_from_s3(self) -> None:
        """Download the model weights from S3 on first cold start."""
        import boto3  # noqa: PLC0415
        from config import AWS_BUCKET_NAME, AWS_REGION, YOLO_MODEL_S3_KEY  # noqa: PLC0415

        logger.info("Downloading model s3://%s/%s → %s", AWS_BUCKET_NAME, YOLO_MODEL_S3_KEY, self.model_path)
        s3 = boto3.client("s3", region_name=AWS_REGION)
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        s3.download_file(AWS_BUCKET_NAME, YOLO_MODEL_S3_KEY, self.model_path)
        logger.info("Model downloaded successfully")

    def detect(self, image_path: str) -> List[Detection]:
        """Run inference on a single image and return detections above threshold."""
        self._load_model()
        results = self._model.predict(
            source=image_path,
            conf=self.confidence_threshold,
            save=False,
            verbose=False,
        )

        detections: List[Detection] = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                xyxyn = box.xyxyn[0].tolist()
                x1, y1, x2, y2 = xyxyn
                area_px = (x2 - x1) * (y2 - y1) * result.orig_shape[0] * result.orig_shape[1]

                detections.append(Detection(
                    class_id=class_id,
                    class_name=DETECTION_CLASSES.get(class_id, "unknown"),
                    confidence=confidence,
                    bbox=xyxyn,
                    area_px=area_px,
                ))

        logger.info("Found %d detections in %s", len(detections), Path(image_path).name)
        return detections
