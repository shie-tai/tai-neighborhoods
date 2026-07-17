"""Floor-level classification rules for neighborhood hero images.

Every resolved neighborhood in the internal-match CSV is assigned one of
three floor tiers:

  second  Keep the existing second-floor image. Low-rise fabric where a
          second-floor vantage is believable and representative
          (brownstone streets, historic old towns, beach towns, village
          high streets). These are NOT regenerated.
  mid     Regenerate with a mid-floor vantage (3rd-8th storey). Dense
          walk-up / mid-rise fabric where the typical rental sits well
          above the second floor but not in a tower (Manhattan walk-up
          districts, European apartment blocks, loft conversions).
  high    Regenerate with a genuine high-floor vantage (15th-40th
          storey). Residential/hotel tower fabric where a second-floor
          room is implausible (the Las Vegas Strip, Financial District
          Manhattan, Brickell, Coal Harbour, Hong Kong, Chinese CBDs).

Precedence: exact slug override -> (country, neighborhood-leaf) pair ->
leaf keyword -> city default -> country default -> default (second).

US and Canadian slugs are curated as exact display slugs (validated
against the source CSV). International curation uses (country, leaf)
pairs because the region segment in international slugs varies
(e.g. japan/tokyo-prefecture/tokyo/roppongi).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Exact per-slug overrides: USA + Canada (validated against the CSV).
# ---------------------------------------------------------------------------

HIGH_SLUGS: set[str] = {
    # --- USA: hotel/residential tower fabric -------------------------------
    "usa/nevada/las-vegas/las-vegas-strip",
    "usa/new-york/new-york/midtown",
    "usa/new-york/new-york/financial-district",
    "usa/new-york/new-york/hell-s-kitchen",
    "usa/new-york/new-york/upper-east-side",
    "usa/new-york/new-york/upper-west-side",
    "usa/new-york/long-island-city",
    "usa/new-york/brooklyn/downtown-brooklyn",
    "usa/illinois/chicago/river-north",
    "usa/illinois/chicago/streeterville",
    "usa/illinois/chicago/the-loop",
    "usa/illinois/chicago/gold-coast",
    "usa/illinois/chicago/west-loop",
    "usa/florida/miami/brickell",
    "usa/florida/miami/downtown-miami",
    "usa/florida/miami/edgewater",
    "usa/hawaii/honolulu/waikiki",
    "usa/hawaii/honolulu/ala-moana",
    "usa/hawaii/honolulu/downtown-honolulu",
    "usa/washington/seattle/belltown",
    "usa/washington/seattle/downtown-seattle",
    "usa/washington/seattle/south-lake-union",
    "usa/california/san-francisco/financial-district",
    "usa/california/san-francisco/union-square",
    "usa/massachusetts/boston/seaport-district",
    "usa/pennsylvania/philadelphia/center-city",
    "usa/new-jersey/jersey-city/newport",
    "usa/new-jersey/jersey-city/downtown-jersey-city",
    "usa/texas/austin/downtown-austin",
    "usa/texas/austin/rainey-street-historic-district",
    "usa/texas/houston/downtown-houston",
    "usa/texas/houston/uptown",
    "usa/texas/dallas/downtown-dallas",
    "usa/texas/dallas/uptown",
    "usa/georgia/atlanta/midtown",
    "usa/georgia/atlanta/downtown-atlanta",
    "usa/georgia/atlanta/buckhead",
    "usa/colorado/denver/lodo",
    "usa/tennessee/nashville/the-gulch",
    "usa/tennessee/nashville/downtown-nashville",
    "usa/minnesota/minneapolis/downtown-minneapolis",
    "usa/minnesota/minneapolis/mill-district",
    "usa/oregon/portland/pearl-district",
    "usa/oregon/portland/downtown-portland",
    "usa/california/san-diego/east-village",
    "usa/california/san-diego/little-italy",
    "usa/utah/salt-lake-city/downtown-salt-lake-city",
    "usa/missouri/kansas-city/downtown-kansas-city",
    "usa/missouri/kansas-city/power-and-light-district",
    "usa/ohio/cleveland/downtown-cleveland",
    "usa/michigan/detroit/downtown-detroit",
    "usa/pennsylvania/pittsburgh/downtown-pittsburgh",
    "usa/ohio/columbus/downtown-columbus",
    "usa/indiana/indianapolis/downtown-indianapolis",
    "usa/ohio/cincinnati/downtown-cincinnati",
    "usa/louisiana/new-orleans/central-business-district",
    "usa/oklahoma/oklahoma-city/downtown-oklahoma-city",
    "usa/oklahoma/tulsa/downtown-tulsa",
    "usa/florida/tampa/downtown-tampa",
    "usa/florida/orlando/downtown-orlando",
    "usa/florida/jacksonville/downtown-jacksonville",
    "usa/california/oakland/downtown-oakland",
    "usa/california/oakland/uptown-oakland",
    "usa/california/sacramento/downtown-sacramento",
    "usa/california/san-jose/downtown-san-jose",
    "usa/california/long-beach/downtown-long-beach",
    "usa/arizona/phoenix/downtown-phoenix",
    "usa/missouri/st-louis/downtown-st-louis",
    "usa/wisconsin/milwaukee/historic-third-ward",
    "usa/nebraska/omaha/downtown-omaha",
    "usa/new-jersey/newark/downtown-newark",
    "usa/nevada/reno/downtown-reno",
    "usa/new-york/buffalo/downtown-buffalo",
    # --- Canada -------------------------------------------------------------
    "canada/british-columbia/vancouver/coal-harbour",
    "canada/british-columbia/vancouver/downtown-vancouver",
    "canada/british-columbia/vancouver/yaletown",
    "canada/british-columbia/vancouver/west-end",
    "canada/ontario/toronto/downtown-toronto",
    "canada/ontario/toronto/king-west-village",
    "canada/ontario/toronto/liberty-village",
    "canada/ontario/toronto/yorkville",
    "canada/ontario/toronto/humber-bay-shores",
    "canada/quebec/montreal/downtown-montreal",
    "canada/quebec/montreal/griffintown",
    "canada/alberta/calgary/downtown-calgary",
    "canada/alberta/calgary/eau-claire",
    "canada/alberta/calgary/beltline",
    "canada/alberta/edmonton/downtown-edmonton",
}

MID_SLUGS: set[str] = {
    # --- USA: walk-up / mid-rise / loft fabric ------------------------------
    "usa/new-york/new-york/chelsea",
    "usa/new-york/new-york/east-village",
    "usa/new-york/new-york/flatiron-district",
    "usa/new-york/new-york/gramercy",
    "usa/new-york/new-york/greenwich-village",
    "usa/new-york/new-york/nolita",
    "usa/new-york/new-york/soho",
    "usa/new-york/new-york/tribeca",
    "usa/new-york/new-york/west-village",
    "usa/new-york/brooklyn/williamsburg",
    "usa/new-york/brooklyn/greenpoint",
    "usa/new-york/brooklyn/bushwick",
    "usa/new-york/bronx/mott-haven",
    "usa/illinois/chicago/lakeview",
    "usa/illinois/chicago/lincoln-park",
    "usa/illinois/chicago/old-town",
    "usa/california/san-francisco/nob-hill",
    "usa/california/san-francisco/russian-hill",
    "usa/california/san-francisco/north-beach",
    "usa/california/san-francisco/pacific-heights",
    "usa/california/san-francisco/fisherman-s-wharf",
    "usa/california/los-angeles/koreatown",
    "usa/california/los-angeles/westwood",
    "usa/california/los-angeles/hollywood",
    "usa/massachusetts/boston/back-bay",
    "usa/massachusetts/boston/fenway-kenmore",
    "usa/massachusetts/boston/north-end",
    "usa/massachusetts/boston/south-end",
    "usa/pennsylvania/philadelphia/old-city",
    "usa/pennsylvania/philadelphia/washington-square-west",
    "usa/texas/houston/midtown",
    "usa/texas/dallas/oak-lawn",
    "usa/texas/dallas/deep-ellum",
    "usa/texas/dallas/dallas-design-district",
    "usa/georgia/atlanta/old-fourth-ward",
    "usa/colorado/denver/capitol-hill",
    "usa/colorado/denver/uptown",
    "usa/colorado/denver/cherry-creek",
    "usa/colorado/denver/five-points",
    "usa/district-of-columbia/washington/navy-yard",
    "usa/district-of-columbia/washington/district-wharf",
    "usa/district-of-columbia/washington/penn-quarter",
    "usa/district-of-columbia/washington/foggy-bottom",
    "usa/district-of-columbia/washington/dupont-circle",
    "usa/district-of-columbia/washington/logan-circle",
    "usa/district-of-columbia/washington/shaw",
    "usa/district-of-columbia/washington/u-street-corridor",
    "usa/tennessee/nashville/midtown",
    "usa/minnesota/minneapolis/uptown",
    "usa/oregon/portland/nob-hill",
    "usa/oregon/portland/old-town-chinatown",
    "usa/california/san-diego/gaslamp-quarter",
    "usa/california/san-diego/bankers-hill",
    "usa/washington/seattle/capitol-hill",
    "usa/washington/seattle/pioneer-square",
    "usa/washington/seattle/ballard",
    "usa/florida/miami/wynwood-art-district",
    "usa/florida/miami/coconut-grove",
    "usa/wisconsin/milwaukee/lower-east-side",
    "usa/arizona/phoenix/midtown",
    "usa/nevada/reno/midtown",
    "usa/kentucky/louisville/downtown-louisville",
    "usa/tennessee/memphis/downtown-memphis",
    "usa/maryland/baltimore/inner-harbor",
    "usa/maryland/baltimore/harbor-east",
    "usa/maryland/baltimore/mount-vernon",
    "usa/virginia/richmond/fan-district",
    "usa/ohio/cincinnati/over-the-rhine",
    "usa/ohio/cleveland/ohio-city",
    "usa/michigan/detroit/midtown",
    "usa/michigan/detroit/new-center-detroit",
    "usa/pennsylvania/pittsburgh/strip-district",
    "usa/missouri/st-louis/central-west-end",
    "usa/nebraska/omaha/old-market",
    "usa/iowa/des-moines/historic-east-village",
    "usa/texas/el-paso/downtown-el-paso",
    "usa/texas/san-antonio/downtown-san-antonio",
    "usa/texas/fort-worth/fort-worth-cultural-district",
    "usa/kansas/wichita/downtown-wichita",
    "usa/nebraska/lincoln/downtown-lincoln",
    "usa/idaho/boise/downtown-boise",
    "usa/alaska/anchorage/downtown-anchorage",
    "usa/alaska/anchorage/midtown-anchorage",
    "usa/colorado/colorado-springs/downtown-colorado-springs",
    "usa/north-carolina/raleigh/downtown",
    "usa/north-carolina/raleigh/glenwood-south",
    "usa/north-carolina/raleigh/north-hills",
    "usa/north-carolina/durham/downtown",
    "usa/north-carolina/greensboro/downtown-greensboro",
    "usa/florida/st-petersburg/downtown-st-petersburg",
    "usa/florida/fort-lauderdale/flagler-village",
    "usa/florida/hollywood/downtown-hollywood",
    "usa/ohio/toledo/downtown-toledo",
    "usa/california/fresno/downtown",
    "usa/california/bakersfield/downtown",
    "usa/california/riverside/downtown-riverside",
    "usa/arizona/tucson/downtown-tucson",
    "usa/oregon/eugene/downtown-eugene",
    "usa/south-dakota/sioux-falls/downtown",
    "usa/missouri/kansas-city/crossroads-arts-district",
    "usa/missouri/kansas-city/river-market",
    "usa/new-jersey/jersey-city/the-heights",
    # --- Canada -------------------------------------------------------------
    "canada/british-columbia/vancouver/olympic-village",
    "canada/british-columbia/vancouver/gastown",
    "canada/british-columbia/vancouver/fairview",
    "canada/british-columbia/vancouver/south-granville",
    "canada/ontario/toronto/west-queen-west",
    "canada/ontario/toronto/mimico",
    "canada/quebec/montreal/quartier-des-spectacles",
    "canada/quebec/montreal/old-montreal",
    "canada/quebec/montreal/shaughnessy-village",
    "canada/alberta/calgary/mission-district",
    "canada/ontario/ottawa/centretown",
    "canada/ontario/ottawa/byward-market",
    "canada/manitoba/winnipeg/downtown-winnipeg",
    "canada/manitoba/winnipeg/exchange-district",
    "canada/nova-scotia/halifax/downtown-halifax",
    "canada/british-columbia/victoria/downtown-victoria",
    "canada/british-columbia/victoria/inner-harbour",
    "canada/saskatchewan/saskatoon/saskatoon-downtown",
    "canada/ontario/london/downtown-london",
    "canada/quebec/laval/centropolis",
    "canada/ontario/mississauga/port-credit",
}

# Slugs that must stay on the second floor even when a broader rule would
# push them higher (historic/low-rise pockets in otherwise vertical cities).
SECOND_SLUGS: set[str] = {
    "usa/georgia/savannah/historic-district-north",
    "usa/south-carolina/charleston/french-quarter",
    "usa/louisiana/new-orleans/french-quarter",
    "usa/louisiana/new-orleans/garden-district",
    "usa/florida/miami/golden-beach",
    "usa/hawaii/honolulu/manoa",
    "canada/quebec/quebec/vieux-quebec-cap-blanc-colline-parlementaire",
    "canada/ontario/toronto/kensington-market",
}

# ---------------------------------------------------------------------------
# International curation: (country_slug, neighborhood_leaf) pairs.
# ---------------------------------------------------------------------------

HIGH_PAIRS: set[tuple[str, str]] = {
    # United Arab Emirates / Qatar
    ("united-arab-emirates", "difc"),
    ("united-arab-emirates", "downtown-dubai"),
    ("united-arab-emirates", "dubai-marina"),
    ("united-arab-emirates", "jumeirah-beach-residence"),
    ("united-arab-emirates", "al-barsha"),
    ("qatar", "west-bay"),
    # Singapore (tower districts; shophouse hoods stay low)
    ("singapore", "marina-bay"),
    ("singapore", "raffles-place"),
    ("singapore", "tanjong-pagar"),
    ("singapore", "orchard"),
    ("singapore", "bugis"),
    ("singapore", "clarke-quay"),
    ("singapore", "robertson-quay"),
    # Japan (tower districts)
    ("japan", "roppongi"),
    ("japan", "akasaka"),
    ("japan", "marunouchi"),
    ("japan", "ginza"),
    ("japan", "shinjuku"),
    ("japan", "umeda"),
    ("japan", "nakanoshima"),
    ("japan", "daiba"),
    # South Korea
    ("south-korea", "gangnam"),
    ("south-korea", "apgujeong"),
    # Brazil (tower fabric)
    ("brazil", "jardins"),
    ("brazil", "itaim-bibi"),
    ("brazil", "moema"),
    ("brazil", "vila-olimpia"),
    ("brazil", "higienopolis"),
    ("brazil", "jardim-paulista"),
    ("brazil", "vila-mariana"),
    ("brazil", "copacabana"),
    ("brazil", "ipanema"),
    ("brazil", "leblon"),
    ("brazil", "leme"),
    ("brazil", "lagoa"),
    # Argentina
    ("argentina", "puerto-madero"),
    ("argentina", "microcentro"),
    ("argentina", "belgrano"),
    # Mexico
    ("mexico", "santa-fe"),
    # Australia
    ("australia", "southbank"),
    ("australia", "docklands"),
    ("australia", "parramatta-cbd"),
    # United Kingdom
    ("united-kingdom", "canary-wharf"),
    # Israel
    ("israel", "sarona"),
    # Turkey
    ("turkey", "sisli"),
    # Philippines (Metro Manila tower districts)
    ("philippines", "bonifacio-global-city"),
    ("philippines", "ortigas-center"),
    ("philippines", "legazpi-village"),
    ("philippines", "salcedo-village"),
    ("philippines", "eastwood"),
    # Indonesia / Malaysia
    ("indonesia", "kuningan"),
    ("malaysia", "bukit-bintang"),
    ("malaysia", "mont-kiara"),
    # India (tower corridors)
    ("india", "lower-parel"),
    ("india", "worli"),
    ("india", "powai"),
    ("india", "hitec-city"),
    ("india", "gachibowli"),
    ("india", "whitefield"),
    ("india", "new-town"),
    # Kenya
    ("kenya", "westlands"),
    ("kenya", "nairobi-upper-hill"),
    ("kenya", "kilimani"),
    # Poland
    ("poland", "srodmiescie"),
    ("poland", "wola"),
    # Taiwan
    ("taiwan", "xinyi"),
    ("taiwan", "banqiao"),
    # China CBD confirmations (country default is already high)
    ("china", "lujiazui"),
    ("china", "guomao"),
}

MID_PAIRS: set[tuple[str, str]] = {
    # Japan (dense mansion-block fabric)
    ("japan", "shibuya"),
    ("japan", "ebisu"),
    ("japan", "aoyama"),
    ("japan", "harajuku"),
    ("japan", "kagurazaka"),
    ("japan", "nakameguro"),
    ("japan", "namba"),
    ("japan", "shinsaibashi"),
    ("japan", "honmachi"),
    ("japan", "tennoji"),
    ("japan", "kitahama"),
    ("japan", "azabu-juban"),
    ("japan", "hiroo"),
    ("japan", "shirokane"),
    # South Korea
    ("south-korea", "myeongdong"),
    ("south-korea", "hongdae"),
    ("south-korea", "itaewon"),
    ("south-korea", "insadong"),
    ("south-korea", "garosu-gil"),
    ("south-korea", "yeonnam-dong"),
    # Brazil
    ("brazil", "pinheiros"),
    ("brazil", "vila-madalena"),
    ("brazil", "gavea"),
    ("brazil", "centro"),
    # Argentina
    ("argentina", "recoleta"),
    ("argentina", "palermo"),
    ("argentina", "retiro"),
    ("argentina", "colegiales"),
    ("argentina", "las-canitas"),
    # Mexico
    ("mexico", "polanco"),
    ("mexico", "roma-norte"),
    ("mexico", "la-condesa"),
    ("mexico", "del-valle"),
    ("mexico", "benito-juarez"),
    # Europe: dense apartment-block districts (typical unit 3rd-6th floor)
    ("spain", "eixample"),
    ("spain", "chamberi"),
    ("spain", "salamanca"),
    ("spain", "chamartin"),
    ("spain", "retiro"),
    ("united-kingdom", "south-bank"),
    ("turkey", "besiktas"),
    ("turkey", "nisantasi"),
    ("turkey", "kadikoy"),
    ("israel", "old-north"),
    ("israel", "rothschild-boulevard"),
    # Australia / New Zealand
    ("australia", "pyrmont"),
    ("australia", "potts-point"),
    ("australia", "south-yarra"),
    ("australia", "st-kilda"),
    ("australia", "south-brisbane"),
    ("australia", "newstead"),
    ("australia", "fortitude-valley"),
    ("new-zealand", "wynyard-quarter"),
    # Southeast Asia
    ("philippines", "ermita"),
    ("philippines", "malate"),
    ("philippines", "kapitolyo"),
    ("indonesia", "kemang"),
    ("indonesia", "pantai-indah-kapuk"),
    ("malaysia", "bangsar"),
    ("malaysia", "brickfields"),
    ("vietnam", "district-1"),
    ("vietnam", "binh-thanh"),
    ("vietnam", "thao-dien"),
    ("vietnam", "an-phu"),
    # India
    ("india", "bandra-west"),
    ("india", "khar"),
    ("india", "juhu"),
    ("india", "colaba"),
    ("india", "fort"),
    ("india", "connaught-place"),
    ("india", "saket"),
    ("india", "koramangala"),
    ("india", "hsr-layout"),
    ("india", "church-street"),
    ("india", "banjara-hills"),
    ("india", "jubilee-hills"),
    ("india", "begumpet"),
    ("india", "madhapur"),
    ("india", "salt-lake"),
    ("india", "park-street"),
    ("india", "koregaon-park"),
    ("india", "kalyani-nagar"),
    ("india", "baner"),
    ("india", "viman-nagar"),
    ("india", "aundh"),
    # Africa / Middle East
    ("kenya", "lavington"),
    ("kenya", "parklands"),
    ("kenya", "gigiri"),
    ("united-arab-emirates", "bur-dubai"),
    ("united-arab-emirates", "deira"),
    ("united-arab-emirates", "palm-jumeirah"),
    ("saudi-arabia", "al-malaz"),
    ("saudi-arabia", "ash-shati"),
    ("saudi-arabia", "al-hamra-a"),
    ("saudi-arabia", "al-rawdah"),
    ("saudi-arabia", "al-andalus"),
    # Taiwan mid-rise (country default is mid; explicit for clarity)
    ("taiwan", "zhongshan"),
    ("taiwan", "songshan"),
    ("taiwan", "ximending"),
    # Russia / Eastern Europe
    ("russia", "tverskoy"),
    ("russia", "presnensky"),
    ("russia", "khamovniki"),
    ("russia", "zamoskvorechye"),
    ("poland", "mokotow"),
    ("poland", "powisle"),
    ("poland", "zoliborz"),
}

SECOND_PAIRS: set[tuple[str, str]] = {
    ("singapore", "chinatown"),
    ("singapore", "tiong-bahru-estate"),
    ("singapore", "katong"),
    ("singapore", "holland-village"),
    ("singapore", "dempsey-hill"),
    ("united-arab-emirates", "jumeirah"),
    ("china", "nanluoguxiang"),
    ("china", "tianzifang"),
    ("china", "shamian-island"),
    ("japan", "shimokitazawa"),
    ("japan", "jiyugaoka"),
    ("japan", "gion"),
    ("japan", "higashiyama"),
    ("japan", "arashiyama"),
    ("japan", "pontocho"),
    ("south-korea", "ikseon-dong-hanok-village"),
    ("brazil", "santa-teresa"),
    ("argentina", "san-telmo"),
    ("mexico", "coyoacan"),
    ("mexico", "san-angel"),
    ("colombia", "getsemani"),
    ("greece", "plaka"),
    ("france", "marais"),
}

# ---------------------------------------------------------------------------
# City-level defaults: (country_slug, city_token) -> tier. The city token is
# matched against any middle segment of the slug.
# ---------------------------------------------------------------------------

CITY_DEFAULTS: dict[tuple[str, str], str] = {
    ("hong-kong", "hong-kong"): "high",
    ("hong-kong", "hong-kong-island"): "high",
    ("hong-kong", "kowloon"): "high",
    ("united-arab-emirates", "abu-dhabi"): "high",
    ("panama", "panama-city"): "high",
    ("brazil", "sao-paulo"): "high",
    ("spain", "barcelona"): "mid",
    ("spain", "madrid"): "mid",
    ("turkey", "istanbul"): "mid",
    ("israel", "tel-aviv"): "mid",
    ("russia", "moscow"): "mid",
}

# ---------------------------------------------------------------------------
# Country-level defaults (fallback after slug/pair/keyword/city checks).
# ---------------------------------------------------------------------------

# Urban China: the typical rental apartment is in a 20-30 storey tower in
# virtually every district-level neighborhood in the source data.
COUNTRY_DEFAULTS: dict[str, str] = {
    "china": "high",
    "hong-kong": "high",
    "taiwan": "mid",
}

# Keywords in the neighborhood slug leaf that signal a tier when no explicit
# override exists. Second keywords run before high keywords so that historic
# districts always stay low.
SECOND_KEYWORDS: tuple[str, ...] = (
    "old-town", "old-city", "historic", "village", "beach", "island",
    "garden", "old-quarter", "altstadt", "stare-miasto", "vieux",
    "old-market", "hanok",
)
HIGH_KEYWORDS: tuple[str, ...] = (
    "central-business-district", "financial-district", "-cbd", "cbd-",
)

FLOOR_TIERS = ("second", "mid", "high")


def classify_floor(slug: str, why_fit: str = "") -> tuple[str, str]:
    """Return (tier, reason) for a display slug.

    tier is one of "second", "mid", "high". Only "mid" and "high"
    neighborhoods are regenerated; "second" keeps the existing image.
    """
    slug = slug.strip().strip("/")
    parts = slug.split("/")
    country = parts[0]
    leaf = parts[-1]
    middle = parts[1:-1]

    if slug in SECOND_SLUGS:
        return "second", "curated: low-rise/historic fabric, second floor kept"
    if slug in HIGH_SLUGS:
        return "high", "curated: tower fabric, high-floor vantage required"
    if slug in MID_SLUGS:
        return "mid", "curated: walk-up/mid-rise fabric, mid-floor vantage"

    pair = (country, leaf)
    if pair in SECOND_PAIRS:
        return "second", "curated: low-rise/historic fabric, second floor kept"
    if pair in HIGH_PAIRS:
        return "high", "curated: tower fabric, high-floor vantage required"
    if pair in MID_PAIRS:
        return "mid", "curated: walk-up/mid-rise fabric, mid-floor vantage"

    for kw in SECOND_KEYWORDS:
        if kw in leaf:
            return "second", f"keyword '{kw}': low-rise/historic, second floor kept"
    for kw in HIGH_KEYWORDS:
        if kw in leaf or leaf == "cbd":
            return "high", f"keyword '{kw.strip('-')}': CBD/tower district"

    wf = (why_fit or "").lower()
    if any(k in wf for k in ("high-rise", "highrise", "skyscraper")):
        return "high", "why_fit mentions high-rise fabric"

    for seg in middle:
        tier = CITY_DEFAULTS.get((country, seg))
        if tier is not None:
            return tier, f"city default for {seg}, {country}"

    tier = COUNTRY_DEFAULTS.get(country)
    if tier is not None:
        return tier, f"country default for {country}"

    return "second", "default: second-floor image remains representative"
