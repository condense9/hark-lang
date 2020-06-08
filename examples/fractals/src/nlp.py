import os
import gzip
import boto3
from botocore.client import Config


def _get_s3_bucket():
    endpoint = os.getenv("MINIO_ENDPOINT", None)
    config = Config(signature_version="s3v4") if endpoint else None
    auth = "minioadmin" if endpoint else None
    s3 = boto3.resource(
        "s3",
        endpoint_url=endpoint,
        config=config,
        aws_access_key_id=auth,
        aws_secret_access_key=auth,
    )
    name = os.environ["S3_BUCKET"]
    return s3.Bucket(name)


def extract_archive(key, dest_key):
    """Extract the .GZ file"""
    bucket = _get_s3_bucket()
    archive = bucket.Object(key)
    dest = bucket.Object(dest_key)
    with gzip.open(archive.get()["Body"]) as f:
        dest.put(Body=f)


# https://kokes.github.io/blog/2018/07/26/s3-objects-streaming-python.html
# TODO use https://github.com/RaRe-Technologies/smart_open


def extract_pages(key):
    """Extract pages from the abstract archive"""
    bucket = _get_s3_bucket()
    # ObjectSummary: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#objectsummary
    archive = bucket.Object(key)
    # get: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Object.get
    body = archive.get()["Body"]


def process_page(page_name):
    """Process a single page"""
    pass


def aggregate(page_name):
    """Join all results together"""
    pass


if __name__ == "__main__":
    # extract_pages("enwiki-latest-abstract.xml.gz")
    extract_archive("enwiki-latest-abstract.xml.gz", "data.xml")
