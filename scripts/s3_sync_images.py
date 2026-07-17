#!/usr/bin/env python3
"""Sync images/neighborhoods_dynamic/ to the S3 bucket.

Uploads any local PNG whose key is missing from the bucket or whose size
differs. Keys mirror the repo-relative path, e.g.
images/neighborhoods_dynamic/usa/nevada/las-vegas/las-vegas-strip.png.

Credentials come from the default boto3 chain (~/.aws/credentials or
environment variables); nothing is hard-coded here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = REPO_ROOT / "images" / "neighborhoods_dynamic"
BUCKET = "image.travelai.storage"


def main() -> None:
    s3 = boto3.client("s3")
    local = sorted(IMAGES_DIR.rglob("*.png"))
    uploaded = skipped = 0
    for path in local:
        key = path.relative_to(REPO_ROOT).as_posix()
        size = path.stat().st_size
        try:
            head = s3.head_object(Bucket=BUCKET, Key=key)
            if head["ContentLength"] == size:
                skipped += 1
                continue
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in ("404", "NoSuchKey"):
                raise
        s3.upload_file(str(path), BUCKET, key,
                       ExtraArgs={"ContentType": "image/png"})
        uploaded += 1
        print(f"uploaded s3://{BUCKET}/{key} ({size // 1024} KiB)")
    print(f"done: {uploaded} uploaded, {skipped} already current, "
          f"{len(local)} local files")
    sys.exit(0)


if __name__ == "__main__":
    main()
