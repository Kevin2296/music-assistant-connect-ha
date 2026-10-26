# Music Assistant Connect

> **Experimenteel communityproject** — Home Assistant-app met een telefoonvriendelijke interface om muziekdiensten aan Music Assistant te koppelen. Niet officieel van Music Assistant, Google, SoundCloud of Deezer.

## Waarom?

Koppel Music Assistant-providers direct vanuit de **Home Assistant-app op je telefoon**. Geen aparte PWA, browserextensie, TrueNAS-installatie of open webpoort nodig: de interface draait via [Home Assistant Ingress](https://developers.home-assistant.io/docs/apps/presentation/#ingress).

- Ondersteunt Music Assistant-koppelstappen voor meerdere providers (o.a. Spotify, Tidal, Qobuz en Apple Music; afhankelijk van je MA-versie).
- Experimentele tijdelijke browser voor het verzamelen van SoundCloud-, Deezer- en YouTube Music-gegevens, zonder extensie op de telefoon.
- Ingress-login van Home Assistant, geen aparte appaccounts.
- Tijdelijke browsersessies worden na 15 minuten gesloten. Geen bewuste permanente opslag van streamcookies.

## Installeren

1. Open Home Assistant → **Instellingen → Apps → App store → ⋮ → Repositories**.
2. Voeg toe: `https://github.com/Kevin2296/music-assistant-connect-ha`
3. Installeer **Music Assistant Connect** en start hem.
4. Schakel **Weergeven in zijbalk** in; open **Music Connect** op je telefoon via de Home Assistant Companion-app.
5. Vul vooraf bij **Configuratie** `ma_url` en `ma_token` in (intern Music Assistant-adres en MA-token met providerbeheerrechten), sla op en herstart. Het token blijft op de server. Handmatige invoer in de app blijft mogelijk.
6. Stel optioneel `ma_ui_url` in op je HA Music Assistant-paneelpad of bestaand HTTPS MA-adres voor snelkoppelingen. Kies de provider en volg de wizard.

Ook buiten je wifi: open je bestaande **DuckDNS/HTTPS Home Assistant-toegang** en kies Music Connect in de zijbalk. Het interne MA-adres hoeft niet vanaf je telefoon bereikbaar te zijn. Geen extra portforwarding nodig. Zie de [handleiding](music_assistant_connect/DOCS.md) voor veilige navigatie en de grenzen van automatisch cookies koppelen.

**Vereist:** Home Assistant OS met app-ondersteuning (`amd64`/`aarch64`) en een bereikbare Music Assistant-server. De ingebouwde browser vraagt relatief veel geheugen. Geen ondersteuning op Home Assistant Container.

## Status

**v0.5.0 – experimenteel.** De tijdelijke browser draait nu als een gewone Chromium-sessie met een meegeleverde cookie-extensie op de HA-server. Je bedient hem vanuit HA, inclusief slepen; er is geen extensie op je telefoon nodig. Een test met echte browser/extensie en kunstmatige cookies controleert de overdracht. Dit bewijst geen succesvolle Google/SoundCloud-aanmelding of CAPTCHA-afhandeling. Providers kunnen ook deze browser blokkeren. De Docker-build op jouw HAOS-installatie en echte provideraccounts zijn niet live gevalideerd. YouTube Music vereist nog steeds een passende PO Token Generator.

Zie [documentatie](music_assistant_connect/DOCS.md) voor beperkingen, veiligheid en het gebruik. Deel geen credentials of cookies in openbare issues.

## Testen

```sh
python -m pip install -r music_assistant_connect/requirements.txt pytest pytest-asyncio pyyaml
python -m pytest -q music_assistant_connect/tests
```

## Licentie

MIT – zie [LICENSE](LICENSE).
