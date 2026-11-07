# Die Depesche

Persönliche Zeitung für Adrian: MLB & NBA (spoilerfrei, mit Link zum Sport Recap), Fußball (Hertha BSC,
1. und 2. Bundesliga, Champions League, mit Ergebnissen), Wetter für
Brandenburg an der Havel, Nachrichten aus Brandenburg und der Welt, dazu täglich drei Longreads.
Nur frei zugängliche Quellen, alle Artikel verlinken auf das Original.

## So funktioniert es

Ein GitHub-Actions-Job baut um **6, 13 und 19 Uhr** (Berliner Zeit) eine fertige, statische Seite
und veröffentlicht sie auf GitHub Pages:

1. `briefing/sources.py` holt RSS-Feeds, die Tagesschau-API, MLB-Transaktionen (MLB Stats API),
   Tabellen und Ergebnisse für Bundesliga, 2. Bundesliga und Champions League (OpenLigaDB) und das Wetter (Open-Meteo, DWD-Warnungen über Bright Sky).
2. `briefing/curate.py` filtert, sortiert (Padres und Athletics zuerst, höchstens drei Hertha-Meldungen oben, danach die Ligen im Wechsel, Brandenburg an
   der Havel zuerst) und entfernt Dubletten.
3. `briefing/llm.py` lässt Claude Spoiler prüfen, den Welt-Aufmacher wählen und drei Longreads
   aussuchen (nach Adrians Interessen-Ranking in `LONGREAD_INTERESTS`, sobald es gesetzt ist). Ohne Claude-Zugang läuft alles mit festen Regeln weiter.
4. `briefing/render.py` + `templates/index.html.j2` + `static/` erzeugen die Seite.

**Spoiler-Schutz:** Nur MLB und NBA (auch Sport-Longreads), nur Ergebnisse vom Vortag und von heute. Feste Muster
(z. B. `5-3`, „recap“, „no-hitter“, „40 points“) greifen immer, Claude prüft zusätzlich den Rest.
Ältere Meldungen bleiben unverändert.

## Einrichtung (einmalig)

1. **GitHub Pages einschalten:** Settings → Pages → Source: *GitHub Actions*.
2. **Claude anbinden (Pro-Abo):** Lokal `claude setup-token` ausführen und den Token unter
   Settings → Secrets and variables → Actions als Secret `CLAUDE_CODE_OAUTH_TOKEN` speichern.
   Alternativ geht ein API-Key als `ANTHROPIC_API_KEY`.
3. Optional als *Variable*: `BRIEFING_MODEL` (Standard `sonnet`, sparsamer: `haiku`).

Eine Ausgabe sofort bauen: Actions → „Ausgabe bauen“ → *Run workflow*.

## Lokal ausprobieren

```bash
pip install -r requirements.txt
python -m briefing.build --out site       # holt echte Daten
python -m http.server -d site 8000
```

`--dump raw.json` speichert die Rohdaten, `--fixture raw.json` baut daraus erneut (ohne Netz),
`--now 2026-11-06T13:05` simuliert eine Uhrzeit.

## Quellen anpassen

Alles steht in `briefing/config.py`: Feeds, Lieblingsteams, Ort, Anzahl der Meldungen pro Rubrik.

## Hinweis zur Sichtbarkeit

GitHub Pages ist im kostenlosen Plan öffentlich erreichbar (die Seite ist für Suchmaschinen
gesperrt). Für eine wirklich private Seite kann der Job stattdessen zu Cloudflare Pages mit
Cloudflare Access (kostenloser Login davor) veröffentlichen.
