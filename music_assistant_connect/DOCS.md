# Music Assistant Connect — gebruikershandleiding

Dit is een **experimentele, niet-officiële Home Assistant-app**, niet verbonden aan Music Assistant of de streamproviders.

## Gebruik (ook op je telefoon)

1. Voeg de app-repository `https://github.com/Kevin2296/music-assistant-connect-ha` toe bij **Home Assistant → Instellingen → Apps → App store → ⋮ → Repositories**.
2. Installeer **Music Assistant Connect**, start de app en schakel **Weergeven in zijbalk** in.
3. Open **Music Connect** via de Home Assistant Companion-app op je telefoon. Geen aparte PWA, extensie of TrueNAS vereist.
4. Vul het bereikbare Music Assistant-adres en een geldig Music Assistant API-token in. Het token blijft in de tijdelijke browsersessie.
5. Selecteer de dienst; volg de Music Assistant-koppelstappen. Voor YouTube Music, SoundCloud en Deezer is optioneel een tijdelijke browser voor cookie-/tokenhulp beschikbaar.

## Privacy en veiligheidsgrenzen

- Alle webverzoeken moeten via **Home Assistant Ingress** komen; er is geen zelfstandig wachtwoord of open netwerkpoort. Home Assistant verzorgt de gebruikersauthenticatie.
- Het paneel is standaard alleen beschikbaar voor Home Assistant-beheerders.
- Er kan tegelijk één tijdelijke browser actief zijn, maximaal 15 minuten, afgeschermd op basis van de Home Assistant-gebruiker.
- Wachtwoorden en muziekcookies worden niet bewust permanent opgeslagen; ze kunnen wel tijdelijk in het RAM van de app zitten.
- De browser draait op de Home Assistant-host, niet letterlijk op de telefoon. Deze browser kan door providers worden geblokkeerd; YouTube Music kan aanvullende PO-tokeninrichting vereisen.
- Music Assistant-API en providerflows verschillen per versie. **Deze app is niet live met alle diensten of een HAOS-imagebuild gevalideerd.** Test eerst in je eigen omgeving.
- Gebruik uitsluitend accounts waar je bevoegd toe bent. Deel nooit persoonlijke cookies, Google-wachtwoorden of HA-toegangstokens via issues op GitHub.

## Vereisten

Home Assistant OS met apps, x86-64 of ARM64. Minstens voldoende schijfruimte/RAM voor een Chromium-image. Music Assistant bereikbaar via het lokale netwerk. Geen ondersteuning voor Home Assistant Container.