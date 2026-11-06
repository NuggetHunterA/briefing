"""Redaktion per Claude: Spoiler prüfen, Welt-Aufmacher wählen, Longreads auswählen.

Läuft über die Claude-Code-CLI (`claude -p`). In GitHub Actions authentifiziert sie
sich mit CLAUDE_CODE_OAUTH_TOKEN (aus dem Pro-Abo, erzeugt mit `claude setup-token`)
oder alternativ mit ANTHROPIC_API_KEY. Fehlt beides oder schlägt der Aufruf fehl,
gibt die Funktion None zurück und die Ausgabe wird mit festen Regeln gebaut.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess

log = logging.getLogger("briefing")

PROMPT = """Du bist der Redakteur einer persönlichen Morgenzeitung für Adrian aus Brandenburg an der Havel.
Du bekommst unten JSON mit Kandidaten. Antworte NUR mit einem JSON-Objekt, ohne Erklärung, ohne Markdown.

Aufgaben:
1. "spoilers": Prüfe jede Meldung in "spoiler_check" (MLB/NBA, alle vom Vortag oder heute).
   Adrian schaut die Spiele zeitversetzt. Markiere jede Meldung, die verrät, wie ein Spiel
   von gestern oder heute ausgegangen ist oder verlaufen ist: Ergebnisse, Sieger, Serien,
   Siegesserien, Statistiken aus dem Spiel, Tabellen- oder Playoff-Folgen daraus, auch indirekt
   ("nach der Niederlage", "feiert", "Comeback"). Trades, Gerüchte, Verträge, Verletzungen ohne
   Spielergebnis sind OK. Im Zweifel markieren. Gib die ids als Liste zurück.
2. "welt": Ordne die Weltnachrichten nach Bedeutung für einen informierten Leser. Gib bis zu 8 ids
   zurück, die erste ist der Aufmacher. Keine Doppelungen zum selben Ereignis (behalte die beste Quelle),
   achte auf Themenvielfalt, kein Boulevard.
3. "brandenburg": Ordne die Brandenburg-Meldungen, bis zu 7 ids. Meldungen aus Brandenburg an der Havel
   und Umgebung zuerst, dann landesweit Wichtiges. Keine Doppelungen, keine reinen Berlin-Themen.
4. "longreads": Wähle genau 3 Texte aus "longreads", die gut geschrieben, substanziell und für das
   aktuelle Zeitgeschehen relevant sind. Unterschiedliche Themen und möglichst unterschiedliche Quellen.
   Nichts aus "already_shown". Zu jedem ein Satz "why" auf Deutsch (max. 160 Zeichen), warum sich
   das Lesen lohnt, ohne Floskeln.

Format:
{"spoilers": ["id", ...], "welt": ["id", ...], "brandenburg": ["id", ...],
 "longreads": [{"id": "...", "why": "..."}, ...]}

Kandidaten:
"""


def _slim(items: list[dict], n: int, summary_len: int = 280) -> list[dict]:
    return [{"id": it["id"], "source": it["source"], "title": it["title"],
             "summary": it["summary"][:summary_len]} for it in items[:n]]


def available() -> bool:
    return bool(shutil.which("claude")) and bool(
        os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
    )


def edit(spoiler_items, welt, brandenburg, longreads, already_shown) -> dict | None:
    if not available():
        log.info("Kein Claude-Zugang konfiguriert: Ausgabe wird ohne LLM gebaut.")
        return None
    payload = {
        "spoiler_check": _slim(spoiler_items, 80, 400),
        "welt": _slim(welt, 40),
        "brandenburg": _slim(brandenburg, 30),
        "longreads": _slim(longreads, 40, 400),
        "already_shown": sorted(already_shown),
    }
    prompt = PROMPT + json.dumps(payload, ensure_ascii=False)
    model = os.environ.get("BRIEFING_MODEL", "sonnet")
    try:
        res = subprocess.run(
            ["claude", "-p", "--model", model, "--output-format", "text", "--max-turns", "1"],
            input=prompt, capture_output=True, text=True, timeout=300,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("Claude-Aufruf fehlgeschlagen: %s", e)
        return None
    if res.returncode != 0:
        log.warning("Claude-Aufruf fehlgeschlagen (%s): %s", res.returncode, (res.stderr or res.stdout)[-500:])
        return None
    m = re.search(r"\{.*\}", res.stdout, re.S)
    if not m:
        log.warning("Claude-Antwort ohne JSON: %s", res.stdout[:300])
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        log.warning("Claude-Antwort nicht lesbar: %s", e)
        return None
    log.info("Claude: %d Spoiler, %d Welt, %d Longreads",
             len(data.get("spoilers", [])), len(data.get("welt", [])), len(data.get("longreads", [])))
    return data
