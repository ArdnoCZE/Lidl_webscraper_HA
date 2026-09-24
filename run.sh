#!/usr/bin/env bash
set -e

OPTIONS_FILE="/data/options.json"

get_opt() {
  jq -r ".$1 // \"$2\"" "$OPTIONS_FILE"
}

SCRAPE_INTERVAL_MINUTES="$(get_opt scrape_interval_minutes 180)"
HEADLESS="$(get_opt headless true)"
DEBUG_SCRAPER="$(get_opt debug_scraper false)"

echo "[lidl-scraper] Interval scrapu: ${SCRAPE_INTERVAL_MINUTES} minut"

# Zkusíme přes Supervisor API najít MQTT broker (Mosquitto broker add-on
# nebo jinou nakonfigurovanou MQTT službu). Vyžaduje 'hassio_api: true'
# a 'services: [mqtt:want]' v config.yaml - odtud se bere SUPERVISOR_TOKEN.
MQTT_JSON="$(curl -sf -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
  -H "Content-Type: application/json" \
  http://supervisor/services/mqtt || echo '{}')"

MQTT_RESULT="$(echo "${MQTT_JSON}" | jq -r '.result // "error"')"

if [ "${MQTT_RESULT}" = "ok" ]; then
  export MQTT_ENABLED=true
  export MQTT_HOST="$(echo "${MQTT_JSON}" | jq -r '.data.host')"
  export MQTT_PORT="$(echo "${MQTT_JSON}" | jq -r '.data.port')"
  export MQTT_USERNAME="$(echo "${MQTT_JSON}" | jq -r '.data.username // empty')"
  export MQTT_PASSWORD="$(echo "${MQTT_JSON}" | jq -r '.data.password // empty')"
  echo "[lidl-scraper] MQTT broker nalezen automaticky: ${MQTT_HOST}:${MQTT_PORT}"
else
  export MQTT_ENABLED=false
  echo "[lidl-scraper] VAROVÁNÍ: MQTT broker nenalezen."
  echo "[lidl-scraper] Nainstaluj add-on 'Mosquitto broker' a/nebo nastav MQTT integraci v HA,"
  echo "[lidl-scraper] jinak se ceny nebudou posílat do Home Assistant (jen do webového UI)."
fi

export SCRAPE_INTERVAL_MINUTES
export HEADLESS
export DEBUG_SCRAPER
export DB_DIR="/data"

cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8088
