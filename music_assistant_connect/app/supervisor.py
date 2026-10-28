"""Minimal Supervisor client: find the MA app and store this app's own options.

Uses only calls the default app role may make (`/addons/<slug>/info` and
`/addons/self/options`). Never logs or returns the Supervisor token.
"""
from __future__ import annotations

import re
import time

import httpx

SUPERVISOR_URL = "http://supervisor"
TOKEN = ""  # Set by startup.py from the environment, then removed from os.environ.
# MA publishes its official apps in repository d5369777; stable first.
MA_SLUGS = ("d5369777_music_assistant", "d5369777_music_assistant_beta",
            "d5369777_music_assistant_nightly")
PO_TOKEN_SLUG = "d5369777_ytm_po_token_generator"
# MA runs on the host network, which this container reaches on the hassio bridge.
HOST_IP = "172.30.32.1"
DEFAULT_MA_URL = f"http://{HOST_IP}:8095"
DEFAULT_MA_UI_URL = f"/hassio/ingress/{MA_SLUGS[0]}"
PO_TOKEN_PING_URL = f"http://{HOST_IP}:4416/ping"
INGRESS_URL = re.compile(r"^/api/hassio_ingress/[A-Za-z0-9_-]{8,128}/$")
_CACHE_SECONDS = 60
_cache: tuple[float, dict | None] | None = None


def available() -> bool:
    return bool(TOKEN)


def _client(timeout=8):
    return httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False)


async def app_info(slug: str) -> dict | None:
    """Return another app's public info, or None when missing or unreachable."""
    if not TOKEN or slug not in MA_SLUGS + (PO_TOKEN_SLUG,):
        return None
    try:
        async with _client() as client:
            response = await client.get(f"{SUPERVISOR_URL}/addons/{slug}/info",
                                        headers={"Authorization": "Bearer " + TOKEN})
        if response.status_code != 200:
            return None
        data = response.json().get("data")
        return data if isinstance(data, dict) else None
    except (httpx.HTTPError, ValueError, AttributeError):
        return None


async def find_music_assistant(use_cache=True) -> dict | None:
    """Locate the installed MA app; prefer a started one."""
    global _cache
    if use_cache and _cache and time.monotonic() - _cache[0] < _CACHE_SECONDS:
        return _cache[1]
    found = None
    for slug in MA_SLUGS:
        info = await app_info(slug)
        if not info or not info.get("version"):
            continue
        ingress = info.get("ingress_url") or ""
        candidate = {"slug": slug, "state": info.get("state", ""),
                     "ingress_url": ingress if INGRESS_URL.match(ingress) else ""}
        if candidate["state"] == "started":
            found = candidate
            break
        found = found or candidate
    _cache = (time.monotonic(), found)
    return found


async def save_own_options(new_options: dict) -> bool:
    """Persist options through Supervisor; /data/options.json stays root-owned."""
    if not TOKEN:
        return False
    try:
        async with _client() as client:
            response = await client.post(f"{SUPERVISOR_URL}/addons/self/options",
                                         headers={"Authorization": "Bearer " + TOKEN},
                                         json={"options": new_options})
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def po_token_status() -> dict:
    """Report whether MA's YT Music PO Token Generator app is installed and answering."""
    info = await app_info(PO_TOKEN_SLUG)
    reachable = False
    try:
        async with _client(timeout=3) as client:
            reachable = (await client.get(PO_TOKEN_PING_URL)).status_code == 200
    except httpx.HTTPError:
        pass
    installed = bool(info and info.get("version"))
    return {
        "known": available(),
        "installed": installed,
        "state": (info or {}).get("state", ""),
        "reachable": reachable,
        # Not installed yet: HA's store page for this app shows the Install button.
        "app_path": f"/config/app/{PO_TOKEN_SLUG}/info" + ("" if installed else "?store=true"),
        "server_url": "http://127.0.0.1:4416",
    }
