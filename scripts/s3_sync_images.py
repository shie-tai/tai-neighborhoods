#!/usr/bin/env python3
"""Upload local finalized PNGs to S3, record them, then delete them locally.

S3 is the system of record for generated images; the git repo only tracks
data/done_slugs.txt (one slug per line) so it stays lightweight. Keys mirror
the old repo-relative path, e.g.
images/neighborhood_backfill/usa/nevada/las-vegas/las-vegas-strip.png.

Credentials come from the default boto3 chain (~/.aws/credentials or
environment variables); nothing is hard-coded here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIRS = [
    REPO_ROOT / "images" / "neighborhoods_dynamic",
    REPO_ROOT / "images" / "neighborhood_backfill",
]
BUCKET = "image.travelai.storage"
DONE_SLUGS_FILE = REPO_ROOT / "data" / "done_slugs.txt"


def main() -> None:
    s3 = boto3.client("s3")
    local = sorted(p for d in IMAGES_DIRS if d.exists()
                   for p in d.rglob("*.png"))
    done: set[str] = set()
    if DONE_SLUGS_FILE.exists():
        done = {line.strip() for line in
                DONE_SLUGS_FILE.read_text().splitlines() if line.strip()}
    uploaded = 0
    for path in local:
        key = path.relative_to(REPO_ROOT).as_posix()
        size = path.stat().st_size
        try:
            head = s3.head_object(Bucket=BUCKET, Key=key)
            already = head["ContentLength"] == size
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in ("404", "NoSuchKey"):
                raise
            already = False
        if not already:
            s3.upload_file(str(path), BUCKET, key,
                           ExtraArgs={"ContentType": "image/png"})
            uploaded += 1
            print(f"uploaded s3://{BUCKET}/{key} ({size // 1024} KiB)")
        slug = key.split("/", 2)[2].rsplit(".", 1)[0]
        done.add(slug)
        path.unlink()
    for d in IMAGES_DIRS:
        if d.exists():
            for sub in sorted(d.rglob("*"), reverse=True):
                if sub.is_dir() and not any(sub.iterdir()):
                    sub.rmdir()
    DONE_SLUGS_FILE.write_text("\n".join(sorted(done)) + "\n")
    print(f"done: {uploaded} uploaded, {len(local)} local files synced+removed, "
          f"{len(done)} slugs tracked")
    sys.exit(0)


if __name__ == "__main__":
    main()
