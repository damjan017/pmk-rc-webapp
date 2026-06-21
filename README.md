# 🏁 PMK RC-Rally App

> Digitale Rennsoftware für RC-Car-Veranstaltungen — selbst gehostet, kostenlos, einfach zu starten.

Entwickelt im Rahmen des Moduls **Projekt Management und Kommunikation (PMK)** an der **Hochschule Pforzheim**, Sommersemester 2026.

---

## Features

- **Fahrer-Registrierung & Login** mit DSGVO-konformer Einwilligung
- **Live-Leaderboard** mit Auto-Refresh — auch als TV-Modus für externe Displays
- **QR-Code Check-in** — Fahrer scannen ihren Code, werden automatisch eingecheckt
- **Admin-Dashboard** — Rennen erstellen, starten, Zeiten & Strafzeiten eintragen
- **KI-Kamera-Simulator** — Tor-Signale per Handy senden
- **Cloudflare-Tunnel** — App über das Internet erreichbar, ohne Port-Freigabe
- **CSV/Excel-Import** — Fahrerlisten direkt importieren
- **Ergebnis-Mail** — automatische Benachrichtigung nach Rennende
- **Urkunden-Druck** — PDF-Urkunden für die Platzierten
- **Demo-Modus** — Testdaten mit einem Klick laden

---

## Schnellstart

### Voraussetzungen

| Software | Version | Download |
|----------|---------|----------|
| Python | 3.10+ | https://python.org/downloads |
| Node.js | 18 LTS+ | https://nodejs.org |

> **Wichtig:** Bei der Python-Installation den Haken bei **"Add Python to PATH"** setzen.

### Starten

```bash
# 1. Repository herunterladen
git clone https://github.com/damjan017/pmk-rc-webapp.git
cd pmk-rc-webapp

# 2. App starten (installiert alles automatisch)
start.bat
```

Die App öffnet sich automatisch unter `http://localhost:5173`.

### Admin-Account anlegen

```bash
cd backend
python reset_admin.py
```

**Standard-Zugangsdaten:**
```
E-Mail:   admin@pmk.de
Passwort: Admin2026!
```

Eigene Credentials: `python reset_admin.py --custom`

---

## Tech Stack

| Schicht | Technologie |
|---------|------------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | FastAPI (Python 3.10+) |
| Datenbank | SQLite via SQLAlchemy ORM |
| Tunnel | Cloudflare Tunnel |
| Scheduler | APScheduler (2h-Erinnerungsmail) |

---

## API-Dokumentation

Läuft das Backend, ist die interaktive Doku automatisch verfügbar:

```
http://localhost:8000/docs    ← Swagger UI
http://localhost:8000/redoc   ← ReDoc
```

---

## Projektstruktur

```
pmk-rc-webapp/
├── start.bat              ← Ein-Klick-Start (Windows)
├── start-tunnel.ps1       ← Cloudflare-Tunnel
├── docker-compose.yml     ← Docker-Deployment
├── backend/
│   ├── main.py            ← FastAPI-App (alle Endpunkte)
│   ├── requirements.txt
│   ├── reset_admin.py     ← Admin einrichten
│   └── demo_daten.py      ← Testdaten laden
└── frontend/
    └── src/
        ├── pages/         ← React-Seiten
        └── components/    ← Wiederverwendbare Komponenten
```

---

## Belastungstest

```bash
pip install requests openpyxl
python belastungstest.py
```

Testet automatisch 25 Fahrer, 3 Rennen, Zeiten, Leaderboard, CSV-Import und 50 parallele Requests.

---

## Team

| Name | Rolle |
|------|-------|
| David Dumke | Projektleitung |
| Damjan Besarovic | Backend & Deployment |
| Daniel Richter | Frontend |
| Dino Telalovic | Testing & QA |
| Philip Graff | Dokumentation |

**Hochschule Pforzheim · Wirtschaftsinformatik (PO 2020) · PMK SS 2026**

---

## KI-Einsatz

Dieses Projekt wurde mit Unterstützung von **Claude Code** (Anthropic) entwickelt.
Die KI-Auswahl erfolgte auf Basis einer gewichteten Nutzwertanalyse — Claude Code erzielte den Höchstwert (4,40 / 5,0).

---

<div align="center">
  <sub>TechDay 22. Juni 2026 · Stand Nr. 13 · Ebene 2, T1-Gebäude · Hochschule Pforzheim</sub>
</div>
