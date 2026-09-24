# Lidl Price Scraper - instalace jako lokální HA add-on

Tohle je add-on pro **Home Assistant OS / Supervised**. Nasazuje se tak,
že celou tuhle složku (`lidl_price_scraper`) nahraješ do `/addons` na
svém HA stroji - žádné psaní do YAML konfigurace HA, žádný Docker
Compose. Po prvním nahrání a startu add-on běží úplně samostatně.

## Krok 1 - zpřístupni si souborový systém HA

Pokud ještě nemáš, nainstaluj jeden z add-onů pro přístup k souborům
(Nastavení → Add-ony → Add-on Store):

- **Samba share** (nejpohodlnější - připojíš si HA jako síťovou složku
  z Windows/macOS/Linuxu), nebo
- **SSH & Web Terminal** / **Terminal & SSH** (pro zkušenější, kopíruje
  se přes `scp`/`cp`).

## Krok 2 - nahraj složku do /addons

**Přes Samba:**
1. Připoj se na `\\<IP-adresa-HA>\addons` (Windows) nebo
   `smb://<IP-adresa-HA>/addons` (macOS/Linux).
2. Zkopíruj do ní celou složku `lidl_price_scraper` (přesně jak je -
   se souborem `config.yaml` přímo uvnitř ní, ne o úroveň hlouběji).

**Přes SSH/Terminal add-on:**
```bash
# na svém počítači, kde máš rozbalený stažený .zip:
scp -r lidl_price_scraper root@<IP-adresa-HA>:/addons/
```

Výsledná struktura na HA musí vypadat takto:
```
/addons/lidl_price_scraper/config.yaml
/addons/lidl_price_scraper/Dockerfile
/addons/lidl_price_scraper/run.sh
/addons/lidl_price_scraper/app/...
/addons/lidl_price_scraper/templates/...
/addons/lidl_price_scraper/static/...
```

## Krok 3 - najdi a nainstaluj add-on v HA

1. Nastavení → Add-ony → **Add-on Store**.
2. Vpravo nahoře klikni na tři tečky (⋮) → **Check for updates**
   (případně restartuj Supervisor: Nastavení → Systém → Hardware,
   ⋮ → Restart Supervisor, pokud se add-on hned neobjeví).
3. Dole na stránce se objeví sekce **Local add-ons** a v ní **Lidl
   Price Scraper**.
4. Klikni na něj → **Install**. První build stahuje i Chromium
   prohlížeč (~300 MB), může to pár minut trvat.

## Krok 4 - nastav a spusť

1. Záložka **Configuration** - výchozí hodnoty (scrape každé 3 hodiny)
   jsou v pořádku, můžeš je upravit.
2. Záložka **Info** → zapni **Start on boot** a **Watchdog**, ať add-on
   naskočí i po restartu HA.
3. Klikni **Start**.
4. Otevři **OPEN WEB UI** (nebo zapni "Show in sidebar" pro trvalý
   odkaz v levém menu HA).

## Krok 5 - MQTT

Pokud máš (typicky ano) add-on **Mosquitto broker** a nastavenou MQTT
integraci v HA, add-on si broker najde sám - nic dalšího dělat nemusíš.
Pokud MQTT nemáš, nainstaluj add-on "Mosquitto broker" ze Store a
integraci "MQTT" přidej v Nastavení → Zařízení a služby.

## Krok 6 - přidej sledované produkty

Ve webovém UI add-onu přidej klíčová slova jako `aku vrtačka`,
`Parkside`, `benzínová sekačka`, `příslušenství nářadí` a zvol, jestli
se mají hledat v e-shopu, letáku, nebo obojím.

Během chvíle se v Home Assistant objeví entity `sensor.lidl_*` a
`sensor.lidl_letak_shody`, které přidáš do dashboardu jako běžné
entity.

---

Podrobnější dokumentace (nastavení, řešení problémů) je v `DOCS.md` -
zobrazí se i přímo v HA na záložce "Documentation" stránky add-onu.
