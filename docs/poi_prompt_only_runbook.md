# POI Prompt-Only Worker Runbook (unresolved-neighborhoods batch)

You are one of 20 shard workers writing **prompt rows only** — no image
generation, no S3 uploads. For each pending neighborhood you select the 4
POIs and record the filled verbatim generation prompt in
`data/poi_prompts/shard_<NN>.csv` (committed to git by the orchestrator).

All commands run from `/workspace`. `GOOGLE_PLACES_API_KEY` is in the
environment.

## Hard rules

- **Never invent a place.** Every POI must be a real, verifiable place
  walkable from the neighborhood. Verify with the `verify` subcommand
  and/or your own knowledge; record the matched `place_id`/address.
- **Never run git.** The orchestrator commits.
- **Never write to S3** and never call the image-generation tool.
- Do not stop to ask questions; make the best call and keep going.

## Per-neighborhood workflow

### 0. Get your pending list

```bash
python3 scripts/poi_prompts.py pending --shard <N> --limit 5
```

Each entry shows `need` (how many prompts to add), `uploaded_slugs`
(POIs already generated on S3 — do not duplicate them), and
`prompted_pois` (prompts already written). `anchor_hint` and `why_fit`
come from the earlier research pass. Re-run as you finish; it is
idempotent.

### 1. Choose the POIs (usually 4)

Same selection rules as the image run — see the category definitions in
`docs/poi_worker_runbook.md` (anchor / outdoors / shopping-dining /
culture-architecture). For style examples of good POI picks, skim rows
in `data/poi_provenance/shard_<NN>.csv` from the ~6,000 already
generated. For partial neighborhoods, pick categories not covered by
`uploaded_slugs`/`prompted_pois`.

### 2. Verify each POI is real

```bash
python3 scripts/poi_prompts.py verify "<POI name>, <city>" --lat <lat> --lng <lng>
```

Check the matched name/address/location is genuinely your POI in the
right city (Places often matches same-named places in distant cities —
compare the returned lat/lng with the neighborhood's). If Places has no
match but you are confident the place is real and walkable (well-known
street, market, square), you may proceed without a place_id — but only
when you are certain it exists.

### 3. Record the prompt

```bash
python3 scripts/poi_prompts.py add "<parent_id>" "<POI name>" \
    --category <anchor|outdoors|shopping-dining|culture-architecture> \
    --place-id "<place_id>" --address "<formatted_address>"
```

This fills the verbatim template with the POI name and the manifest's
`destination`, and appends the row (idempotent per parent_id+slug).
Never edit the prompt text yourself.

## Flagging problems

If you cannot name enough real walkable POIs, add prompts for the ones
you can verify, then append `parent_id,reason` to
`data/poi_provenance/flagged_shard_<N>.csv` and move on. Never pad with
invented places.

## Reporting

When you finish your quota, report: neighborhoods completed, prompt rows
written, POIs without place_id (name-only verifications), flagged
neighborhoods, and any systematic issues.
