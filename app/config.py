import os


def _bool(val, default=False):
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    # jak často scrapovat (v minutách)
    SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "180"))

    # MQTT / Home Assistant
    MQTT_ENABLED = _bool(os.getenv("MQTT_ENABLED"), default=True)
    MQTT_HOST = os.getenv("MQTT_HOST", "core-mosquitto")
    MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
    MQTT_USERNAME = os.getenv("MQTT_USERNAME") or None
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD") or None
    MQTT_DISCOVERY_PREFIX = os.getenv("MQTT_DISCOVERY_PREFIX", "homeassistant")

    # Playwright
    HEADLESS = _bool(os.getenv("HEADLESS"), default=True)
    DEBUG_SCRAPER = _bool(os.getenv("DEBUG_SCRAPER"), default=False)


settings = Settings()
