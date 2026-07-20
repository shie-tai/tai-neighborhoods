#!/usr/bin/env python3
"""Generate stage 3 prompts (46k-sheet fresh generations) as sharded CSVs.

Prompt-only pipeline for stage 3: no images are generated here. The output
shards live under data/prompt/stage3/ (full stage 3) or
data/prompt/stage3_remaining/ (--remaining-only) and are committed to
GitHub so a downstream OpenAI Batch job (image-gen-2) can render them later.

Each row carries the slug, the target filename (slug with "/" replaced by
"__", .png extension), destination, floor tier, and the full prompt, so the
batch job output can be mapped straight back onto the repo layout
images/neighborhood_backfill/{slug}.png (or neighborhoods_dynamic/).

Runs with a 20-worker process pool; each worker renders one shard.
"""

from __future__ import annotations

import argparse
import csv
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from neighborhood_hero_pipeline import (  # noqa: E402
    REPO_ROOT, build_prompt, done_slugs, load_manifest,
)

STAGE3_DIR = REPO_ROOT / "data" / "prompt" / "stage3"
STAGE3_REMAINING_DIR = REPO_ROOT / "data" / "prompt" / "stage3_remaining"
WORKERS = 20
SHARD_SIZE = 1000


def _write_shard(args: tuple[Path, int, list[dict[str, str]]]) -> str:
    out_dir, shard_no, rows = args
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"stage3_prompts_shard_{shard_no:02d}.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(["slug", "filename", "destination", "floor_tier",
                    "prompt"])
        for row in rows:
            slug = row["slug"]
            w.writerow([
                slug,
                slug.replace("/", "__") + ".png",
                row["destination"],
                row["floor_tier"],
                build_prompt(slug, row["destination"], row["floor_tier"]),
            ])
    return f"{path.relative_to(REPO_ROOT)} ({len(rows)} prompts)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", type=str, default=None,
                    help="comma-separated shard numbers to (re)generate; "
                         "default: all")
    ap.add_argument("--remaining-only", action="store_true",
                    help="only neighborhoods not yet in data/done_slugs.txt; "
                         "write under data/prompt/stage3_remaining/")
    args = ap.parse_args()

    stage3 = [r for r in load_manifest().values() if r["stage"] == "3"]
    out_dir = STAGE3_DIR
    if args.remaining_only:
        done = done_slugs()
        stage3 = [r for r in stage3 if r["slug"] not in done]
        out_dir = STAGE3_REMAINING_DIR

    shards = [(out_dir, i // SHARD_SIZE + 1, stage3[i:i + SHARD_SIZE])
              for i in range(0, len(stage3), SHARD_SIZE)]
    if args.shards:
        wanted = {int(s) for s in args.shards.split(",")}
        shards = [s for s in shards if s[1] in wanted]

    with Pool(WORKERS) as pool:
        for msg in pool.imap_unordered(_write_shard, shards):
            print(f"wrote {msg}", flush=True)
    print(f"done: {len(shards)} shards, {sum(len(r) for _, _, r in shards)} "
          f"prompts total -> {out_dir.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
