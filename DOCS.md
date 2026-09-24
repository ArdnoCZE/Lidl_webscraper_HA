# Lidl Price Scraper - dokumentace

## Co add-on dělá

- Sleduje ceny vybraných produktů na e-shopu **Lidl.cz** (nářadí, aku
  nářadí, benzínové/elektrické nářadí, příslušenství...).
- Hledá zadaná klíčová slova v aktuálním **týdenním letáku** Lidl.cz.
- Má vlastní webové rozhraní (otevřeš tlačítkem **OPEN WEB UI** nebo
  přes postranní panel, pokud si ho zapneš).
- Posílá výsledky do Home Assistant přes **MQTT Discovery** - žádné
  ruční úpravy `configuration.yaml`.

## Nastavení (záložka Configuration)

| Volba | Význam |
|---|---|
| `scrape_interval_minutes` | Jak často se má spouštět scrape (15–1440 minut). Výchozí 180. |
| `headless` | Nechat vypnuté (`true`) - prohlížeč běží na pozadí bez okna, jak má. |
| `debug_scraper` | Zapni na `true`, pokud e-shop scraper přestane nacházet produkty - uloží se screenshot a HTML do `/data/debug` pro diagnostiku. |

## MQTT

Add-on si po startu **sám** zkusí najít MQTT broker přes Supervisor
(funguje automaticky, pokud máš nainstalovaný a nastavený add-on
**Mosquitto broker**, nebo jinak nakonfigurované MQTT). V logu add-onu
uvidíš buď:

```
[lidl-scraper] MQTT broker nalezen automaticky: ...
```

nebo varování, že broker nenašel - v tom případě si data uvidíš jen ve
webovém UI add-onu, ale neobjeví se jako entity v HA.

Po úspěšném připojení se v HA samy vytvoří entity:

- `sensor.lidl_<produkt>` - cena každého sledovaného produktu z e-shopu
- `sensor.lidl_letak_shody` - počet nálezů v aktuálním letáku (atribut
  `matches` obsahuje detaily a odkaz na obrázek stránky letáku)

## Přidávání sledovaných položek

Ve webovém UI add-onu (sekce „Sledované položky“) přidáš klíčové slovo,
např. `aku vrtačka`, `Parkside`, `benzínová sekačka`, `příslušenství
nářadí`, a zaškrtneš, jestli se má hledat v e-shopu, letáku, nebo obojím.

## Řešení problémů

- **Add-on se nezobrazuje v Local add-ons** - zkontroluj, že složka
  `lidl_price_scraper` je přímo v `/addons/` (ne o úroveň hlouběji), a
  restartuj Supervisor (Nastavení → Systém → Hardware/Supervisor →
  restart, nebo `ha supervisor reload` v Terminálu).
- **Build trvá dlouho** - první instalace stahuje Chromium (~300 MB),
  může to trvat několik minut, hlavně na Raspberry Pi.
- **E-shop scraper nic nenajde** - zapni `debug_scraper`, podívej se do
  `/data/debug` (přes add-on „File editor“ nebo Samba), a uprav CSS
  selektory v `app/scraper_shop.py` (viz komentáře v souboru).
- **Entity se neobjevují v HA** - zkontroluj log add-onu, jestli se
  podařilo najít MQTT broker (viz sekce MQTT výše).
