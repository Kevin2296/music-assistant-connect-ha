# Music Assistant Connect — gebruikershandleiding

Dit is een **experimentele, niet-officiële Home Assistant-app**, niet verbonden aan Music Assistant of de streamproviders.

## Gebruik (ook op je telefoon)

1. Voeg de app-repository `https://github.com/Kevin2296/music-assistant-connect-ha` toe bij **Home Assistant → Instellingen → Apps → App store → ⋮ → Repositories**.
2. Installeer **Music Assistant Connect**, start de app en schakel **Weergeven in zijbalk** in.
3. Open **Music Connect** via de Home Assistant Companion-app op je telefoon. Geen aparte PWA, extensie of TrueNAS vereist.
4. Open eerst **Instellingen → Apps → Music Assistant Connect → Configuratie**. Vul `ma_url` (intern adres, bijvoorbeeld `http://192.168.1.50:8095`) en `ma_token` (Music Assistant-token via **Instellingen → Profiel**, met rechten voor providerbeheer) in. Opslaan en herstarten. Dit is geen Home Assistant-token. Zonder deze opties kun je nog handmatig verbinden; de pagina bewaart die invoer niet in browseropslag.
5. Selecteer de dienst; volg de Music Assistant-koppelstappen. Voor YouTube Music, SoundCloud en Deezer is optioneel een tijdelijke browser voor cookie-/tokenhulp beschikbaar.

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

Niet automatisch: cookies uitlezen uit een andere browser/app of extern tabblad. Same-origin-beveiliging en HttpOnly-cookies staan dit niet toe. Een gewone inloglink naar YouTube/SoundCloud geeft deze app dus geen toegang tot die sessie. Er is geen bypass voor Google-blokkades, CAPTCHA of 2FA. Gebruik bij blokkade de providerhandleiding en handmatige invoer; op een telefoon kan daarvoor alsnog een computer nodig zijn. Cookies kunnen verlopen. YouTube Music vereist Premium en een passende PO Token Generator; die wordt niet door deze app geïnstalleerd. OAuth-callbacks zijn eigendom van MA en moeten bereikbaar zijn zoals MA/provider dit vereist; deze app herschrijft geen redirectadressen.

## Leeg koppelscherm

In 0.3.0 werd een geldig HTTP-formulier met `result: null` onterecht tot `null` teruggebracht. Dit is in 0.4.0 hersteld. Werk de app bij en herstart. Blijft een stap onbeschikbaar, controleer dan MA-versie/tokenrechten en open de eigen MA-providerinstellingen. De automatische tests simuleren MA; ze bewijzen geen geslaagde aanmelding bij echte muziekdiensten of jouw DuckDNS-installatie.

## Geraadpleegde bronnen

- [HA Ingress](https://contributors.home-assistant.io/apps/guides/ingress/) en [appopties](https://contributors.home-assistant.io/apps/reference/configuration/)
- [MA HTTP API](https://www.music-assistant.io/api/) en [providerflows](https://developers.music-assistant.io/setup-flows/)
- [MA HTTP response-implementatie](https://github.com/music-assistant/server/blob/dev/music_assistant/controllers/webserver/controller.py), [frontendroutes](https://github.com/music-assistant/frontend/blob/main/src/plugins/router.ts)
- [YouTube Music](https://www.music-assistant.io/music-providers/youtube-music/) en [SoundCloud](https://www.music-assistant.io/music-providers/soundcloud/)
