#!/usr/bin/env python3
"""Print the next N pending manifest entries (slug + prompt) for a stage."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from neighborhood_hero_pipeline import (  # noqa: E402
    IMAGES_DIR, build_prompt, load_manifest,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("-n", type=int, default=8)
    args = ap.parse_args()

    done = {p.relative_to(IMAGES_DIR).with_suffix("").as_posix()
            for p in IMAGES_DIR.rglob("*.png")} if IMAGES_DIR.exists() else set()
    manifest = load_manifest()
    printed = 0
    for slug, row in manifest.items():
        if row["stage"] != args.stage or slug in done:
            continue
        fname = slug.replace("/", "__") + ".png"
        print(f"### {slug} | {fname} | {row['floor_tier']}")
        print(build_prompt(slug, row["destination"], row["floor_tier"]))
        printed += 1
        if printed >= args.n:
            break
    if printed == 0:
        print(f"stage {args.stage} complete")


if __name__ == "__main__":
    main()
