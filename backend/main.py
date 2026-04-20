from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
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

Base.metadata.create_all(bind=engine)

# Renn-Status initialisieren falls noch nicht vorhanden
def init_status():
    db = SessionLocal()
    if db.query(RennStatus).count() == 0:
        db.add(RennStatus(abgeschlossen=False))
        db.commit()
    db.close()

init_status()

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

# ── Hilfsfunktion ────────────────────────────────────────────
def rennen_offen():
    db = SessionLocal()
    status = db.query(RennStatus).first()
    db.close()
    return not status.abgeschlossen

# ── Endpunkte ────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "PMK RC-Rally API läuft!"}

@app.get("/status")
def status():
    db = SessionLocal()
    s = db.query(RennStatus).first()
    db.close()
    return {
        "abgeschlossen": s.abgeschlossen,
        "abgeschlossen_um": s.abgeschlossen_um
    }

@app.post("/fahrer")
def fahrer_registrieren(fahrer: FahrerCreate):
    if not rennen_offen():
        raise HTTPException(status_code=403, detail="Rennen ist bereits abgeschlossen")
    if not fahrer.einwilligung:
        raise HTTPException(status_code=400, detail="Einwilligung erforderlich")
    db = SessionLocal()
    vorhanden = db.query(Fahrer).filter(Fahrer.email == fahrer.email).first()
    if vorhanden:
        db.close()
        raise HTTPException(status_code=400, detail="Diese E-Mail ist bereits registriert")
    neuer_fahrer = Fahrer(
        name=fahrer.name,
        email=fahrer.email,
        fahrzeug=fahrer.fahrzeug,
        einwilligung=fahrer.einwilligung,
        startnummer=db.query(Fahrer).count() + 1
    )
    db.add(neuer_fahrer)
    db.commit()
    db.refresh(neuer_fahrer)
    db.close()
    qr_url = f"http://127.0.0.1:8000/fahrer/{neuer_fahrer.id}/qrcode"
    return {
        "message": f"Fahrer {fahrer.name} registriert!",
        "startnummer": neuer_fahrer.startnummer,
        "qr_code_url": qr_url
    }

@app.get("/fahrer")
def alle_fahrer():
    db = SessionLocal()
    fahrer = db.query(Fahrer).all()
    db.close()
    return fahrer

@app.get("/fahrer/{fahrer_id}/qrcode")
def qrcode_generieren(fahrer_id: int):
    db = SessionLocal()
    fahrer = db.query(Fahrer).filter(Fahrer.id == fahrer_id).first()
    db.close()
    if not fahrer:
        raise HTTPException(status_code=404, detail="Fahrer nicht gefunden")
    inhalt = f"Fahrer: {fahrer.name}\nStartnummer: {fahrer.startnummer}\nFahrzeug: {fahrer.fahrzeug}"
    img = qrcode.make(inhalt)
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
    return {"message": f"Fahrer {fahrer.name} erfolgreich eingecheckt!",
            "startnummer": fahrer.startnummer}

@app.post("/zeiten")
def zeit_eintragen(z: ZeitCreate):
    if not rennen_offen():
        raise HTTPException(status_code=403, detail="Rennen ist bereits abgeschlossen")
    db = SessionLocal()
    fahrer = db.query(Fahrer).filter(Fahrer.id == z.fahrer_id).first()
    if not fahrer:
        db.close()
        raise HTTPException(status_code=404, detail="Fahrer nicht gefunden")
    neue_zeit = Zeit(
        fahrer_id=z.fahrer_id,
        rundenzeit=z.rundenzeit,
        strafzeit=z.strafzeit,
        gesamtzeit=z.rundenzeit + z.strafzeit
    )
    db.add(neue_zeit)
    db.commit()
    db.close()
    return {"message": "Zeit eingetragen", "gesamtzeit": neue_zeit.gesamtzeit}

@app.get("/zeiten/{fahrer_id}")
def zeiten_von_fahrer(fahrer_id: int):
    db = SessionLocal()
    zeiten = db.query(Zeit).filter(Zeit.fahrer_id == fahrer_id).all()
    db.close()
    return zeiten

@app.post("/strafzeiten")
def strafzeit_hinzufuegen(s: StrafzeitCreate):
    if not rennen_offen():
        raise HTTPException(status_code=403, detail="Rennen ist bereits abgeschlossen")
    db = SessionLocal()
    fahrer = db.query(Fahrer).filter(Fahrer.id == s.fahrer_id).first()
    if not fahrer:
        db.close()
        raise HTTPException(status_code=404, detail="Fahrer nicht gefunden")
    neue_strafe = Strafzeit(
        fahrer_id=s.fahrer_id,
        strafzeit=s.strafzeit,
        grund=s.grund
    )
    db.add(neue_strafe)
    letzte_zeit = db.query(Zeit).filter(
        Zeit.fahrer_id == s.fahrer_id
    ).order_by(Zeit.id.desc()).first()
    if letzte_zeit:
        letzte_zeit.strafzeit += s.strafzeit
        letzte_zeit.gesamtzeit += s.strafzeit
    db.commit()
    db.close()
    return {"message": f"Strafzeit von {s.strafzeit}s für {fahrer.name} eingetragen",
            "grund": s.grund}

