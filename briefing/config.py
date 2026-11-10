"""Alle Quellen und Einstellungen an einem Ort.

Nur frei zugängliche Quellen (keine Paywalls). Fällt eine Quelle aus,
bleibt nur ihr Beitrag leer, der Rest der Ausgabe wird trotzdem gebaut.
"""

TIMEZONE = "Europe/Berlin"

# Brandenburg an der Havel
LOCATION = {"name": "Brandenburg an der Havel", "lat": 52.4125, "lon": 12.5316}

# Ausgaben (Stunde in Berliner Zeit -> Name)
EDITIONS = {6: "Morgenausgabe", 13: "Mittagsausgabe", 19: "Abendausgabe"}
# Erste Ausgabe: Morgenausgabe an diesem Tag ist Nr. 1, danach drei Nummern pro Tag.
FIRST_ISSUE_DATE = "2026-11-06"

# Wie viele Meldungen pro Rubrik höchstens gezeigt werden (hält das Layout planbar).
# Profile (unten) überschreiben das pro Seite.
LIMITS = {"mlb": 7, "nba": 6, "gute": 6, "brandenburg": 7, "welt": 8, "longreads": 3}

# Wie alt eine Meldung höchstens sein darf (Stunden)
MAX_AGE_HOURS = {"mlb": 72, "nba": 48, "fussball": 48, "brandenburg": 48, "welt": 24, "longreads": 24 * 10,
                 "gute": 72, "wissen": 72, "verbraucher": 96, "jura": 96}

# Lieblingsteams: werden in der MLB-Rubrik nach oben sortiert
MLB_FAVORITES = {
    "padres": {"name": "Padres", "team_id": 135, "words": ["padres", "san diego"]},
    "athletics": {"name": "Athletics", "team_id": 133, "words": ["athletics", "a's", "oakland a", "sacramento a"]},
}

# Rubriken mit Spoiler-Schutz (nur Ergebnisse des Vortags werden verborgen)
SPOILER_SECTIONS = {"mlb", "nba"}

# Spalten-Rubriken unter dem Aufmacher (Reihenfolge = Reihenfolge auf der Seite)
COLUMNS = ["mlb", "nba", "gute"]

# Überschriften der Spalten-Rubriken
SECTION_INFO = {
    "mlb": {"title": "MLB", "sub": "Trades · Gerüchte · Verträge"},
    "nba": {"title": "NBA", "sub": "Trades · Gerüchte · Verträge"},
    "fussball": {"title": "Fußball", "sub": "Hertha BSC · Bundesliga · Champions League · 2. Liga"},
    "gute": {"title": "Gute Nachrichten", "sub": "Was heute gelingt", "empty": "Heute keine guten Nachrichten gefunden."},
    "wissen": {"title": "Wissen & Gesundheit", "sub": "Forschung · Medizin · Ernährung", "empty": "Heute keine Meldungen."},
    "verbraucher": {"title": "Verbraucher", "sub": "Tests · Rechte · Haushalt", "empty": "Heute keine Meldungen."},
    "jura": {"title": "Recht", "sub": "Urteile · Gesetze · Gerichte", "empty": "Heute keine Meldungen."},
}

# --- Quellen (frei zugänglich) ---

