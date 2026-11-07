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

# Wie viele Meldungen pro Rubrik höchstens gezeigt werden (hält das Layout planbar)
LIMITS = {"mlb": 7, "nba": 6, "fussball": 8, "brandenburg": 7, "welt": 8, "longreads": 3}

# Wie alt eine Meldung höchstens sein darf (Stunden)
MAX_AGE_HOURS = {"mlb": 72, "nba": 48, "fussball": 48, "brandenburg": 48, "welt": 24, "longreads": 24 * 10}

# Lieblingsteams: werden in der MLB-Rubrik nach oben sortiert
MLB_FAVORITES = {
    "padres": {"name": "Padres", "team_id": 135, "words": ["padres", "san diego"]},
    "athletics": {"name": "Athletics", "team_id": 133, "words": ["athletics", "a's", "oakland a", "sacramento a"]},
}

# Rubriken mit Spoiler-Schutz (nur Ergebnisse des Vortags werden verborgen)
SPOILER_SECTIONS = {"mlb", "nba"}

FEEDS = {
    "mlb": [
        {"name": "MLB Trade Rumors", "url": "https://www.mlbtraderumors.com/feed"},
        {"name": "MLB Trade Rumors", "url": "https://www.mlbtraderumors.com/san-diego-padres/feed"},
        {"name": "MLB Trade Rumors", "url": "https://www.mlbtraderumors.com/oakland-athletics/feed"},
    ],
    "nba": [
        {"name": "Hoops Rumors", "url": "https://www.hoopsrumors.com/feed"},
    ],
    "fussball": [
        {"name": "kicker", "url": "https://newsfeed.kicker.de/team/hertha-bsc", "tag": "Hertha"},
        {"name": "kicker", "url": "https://newsfeed.kicker.de/news/bundesliga", "league": "Bundesliga"},
        {"name": "kicker", "url": "https://newsfeed.kicker.de/news/2-bundesliga", "league": "2. Bundesliga"},
        {"name": "kicker", "url": "https://newsfeed.kicker.de/news/champions-league", "league": "Champions League"},
        {"name": "rbb24 Sport", "url": "https://www.rbb24.de/sport/index.xml/feed=rss.xml"},
    ],
    "brandenburg": [
        {"name": "rbb24", "url": "https://www.rbb24.de/aktuell/index.xml/feed=rss.xml"},
    ],
    "welt": [
        {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss"},
        {"name": "BBC", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
        {"name": "Deutschlandfunk", "url": "https://www.deutschlandfunk.de/nachrichten-100.rss"},
    ],
    # "tag": grobe Einordnung als Hinweis für Claude; "sport" wird zusätzlich auf MLB/NBA-Spoiler geprüft
    "longreads": [
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
    ],
}

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
HERTHA_MAX_NEWS = 3

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
