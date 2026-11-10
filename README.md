# Die Depesche

Persönliche Zeitung in zwei Ausgaben, beide mit Wetter für Brandenburg an der Havel, Nachrichten aus
Brandenburg und der Welt und täglich drei Longreads:

- **Adrian** (Startseite): MLB & NBA (spoilerfrei, mit Link zum Sport Recap) und Gute Nachrichten.
- **Ulrike** (`/ulrike/`): Wissen & Gesundheit, Verbraucher, Recht, Gute Nachrichten und ein
  Alltagskasten (Pollenflug, UV-Index, Tageslicht, Mond, nächster Feiertag, Schulferien).

Nur frei zugängliche Quellen, alle Artikel verlinken auf das Original.

## So funktioniert es

Ein GitHub-Actions-Job baut um **6, 13 und 19 Uhr** (Berliner Zeit) eine fertige, statische Seite
und veröffentlicht sie auf GitHub Pages:

1. `briefing/sources.py` holt RSS-Feeds, die Tagesschau-API, MLB-Transaktionen (MLB Stats API)
   und das Wetter (Open-Meteo, DWD-Warnungen über Bright Sky). `briefing/alltag.py` holt Pollenflug
   (DWD) und Schulferien (OpenHolidays API) und berechnet Feiertage und Mondphase selbst.
2. `briefing/curate.py` filtert, sortiert (Padres und Athletics zuerst, Brandenburg an der Havel zuerst,
   bei Verbraucher-Meldungen Geldthemen nach hinten) und entfernt Dubletten.
3. `briefing/llm.py` lässt Claude Spoiler prüfen, den Welt-Aufmacher wählen und drei Longreads
   aussuchen (nach dem Interessen-Ranking der Person in `LONGREAD_INTERESTS`). Ohne Claude-Zugang läuft alles mit festen Regeln weiter.
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

`--dump raw.json` speichert die Rohdaten (Ulrikes in `raw-ulrike.json`), `--fixture raw.json` baut daraus erneut (ohne Netz),
`--now 2026-11-06T13:05` simuliert eine Uhrzeit.

## Quellen anpassen

Alles steht in `briefing/config.py`: Feeds, Lieblingsteams, Ort, Anzahl der Meldungen pro Rubrik.
Die Werte oben gelten für Adrian. Unter `PROFILES` überschreibt jede weitere Person nur, was bei ihr
anders ist (Rubriken in `COLUMNS`, Feeds, Longread-Interessen, Unterordner `PATH`). Ein Lauf baut
alle Profile, `--profile ulrike` baut nur eines. Fußball (Hertha, Ligen) ist abgeschaltet, der Code
bleibt aber da: `"fussball"` in `COLUMNS`, `LIMITS` und `FEEDS` aufnehmen.

## Hinweis zur Sichtbarkeit

GitHub Pages ist im kostenlosen Plan öffentlich erreichbar (die Seite ist für Suchmaschinen
gesperrt). Für eine wirklich private Seite kann der Job stattdessen zu Cloudflare Pages mit
Cloudflare Access (kostenloser Login davor) veröffentlichen.