WELT_FEEDS = [
    {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss"},
    {"name": "BBC", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Deutschlandfunk", "url": "https://www.deutschlandfunk.de/nachrichten-100.rss"},
]
BRANDENBURG_FEEDS = [
    {"name": "rbb24", "url": "https://www.rbb24.de/aktuell/index.xml/feed=rss.xml"},
]
GUTE_FEEDS = [
    {"name": "Squirrel News", "url": "https://squirrel-news.net/feed/"},
    {"name": "Positive News", "url": "https://www.positive.news/feed/"},
    {"name": "Good News Network", "url": "https://www.goodnewsnetwork.org/feed/"},
]
WISSEN_FEEDS = [
    {"name": "Spektrum", "url": "https://www.spektrum.de/alias/rss/spektrum-de-rss-feed/996406"},
    {"name": "Quarks", "url": "https://www.quarks.de/feed/"},
    {"name": "NDR Gesundheit", "url": "https://www.ndr.de/ratgeber/gesundheit/index-rss.xml"},
]
VERBRAUCHER_FEEDS = [
    {"name": "Verbraucherzentrale", "url": "https://www.verbraucherzentrale.de/aktuelle-meldungen/feed"},
    {"name": "Stiftung Warentest", "url": "https://www.test.de/rss/alles/"},
    {"name": "NDR Ratgeber", "url": "https://www.ndr.de/ratgeber/verbraucher/index-rss.xml"},
]
JURA_FEEDS = [
    {"name": "LTO", "url": "https://www.lto.de/rss/feed.xml"},
    {"name": "BGH", "url": "https://www.bundesgerichtshof.de/DE/Service/RSSFeed/Function/RSS_PM.xml"},
    {"name": "BVerfG", "url": "https://www.bundesverfassungsgericht.de/SiteGlobals/Functions/RSSFeed/DE/RSSNewsticker/RSSNewsticker_Presse.xml"},
    {"name": "Verfassungsblog", "url": "https://verfassungsblog.de/feed/"},
]
# Wirtschaftslastige Verbraucher-Meldungen rutschen nach hinten (Ulrike: weniger Finanzen)
FINANCE_WORDS = ["aktie", "börse", "etf", "depot", "dax", "zins", "kredit", "anleihe", "fonds", "rendite",
                 "geldanlage", "sparbuch", "tagesgeld", "festgeld", "krypto", "bitcoin", "steuererklärung"]

# "tag": grobe Einordnung als Hinweis für Claude; "sport" wird zusätzlich auf MLB/NBA-Spoiler geprüft
LONGREADS_ADRIAN = [
    {"name": "FanGraphs", "url": "https://www.fangraphs.com/blogs/feed/", "tag": "sport"},
    {"name": "Spielverlagerung", "url": "https://spielverlagerung.de/feed/", "tag": "sport"},
    {"name": "The Guardian US Sport", "url": "https://www.theguardian.com/sport/us-sport/rss", "tag": "sport"},
    {"name": "JSTOR Daily", "url": "https://daily.jstor.org/feed/", "tag": "geschichte"},
    {"name": "Smithsonian", "url": "https://www.smithsonianmag.com/rss/history/", "tag": "geschichte"},
    {"name": "The Guardian Long Read", "url": "https://www.theguardian.com/news/series/the-long-read/rss"},
    {"name": "ProPublica", "url": "https://www.propublica.org/feeds/propublica/main", "tag": "investigativ"},
    {"name": "CORRECTIV", "url": "https://correctiv.org/feed/", "tag": "investigativ"},
    {"name": "Rest of World", "url": "https://restofworld.org/feed/latest", "tag": "technik"},
    {"name": "Atlas Obscura", "url": "https://www.atlasobscura.com/feeds/latest", "tag": "reisen"},
    {"name": "Aeon", "url": "https://aeon.co/feed.rss"},
    {"name": "Quanta Magazine", "url": "https://www.quantamagazine.org/feed/", "tag": "wissenschaft"},
]
# Reihenfolge = Ulrikes Interessen (gilt, wenn Claude nicht verfügbar ist)
LONGREADS_ULRIKE = [
    {"name": "Quanta Magazine", "url": "https://www.quantamagazine.org/feed/", "tag": "wissenschaft"},
    {"name": "Knowable Magazine", "url": "https://knowablemagazine.org/rss", "tag": "wissenschaft"},
    {"name": "Yale Environment 360", "url": "https://e360.yale.edu/feed.xml", "tag": "klima"},
    {"name": "ProPublica", "url": "https://www.propublica.org/feeds/propublica/main", "tag": "investigativ"},
    {"name": "CORRECTIV", "url": "https://correctiv.org/feed/", "tag": "investigativ"},
    {"name": "Psyche", "url": "https://psyche.co/feed", "tag": "psychologie"},
    {"name": "Undark", "url": "https://undark.org/feed/", "tag": "wissenschaft"},
    {"name": "The Guardian Long Read", "url": "https://www.theguardian.com/news/series/the-long-read/rss"},
    {"name": "Aeon", "url": "https://aeon.co/feed.rss", "tag": "philosophie"},
    {"name": "JSTOR Daily", "url": "https://daily.jstor.org/feed/", "tag": "geschichte"},
    {"name": "Atlas Obscura", "url": "https://www.atlasobscura.com/feeds/latest", "tag": "reisen"},
]

FEEDS = {
    "mlb": [
        {"name": "MLB Trade Rumors", "url": "https://www.mlbtraderumors.com/feed"},
        {"name": "MLB Trade Rumors", "url": "https://www.mlbtraderumors.com/san-diego-padres/feed"},
        {"name": "MLB Trade Rumors", "url": "https://www.mlbtraderumors.com/oakland-athletics/feed"},
    ],
    "nba": [
        {"name": "Hoops Rumors", "url": "https://www.hoopsrumors.com/feed"},
    ],
    "gute": GUTE_FEEDS,
    "brandenburg": BRANDENBURG_FEEDS,
    "welt": WELT_FEEDS,
    "longreads": LONGREADS_ADRIAN,
}

# Fußball (Hertha, Ligen) ist abgeschaltet, seit "Gute Nachrichten" die Spalte übernommen hat.
# Zum Wiedereinschalten: "fussball" in COLUMNS, LIMITS und FEEDS aufnehmen (Feeds siehe FUSSBALL_FEEDS).
FUSSBALL_FEEDS = [
    {"name": "kicker", "url": "https://newsfeed.kicker.de/team/hertha-bsc", "tag": "Hertha"},
    {"name": "kicker", "url": "https://newsfeed.kicker.de/news/bundesliga", "league": "Bundesliga"},
    {"name": "kicker", "url": "https://newsfeed.kicker.de/news/2-bundesliga", "league": "2. Bundesliga"},
    {"name": "kicker", "url": "https://newsfeed.kicker.de/news/champions-league", "league": "Champions League"},
    {"name": "rbb24 Sport", "url": "https://www.rbb24.de/sport/index.xml/feed=rss.xml"},
]

# Tagesschau-API (frei, JSON). regions=4 ist Brandenburg.
TAGESSCHAU = {
    "brandenburg": "https://www.tagesschau.de/api2u/news/?regions=4",
    "welt": "https://www.tagesschau.de/api2u/news/?ressort=ausland",
}

# Begriffe für Brandenburg-Meldungen aus gemischten Feeds (rbb24 deckt auch Berlin ab)
BRANDENBURG_WORDS = [
    "brandenburg", "potsdam", "havel", "cottbus", "frankfurt (oder)", "oranienburg",
    "eberswalde", "neuruppin", "rathenow", "premnitz", "werder", "falkensee", "lausitz",
    "uckermark", "prignitz", "barnim", "oberhavel", "spreewald", "teltow", "fläming",
    "landtag", "woidke", "märkisch",
]
LOCAL_WORDS = ["brandenburg an der havel", "brandenburg/havel", "havelstadt", "plaue", "kirchmöser"]

HERTHA_WORDS = ["hertha", "herthaner", "olympiastadion"]

OPENLIGADB = "https://api.openligadb.de"
HERTHA_TEAM_NAMES = ["hertha bsc", "hertha"]
# Ligen mit Ergebnissen (OpenLigaDB-Kürzel). Die Champions League wird pro Saison automatisch gesucht.
FOOTBALL_LEAGUES = [
    {"shortcut": "bl1", "label": "Bundesliga", "short": "1. BL"},
    {"shortcut": "bl2", "label": "2. Bundesliga", "short": "2. BL"},
]
# Höchstens so viele Hertha-Meldungen oben in der Fußball-Rubrik, danach wechseln sich die Ligen ab
HERTHA_MAX_NEWS = 2
# Höchstens so viele Spiele pro Liga (nur Spiele von gestern und heute werden gezeigt)
FOOTBALL_MAX_MATCHES = 5

# Spielberichte (mit Ergebnissen) liegen auf der eigenen Recap-Seite, verlinkt in MLB und NBA
SPORT_RECAP_URL = "https://nuggethuntera.github.io/sport-recap/"

# Longreads: Adrians Interessen, wichtigstes zuerst. Claude nutzt die Reihenfolge bei der Auswahl.
# Leer = neutrale Auswahl (gut geschrieben, substanziell, aktuell).
LONGREAD_INTERESTS: list[str] = [
    "Sport-Hintergründe (Baseball, Basketball, Fußball)",
    "Geschichte",
    "Internationale Politik & Konflikte",
    "Menschen & Reportagen aus dem Alltag",
    "Investigative Recherchen",
    "Deutschland & Europa",
    "Technik & KI",
    "Reisen & besondere Orte",
    "Kultur, Medien, Film & Musik",
    "Wirtschaft & Unternehmen",
    "Psychologie & Gesundheit",
    "Klima, Umwelt & Natur",
    "Wissenschaft & Forschung (Physik, Biologie, Mathematik)",
    "Philosophie & Ideen",
]

USER_AGENT = "Mozilla/5.0 (compatible; PersonalBriefing/1.0; private use)"

# Wer die Seite liest (für Claude-Prompt, Grüße und Kopfzeile)
READER = "Adrian"
DATELINE_NOTE = "Spoilerfrei für MLB & NBA"
# Alltagskasten (Pollen, UV, Sonne, Feiertage, Schulferien) beim Wetter zeigen
ALLTAG = False
# Unterordner der Seite (leer = Startseite), daraus ergibt sich der Link
PATH = ""

# --- Profile: eine Seite pro Person. "adrian" ist der Stand oben, andere Profile überschreiben Werte. ---
PROFILES: dict[str, dict] = {
    "adrian": {},
    "ulrike": {
        "READER": "Ulrike",
        "PATH": "ulrike",
        "DATELINE_NOTE": "Wissen · Verbraucher · Recht",
        "ALLTAG": True,
        "SPOILER_SECTIONS": set(),
        "COLUMNS": ["wissen", "verbraucher", "jura", "gute"],
        "LIMITS": {"wissen": 6, "verbraucher": 6, "jura": 6, "gute": 6, "brandenburg": 7, "welt": 8, "longreads": 3},
        "FEEDS": {
            "wissen": WISSEN_FEEDS,
            "verbraucher": VERBRAUCHER_FEEDS,
            "jura": JURA_FEEDS,
            "gute": GUTE_FEEDS,
            "brandenburg": BRANDENBURG_FEEDS,
            "welt": WELT_FEEDS,
            "longreads": LONGREADS_ULRIKE,
        },
        "TAGESSCHAU": {
            "brandenburg": TAGESSCHAU["brandenburg"],
            "welt": TAGESSCHAU["welt"],
            "wissen": "https://www.tagesschau.de/api2u/news/?ressort=wissen",
        },
        # Ulrikes Ranking, wichtigstes zuerst
        "LONGREAD_INTERESTS": [
            "Wissenschaft & Forschung (Physik, Biologie, Mathematik)",
            "Klima, Umwelt & Natur",
            "Investigative Recherchen",
            "Psychologie & Gesundheit",
            "Deutschland & Europa",
            "Internationale Politik & Konflikte",
            "Philosophie & Ideen",
            "Geschichte",
            "Reisen & besondere Orte",
            "Wirtschaft & Unternehmen",
            "Menschen & Reportagen aus dem Alltag",
            "Technik & KI",
            "Kultur, Medien, Film & Musik",
            "Sport-Hintergründe (Baseball, Basketball, Fußball)",
        ],
    },
}


def use(name: str) -> None:
    """Profil aktivieren: überschreibt die Werte oben (alle Module lesen config.X erst beim Aufruf)."""
    if name not in PROFILES:
        raise SystemExit(f"Unbekanntes Profil: {name} (vorhanden: {', '.join(PROFILES)})")
    keys = {k for p in PROFILES.values() for k in p}
    _DEFAULTS.update({k: globals()[k] for k in keys if k not in _DEFAULTS})
    globals().update(_DEFAULTS)
    globals().update(PROFILES[name])


_DEFAULTS: dict = {}
