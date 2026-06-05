"""S3 service — download raw satellite images and upload processed results."""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import List

import boto3
from botocore.exceptions import ClientError

from config import AWS_BUCKET_NAME, AWS_REGION

logger = logging.getLogger(__name__)

# ── TODO: set AWS_BUCKET_NAME in .env / Lambda environment variables ──────────
_s3 = boto3.client("s3", region_name=AWS_REGION)


def list_new_images(prefix: str = "raw/", since_key: str | None = None) -> List[str]:
    """Return S3 object keys under *prefix* that haven't been processed yet."""
    paginator = _s3.get_paginator("list_objects_v2")
    keys: List[str] = []

    for page in paginator.paginate(Bucket=AWS_BUCKET_NAME, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith((".tif", ".tiff", ".png", ".jpg", ".jpeg")):
                keys.append(key)

    return keys


def download_image(s3_key: str, local_dir: str | None = None) -> str:
    """Download an image from S3 and return the local file path."""
    if local_dir is None:
        local_dir = tempfile.mkdtemp()

    local_path = os.path.join(local_dir, Path(s3_key).name)
    try:
        _s3.download_file(AWS_BUCKET_NAME, s3_key, local_path)
        logger.info("Downloaded s3://%s/%s → %s", AWS_BUCKET_NAME, s3_key, local_path)
    except ClientError as exc:
        logger.error("Failed to download %s: %s", s3_key, exc)
        raise

    return local_path


def upload_result(local_path: str, s3_key: str) -> str:
    """Upload a processed file to S3 and return its key."""
    try:
        _s3.upload_file(local_path, AWS_BUCKET_NAME, s3_key)
        logger.info("Uploaded %s → s3://%s/%s", local_path, AWS_BUCKET_NAME, s3_key)
    except ClientError as exc:
        logger.error("Failed to upload to %s: %s", s3_key, exc)
        raise

    return s3_key
