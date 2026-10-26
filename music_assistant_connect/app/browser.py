"""Ephemeral, opt-in browser for extracting provider tokens on a SELF-HOSTED instance.

No credentials/cookies are saved to disk. Only known provider cookies are read.
Playwright sessions are held in memory and destroyed after use.
"""
from __future__ import annotations

import asyncio
import re
import time
from urllib.parse import parse_qs, urlparse
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

PROVIDER_URLS = {
    "ytmusic": "https://music.youtube.com/",
    "soundcloud": "https://soundcloud.com/",
    "deezer": "https://www.deezer.com/",
}


class BrowserUnavailable(Exception):
    pass


class ProviderBrowser:
    def __init__(self):
        self.driver = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.provider = ""
        self.started = 0.0
        self.client_id = ""
        self.yt_cookie = ""
        self._lock = asyncio.Lock()
        self.viewport = {"width": 980, "height": 720}
        self._expiry_task = None

    def _record_request(self, request):
        if self.provider == "soundcloud":
            parsed = urlparse(request.url)
            # Inspect the URL of actual requests; do not guess or expose a shared client-id.
            if parsed.hostname and (parsed.hostname == "soundcloud.com" or parsed.hostname.endswith(".soundcloud.com")):
                ids = parse_qs(parsed.query).get("client_id", [])
                if ids and re.fullmatch(r"[a-zA-Z0-9]{32}", ids[0]):
                    self.client_id = ids[0]
        if self.provider == "ytmusic":
            parsed = urlparse(request.url)
            if parsed.hostname == "music.youtube.com" and "/youtubei/v1/browse" in parsed.path:
                asyncio.create_task(self._read_youtube_request(request))

    async def _read_youtube_request(self, request):
        try:
            headers = await request.all_headers()
            value = headers.get("cookie", "")
            if "__Secure-3PAPISID=" in value:
                self.yt_cookie = value
        except Exception:
            pass

    async def start(self, provider: str):
        if provider not in PROVIDER_URLS:
            raise ValueError("Deze dienst heeft geen ingebouwde browsermodus.")
        async with self._lock:
            await self._close_unlocked()
            try:
                self.driver = await async_playwright().start()
                self.browser = await self.driver.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                self.viewport = {"width": 980, "height": 720} if provider == "ytmusic" else {"width": 440, "height": 760}
                self.context = await self.browser.new_context(
                    viewport=self.viewport,
                    locale="nl-NL", timezone_id="Europe/Amsterdam", device_scale_factor=1,
                    accept_downloads=False,
                )
                self.page = await self.context.new_page()
                self.provider = provider
                self.started = time.monotonic()
                self.client_id = ""
                self.yt_cookie = ""
                self.page.on("request", self._record_request)
                try:
                    await self.page.goto(PROVIDER_URLS[provider], wait_until="domcontentloaded", timeout=35000)
                except Exception:
                    # Browser may still have loaded login page even if subresources time out.
                    pass
                self._expiry_task = asyncio.create_task(self._expire_after(900))
                return {"ready": True, "provider": provider, "page": self.page.url, "viewport": self.viewport}
            except Exception as exc:
                await self._close_unlocked()
                raise BrowserUnavailable("Chromium kon niet worden gestart. Controleer de containerlogs en het geheugen.") from exc

    def ensure_live(self):
        if not self.page or self.page.is_closed():
            raise BrowserUnavailable("Start eerst een nieuwe browsersessie.")
        if time.monotonic() - self.started > 900:
            raise BrowserUnavailable("Deze browsersessie is verlopen. Begin opnieuw.")

    async def screenshot(self) -> bytes:
        async with self._lock:
            self.ensure_live()
            return await self.page.screenshot(type="jpeg", quality=67, animations="disabled", timeout=15000)

    async def click(self, x: float, y: float):
        async with self._lock:
            self.ensure_live()
            await self.page.mouse.click(max(0, min(self.viewport["width"]-1, x)), max(0, min(self.viewport["height"]-1, y)))
            await self.page.wait_for_timeout(400)
            return {"ok": True, "url": self.page.url}

    async def type_text(self, value: str):
        async with self._lock:
            self.ensure_live()
            if len(value) > 1024:
                raise ValueError("Maximaal 1024 tekens per invoer.")
            await self.page.keyboard.insert_text(value)
            return {"ok": True}

    async def key(self, value: str):
        async with self._lock:
            self.ensure_live()
            if value not in ("Enter", "Tab", "Escape", "Backspace", "ArrowDown", "ArrowUp"):
                raise ValueError("Onbekende toets.")
            await self.page.keyboard.press(value)
            await self.page.wait_for_timeout(250)
            return {"ok": True}

    async def reload(self):
        async with self._lock:
            self.ensure_live()
            try:
                await self.page.reload(wait_until="domcontentloaded", timeout=15000)
            except Exception:
                pass
            return {"ok": True}

    async def extract(self):
        async with self._lock:
            self.ensure_live()
            cookies = await self.context.cookies()
            result = {}
            if self.provider == "soundcloud":
                token = next((c["value"] for c in cookies if c["name"] == "oauth_token" and "soundcloud.com" in c["domain"]), "")
                if token:
                    result["authorization"] = "OAuth " + token.removeprefix("OAuth ")
                if self.client_id:
                    result["client_id"] = self.client_id
                missing = [x for x in ("client_id", "authorization") if x not in result]
                message = "SoundCloud-gegevens gevonden." if not missing else "Nog niet gevonden: " + ", ".join(missing) + ". Open een afspeellijst, ververs en probeer opnieuw."
            elif self.provider == "deezer":
                arl = next((c["value"] for c in cookies if c["name"].lower() == "arl" and "deezer.com" in c["domain"]), "")
                if arl:
                    result["arl"] = arl
                message = "Deezer ARL gevonden." if arl else "ARL nog niet gevonden. Log eerst in op Deezer."
            elif self.provider == "ytmusic":
                if self.yt_cookie and "__Secure-3PAPISID=" in self.yt_cookie:
                    result["cookie"] = self.yt_cookie
                message = "YouTube Music-cookie gevonden." if result else "Geen geldige cookie uit een /browse-aanvraag gevonden. Open een eigen afspeellijst en probeer opnieuw. Google kan deze browser blokkeren."
            else:
                raise ValueError("Geen export voor deze dienst.")
            if result:
                # Especially important for YT Music: immediately destroy rotating session.
                await self._close_unlocked()
            return {"found": bool(result), "values": result, "message": message}

    async def close(self):
        async with self._lock:
            await self._close_unlocked()

    async def _expire_after(self, seconds):
        try:
            await asyncio.sleep(seconds)
            await self.close()
        except asyncio.CancelledError:
            pass

    async def _close_unlocked(self):
        task = self._expiry_task
        self._expiry_task = None
        if task and task is not asyncio.current_task():
            task.cancel()
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.driver:
                await self.driver.stop()
        finally:
            self.context = None
            self.browser = None
            self.driver = None
            self.page = None
            self.client_id = ""
            self.yt_cookie = ""
            self.provider = ""
            self.started = 0.0