# RC Rally App — Start-Anleitung

## Voraussetzungen

Folgende Programme müssen installiert sein:

- **Python 3.10+** → https://www.python.org/downloads/  
  ⚠️ Beim Installieren: Haken bei **"Add Python to PATH"** setzen!
- **Node.js 18+** → https://nodejs.org/en (LTS-Version nehmen)
- **Git** (optional, nur für Updates) → https://git-scm.com

Prüfen ob alles installiert ist — PowerShell öffnen und eingeben:
```
python --version
node --version
npm --version
```
Alle drei müssen eine Versionsnummer anzeigen.

---

## App starten

1. Den Ordner `pmk-rc-webapp-v2` irgendwo auf dem PC speichern
2. Die Datei **`start.bat`** doppelklicken
3. Fertig — es öffnen sich 3 schwarze Fenster:
   - **RC Rally – Backend** (Python/FastAPI)
   - **RC Rally – Frontend** (React)
   - **RC Rally – Tunnel** (Cloudflare, öffentlicher Link)
4. Nach ~10 Sekunden öffnet sich der Browser automatisch auf `http://localhost:5173`

> ⚠️ **Nicht** die `index.html` direkt öffnen und **nicht** VS Code Live Server verwenden.  
> Die App ist eine React-App und braucht einen eigenen Entwicklungsserver.

---

## Beim ersten Start

Beim allerersten Start werden automatisch alle Pakete installiert (~2–5 Min).  
Das passiert nur einmal. Danach startet alles in ~10 Sekunden.

---

## Admin-Account erstellen

Nach dem ersten Start einmalig ausführen:

1. PowerShell im Ordner `backend` öffnen
2. Eingeben:
```
python reset_admin.py
```
3. Benutzername und Passwort werden angezeigt → notieren

Danach unter `http://localhost:5173/admin` einloggen.

---

## App aufrufen

| Was | URL |
|-----|-----|
| Startseite | http://localhost:5173 |
| Admin-Panel | http://localhost:5173/admin |
| Öffentlicher Link | Wird im Tunnel-Fenster angezeigt und automatisch im Browser geöffnet |

---

## Wichtig: Fenster offen lassen

Solange die App läuft, müssen **alle 3 schwarzen Fenster offen bleiben**.  
Zum Beenden einfach alle 3 Fenster schließen.

---

## Häufige Fehler

**„python wird nicht erkannt"**  
→ Python wurde ohne PATH installiert. Python neu installieren, diesmal Haken bei "Add to PATH" setzen.

**„npm wird nicht erkannt"**  
→ Node.js installieren (https://nodejs.org), dann PC neu starten.

**Browser zeigt „This site can't be reached"**  
→ Warten bis das Backend-Fenster `Application startup complete` anzeigt (~30 Sek).

**Backend-Fenster schließt sich sofort**  
→ Fehlende Python-Pakete. Im `backend`-Ordner PowerShell öffnen und ausführen:
```
pip install -r requirements.txt
```

**„Index öffnet sich nicht im Live Server" (VS Code)**  
→ Live Server funktioniert hier nicht. Nur `start.bat` verwenden.

---

## Projektstruktur

```
pmk-rc-webapp-v2/
├── start.bat          ← Hier starten (Doppelklick)
├── start-tunnel.ps1   ← Cloudflare-Tunnel (wird von start.bat aufgerufen)
├── backend/
│   ├── main.py        ← FastAPI-Server (alle Endpunkte)
│   ├── requirements.txt
│   └── reset_admin.py ← Admin-Passwort zurücksetzen
└── frontend/
    ├── src/           ← React-Quellcode
    └── package.json
```

---

## Team

David Dumke · Damjan Besarovic · Daniel Richter · Dino Telalovic · Philip Graff  
Hochschule Pforzheim · PMK SS2026
