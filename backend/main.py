from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import qrcode
import io
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./rally.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ── Modelle ──────────────────────────────────────────────────
class Fahrer(Base):
    __tablename__ = "fahrer"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    startnummer = Column(Integer)
    fahrzeug = Column(String)
    einwilligung = Column(Boolean, default=False)
    eingecheckt = Column(Boolean, default=False)

class Zeit(Base):
    __tablename__ = "zeiten"
    id = Column(Integer, primary_key=True)
    fahrer_id = Column(Integer)
    rundenzeit = Column(Float)
    strafzeit = Column(Float, default=0.0)
    gesamtzeit = Column(Float)

class Strafzeit(Base):
    __tablename__ = "strafzeiten"
    id = Column(Integer, primary_key=True)
    fahrer_id = Column(Integer)
    strafzeit = Column(Float)
    grund = Column(String)

class RennStatus(Base):
    __tablename__ = "renn_status"
    id = Column(Integer, primary_key=True)
    abgeschlossen = Column(Boolean, default=False)
    abgeschlossen_um = Column(String, nullable=True)

# Tor-Durchfahrten speichern
class TorSignal(Base):
    __tablename__ = "tor_signale"
    id = Column(Integer, primary_key=True)
    fahrer_id = Column(Integer)
    tor_nr = Column(Integer)       # 1 = erstes Tor, N = letztes Tor
    zeitstempel = Column(Float)    # Unix timestamp
    lauf_id = Column(Integer)      # welcher Lauf (wird hochgezählt)

Base.metadata.create_all(bind=engine)

def init_status():
    db = SessionLocal()
    if db.query(RennStatus).count() == 0:
        db.add(RennStatus(abgeschlossen=False))
        db.commit()
    db.close()

init_status()

# Anzahl Tore (anpassbar)
ANZAHL_TORE = 6

