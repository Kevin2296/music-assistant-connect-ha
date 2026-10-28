# 0.6.3

- One tap on a field in the browser image now also opens the phone keyboard; no separate tap on the typing field. The typing row sits directly under the browser image.

# 0.6.2

- Live keyboard for the temporary browser: each character goes straight to the page, in order. Backspace on an empty field and Enter/Tab are forwarded; the separate "Typ" button is gone. After tapping in the image while typing, the phone keyboard stays open.
- Explain Google's passkey/security-key screen (it cannot use the phone's passkey): tap Cancel, then "Try another way" and choose password or a phone prompt.

# 0.6.1

- Open the YT Music PO Token Generator at its current Home Assistant path `/config/app/<slug>/info` instead of the old `/hassio/addon/...` path, with `?store=true` while it is not installed so the Install button shows.

# 0.6.0 (experimental)

- Default `ma_url` to `http://172.30.32.1:8095` (MA app on the host network) and derive `ma_ui_url` from the installed MA app via Supervisor (`hassio_api`, default role, read-only app info). Configured values still win.
- Add one-tap "Koppel met Music Assistant": the page asks MA for a long-lived token through MA's own HA ingress with the signed-in HA user (`auth/token/create`), the server verifies it and stores it via Supervisor (`/addons/self/options`). The token is never returned to the page or logged. Manual connection stays available under "Handmatig verbinden".
- YouTube Music: check whether the YT Music PO Token Generator app is installed and answers on port 4416, with a direct link to install/start it. Prefill an empty username. Explain plainly when Google refuses sign-in in the server browser; no workaround is attempted.
- SoundCloud/Deezer/YouTube Music: name the exact missing value and the next step after a partial capture; jump to "Opslaan en koppelen" after a full capture. Rename the browser button to "Inloggen bij <dienst>".
- Remove the Supervisor token from the process environment at startup so Chromium and Xvfb do not inherit it.
- Add tests for linking, Supervisor lookups, token storage, PO token status and hints, plus a browser smoke test of the one-tap flow. Not yet validated on a real HAOS installation.

# 0.5.1

- Remove synchronous pointer-movement waits from manual browser controls; clicks and wheel events no longer depend on a fresh movement notification. Test repeated clicks at the same coordinates against real Chromium.
- Add "Terug naar muziekdienst" to return to the selected provider after account security pages, preserving the temporary login session. Navigation destinations are fixed by the app, not supplied by arbitrary clients.
- Log the app version on startup and log input timeout action types without text, coordinates, URLs or credentials. Allow longer typed text to finish within its own bounded timeout.

# 0.5.0 (experimental)

- Add a human-operated Chromium session without WebDriver/DevTools, embedded through the existing HA screenshot interface. No browser-identity spoofing or automated sign-in.
- Bundle a session-local cookie extension on the HA server. No phone/desktop extension installation is needed. Export happens only after the authenticated user requests it; the extension can only contact a random, nonce-protected loopback bridge.
- Limit extension cookie/network permissions to the selected provider. Temporary browser profiles and extension configuration live in RAM (/dev/shm) and are removed on close or expiry.
- Add manual drag input for sliders and other UI controls. CAPTCHA/2FA remain user actions; challenges are not solved automatically.
- Show the temporary browser's current address, excluding query parameters in manual mode.
- Add real Chromium/extension tests using synthetic cookies, and authorization tests for the local bridge. These do not verify Google/SoundCloud sign-in or solve their anti-bot checks.

# 0.4.2

- Replace Chromium's headless shell with full Chromium on a temporary virtual display, using its real browser identity. This addresses browser compatibility; Google may still refuse automated sign-in.
- Add scroll buttons and mouse-wheel control for long pages and nested cookie-consent dialogs. Cookie choices remain with the user.
- Refresh the browser image automatically while visible; ignore stale image responses after closing a session.
- Treat PO token server URL fields as URLs rather than passwords.
- Add Linux tests using the actual production browser/display, plus scroll authorization and mobile UI checks. No Google account login is claimed by these tests.

# 0.4.1

- Read Home Assistant's root-owned mode-0600 options file during startup, then drop all supplementary groups and switch to pwuser before starting HTTP or Chromium. Keep credentials only in memory; do not weaken Supervisor file permissions.
- Explain configuration-read failures and discourage unrelated password-manager autofill in connection fields.
- Add bootstrap tests and a Linux integration check using an actual root-owned options file and privilege change.

# 0.4.0

- Fixed empty provider wizard: MA HTTP responses are bare steps with `result: null`; preserve the whole step instead of treating it as a message envelope.
- Configure `ma_url`, `ma_token`, and `ma_ui_url` before opening the app. Configured tokens remain server-side and cannot be redirected by a browser request.
- Clarified DuckDNS/HTTPS Ingress access; preserved the socket peer used for Ingress authentication by disabling Uvicorn proxy-header rewriting.
- Added MA navigation, clipboard paste with manual fallback, exact credential field matching, and SoundCloud authorization normalization.
- Keep SoundCloud's temporary browser open until both required values are found. Preserve previously entered form fields when filling captured values.
- Added regression tests and clearer API permission/version failures.
