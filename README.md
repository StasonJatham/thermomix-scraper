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

