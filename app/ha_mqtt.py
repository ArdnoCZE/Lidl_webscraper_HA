"""
Publikování dat do Home Assistant přes MQTT Discovery.

Tohle je doporučený způsob, jak dostat data z externí appky do HA -
stačí, aby v HA byl nastavený MQTT integrace/broker (většina instalací
HA ho má, buď add-on Mosquitto broker, nebo externí broker). HA si pak
sám vytvoří senzory podle "discovery" zpráv, není potřeba nic ručně
přidávat do configuration.yaml.

Vytváří:
  - sensor.lidl_<slug> pro každý sledovaný produkt (aktuální cena)
  - sensor.lidl_letak_shody s počtem nálezů v aktuálním letáku a
    atributem obsahujícím detaily (název, stránka, platnost, obrázek)
"""
import json
import logging
import re
import paho.mqtt.client as mqtt

logger = logging.getLogger("lidl_scraper.mqtt")


def _slug(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
    return re.sub(r"_+", "_", text).strip("_")[:60]


class HAMqttPublisher:
    def __init__(self, host, port=1883, username=None, password=None, discovery_prefix="homeassistant"):
        self.host = host
        self.port = port
        self.discovery_prefix = discovery_prefix
        self.client = mqtt.Client(client_id="lidl-ha-scraper")
        if username:
            self.client.username_pw_set(username, password)

    def connect(self):
        self.client.connect(self.host, self.port, keepalive=60)

    def disconnect(self):
        self.client.disconnect()

    def publish_product_price(self, product_key: str, name: str, price, currency: str, url: str, image_url: str):
        slug = _slug(product_key)
        config_topic = f"{self.discovery_prefix}/sensor/lidl_{slug}/config"
        state_topic = f"lidl_scraper/{slug}/state"
        attr_topic = f"lidl_scraper/{slug}/attributes"

        config_payload = {
            "name": f"Lidl: {name}"[:250],
            "unique_id": f"lidl_scraper_{slug}",
            "state_topic": state_topic,
            "json_attributes_topic": attr_topic,
            "unit_of_measurement": currency or "CZK",
            "icon": "mdi:tag-outline",
            "device": {
                "identifiers": ["lidl_ha_scraper"],
                "name": "Lidl Price Scraper",
                "manufacturer": "vlastní integrace",
            },
        }
        self.client.publish(config_topic, json.dumps(config_payload), retain=True)
        self.client.publish(state_topic, price if price is not None else "unknown", retain=True)
        self.client.publish(attr_topic, json.dumps({"url": url, "image_url": image_url, "name": name}), retain=True)

    def publish_leaflet_summary(self, matches: list):
        config_topic = f"{self.discovery_prefix}/sensor/lidl_letak_shody/config"
        state_topic = "lidl_scraper/letak/state"
        attr_topic = "lidl_scraper/letak/attributes"

        config_payload = {
            "name": "Lidl leták: shody",
            "unique_id": "lidl_scraper_leaflet_matches",
            "state_topic": state_topic,
            "json_attributes_topic": attr_topic,
            "icon": "mdi:newspaper-variant-outline",
            "device": {
                "identifiers": ["lidl_ha_scraper"],
                "name": "Lidl Price Scraper",
                "manufacturer": "vlastní integrace",
            },
        }
        self.client.publish(config_topic, json.dumps(config_payload), retain=True)
        self.client.publish(state_topic, len(matches), retain=True)
        # HA má limit velikosti atributů, proto posíláme jen omezený výřez
        trimmed = matches[:25]
        self.client.publish(attr_topic, json.dumps({"matches": trimmed}), retain=True)
