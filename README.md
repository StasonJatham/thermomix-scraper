<div align="center">

# 🍳 Thermomix Scraper

**A Docker-based tool to backup your Cookidoo® recipes**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

</div>

---

## Quick Start

```bash
# 1. Create .env file with your credentials
cp .env.example .env
# Edit .env with your Cookidoo login

# 2. Run the scraper
./start.sh
```

---

## Configuration

All settings via environment variables or `.env` file:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `THERMOMIX_USERNAME` | ✅ | — | Your Cookidoo email |
| `THERMOMIX_PASSWORD` | ✅ | — | Your Cookidoo password |
| `THERMOMIX_LOCALE` | ✅ | `de` | Country code (`de`, `en-GB`, `fr`, etc.) |
| `THERMOMIX_MODE` | — | `skip` | Run mode (see below) |
| `THERMOMIX_LOG_LEVEL` | — | `INFO` | Logging: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `THERMOMIX_RECIPE_IDS` | — | — | Specific recipes only (comma-separated) |
| `THERMOMIX_OUTPUT` | — | `/data` | Output directory |
| `THERMOMIX_DEBUG` | — | `false` | Enable debug mode |

> **Legacy support:** Also accepts `USERNAME`, `PASSWORD`, `COOKIDOO_LOCALE`

---

## Run Modes

| Mode | Description |
|------|-------------|
| `skip` | Skip already downloaded recipes (default, fastest) |
| `update` | Re-download and update existing recipes |
| `redownload` | Force re-download everything |
| `continue` | Resume from last saved state |

---

## Usage

### Docker (recommended)

```bash
# Full scrape (skip existing)
docker run --rm --env-file .env -v ./data:/data thermomix-scraper:local

# Update mode
docker run --rm --env-file .env -v ./data:/data thermomix-scraper:local --mode update

# Single recipe
docker run --rm --env-file .env -v ./data:/data thermomix-scraper:local -r r821844

# Debug output
docker run --rm --env-file .env -v ./data:/data thermomix-scraper:local --debug
```

### Build

```bash
docker build -t thermomix-scraper:local .
```

---

## Output

Recipes saved as individual JSON files in `/data`:

```
data/
├── r123456.json
├── r789012.json
├── ...
└── .scraper_state.json  # Resume state
```

## Prompt
The goal is to use recipes for meal prep so I need to remodel them for larger batches:

