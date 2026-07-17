# tai-neighborhoods

Neighborhood hero images for destination pages, regenerated with a
**dynamic floor level** (fixing the uniform-second-floor and
uniform-window-width mistakes of the first batch).

## Layout

- `analysis/dynamic_floor_neighborhoods/` — which neighborhoods keep their
  existing second-floor image vs. get regenerated at a mid (3rd–6th) or
  high (18th–34th storey) vantage, with reasons.
- `data/neighborhoods_source.csv` — the internal-match CSV of already
  generated neighborhoods (naming convention source of truth).
- `data/secondary_locations_46k.csv` — the 46k locations sheet (stage 3
  uses its `neighborhood` rows only).
- `data/neighborhoods_manifest.csv` — staged work manifest (stage 1 =
  USA + Canada, stage 2 = rest of priority CSV, stage 3 = 46k sheet).
- `data/prompt/neighborhood_prompts.csv` — generated `destination,prompt`
  rows for every neighborhood to regenerate.
- `scripts/neighborhood_floor_rules.py` — floor-tier classification rules.
- `scripts/neighborhood_hero_pipeline.py` — classify / manifest / prompt /
  finalize / status pipeline.
- `images/neighborhoods_dynamic/{country}/{region}/{city}/{neighborhood}.png`
  — final 16:9 PNG hero images, named exactly by internal `display_slug`.
- `docs/neighborhood_dynamic_floor_meta_prompt.md` — the revised
  meta-prompt and full workflow documentation.
