"""Daten abholen: RSS-Feeds, Tagesschau, MLB Stats API, OpenLigaDB, Open-Meteo."""

from __future__ import annotations

import calendar
import hashlib
import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from . import config

log = logging.getLogger("briefing")

session = requests.Session()
session.headers["User-Agent"] = config.USER_AGENT
TIMEOUT = 20


def get(url: str, **kw) -> requests.Response | None:
    try:
        r = session.get(url, timeout=TIMEOUT, **kw)
        r.raise_for_status()
        return r
    except Exception as e:  # noqa: BLE001 - eine kaputte Quelle darf nie den Build stoppen
        log.warning("Quelle nicht erreichbar: %s (%s)", url, e)
        return None


TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def clean(text: str | None, limit: int = 400) -> str:
    if not text:
        return ""
    text = html.unescape(TAG_RE.sub(" ", text))
    text = WS_RE.sub(" ", text).strip()
    # Feed-Floskeln am Ende entfernen
    text = re.sub(r"\s*(Continue reading|Read more|Weiterlesen|mehr)\s*\.{0,3}\s*$", "", text, flags=re.I)
    text = re.sub(r"\s*The post .{5,300}? appeared first on .{2,60}?\.?\s*$", "", text)  # WordPress-Floskel
    text = re.sub(r"^(\d{1,2}:\d{2} ?[ap]m( [A-Z]{2,3})?:\s*)", "", text)  # "12:03 pm CT:" in Live-Updates
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + " …"
    return text


def item_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:10]


def _image(entry) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        media = entry.get(key) or []
        best = None
        for m in media:
            url = m.get("url")
            if not url:
                continue
            width = int(m.get("width") or 0)
            if best is None or width > best[0]:
                best = (width, url)
        if best:
            return best[1]
    for enc in entry.get("enclosures") or []:
        if (enc.get("type") or "").startswith("image") and enc.get("href"):
            return enc["href"]
    m = re.search(r'<img[^>]+src="([^"]+)"', entry.get("summary", "") or "")
    return m.group(1) if m else None


def _published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
    return None


def fetch_feed(src: dict, section: str) -> list[dict]:
    r = get(src["url"])
    if r is None:
        return []
    feed = feedparser.parse(r.content)
    items = []
    for e in feed.entries:
        link = e.get("link")
        title = clean(e.get("title"), 220)
        if not link or not title:
            continue
        items.append({
            "id": item_id(link),
            "section": section,
            "source": src["name"],
            "tag": src.get("tag"),
            "league": src.get("league"),
            "title": title,
            "summary": clean(e.get("summary") or e.get("description")),
            "url": link,
            "image": _image(e),
            "published": _published(e),
            "categories": [t.get("term", "") for t in e.get("tags", []) if t.get("term")],
        })
    log.info("%-12s %-28s %3d Einträge  %s", section, src["name"], len(items), src["url"])
    return items


def fetch_tagesschau(url: str, section: str) -> list[dict]:
    r = get(url)
    if r is None:
        return []
    items = []
    for n in r.json().get("news", []):
        link = n.get("shareURL") or n.get("detailsweb")
        if not link or n.get("type") not in (None, "story"):
            continue
        img = None
        variants = (n.get("teaserImage") or {}).get("imageVariants") or {}
        for k in ("16x9-960", "16x9-640", "16x9-1280", "1x1-640"):
            if variants.get(k):
                img = variants[k]
                break
        pub = None
        if n.get("date"):
            try:
                pub = datetime.fromisoformat(n["date"]).astimezone(timezone.utc)
            except ValueError:
                pass
        items.append({
            "id": item_id(link),
            "section": section,
            "source": "tagesschau",
            "tag": n.get("topline"),
            "title": clean(n.get("title"), 220),
            "summary": clean(n.get("firstSentence") or ""),
            "url": link,
            "image": img,
            "published": pub,
            "categories": [t.get("tag", "") for t in n.get("tags", [])],
        })
    log.info("%-12s %-28s %3d Einträge", section, "tagesschau", len(items))
    return items


def fetch_all_news() -> dict[str, list[dict]]:
    jobs = []
    for section, feeds in config.FEEDS.items():
        for src in feeds:
            jobs.append((fetch_feed, src, section))
    for section, url in config.TAGESSCHAU.items():
        jobs.append((fetch_tagesschau, url, section))
    out: dict[str, list[dict]] = {s: [] for s in config.LIMITS}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for res in pool.map(lambda j: j[0](j[1], j[2]), jobs):
            for it in res:
                out[it["section"]].append(it)
    return out


# --- MLB Stats API: offizielle Transaktionen (enthalten keine Spielergebnisse) ---

TRANSACTION_TYPES = {
    "TR": "Trade", "SFA": "Free Agent", "SGN": "Vertrag", "CLW": "Waiver-Claim",
    "REL": "Entlassen", "DES": "Designated", "OUT": "Outright", "RET": "Rücktritt",
    "DFA": "Free Agency",
}
FA_RE = re.compile(r"^(.*?) elected free agency\.?$", re.I)
BORING_TYPES = {"SC", "ASG", "OPT", "CU", "RTN", "DFA_N", "NUM"}


