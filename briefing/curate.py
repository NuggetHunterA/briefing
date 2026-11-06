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

FOOTBALL_WORDS = re.compile(r"hertha|union|fußball|bundesliga|energie cottbus|babelsberg|turbine|dfb|kicker", re.I)


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
                keep.append(it)
            items = newest_first(keep)
            items.sort(key=lambda x: not x["hertha"])
        elif section == "welt":
            items = round_robin(items)
        elif section == "longreads":
            # keine Podcasts, Videos oder Audio-Beiträge
            items = [it for it in items if not re.search(r"podcast|/videos?/|/audio/", it["title"] + " " + it["url"], re.I)]
            items = newest_first(items)
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


def order_by(items: list[dict], ids: list[str]) -> list[dict]:
    if not ids:
        return items
    pos = {i: n for n, i in enumerate(ids)}
    chosen = [it for it in items if it["id"] in pos]
    chosen.sort(key=lambda x: pos[x["id"]])
    rest = [it for it in items if it["id"] not in pos]
    return chosen + rest


def fallback_longreads(items: list[dict], exclude: set[str]) -> list[dict]:
    picks, used_sources = [], set()
    for it in newest_first(items):
        if it["id"] in exclude or it["source"] in used_sources:
            continue
        picks.append({**it, "why": ""})
        used_sources.add(it["source"])
        if len(picks) == config.LIMITS["longreads"]:
            break
    return picks
