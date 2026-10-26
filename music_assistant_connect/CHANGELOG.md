# 0.4.0

- Fixed empty provider wizard: MA HTTP responses are bare steps with `result: null`; preserve the whole step instead of treating it as a message envelope.
- Configure `ma_url`, `ma_token`, and `ma_ui_url` before opening the app. Configured tokens remain server-side and cannot be redirected by a browser request.
- Clarified DuckDNS/HTTPS Ingress access; preserved the socket peer used for Ingress authentication by disabling Uvicorn proxy-header rewriting.
- Added MA navigation, clipboard paste with manual fallback, exact credential field matching, and SoundCloud authorization normalization.
- Keep SoundCloud's temporary browser open until both required values are found. Preserve previously entered form fields when filling captured values.
- Added regression tests and clearer API permission/version failures.