app = FastAPI(title="RC-Car Rally API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic Models ──────────────────────────────────────────
class FahrerCreate(BaseModel):
    name: str
    email: str
    fahrzeug: str
    einwilligung: bool

class ZeitCreate(BaseModel):
    fahrer_id: int
    rundenzeit: float
    strafzeit: float = 0.0

class StrafzeitCreate(BaseModel):
    fahrer_id: int
    strafzeit: float
    grund: str

class TorSignalCreate(BaseModel):
    fahrer_id: int
    tor_nr: int
    zeitstempel: float

# ── Hilfsfunktion ────────────────────────────────────────────
def rennen_offen():
    db = SessionLocal()
    s = db.query(RennStatus).first()
    db.close()
    return not s.abgeschlossen

# ── Basis ────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "PMK RC-Rally API läuft!"}

@app.get("/status")
def status():
    db = SessionLocal()
    s = db.query(RennStatus).first()
    db.close()
    return {"abgeschlossen": s.abgeschlossen, "abgeschlossen_um": s.abgeschlossen_um}

# ── Fahrer ───────────────────────────────────────────────────
@app.post("/fahrer")
def fahrer_registrieren(fahrer: FahrerCreate, request: Request):
    if not rennen_offen():
        raise HTTPException(status_code=403, detail="Rennen ist bereits abgeschlossen")
    if not fahrer.einwilligung:
        raise HTTPException(status_code=400, detail="Einwilligung erforderlich")
    db = SessionLocal()
    if db.query(Fahrer).filter(Fahrer.email == fahrer.email).first():
        db.close()
        raise HTTPException(status_code=400, detail="Diese E-Mail ist bereits registriert")
    neuer_fahrer = Fahrer(
        name=fahrer.name, email=fahrer.email, fahrzeug=fahrer.fahrzeug,
        einwilligung=fahrer.einwilligung, startnummer=db.query(Fahrer).count() + 1
    )
    db.add(neuer_fahrer)
    db.commit()
    db.refresh(neuer_fahrer)
    db.close()
    return {
        "message": f"Fahrer {fahrer.name} registriert!",
        "startnummer": neuer_fahrer.startnummer,
        "qr_code_url": f"{request.base_url}fahrer/{neuer_fahrer.id}/qrcode"
    }

@app.get("/fahrer")
def alle_fahrer():
    db = SessionLocal()
    f = db.query(Fahrer).all()
    db.close()
    return f

@app.get("/fahrer/{fahrer_id}/qrcode")
def qrcode_generieren(fahrer_id: int):
    db = SessionLocal()
    fahrer = db.query(Fahrer).filter(Fahrer.id == fahrer_id).first()
    db.close()
    if not fahrer:
        raise HTTPException(status_code=404, detail="Fahrer nicht gefunden")
    img = qrcode.make(f"Fahrer: {fahrer.name}\nStartnummer: {fahrer.startnummer}\nFahrzeug: {fahrer.fahrzeug}")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

@app.post("/checkin/{fahrer_id}")
def checkin(fahrer_id: int):
    db = SessionLocal()
    fahrer = db.query(Fahrer).filter(Fahrer.id == fahrer_id).first()
    if not fahrer:
        db.close()
        raise HTTPException(status_code=404, detail="Fahrer nicht gefunden")
    if fahrer.eingecheckt:
        db.close()
        raise HTTPException(status_code=400, detail="Fahrer bereits eingecheckt")
    fahrer.eingecheckt = True
    db.commit()
    db.close()
    return {"message": f"Fahrer {fahrer.name} eingecheckt!", "startnummer": fahrer.startnummer}

# ── Zeiten ───────────────────────────────────────────────────
@app.post("/zeiten")
def zeit_eintragen(z: ZeitCreate):
    if not rennen_offen():
        raise HTTPException(status_code=403, detail="Rennen ist bereits abgeschlossen")
    db = SessionLocal()
    fahrer = db.query(Fahrer).filter(Fahrer.id == z.fahrer_id).first()
    if not fahrer:
        db.close()
        raise HTTPException(status_code=404, detail="Fahrer nicht gefunden")
    neue_zeit = Zeit(fahrer_id=z.fahrer_id, rundenzeit=z.rundenzeit,
                     strafzeit=z.strafzeit, gesamtzeit=z.rundenzeit + z.strafzeit)
    db.add(neue_zeit)
    db.commit()
    db.close()
    return {"message": "Zeit eingetragen", "gesamtzeit": neue_zeit.gesamtzeit}

@app.get("/zeiten/{fahrer_id}")
def zeiten_von_fahrer(fahrer_id: int):
    db = SessionLocal()
    z = db.query(Zeit).filter(Zeit.fahrer_id == fahrer_id).all()
    db.close()
    return z

# ── Strafzeiten ──────────────────────────────────────────────
@app.post("/strafzeiten")
def strafzeit_hinzufuegen(s: StrafzeitCreate):
    if not rennen_offen():
        raise HTTPException(status_code=403, detail="Rennen ist bereits abgeschlossen")
    db = SessionLocal()
    fahrer = db.query(Fahrer).filter(Fahrer.id == s.fahrer_id).first()
    if not fahrer:
        db.close()
        raise HTTPException(status_code=404, detail="Fahrer nicht gefunden")
    db.add(Strafzeit(fahrer_id=s.fahrer_id, strafzeit=s.strafzeit, grund=s.grund))
    letzte = db.query(Zeit).filter(Zeit.fahrer_id == s.fahrer_id).order_by(Zeit.id.desc()).first()
    if letzte:
        letzte.strafzeit += s.strafzeit
        letzte.gesamtzeit += s.strafzeit
    db.commit()
    db.close()
    return {"message": f"Strafzeit von {s.strafzeit}s für {fahrer.name} eingetragen", "grund": s.grund}

# ── Leaderboard ──────────────────────────────────────────────
@app.get("/leaderboard")
def leaderboard():
    db = SessionLocal()
    ergebnis = []
    for fahrer in db.query(Fahrer).all():
        zeiten = db.query(Zeit).filter(Zeit.fahrer_id == fahrer.id).all()
        strafen = db.query(Strafzeit).filter(Strafzeit.fahrer_id == fahrer.id).all()
        ergebnis.append({
            "startnummer": fahrer.startnummer, "name": fahrer.name,
            "fahrzeug": fahrer.fahrzeug, "eingecheckt": fahrer.eingecheckt,
            "beste_gesamtzeit": min((z.gesamtzeit for z in zeiten), default=None),
            "gesamt_strafzeit": sum(s.strafzeit for s in strafen),
            "anzahl_laeufe": len(zeiten)
        })
    db.close()
    ergebnis.sort(key=lambda x: (x["beste_gesamtzeit"] is None, x["beste_gesamtzeit"]))
    return ergebnis

# ── Rennen ───────────────────────────────────────────────────
@app.post("/rennen/abschliessen")
def rennen_abschliessen():
    if not rennen_offen():
        raise HTTPException(status_code=400, detail="Rennen bereits abgeschlossen")
    db = SessionLocal()
    s = db.query(RennStatus).first()
    s.abgeschlossen = True
    s.abgeschlossen_um = datetime.now().strftime("%d.%m.%Y um %H:%M Uhr")
    db.commit()
    db.close()
    return {"message": "Rennen erfolgreich abgeschlossen!"}

@app.post("/rennen/reset")
def rennen_reset():
    db = SessionLocal()
    s = db.query(RennStatus).first()
    s.abgeschlossen = False
    s.abgeschlossen_um = None
    db.commit()
    db.close()
    return {"message": "Rennen wieder geöffnet"}

# ── KI-KAMERA MEHRTOR-SYSTEM ─────────────────────────────────
@app.post("/kamera/tor")
def tor_signal(signal: TorSignalCreate):
    """
    Empfängt ein Signal von einem Tor.
    - Tor 1 = Starttor → startet neuen Lauf
    - Tore 2 bis N-1 = Zwischentore → Zwischenzeit
    - Letztes Tor = Zieltor → Gesamtzeit berechnen und speichern
    """
    if not rennen_offen():
        raise HTTPException(status_code=403, detail="Rennen ist bereits abgeschlossen")
    db = SessionLocal()
    fahrer = db.query(Fahrer).filter(Fahrer.id == signal.fahrer_id).first()
    if not fahrer:
        db.close()
        raise HTTPException(status_code=404, detail="Fahrer nicht gefunden")

    # Aktuellen Lauf bestimmen
    letzter_lauf = db.query(TorSignal).filter(
        TorSignal.fahrer_id == signal.fahrer_id
    ).order_by(TorSignal.lauf_id.desc()).first()

    if signal.tor_nr == 1:
        # Neuer Lauf beginnt
        lauf_id = (letzter_lauf.lauf_id + 1) if letzter_lauf else 1
        db.add(TorSignal(fahrer_id=signal.fahrer_id, tor_nr=1,
                         zeitstempel=signal.zeitstempel, lauf_id=lauf_id))
        db.commit()
        db.close()
        return {
            "status": "start",
            "message": f"🚦 Tor 1 — START für {fahrer.name}! Lauf {lauf_id}",
            "lauf_id": lauf_id,
            "tor_nr": 1,
            "naechstes_tor": 2
        }

    # Welcher Lauf läuft gerade?
    lauf_id = letzter_lauf.lauf_id if letzter_lauf else None
    if not lauf_id:
        db.close()
        raise HTTPException(status_code=400, detail="Kein aktiver Lauf — bitte zuerst Tor 1 passieren")

    # Startzeit dieses Laufs
    start_signal = db.query(TorSignal).filter(
        TorSignal.fahrer_id == signal.fahrer_id,
        TorSignal.lauf_id == lauf_id,
        TorSignal.tor_nr == 1
    ).first()
    if not start_signal:
        db.close()
        raise HTTPException(status_code=400, detail="Startzeit nicht gefunden")

    # Zwischenzeit berechnen
    zwischenzeit = round(signal.zeitstempel - start_signal.zeitstempel, 3)

    # Signal speichern
    db.add(TorSignal(fahrer_id=signal.fahrer_id, tor_nr=signal.tor_nr,
                     zeitstempel=signal.zeitstempel, lauf_id=lauf_id))

    # Letztes Tor → Gesamtzeit speichern
    if signal.tor_nr >= ANZAHL_TORE:
        neue_zeit = Zeit(
            fahrer_id=signal.fahrer_id,
            rundenzeit=zwischenzeit,
            strafzeit=0.0,
            gesamtzeit=zwischenzeit
        )
        db.add(neue_zeit)
        db.commit()
        db.close()
        return {
            "status": "ziel",
            "message": f"🏁 ZIEL! Gesamtzeit: {zwischenzeit:.3f}s",
            "gesamtzeit": zwischenzeit,
            "zwischenzeit": zwischenzeit,
            "tor_nr": signal.tor_nr,
            "lauf_id": lauf_id
        }

    # Zwischentor
    db.commit()
    db.close()
    return {
        "status": "zwischen",
        "message": f"✓ Tor {signal.tor_nr} passiert — Zwischenzeit: {zwischenzeit:.3f}s",
        "zwischenzeit": zwischenzeit,
        "tor_nr": signal.tor_nr,
        "naechstes_tor": signal.tor_nr + 1,
        "lauf_id": lauf_id
    }

@app.get("/kamera/lauf/{fahrer_id}")
def aktueller_lauf(fahrer_id: int):
    """Zeigt den aktuellen Lauf-Status eines Fahrers"""
    db = SessionLocal()
    signale = db.query(TorSignal).filter(
        TorSignal.fahrer_id == fahrer_id
    ).order_by(TorSignal.lauf_id.desc(), TorSignal.tor_nr.asc()).all()
    db.close()
    if not signale:
        return {"lauf_id": None, "tore": [], "naechstes_tor": 1}
    lauf_id = signale[0].lauf_id
    tore_dieses_laufs = [s for s in signale if s.lauf_id == lauf_id]
    passierte_tore = [s.tor_nr for s in tore_dieses_laufs]
    naechstes = max(passierte_tore) + 1 if passierte_tore else 1
    return {
        "lauf_id": lauf_id,
        "tore": passierte_tore,
        "naechstes_tor": naechstes if naechstes <= ANZAHL_TORE else None,
        "fertig": naechstes > ANZAHL_TORE
    }

@app.delete("/kamera/lauf/{fahrer_id}/reset")
def lauf_reset(fahrer_id: int):
    """Aktuellen Lauf abbrechen"""
    db = SessionLocal()
    db.query(TorSignal).filter(TorSignal.fahrer_id == fahrer_id).delete()
    db.commit()
    db.close()
    return {"message": "Lauf zurückgesetzt"}

@app.get("/kamera/config")
def kamera_config():
    return {"anzahl_tore": ANZAHL_TORE}

# ── KAMERA SIMULATOR (direkt als HTML) ───────────────────────
@app.get("/simulator", response_class=HTMLResponse)
def simulator():
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KI-Kamera Simulator</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#1a1a2e;min-height:100vh;padding:20px;color:white}}
  .header{{max-width:650px;margin:0 auto 20px;text-align:center}}
  .header h1{{font-size:22px}}
  .header p{{font-size:13px;color:#888;margin-top:4px}}
  .badge{{display:inline-block;background:#C62828;color:white;font-size:11px;font-weight:700;padding:3px 12px;border-radius:20px;margin-bottom:10px;animation:blink 1.5s infinite}}
  @keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0.4}}}}
  .card{{background:#16213e;border-radius:12px;padding:20px;max-width:650px;margin:0 auto 16px;border:1px solid #0f3460}}
  .card h2{{font-size:14px;font-weight:700;color:#C8A415;margin-bottom:14px}}
  select{{width:100%;padding:10px 12px;background:#0f3460;border:1.5px solid #1a4a8a;border-radius:8px;font-size:14px;color:white;outline:none}}
  select:focus{{border-color:#C8A415}}
  .timer{{text-align:center;padding:20px;background:#0f1b2d;border-radius:10px;margin:14px 0;border:1px solid #1a4a8a}}
  .timer-label{{font-size:12px;color:#888;margin-bottom:6px}}
  .timer-zahl{{font-size:48px;font-weight:800;color:#C8A415;font-family:'Courier New',monospace}}
  .timer-zahl.laueft{{animation:pulse 1s infinite}}
  @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.7}}}}
  .tore-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}}
  .tor-btn{{padding:14px 8px;border:none;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;transition:all 0.15s;background:#0f3460;color:#888;border:1.5px solid #1a4a8a}}
  .tor-btn.aktiv{{background:#2E7D32;color:white;border-color:#2E7D32;animation:glow 1s infinite alternate}}
  @keyframes glow{{from{{box-shadow:0 0 5px #2E7D32}}to{{box-shadow:0 0 20px #2E7D32}}}}
  .tor-btn.passiert{{background:#1a4a8a;color:#69F0AE;border-color:#1a4a8a}}
  .tor-btn.ziel-btn{{background:#C62828;color:white;border-color:#C62828}}
  .tor-btn.ziel-btn.aktiv{{animation:glow-red 1s infinite alternate}}
  @keyframes glow-red{{from{{box-shadow:0 0 5px #C62828}}to{{box-shadow:0 0 20px #C62828}}}}
  .tor-btn:disabled{{opacity:0.3;cursor:not-allowed;animation:none}}
  .status{{padding:12px 16px;border-radius:8px;margin-top:12px;font-size:14px;font-weight:600;text-align:center;display:none}}
  .status.ok{{background:#1B5E20;color:#69F0AE}}
  .status.err{{background:#4a0000;color:#FF5252}}
  .status.info{{background:#0d2b5e;color:#82B1FF}}
  .status.zwischen{{background:#1a3060;color:#FFD740}}
  .zeiten-box{{font-size:13px}}
  .zeit-row{{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #1a3060;color:#888}}
  .zeit-row:last-child{{border:none}}
  .zeit-val{{color:#69F0AE;font-family:monospace;font-weight:700}}
  .beste{{color:#C8A415;font-weight:700;margin-top:10px;text-align:right;font-size:14px}}
  .zwischen-list{{margin-top:10px}}
  .zwischen-item{{display:flex;justify-content:space-between;padding:4px 0;font-size:12px;color:#555;border-bottom:1px solid #111}}
  .zwischen-item.aktiv{{color:#FFD740}}
  .reset-btn{{width:100%;padding:8px;background:none;border:1px solid #4a0000;color:#FF5252;border-radius:6px;cursor:pointer;font-size:12px;margin-top:10px}}
  .debug{{background:#0a0a1a;border-radius:8px;padding:12px;font-family:monospace;font-size:11px;color:#555;max-height:150px;overflow-y:auto;margin-top:10px}}
  .debug .ok{{color:#69F0AE}}.debug .err{{color:#FF5252}}.debug .info{{color:#82B1FF}}.debug .w{{color:#FFD740}}
  .nav{{text-align:center;margin-top:16px;font-size:13px;color:#555}}
  .nav a{{color:#C8A415;text-decoration:none;font-weight:600;margin:0 8px}}
</style>
</head>
<body>
<div class="header">
  <div class="badge">● KI-KAMERA SIMULATOR</div>
  <h1>📷 Mehrtor-Kamera-Simulator</h1>
  <p>Simuliert {ANZAHL_TORE} KI-Kameras entlang der Strecke</p>
</div>

<div class="card">
  <h2>🏎️ Fahrer auswählen</h2>
  <select id="fahrerSelect" onchange="fahrerGewaehlt()">
    <option value="">-- Wird geladen... --</option>
  </select>
</div>

<div class="card">
  <h2>📡 Tor-Signale</h2>
  <div class="timer">
    <div class="timer-label" id="timerLabel">Fahrer auswählen um zu starten</div>
    <div class="timer-zahl" id="timerZahl">00.000</div>
  </div>

  <div class="tore-grid" id="toreGrid"></div>

  <div class="zwischen-list" id="zwischenList"></div>
  <div class="status" id="statusBox"></div>
  <button class="reset-btn" id="resetBtn" onclick="laufReset()" style="display:none">
    ✕ Lauf abbrechen / zurücksetzen
  </button>
</div>

<div class="card">
  <h2>🏁 Gespeicherte Zeiten</h2>
  <div class="zeiten-box" id="zeitenBox">
    <p style="color:#555;font-size:13px">Noch keine Zeiten.</p>
  </div>
  <button onclick="zeitenLaden()" style="width:100%;margin-top:12px;padding:8px;background:none;border:1px solid #1a4a8a;color:#888;border-radius:6px;cursor:pointer;font-size:12px">
    ↻ Aktualisieren
  </button>
</div>

<div class="card">
  <h2>📋 Log</h2>
  <div class="debug" id="debugLog"><div class="info">System bereit...</div></div>
</div>

<div class="nav">
  <a href="/app/index.html">📝 Registrierung</a>
  <a href="/app/leaderboard.html">📊 Leaderboard</a>
  <a href="/app/dashboard.html">⚙️ Dashboard</a>
</div>

<script>
const API = '';
const TORE = {ANZAHL_TORE};
let aktiverFahrer = null;
let naechstesTor = 1;
let startTs = null;
let timerInt = null;
let zwischenzeiten = [];

function log(text, typ='info') {{
  const el = document.getElementById('debugLog');
  const now = new Date().toTimeString().slice(0,8);
  el.innerHTML = `<div class="${{typ}}">[${{now}}] ${{text}}</div>` + el.innerHTML;
}}

function statusZeigen(text, typ) {{
  const el = document.getElementById('statusBox');
  el.textContent = text;
  el.className = 'status ' + typ;
  el.style.display = 'block';
}}

function toreAufbauen() {{
  const grid = document.getElementById('toreGrid');
  grid.innerHTML = '';
  for (let i = 1; i <= TORE; i++) {{
    const btn = document.createElement('button');
    btn.className = 'tor-btn' + (i === TORE ? ' ziel-btn' : '');
    btn.id = 'tor-' + i;
    btn.disabled = true;
    btn.textContent = i === 1 ? '🚦 Tor 1\\nSTART' : i === TORE ? `🏁 Tor ${{i}}\\nZIEL` : `📡 Tor ${{i}}`;
    btn.style.whiteSpace = 'pre';
    btn.onclick = () => torSignalSenden(i);
    grid.appendChild(btn);
  }}
}}

function toreUpdaten(naechstes) {{
  for (let i = 1; i <= TORE; i++) {{
    const btn = document.getElementById('tor-' + i);
    if (!btn) continue;
    btn.disabled = true;
    btn.classList.remove('aktiv', 'passiert');
    if (i < naechstes) btn.classList.add('passiert');
    if (i === naechstes) {{
      btn.classList.add('aktiv');
      btn.disabled = false;
    }}
  }}
}}

function timerStarten() {{
  startTs = Date.now();
  zwischenzeiten = [];
  const zahl = document.getElementById('timerZahl');
  zahl.classList.add('laueft');
  document.getElementById('timerLabel').textContent = '⏱️ Lauf läuft...';
  document.getElementById('resetBtn').style.display = 'block';
  timerInt = setInterval(() => {{
    const sek = (Date.now() - startTs) / 1000;
    zahl.textContent = sek.toFixed(3).padStart(6, '0');
  }}, 50);
}}

function timerStoppen(finalSek) {{
  if (timerInt) {{ clearInterval(timerInt); timerInt = null; }}
  const zahl = document.getElementById('timerZahl');
  zahl.classList.remove('laueft');
  if (finalSek !== undefined) zahl.textContent = finalSek.toFixed(3);
  document.getElementById('timerLabel').textContent = 'Lauf beendet — bereit für nächsten';
  document.getElementById('resetBtn').style.display = 'none';
}}

function zwischenzeigUpdaten() {{
  const list = document.getElementById('zwischenList');
  if (zwischenzeiten.length === 0) {{ list.innerHTML = ''; return; }}
  list.innerHTML = zwischenzeiten.map((z, i) =>
    `<div class="zwischen-item aktiv">Tor ${{z.tor}} passiert: <span style="color:#FFD740;font-family:monospace">${{z.zeit.toFixed(3)}}s</span></div>`
  ).join('');
}}

async function fahrerLaden() {{
  try {{
    const res = await fetch(API + '/fahrer');
    const daten = await res.json();
    const sel = document.getElementById('fahrerSelect');
    if (daten.length === 0) {{
      sel.innerHTML = '<option value="">Keine Fahrer registriert</option>';
      return;
    }}
    sel.innerHTML = '<option value="">-- Fahrer auswählen --</option>' +
      daten.map(f => `<option value="${{f.id}}">#${{f.startnummer}} — ${{f.name}} (${{f.fahrzeug}})</option>`).join('');
    log('Fahrer geladen: ' + daten.length, 'ok');
  }} catch(e) {{ log('Fehler: ' + e.message, 'err'); }}
}}

function fahrerGewaehlt() {{
  const sel = document.getElementById('fahrerSelect');
  aktiverFahrer = sel.value ? parseInt(sel.value) : null;
  if (!aktiverFahrer) {{
    toreUpdaten(0);
    document.getElementById('timerLabel').textContent = 'Fahrer auswählen um zu starten';
    document.getElementById('timerZahl').textContent = '00.000';
    document.getElementById('zwischenList').innerHTML = '';
    document.getElementById('resetBtn').style.display = 'none';
    if (timerInt) {{ clearInterval(timerInt); timerInt = null; }}
    return;
  }}
  naechstesTor = 1;
  toreUpdaten(1);
  document.getElementById('timerLabel').textContent = 'Bereit — Tor 1 (Start) drücken';
  document.getElementById('timerZahl').textContent = '00.000';
  document.getElementById('zwischenList').innerHTML = '';
  statusZeigen('✓ Fahrer ausgewählt — Tor 1 drücken um Lauf zu starten', 'info');
  log('Fahrer: ID ' + aktiverFahrer, 'info');
  zeitenLaden();
}}

async function torSignalSenden(torNr) {{
  if (!aktiverFahrer) return;
  const ts = Date.now() / 1000;
  document.getElementById('tor-' + torNr).disabled = true;
  log(`Tor ${{torNr}} Signal — ts: ${{ts.toFixed(3)}}`, 'info');
  try {{
    const res = await fetch(API + '/kamera/tor', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{fahrer_id: aktiverFahrer, tor_nr: torNr, zeitstempel: ts}})
    }});
    const data = await res.json();
    if (!res.ok) {{
      statusZeigen('Fehler: ' + data.detail, 'err');
      log('Fehler: ' + data.detail, 'err');
      document.getElementById('tor-' + torNr).disabled = false;
      return;
    }}
    log(data.message, 'ok');

    if (data.status === 'start') {{
      timerStarten();
      naechstesTor = 2;
      toreUpdaten(2);
      statusZeigen('🚦 START! Lauf ' + data.lauf_id + ' — weiter zu Tor 2', 'info');

    }} else if (data.status === 'zwischen') {{
      zwischenzeiten.push({{tor: torNr, zeit: data.zwischenzeit}});
      zwischenzeigUpdaten();
      naechstesTor = data.naechstes_tor;
      toreUpdaten(naechstesTor);
      statusZeigen(`✓ Tor ${{torNr}} — ${{data.zwischenzeit.toFixed(3)}}s — weiter zu Tor ${{data.naechstes_tor}}`, 'zwischen');

    }} else if (data.status === 'ziel') {{
      timerStoppen(data.gesamtzeit);
      toreUpdaten(0);
      statusZeigen(`🏁 ZIEL! Gesamtzeit: ${{data.gesamtzeit.toFixed(3)}} Sekunden`, 'ok');
      zwischenzeiten.push({{tor: torNr, zeit: data.gesamtzeit}});
      zwischenzeigUpdaten();
      naechstesTor = 1;
      setTimeout(() => {{
        toreUpdaten(1);
        document.getElementById('timerLabel').textContent = 'Bereit für nächsten Lauf — Tor 1 drücken';
        document.getElementById('zwischenList').innerHTML = '';
      }}, 4000);
      zeitenLaden();
    }}

  }} catch(e) {{
    log('Netzwerkfehler: ' + e.message, 'err');
    statusZeigen('Server nicht erreichbar!', 'err');
    document.getElementById('tor-' + torNr).disabled = false;
  }}
}}

async function laufReset() {{
  if (!aktiverFahrer) return;
  if (!confirm('Aktuellen Lauf abbrechen?')) return;
  try {{
    await fetch(API + '/kamera/lauf/' + aktiverFahrer + '/reset', {{method: 'DELETE'}});
    if (timerInt) {{ clearInterval(timerInt); timerInt = null; }}
    naechstesTor = 1;
    toreUpdaten(1);
    document.getElementById('timerZahl').textContent = '00.000';
    document.getElementById('timerLabel').textContent = 'Lauf abgebrochen — Tor 1 drücken';
    document.getElementById('zwischenList').innerHTML = '';
    document.getElementById('resetBtn').style.display = 'none';
    statusZeigen('Lauf zurückgesetzt', 'info');
    log('Lauf abgebrochen', 'w');
  }} catch(e) {{ log('Reset Fehler: ' + e.message, 'err'); }}
}}

async function zeitenLaden() {{
  if (!aktiverFahrer) return;
  try {{
    const res = await fetch(API + '/zeiten/' + aktiverFahrer);
    const zeiten = await res.json();
    const box = document.getElementById('zeitenBox');
    if (zeiten.length === 0) {{
      box.innerHTML = '<p style="color:#555;font-size:13px">Noch keine Zeiten.</p>';
      return;
    }}
    const beste = Math.min(...zeiten.map(z => z.gesamtzeit));
    box.innerHTML = zeiten.map((z, i) => `
      <div class="zeit-row">
        <span>Lauf ${{i+1}}</span>
        <span>${{z.rundenzeit.toFixed(3)}}s</span>
        <span class="zeit-val">${{z.gesamtzeit.toFixed(3)}}s</span>
      </div>`).join('') +
      `<div class="beste">⭐ Beste Zeit: ${{beste.toFixed(3)}}s</div>`;
  }} catch(e) {{ log('Fehler Zeiten: ' + e.message, 'err'); }}
}}

// ── PDF Export ─────────────────────────────────────────────
toreAufbauen();
fahrerLaden();
</script>
</body>
</html>"""
    return HTMLResponse(content=html)

# ── PDF Export ───────────────────────────────────────────────
@app.get("/ergebnisse/pdf", response_class=HTMLResponse)
def ergebnisse_pdf():
    db = SessionLocal()
    fahrer_liste = db.query(Fahrer).all()
    status = db.query(RennStatus).first()
    ergebnis = []
    for fahrer in fahrer_liste:
        zeiten = db.query(Zeit).filter(Zeit.fahrer_id == fahrer.id).all()
        beste_zeit = min((z.gesamtzeit for z in zeiten), default=None)
        strafzeiten = db.query(Strafzeit).filter(Strafzeit.fahrer_id == fahrer.id).all()
        gesamt_strafe = sum(s.strafzeit for s in strafzeiten)
        ergebnis.append({"startnummer": fahrer.startnummer, "name": fahrer.name,
                         "fahrzeug": fahrer.fahrzeug, "beste_zeit": beste_zeit,
                         "gesamt_strafe": gesamt_strafe, "anzahl_laeufe": len(zeiten)})
    db.close()
    ergebnis.sort(key=lambda x: (x["beste_zeit"] is None, x["beste_zeit"]))
    def fmt(s):
        if s is None: return "—"
        m = int(s // 60)
        r = s % 60
        return f"{m}:{r:05.2f} min" if m > 0 else f"{r:.2f} s"
    plaetze = ["🥇","🥈","🥉"]
    zeilen = ""
    for i, f in enumerate(ergebnis):
        platz = plaetze[i] if i < 3 else str(i+1)+"."
        bg = "#FFF8E1" if i==0 else "#F5F5F5" if i==1 else "#FFF3E0" if i==2 else "white"
        zeilen += f'<tr style="background:{bg}"><td style="text-align:center;font-size:20px">{platz}</td><td><strong>{f["name"]}</strong></td><td>{f["fahrzeug"]}</td><td style="text-align:center">#{f["startnummer"]}</td><td style="text-align:center">{f["anzahl_laeufe"]}</td><td style="text-align:center;color:#C62828;font-weight:700">{("+" + str(f["gesamt_strafe"]) + "s") if f["gesamt_strafe"] > 0 else "—"}</td><td style="text-align:center;font-family:monospace;font-weight:700;font-size:16px">{fmt(f["beste_zeit"])}</td></tr>'
    abschluss = f"Abgeschlossen: {status.abgeschlossen_um}" if status and status.abgeschlossen_um else "Rennen läuft noch"
    return HTMLResponse(f"""<!DOCTYPE html><html lang="de"><head><meta charset="UTF-8"><title>Ergebnisse</title>
<style>body{{font-family:'Segoe UI',Arial,sans-serif;padding:40px;color:#2B2B2B}}h1{{font-size:28px;margin-bottom:4px}}.sub{{color:#888;font-size:14px;margin-bottom:30px}}table{{width:100%;border-collapse:collapse}}th{{background:#2B2B2B;color:white;padding:12px;font-size:13px}}td{{padding:12px;border-bottom:1px solid #F0F0F0}}@media print{{button{{display:none}}}}</style>
</head><body><h1>🏁 RC-Car Rally — Ergebnisse</h1><p class="sub">{abschluss} | {len(ergebnis)} Fahrer</p>
<button onclick="window.print()" style="background:#2B2B2B;color:white;border:none;padding:10px 24px;border-radius:8px;font-size:14px;cursor:pointer;margin-bottom:24px">🖨️ Drucken / Als PDF</button>
<table><thead><tr><th>Platz</th><th>Name</th><th>Fahrzeug</th><th>Start-Nr.</th><th>Läufe</th><th>Strafzeit</th><th>Beste Zeit</th></tr></thead><tbody>{zeilen}</tbody></table></body></html>""")

# ── Frontend Static Files ─────────────────────────────────────
import os
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")