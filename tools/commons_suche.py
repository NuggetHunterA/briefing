"""Sucht frei lizenzierte Fotos auf Wikimedia Commons und speichert Vorschaubilder + Metadaten.

python tools/commons_suche.py kandidaten/
"""
import json
import re
import sys
import time
from pathlib import Path

import requests

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "PersonalBriefing/1.0 (https://github.com/NuggetHunterA/briefing)"}
OK_LICENSE = re.compile(r"^(CC0|CC BY(-SA)? [0-9.]+( de)?|Public domain|PD)", re.I)

QUERIES = {
    "morgen": ["coffee cup morning", "cup of coffee window light", "Kaffeetasse Frühstück", "coffee newspaper breakfast", "espresso cup table"],
    "havel-sonne": ["Brandenburg an der Havel Havel", "Dom St. Peter und Paul Brandenburg an der Havel", "Brandenburg an der Havel Altstadt", "Beetzsee Brandenburg", "Brandenburg an der Havel Dominsel", "Brandenburg an der Havel Jahrtausendbrücke"],
    "havel-grau": ["Brandenburg an der Havel cloudy", "Havel Brandenburg Regen", "Brandenburg an der Havel November", "Havel Herbst Brandenburg"],
    "havel-winter": ["Brandenburg an der Havel Winter", "Brandenburg an der Havel Schnee", "Havel Eis Winter"],
    "havel-nebel": ["Havel Nebel", "Brandenburg an der Havel fog", "Beetzsee Nebel"],
    "abend": ["Brandenburg an der Havel night", "Brandenburg an der Havel Nacht", "Brandenburg an der Havel Abend", "Havel Sonnenuntergang", "Brandenburg an der Havel sunset", "Beetzsee Sonnenuntergang"],
}


def search(q):
    r = requests.get(API, headers=UA, timeout=30, params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{q} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": 30, "prop": "imageinfo",
        "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 640,
    })
    r.raise_for_status()
    return (r.json().get("query") or {}).get("pages", {}).values()


def clean(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    meta, seen = [], set()
    for group, qs in QUERIES.items():
        n = 0
        for q in qs:
            for p in search(q):
                ii = (p.get("imageinfo") or [{}])[0]
                if p["title"] in seen or ii.get("mime") not in ("image/jpeg", "image/png"):
                    continue
                w, h = ii.get("width", 0), ii.get("height", 0)
                if w < 1600 or w < h * 1.2:  # nur Querformat, ausreichend groß
                    continue
                em = ii.get("extmetadata", {})
                lic = clean(em.get("LicenseShortName", {}).get("value"))
                if not OK_LICENSE.match(lic):
                    continue
                seen.add(p["title"])
                n += 1
                fname = f"{group}-{n:02d}.jpg"
                img = requests.get(ii["thumburl"], headers=UA, timeout=30)
                if img.ok:
                    (out / fname).write_bytes(img.content)
                meta.append({
                    "file": fname, "group": group, "query": q, "title": p["title"],
                    "page": ii.get("descriptionurl"), "url": ii.get("url"), "width": w, "height": h,
                    "license": lic, "artist": clean(em.get("Artist", {}).get("value"))[:120],
                })
                time.sleep(0.2)
                if n >= 24:
                    break
            if n >= 24:
                break
        print(group, n)
    (out / "kandidaten.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
