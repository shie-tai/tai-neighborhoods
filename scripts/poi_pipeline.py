#!/usr/bin/env python3
"""POI image pipeline for the unresolved-neighborhoods batch.

Generates the worklist, fetches Google Places reference photos, fills the
verbatim generation prompt, and finalizes generated images (center-crop to
16:9, upload straight to S3 — images are NOT committed to GitHub).

S3 key layout (mirrors the already-uploaded POIs, keyed by the CSV
``parent_id`` minus its ``neighborhoods/`` prefix):

    images/Neighborhood_POIs/<cc>-<city-slug>/<nhood-slug>/<poi-slug>.png

Subcommands:
    shard    --shard N [--limit K]   list pending neighborhoods in shard N
    fetchref "<query>" [--lat --lng] download candidate reference photos
    prompt   "<POI name>" "<destination>" [--text-only]  print the prompt
    finalize <parent_id> "<POI name>" <generated.png> --category C
             [--ref-source R --ref-attribution A]        crop+upload+log
    status   [--shard N]             progress counts (S3-backed)

Credentials: AWS_Access_Key / AWS_Secret_key and GOOGLE_PLACES_API_KEY
environment variables.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_CSV = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/"
    "unresolved_neighborhoods_for_pois_fd82.csv"
)
SOURCE_CSV = REPO_ROOT / "data" / "neighborhoods_source.csv"
MANIFEST_CSV = REPO_ROOT / "data" / "poi_unresolved_manifest.csv"
PROVENANCE_DIR = REPO_ROOT / "data" / "poi_provenance"
PROMPT_TEMPLATE = REPO_ROOT / "docs" / "poi_prompt_template.txt"
BUCKET = "image.travelai.storage"
KEY_PREFIX = "images/Neighborhood_POIs/"
NUM_SHARDS = 20
REF_DIR = Path("/tmp/poi_refs")
FINAL_WIDTH, FINAL_HEIGHT = 1536, 864  # 16:9, >= 1280 wide


def slugify(name: str) -> str:
    """Lowercase ASCII; runs of non-alphanumerics -> single hyphen."""
    text = unicodedata.normalize("NFKD", name)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def s3_client():
    import boto3

    return boto3.client(
        "s3",
        aws_access_key_id=os.environ["AWS_Access_Key"],
        aws_secret_access_key=os.environ["AWS_Secret_key"],
        region_name="us-east-1",
    )


def load_manifest() -> list[dict]:
    if not MANIFEST_CSV.exists():
        build_manifest()
    with open(MANIFEST_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_manifest() -> None:
    """Join the uploaded CSV with the source CSV (lat/lng, anchor hints)."""
    src: dict[tuple[str, str, str], dict] = {}
    with open(SOURCE_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (
                r["country_code"].strip().lower(),
                r["city"].strip().lower(),
                r["neighborhood"].strip().lower(),
            )
            src.setdefault(key, r)
    rows = []
    with open(UPLOAD_CSV, newline="", encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(f)):
            key = (
                r["country_code"].strip().lower(),
                r["city"].strip().lower(),
                r["neighborhood"].strip().lower(),
            )
            s = src.get(key, {})
            rows.append(
                {
                    "shard": f"{i % NUM_SHARDS:02d}",
                    "parent_id": r["parent_id"],
                    "s3_prefix": KEY_PREFIX
                    + r["parent_id"].removeprefix("neighborhoods/")
                    + "/",
                    "neighborhood": r["neighborhood"],
                    "city": r["city"],
                    "region": r["region"],
                    "country": r["country"],
                    "country_code": r["country_code"],
                    "destination": r["destination"],
                    "lat": s.get("lat", ""),
                    "lng": s.get("lng", ""),
                    "anchor_hint": s.get("anchor_spot", ""),
                    "why_fit": s.get("why_fit", ""),
                }
            )
    MANIFEST_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()),
                           quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)
    print(f"manifest written: {len(rows)} rows -> {MANIFEST_CSV}",
          file=sys.stderr)


def existing_counts(prefixes: list[str]) -> dict[str, int]:
    """Number of PNGs already uploaded under each neighborhood prefix."""
    s3 = s3_client()
    paginator = s3.get_paginator("list_objects_v2")
    counts: dict[str, int] = {p: 0 for p in prefixes}
    # One paginated listing of the whole POI tree is far cheaper than
    # thousands of per-prefix requests.
    for page in paginator.paginate(Bucket=BUCKET, Prefix=KEY_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            slash = key.rfind("/")
            prefix = key[: slash + 1]
            if prefix in counts:
                counts[prefix] += 1
    return counts


def flagged_ids() -> set[str]:
    """parent_ids flagged as ungeneratable in any flagged_shard_*.csv."""
    ids: set[str] = set()
    for path in PROVENANCE_DIR.glob("flagged_shard_*.csv"):
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                if row and row[0].startswith("neighborhoods/"):
                    ids.add(row[0])
    return ids


def cmd_shard(args: argparse.Namespace) -> None:
    rows = [r for r in load_manifest() if int(r["shard"]) == args.shard]
    counts = existing_counts([r["s3_prefix"] for r in rows])
    skip = flagged_ids()
    pending = [r for r in rows
               if counts[r["s3_prefix"]] < 4 and r["parent_id"] not in skip]
    done = len(rows) - len(pending)
    if args.limit:
        pending = pending[: args.limit]
    print(json.dumps(
        {
            "shard": args.shard,
            "total": len(rows),
            "done": done,
            "pending": pending,
        },
        ensure_ascii=False, indent=1,
    ))


def cmd_fetchref(args: argparse.Namespace) -> None:
    key = os.environ["GOOGLE_PLACES_API_KEY"]
    params = {"query": args.query, "key": key}
    if args.lat and args.lng:
        params["location"] = f"{args.lat},{args.lng}"
        params["radius"] = "3000"
    url = ("https://maps.googleapis.com/maps/api/place/textsearch/json?"
           + urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    if data.get("status") != "OK" or not data.get("results"):
        print(json.dumps({"status": data.get("status", "EMPTY"),
                          "candidates": []}))
        return
    REF_DIR.mkdir(parents=True, exist_ok=True)
    stem = slugify(args.query)[:60]
    top = data["results"][0]
    photo_pool: list[tuple[dict, dict]] = []
    # Legacy text search returns at most one photo per place; pull the top
    # result's full photo list from Place Details for real alternatives.
    details_url = (
        "https://maps.googleapis.com/maps/api/place/details/json?"
        + urllib.parse.urlencode(
            {"place_id": top["place_id"],
             "fields": "name,formatted_address,photos", "key": key}
        )
    )
    try:
        with urllib.request.urlopen(details_url, timeout=30) as resp:
            details = json.load(resp).get("result", {})
        for photo in details.get("photos", [])[: args.max_photos]:
            photo_pool.append((top, photo))
    except Exception:
        pass
    if not photo_pool:
        for res in data["results"][:2]:
            for photo in res.get("photos", [])[:2]:
                photo_pool.append((res, photo))
    candidates = []
    seen = 0
    for res, photo in photo_pool:
        if seen >= args.max_photos:
            break
        ref = photo["photo_reference"]
        photo_url = (
            "https://maps.googleapis.com/maps/api/place/photo?"
            + urllib.parse.urlencode(
                {"maxwidth": "1600", "photo_reference": ref, "key": key}
            )
        )
        path = REF_DIR / f"{stem}_{seen}.jpg"
        with urllib.request.urlopen(photo_url, timeout=60) as r, \
                open(path, "wb") as out:
            out.write(r.read())
        candidates.append(
            {
                "path": str(path),
                "place_name": res.get("name"),
                "address": res.get("formatted_address"),
                "photo_reference": ref,
                "attribution": "; ".join(
                    re.sub(r"<[^>]+>", "", a)
                    for a in photo.get("html_attributions", [])
                ),
                "attribution_html": "; ".join(
                    photo.get("html_attributions", [])
                ),
            }
        )
        seen += 1
    print(json.dumps({"status": "OK", "candidates": candidates},
                     ensure_ascii=False, indent=1))


def cmd_prompt(args: argparse.Namespace) -> None:
    template = PROMPT_TEMPLATE.read_text(encoding="utf-8").strip()
    text = template.replace("{POI_NAME}", args.poi_name).replace(
        "{DESTINATION}", args.destination
    )
    if args.text_only:
        # Per spec: drop only the "based on the attached reference
        # photograph" clause; keep everything else verbatim.
        text = text.replace(
            " based on the attached reference photograph of",
            " of", 1,
        )
    print(text)


def cmd_finalize(args: argparse.Namespace) -> None:
    from PIL import Image

    manifest = {r["parent_id"]: r for r in load_manifest()}
    row = manifest.get(args.parent_id)
    if row is None:
        sys.exit(f"unknown parent_id: {args.parent_id}")
    poi_slug = slugify(args.poi_name)
    if not poi_slug:
        sys.exit(f"empty slug for POI name: {args.poi_name!r}")
    key = row["s3_prefix"] + poi_slug + ".png"

    src = Path(args.image)
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if w < FINAL_WIDTH:
        sys.exit(f"image too small: {w}x{h} (need >= {FINAL_WIDTH} wide)")
    target_h = round(w * 9 / 16)
    if h < target_h:
        # Narrower than 16:9 already -> crop width instead.
        target_w = round(h * 16 / 9)
        left = (w - target_w) // 2
        im = im.crop((left, 0, left + target_w, h))
    else:
        top = (h - target_h) // 2
        im = im.crop((0, top, w, top + target_h))
    im = im.resize((FINAL_WIDTH, FINAL_HEIGHT), Image.LANCZOS)

    tmp_out = Path("/tmp/poi_out")
    tmp_out.mkdir(parents=True, exist_ok=True)
    final_path = tmp_out / (poi_slug + ".png")
    im.save(final_path, "PNG")

    s3 = s3_client()
    s3.upload_file(str(final_path), BUCKET, key,
                   ExtraArgs={"ContentType": "image/png"})

    PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)
    prov = PROVENANCE_DIR / f"shard_{row['shard']}.csv"
    is_new = not prov.exists()
    with open(prov, "a", newline="", encoding="utf-8") as f:
        w_ = csv.writer(f, quoting=csv.QUOTE_ALL)
        if is_new:
            w_.writerow(
                ["parent_id", "neighborhood", "city", "destination",
                 "poi_name", "poi_slug", "category", "s3_key",
                 "ref_photo_reference", "ref_attribution", "generated_at"]
            )
        w_.writerow(
            [args.parent_id, row["neighborhood"], row["city"],
             row["destination"], args.poi_name, poi_slug, args.category,
             key, args.ref_source or "text-only",
             args.ref_attribution or "",
             datetime.datetime.now(datetime.timezone.utc).isoformat()]
        )

    final_path.unlink()
    if args.delete_source:
        src.unlink(missing_ok=True)
    print(f"uploaded s3://{BUCKET}/{key}")


def cmd_status(args: argparse.Namespace) -> None:
    rows = load_manifest()
    if args.shard is not None:
        rows = [r for r in rows if int(r["shard"]) == args.shard]
    counts = existing_counts([r["s3_prefix"] for r in rows])
    done = sum(1 for r in rows if counts[r["s3_prefix"]] >= 4)
    partial = sum(1 for r in rows if 0 < counts[r["s3_prefix"]] < 4)
    images = sum(counts[r["s3_prefix"]] for r in rows)
    print(f"neighborhoods: {len(rows)}  complete(4/4): {done}  "
          f"partial: {partial}  images uploaded: {images}/{len(rows) * 4}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("build-manifest")
    sp.set_defaults(func=lambda a: build_manifest())

    sp = sub.add_parser("shard")
    sp.add_argument("--shard", type=int, required=True)
    sp.add_argument("--limit", type=int, default=0)
    sp.set_defaults(func=cmd_shard)

    sp = sub.add_parser("fetchref")
    sp.add_argument("query")
    sp.add_argument("--lat", default="")
    sp.add_argument("--lng", default="")
    sp.add_argument("--max-photos", type=int, default=3)
    sp.set_defaults(func=cmd_fetchref)

    sp = sub.add_parser("prompt")
    sp.add_argument("poi_name")
    sp.add_argument("destination")
    sp.add_argument("--text-only", action="store_true")
    sp.set_defaults(func=cmd_prompt)

    sp = sub.add_parser("finalize")
    sp.add_argument("parent_id")
    sp.add_argument("poi_name")
    sp.add_argument("image")
    sp.add_argument("--category", required=True,
                    choices=["anchor", "outdoors", "shopping-dining",
                             "culture-architecture"])
    sp.add_argument("--ref-source", default="")
    sp.add_argument("--ref-attribution", default="")
    sp.add_argument("--delete-source", action="store_true", default=True)
    sp.set_defaults(func=cmd_finalize)

    sp = sub.add_parser("status")
    sp.add_argument("--shard", type=int, default=None)
    sp.set_defaults(func=cmd_status)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