@app.get("/leaderboard")
def leaderboard():
    db = SessionLocal()
    fahrer_liste = db.query(Fahrer).all()
    ergebnis = []
    for fahrer in fahrer_liste:
        zeiten = db.query(Zeit).filter(Zeit.fahrer_id == fahrer.id).all()
        beste_zeit = min((z.gesamtzeit for z in zeiten), default=None)
        strafzeiten = db.query(Strafzeit).filter(Strafzeit.fahrer_id == fahrer.id).all()
        gesamt_strafe = sum(s.strafzeit for s in strafzeiten)
        ergebnis.append({
            "startnummer": fahrer.startnummer,
            "name": fahrer.name,
            "fahrzeug": fahrer.fahrzeug,
            "eingecheckt": fahrer.eingecheckt,
            "beste_gesamtzeit": beste_zeit,
            "gesamt_strafzeit": gesamt_strafe,
            "anzahl_laeufe": len(zeiten)
        })
    db.close()
    ergebnis.sort(key=lambda x: (x["beste_gesamtzeit"] is None, x["beste_gesamtzeit"]))
    return ergebnis

@app.post("/rennen/abschliessen")
def rennen_abschliessen():
    if not rennen_offen():
        raise HTTPException(status_code=400, detail="Rennen ist bereits abgeschlossen")
    db = SessionLocal()
    status = db.query(RennStatus).first()
    status.abgeschlossen = True
    status.abgeschlossen_um = datetime.now().strftime("%d.%m.%Y um %H:%M Uhr")
    db.commit()
    db.close()
    return {"message": "Rennen erfolgreich abgeschlossen!"}

@app.post("/rennen/reset")
def rennen_reset():
    db = SessionLocal()
    status = db.query(RennStatus).first()
    status.abgeschlossen = False
    status.abgeschlossen_um = None
    db.commit()
    db.close()
    return {"message": "Rennen wieder geöffnet"}

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
        ergebnis.append({
            "startnummer": fahrer.startnummer,
            "name": fahrer.name,
            "fahrzeug": fahrer.fahrzeug,
            "beste_zeit": beste_zeit,
            "gesamt_strafe": gesamt_strafe,
            "anzahl_laeufe": len(zeiten)
        })
    db.close()
    ergebnis.sort(key=lambda x: (x["beste_zeit"] is None, x["beste_zeit"]))

    def fmt(sek):
        if sek is None: return "—"
        m = int(sek // 60)
        s = sek % 60
        return f"{m}:{s:05.2f} min" if m > 0 else f"{s:.2f} s"

    plaetze = ["🥇", "🥈", "🥉"]
    zeilen = ""
    for i, f in enumerate(ergebnis):
        platz = plaetze[i] if i < 3 else str(i + 1) + "."
        bg = "#FFF8E1" if i == 0 else "#F5F5F5" if i == 1 else "#FFF3E0" if i == 2 else "white"
        zeilen += f"""
        <tr style="background:{bg}">
          <td style="text-align:center;font-size:20px">{platz}</td>
          <td><strong>{f['name']}</strong></td>
          <td>{f['fahrzeug']}</td>
          <td style="text-align:center">#{f['startnummer']}</td>
          <td style="text-align:center">{f['anzahl_laeufe']}</td>
          <td style="text-align:center;color:#C62828;font-weight:700">
            {f'+' + str(f['gesamt_strafe']) + 's' if f['gesamt_strafe'] > 0 else '—'}
          </td>
          <td style="text-align:center;font-family:monospace;font-weight:700;font-size:16px">
            {fmt(f['beste_zeit'])}
          </td>
        </tr>"""

    abschluss = f"Abgeschlossen: {status.abgeschlossen_um}" if status and status.abgeschlossen_um else ""
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>RC-Car Rally — Ergebnisse</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; color: #2B2B2B; }}
  h1 {{ font-size: 28px; margin-bottom: 4px; }}
  .sub {{ color: #888; font-size: 14px; margin-bottom: 30px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #2B2B2B; color: white; padding: 12px; font-size: 13px; }}
  td {{ padding: 12px; border-bottom: 1px solid #F0F0F0; }}
  .gold {{ color: #C8A415; font-weight: 700; }}
  @media print {{
    button {{ display: none; }}
    body {{ padding: 20px; }}
  }}
</style>
</head>
<body>
<h1>🏁 RC-Car Rally — Ergebnisse</h1>
<p class="sub">{abschluss} &nbsp;|&nbsp; {len(ergebnis)} Fahrer</p>
<button onclick="window.print()"
  style="background:#2B2B2B;color:white;border:none;padding:10px 24px;border-radius:8px;font-size:14px;cursor:pointer;margin-bottom:24px">
  🖨️ Drucken / Als PDF speichern
</button>
<table>
  <thead>
    <tr>
      <th>Platz</th>
      <th>Name</th>
      <th>Fahrzeug</th>
      <th>Start-Nr.</th>
      <th>Läufe</th>
      <th>Strafzeit</th>
      <th>Beste Zeit</th>
    </tr>
  </thead>
  <tbody>{zeilen}</tbody>
</table>
</body>
</html>"""
    return HTMLResponse(content=html)