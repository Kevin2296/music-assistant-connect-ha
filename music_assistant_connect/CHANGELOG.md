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
