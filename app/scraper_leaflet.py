"""
Scraper aktuálního letáku Lidl.cz.

Letáky všech zemí skupiny Schwarz (Lidl, Kaufland) běží na veřejném JSON API
`endpoints.leaflets.schwarz` - bez přihlášení, bez cookies. Používá ho i
samotný web lidl.cz jako svůj backend, takže je to spolehlivější a rychlejší
cesta než scrapovat vykreslenou stránku prohlížeče.

Jednotlivé stránky letáku obsahují OCR text (`keyWords`) rozpoznaný ze skenu
- není to čistý strukturovaný seznam produktů, ale dá se v něm hledat
klíčová slova ("aku vrtačka", "sekačka" apod.). Když se slovo najde,
uživateli vrátíme odkaz na obrázek dané stránky letáku, ať si cenu
zkontroluje vizuálně - OCR text bývá poskládaný nespolehlivě (čísla cen
bez desetinné čárky, rozhozené pořadí slov).
"""
import logging
import requests
from unidecode import unidecode

logger = logging.getLogger("lidl_scraper.leaflet")

OVERVIEW_URL = "https://endpoints.leaflets.schwarz/v4/overview"
FLYER_URL = "https://endpoints.leaflets.schwarz/v4/flyer"
CLIENT_LOCALE = "lidl/cs-CZ"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ha-lidl-scraper/1.0)"}


def _norm(text: str) -> str:
    """Odstraní diakritiku a převede na malá písmena pro fulltextové porovnání."""
    return unidecode(text or "").lower()


def get_active_flyers():
    """Vrátí seznam aktuálně platných letáků (celostátní, status='current')."""
    resp = requests.get(
        OVERVIEW_URL,
        params={"client_locale": CLIENT_LOCALE, "region_id": 0},
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    flyers = []
    for category in data.get("categories", []):
        for sub in category.get("subcategories", []):
            for flyer in sub.get("flyers", []):
                if flyer.get("status") == "current" and flyer.get("isActive"):
                    flyers.append(flyer)
    return flyers


def get_flyer_pages(flyer: dict):
    """Stáhne detail jednoho letáku a vrátí seznam jeho stránek s OCR textem."""
    # flyer_identifier je poslední část flyerUrlAbsolute, region z regions[0].code
    url_abs = flyer.get("flyerUrlAbsolute", "")
    slug = url_abs.rstrip("/").split("/ar/")[0].split("/")[-1] if url_abs else None
    if not slug:
        return []
    regions = flyer.get("regions") or [{"code": 0}]
    region_code = regions[0].get("code", 0)

    resp = requests.get(
        FLYER_URL,
        params={
            "flyer_identifier": slug,
            "region_id": region_code,
            "region_code": region_code,
        },
        headers=HEADERS,
        timeout=20,
    )
    if resp.status_code != 200:
        logger.warning("Leták %s nebyl dostupný (HTTP %s)", slug, resp.status_code)
        return []
    data = resp.json()
    return data.get("flyer", {}).get("pages", [])


def find_matches(keywords: list[str]):
    """
    Projde všechny aktivní letáky a vrátí seznam nálezů pro zadaná klíčová
    slova (bez diakritiky, case-insensitive substring match v OCR textu).

    Návratová hodnota: list of dict:
      {keyword, flyer_name, page_number, matched_text, image_url, valid_from, valid_to}
    """
    norm_keywords = [(kw, _norm(kw)) for kw in keywords if kw.strip()]
    if not norm_keywords:
        return []

    matches = []
    try:
        flyers = get_active_flyers()
    except Exception as e:
        logger.error("Nepodařilo se stáhnout přehled letáků: %s", e)
        return []

    for flyer in flyers:
        try:
            pages = get_flyer_pages(flyer)
        except Exception as e:
            logger.warning("Chyba při stahování stránek letáku %s: %s", flyer.get("name"), e)
            continue

        for page in pages:
            haystack = _norm((page.get("keyWords") or "") + " " + (page.get("altText") or ""))
            for original_kw, kw in norm_keywords:
                if kw in haystack:
                    matches.append({
                        "keyword": original_kw,
                        "flyer_name": flyer.get("name", "Leták"),
                        "page_number": page.get("number"),
                        "matched_text": (page.get("altText") or "")[:200],
                        "image_url": page.get("zoom") or page.get("image") or page.get("thumbnail"),
                        "valid_from": flyer.get("offerStartDate") or flyer.get("startDate"),
                        "valid_to": flyer.get("offerEndDate") or flyer.get("endDate"),
                    })
    return matches
