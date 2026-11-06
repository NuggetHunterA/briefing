"""HTML aus der Ausgabe erzeugen (Jinja2)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import config

TZ = ZoneInfo(config.TIMEZONE)
TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
WD_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]

# WMO-Wettercodes -> (Text, Symbol)
WMO = {
    0: ("Klar", "sun"), 1: ("Überwiegend klar", "sun-cloud"), 2: ("Teils bewölkt", "sun-cloud"),
    3: ("Bedeckt", "cloud"), 45: ("Nebel", "fog"), 48: ("Reifnebel", "fog"),
    51: ("Leichter Niesel", "drizzle"), 53: ("Niesel", "drizzle"), 55: ("Starker Niesel", "drizzle"),
    56: ("Gefrierender Niesel", "sleet"), 57: ("Gefrierender Niesel", "sleet"),
    61: ("Leichter Regen", "rain"), 63: ("Regen", "rain"), 65: ("Starker Regen", "rain"),
    66: ("Gefrierender Regen", "sleet"), 67: ("Gefrierender Regen", "sleet"),
    71: ("Leichter Schnee", "snow"), 73: ("Schnee", "snow"), 75: ("Starker Schnee", "snow"),
    77: ("Schneegriesel", "snow"), 80: ("Regenschauer", "rain"), 81: ("Regenschauer", "rain"),
    82: ("Heftige Schauer", "rain"), 85: ("Schneeschauer", "snow"), 86: ("Schneeschauer", "snow"),
    95: ("Gewitter", "storm"), 96: ("Gewitter mit Hagel", "storm"), 99: ("Gewitter mit Hagel", "storm"),
}
COMPASS = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]


def as_dt(v) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v)
        except ValueError:
            return None
    if v.tzinfo is None:
        v = v.replace(tzinfo=TZ)
    return v.astimezone(TZ)


def long_date(d: datetime) -> str:
    return f"{WEEKDAYS[d.weekday()]}, {d.day}. {MONTHS[d.month - 1]} {d.year}"


def make_env(now: datetime) -> Environment:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(), trim_blocks=True, lstrip_blocks=True)

    def ago(v):
        d = as_dt(v)
        if not d:
            return ""
        mins = int((now - d).total_seconds() // 60)
        if mins < 1:
            return "gerade eben"
        if mins < 60:
            return f"vor {mins} Min."
        if mins < 60 * 24:
            return f"vor {mins // 60} Std."
        if mins < 60 * 48:
            return "gestern"
        return f"{d.day}.{d.month}."

    def hhmm(v):
        d = as_dt(v)
        return d.strftime("%H:%M") if d else ""

    def short_day(v):
        d = as_dt(v)
        return f"{WD_SHORT[d.weekday()]} {d.day}.{d.month}." if d else ""

    def wx(code, field=0):
        return WMO.get(int(code or 0), ("—", "cloud"))[field]

    def compass(deg):
        return COMPASS[int(((deg or 0) + 22.5) // 45) % 8]

    def num(v, digits=0):
        return "–" if v is None else f"{round(v, digits):.{digits}f}".replace(".", ",")

    env.filters.update(ago=ago, hhmm=hhmm, short_day=short_day, wx=wx, compass=compass, num=num, dt=as_dt)
    env.globals.update(long_date=long_date, WD_SHORT=WD_SHORT)
    return env


def weather_view(w: dict | None, now: datetime) -> dict | None:
    if not w:
        return None
    hourly = w.get("hourly", {})
    hours = []
    for t, temp, pp, code in zip(hourly.get("time", []), hourly.get("temperature_2m", []),
                                 hourly.get("precipitation_probability", []), hourly.get("weather_code", [])):
        d = as_dt(t)
        if d and d >= now.replace(minute=0, second=0, microsecond=0) and len(hours) < 24:
            hours.append({"time": d, "temp": temp, "pp": pp or 0, "code": code})
    hours = hours[::2][:12]  # alle zwei Stunden
    temps = [h["temp"] for h in hours if h["temp"] is not None] or [0]
    lo, hi = min(temps), max(temps)
    for h in hours:
        h["y"] = 0.5 if hi == lo else (h["temp"] - lo) / (hi - lo)
    daily = w.get("daily", {})
    days = []
    for i, t in enumerate(daily.get("time", [])):
        days.append({
            "date": as_dt(t + "T12:00"),
            "code": daily["weather_code"][i],
            "max": daily["temperature_2m_max"][i],
            "min": daily["temperature_2m_min"][i],
            "pp": daily["precipitation_probability_max"][i],
            "rain": daily["precipitation_sum"][i],
            "sunrise": daily["sunrise"][i],
            "sunset": daily["sunset"][i],
            "uv": daily["uv_index_max"][i],
        })
    return {"current": w.get("current", {}), "hours": hours, "days": days, "alerts": w.get("alerts", [])}


MORNING_LINES = [
    "Erst mal Kaffee.", "Der Tag beginnt mit einer Tasse.", "Kaffee ist fertig, die Zeitung auch.",
    "Guten Morgen, Adrian.", "Noch fünf Minuten, dann geht's los.",
]
EVENING_LINES = [
    "Feierabend.", "Der Tag ist gelesen.", "Licht aus an der Havel.", "Guten Abend, Adrian.",
]


def mood_view(weather: dict | None, now: datetime) -> dict:
    """Stimmungsbild: Szene nach Tageszeit, Details nach Wetter."""
    scene = "morning" if now.hour < 11 else ("noon" if now.hour < 17 else "evening")
    cur = (weather or {}).get("current", {})
    code = cur.get("weather_code")
    kind = WMO.get(int(code), ("", "cloud"))[1] if code is not None else "cloud"
    temp = cur.get("temperature_2m")
    cond = WMO.get(int(code), ("",))[0] if code is not None else ""
    day = (weather or {}).get("days") or []
    t = f"{round(temp)}°" if temp is not None else ""
    seed = now.toordinal()
    if scene == "morning":
        caption = f"{MORNING_LINES[seed % len(MORNING_LINES)]} Draußen: {cond} bei {t}." if t else MORNING_LINES[0]
    elif scene == "noon":
        caption = f"Mittag an der Havel: {cond}, {t}."
        if day and (day[0].get("pp") or 0) >= 40:
            caption += f" Regenrisiko {day[0]['pp']} %."
    else:
        caption = f"{EVENING_LINES[seed % len(EVENING_LINES)]} {cond} bei {t}."
        if day and day[0].get("sunset"):
            caption += f" Die Sonne ist um {as_dt(day[0]['sunset']).strftime('%H:%M')} untergegangen." if as_dt(day[0]["sunset"]) <= now else ""
    clear = kind in ("sun", "sun-cloud")
    return {"scene": scene, "kind": kind, "sunny": clear, "caption": caption,
            "wet": kind in ("rain", "drizzle", "storm", "sleet"), "snow": kind == "snow",
            "fog": kind == "fog", "storm": kind == "storm", "cloudy": kind in ("cloud", "fog") or not clear}


def render(edition: dict, now: datetime) -> str:
    env = make_env(now)
    tpl = env.get_template("index.html.j2")
    welt = edition["sections"]["welt"]
    lead = next((it for it in welt[:3] if it.get("image")), welt[0] if welt else None)
    welt_rest = [it for it in welt if it is not lead]
    return tpl.render(
        e=edition, s=edition["sections"], now=now, lead=lead, welt_rest=welt_rest,
        weather=weather_view(edition["weather"], now), favorites=config.MLB_FAVORITES,
        mood=mood_view(weather_view(edition["weather"], now), now),
        issue_no=now.timetuple().tm_yday, utc_now=datetime.now(timezone.utc),
    )
