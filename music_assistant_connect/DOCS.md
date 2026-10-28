# Music Assistant Connect — gebruikershandleiding

Dit is een **experimentele, niet-officiële Home Assistant-app**, niet verbonden aan Music Assistant of de streamproviders.

## Gebruik (ook op je telefoon)

1. Voeg de app-repository `https://github.com/Kevin2296/music-assistant-connect-ha` toe bij **Home Assistant → Instellingen → Apps → App store → ⋮ → Repositories**.
2. Installeer **Music Assistant Connect**, start de app en schakel **Weergeven in zijbalk** in.
3. Open **Music Connect** via de Home Assistant Companion-app op je telefoon. Geen aparte PWA, extensie of TrueNAS vereist.
4. Tik bij stap 1 op **Koppel met Music Assistant** (zie hieronder). Draait MA niet als app op deze HA, open dan **Handmatig verbinden** of vul bij **Configuratie** `ma_url` (bijvoorbeeld `http://192.168.1.50:8095`) en `ma_token` (MA-token via **Instellingen → Profiel**) in. Dit is geen Home Assistant-token. Handmatige invoer bewaart de pagina niet in browseropslag.
5. Selecteer de dienst; volg de Music Assistant-koppelstappen. Voor YouTube Music, SoundCloud en Deezer is optioneel een tijdelijke browser voor cookie-/tokenhulp beschikbaar.

## Koppel met Music Assistant (0.6.0)

- **Adres automatisch.** Standaard gebruikt de app `http://172.30.32.1:8095`: de Music Assistant-app draait op het hostnetwerk en is vanuit deze app via dat interne adres bereikbaar. Met `hassio_api` vraagt de app Supervisor alleen de openbare app-informatie van `d5369777_music_assistant` (of beta/nightly) op, zodat ook de snelkoppeling `ma_ui_url` automatisch klopt. Een zelf ingevuld `ma_url` of `ma_ui_url` gaat altijd voor.
- **Token in één tik.** De pagina stuurt via de bestaande Home Assistant-ingress van MA (zelfde HA-adres, jouw HA-login) één verzoek `auth/token/create` met de naam *Music Assistant Connect*. Dat is hetzelfde wat je in MA onder **Instellingen → Profiel** met de hand doet. De app controleert het token bij MA en bewaart het via Supervisor in de eigen appconfiguratie; het komt daarna nooit meer terug naar de pagina en wordt niet gelogd. Intrekken kan in MA onder **Instellingen → Profiel**.
- **Waarom niet volledig automatisch?** MA vertrouwt aanmeldingen via ingress alleen als ze rechtstreeks van Supervisor komen, en het token dat MA aan de HA-integratie geeft is alleen voor HA Core leesbaar. Een andere app kan dus legitiem geen MA-token voor je ophalen. Daarom één tik, met jou als bevestiging.
- Werkt het niet (bijvoorbeeld MA nog nooit geopend, of een oudere MA-versie zonder gebruikersbeheer), dan opent **Handmatig verbinden** met uitleg.
- Het Supervisor-token van deze app wordt bij het opstarten uit de omgevingsvariabelen gehaald, zodat de tijdelijke browser het niet erft.

## YouTube Music zo eenvoudig mogelijk

MA's YouTube Music-provider ondersteunt alleen een aanmeldcookie, geen OAuth of koppelcode. Daarnaast is de app **YT Music PO Token Generator** (`d5369777_ytm_po_token_generator`, uit dezelfde repository als Music Assistant) nodig. De wizard controleert of die app geïnstalleerd is en op poort 4416 antwoordt. Zo niet, dan opent **Open PO Token Generator** direct de juiste app-pagina; tik daar op **Installeren** en **Starten** en kom terug. Het veld `po_token_server_url` blijft `http://127.0.0.1:4416` (MA en de generator delen het hostnetwerk). Een leeg gebruikersnaamveld wordt met je HA-naam gevuld; dat veld telt alleen bij een merkaccount (21 cijfers).

