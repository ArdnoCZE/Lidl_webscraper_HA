"""
Scraper e-shopu Lidl.cz (nářadí, aku nářadí atd.) pomocí headless prohlížeče.

DŮLEŽITÉ: Lidl.cz je postavený jako moderní JS aplikace, takže obyčejný
requests.get() nefunguje - stránka se dorenderuje až v prohlížeči. Proto
používáme Playwright (Chromium na pozadí).

CSS selektory níže jsou nejlepší odhad podle běžné struktury e-shopů skupiny
Schwarz (Lidl/Kaufland). Web se čas od času předělá, takže pokud přestanou
sedět, je potřeba je zaktualizovat - viz README, sekce "Ladění selektorů".
Pro snazší ladění je tu funkce debug_dump(), která uloží HTML a screenshot.
"""
import re
import time
import logging
from urllib.parse import quote

from playwright.sync_api import sync_playwright

logger = logging.getLogger("lidl_scraper.shop")

BASE_URL = "https://www.lidl.cz"

# Pokud hledaný text neodpovídá žádné konkrétní kategorii, hledá se přes
# fulltextové vyhledávání e-shopu.
SEARCH_URL_TMPL = BASE_URL + "/q/search?q={query}"

# Volitelné přímé odkazy na kategorie (uživatel je může zadat jako "keyword"
# rovnou ve tvaru URL kategorie, pokud fulltextové hledání nestačí).
CATEGORY_HINT_URLS = {
    "naradi": BASE_URL + "/c/naradi/s10007544",
    "aku-naradi": BASE_URL + "/c/aku-naradi/s10012345",
    "zahradni-technika": BASE_URL + "/c/zahradni-technika/s10012346",
}

# Selektory produktové dlaždice - uprav podle aktuální podoby webu.
SEL_PRODUCT_CARD = "[data-grid-id], .product-grid-box, article[data-testid='product-tile']"
SEL_NAME = "[data-testid='product-tile-title'], .product-grid-box__title, h3, h2"
SEL_PRICE = "[data-testid='product-price'], .m-pricetag__price, .price"
SEL_LINK = "a"
SEL_IMAGE = "img"

PRICE_RE = re.compile(r"(\d[\d\s.,]*\d|\d)\s*(Kč|CZK)?", re.IGNORECASE)


def _parse_price(text: str):
    if not text:
        return None
    text = text.replace("\xa0", " ").strip()
    m = PRICE_RE.search(text)
    if not m:
        return None
    raw = m.group(1).replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def debug_dump(page, name="debug"):
    """Uloží HTML a screenshot pro ruční kontrolu, když scraper nic nenajde."""
    import os
    from pathlib import Path
    data_dir = Path(os.environ.get("DB_DIR", Path(__file__).resolve().parent.parent / "data"))
    out_dir = data_dir / "debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    page.screenshot(path=str(out_dir / f"{name}_{ts}.png"), full_page=True)
    (out_dir / f"{name}_{ts}.html").write_text(page.content(), encoding="utf-8")
    logger.warning("Uložen debug výstup do data/debug/%s_%s.*", name, ts)


def search_shop(query: str, max_items: int = 20, headless: bool = True, debug: bool = False):
    """
    Vyhledá produkty na Lidl.cz pro daný dotaz (klíčové slovo nebo slug kategorie
    z CATEGORY_HINT_URLS) a vrátí seznam slovníků:
    {name, price, currency, url, image_url}
    """
    url = CATEGORY_HINT_URLS.get(query, SEARCH_URL_TMPL.format(query=quote(query)))
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            locale="cs-CZ",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            # cookie lišta
            for txt in ["Přijmout vše", "Souhlasím", "Accept all"]:
                try:
                    btn = page.get_by_text(txt, exact=False)
                    if btn.count() > 0:
                        btn.first.click(timeout=2000)
                        break
                except Exception:
                    pass

            page.wait_for_timeout(1500)  # dorenderování JS

            cards = page.locator(SEL_PRODUCT_CARD)
            count = min(cards.count(), max_items)
            if count == 0 and debug:
                debug_dump(page, name="empty_result")

            for i in range(count):
                card = cards.nth(i)
                try:
                    name = card.locator(SEL_NAME).first.inner_text(timeout=1000).strip()
                except Exception:
                    continue
                try:
                    price_text = card.locator(SEL_PRICE).first.inner_text(timeout=1000)
                except Exception:
                    price_text = ""
                price = _parse_price(price_text)

                try:
                    href = card.locator(SEL_LINK).first.get_attribute("href")
                    full_url = href if href and href.startswith("http") else BASE_URL + (href or "")
                except Exception:
                    full_url = url

                try:
                    img = card.locator(SEL_IMAGE).first.get_attribute("src")
                except Exception:
                    img = None

                results.append({
                    "name": name,
                    "price": price,
                    "currency": "CZK",
                    "url": full_url,
                    "image_url": img,
                })
        finally:
            context.close()
            browser.close()

    return results
