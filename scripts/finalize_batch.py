#!/usr/bin/env python3
"""Finalize all generated images from a staging directory.

Looks for files named <slug with / replaced by __>.png, copies each to a
temp path, converts to a 16:9 PNG at its slug path under
images/neighborhoods_dynamic/, and removes the temp copy. The staging
originals are left untouched (artifact files are immutable).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from neighborhood_hero_pipeline import (  # noqa: E402
    BACKFILL_DIR, IMAGES_DIR, finalize_cmd, load_manifest,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("staging", type=Path)
    args = ap.parse_args()

    manifest = load_manifest()
    n = skipped = 0
    for f in sorted(args.staging.glob("*__*.png")):
        slug = f.stem.replace("__", "/")
        if slug not in manifest:
            print(f"SKIP (not in manifest): {f.name}")
            skipped += 1
            continue
        out_dir = (BACKFILL_DIR if manifest[slug]["stage"] == "3"
                   else IMAGES_DIR)
        out = out_dir / f"{slug}.png"
        if out.exists():
            skipped += 1
            continue
        tmp = Path("/tmp") / f.name
        shutil.copy(f, tmp)
        finalize_cmd(slug, tmp, out_dir)
        n += 1
    print(f"finalized {n}, skipped {skipped}")


if __name__ == "__main__":
    main()
