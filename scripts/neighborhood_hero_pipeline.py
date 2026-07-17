#!/usr/bin/env python3
"""Neighborhood hero image pipeline (dynamic floor level).

Adapted from scripts/city_hero_pipeline.py for neighborhoods. Two key
differences from the city pipeline:

1. Destinations are specific neighborhoods within a city, and the view
   through the window shows the everyday atmosphere of the neighborhood,
   never a named landmark (Google Places reference photos are not used).
2. The camera vantage uses a dynamic floor level. The room is never on
   the ground floor: it defaults to a second-floor room, moves to a
   mid-floor walk-up/mid-rise vantage (3rd-6th storey) in dense walk-up
   fabric, and to a genuine high-floor tower vantage (20th-40th storey)
   where the neighborhood's typical accommodation is a high-rise
   (Financial District Manhattan, the Las Vegas Strip, Hong Kong).

Only neighborhoods classified "mid" or "high" are regenerated; every
"second" neighborhood already has a correct second-floor image from the
previous batch and is excluded from the manifest.

Images are written as slug-named 16:9 PNG files under
images/neighborhoods_dynamic/<display_slug>.png, preserving the internal
naming convention exactly (country/region/city/neighborhood).

Subcommands:
  classify      Write analysis/dynamic_floor_neighborhoods/ from the
                internal-match CSV.
  manifest      Build data/neighborhoods_manifest.csv (staged, mid/high
                only): stage 1 = USA + Canada, stage 2 = rest of the
                priority CSV, stage 3 = 46k-sheet neighborhoods.
  prompt        Print the generated prompt for one slug.
  prompts-csv   Emit data/prompt/neighborhood_prompts.csv
                (destination,prompt) for a stage (or all stages).
  finalize      Convert a generated image to a 16:9 PNG at its slug path
                and delete the temporary input.
  status        Print progress counts per stage.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from neighborhood_floor_rules import classify_floor  # noqa: E402

DATA_DIR = REPO_ROOT / "data"
SOURCE_CSV = DATA_DIR / "neighborhoods_source.csv"
MANIFEST_CSV = DATA_DIR / "neighborhoods_manifest.csv"
PROMPT_CSV = DATA_DIR / "prompt" / "neighborhood_prompts.csv"
ANALYSIS_DIR = REPO_ROOT / "analysis" / "dynamic_floor_neighborhoods"
IMAGES_DIR = REPO_ROOT / "images" / "neighborhoods_dynamic"

US_STATE_NAMES: dict[str, str] = {
    "alabama": "Alabama", "alaska": "Alaska", "arizona": "Arizona",
    "arkansas": "Arkansas", "california": "California", "colorado": "Colorado",
    "connecticut": "Connecticut", "delaware": "Delaware",
    "district-of-columbia": "District of Columbia", "florida": "Florida",
    "georgia": "Georgia", "hawaii": "Hawaii", "idaho": "Idaho",
    "illinois": "Illinois", "indiana": "Indiana", "iowa": "Iowa",
    "kansas": "Kansas", "kentucky": "Kentucky", "louisiana": "Louisiana",
    "maine": "Maine", "maryland": "Maryland", "massachusetts": "Massachusetts",
    "michigan": "Michigan", "minnesota": "Minnesota", "mississippi": "Mississippi",
    "missouri": "Missouri", "montana": "Montana", "nebraska": "Nebraska",
    "nevada": "Nevada", "new-hampshire": "New Hampshire", "new-jersey": "New Jersey",
    "new-mexico": "New Mexico", "new-york": "New York",
    "north-carolina": "North Carolina", "north-dakota": "North Dakota",
    "ohio": "Ohio", "oklahoma": "Oklahoma", "oregon": "Oregon",
    "pennsylvania": "Pennsylvania", "rhode-island": "Rhode Island",
    "south-carolina": "South Carolina", "south-dakota": "South Dakota",
    "tennessee": "Tennessee", "texas": "Texas", "utah": "Utah",
    "vermont": "Vermont", "virginia": "Virginia", "washington": "Washington",
    "west-virginia": "West Virginia", "wisconsin": "Wisconsin",
    "wyoming": "Wyoming",
}

CA_PROVINCE_NAMES: dict[str, str] = {
    "alberta": "Alberta", "british-columbia": "British Columbia",
    "manitoba": "Manitoba", "new-brunswick": "New Brunswick",
    "newfoundland-and-labrador": "Newfoundland and Labrador",
    "nova-scotia": "Nova Scotia", "ontario": "Ontario", "quebec": "Quebec",
    "saskatchewan": "Saskatchewan", "prince-edward-island": "Prince Edward Island",
}


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _pretty(segment: str) -> str:
    return " ".join(w.capitalize() for w in segment.split("-"))


def destination_name(slug: str, neighborhood: str, city: str,
                     country: str) -> str:
    parts = slug.split("/")
    if parts[0] == "usa" and len(parts) >= 3 and parts[1] in US_STATE_NAMES:
        return f"{neighborhood}, {city}, {US_STATE_NAMES[parts[1]]}, USA"
    if parts[0] == "usa":
        return f"{neighborhood}, {city}, USA"
    if parts[0] == "canada" and len(parts) >= 3 and parts[1] in CA_PROVINCE_NAMES:
        return f"{neighborhood}, {city}, {CA_PROVINCE_NAMES[parts[1]]}, Canada"
    if parts[0] == "canada":
        return f"{neighborhood}, {city}, Canada"
    return f"{neighborhood}, {city}, {country}"


# ---------------------------------------------------------------------------
# Interior styles per floor tier
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InteriorStyle:
    accommodation: str   # e.g. "converted warehouse loft"
    room: str            # e.g. "living room"
    opening: str         # the window/door treatment
    furniture: str
    edges: str
    floor_cue: bool


MID_STYLES: list[InteriorStyle] = [
    InteriorStyle(
        "converted loft apartment", "living room",
        "tall steel-framed factory windows",
        "a cognac leather sofa with a chaise and a marble-topped side table "
        "with a coffee mug and a folded magazine, a large abstract canvas "
        "leaning against the wall, a worn Persian rug over warm hardwood "
        "floors, an arc floor lamp",
        "exposed brick walls softened with white paint fall toward the left "
        "and right edges as calm space",
        True),
    InteriorStyle(
        "classic walk-up apartment", "sitting room",
        "a generous double-hung window with painted timber trim",
        "a linen sofa and a rattan armchair around a low wooden coffee table "
        "with an espresso cup and an open book, a woven jute rug, a side "
        "table with a small vase of flowers, a leafy potted plant",
        "calm plaster walls fall toward the left and right edges as calm "
        "space",
        True),
    InteriorStyle(
        "mid-rise apartment", "dining room",
        "a wide picture window with a deep painted sill",
        "a round walnut dining table with bentwood chairs, a bowl of citrus "
        "and a small carafe of water on the table, a sideboard with framed "
        "photographs and ceramics, a brass pendant light, a patterned kilim "
        "runner",
        "warm ivory walls fall toward the left and right edges as calm space",
        True),
    InteriorStyle(
        "renovated heritage apartment", "bedroom",
        "a tall sash window with folded-back interior shutters",
        "an upholstered bed dressed in crisp white linens with a knitted "
        "throw folded at its foot, a nightstand with a small lamp and a "
        "book, a bench at the foot of the bed, a soft wool rug",
        "soft dove-grey painted walls fall toward the left and right edges "
        "as calm space",
        True),
]

HIGH_STYLES: list[InteriorStyle] = [
    InteriorStyle(
        "modern high-rise condo", "living room",
        "floor-to-ceiling windows",
        "a low fabric sectional facing the view, a round marble side table "
        "with a coffee mug and an open book, a wool rug, a slim floor lamp, "
        "a large potted fiddle-leaf fig, light oak floors",
        "calm pale-grey walls and light oak panelling fall toward the left "
        "and right edges as calm space",
        True),
    InteriorStyle(
        "upper-floor residential tower apartment", "open-plan space",
        "a wide wall of full-height glazing with a slim frame",
        "a caramel leather lounge chair and a linen sofa around a travertine "
        "coffee table with a carafe of water and two glasses, a flat-weave "
        "rug in muted tones, a console with a stack of art books, a "
        "sculptural table lamp",
        "smooth warm-white walls fall toward the left and right edges as "
        "calm space",
        True),
    InteriorStyle(
        "high-floor serviced apartment", "bedroom",
        "a broad full-height window with sheer curtains drawn back",
        "a low platform bed in soft grey and white linens with a throw "
        "folded at its foot, a pair of walnut nightstands with ceramic "
        "lamps, a cushioned bench, a deep-pile rug",
        "quiet greige walls fall toward the left and right edges as calm "
        "space",
        True),
]

VANTAGE_TEXT: dict[str, str] = {
    "mid": (
        "The room sits on the {floor_word} floor of the building, looking "
        "slightly over and along the street and rooftops below, never at "
        "street or ground level and never an aerial view."
    ),
    "high": (
        "The room sits on a high upper floor of the tower, roughly the "
        "{floor_word} storey, and the view reads as a genuine high-floor "
        "outlook over the neighborhood's rooftops and towers below, never "
        "at street level."
    ),
}

MID_FLOOR_WORDS = ["third", "fourth", "fifth", "sixth"]
HIGH_FLOOR_WORDS = ["18th", "22nd", "26th", "30th", "34th"]

# Window-width realism: full-height glazing is believable only in towers.
MID_WIDTH_NOTE = (
    " The window is as wide as is realistic for this building type, "
    "generous enough to frame the view well, but not floor-to-ceiling "
    "glazing."
)

# ---------------------------------------------------------------------------
# Neighborhood view descriptions
# ---------------------------------------------------------------------------

# Negative hints against city icons the model tends to insert unprompted.
# Keyed on a city token found in the slug's middle segments.
NEGATIVE_HINTS: dict[str, str] = {
    "paris": "No Eiffel Tower in view, no monuments.",
    "new-york": ("Not a postcard skyline shot; no Empire State Building or "
                 "Statue of Liberty featured in the view."),
    "brooklyn": ("Not the Manhattan skyline as the subject; no Empire State "
                 "Building, no Statue of Liberty."),
    "athens": "No Acropolis, no Parthenon, no ancient ruins in view.",
    "rome": "No Colosseum, no St Peter's dome in view.",
    "london": "No Big Ben, no London Eye, no Tower Bridge in view.",
    "san-francisco": "No Golden Gate Bridge featured in the view.",
    "sydney": "No Opera House, no Harbour Bridge in view.",
    "seattle": "No Space Needle in view.",
    "toronto": "No CN Tower featured in the view.",
    "las-vegas": ("No casino logos or readable signage, no Bellagio "
                  "fountains show, no Eiffel Tower or Statue of Liberty "
                  "replicas featured."),
    "dubai": "No Burj Khalifa featured in the view.",
    "istanbul": "No Hagia Sophia, no Blue Mosque in view.",
    "barcelona": "No Sagrada Familia in view.",
    "moscow": "No Kremlin, no St Basil's Cathedral in view.",
    "rio-de-janeiro": "No Christ the Redeemer statue in view.",
    "kuala-lumpur": "No Petronas Towers featured in the view.",
    "taipei": "No Taipei 101 featured in the view.",
    "tokyo": "No Tokyo Tower, no Skytree featured in the view.",
    "shanghai": "No Oriental Pearl Tower featured in the view.",
    "chicago": "Not a postcard skyline shot of Willis Tower.",
    "cairo": "No pyramids in view.",
    "agra": "No Taj Mahal in view.",
    "washington": "No Washington Monument, no Capitol dome in view.",
}


def _view_description(tier: str, destination: str) -> str:
    hood = destination.split(",")[0]
    if tier == "high":
        return (
            f"the everyday elevated cityscape of {hood}: the tops and upper "
            f"floors of neighbouring residential and office towers at "
            f"believable distance, lower rooftops with vents and terraces "
            f"far below, streets reading only as thin lines between "
            f"buildings, and open sky above, exactly what a rental on this "
            f"floor in this neighborhood would genuinely see"
        )
    return (
        f"the everyday streetscape of {hood} from a gently elevated vantage: "
        f"the facades and rooflines of the buildings across the street at "
        f"realistic close scale, street trees and awnings just below, the "
        f"street running sideways beneath the window and out of frame, "
        f"exactly what a rental on this floor in this neighborhood would "
        f"genuinely see"
    )


def _negative_hint(slug: str) -> str:
    for seg in slug.split("/")[1:]:
        hint = NEGATIVE_HINTS.get(seg)
        if hint:
            return " " + hint
    return ""


def pick_style(slug: str, tier: str) -> InteriorStyle:
    pool = HIGH_STYLES if tier == "high" else MID_STYLES
    digest = hashlib.sha256(slug.encode("utf-8")).digest()
    return pool[digest[0] % len(pool)]


def pick_floor_word(slug: str, tier: str) -> str:
    words = HIGH_FLOOR_WORDS if tier == "high" else MID_FLOOR_WORDS
    digest = hashlib.sha256(slug.encode("utf-8")).digest()
    return words[digest[1] % len(words)]


def build_prompt(slug: str, destination: str, tier: str) -> str:
    style = pick_style(slug, tier)
    floor_word = pick_floor_word(slug, tier)
    vantage = VANTAGE_TEXT[tier].format(floor_word=floor_word)
    width_note = "" if tier == "high" else MID_WIDTH_NOTE
    floor_cue = ", floor visible in the lower third" if style.floor_cue else ""
    view = _view_description(tier, destination)
    negative = _negative_hint(slug)
    if tier == "high":
        accommodation_phrase = (
            f"{style.accommodation} vacation rental {style.room} on a high "
            f"floor (around the {floor_word} storey)"
        )
    else:
        accommodation_phrase = (
            f"{floor_word}-floor {style.accommodation} vacation rental "
            f"{style.room}"
        )
    plausibility = (
        f"The view captures the everyday atmosphere and character of the "
        f"neighborhood, not a famous sight: describe only typical, generic "
        f"elements any rental in {destination} could plausibly see, such as "
        f"local rooftop materials, facade styles and colours, street trees "
        f"and greenery, and the local quality of light, in the "
        f"neighborhood's most representative season. Never center or "
        f"feature a named landmark; a quiet, authentic view is better than "
        f"an impressive but implausible one.{negative} Render the view in "
        f"soft, appealing daylight typical of the destination (clear "
        f"morning or golden late afternoon), with the interior lit "
        f"consistently by the same natural light."
    )
    article = "an" if accommodation_phrase[0].lower() in "aeiou" else "a"
    return (
        f"Photorealistic interior of {article} {accommodation_phrase} in "
        f"{destination}, captured as a natural editorial photograph from "
        f"the centre of the room looking out through {style.opening}, where "
        f"the view beyond the opening shows {view}. {plausibility} The "
        f"opening and the neighborhood view sit in the central two-thirds "
        f"of the frame; {style.edges}. {vantage}{width_note} The room is "
        f"furnished with {style.furniture}. Interior materials and decor "
        f"are authentic to the neighborhood's typical housing stock and "
        f"character. Styled and polished like a travel magazine interior, "
        f"tidy and aspirational yet warm and believable as a real vacation "
        f"rental, with a few natural lived-in touches, no people in the "
        f"scene, no cars prominent in the scene. Style: ultra-realistic "
        f"editorial interior photography, natural believable daylight, "
        f"center-safe composition with the outdoor view within the central "
        f"two-thirds of the frame and calm low-contrast walls toward the "
        f"left and right edges for text overlay, nothing critical at the "
        f"extreme edges, slightly muted tonal range for legibility, no busy "
        f"clutter, seamless believable transition between interior and view "
        f"with correct perspective through the window plane and no collage "
        f"effect. Shot on a 28mm lens from standing eye-level (camera "
        f"approximately 1.5 metres above the floor), camera held level with "
        f"no upward tilt, horizon at mid-frame, natural straight-on "
        f"perspective with no low-angle view{floor_cue}. Both the room and "
        f"the outdoor view are rendered crisp and detailed, with only the "
        f"faintest natural falloff at extreme distance, so the neighborhood "
        f"reads sharply, as if the inhabitant's eye has settled on the view "
        f"beyond the window. High detail, 8K resolution, realistic textures "
        f"and materials, subtle film grain. Aspect ratio: 16:9 (landscape)"
    )


# ---------------------------------------------------------------------------
# Classification output (analysis/dynamic_floor_neighborhoods/)
# ---------------------------------------------------------------------------

def load_source_rows() -> list[dict[str, str]]:
    if not SOURCE_CSV.exists():
        raise SystemExit(f"missing {SOURCE_CSV}; commit the internal-match "
                         f"CSV to data/neighborhoods_source.csv first")
    with SOURCE_CSV.open() as fh:
        return [r for r in csv.DictReader(fh) if r["display_slug"].strip()]


def classify_cmd() -> None:
    rows = load_source_rows()
    seen: set[str] = set()
    dynamic: list[dict[str, str]] = []
    second: list[dict[str, str]] = []
    for r in rows:
        slug = r["display_slug"].strip().strip("/")
        if slug in seen:
            continue
        seen.add(slug)
        tier, reason = classify_floor(slug, r["why_fit"])
        rec = {
            "display_slug": slug,
            "neighborhood": _norm(r["neighborhood"]),
            "city": _norm(r["city"]),
            "country": r["country"],
            "country_code": r["country_code"],
            "floor_tier": tier,
            "reason": reason,
        }
        (second if tier == "second" else dynamic).append(rec)

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    fields = ["display_slug", "neighborhood", "city", "country",
              "country_code", "floor_tier", "reason"]

    def write(path: Path, recs: list[dict[str, str]]) -> None:
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(recs)

    def sort_key(rec: dict[str, str]) -> tuple:
        prio = 0 if rec["country_code"] in ("US", "CA") else 1
        return (prio, rec["display_slug"])

    dynamic.sort(key=sort_key)
    second.sort(key=sort_key)
    write(ANALYSIS_DIR / "dynamic_floor_neighborhoods.csv", dynamic)
    write(ANALYSIS_DIR / "second_floor_neighborhoods.csv", second)
    n_high = sum(1 for r in dynamic if r["floor_tier"] == "high")
    n_mid = len(dynamic) - n_high
    print(f"classified {len(seen)} unique neighborhoods: "
          f"{len(dynamic)} to regenerate ({n_high} high, {n_mid} mid), "
          f"{len(second)} keep second-floor image")


# ---------------------------------------------------------------------------
# Manifest (staged; mid/high only)
# ---------------------------------------------------------------------------

def manifest_cmd(secondary_csv: Path | None) -> None:
    dyn_path = ANALYSIS_DIR / "dynamic_floor_neighborhoods.csv"
    if not dyn_path.exists():
        raise SystemExit("run `classify` first")
    with dyn_path.open() as fh:
        dynamic = list(csv.DictReader(fh))

    rows_out: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(slug: str, destination: str, tier: str, stage: int,
            source: str) -> None:
        if slug in seen:
            return
        seen.add(slug)
        rows_out.append({
            "slug": slug, "destination": destination, "floor_tier": tier,
            "stage": str(stage), "source": source,
        })

    # Stage 1: USA + Canada. Stage 2: rest of the priority CSV.
    for r in dynamic:
        stage = 1 if r["country_code"] in ("US", "CA") else 2
        dest = destination_name(r["display_slug"], r["neighborhood"],
                                r["city"], r["country"])
        add(r["display_slug"], dest, r["floor_tier"], stage, "priority_csv")

    # Stage 3: neighborhoods (only) from the 46k sheet, classified with the
    # same rules; only mid/high tiers enter the manifest.
    if secondary_csv is not None:
        with secondary_csv.open() as fh:
            for r in csv.DictReader(fh):
                if r["location_type"] != "neighborhood":
                    continue
                slug = r["display_slug"].strip().strip("/")
                if not slug or slug in seen:
                    continue
                tier, _ = classify_floor(slug)
                if tier == "second":
                    continue
                dest = r["name"].strip()
                if "," not in dest:
                    dest = f"{dest}, {_pretty(slug.split('/')[0])}"
                add(slug, dest, tier, 3, "sheet_46k")

    MANIFEST_CSV.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["slug", "destination", "floor_tier", "stage",
                            "source"],
            quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows_out)
    counts: dict[str, int] = {}
    for r in rows_out:
        counts[r["stage"]] = counts.get(r["stage"], 0) + 1
    print(f"manifest: {len(rows_out)} neighborhoods "
          f"({', '.join(f'stage {k}: {v}' for k, v in sorted(counts.items()))})")


def load_manifest() -> dict[str, dict[str, str]]:
    with MANIFEST_CSV.open() as fh:
        return {r["slug"]: r for r in csv.DictReader(fh)}


# ---------------------------------------------------------------------------
# Prompt commands
# ---------------------------------------------------------------------------

def prompt_cmd(slug: str) -> None:
    row = load_manifest().get(slug)
    if row is None:
        raise SystemExit(f"slug not in manifest: {slug}")
    print(build_prompt(slug, row["destination"], row["floor_tier"]))


def prompts_csv_cmd(stage: str | None) -> None:
    manifest = load_manifest()
    PROMPT_CSV.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with PROMPT_CSV.open("w", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(["destination", "prompt"])
        for slug, row in manifest.items():
            if stage is not None and row["stage"] != stage:
                continue
            w.writerow([row["destination"],
                        build_prompt(slug, row["destination"],
                                     row["floor_tier"])])
            n += 1
    print(f"wrote {n} prompts to {PROMPT_CSV.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# Finalize / status
# ---------------------------------------------------------------------------

def finalize_cmd(slug: str, generated: Path) -> None:
    from PIL import Image

    out_path = IMAGES_DIR / f"{slug}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(generated) as im:
        im = im.convert("RGB")
        w, h = im.size
        target = 16 / 9
        if w / h > target:
            new_w = int(h * target)
            left = (w - new_w) // 2
            im = im.crop((left, 0, left + new_w, h))
        elif w / h < target:
            new_h = int(w / target)
            top = (h - new_h) // 2
            im = im.crop((0, top, w, top + new_h))
        if im.size[0] > 1920:
            im = im.resize((1920, 1080), Image.LANCZOS)
        im.save(out_path, "PNG", optimize=True)
    generated.unlink(missing_ok=True)
    print(f"saved {out_path.relative_to(REPO_ROOT)} "
          f"({out_path.stat().st_size // 1024} KiB)")


def status_cmd() -> None:
    manifest = load_manifest()
    done = {p.relative_to(IMAGES_DIR).with_suffix("").as_posix()
            for p in IMAGES_DIR.rglob("*.png")} if IMAGES_DIR.exists() else set()
    by_stage: dict[str, list[str]] = {}
    for slug, row in manifest.items():
        by_stage.setdefault(row["stage"], []).append(slug)
    for stage in sorted(by_stage):
        slugs = by_stage[stage]
        n_done = sum(1 for s in slugs if s in done)
        print(f"stage {stage}: {n_done}/{len(slugs)} done")
    print(f"total images: {len(done)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("classify")

    p_man = sub.add_parser("manifest")
    p_man.add_argument("--secondary-csv", type=Path, default=None,
                       help="46k sheet CSV for stage 3 (optional)")

    p_prompt = sub.add_parser("prompt")
    p_prompt.add_argument("slug")

    p_pcsv = sub.add_parser("prompts-csv")
    p_pcsv.add_argument("--stage", default=None)

    p_fin = sub.add_parser("finalize")
    p_fin.add_argument("slug")
    p_fin.add_argument("generated", type=Path)

    sub.add_parser("status")

    args = parser.parse_args()
    if args.cmd == "classify":
        classify_cmd()
    elif args.cmd == "manifest":
        manifest_cmd(args.secondary_csv)
    elif args.cmd == "prompt":
        prompt_cmd(args.slug)
    elif args.cmd == "prompts-csv":
        prompts_csv_cmd(args.stage)
    elif args.cmd == "finalize":
        finalize_cmd(args.slug, args.generated)
    elif args.cmd == "status":
        status_cmd()


if __name__ == "__main__":
    main()
