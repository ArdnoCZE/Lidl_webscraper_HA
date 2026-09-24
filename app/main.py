import logging
import threading
from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db
from .scheduler import start_scheduler, run_full_scrape

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Lidl HA Price Scraper")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class IngressRootPathMiddleware:
    """
    Home Assistant Ingress zpřístupňuje add-on pod dynamickou cestou typu
    /api/hassio_ingress/<token>/ a posílá ji v hlavičce X-Ingress-Path.
    Bez tohohle by odkazy na statické soubory a formuláře (které jsou
    v šablonách relativní vůči rootu) mířily mimo tuhle cestu.
    Mimo Ingress (přímý přístup na port) hlavička chybí a nic se neděje.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            for name, value in scope.get("headers", []):
                if name == b"x-ingress-path":
                    scope["root_path"] = value.decode()
                    break
        await self.app(scope, receive, send)


app.add_middleware(IngressRootPathMiddleware)


def base_path(request: Request) -> str:
    """Prefix, který je potřeba dát před každý interní odkaz/redirect."""
    return request.scope.get("root_path", "") or ""


def redirect_home(request: Request):
    return RedirectResponse(url=f"{base_path(request)}/", status_code=303)

# Předvyplněné kategorie podle zadání - nářadí (elektrické, benzínové, aku) + příslušenství
SUGGESTED_KEYWORDS = [
    "aku vrtačka", "aku šroubovák", "aku bruska", "aku pila",
    "benzínová sekačka", "benzínová pila", "elektrická sekačka",
    "elektrická bruska", "elektrická pila", "Parkside",
    "baterie Parkside", "nabíječka Parkside", "příslušenství nářadí",
]


@app.on_event("startup")
def on_startup():
    db.init_db()
    start_scheduler()
    # první scrape spustíme na pozadí, ať web hned naběhne
    threading.Thread(target=run_full_scrape, daemon=True).start()


@app.get("/")
def dashboard(request: Request):
    items = db.list_watch_items()
    products = db.list_products()
    leaflet_matches = db.list_leaflet_matches()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "base": base_path(request),
        "items": items,
        "products": products,
        "leaflet_matches": leaflet_matches,
        "suggested": SUGGESTED_KEYWORDS,
    })


@app.post("/watch/add")
def add_watch(
    request: Request,
    value: str = Form(...),
    label: str = Form(None),
    watch_shop: bool = Form(False),
    watch_leaflet: bool = Form(False),
):
    value = value.strip()
    if value:
        db.add_watch_item(
            kind="keyword",
            value=value,
            label=(label or value).strip(),
            watch_shop=watch_shop,
            watch_leaflet=watch_leaflet,
        )
    return redirect_home(request)


@app.post("/watch/{item_id}/delete")
def delete_watch(item_id: int, request: Request):
    db.delete_watch_item(item_id)
    return redirect_home(request)


@app.post("/watch/{item_id}/toggle")
def toggle_watch(item_id: int, request: Request, active: bool = Form(...)):
    db.set_watch_item_active(item_id, active)
    return redirect_home(request)


@app.post("/scrape/run")
def trigger_scrape(request: Request):
    threading.Thread(target=run_full_scrape, daemon=True).start()
    return redirect_home(request)


@app.get("/api/prices")
def api_prices():
    """Volitelný JSON endpoint - lze použít i jako zdroj pro HA RESTful sensor,
    pokud by MQTT nebylo k dispozici."""
    return JSONResponse(db.list_products())


@app.get("/api/history/{product_key:path}")
def api_history(product_key: str):
    return JSONResponse(db.price_history_for(product_key))
