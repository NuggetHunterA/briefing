"""Alltagskasten: Pollenflug (DWD), UV-Index und Sonne (aus dem Wetter), Feiertage und Schulferien in Brandenburg."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from . import config, sources

log = logging.getLogger("briefing")

POLLEN_URL = "https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json"
POLLEN_REGION = "Brandenburg"  # DWD-Region "Brandenburg und Berlin" (region_id 50)
SCHOOL_URL = "https://openholidaysapi.org/SchoolHolidays"

# DWD-Belastungsstufen -> (Rang, Text)
POLLEN_LEVELS = {
    "0": (0, "keine"), "0-1": (1, "kaum"), "1": (2, "gering"), "1-2": (3, "gering bis mittel"),
    "2": (4, "mittel"), "2-3": (5, "mittel bis hoch"), "3": (6, "hoch"),
}


def fetch(now: datetime) -> dict:
    """Rohdaten holen. Fällt eine Quelle aus, fehlt nur ihr Teil."""
    out: dict = {"pollen": None, "school": []}
    r = sources.get(POLLEN_URL)
    if r is not None:
        try:
            for reg in r.json().get("content", []):
                if POLLEN_REGION.lower() in (reg.get("region_name") or "").lower():
                    out["pollen"] = reg.get("Pollen")
                    break
        except ValueError:
            pass
    today = now.date()
    r = sources.get(SCHOOL_URL, params={
        "countryIsoCode": "DE", "subdivisionCode": "DE-BB", "languageIsoCode": "DE",
        "validFrom": today.isoformat(), "validTo": (today + timedelta(days=366)).isoformat(),
    }, headers={"accept": "text/json"})
    if r is not None:
        try:
            for h in r.json() or []:
                name = next((n.get("text") for n in h.get("name", []) if n.get("language") == "DE"), None)
                out["school"].append({"name": name or "Ferien", "start": h.get("startDate"), "end": h.get("endDate")})
        except ValueError:
            pass
    log.info("alltag       Pollen %s, %d Ferienzeiträume", "ok" if out["pollen"] else "fehlt", len(out["school"]))
    return out


def easter(year: int) -> date:
    """Ostersonntag (Gaußsche Osterformel, anonymer gregorianischer Algorithmus)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def holidays(year: int) -> list[tuple[date, str]]:
    """Gesetzliche Feiertage in Brandenburg (inkl. Oster- und Pfingstsonntag)."""
    e = easter(year)
    return sorted([
        (date(year, 1, 1), "Neujahr"),
        (e - timedelta(days=2), "Karfreitag"),
        (e, "Ostersonntag"),
        (e + timedelta(days=1), "Ostermontag"),
        (date(year, 5, 1), "Tag der Arbeit"),
        (e + timedelta(days=39), "Christi Himmelfahrt"),
        (e + timedelta(days=49), "Pfingstsonntag"),
        (e + timedelta(days=50), "Pfingstmontag"),
        (date(year, 10, 3), "Tag der Deutschen Einheit"),
        (date(year, 10, 31), "Reformationstag"),
        (date(year, 12, 25), "1. Weihnachtstag"),
        (date(year, 12, 26), "2. Weihnachtstag"),
    ])


def next_holiday(today: date) -> dict:
    d, name = next((d, n) for d, n in holidays(today.year) + holidays(today.year + 1) if d >= today)
    return {"date": d, "name": name, "days": (d - today).days}


def moon_phase(today: date) -> str:
    """Grobe Mondphase aus dem synodischen Monat (Referenz-Neumond 6.1.2000)."""
    age = ((today - date(2000, 1, 6)).days + 0.5) % 29.530588
    for limit, name in ((1.8, "Neumond"), (5.5, "zunehmende Sichel"), (9.2, "erstes Viertel"),
                        (12.9, "zunehmender Mond"), (16.6, "Vollmond"), (20.3, "abnehmender Mond"),
                        (24.0, "letztes Viertel"), (27.7, "abnehmende Sichel"), (99, "Neumond")):
        if age < limit:
            return name
    return ""


def uv_label(uv: float | None) -> str:
    if uv is None:
        return ""
    for limit, text in ((3, "niedrig"), (6, "mäßig"), (8, "hoch"), (11, "sehr hoch")):
        if uv < limit:
            return text
    return "extrem"


def _school_view(school: list[dict], today: date) -> dict | None:
    for h in sorted(school, key=lambda x: x.get("start") or ""):
        try:
            start, end = date.fromisoformat(h["start"]), date.fromisoformat(h["end"])
        except (TypeError, ValueError, KeyError):
            continue
        if end < today:
            continue
        name = h["name"].strip()
        if start <= today:
            return {"name": name, "now": True, "end": end}
        return {"name": name, "now": False, "start": start, "end": end, "days": (start - today).days}
    return None


def view(raw: dict | None, weather: dict | None, now: datetime) -> dict:
    """Fertige Werte für die Seite. Morgens zählt 'heute', ab 19 Uhr beim Pollenflug 'morgen'."""
    raw = raw or {}
    today = now.date()
    out: dict = {"holiday": next_holiday(today), "moon": moon_phase(today)}

    pollen = raw.get("pollen") or {}
    key = "tomorrow" if now.hour >= 19 else "today"
    active = []
    for name, vals in pollen.items():
        rank, text = POLLEN_LEVELS.get(str((vals or {}).get(key, "0")), (0, ""))
        if rank > 0:
            active.append({"name": name, "rank": rank, "text": text})
    active.sort(key=lambda x: -x["rank"])
    out["pollen"] = {"day": "morgen" if key == "tomorrow" else "heute", "top": active[:3], "known": bool(pollen)}

    days = (weather or {}).get("days") or []
    if days:
        d0 = days[0]
        out["uv"] = {"value": d0.get("uv"), "label": uv_label(d0.get("uv"))}
        rise, sset = d0.get("sunrise"), d0.get("sunset")
        if rise and sset:
            r, s = datetime.fromisoformat(rise), datetime.fromisoformat(sset)
            mins = int((s - r).total_seconds() // 60)
            out["sun"] = {"rise": r, "set": s, "length": f"{mins // 60} Std. {mins % 60} Min."}
            if len(days) > 1 and days[1].get("sunrise") and days[1].get("sunset"):
                r1, s1 = datetime.fromisoformat(days[1]["sunrise"]), datetime.fromisoformat(days[1]["sunset"])
                delta = int(round(((s1 - r1).total_seconds() - (s - r).total_seconds()) / 60))
                out["sun"]["delta"] = delta

    out["school"] = _school_view(raw.get("school") or [], today)
    return out