def fetch_mlb_transactions(now: datetime, days: int = 4) -> list[dict]:
    start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")
    r = get(f"https://statsapi.mlb.com/api/v1/transactions?sportId=1&startDate={start}&endDate={end}")
    if r is None:
        return []
    fav_ids = {f["team_id"]: key for key, f in config.MLB_FAVORITES.items()}
    out = []
    for t in r.json().get("transactions", []):
        code = t.get("typeCode", "")
        desc = t.get("description")
        if not desc or code in BORING_TYPES:
            continue
        # Minor-League-Kleinkram nur bei Lieblingsteams
        team_ids = {(t.get("toTeam") or {}).get("id"), (t.get("fromTeam") or {}).get("id")}
        fav = next((fav_ids[i] for i in team_ids if i in fav_ids), None)
        major = code in TRANSACTION_TYPES
        if not major and not fav:
            continue
        out.append({
            "date": t.get("date") or t.get("effectiveDate"),
            "type": TRANSACTION_TYPES.get(code, t.get("typeDesc", "")),
            "code": code,
            "text": desc,
            "favorite": fav,
        })
    # "X elected free agency" desselben Teams und Tages zu einer Zeile zusammenfassen
    grouped, fa, seen = [], {}, set()
    for t in out:
        if t["text"] in seen:  # Trades stehen bei beiden Teams
            continue
        seen.add(t["text"])
        m = FA_RE.match(t["text"])
        if m and t["favorite"]:
            key = (t["favorite"], t["date"])
            if key in fa:
                fa[key]["names"].append(m.group(1))
                continue
            t = {**t, "names": [m.group(1)]}
            fa[key] = t
        grouped.append(t)
    for t in grouped:
        if t.get("names"):
            team = config.MLB_FAVORITES[t["favorite"]]["name"]
            names = t.pop("names")
            t["text"] = f'{team}: {", ".join(names)} {"ist" if len(names) == 1 else "sind"} Free Agent.'
    out = grouped
    # Trades und Lieblingsteams zuerst, dann nach Datum
    out.sort(key=lambda x: x["date"] or "", reverse=True)
    out.sort(key=lambda x: (x["favorite"] is None, x["code"] != "TR"))
    log.info("mlb          MLB Stats API Transaktionen  %3d", len(out))
    return out[:8]


# --- OpenLigaDB: Hertha-Kasten und Ligen-Übersicht (Fußball: Spoiler erlaubt) ---

def _is_hertha(name: str | None) -> bool:
    return bool(name) and any(w in name.lower() for w in config.HERTHA_TEAM_NAMES)


def _season(now: datetime) -> int:
    return now.year if now.month >= 7 else now.year - 1


def _league_data(shortcut: str, season: int) -> tuple[list, list]:
    """Tabelle und alle Spiele einer Saison (beides darf leer sein)."""
    t = get(f"{config.OPENLIGADB}/getbltable/{shortcut}/{season}")
    m = get(f"{config.OPENLIGADB}/getmatchdata/{shortcut}/{season}")
    table = (t.json() or []) if t is not None else []
    matches = (m.json() or []) if m is not None else []
    return table, matches


def _hertha_box(label: str, table: list, matches: list) -> dict | None:
    pos = next((i for i, row in enumerate(table) if _is_hertha(row.get("teamName"))), None)
    if pos is None:
        return None
    lo = max(0, min(pos - 2, len(table) - 5))
    rows = [{
        "rank": i + 1,
        "team": row.get("shortName") or row.get("teamName"),
        "games": row.get("matches"),
        "diff": row.get("goalDiff"),
        "points": row.get("points"),
        "hertha": i == pos,
    } for i, row in enumerate(table) if lo <= i < lo + 5]
    last = nxt = None
    mine = [x for x in matches if _is_hertha(x["team1"]["teamName"]) or _is_hertha(x["team2"]["teamName"])]
    mine.sort(key=lambda x: x.get("matchDateTimeUTC") or "")
    done = [x for x in mine if x.get("matchIsFinished")]
    todo = [x for x in mine if not x.get("matchIsFinished")]
    if done:
        last = _match(done[-1])
    if todo:
        nxt = _match(todo[0])
    return {"league": label, "rank": pos + 1, "table": rows, "last": last, "next": nxt}


