"""An S3 data store for the fractals"""

import os
from pathlib import Path

import boto3
from botocore.client import Config

DATA_BUCKET_NAME = os.environ["FRACTALS_BUCKET"]
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", None)


def _get_s3_bucket():
    """Get the Boto3 Bucket object to upload fractals"""
    # minio requires special config:
    print(f"S3 Endpoint: {MINIO_ENDPOINT}")
    config = Config(signature_version="s3v4") if MINIO_ENDPOINT else None
    auth = "minioadmin" if MINIO_ENDPOINT else None
    s3 = boto3.resource(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        config=config,
        aws_access_key_id=auth,
        aws_secret_access_key=auth,
    )
    return s3.Bucket(DATA_BUCKET_NAME)


def upload_to_bucket(filepath, key_prefix: str = "fractals/") -> str:
    """Upload a fractal to a bucket"""
    filepath = Path(filepath)
    bucket = _get_s3_bucket()
    print(f"uploading {filepath} to {bucket}...")
    dest = key_prefix + filepath.name
    bucket.upload_file(str(filepath), dest)
    return dest
