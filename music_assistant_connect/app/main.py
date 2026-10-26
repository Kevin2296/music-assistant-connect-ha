"""Music Assistant Connect. Local-only credential helper and setup-flow bridge."""
from __future__ import annotations

import asyncio
import ipaddress
import json
import secrets
import socket
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from browser import ProviderBrowser, BrowserUnavailable

SUPERVISOR_IP = "172.30.32.2"
browser = ProviderBrowser()
SITE = Path(__file__).parent / "static"
OPTIONS_FILE = Path("/data/options.json")
APP_OPTIONS: dict | None = None

def options() -> dict:
    # Supervisor owns this file. Never send its token back to the browser.
    if APP_OPTIONS is not None:
        return APP_OPTIONS
    if not OPTIONS_FILE.exists():
        return {}
    try:
        return json.loads(OPTIONS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(503, "Appconfiguratie niet leesbaar. Werk Music Assistant Connect bij en herstart de app.") from exc

def navigation_url(value: str) -> str:
    """Allow HA root paths or explicit HTTPS UI addresses, never executable URLs."""
    if not value:
        return ""
    parsed = urlparse(value)
    if any(c in value for c in ('\\', '\r', '\n')) or parsed.username or parsed.password:
        return ""
    if value.startswith('/') and not value.startswith('//'):
        return value
    return value if parsed.scheme == 'https' and parsed.hostname else ""

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await browser.close()

app = FastAPI(title="Music Assistant Connect", docs_url=None, redoc_url=None, lifespan=lifespan)

def trusted_ingress(request: Request) -> bool:
    # The Supervisor is the only trusted authentication proxy, not the X-Ingress-Path header.
    return bool(request.client and request.client.host == SUPERVISOR_IP)

async def auth(request: Request):
    # Supervisor is the sole gateway. Never accept direct connections or spoofed headers.
    if not trusted_ingress(request):
        raise HTTPException(status_code=403, detail="Open de app via Home Assistant.")

@app.get("/api/settings")
async def settings(_: None = Depends(auth)):
    config = options()
    return {
        "configured": bool(config.get("ma_url") and config.get("ma_token")),
        "ma_url": config.get("ma_url", ""),
        "ma_ui_url": navigation_url(config.get("ma_ui_url", "")),
    }

@app.middleware("http")
async def no_cache(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN" if trusted_ingress(request) else "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors " + ("'self'" if trusted_ingress(request) else "'none'")
    return response

@app.get("/")
async def home(_: None = Depends(auth)):
    return FileResponse(SITE / "index.html")

@app.get("/app.js")
async def js(_: None = Depends(auth)):
    return FileResponse(SITE / "app.js", media_type="text/javascript")

@app.get("/style.css")
async def css(_: None = Depends(auth)):
    return FileResponse(SITE / "style.css", media_type="text/css")

@app.get("/helpers.js")
async def helpers(_: None = Depends(auth)):
    return FileResponse(SITE / "helpers.js", media_type="text/javascript")

@app.get("/health")
async def health(_: None = Depends(auth)):
    return {"ok": True, "app": "Music Assistant Connect", "ingress_only": True}

class MARequest(BaseModel):
    url: str = Field(default="", max_length=512)
    token: str = Field(default="", max_length=8192)
    command: str = Field(max_length=90)
    args: dict = Field(default_factory=dict)

ALLOWED_COMMANDS = {
    "config/providers", "config/providers/setup", "config/providers/reconfigure",
    "config/flows/submit", "config/flows/get", "config/flows/abort",
    "config/providers/manifests", "music/sync",
}

def validate_ma_url(url: str) -> str:
    """Forbid this LAN proxy from contacting the public Internet / metadata endpoints."""
    parsed = urlparse(url.strip().rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("Gebruik alleen een basis-URL zoals http://192.168.1.50:8095")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Music Assistant-hostnaam kon niet worden opgezocht.") from exc
    if not addresses:
        raise ValueError("Onbekende server.")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not (ip.is_private or ip.is_loopback) or ip.is_link_local:
            raise ValueError("Alleen een server op je lokale netwerk is toegestaan.")
    if parsed.port and parsed.port not in (8095, 80, 443):
        raise ValueError("Gebruik Music Assistant op poort 8095 of een reverse proxy op 80/443.")
    return url.strip().rstrip("/")

@app.post("/api/ma")
async def ma_api(body: MARequest, _: None = Depends(auth)):
    if body.command not in ALLOWED_COMMANDS:
        raise HTTPException(400, "Niet-toegestaan API-commando")
    config = options()
    configured = bool(config.get("ma_url") and config.get("ma_token"))
    # A configured credential can only be sent to its configured target.
    url = config["ma_url"] if configured else body.url
    token = config["ma_token"] if configured else body.token
    if len(token) < 8:
        raise HTTPException(400, "Stel het Music Assistant API-token in bij de appconfiguratie.")
    try:
        target = validate_ma_url(url)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        async with httpx.AsyncClient(timeout=130, follow_redirects=False, trust_env=False) as client:
            response = await client.post(
                target + "/api", json={"message_id": secrets.token_hex(8), "command": body.command, "args": body.args},
                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            )
        if response.status_code == 401:
            raise HTTPException(401, "Music Assistant weigert het API-token. Maak een nieuw token via Instellingen → Profiel.")
        if response.status_code == 403:
            raise HTTPException(403, "Dit Music Assistant-token heeft onvoldoende rechten om providers te beheren.")
        if response.status_code == 400:
            raise HTTPException(400, "Music Assistant ondersteunt dit verzoek niet. Controleer je MA-versie of gebruik de providerinstellingen in Music Assistant.")
        response.raise_for_status()
        data = response.json()
        # Do not log any returned values; provider forms may contain secrets.
        if isinstance(data, dict) and (data.get("error") or "error_code" in data):
            return JSONResponse(status_code=400, content={"error": "Music Assistant heeft het verzoek geweigerd. Controleer de rechten en de MA-versie."})
        # HTTP returns the step itself, including result:null for a FORM step.
        # Only unwrap an actual message envelope; never unwrap the step's result.
        if isinstance(data, dict) and "message_id" in data and "result" in data:
            data = data["result"]
        return {"data": data}
    except (httpx.HTTPError, ValueError) as exc:
        # HTTP errors can contain requested URL, but not the access token.
        raise HTTPException(502, "Geen geldige verbinding met Music Assistant. Controleer het adres, token en de lokale netwerktoegang.") from exc

class ProviderInput(BaseModel):
    provider: str

class TextInput(BaseModel):
    value: str = Field(max_length=1024)

class ClickInput(BaseModel):
    x: float = Field(ge=0, le=980)
    y: float = Field(ge=0, le=800)

def session_owner(request: Request) -> str:
    if not trusted_ingress(request):
        raise HTTPException(403, "Alleen Home Assistant Ingress is toegestaan.")
    uid = request.headers.get("x-remote-user-id", "").strip()
    if not uid:
        raise HTTPException(403, "Home Assistant kon je gebruikersidentiteit niet doorgeven.")
    return "ha:" + uid

browser_start_lock = asyncio.Lock()
browser_session_owner: str | None = None

def assert_browser_owner(request: Request):
    if browser.page is not None and browser_session_owner != session_owner(request):
        raise HTTPException(423, "Een andere Home Assistant-gebruiker heeft al een tijdelijke browsersessie.")

@app.post("/api/browser/start")
async def browser_start(body: ProviderInput, request: Request, _: None = Depends(auth)):
    global browser_session_owner
    async with browser_start_lock:
        assert_browser_owner(request)
        owner = session_owner(request)
        try:
            started = await browser.start(body.provider)
            browser_session_owner = owner
            return started
        except (ValueError, BrowserUnavailable) as exc:
            raise HTTPException(400, str(exc)) from exc

@app.get("/api/browser/screenshot")
async def browser_screenshot(request: Request, _: None = Depends(auth)):
    assert_browser_owner(request)
    try:
        jpg = await browser.screenshot()
        return Response(content=jpg, media_type="image/jpeg")
    except BrowserUnavailable as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post("/api/browser/click")
async def browser_click(body: ClickInput, request: Request, _: None = Depends(auth)):
    assert_browser_owner(request)
    try:
        return await browser.click(body.x, body.y)
    except BrowserUnavailable as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post("/api/browser/type")
async def browser_type(body: TextInput, request: Request, _: None = Depends(auth)):
    assert_browser_owner(request)
    try:
        return await browser.type_text(body.value)
    except BrowserUnavailable as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post("/api/browser/key")
async def browser_key(body: TextInput, request: Request, _: None = Depends(auth)):
    assert_browser_owner(request)
    try:
        return await browser.key(body.value)
    except (ValueError, BrowserUnavailable) as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post("/api/browser/reload")
async def browser_reload(request: Request, _: None = Depends(auth)):
    assert_browser_owner(request)
    try:
        return await browser.reload()
    except BrowserUnavailable as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post("/api/browser/extract")
async def browser_extract(request: Request, _: None = Depends(auth)):
    assert_browser_owner(request)
    try:
        return await browser.extract()
    except BrowserUnavailable as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post("/api/browser/close")
async def browser_close(request: Request, _: None = Depends(auth)):
    assert_browser_owner(request)
    await browser.close()
    return {"ok": True}
