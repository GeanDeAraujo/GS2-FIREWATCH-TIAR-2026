import os

AWS_REGION = os.environ.get("AWS_REGION", "sa-east-1")
AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "")
DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
YOLO_MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", "/tmp/firewatch_yolov8.pt")
YOLO_MODEL_S3_KEY = os.environ.get("YOLO_MODEL_S3_KEY", "models/firewatch_yolov8.pt")
YOLO_CONFIDENCE_THRESHOLD = float(os.environ.get("YOLO_CONFIDENCE_THRESHOLD", "0.75"))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

DETECTION_CLASSES = {
    0: "foco_ativo",
    1: "fumaca",
    2: "area_queimada",
}

SEVERITY_THRESHOLDS = {
    "low": 0.75,
    "medium": 0.85,
    "high": 0.92,
}
