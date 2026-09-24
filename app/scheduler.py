import logging
from apscheduler.schedulers.background import BackgroundScheduler

from . import db
from .config import settings
from .scraper_shop import search_shop
from .scraper_leaflet import find_matches
from .ha_mqtt import HAMqttPublisher

logger = logging.getLogger("lidl_scraper.job")

_scheduler = BackgroundScheduler()


def _mqtt_publisher():
    if not settings.MQTT_ENABLED:
        return None
    pub = HAMqttPublisher(
        host=settings.MQTT_HOST,
        port=settings.MQTT_PORT,
        username=settings.MQTT_USERNAME,
        password=settings.MQTT_PASSWORD,
        discovery_prefix=settings.MQTT_DISCOVERY_PREFIX,
    )
    try:
        pub.connect()
        return pub
    except Exception as e:
        logger.error("Připojení k MQTT brokeru selhalo (%s) - přeskakuji publikaci do HA.", e)
        return None


def run_full_scrape():
    logger.info("Spouštím scrape...")
    items = db.list_watch_items(active_only=True)
    pub = _mqtt_publisher()

    # 1) e-shop
    for item in items:
        if not item["watch_shop"]:
            continue
        try:
            results = search_shop(item["value"], headless=settings.HEADLESS, debug=settings.DEBUG_SCRAPER)
        except Exception as e:
            logger.error("Chyba při scrapování e-shopu pro '%s': %s", item["value"], e)
            continue

        for r in results:
            if r["price"] is None:
                continue
            product_key = f"{item['id']}:{r['url']}"
            db.upsert_product_price(
                product_key=product_key,
                watch_item_id=item["id"],
                name=r["name"],
                url=r["url"],
                image_url=r["image_url"],
                price=r["price"],
                currency=r["currency"],
            )
            if pub:
                pub.publish_product_price(
                    product_key, r["name"], r["price"], r["currency"], r["url"], r["image_url"]
                )

    # 2) leták - hledáme napříč všemi sledovanými klíčovými slovy najednou
    leaflet_keywords = [i["value"] for i in items if i["watch_leaflet"]]
    if leaflet_keywords:
        try:
            matches = find_matches(leaflet_keywords)
        except Exception as e:
            logger.error("Chyba při scrapování letáku: %s", e)
            matches = []

        db.clear_leaflet_matches()
        # namapujeme keyword zpět na watch_item_id kvůli zobrazení v UI
        kw_to_item = {i["value"]: i["id"] for i in items}
        for m in matches:
            db.add_leaflet_match(
                watch_item_id=kw_to_item.get(m["keyword"]),
                flyer_name=m["flyer_name"],
                page_number=m["page_number"],
                matched_text=m["matched_text"],
                image_url=m["image_url"],
                valid_from=m["valid_from"],
                valid_to=m["valid_to"],
            )
        if pub:
            pub.publish_leaflet_summary(matches)

    if pub:
        pub.disconnect()
    logger.info("Scrape dokončen.")


def start_scheduler():
    _scheduler.add_job(
        run_full_scrape,
        "interval",
        minutes=settings.SCRAPE_INTERVAL_MINUTES,
        id="lidl_scrape",
        next_run_time=None,  # první běh spustíme ručně po startu, viz main.py
        replace_existing=True,
    )
    _scheduler.start()
    return _scheduler
