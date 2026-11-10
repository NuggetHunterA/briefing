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

from . import alltag, config, curate, llm, sources
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
        if config.PATH:
            url = url.rstrip("/") + "/" + config.PATH
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
        "transactions": sources.fetch_mlb_transactions(now_utc) if "mlb" in config.COLUMNS else [],
        "football": sources.fetch_football(now_utc) if "fussball" in config.COLUMNS else {},
        "weather": sources.fetch_weather(),
        "alltag": alltag.fetch(now_utc) if config.ALLTAG else None,
    }


def revive(raw: dict) -> dict:
    """Fixture-Daten (JSON) zurück in datetime verwandeln."""
    for items in raw["news"].values():
        for it in items:
            if isinstance(it.get("published"), str):
                it["published"] = datetime.fromisoformat(it["published"])
    fb = raw.get("football") or {"hertha": raw.get("hertha"), "leagues": []}  # ältere Fixtures
    for section in config.LIMITS:
        raw["news"].setdefault(section, [])
    raw["football"] = fb
    matches = [(fb.get("hertha") or {}).get(k) for k in ("last", "next")]
    for lg in fb.get("leagues") or []:
        matches += lg.get("matches") or []
    for m in matches:
        if m and isinstance(m.get("when"), str):
            m["when"] = datetime.fromisoformat(m["when"])
    return raw


def per_profile(path: str | None, name: str) -> str | None:
    """raw.json -> raw.json für Adrian, raw-ulrike.json für Ulrike (oder {profile} im Pfad)."""
    if not path or name == "adrian":
        return path.replace("{profile}", name) if path else path
    if "{profile}" in path:
        return path.replace("{profile}", name)
    p = Path(path)
    return str(p.with_name(f"{p.stem}-{name}{p.suffix}"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site")
    ap.add_argument("--profile", default="all", help="adrian, ulrike oder all (Standard)")
    ap.add_argument("--fixture", help="Rohdaten aus Datei statt aus dem Netz")
    ap.add_argument("--dump", help="Rohdaten zusätzlich in diese Datei schreiben")
    ap.add_argument("--now", help="Zeitpunkt simulieren (ISO, Berliner Zeit)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    now_local = datetime.fromisoformat(args.now).replace(tzinfo=TZ) if args.now else datetime.now(TZ)
    out = ROOT / args.out
    if out.exists():
        shutil.rmtree(out)
    names = list(config.PROFILES) if args.profile == "all" else [args.profile]
    for name in names:
        config.use(name)
        log.info("=== Profil %s ===", name)
        build_one(out / config.PATH if config.PATH else out, now_local,
                  per_profile(args.fixture, name), per_profile(args.dump, name))


def build_one(out: Path, now_local: datetime, fixture: str | None, dump: str | None) -> None:
    now_utc = now_local.astimezone(timezone.utc)

    raw = revive(json.loads(Path(fixture).read_text())) if fixture else collect(now_utc)
    if dump:
        Path(dump).write_text(json.dumps(raw, default=to_json, ensure_ascii=False, indent=1))

    sections = curate.prepare(raw["news"], now_utc)
    cutoff = curate.spoiler_cutoff(now_local).astimezone(timezone.utc)

    sections["longreads"] = curate.drop_sport_spoilers(sections["longreads"], cutoff)

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
        welt_ids = edited.get("welt", [])
        sections["welt"] = curate.order_by(sections["welt"], welt_ids)
        if len(welt_ids) >= 5:  # Claude hat Dubletten und Boulevard schon aussortiert
            sections["welt"] = [it for it in sections["welt"] if it["id"] in set(welt_ids)]
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
        "hertha": raw["football"].get("hertha"),
        "leagues": raw["football"].get("leagues", []),
        "weather": raw["weather"],
        "alltag": raw.get("alltag"),
        "reader": config.READER,
        "columns": config.COLUMNS,
    }

    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(render(edition, now_local), encoding="utf-8")
    (out / "data.json").write_text(json.dumps(edition, default=to_json, ensure_ascii=False))
    for f in (ROOT / "static").iterdir():
        if f.is_dir():
            shutil.copytree(f, out / f.name, dirs_exist_ok=True)
        else:
            shutil.copy(f, out / f.name)
    log.info("Fertig: %s (%s, Redaktion: %s)", out / "index.html", edition["edition"], edition["editor"])


if __name__ == "__main__":
    main()