Daarna: **Inloggen bij YouTube Music**, zelf inloggen in de tijdelijke browser, **Haal mijn gegevens op**, **Opslaan en koppelen**. Als Google het inloggen weigert ("deze browser of app is mogelijk niet veilig"), toont de app dat meteen. Dat is een beveiliging van Google die deze app bewust niet omzeilt. Alternatieven: later opnieuw proberen, eenmalig de MA-handleiding op een computer volgen, of een dienst met officiële koppeling kiezen (Spotify, Tidal).

## SoundCloud

Ontbreekt na ophalen nog iets, dan zegt de app precies wat: het OAuth-token (nog niet ingelogd) of de Client ID (speel een nummer af of zoek iets). Na een volledige vondst springt het scherm naar **Opslaan en koppelen**.

## Privacy en veiligheidsgrenzen

- Alle webverzoeken moeten via **Home Assistant Ingress** komen; er is geen zelfstandig wachtwoord of open netwerkpoort. Home Assistant verzorgt de gebruikersauthenticatie.
- Het paneel is standaard alleen beschikbaar voor Home Assistant-beheerders.
- Het vooraf ingestelde API-token staat in de Supervisor-appconfiguratie, wordt niet aan de pagina teruggegeven en kan in HA-back-ups terechtkomen. Beveilig die back-ups. Het appconfiguratiescherm maskeert het token; dat is geen afzonderlijke versleutelingsgarantie. Alle beheerders met toegang tot deze app kunnen de ingestelde MA-rechten gebruiken.
- Er kan tegelijk één tijdelijke browser actief zijn, maximaal 15 minuten, afgeschermd op basis van de Home Assistant-gebruiker.
- Wachtwoorden en muziekcookies worden niet bewust permanent opgeslagen; ze kunnen wel tijdelijk in het RAM van de app zitten.
- De browser draait op de Home Assistant-host, niet letterlijk op de telefoon. Deze browser kan door providers worden geblokkeerd; YouTube Music kan aanvullende PO-tokeninrichting vereisen.
- Music Assistant-API en providerflows verschillen per versie. **Deze app is niet live met alle diensten of een HAOS-imagebuild gevalideerd.** Test eerst in je eigen omgeving.
- Gebruik uitsluitend accounts waar je bevoegd toe bent. Deel nooit persoonlijke cookies, Google-wachtwoorden of HA-toegangstokens via issues op GitHub.

## Vereisten

Home Assistant OS met apps, x86-64 of ARM64. Minstens voldoende schijfruimte/RAM voor een Chromium-image. Music Assistant bereikbaar via het lokale netwerk. Geen ondersteuning voor Home Assistant Container.

## DuckDNS / HTTPS en snelkoppelingen

Open je **bestaande HTTPS Home Assistant-adres** en kies Music Connect in de zijbalk. Ingress werkt via dezelfde toegang, ook in de Companion-app buiten je wifi. DuckDNS alleen verzorgt de naam; HTTPS en je bestaande HA-aanmelding blijven vereist. Je hoeft voor deze app of MA geen extra poort door te sturen. Het interne `ma_url` blijft hetzelfde: de appserver spreekt MA aan, de telefoon alleen HA. Publieke adressen blijven bewust geweigerd als doel van de API-proxy.

De oude aanduiding “Lokaal” betekende interne MA-toegang, geen beperking tot je wifi. Alle appverzoeken blijven relatief aan het tijdelijke Ingress-pad. Bij 403: open opnieuw vanuit de HA-zijbalk, niet via een bewaarde tijdelijke Ingress-URL. Je bestaande HA reverse proxy moet HA en eventueel WebSockets correct doorgeven; schakel TLS-controle of Ingress-authenticatie niet uit.

Optioneel `ma_ui_url`: kopieer het pad van je Music Assistant-paneel, bijvoorbeeld `/hassio/ingress/JOUW_MA_APP_SLUG` (vervang de placeholder door je echte paneelpad). De app opent dan MA via dezelfde HA-host; ga daar naar **Instellingen → Muziekproviders** of **Instellingen → Profiel**. Gebruik geen tijdelijk `/api/hassio_ingress/...`-adres. We raden geen vaste appslug: die verschilt per installatie/kanaal.