def _round_view(label: str, short: str, table: list, matches: list, german: set[str] | None = None) -> dict | None:
    """Letzter gespielter Spieltag (alle Ergebnisse), nächster Spieltag und Tabellenspitze."""
    if not matches:
        return None
    groups: dict[int, list] = {}
    for x in matches:
        groups.setdefault((x.get("group") or {}).get("groupOrderID") or 0, []).append(x)
    played = [g for g, xs in groups.items() if any(x.get("matchIsFinished") for x in xs)]
    upcoming = [g for g, xs in groups.items() if any(not x.get("matchIsFinished") for x in xs)]
    last_g = max(played) if played else None
    next_g = min((g for g in upcoming if last_g is None or g > last_g), default=None)

    def view(g):
        if g is None:
            return None
        xs = sorted(groups[g], key=lambda x: x.get("matchDateTimeUTC") or "")
        ms = [_match(x) for x in xs]
        for mm, x in zip(ms, xs):
            names = (x["team1"]["teamName"], x["team2"]["teamName"])
            mm["hertha"] = any(_is_hertha(n) for n in names)
            mm["german"] = bool(german) and any(n in german for n in names)
        # Hertha zuerst, in der Champions League die deutschen Klubs
        ms.sort(key=lambda mm: (not mm["hertha"], not mm["german"]))
        start = min((mm["when"] for mm in ms if mm["when"]), default=None)
        return {"name": ms[0]["matchday"] if ms else "", "matches": ms, "start": start}

    last, nxt = view(last_g), view(next_g)
    top = [{"rank": i + 1, "team": r.get("shortName") or r.get("teamName"), "points": r.get("points"),
            "hertha": _is_hertha(r.get("teamName"))} for i, r in enumerate(table[:3])]
    return {"label": label, "short": short, "last": last, "next": nxt, "top": top}


def _find_cl(season: int) -> str | None:
    """Kürzel der Champions League bei OpenLigaDB suchen (wechselt je Saison)."""
    r = get(f"{config.OPENLIGADB}/getavailableleagues")
    if r is None:
        return None
    for lg in r.json() or []:
        name = (lg.get("leagueName") or "").lower()
        if (str(lg.get("leagueSeason")) == str(season) and "champions league" in name
                and not any(w in name for w in ("frauen", "women", "youth", "uefa youth"))):
            log.info("fussball     OpenLigaDB CL-Kürzel: %s (%s)", lg.get("leagueShortcut"), lg.get("leagueName"))
            return lg.get("leagueShortcut")
    log.info("fussball     OpenLigaDB: keine Champions League für Saison %s gefunden", season)
    return None


def fetch_football(now: datetime) -> dict:
    """Hertha-Kasten plus Ergebnisse aus 1. Bundesliga, 2. Bundesliga und Champions League."""
    season = _season(now)
    leagues = [(lg["shortcut"], lg["label"], lg["short"]) for lg in config.FOOTBALL_LEAGUES]
    cl = _find_cl(season)
    if cl:
        leagues.append((cl, "Champions League", "CL"))
    with ThreadPoolExecutor(max_workers=3) as pool:
        data = list(pool.map(lambda lg: _league_data(lg[0], season), leagues))
    hertha, rounds = None, []
    german = {row.get("teamName") for sc, (table, _) in zip(leagues, data) if sc[0] in ("bl1", "bl2") for row in table}
    for (shortcut, label, short), (table, matches) in zip(leagues, data):
        if hertha is None and shortcut in ("bl1", "bl2"):
            hertha = _hertha_box(label, table, matches)
            if hertha:
                log.info("fussball     OpenLigaDB %s Hertha Platz %d", shortcut, hertha["rank"])
        rv = _round_view(label, short, table, matches, german if shortcut == cl else None)
        log.info("fussball     OpenLigaDB %-8s %3d Spiele, %3d Tabellenzeilen", shortcut, len(matches), len(table))
        if rv:
            rounds.append(rv)
    return {"hertha": hertha, "leagues": rounds}


def _match(x: dict) -> dict:
    res = None
    for r in x.get("matchResults") or []:
        if r.get("resultTypeID") == 2 or r.get("resultName") == "Endergebnis":
            res = f'{r["pointsTeam1"]}:{r["pointsTeam2"]}'
    when = x.get("matchDateTimeUTC")
    return {
        "home": x["team1"].get("shortName") or x["team1"]["teamName"],
        "away": x["team2"].get("shortName") or x["team2"]["teamName"],
        "result": res,
        "when": datetime.fromisoformat(when.replace("Z", "+00:00")) if when else None,
        "matchday": (x.get("group") or {}).get("groupName"),
    }


# --- Wetter: Open-Meteo (DWD ICON) + DWD-Warnungen über Bright Sky ---

def fetch_weather() -> dict | None:
    loc = config.LOCATION
    r = get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": loc["lat"], "longitude": loc["lon"], "timezone": config.TIMEZONE,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,relative_humidity_2m,is_day",
            "hourly": "temperature_2m,precipitation_probability,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,sunrise,sunset,uv_index_max",
            "forecast_days": 4, "wind_speed_unit": "kmh",
        },
    )
    if r is None:
        return None
    data = r.json()
    alerts = []
    a = get("https://api.brightsky.dev/alerts", params={"lat": loc["lat"], "lon": loc["lon"]})
    if a is not None:
        for al in a.json().get("alerts", []):
            alerts.append({"headline": al.get("headline_de") or al.get("event_de"), "severity": al.get("severity")})
    data["alerts"] = alerts
    return data
