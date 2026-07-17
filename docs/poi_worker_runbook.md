# POI Image Worker Runbook (unresolved-neighborhoods batch)

You are one of 20 shard workers generating "What's Around" point-of-interest
images. Your shard number is given in your task prompt. Work through every
pending neighborhood in your shard, one at a time, until none remain or you
are stopped.

All commands run from `/workspace`. Credentials are already in the
environment (`GOOGLE_PLACES_API_KEY`, `AWS_Access_Key`, `AWS_Secret_key`).

## Hard rules

- **Never invent a place.** Every POI must be a real, verifiable place
  walkable from the neighborhood.
- **Never run git.** Do not commit, push, or touch branches. Images go to
  S3 only (the `finalize` command does the upload); provenance CSVs are
  committed later by the orchestrator.
- **Never upload originals.** Always go through `finalize`, which
  center-crops to 16:9 (1536x864) and uploads to the correct S3 key.
- Do not stop to ask questions; make the best call and keep going.

## Per-neighborhood workflow

### 0. Get your pending list

```bash
python3 scripts/poi_pipeline.py shard --shard <N> --limit 5
```

Returns pending neighborhoods (fewer than 4 images uploaded), with
`parent_id`, `destination`, `lat`/`lng`, and an `anchor_hint` +
`why_fit` from the earlier research pass. Re-run it as you finish
neighborhoods; it is S3-backed and idempotent, so already-finished
neighborhoods drop off automatically.

### 1. Choose exactly 4 POIs

Pick 4 real places for a traveler on a design-led, urban, walkable stay.
One from each category where possible:

1. **anchor** — the neighborhood's defining landmark or gathering place
   (promenade, pier, plaza, market hall, historic street). The
   `anchor_hint` column is a good starting point, but verify it makes
   sense.
2. **outdoors** — park, garden, waterfront path, beach walk, or viewpoint.
3. **shopping-dining** — open-air shopping center, market, or café street.
4. **culture-architecture** — museum, gallery, theater, historic building,
   or design icon.

Rules: every POI must be real and walkable from the neighborhood. Prefer
places with strong visual identity that photograph well as a landscape.
Skip transient businesses (individual restaurants/bars/shops); prefer
streets, markets, parks, landmarks, institutions. If a category has no
real walkable option, substitute another category (e.g. two outdoors) —
never fabricate. For obscure neighborhoods, city-level landmarks are
acceptable only if they are genuinely adjacent/walkable.

### 2. Fetch and screen a reference photo

```bash
python3 scripts/poi_pipeline.py fetchref "<POI name>, <city>" \
    --lat <lat> --lng <lng> --max-photos 3
```

This downloads candidate photos to `/tmp/poi_refs/` and prints their
paths, matched place name, and attribution. **Look at the photos with
your image-reading tool before using one.** Check the matched
`place_name`/`address` is really your POI. Reject a photo if it shows:

- night shots, fireworks/events
- overcast/gloomy weather
- heavy crowds or traffic
- construction
- interiors of outdoor places
- photos taken *from* the POI (the POI itself must be in frame)
- close-up details, watermarks

If no acceptable photo after 2 attempts (vary the query on the second,
e.g. add "fort", "park", district name), fall back to **text-only**
generation. Record the winning photo's attribution for provenance.

### 3. Build the prompt (verbatim template)

```bash
python3 scripts/poi_pipeline.py prompt "<POI name>" "<destination>"          # with reference
python3 scripts/poi_pipeline.py prompt "<POI name>" "<destination>" --text-only  # no reference
```

`<destination>` is the `destination` field from the shard listing,
verbatim. Use the command output as the image-generation description
**unchanged** — do not edit, trim, or add to it.

### 4. Generate

Call your image-generation tool with:

- `description` = the exact prompt output from step 3
- `aspect_ratio` = `16:9` (the generator still returns 3:2; `finalize`
  center-crops)
- `reference_image_paths` = the accepted reference photo path (omit for
  text-only)
- `filename` = something unique, e.g. `s<N>_<poi-slug>.png`

### 5. QA the result

Look at the generated image. Regenerate if it shows: the wrong place,
prominent people/crowds, readable signage/text, visible artifacts, or
gloomy/dark light. One regeneration is usually enough; if a reference
keeps failing, try another candidate photo or text-only.

### 6. Finalize (crop + upload + provenance)

```bash
python3 scripts/poi_pipeline.py finalize "<parent_id>" "<POI name>" \
    <generated.png> --category <anchor|outdoors|shopping-dining|culture-architecture> \
    --ref-source "places-photo" --ref-attribution "<photographer> (Google Maps contributor)"
```

Omit `--ref-source/--ref-attribution` for text-only generations. This
center-crops to 16:9 1536x864 PNG, uploads to
`images/Neighborhood_POIs/<cc>-<city-slug>/<nhood-slug>/<poi-slug>.png`,
appends provenance to `data/poi_provenance/shard_<N>.csv`, and deletes
the local generated file.

### 7. Clean up and continue

Delete that neighborhood's reference photos
(`rm -f /tmp/poi_refs/<stems>*`) and move to the next pending
neighborhood. Repeat until your shard has no pending neighborhoods.

## Flagging problems

If a neighborhood is ungeneratable (e.g. no real walkable POIs exist, or
Places returns nothing usable and you cannot name 4 real places with
confidence), generate what you can (minimum 0), then append a line to
`data/poi_provenance/flagged_shard_<N>.csv` with
`parent_id,reason` and move on. Never pad with invented places.

## Reporting

When you finish (or must stop), report: neighborhoods completed this
session, images uploaded, text-only count, flagged neighborhoods, and any
systematic issues (API errors, rate limits).