Heb je al een apart beveiligd HTTPS-adres voor MA, dan mag dat als `ma_ui_url`, bijvoorbeeld `https://music.example.nl`. Dan verschijnen ook directe links naar providers, profiel/API-token en `/api-docs`. Dit opent alleen navigatie en stuurt geen API-token mee. MA handelt zijn eigen login af. Deze optie maakt geen nieuwe proxy of publieke toegang aan. Bij een afwijkende MA-versie kun je altijd de knop **Open Music Assistant** gebruiken.

## Wat kan automatisch?

- De vooraf ingestelde verbinding wordt automatisch getest. Providerformulieren worden uit de actuele MA-setupflow opgebouwd; de app verzint geen OAuth-client of koppelcodes.
- Je kiest zelf de tijdelijke browser en logt zelf in. Bij YouTube Music, SoundCloud en Deezer kunnen geschikte cookies/tokens uit **die eigen tijdelijke sessie** worden overgenomen. Velden worden exact gekoppeld, bestaande invoer blijft behouden, en je bevestigt zelf het opslaan in MA.
- SoundCloud vereist zowel Client ID als Authorization. Bij een gedeeltelijke vondst blijft de browser open. Een geplakt OAuth-token krijgt indien nodig `OAuth ` als voorvoegsel.
- Knoppen **Plak uit klembord** lezen alleen na een klik en browsertoestemming. Als HTTPS, iframebeleid of de Companion-app dit blokkeert: houd het veld ingedrukt en plak handmatig.

Niet automatisch: cookies uitlezen uit een andere browser/app of extern tabblad. Same-origin-beveiliging en HttpOnly-cookies staan dit niet toe. Een gewone inloglink naar YouTube/SoundCloud geeft deze app dus geen toegang tot die sessie. Er is geen bypass voor Google-blokkades, CAPTCHA of 2FA. Gebruik bij blokkade de providerhandleiding en handmatige invoer; op een telefoon kan daarvoor alsnog een computer nodig zijn. Cookies kunnen verlopen. YouTube Music vereist Premium en de YT Music PO Token Generator; deze app controleert die en verwijst ernaar, maar installeert of start hem niet zelf (daarvoor zijn ruimere Supervisor-rechten nodig). OAuth-callbacks zijn eigendom van MA en moeten bereikbaar zijn zoals MA/provider dit vereist; deze app herschrijft geen redirectadressen.

## Leeg koppelscherm

In 0.3.0 werd een geldig HTTP-formulier met `result: null` onterecht tot `null` teruggebracht. Dit is in 0.4.0 hersteld. Werk de app bij en herstart. Blijft een stap onbeschikbaar, controleer dan MA-versie/tokenrechten en open de eigen MA-providerinstellingen. De automatische tests simuleren MA; ze bewijzen geen geslaagde aanmelding bij echte muziekdiensten of jouw DuckDNS-installatie.

## Appconfiguratie kon niet worden geladen

Werk bij naar **0.4.1** en herstart. In 0.4.0 probeerde de app de beschermde `/data/options.json` als `pwuser` te lezen; Supervisor maakt dit bestand als root met alleen leestoegang voor de eigenaar. Vanaf 0.4.1 leest de opstartroutine de instellingen eerst en schakelt vervolgens naar `pwuser`, zonder extra groepen, voordat de webserver of browser start. De instellingen blijven alleen in procesgeheugen; de bestandstoegangsrechten worden niet verruimd. Na gewijzigde configuratie moet je opnieuw herstarten.

Zie je een andere naam zoals `Phoscon-GW` in het serverveld, dan is dat geen geldig MA-basisadres. Controleer of je browser/wachtwoordmanager automatisch gegevens van een andere app heeft ingevuld. Gebruik het volledige Music Assistant-adres inclusief `http://` en poort, of stel het vooraf in bij Configuratie.

## Tijdelijke browser: cookieknoppen en browserondersteuning

