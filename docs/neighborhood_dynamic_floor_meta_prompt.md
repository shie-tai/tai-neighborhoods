# Neighborhood Interior Hero Images — Dynamic Floor Level

This document is the revised meta-prompt and workflow for regenerating
neighborhood hero images with a **dynamic floor level**. It fixes the two
mistakes in the original batch:

1. **Every image was on the second floor.** A second-floor apartment is
   implausible in the Financial District of Manhattan or on the Las Vegas
   Strip, where the typical stay is on a much higher floor. The floor level
   is now chosen per neighborhood, driven by that neighborhood's typical
   housing stock — never the ground floor, and never uniformly the second
   floor.
2. **Window width was uniform.** The window is now as wide as is realistic
   for the building type: floor-to-ceiling glazing only in genuine
   residential towers; realistically generous (but not full-height) windows
   everywhere else.

## Floor tiers

Every neighborhood in `data/neighborhoods_source.csv` is classified into
one of three tiers by `scripts/neighborhood_floor_rules.py`:

| Tier | Vantage | Example | Action |
|---|---|---|---|
| `second` | Second floor (unchanged) | Getsemaní, Plaka, Savannah Historic District, Silver Lake | **Keep existing image — not regenerated** |
| `mid` | 3rd–6th floor walk-up / mid-rise | SoHo, Le Marais-type fabric, Eixample, Recoleta | Regenerate |
| `high` | 18th–34th storey tower | Las Vegas Strip, Financial District NYC, Brickell, Coal Harbour, Hong Kong | Regenerate |

Classification precedence: curated slug override → curated
(country, neighborhood) pair → historic/low-rise keyword → high-rise
keyword → city default (e.g. Hong Kong = high) → country default
(e.g. urban China = high, Taiwan = mid) → second.

The full classification lives in `analysis/dynamic_floor_neighborhoods/`:

- `dynamic_floor_neighborhoods.csv` — the 657 neighborhoods to regenerate
  (with tier and reason), USA/Canada first.
- `second_floor_neighborhoods.csv` — the 1,433 neighborhoods whose existing
  second-floor image stays.

## Workflow diagram

1. **Destination list** — `data/neighborhoods_source.csv` (internal-match
   CSV) plus, for the tertiary stage, the 46k locations sheet filtered to
   `location_type=neighborhood` only.
2. **Generate prompts** — `scripts/neighborhood_hero_pipeline.py` builds a
   dynamic prompt per neighborhood (CSV output:
   `data/prompt/neighborhood_prompts.csv`, columns `destination,prompt`).
3. **Batch process** — feed the prompt CSV to the selected image model
   (OpenAI image gen preferred when available), 20 workers splitting the
   manifest, then `finalize` each output into a slug-named 16:9 PNG under
   `images/neighborhoods_dynamic/{country}/{region}/{city}/{neighborhood}.png`.

Staging (from `data/neighborhoods_manifest.csv`):

- **Stage 1**: USA (50 states + DC) and Canada revisions from the priority
  CSV — 211 neighborhoods (`mid`/`high` only; `second` keeps its image).
- **Stage 2**: the rest of the priority CSV revisions — 446 neighborhoods.
  The last PR that completes stage 1 must state that the priority list is
  done and stage 2 begins.
- **Stage 3**: the 46k sheet — neighborhoods **only** (no cities, states,
  countries) that are **not** already in the priority CSV. These were
  never generated, so **all tiers** are included (18,876 neighborhoods:
  17,664 fresh `second`-floor generations plus 853 `high` and 359 `mid`).

Operational rules for the batch run:

- Save each image as PNG named by the internal `display_slug` — the naming
  convention must not change.
- Push to GitHub every 100–200 images; after each push, delete the local
  copies from the work cache and monitor disk space so the run stays fast.

## Meta-prompt (how prompts are generated)

You are an expert prompt engineer for text-to-image models. You will be
given a list of travel destinations, each a specific neighborhood within a
city, together with a floor tier (`second`, `mid`, or `high` — `second`
appears only for stage-3 neighborhoods that were never generated). For
each neighborhood,
generate one photorealistic image-generation prompt for the interior of a
typical vacation rental there, viewed from inside looking out through a
window to a characteristic outdoor view of that neighborhood. These prompts
are used as landscape hero images on neighborhood destination pages and are
run across multiple image models.

### Output format

- CSV with exactly two columns: `destination,prompt`; header row first;
  one row per destination; both fields wrapped in double quotes with
  internal quotes doubled. Output only the CSV.

### Floor level (the key change)

- The room is **never on the ground floor** and no longer defaults to the
  second floor. Use the supplied tier:
  - `second` (stage-3 fresh generations only) — a second-floor room with a
    gently elevated outlook, exactly like the original meta-prompt.
  - `mid` — state an explicit third-to-sixth floor (vary across the list),
    e.g. "fifth-floor converted loft living room". The view looks slightly
    over and along the street and rooftops below, never an aerial view.
  - `high` — place the room on a named high floor (18th–34th storey, vary
    across the list) of a residential tower, e.g. "living room on a high
    floor (around the 26th storey)". The view must read as a genuine
    high-floor outlook: tops and upper floors of neighbouring towers,
    rooftops far below, streets as thin lines, open sky.
