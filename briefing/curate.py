"""Filtern, sortieren, Spoiler entfernen."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from . import config

log = logging.getLogger("briefing")

# Eindeutige Ergebnis-Muster: greifen immer
HARD_PATTERNS = [
    r"\b\d{1,3}\s*[-–]\s*\d{1,3}\b(?!\s*(?:year|yr|million|m\b|percent))",  # 5-3, 112-108 (keine Vertragslaufzeiten)
    r"\b(no-hitter|perfect game|shutout|grand slam|triple-double|double-double|buzzer-beater|overtime|extra innings)\b",
    r"\b(scored|scores|drops|dropped) \d+\b",
    r"\b\d+ (points|rebounds|assists|strikeouts|rbis?|hits|homers)\b",
    r"\b(recap|box score|final score|game \d|game one|game two|game three|game four|game five|game six|game seven|series lead|leads series|tied series)\b",
]
# Weiche Muster: nur wenn kein LLM verfügbar ist (sonst zu viele Fehlalarme wie "top prospect")
SOFT_PATTERNS = [
    r"\b(beat|beats|defeat|defeats|defeated|rout|routs|routed|outlast|outlasts|blank|blanks|blanked|stun|stuns|stunned)\b",
    r"\b(rally|rallies|rallied|comeback|walk-?off|walks off|sweep|sweeps|swept|clinch|clinches|clinched|eliminat\w*|advance[sd]? to|force[sd]? game)\b",
    r"\b(win|wins|won|lose|loses|lost|loss|victory|victories|triumph)\b(?!-now)",
    r"\b(winning|losing) streak\b",
    r"\b(last night|tonight's game|yesterday's game|monday's|tuesday's|wednesday's|thursday's|friday's|saturday's|sunday's) (game|loss|win|victory|defeat|contest|matchup)\b",
]
HARD_RE = re.compile("|".join(HARD_PATTERNS), re.I)
SOFT_RE = re.compile("|".join(SOFT_PATTERNS), re.I)

FOOTBALL_WORDS = re.compile(r"hertha|union|fußball|bundesliga|champions league|energie cottbus|babelsberg|turbine|dfb|kicker", re.I)


LEAGUE_WORDS = [
    ("Champions League", re.compile(r"champions league|königsklasse|\bcl\b", re.I)),
    ("2. Bundesliga", re.compile(r"2\. (fußball-)?bundesliga|zweite liga|zweitliga", re.I)),
    ("Bundesliga", re.compile(r"bundesliga", re.I)),
]


def league_of(txt: str) -> str | None:
    return next((name for name, rx in LEAGUE_WORDS if rx.search(txt)), None)


def football_mix(items: list[dict]) -> list[dict]:
    """Ein paar Hertha-Meldungen oben, danach Bundesliga, Champions League und 2. Liga im Wechsel."""
    hertha = [it for it in items if it["hertha"]][: config.HERTHA_MAX_NEWS]
    taken = {it["id"] for it in hertha}
    by_league: dict[str, list[dict]] = {"Bundesliga": [], "Champions League": [], "2. Bundesliga": [], "": []}
    for it in items:
        if it["id"] not in taken:
            by_league.setdefault(it.get("league") or "", []).append(it)
    rest = []
    while any(by_league.values()):
        for lg in by_league:
            if by_league[lg]:
                rest.append(by_league[lg].pop(0))
    return hertha + rest


def _text(it: dict) -> str:
    return f'{it["title"]} {it["summary"]}'


def spoiler_cutoff(now_local: datetime) -> datetime:
    """Ab hier gilt eine Meldung als 'Vortag oder neuer' und wird auf Spoiler geprüft."""
    return (now_local - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def needs_spoiler_check(it: dict, cutoff: datetime) -> bool:
    return it["section"] in config.SPOILER_SECTIONS and (it["published"] is None or it["published"] >= cutoff)


def rule_spoiler(it: dict, strict: bool) -> bool:
    t = _text(it)
    return bool(HARD_RE.search(t) or (strict and SOFT_RE.search(t)))


def favorite_of(it: dict) -> str | None:
    hay = (_text(it) + " " + " ".join(it.get("categories", []))).lower()
    for key, fav in config.MLB_FAVORITES.items():
        if any(w in hay for w in fav["words"]):
            return key
    return None


def is_finance(it: dict) -> bool:
    txt = _text(it).lower()
    return any(re.search(rf"\b{re.escape(w)}", txt) for w in config.FINANCE_WORDS)


def dedupe(items: list[dict]) -> list[dict]:
    seen_url, seen_title, out = set(), set(), []
    for it in items:
        key = re.sub(r"[^a-z0-9äöüß]", "", it["title"].lower())[:60]
        if it["url"] in seen_url or key in seen_title:
            continue
        seen_url.add(it["url"])
        seen_title.add(key)
        out.append(it)
    return out


def fresh(items: list[dict], section: str, now_utc: datetime) -> list[dict]:
    limit = now_utc - timedelta(hours=config.MAX_AGE_HOURS[section])
    return [it for it in items if it["published"] is None or it["published"] >= limit]


def newest_first(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda x: x["published"].timestamp() if x["published"] else 0, reverse=True)


def round_robin(items: list[dict]) -> list[dict]:
    """Quellen abwechseln, damit nicht eine Redaktion die Rubrik füllt."""
    by_src: dict[str, list[dict]] = {}
    for it in newest_first(items):
        by_src.setdefault(it["source"], []).append(it)
    out = []
    while any(by_src.values()):
        for src in list(by_src):
            if by_src[src]:
                out.append(by_src[src].pop(0))
    return out


def prepare(raw: dict[str, list[dict]], now_utc: datetime) -> dict[str, list[dict]]:
    out = {}
    for section, items in raw.items():
        items = dedupe(fresh(items, section, now_utc))
        if section == "mlb":
            for it in items:
                it["favorite"] = favorite_of(it)
            items = newest_first(items)
            items.sort(key=lambda x: x["favorite"] is None)
        elif section == "brandenburg":
            keep = []
            for it in items:
                txt = _text(it).lower()
                if it["source"] == "tagesschau" or any(w in txt for w in config.BRANDENBURG_WORDS):
                    it["local"] = any(w in txt for w in config.LOCAL_WORDS)
                    keep.append(it)
            items = newest_first(keep)
            items.sort(key=lambda x: not x.get("local"))
        elif section == "fussball":
            keep = []
            for it in items:
                txt = _text(it).lower()
                if it["source"].startswith("rbb") and not FOOTBALL_WORDS.search(txt):
                    continue
                it["hertha"] = it.get("tag") == "Hertha" or any(w in txt for w in config.HERTHA_WORDS)
                if not it.get("league"):
                    it["league"] = league_of(txt)
                keep.append(it)
            items = football_mix(newest_first(keep))
        elif section in ("welt", "gute", "wissen", "jura"):
            items = round_robin(items)
        elif section == "verbraucher":
            items = round_robin(items)
            items.sort(key=is_finance)  # Geld-Themen nach hinten, Reihenfolge sonst unverändert
        elif section == "longreads":
            # keine Podcasts, Videos oder Audio-Beiträge
            items = [it for it in items if not re.search(r"podcast|/videos?/|/audio/", it["title"] + " " + it["url"], re.I)]
            items = round_robin(items)  # jede Quelle kommt unter die Kandidaten, nicht nur die fleißigsten
        else:
            items = newest_first(items)
        out[section] = items
    return out


def apply_spoilers(sections: dict[str, list[dict]], llm_spoilers: set[str] | None, cutoff: datetime) -> dict[str, int]:
    """llm_spoilers=None heißt: kein LLM gelaufen, dann strenge Regeln."""
    strict = llm_spoilers is None
    llm_spoilers = llm_spoilers or set()
    hidden = {}
    for section in config.SPOILER_SECTIONS:
        keep, n = [], 0
        for it in sections.get(section, []):
            if needs_spoiler_check(it, cutoff) and (rule_spoiler(it, strict) or it["id"] in llm_spoilers):
                n += 1
                continue
            keep.append(it)
        sections[section] = keep
        hidden[section] = n
        log.info("Spoiler-Schutz %s: %d Meldungen verborgen", section, n)
    return hidden


def drop_sport_spoilers(items: list[dict], cutoff: datetime) -> list[dict]:
    """Sport-Longreads vom Vortag oder heute mit klaren Ergebnis-Mustern aussortieren (MLB/NBA spoilerfrei)."""
    keep = []
    for it in items:
        fresh_one = it["published"] is None or it["published"] >= cutoff
        if it.get("tag") == "sport" and fresh_one and rule_spoiler(it, strict=False):
            continue
        keep.append(it)
    return keep


def order_by(items: list[dict], ids: list[str]) -> list[dict]:
    if not ids:
        return items
    pos = {i: n for n, i in enumerate(ids)}
    chosen = [it for it in items if it["id"] in pos]
    chosen.sort(key=lambda x: pos[x["id"]])
    rest = [it for it in items if it["id"] not in pos]
    return chosen + rest


def fallback_longreads(items: list[dict], exclude: set[str]) -> list[dict]:
    """Ohne Claude: Quellen in der Reihenfolge aus config.FEEDS (nach den Interessen des Profils sortiert)."""
    rank = {f["name"]: i for i, f in enumerate(config.FEEDS["longreads"])}
    picks, used_sources = [], set()
    for it in sorted(newest_first(items), key=lambda x: rank.get(x["source"], 99)):
        if it["id"] in exclude or it["source"] in used_sources:
            continue
        picks.append({**it, "why": ""})
        used_sources.add(it["source"])
        if len(picks) == config.LIMITS["longreads"]:
            break
    return picks


# --- Wiederholungen über mehrere Tage ---
# Jede Ausgabe merkt sich in data.json ("shown"), welche Meldungen sie gezeigt hat und an welchem Tag zuerst.
# Was schon an einem früheren Tag zu sehen war, fliegt raus. Am selben Tag (Morgen, Mittag, Abend) bleibt alles stehen.

STOPWORDS = {"der", "die", "das", "und", "oder", "mit", "für", "von", "vom", "zum", "zur", "den", "dem", "des",
             "ein", "eine", "einen", "auf", "aus", "bei", "nach", "über", "wie", "was", "ist", "sind", "nicht",
             "the", "and", "for", "with", "from", "into", "after", "over", "how", "what", "why", "are", "was"}


def title_words(title: str) -> set[str]:
    words = re.findall(r"[a-z0-9äöüß]+", title.lower())
    return {w for w in words if (len(w) > 2 or w.isdigit()) and w not in STOPWORDS}


def similarity(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def shown_log(prev: dict, now_date: str) -> list[dict]:
    """Bisher gezeigte Meldungen der letzten Tage. Alte Ausgaben ohne "shown" liefern ihre Rubriken nach."""
    log_ = [x for x in prev.get("shown", []) if isinstance(x, dict) and x.get("id")]
    if prev.get("date"):
        log_ = remember(log_, prev.get("sections") or {}, prev["date"], now_date)
    return log_


def remember(log_: list[dict], sections: dict[str, list[dict]], date: str, now_date: str) -> list[dict]:
    """Gezeigte Meldungen eintragen (erster Tag bleibt), Einträge älter als REPEAT_DAYS verwerfen."""
    first = {x["id"]: x for x in log_}
    for section, items in sections.items():
        if section == "longreads":  # haben ihre eigene Liste (longread_history)
            continue
        for it in items:
            if it["id"] not in first:
                first[it["id"]] = {"id": it["id"], "d": date, "s": section, "title": it["title"]}
    oldest = (datetime.fromisoformat(now_date) - timedelta(days=config.REPEAT_DAYS)).date().isoformat()
    return [x for x in first.values() if x.get("d", "") >= oldest]


def seen_before(it: dict, earlier: list[dict], earlier_by_id: dict[str, dict]) -> bool:
    """Schon an einem früheren Tag gezeigt? Gleiche Adresse mit deutlich neuer Überschrift gilt als
    aktualisierte Meldung und darf wieder erscheinen. Fast gleiche Überschrift (80 % gleiche Wörter) unter neuer Adresse gilt als Wiederholung."""
    words = title_words(it["title"])
    old = earlier_by_id.get(it["id"])
    if old is not None:
        return similarity(words, title_words(old.get("title", ""))) >= 0.5
    return any(similarity(words, title_words(x.get("title", ""))) >= 0.8 for x in earlier)


def drop_repeats(sections: dict[str, list[dict]], log_: list[dict], today: str) -> dict[str, int]:
    """Meldungen von früheren Tagen entfernen. Bleiben in einer Rubrik zu wenige neue übrig,
    füllen Wiederholungen bis REPEAT_MIN_ITEMS auf (lieber eine bekannte Meldung als eine leere Spalte)."""
    earlier = [x for x in log_ if x.get("d", "") < today]
    by_id = {x["id"]: x for x in earlier}
    dropped = {}
    for section, items in sections.items():
        if section == "longreads" or not items:
            continue
        new, old = [], []
        for it in items:
            (old if seen_before(it, earlier, by_id) else new).append(it)
        if len(new) < config.REPEAT_MIN_ITEMS:
            new += old[: config.REPEAT_MIN_ITEMS - len(new)]
        sections[section] = new
        dropped[section] = len(items) - len(new)
        if dropped[section]:
            log.info("Wiederholungen %s: %d Meldungen von früheren Tagen ausgelassen", section, dropped[section])
    return dropped