Vanaf **0.4.2** zijn er knoppen **Omhoog scrollen**, **Omlaag scrollen** en **Beeld verversen**. Je kunt ook het muiswiel binnen het browserbeeld gebruiken. Scroll naar de cookieknoppen en maak zelf een keuze; de app accepteert geen cookies namens je. Het beeld wordt iedere twee seconden vernieuwd zolang de app zichtbaar is en de browser actief is.

Versies tot 0.4.1 gebruikten de vereenvoudigde headless-shellbrowser, die door YouTube Music als niet-ondersteund kan worden gezien. Vanaf 0.4.2 draait volledige Chromium op een tijdelijk virtueel scherm, met de echte browseridentiteit. Je hoeft op het getoonde scherm dus geen Chrome te downloaden. Dit is geen omzeiling van CAPTCHA, 2FA of Googles blokkade van geautomatiseerde aanmeldingen: als Google vervolgens inloggen weigert, is de automatische route niet beschikbaar. De Linux-test controleert echte browserbediening met een lokale cookiedialoog, geen succesvolle Google-aanmelding.

## Gewone browser met ingebouwde cookie-extensie (0.5.0, experimenteel)

Je kunt deze methode volledig vanuit de HA-app bedienen. De extensie draait **in de tijdelijke browser op de HA-server**, niet in de Companion-app of je telefoonbrowser. Er hoeft op je telefoon niets geïnstalleerd te worden.

Klik **Inloggen bij …** (vóór 0.6.0: *Inloggen zonder extensie*) om een gewone Chromium-sessie te openen. Je hoeft zelf geen extensie te installeren. Je logt zelf in en bedient zelf eventuele verificaties. Klikken, typen, scrollen en slepen worden doorgegeven aan het tijdelijke bureaublad. Dit gebruikt geen browserautomatiseringsverbinding, aangepaste browseridentiteit of automatische aanmeldscripts. Klik vervolgens **Haal mijn gegevens op** om de meegeleverde cookie-extensie toestemming te geven de relevante gegevens uit die sessie over te nemen. Controleer de velden en bevestig het opslaan in MA.

De extensie heeft alleen toegang tot de gekozen provider en een tijdelijke lokale verbinding binnen de container. Browserprofiel en extensieconfiguratie staan in RAM onder `/dev/shm`; na sluiten/verlopen worden die verwijderd. Het huidige browseradres wordt bijgewerkt zonder queryparameters. De extensie krijgt geen toegang tot de cookies van je telefoon of je andere browsers. SoundCloud Client ID wordt waargenomen in de eigen providerverzoeken; het OAuth-token komt uit de eigen sessiecookie.

**Dit is nog geen bewezen oplossing voor Googles of SoundClouds blokkades.** Google kan ook deze sessie weigeren. SoundCloud kan een CAPTCHA tonen die je zelf moet voltooien en kan de sessie alsnog afwijzen. De app lost geen CAPTCHA/2FA op en gebruikt geen diensten om die te omzeilen. De integratietest gebruikt een echte browser en extensie met een kunstmatige testcookie; er zijn geen echte provideraccounts mee aangemeld.

## Bronnen

- [Playwright: Chromium en de headless shell](https://playwright.dev/docs/browsers)
- [Playwright: volledige browser op Linux met een virtueel scherm](https://playwright.dev/python/docs/ci#running-headed)

- [HA Ingress](https://contributors.home-assistant.io/apps/guides/ingress/) en [appopties](https://contributors.home-assistant.io/apps/reference/configuration/)
- [MA HTTP API](https://www.music-assistant.io/api/) en [providerflows](https://developers.music-assistant.io/setup-flows/)
- [MA HTTP response-implementatie](https://github.com/music-assistant/server/blob/dev/music_assistant/controllers/webserver/controller.py), [frontendroutes](https://github.com/music-assistant/frontend/blob/main/src/plugins/router.ts)
- [YouTube Music](https://www.music-assistant.io/music-providers/youtube-music/) en [SoundCloud](https://www.music-assistant.io/music-providers/soundcloud/)