- The floor level is **city-specific**: on the Las Vegas Strip the stay is
  high in a tower; in Santa Monica it stays close to ground level (such
  neighborhoods are tier `second` and are not regenerated at all).

### Window width realism

- The window is as wide as is relevant for the building type: generous
  enough to frame the cityscape well, but floor-to-ceiling glazing only in
  genuine residential towers (`high` tier). Most homes do not have
  ground-to-ceiling windows; `mid`-tier prompts must say so explicitly.

### Room and property

- Identify the accommodation type most typical for that specific
  neighborhood, not the city in general (converted loft, heritage walk-up,
  high-rise condo, serviced apartment, and so on).
- Choose the room type (living room, kitchen, dining room, bedroom,
  sunroom, or open-plan space) that best frames the neighborhood's
  characteristic view; vary room types and furnishing across the list.
- The room must read as genuinely furnished and lived-in: a main seating
  or dining group plus supporting pieces (rug, lamp, side table, plant,
  art). Never sparse or empty.

### Composition and framing

- Key outdoor view within the central two-thirds of the frame (survives a
  mobile center-crop); calm, low-contrast surfaces at the far left and
  right edges for text overlay; nothing critical at the extreme edges;
  slightly muted tonal range; 16:9 landscape.

### Camera and perspective

- 28mm lens, standing eye-level (camera about 1.5 m above the room's
  floor), camera level with no upward tilt, horizon at mid-frame, natural
  straight-on perspective, floor visible in the lower third (omit the
  floor cue for balcony-facing views).
- The vantage through the opening must read as elevated per the tier,
  never at street or ground level.

### Neighborhood authenticity and view realism

- Always include the neighborhood, city, and country in the destination
  name.
- Interior materials, furniture, palette, and decor authentic to the
  neighborhood's typical housing stock.
- The view shows what a guest in an **upscale stay** in that neighborhood
  would realistically see: characteristic of the neighborhood and clearly
  of that place, **neither too grand nor too nondescript**. On the Las
  Vegas Strip that means the resort towers lining the boulevard, not a
  parking lot; in SoHo the cast-iron facades opposite, not an anonymous
  wall. Never make the main subject a parking lot, service rooftops,
  blank walls, or back-of-house fabric.
- Never center or feature a named landmark filling the view like a
  poster, and do not invent dramatic vistas most rentals there would not
  have. Describe the buildings, materials, greenery, and light that
  define the neighborhood's character.
- Signature neighborhoods carry a curated view hint (see `VIEW_HINTS` in
  `scripts/neighborhood_hero_pipeline.py`): a one-line description of the
  characteristic view an upscale rental there genuinely has (e.g. the
  Strip corridor's resort towers, Coal Harbour's water-and-mountains).
  Extend this dict when a generic view under-delivers for a well-known
  neighborhood.
- Add a short negative hint where the model is likely to insert the city's
  icon unprompted (e.g. "No Eiffel Tower in view" for Paris; "no casino
  logos or readable signage" for Las Vegas).
- For window-onto-street views, show a single building close opposite at
  realistic scale; the street runs sideways below rather than receding
  into the distance, seen slightly from above per the elevated vantage.

### Look, feel, and technical specs

- Styled like a polished travel-magazine interior: tidy and aspirational
  yet warm and believable, a few natural lived-in touches, no people, no
  cars prominent.
- Natural light filling the room evenly; both the room and the view
  rendered crisp and detailed (the view must stay sharp enough to read the
  neighborhood).
- Ultra-realistic editorial interior photography, high detail, 8K
  resolution, realistic textures and materials, subtle film grain.
- Final line of every prompt: `Aspect ratio: 16:9 (landscape)`.

## Pipeline commands

```bash
# 1. Classify all neighborhoods into floor tiers
python3 scripts/neighborhood_hero_pipeline.py classify

# 2. Build the staged manifest (mid/high only)
python3 scripts/neighborhood_hero_pipeline.py manifest \
    --secondary-csv data/secondary_locations_46k.csv

# 3. Emit the prompts CSV (one stage at a time; the committed CSV holds
#    stages 1-2 only — regenerate stage 3 locally at batch time, since all
#    18,876 stage-3 prompts together exceed GitHub's file-size limits)
python3 scripts/neighborhood_hero_pipeline.py prompts-csv --stage 1

# 4. Inspect one prompt
python3 scripts/neighborhood_hero_pipeline.py prompt usa/nevada/las-vegas/las-vegas-strip

# 5. After generating an image, finalize it to its slug path as 16:9 PNG
python3 scripts/neighborhood_hero_pipeline.py finalize \
    usa/nevada/las-vegas/las-vegas-strip /tmp/generated.png

# 6. Track progress
python3 scripts/neighborhood_hero_pipeline.py status
```
