"""Baut eine Ausgabe: python -m briefing.build [--out site] [--fixture datei.json]"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config, curate, llm, sources
from .render import render

log = logging.getLogger("briefing")
ROOT = Path(__file__).resolve().parent.parent
TZ = ZoneInfo(config.TIMEZONE)


def edition_name(now_local: datetime) -> str:
    name = "Morgenausgabe"
    for hour, label in sorted(config.EDITIONS.items()):
        if now_local.hour >= hour:
            name = label
    return name


def previous_edition() -> dict:
    """Letzte Ausgabe lesen, damit Longreads über den Tag stabil bleiben und sich nicht wiederholen."""
    url = os.environ.get("BRIEFING_SITE_URL")
    if url:
        r = sources.get(url.rstrip("/") + "/data.json")
        if r is not None:
            try:
                return r.json()
            except ValueError:
                pass
    return {}


def to_json(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(type(obj))


def collect(now_utc: datetime) -> dict:
    return {
        "news": sources.fetch_all_news(),
        "transactions": sources.fetch_mlb_transactions(now_utc),
        "hertha": sources.fetch_hertha(now_utc),
        "weather": sources.fetch_weather(),
    }


def revive(raw: dict) -> dict:
    """Fixture-Daten (JSON) zurück in datetime verwandeln."""
    for items in raw["news"].values():
        for it in items:
            if isinstance(it.get("published"), str):
                it["published"] = datetime.fromisoformat(it["published"])
    h = raw.get("hertha") or {}
    for k in ("last", "next"):
        if h.get(k) and isinstance(h[k].get("when"), str):
            h[k]["when"] = datetime.fromisoformat(h[k]["when"])
    return raw


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site")
    ap.add_argument("--fixture", help="Rohdaten aus Datei statt aus dem Netz")
    ap.add_argument("--dump", help="Rohdaten zusätzlich in diese Datei schreiben")
    ap.add_argument("--now", help="Zeitpunkt simulieren (ISO, Berliner Zeit)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    now_local = datetime.fromisoformat(args.now).replace(tzinfo=TZ) if args.now else datetime.now(TZ)
    now_utc = now_local.astimezone(timezone.utc)

    raw = revive(json.loads(Path(args.fixture).read_text())) if args.fixture else collect(now_utc)
    if args.dump:
        Path(args.dump).write_text(json.dumps(raw, default=to_json, ensure_ascii=False, indent=1))

    sections = curate.prepare(raw["news"], now_utc)
    cutoff = curate.spoiler_cutoff(now_local).astimezone(timezone.utc)

    prev = previous_edition()
    today = now_local.date().isoformat()
    history = set(prev.get("longread_history", []))
    keep_longreads = prev.get("date") == today and prev.get("longreads")

    spoiler_candidates = [it for s in config.SPOILER_SECTIONS for it in sections[s]
                          if curate.needs_spoiler_check(it, cutoff)]
    edited = llm.edit(spoiler_candidates, sections["welt"], sections["brandenburg"],
                      sections["longreads"], history)

    hidden = curate.apply_spoilers(sections, set(edited["spoilers"]) if edited else None, cutoff)

    if edited:
        sections["welt"] = curate.order_by(sections["welt"], edited.get("welt", []))
        bb_ids = edited.get("brandenburg", [])
        if bb_ids:
            sections["brandenburg"] = [it for it in curate.order_by(sections["brandenburg"], bb_ids) if it["id"] in set(bb_ids)]

    if keep_longreads:
        longreads = prev["longreads"]
    else:
        by_id = {it["id"]: it for it in sections["longreads"]}
        longreads = []
        if edited:
            for pick in edited.get("longreads", []):
                it = by_id.get(pick.get("id"))
                if it and it["id"] not in history:
                    longreads.append({**it, "why": pick.get("why", "")})
        if len(longreads) < config.LIMITS["longreads"]:
            have = {x["id"] for x in longreads}
            longreads += [x for x in curate.fallback_longreads(sections["longreads"], history | have)
                          ][: config.LIMITS["longreads"] - len(longreads)]
    history = (list(history) + [x["id"] for x in longreads])[-60:]

    for s, n in config.LIMITS.items():
        if s != "longreads":
            sections[s] = sections[s][:n]

    edition = {
        "date": today,
        "generated": now_local.isoformat(),
        "edition": edition_name(now_local),
        "editor": "claude" if edited else "regeln",
        "location": config.LOCATION,
        "sections": sections,
        "longreads": longreads,
        "longread_history": history,
        "hidden": hidden,
        "transactions": raw["transactions"],
        "hertha": raw["hertha"],
        "weather": raw["weather"],
    }

    out = ROOT / args.out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "index.html").write_text(render(edition, now_local), encoding="utf-8")
    (out / "data.json").write_text(json.dumps(edition, default=to_json, ensure_ascii=False))
    for f in (ROOT / "static").iterdir():
        shutil.copy(f, out / f.name)
    log.info("Fertig: %s (%s, Redaktion: %s)", out / "index.html", edition["edition"], edition["editor"])


if __name__ == "__main__":
    main()