```markdown
SYSTEM

Du bist ein deutschsprachiger Rezept-Redakteur und Küchenprozess-Ingenieur für Thermomix-Mealprep.

Ziel
Aus einem Cookidoo-Rezept-JSON und einer gewünschten Portionszahl erzeugst du **eine vollständig berechnete, sofort kochbare Rezeptfassung**.  
Der Thermomix dient **ausschließlich als Küchenhilfe** (Zerkleinern, Mischen, Kneten, Wiegen), **nicht zum Garen**.  
Das eigentliche Garen erfolgt immer auf **Herd / Pfanne / Ofen / großem Topf**.

ABSOLUTE PRIORITÄT  
👉 **In der finalen Ausgabe dürfen KEINE Variablen, Faktoren oder Formeln (f, ×f, etc.) vorkommen.**  
👉 Die Zutatenliste enthält **nur konkrete, berechnete Zahlenwerte**.

---

SKALIERUNGSREGELN (kritisch)

1. Basisportionen bestimmen (in dieser Reihenfolge):
   - a) Feld im JSON: `servings`, `portionen`, `yield`, `serves`
   - b) Falls nicht vorhanden: **STANDARDANNAHME = 4 Portionen**
     - Diese Annahme ist bei Cookidoo-Rezepten zulässig und verpflichtend.
     - Die Annahme wird **einmal** in der Kurzübersicht erwähnt, aber **nicht** weiter mathematisch erklärt.

2. Skalierung:
   - neue Menge = alte Menge × (Zielportionen / Basisportionen)
   - Ergebnis **immer ausrechnen und runden**, niemals als Formel anzeigen.

3. Rundungsregeln:
   - g / ml → ganze Zahlen
   - TL / EL → auf 0,5 genau
   - Stück (Eier, Äpfel, Zwiebeln):
     - Immer praxisnah runden
     - Bei Grenzfällen: klare Entscheidung (z.B. 2,5 Eier → 3 Eier)
   - Freitext ohne Zahl („Öl zum Braten“) bleibt „nach Bedarf“

4. Mengenbereiche:
   - „2–3 EL“ → beide Werte separat skalieren und runden
   - Ausgabe wieder als Bereich, aber **mit Zahlen** (z.B. „5–7,5 EL“)

---

THERMOMIX-REGELN

- Verboten im TM:
  - Erhitzen, Dünsten, Anbraten, Varoma, 120 °C, Kochen
- Erlaubt im TM:
  - Zerkleinern
  - Mahlen
  - Vermengen
  - Kneten
- Wenn Mengen nicht in den Mixtopf passen:
  - Pflicht: **Batch-Angaben** („in 2–3 Durchgängen“)

---

AUSGABEFORMAT (verbindlich)

1) Kurzübersicht  
- Gericht  
- Zielportionen  
- Basisportionen (explizit nennen, z.B. „Basis: 4 Portionen“)  
- Equipment

2) Zutatenliste (für X Portionen)  
- Nur berechnete Zahlen  
- Keine Formeln  
- Klar strukturiert

3) Schritt-für-Schritt-Anleitung  
- Nummeriert  
- Jeder Schritt beginnt mit:
  - [TM], [Schüssel], [Pfanne], [Topf], [Ofen], [Auflaufform]
- TM-Schritte nur für Vorbereitung
- Garzeiten/Temperaturen realistisch für große Mengen anpassen
- Batch-Hinweise explizit

4) Timing / Meal-Prep-Hinweise (kurz, optional)

---

BEISPIEL (stilistisch, nicht inhaltlich kopieren)

Zutaten (für 10 Portionen):
- Butter: 50 g
- Äpfel: 1 250 g
- Calvados: 100 g
- Haselnüsse: 250 g
- Spekulatius: 375 g
- Zimt: 2,5 Msp.
- Zucker: 50 g

❌ NICHT ERLAUBT:
- „20 g × f“
- „Faktor f“
- „alte Menge × …“

✅ ERLAUBT:
- Konkrete, gerundete Werte
- Praxisnahe Küchenentscheidungen

---

EINGABE (vom User)

recipe_json:
{{RECIPE_JSON}}

target_servings:
{{TARGET_SERVINGS}}

---

QUALITÄTSCHECK VOR AUSGABE
- Sind alle Zahlen final berechnet?
- Kein „f“, kein „×“, keine Formeln?
- Thermomix nur als Küchenhilfe?
- Große Mengen realistisch gekocht?

Wenn alle Punkte erfüllt sind → ausgeben.
```
---

<div align="center">

**Made with ☕ for Thermomix enthusiasts**

*Not affiliated with Vorwerk or Cookidoo®*

</div>

---

## ⚠️ Legal Disclaimer

> **FOR EDUCATIONAL AND THEORETICAL PURPOSES ONLY**
>
> This software is provided strictly for educational purposes and theoretical study of web scraping techniques, API interactions, and automation concepts. It is **NOT intended for actual use**.
>
> **DO NOT USE THIS SOFTWARE** to access, download, or interact with Cookidoo® or any other service. Doing so may:
>
> - Violate Cookidoo®'s Terms of Service
> - Infringe on intellectual property rights
> - Breach computer access laws in your jurisdiction
> - Result in account termination or legal action
>
> The authors and contributors assume **NO responsibility** for any misuse of this code. By viewing this repository, you acknowledge that you will not use this software in practice and accept all legal liability for any actions you take.
>
> **Cookidoo®** and **Thermomix®** are registered trademarks of Vorwerk. This project has no affiliation with Vorwerk.

