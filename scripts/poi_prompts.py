#!/usr/bin/env python3
"""Prompt-only pipeline for the remaining unresolved-neighborhood POIs.

Instead of generating images, workers select the 4 POIs per neighborhood and
write the filled verbatim generation prompt to per-shard CSVs committed to
git (no S3 writes). Image generation happens later from these CSVs.

Output files: data/poi_prompts/shard_NN.csv with one row per POI prompt.

Subcommands:
    pending --shard N [--limit K]   neighborhoods still needing prompts
    verify  "<query>" [--lat --lng] Places textsearch (no photo download)
    add     <parent_id> "<POI name>" --category C [--place-id --address]
                                    fill template + append prompt row
    status  [--shard N]             prompt-progress counts

A neighborhood needs prompts when (images already on S3) + (prompt rows
written) < 4 and it is not flagged ungeneratable.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from poi_pipeline import (  # noqa: E402
    KEY_PREFIX,
    PROMPT_TEMPLATE,
    REPO_ROOT,
    flagged_ids,
    load_manifest,
    s3_client,
    slugify,
)

PROMPTS_DIR = REPO_ROOT / "data" / "poi_prompts"
BUCKET = "image.travelai.storage"
FIELDS = [
    "parent_id", "neighborhood", "city", "destination", "poi_name",
    "poi_slug", "category", "place_id", "place_address", "prompt",
    "created_at",
]


def existing_slugs() -> dict[str, list[str]]:
    """poi slugs already uploaded to S3, grouped by neighborhood prefix."""
    s3 = s3_client()
    paginator = s3.get_paginator("list_objects_v2")
    out: dict[str, list[str]] = {}
    for page in paginator.paginate(Bucket=BUCKET, Prefix=KEY_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            slash = key.rfind("/")
            prefix = key[: slash + 1]
            slug = key[slash + 1:].removesuffix(".png")
            out.setdefault(prefix, []).append(slug)
    return out


def prompt_rows(shard: int | None = None) -> list[dict]:
    rows: list[dict] = []
    paths = (
        [PROMPTS_DIR / f"shard_{shard:02d}.csv"]
        if shard is not None
        else sorted(PROMPTS_DIR.glob("shard_*.csv"))
    )
    for path in paths:
        if path.exists():
            with open(path, newline="", encoding="utf-8") as f:
                rows.extend(csv.DictReader(f))
    return rows


def cmd_pending(args: argparse.Namespace) -> None:
    rows = [r for r in load_manifest() if int(r["shard"]) == args.shard]
    uploaded = existing_slugs()
    skip = flagged_ids()
    prompted: dict[str, list[dict]] = {}
    for pr in prompt_rows(args.shard):
        prompted.setdefault(pr["parent_id"], []).append(
            {"poi_name": pr["poi_name"], "poi_slug": pr["poi_slug"],
             "category": pr["category"]}
        )
    pending = []
    done = 0
    for r in rows:
        if r["parent_id"] in skip:
            done += 1
            continue
        have_imgs = uploaded.get(r["s3_prefix"], [])
        have_prompts = prompted.get(r["parent_id"], [])
        need = 4 - len(have_imgs) - len(have_prompts)
        if need <= 0:
            done += 1
            continue
        entry = dict(r)
        entry["need"] = need
        entry["uploaded_slugs"] = have_imgs
        entry["prompted_pois"] = have_prompts
        pending.append(entry)
    if args.limit:
        pending = pending[: args.limit]
    print(json.dumps(
        {"shard": args.shard, "total": len(rows), "done_or_flagged": done,
         "pending": pending},
        ensure_ascii=False, indent=1,
    ))


def cmd_verify(args: argparse.Namespace) -> None:
    key = os.environ["GOOGLE_PLACES_API_KEY"]
    params = {"query": args.query, "key": key}
    if args.lat and args.lng:
        params["location"] = f"{args.lat},{args.lng}"
        params["radius"] = "3000"
    url = ("https://maps.googleapis.com/maps/api/place/textsearch/json?"
           + urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    results = [
        {
            "name": r.get("name"),
            "address": r.get("formatted_address"),
            "place_id": r.get("place_id"),
            "types": r.get("types", []),
            "location": r.get("geometry", {}).get("location", {}),
        }
        for r in data.get("results", [])[:3]
    ]
    print(json.dumps({"status": data.get("status"), "results": results},
                     ensure_ascii=False, indent=1))


def cmd_add(args: argparse.Namespace) -> None:
    manifest = {r["parent_id"]: r for r in load_manifest()}
    row = manifest.get(args.parent_id)
    if row is None:
        sys.exit(f"unknown parent_id: {args.parent_id}")
    poi_slug = slugify(args.poi_name)
    if not poi_slug:
        sys.exit(f"empty slug for POI name: {args.poi_name!r}")

    template = PROMPT_TEMPLATE.read_text(encoding="utf-8").strip()
    prompt = template.replace("{POI_NAME}", args.poi_name).replace(
        "{DESTINATION}", row["destination"]
    )

    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    path = PROMPTS_DIR / f"shard_{int(row['shard']):02d}.csv"
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            for existing in csv.DictReader(f):
                if (existing["parent_id"] == args.parent_id
                        and existing["poi_slug"] == poi_slug):
                    print(f"already prompted: {args.parent_id} / {poi_slug}")
                    return
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
        if is_new:
            w.writeheader()
        w.writerow(
            {
                "parent_id": args.parent_id,
                "neighborhood": row["neighborhood"],
                "city": row["city"],
                "destination": row["destination"],
                "poi_name": args.poi_name,
                "poi_slug": poi_slug,
                "category": args.category,
                "place_id": args.place_id,
                "place_address": args.address,
                "prompt": prompt,
                "created_at": datetime.datetime.now(
                    datetime.timezone.utc).isoformat(),
            }
        )
    print(f"prompt added: {args.parent_id} / {poi_slug} [{args.category}]")


def cmd_status(args: argparse.Namespace) -> None:
    rows = load_manifest()
    if args.shard is not None:
        rows = [r for r in rows if int(r["shard"]) == args.shard]
    uploaded = existing_slugs()
    skip = flagged_ids()
    prompted: dict[str, int] = {}
    for pr in prompt_rows(args.shard):
        prompted[pr["parent_id"]] = prompted.get(pr["parent_id"], 0) + 1
    total_prompts = sum(prompted.values())
    covered = flagged = pending = 0
    for r in rows:
        if r["parent_id"] in skip:
            flagged += 1
            continue
        have = len(uploaded.get(r["s3_prefix"], [])) + prompted.get(
            r["parent_id"], 0)
        if have >= 4:
            covered += 1
        else:
            pending += 1
    print(f"neighborhoods: {len(rows)}  covered(images+prompts>=4): "
          f"{covered}  flagged: {flagged}  pending: {pending}  "
          f"prompt rows written: {total_prompts}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("pending")
    sp.add_argument("--shard", type=int, required=True)
    sp.add_argument("--limit", type=int, default=0)
    sp.set_defaults(func=cmd_pending)

    sp = sub.add_parser("verify")
    sp.add_argument("query")
    sp.add_argument("--lat", default="")
    sp.add_argument("--lng", default="")
    sp.set_defaults(func=cmd_verify)

    sp = sub.add_parser("add")
    sp.add_argument("parent_id")
    sp.add_argument("poi_name")
    sp.add_argument("--category", required=True,
                    choices=["anchor", "outdoors", "shopping-dining",
                             "culture-architecture"])
    sp.add_argument("--place-id", default="")
    sp.add_argument("--address", default="")
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("status")
    sp.add_argument("--shard", type=int, default=None)
    sp.set_defaults(func=cmd_status)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
