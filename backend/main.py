import hashlib
import secrets
import socket
import os
import io
import csv
import smtplib
import threading
from datetime import datetime, timedelta
from typing import Optional, List
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import qrcode
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler

# ── Konfiguration ─────────────────────────────────────────────
GMAIL_USER  = os.getenv("GMAIL_USER",  "pmkrccarrally@gmail.com")
GMAIL_PW    = os.getenv("GMAIL_APP_PW", "")
APP_URL     = os.getenv("APP_URL",     "http://localhost:8000")
ANZAHL_TORE = int(os.getenv("ANZAHL_TORE", "6"))

# ── Datenbank ─────────────────────────────────────────────────
DATABASE_URL = "sqlite:///./rally.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ── ORM-Modelle ───────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    name          = Column(String)
    email         = Column(String, unique=True, nullable=False)
    passwort_hash = Column(String, nullable=False)
    rolle         = Column(String, default="fahrer")
    token         = Column(String, unique=True, nullable=True)

class Rennen(Base):
    __tablename__    = "rennen"
    id               = Column(Integer, primary_key=True)
    name             = Column(String, nullable=False)
    datum            = Column(String)
    uhrzeit          = Column(String)
    ort              = Column(String)
    ort_link         = Column(String, nullable=True)
    beschreibung     = Column(Text, nullable=True)
    max_teilnehmer   = Column(Integer, default=50)
    status           = Column(String, default="offen")
    erstellt_am      = Column(String)
    # Fahrzeugvorgaben
    fahrzeug_klasse  = Column(String, nullable=True)
    reifen_vorgabe   = Column(String, nullable=True)
    max_breite_mm    = Column(Integer, nullable=True)
    sonstige_regeln  = Column(Text, nullable=True)

class RennAnmeldung(Base):
    __tablename__        = "renn_anmeldungen"
    id                   = Column(Integer, primary_key=True)
    user_id              = Column(Integer)
    rennen_id            = Column(Integer, nullable=True)
    fahrzeug             = Column(String)
    einwilligung         = Column(Boolean, default=False)
    startnummer          = Column(Integer)
    eingecheckt          = Column(Boolean, default=False)
    erinnerung_gesendet  = Column(Boolean, default=False)

class Zeit(Base):
    __tablename__ = "zeiten"
    id            = Column(Integer, primary_key=True)
    fahrer_id     = Column(Integer)
    rennen_id     = Column(Integer, nullable=True)
    rundenzeit    = Column(Float)
    strafzeit     = Column(Float, default=0.0)
    gesamtzeit    = Column(Float)

class Strafzeit(Base):
    __tablename__ = "strafzeiten"
    id            = Column(Integer, primary_key=True)
    fahrer_id     = Column(Integer)
    rennen_id     = Column(Integer, nullable=True)
    strafzeit     = Column(Float)
    grund         = Column(String)

class TorSignal(Base):
    __tablename__ = "tor_signale"
    id            = Column(Integer, primary_key=True)
    fahrer_id     = Column(Integer)
    rennen_id     = Column(Integer, nullable=True)
    tor_nr        = Column(Integer)
    zeitstempel   = Column(Float)
    lauf_id       = Column(Integer)

Base.metadata.create_all(bind=engine)

# ── DB-Migration (bestehende DBs upgraden) ────────────────────
def _migrate_db():
    import sqlite3
    con = sqlite3.connect("./rally.db")
    cur = con.cursor()
    migrations = [
        ("renn_anmeldungen", "rennen_id",           "INTEGER DEFAULT NULL"),
        ("renn_anmeldungen", "erinnerung_gesendet", "INTEGER DEFAULT 0"),
        ("zeiten",           "rennen_id",           "INTEGER DEFAULT NULL"),
        ("strafzeiten",      "rennen_id",           "INTEGER DEFAULT NULL"),
        ("rennen",           "ort_link",            "TEXT DEFAULT NULL"),
        ("rennen",           "fahrzeug_klasse",     "TEXT DEFAULT NULL"),
        ("rennen",           "reifen_vorgabe",      "TEXT DEFAULT NULL"),
        ("rennen",           "max_breite_mm",       "INTEGER DEFAULT NULL"),
        ("rennen",           "sonstige_regeln",     "TEXT DEFAULT NULL"),
        ("tor_signale",      "rennen_id",           "INTEGER DEFAULT NULL"),
    ]
    for table, col, typedef in migrations:
        try:
            cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
            if col not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")
        except Exception:
            pass
    con.commit()
    con.close()

_migrate_db()

# ── Helpers ───────────────────────────────────────────────────
def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _new_token() -> str:
    return secrets.token_hex(32)

def _get_user_by_token(token: str):
    if not token:
        return None
    db = SessionLocal()
    u = db.query(User).filter(User.token == token).first()
    db.close()
    return u

def _require_admin(authorization: str = Header(None)):
    token = (authorization or "").replace("Bearer ", "")
    user = _get_user_by_token(token)
    if not user or user.rolle != "admin":
        raise HTTPException(status_code=403, detail="Nur für Admins")
    return user

def _require_auth(authorization: str = Header(None)):
    token = (authorization or "").replace("Bearer ", "")
    user = _get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Nicht eingeloggt")
    return user

def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def _rennen_dict(r, teilnehmer_count=0):
    return {
        "id": r.id, "name": r.name, "datum": r.datum, "uhrzeit": r.uhrzeit,
        "ort": r.ort, "ort_link": r.ort_link, "beschreibung": r.beschreibung,
        "max_teilnehmer": r.max_teilnehmer, "status": r.status,
        "erstellt_am": r.erstellt_am, "teilnehmer_count": teilnehmer_count,
        "fahrzeug_klasse": r.fahrzeug_klasse, "reifen_vorgabe": r.reifen_vorgabe,
        "max_breite_mm": r.max_breite_mm, "sonstige_regeln": r.sonstige_regeln,
    }

def _parse_rennen_dt(datum, uhrzeit):
    try:
        return datetime.fromisoformat(f"{datum}T{uhrzeit or '00:00'}")
    except Exception:
        return None

def _fmt_datum_de(datum, uhrzeit):
    dt = _parse_rennen_dt(datum, uhrzeit)
    if not dt:
        return f"{datum or ''} {uhrzeit or ''}".strip()
    return dt.strftime("%d.%m.%Y") + (f" um {uhrzeit} Uhr" if uhrzeit else "")

def _make_qr_png(user_id: int) -> bytes:
    img = qrcode.make(f"CHECKIN:{user_id}")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def _html_esc(s) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ── E-Mail ────────────────────────────────────────────────────
def _send_mail(to: str, subject: str, html: str, qr_png: bytes = None):
    if not GMAIL_PW:
        print(f"[Mail] Kein App-Passwort — Mail an {to} nicht gesendet.")
        return
    try:
        msg = MIMEMultipart("related")
        msg["From"]    = f"PMK RC-Car Rally <{GMAIL_USER}>"
        msg["To"]      = to
        msg["Subject"] = subject
        alt = MIMEMultipart("alternative")
        msg.attach(alt)
        alt.attach(MIMEText(html, "html", "utf-8"))
        if qr_png:
            img_part = MIMEImage(qr_png, "png")
            img_part.add_header("Content-ID", "<qrcode>")
            img_part.add_header("Content-Disposition", "inline", filename="qrcode.png")
            msg.attach(img_part)
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(GMAIL_USER, GMAIL_PW)
            s.sendmail(GMAIL_USER, to, msg.as_string())
        print(f"[Mail] ✓ Gesendet an {to}: {subject}")
    except Exception as e:
        print(f"[Mail] ✗ Fehler: {e}")

def _mail_bestaetigung(user_name, user_email, user_id, rennen, startnummer):
    datum_str = _fmt_datum_de(rennen.datum, rennen.uhrzeit)
    ort_link  = (f'<a href="{rennen.ort_link}" style="color:#F59E0B">{rennen.ort}</a>'
                 if rennen.ort_link else rennen.ort)
    html = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#09090B;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:560px;margin:32px auto;background:#18181B;border-radius:14px;overflow:hidden;border:1px solid #3F3F46;">
  <div style="background:#0F172A;padding:28px 32px;text-align:center;border-bottom:1px solid #3F3F46;">
    <div style="font-size:28px;margin-bottom:6px;">🏁</div>
    <div style="font-size:20px;font-weight:800;color:#FAFAFA;">PMK RC-Car <span style="color:#F59E0B;">Rally</span></div>
    <div style="font-size:12px;color:#71717A;margin-top:4px;">Anmeldebestätigung</div>
  </div>
  <div style="padding:28px 32px;">
    <p style="color:#FAFAFA;font-size:16px;font-weight:700;margin:0 0 6px;">Hallo {_html_esc(user_name)}! 👋</p>
    <p style="color:#A1A1AA;font-size:14px;margin:0 0 24px;line-height:1.6;">
      Du bist erfolgreich für das Rennen angemeldet. Zeige deinen QR-Code beim Check-in vor.
    </p>
    <div style="background:#09090B;border:1px solid #3F3F46;border-radius:10px;padding:18px 20px;margin-bottom:20px;">
      <div style="font-size:16px;font-weight:800;color:#FAFAFA;margin-bottom:12px;">{_html_esc(rennen.name)}</div>
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="padding:5px 0;font-size:12px;color:#71717A;width:90px;">📅 Datum</td>
            <td style="padding:5px 0;font-size:13px;color:#FAFAFA;font-weight:600;">{datum_str}</td></tr>
        <tr><td style="padding:5px 0;font-size:12px;color:#71717A;">📍 Ort</td>
            <td style="padding:5px 0;font-size:13px;color:#FAFAFA;font-weight:600;">{ort_link}</td></tr>
        <tr><td style="padding:5px 0;font-size:12px;color:#71717A;">🔢 Startnummer</td>
            <td style="padding:5px 0;font-size:22px;font-weight:900;color:#F59E0B;">#{startnummer}</td></tr>
      </table>
    </div>
    <div style="text-align:center;margin-bottom:24px;">
      <div style="font-size:12px;color:#71717A;margin-bottom:10px;text-transform:uppercase;letter-spacing:0.5px;">Dein Check-in QR-Code</div>
      <img src="cid:qrcode" alt="QR-Code" width="180" height="180"
           style="border-radius:10px;background:white;padding:12px;display:block;margin:0 auto;">
      <div style="font-size:11px;color:#71717A;margin-top:8px;">Beim Check-in vorzeigen</div>
    </div>
    <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);border-radius:8px;padding:14px 16px;margin-bottom:20px;">
      <div style="font-size:12px;font-weight:700;color:#F59E0B;margin-bottom:6px;">📋 Wichtige Hinweise</div>
      <ul style="margin:0;padding-left:16px;color:#A1A1AA;font-size:12px;line-height:1.8;">
        <li>Mindestens 30 Minuten vor Start erscheinen</li>
        <li>Vollgeladene Akkus (mind. 2) mitbringen</li>
        <li>Fahrzeug muss fahrbereit sein</li>
        <li>Fahrermeeting 15 Min. vor Start — Anwesenheit Pflicht</li>
      </ul>
    </div>
  </div>
  <div style="padding:16px 32px;border-top:1px solid #3F3F46;text-align:center;">
    <div style="font-size:11px;color:#71717A;">PMK RC-Car Rally · Hochschule Pforzheim</div>
  </div>
</div>
</body></html>"""
    qr = _make_qr_png(user_id)
    threading.Thread(target=_send_mail,
                     args=(user_email, f"✅ Anmeldung bestätigt: {rennen.name}", html, qr),
                     daemon=True).start()

def _mail_erinnerung(user_name, user_email, user_id, rennen, startnummer):
    datum_str = _fmt_datum_de(rennen.datum, rennen.uhrzeit)
    html = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#09090B;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:560px;margin:32px auto;background:#18181B;border-radius:14px;overflow:hidden;border:1px solid #3F3F46;">
  <div style="background:#0F172A;padding:28px 32px;text-align:center;border-bottom:1px solid #3F3F46;">
    <div style="font-size:28px;margin-bottom:6px;">⏰</div>
    <div style="font-size:20px;font-weight:800;color:#FAFAFA;">Startet in <span style="color:#F59E0B;">2 Stunden!</span></div>
  </div>
  <div style="padding:28px 32px;">
    <p style="color:#FAFAFA;font-size:16px;font-weight:700;margin:0 0 6px;">Hey {_html_esc(user_name)}! 🏎️</p>
    <p style="color:#A1A1AA;font-size:14px;margin:0 0 24px;">In <strong style="color:#F59E0B;">2 Stunden</strong> startet {_html_esc(rennen.name)}. Startnummer: <strong style="color:#F59E0B;">#{startnummer}</strong></p>
    <p style="color:#A1A1AA;font-size:13px;">{datum_str} · {_html_esc(rennen.ort or '')}</p>
    <div style="text-align:center;margin-top:20px;">
      <img src="cid:qrcode" alt="QR-Code" width="160" height="160"
           style="border-radius:10px;background:white;padding:10px;display:block;margin:0 auto;">
      <div style="font-size:11px;color:#71717A;margin-top:6px;">Check-in QR-Code bereithalten</div>
    </div>
  </div>
</div>
</body></html>"""
    qr = _make_qr_png(user_id)
    threading.Thread(target=_send_mail,
                     args=(user_email, f"⏰ Startet in 2h: {rennen.name}", html, qr),
                     daemon=True).start()

# ── 2h-Reminder Scheduler ─────────────────────────────────────
def _check_reminders():
    now   = datetime.now()
    w_low  = now + timedelta(hours=2) - timedelta(minutes=5)
    w_high = now + timedelta(hours=2) + timedelta(minutes=5)
    try:
        db = SessionLocal()
        for r in db.query(Rennen).filter(Rennen.status != "abgeschlossen").all():
            rt = _parse_rennen_dt(r.datum, r.uhrzeit)
            if not rt or not (w_low <= rt <= w_high):
                continue
            for a in db.query(RennAnmeldung).filter(
                RennAnmeldung.rennen_id == r.id,
                RennAnmeldung.erinnerung_gesendet == False,
            ).all():
                u = db.query(User).filter(User.id == a.user_id).first()
                if u and u.email:
                    _mail_erinnerung(u.name, u.email, u.id, r, a.startnummer)
                a.erinnerung_gesendet = True
        db.commit()
        db.close()
    except Exception as e:
        print(f"[Reminder] Fehler: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(_check_reminders, "interval", minutes=5, id="reminder_check")
scheduler.start()

# ── FastAPI App ───────────────────────────────────────────────
app = FastAPI(title="PMK RC-Rally API v2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic Schemas ──────────────────────────────────────────
class RegisterSchema(BaseModel):
    name: str
    email: str
    passwort: str

class LoginSchema(BaseModel):
    email: str
    passwort: str

class RennenSchema(BaseModel):
    name: str
    datum: str
    uhrzeit: str
    ort: str
    ort_link: Optional[str] = None
    beschreibung: Optional[str] = None
    max_teilnehmer: int = 50
    fahrzeug_klasse: Optional[str] = None
    reifen_vorgabe: Optional[str] = None
    max_breite_mm: Optional[int] = None
    sonstige_regeln: Optional[str] = None

class RennAnmeldungSchema(BaseModel):
    fahrzeug: str
    einwilligung: bool

class ManuelleAnmeldungSchema(BaseModel):
    name: str
    email: Optional[str] = None
    fahrzeug: str

class ZeitSchema(BaseModel):
    fahrer_id: int
    rennen_id: int
    rundenzeit: float

class StrafzeitSchema(BaseModel):
    fahrer_id: int
    rennen_id: int
    strafzeit: float
    grund: str

class TorSignalSchema(BaseModel):
    fahrer_id: int
    rennen_id: int
    tor_nr: int
    zeitstempel: float

# ── Auth ──────────────────────────────────────────────────────
@app.post("/auth/register")
def register(data: RegisterSchema):
    if not data.name.strip() or not data.email.strip() or not data.passwort.strip():
        raise HTTPException(400, "Alle Felder erforderlich")
    db = SessionLocal()
    if db.query(User).filter(User.email == data.email.lower()).first():
        db.close()
        raise HTTPException(400, "E-Mail bereits registriert")
    user = User(name=data.name.strip(), email=data.email.lower().strip(),
                passwort_hash=_hash(data.passwort), rolle="fahrer", token=None)
    db.add(user)
    db.commit()
    db.refresh(user)
    uid, uname = user.id, user.name
    db.close()
    return {"message": f"Account für {uname} erstellt", "id": uid}

@app.post("/auth/login")
def login(data: LoginSchema):
    db = SessionLocal()
    user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if not user or user.passwort_hash != _hash(data.passwort):
        db.close()
        raise HTTPException(401, "E-Mail oder Passwort falsch")
    token = _new_token()
    user.token = token
    db.commit()
    uid, uname, uemail, urolle = user.id, user.name, user.email, user.rolle
    db.close()
    return {"token": token, "rolle": urolle, "name": uname, "email": uemail, "id": uid}

@app.post("/auth/logout")
def logout(user: User = Depends(_require_auth)):
    db = SessionLocal()
    db.query(User).filter(User.id == user.id).first().token = None
    db.commit()
    db.close()
    return {"message": "Ausgeloggt"}

@app.get("/auth/me")
def me(user: User = Depends(_require_auth)):
    db = SessionLocal()
    count = db.query(RennAnmeldung).filter(RennAnmeldung.user_id == user.id).count()
    db.close()
    return {"id": user.id, "name": user.name, "email": user.email,
            "rolle": user.rolle, "anmeldungen_count": count}

# ── Rennen CRUD ───────────────────────────────────────────────
@app.get("/rennen")
def alle_rennen():
    db = SessionLocal()
    rennen = db.query(Rennen).order_by(Rennen.datum.asc()).all()
    result = [_rennen_dict(r, db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == r.id).count())
              for r in rennen]
    db.close()
    return result

@app.post("/rennen")
def rennen_erstellen(data: RennenSchema, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = Rennen(
        name=data.name.strip(), datum=data.datum, uhrzeit=data.uhrzeit,
        ort=data.ort.strip(), ort_link=data.ort_link or None,
        beschreibung=data.beschreibung, max_teilnehmer=data.max_teilnehmer,
        status="offen", erstellt_am=datetime.now().strftime("%d.%m.%Y"),
        fahrzeug_klasse=data.fahrzeug_klasse, reifen_vorgabe=data.reifen_vorgabe,
        max_breite_mm=data.max_breite_mm, sonstige_regeln=data.sonstige_regeln,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    result = _rennen_dict(r, 0)
    db.close()
    return result

@app.get("/rennen/{rennen_id}")
def rennen_detail(rennen_id: int):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")
    count = db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).count()
    result = _rennen_dict(r, count)
    db.close()
    return result

@app.put("/rennen/{rennen_id}")
def rennen_bearbeiten(rennen_id: int, data: RennenSchema, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")
    r.name = data.name.strip(); r.datum = data.datum; r.uhrzeit = data.uhrzeit
    r.ort = data.ort.strip(); r.ort_link = data.ort_link or None
    r.beschreibung = data.beschreibung; r.max_teilnehmer = data.max_teilnehmer
    r.fahrzeug_klasse = data.fahrzeug_klasse; r.reifen_vorgabe = data.reifen_vorgabe
    r.max_breite_mm = data.max_breite_mm; r.sonstige_regeln = data.sonstige_regeln
    db.commit()
    db.close()
    return {"message": "Rennen aktualisiert"}

@app.delete("/rennen/{rennen_id}")
def rennen_loeschen(rennen_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")
    db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).delete()
    db.query(Zeit).filter(Zeit.rennen_id == rennen_id).delete()
    db.query(Strafzeit).filter(Strafzeit.rennen_id == rennen_id).delete()
    db.query(TorSignal).filter(TorSignal.rennen_id == rennen_id).delete()
    db.delete(r)
    db.commit()
    db.close()
    return {"message": "Rennen gelöscht"}

@app.post("/rennen/{rennen_id}/starten")
def rennen_starten(rennen_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")
    r.status = "laufend"
    db.commit()
    db.close()
    return {"message": f"Rennen '{r.name}' gestartet"}

@app.post("/rennen/{rennen_id}/abschliessen")
def rennen_abschliessen(rennen_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")
    r.status = "abgeschlossen"
    db.commit()
    db.close()
    return {"message": f"Rennen '{r.name}' abgeschlossen"}

@app.post("/rennen/{rennen_id}/reset")
def rennen_reset(rennen_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")
    r.status = "offen"
    db.commit()
    db.close()
    return {"message": f"Rennen '{r.name}' wieder geöffnet"}

@app.delete("/rennen/{rennen_id}/zeiten")
def zeiten_loeschen(rennen_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")
    z = db.query(Zeit).filter(Zeit.rennen_id == rennen_id).delete()
    db.query(Strafzeit).filter(Strafzeit.rennen_id == rennen_id).delete()
    db.query(TorSignal).filter(TorSignal.rennen_id == rennen_id).delete()
    db.commit()
    db.close()
    return {"message": f"{z} Zeiten & Strafzeiten gelöscht"}

# ── Rennanmeldung ─────────────────────────────────────────────
@app.post("/rennen/{rennen_id}/anmelden")
def fuer_rennen_anmelden(rennen_id: int, data: RennAnmeldungSchema,
                          user: User = Depends(_require_auth)):
    if not data.einwilligung:
        raise HTTPException(400, "DSGVO-Einwilligung erforderlich")
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")
    if r.status == "abgeschlossen":
        db.close()
        raise HTTPException(403, "Rennen ist abgeschlossen")
    if db.query(RennAnmeldung).filter(
        RennAnmeldung.user_id == user.id, RennAnmeldung.rennen_id == rennen_id
    ).first():
        db.close()
        raise HTTPException(400, "Bereits angemeldet")
    count = db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).count()
    if r.max_teilnehmer and count >= r.max_teilnehmer:
        db.close()
        raise HTTPException(400, "Rennen ist voll")
    a = RennAnmeldung(user_id=user.id, rennen_id=rennen_id, fahrzeug=data.fahrzeug.strip(),
                      einwilligung=True, startnummer=count + 1, eingecheckt=False,
                      erinnerung_gesendet=False)
    db.add(a)
    db.commit()
    import copy
    r_snap = copy.copy(r)
    uid, uname, uemail, snr = user.id, user.name, user.email, a.startnummer
    db.close()
    _mail_bestaetigung(uname, uemail, uid, r_snap, snr)
    return {"message": f"Angemeldet für '{r_snap.name}'!", "startnummer": snr,
            "qr_code_url": f"/fahrer/{uid}/qrcode"}

@app.delete("/rennen/{rennen_id}/abmelden")
def von_rennen_abmelden(rennen_id: int, user: User = Depends(_require_auth)):
    db = SessionLocal()
    a = db.query(RennAnmeldung).filter(
        RennAnmeldung.user_id == user.id, RennAnmeldung.rennen_id == rennen_id
    ).first()
    if not a:
        db.close()
        raise HTTPException(404, "Nicht angemeldet")
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if r and r.status != "offen":
        db.close()
        raise HTTPException(403, "Abmeldung nicht mehr möglich")
    db.delete(a)
    db.commit()
    db.close()
    return {"message": "Erfolgreich abgemeldet"}

@app.get("/rennen/{rennen_id}/teilnehmer")
def rennen_teilnehmer(rennen_id: int):
    db = SessionLocal()
    anmeldungen = db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).all()
    users = {u.id: u for u in db.query(User).all()}
    db.close()
    result = []
    for a in anmeldungen:
        u = users.get(a.user_id)
        if u:
            result.append({"id": a.user_id, "name": u.name, "email": u.email,
                           "fahrzeug": a.fahrzeug, "startnummer": a.startnummer,
                           "eingecheckt": a.eingecheckt})
    result.sort(key=lambda x: x["startnummer"])
    return result

@app.get("/rennen/{rennen_id}/leaderboard")
def rennen_leaderboard(rennen_id: int):
    db = SessionLocal()
    anmeldungen = db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).all()
    users = {u.id: u for u in db.query(User).all()}
    result = []
    for a in anmeldungen:
        u = users.get(a.user_id)
        if not u:
            continue
        zeiten  = db.query(Zeit).filter(Zeit.fahrer_id == a.user_id, Zeit.rennen_id == rennen_id).all()
        strafen = db.query(Strafzeit).filter(Strafzeit.fahrer_id == a.user_id, Strafzeit.rennen_id == rennen_id).all()
        beste_runde   = min((z.rundenzeit for z in zeiten), default=None)
        gesamt_strafe = sum(s.strafzeit for s in strafen)
        beste_gesamt  = (beste_runde + gesamt_strafe) if beste_runde is not None else None
        result.append({
            "id": a.user_id, "startnummer": a.startnummer, "name": u.name,
            "fahrzeug": a.fahrzeug, "eingecheckt": a.eingecheckt,
            "beste_rundenzeit": beste_runde, "gesamt_strafzeit": gesamt_strafe,
            "beste_gesamtzeit": beste_gesamt, "anzahl_laeufe": len(zeiten),
            "alle_zeiten": [z.rundenzeit for z in zeiten],
        })
    db.close()
    result.sort(key=lambda x: (x["beste_gesamtzeit"] is None, x["beste_gesamtzeit"]))
    return result

# ── Admin: Manuelle Anmeldung + CSV-Import ────────────────────
@app.post("/rennen/{rennen_id}/anmelden-manuell")
def manuelle_anmeldung(rennen_id: int, data: ManuelleAnmeldungSchema,
                        admin: User = Depends(_require_admin)):
    """Admin meldet einen Fahrer manuell an (z.B. vor Ort ohne Smartphone)."""
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")

    # Benutzer anlegen oder finden
    email = (data.email or f"gast_{secrets.token_hex(4)}@lokal.rally").lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(name=data.name.strip(), email=email,
                    passwort_hash=_hash(secrets.token_hex(16)), rolle="fahrer")
        db.add(user)
        db.flush()

    if db.query(RennAnmeldung).filter(
        RennAnmeldung.user_id == user.id, RennAnmeldung.rennen_id == rennen_id
    ).first():
        db.close()
        raise HTTPException(400, "Fahrer bereits angemeldet")

    count = db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).count()
    a = RennAnmeldung(user_id=user.id, rennen_id=rennen_id, fahrzeug=data.fahrzeug.strip(),
                      einwilligung=True, startnummer=count + 1, eingecheckt=False,
                      erinnerung_gesendet=True)
    db.add(a)
    db.commit()
    snr = a.startnummer
    uid = user.id
    db.close()
    return {"message": f"{data.name} manuell angemeldet", "startnummer": snr, "user_id": uid}

@app.post("/rennen/{rennen_id}/csv-import")
async def csv_import(rennen_id: int, file: UploadFile = File(...),
                     admin: User = Depends(_require_admin)):
    """CSV-Import: Spalten name,email,fahrzeug (Header erforderlich)."""
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")

    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(content.splitlines())
    imported, errors = [], []

    for row in reader:
        name    = (row.get("name") or row.get("Name") or "").strip()
        email   = (row.get("email") or row.get("Email") or "").strip().lower()
        fahrzeug= (row.get("fahrzeug") or row.get("Fahrzeug") or "Unbekannt").strip()
        if not name:
            errors.append(f"Zeile übersprungen: kein Name")
            continue
        if not email:
            email = f"gast_{secrets.token_hex(4)}@lokal.rally"

        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(name=name, email=email,
                        passwort_hash=_hash(secrets.token_hex(16)), rolle="fahrer")
            db.add(user)
            db.flush()

        if db.query(RennAnmeldung).filter(
            RennAnmeldung.user_id == user.id, RennAnmeldung.rennen_id == rennen_id
        ).first():
            errors.append(f"{name} bereits angemeldet")
            continue

        count = db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).count()
        a = RennAnmeldung(user_id=user.id, rennen_id=rennen_id, fahrzeug=fahrzeug,
                          einwilligung=True, startnummer=count + 1, eingecheckt=False,
                          erinnerung_gesendet=True)
        db.add(a)
        db.flush()
        imported.append(name)

    db.commit()
    db.close()
    return {"imported": len(imported), "errors": errors, "names": imported}

# ── Check-in ──────────────────────────────────────────────────
@app.post("/rennen/{rennen_id}/checkin/{user_id}")
def checkin(rennen_id: int, user_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    a = db.query(RennAnmeldung).filter(
        RennAnmeldung.user_id == user_id, RennAnmeldung.rennen_id == rennen_id
    ).first()
    if not a:
        db.close()
        raise HTTPException(404, "Fahrer nicht für dieses Rennen angemeldet")
    a.eingecheckt = True
    db.commit()
    u = db.query(User).filter(User.id == user_id).first()
    uname, snr = (u.name if u else str(user_id)), a.startnummer
    db.close()
    return {"message": f"{uname} eingecheckt!", "startnummer": snr}

@app.post("/checkin/{user_id}")
def checkin_qr(user_id: int):
    """QR-Code Scan Check-in (öffentlich, kein Auth nötig)."""
    db = SessionLocal()
    a = (db.query(RennAnmeldung).filter(RennAnmeldung.user_id == user_id)
         .order_by(RennAnmeldung.id.desc()).first())
    if not a:
        db.close()
        raise HTTPException(404, "Fahrer nicht angemeldet")
    if a.eingecheckt:
        db.close()
        u = db.query(User).filter(User.id == user_id).first()
        return {"message": f"{u.name if u else user_id} bereits eingecheckt",
                "startnummer": a.startnummer, "bereits": True}
    a.eingecheckt = True
    db.commit()
    u = db.query(User).filter(User.id == user_id).first()
    uname, snr = (u.name if u else str(user_id)), a.startnummer
    db.close()
    return {"message": f"{uname} eingecheckt!", "startnummer": snr, "bereits": False}

# ── Zeiten & Strafzeiten ──────────────────────────────────────
@app.post("/zeiten")
def zeit_eintragen(z: ZeitSchema, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == z.rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")
    if r.status == "abgeschlossen":
        db.close()
        raise HTTPException(403, "Rennen ist abgeschlossen")
    if not db.query(RennAnmeldung).filter(
        RennAnmeldung.user_id == z.fahrer_id, RennAnmeldung.rennen_id == z.rennen_id
    ).first():
        db.close()
        raise HTTPException(404, "Fahrer nicht für dieses Rennen angemeldet")
    neue_zeit = Zeit(fahrer_id=z.fahrer_id, rennen_id=z.rennen_id,
                     rundenzeit=z.rundenzeit, strafzeit=0.0, gesamtzeit=z.rundenzeit)
    db.add(neue_zeit)
    db.commit()
    db.close()
    return {"message": "Zeit eingetragen", "rundenzeit": z.rundenzeit}

@app.post("/strafzeiten")
def strafzeit_hinzufuegen(s: StrafzeitSchema, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == s.rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")
    if r.status == "abgeschlossen":
        db.close()
        raise HTTPException(403, "Rennen ist abgeschlossen")
    u = db.query(User).filter(User.id == s.fahrer_id).first()
    db.add(Strafzeit(fahrer_id=s.fahrer_id, rennen_id=s.rennen_id,
                     strafzeit=s.strafzeit, grund=s.grund))
    db.commit()
    db.close()
    return {"message": f"Strafzeit +{s.strafzeit}s für {u.name if u else s.fahrer_id}"}

@app.get("/strafzeiten/{rennen_id}/{fahrer_id}")
def strafzeiten_von_fahrer(rennen_id: int, fahrer_id: int):
    db = SessionLocal()
    strafen = db.query(Strafzeit).filter(
        Strafzeit.fahrer_id == fahrer_id, Strafzeit.rennen_id == rennen_id
    ).all()
    db.close()
    return [{"id": s.id, "strafzeit": s.strafzeit, "grund": s.grund} for s in strafen]

@app.delete("/strafzeiten/{strafzeit_id}")
def strafzeit_loeschen(strafzeit_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    s = db.query(Strafzeit).filter(Strafzeit.id == strafzeit_id).first()
    if not s:
        db.close()
        raise HTTPException(404, "Strafzeit nicht gefunden")
    db.delete(s)
    db.commit()
    db.close()
    return {"message": "Strafzeit gelöscht"}

# ── Fahrer / QR-Code ─────────────────────────────────────────
@app.get("/fahrer/{user_id}/qrcode")
def qrcode_generieren(user_id: int):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    if not user:
        raise HTTPException(404, "Fahrer nicht gefunden")
    buf = io.BytesIO(_make_qr_png(user_id))
    return StreamingResponse(buf, media_type="image/png")

@app.get("/profil/anmeldungen")
def meine_anmeldungen(user: User = Depends(_require_auth)):
    db = SessionLocal()
    anmeldungen = db.query(RennAnmeldung).filter(RennAnmeldung.user_id == user.id).all()
    rennen_map  = {r.id: r for r in db.query(Rennen).all()}
    result = []
    for a in anmeldungen:
        r = rennen_map.get(a.rennen_id) if a.rennen_id else None
        zeiten = db.query(Zeit).filter(Zeit.fahrer_id == user.id,
                                       Zeit.rennen_id == a.rennen_id).all() if a.rennen_id else []
        beste = min((z.rundenzeit for z in zeiten), default=None)
        result.append({
            "anmeldung_id": a.id, "rennen_id": a.rennen_id,
            "rennen_name": r.name if r else "Unbekanntes Rennen",
            "rennen_datum": r.datum if r else None,
            "rennen_status": r.status if r else "unbekannt",
            "fahrzeug": a.fahrzeug, "startnummer": a.startnummer,
            "eingecheckt": a.eingecheckt, "beste_zeit": beste,
            "anzahl_laeufe": len(zeiten),
        })
    db.close()
    result.sort(key=lambda x: (x["rennen_datum"] or ""), reverse=True)
    return result

# ── Netzwerk-Info ─────────────────────────────────────────────
@app.get("/netzwerk-info")
def netzwerk_info():
    ip = _local_ip()
    return {"local_ip": ip, "api_url": f"http://{ip}:8000",
            "frontend_url": f"http://{ip}:5173"}

# ── Ergebnisse HTML/PDF ───────────────────────────────────────
@app.get("/rennen/{rennen_id}/ergebnisse/pdf")
def ergebnisse_pdf(rennen_id: int):
    from fastapi.responses import HTMLResponse
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")
    anmeldungen = db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).all()
    users = {u.id: u for u in db.query(User).all()}
    result = []
    for a in anmeldungen:
        u = users.get(a.user_id)
        if not u:
            continue
        zeiten  = db.query(Zeit).filter(Zeit.fahrer_id == a.user_id, Zeit.rennen_id == rennen_id).all()
        strafen = db.query(Strafzeit).filter(Strafzeit.fahrer_id == a.user_id, Strafzeit.rennen_id == rennen_id).all()
        beste_runde   = min((z.rundenzeit for z in zeiten), default=None)
        gesamt_strafe = sum(s.strafzeit for s in strafen)
        beste_gesamt  = (beste_runde + gesamt_strafe) if beste_runde is not None else None
        result.append({
            "name": u.name, "fahrzeug": a.fahrzeug, "startnummer": a.startnummer,
            "anzahl_laeufe": len(zeiten), "beste_runde": beste_runde,
            "gesamt_strafe": gesamt_strafe, "beste_gesamt": beste_gesamt,
        })
    db.close()
    result.sort(key=lambda x: (x["beste_gesamt"] is None, x["beste_gesamt"]))

    def fmt(s):
        if s is None: return "—"
        m = int(s // 60); r2 = s % 60
        return f"{m}:{r2:05.2f} min" if m > 0 else f"{r2:.2f} s"

    plaetze = ["🥇", "🥈", "🥉"]
    zeilen = ""
    for i, f in enumerate(result):
        platz = plaetze[i] if i < 3 else f"{i+1}."
        bg = "#FFF8E1" if i == 0 else "#F5F5F5" if i == 1 else "#FFF3E0" if i == 2 else "white"
        strafe_str = f'+{f["gesamt_strafe"]}s' if f["gesamt_strafe"] > 0 else "—"
        zeilen += (
            f'<tr style="background:{bg}">'
            f'<td style="text-align:center;font-size:20px">{platz}</td>'
            f'<td><strong>{_html_esc(f["name"])}</strong></td>'
            f'<td>{_html_esc(f["fahrzeug"])}</td>'
            f'<td style="text-align:center">#{f["startnummer"]}</td>'
            f'<td style="text-align:center">{f["anzahl_laeufe"]}</td>'
            f'<td style="text-align:center;color:#C62828;font-weight:700">{strafe_str}</td>'
            f'<td style="text-align:center;font-family:monospace;font-weight:700;color:#C8A415">{fmt(f["beste_runde"])}</td>'
            f'<td style="text-align:center;font-family:monospace;font-weight:700">{fmt(f["beste_gesamt"])}</td>'
            f'</tr>'
        )
    status_str = {"offen": "Anmeldung offen", "laufend": "Renndurchführung läuft",
                  "abgeschlossen": "Abgeschlossen"}.get(r.status, r.status)
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"><title>Ergebnisse — {_html_esc(r.name)}</title>
<style>
body{{font-family:'Segoe UI',sans-serif;padding:40px;color:#1E1E1E;background:#fff}}
h1{{font-size:26px;margin-bottom:4px}} .sub{{color:#888;font-size:13px;margin-bottom:28px}}
table{{width:100%;border-collapse:collapse}}
th{{background:#1E1E1E;color:white;padding:11px 14px;font-size:12px;text-align:left}}
td{{padding:11px 14px;border-bottom:1px solid #F0F0F0;font-size:13px}}
@media print{{.no-print{{display:none}}}}
</style></head>
<body>
<h1>🏁 {_html_esc(r.name)}</h1>
<p class="sub">{_html_esc(r.datum or '')} · {_html_esc(r.ort or '')} &nbsp;|&nbsp; {status_str} &nbsp;|&nbsp; {len(result)} Fahrer</p>
<button class="no-print" onclick="window.print()"
  style="background:#1E1E1E;color:white;border:none;padding:10px 22px;border-radius:8px;font-size:13px;cursor:pointer;margin-bottom:22px">
  🖨️ Drucken / Als PDF speichern
</button>
<table><thead><tr>
  <th>Platz</th><th>Name</th><th>Fahrzeug</th>
  <th>Nr.</th><th>Läufe</th><th>Strafzeit</th>
  <th>Beste Runde</th><th>Beste Gesamt</th>
</tr></thead><tbody>{zeilen}</tbody></table>
<p style="font-size:11px;color:#aaa;margin-top:32px">PMK RC-Car Rally · Hochschule Pforzheim · Erstellt am {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
</body></html>""")

# ── Kamera-System ─────────────────────────────────────────────
@app.post("/kamera/tor")
def tor_signal(signal: TorSignalSchema):
    db = SessionLocal()
    anmeldung = db.query(RennAnmeldung).filter(
        RennAnmeldung.user_id == signal.fahrer_id,
        RennAnmeldung.rennen_id == signal.rennen_id,
    ).first()
    if not anmeldung:
        db.close()
        raise HTTPException(404, "Fahrer nicht für dieses Rennen angemeldet")
    user = db.query(User).filter(User.id == signal.fahrer_id).first()
    user_name = user.name if user else str(signal.fahrer_id)

    if signal.tor_nr == 1:
        # Neuen Lauf starten
        letzter = (db.query(TorSignal)
                   .filter(TorSignal.fahrer_id == signal.fahrer_id,
                           TorSignal.rennen_id == signal.rennen_id)
                   .order_by(TorSignal.lauf_id.desc()).first())
        lauf_id = (letzter.lauf_id + 1) if letzter else 1
        db.add(TorSignal(fahrer_id=signal.fahrer_id, rennen_id=signal.rennen_id,
                         tor_nr=1, zeitstempel=signal.zeitstempel, lauf_id=lauf_id))
        db.commit()
        db.close()
        return {"status": "start", "message": f"START {user_name} — Lauf {lauf_id}",
                "lauf_id": lauf_id, "naechstes_tor": 2}

    # Zwischen- oder Zielsignal
    letzter = (db.query(TorSignal)
               .filter(TorSignal.fahrer_id == signal.fahrer_id,
                       TorSignal.rennen_id == signal.rennen_id)
               .order_by(TorSignal.lauf_id.desc()).first())
    if not letzter:
        db.close()
        raise HTTPException(400, "Kein aktiver Lauf — Tor 1 zuerst drücken")

    lauf_id = letzter.lauf_id
    start_signal = db.query(TorSignal).filter(
        TorSignal.fahrer_id == signal.fahrer_id,
        TorSignal.rennen_id == signal.rennen_id,
        TorSignal.lauf_id == lauf_id,
        TorSignal.tor_nr == 1,
    ).first()
    if not start_signal:
        db.close()
        raise HTTPException(400, "Startzeit fehlt")

    zwischenzeit = round(signal.zeitstempel - start_signal.zeitstempel, 3)
    db.add(TorSignal(fahrer_id=signal.fahrer_id, rennen_id=signal.rennen_id,
                     tor_nr=signal.tor_nr, zeitstempel=signal.zeitstempel, lauf_id=lauf_id))

    if signal.tor_nr >= ANZAHL_TORE:
        db.add(Zeit(fahrer_id=signal.fahrer_id, rennen_id=signal.rennen_id,
                    rundenzeit=zwischenzeit, strafzeit=0.0, gesamtzeit=zwischenzeit))
        db.commit()
        db.close()
        return {"status": "ziel", "message": f"ZIEL! {zwischenzeit:.3f}s",
                "gesamtzeit": zwischenzeit, "lauf_id": lauf_id}

    db.commit()
    db.close()
    return {"status": "zwischen", "zwischenzeit": zwischenzeit,
            "tor_nr": signal.tor_nr, "naechstes_tor": signal.tor_nr + 1, "lauf_id": lauf_id}

@app.get("/kamera/config")
def kamera_config():
    return {"anzahl_tore": ANZAHL_TORE}

@app.delete("/kamera/lauf/{fahrer_id}/{rennen_id}/reset")
def lauf_reset(fahrer_id: int, rennen_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    db.query(TorSignal).filter(TorSignal.fahrer_id == fahrer_id,
                                TorSignal.rennen_id == rennen_id).delete()
    db.commit()
    db.close()
    return {"message": "Lauf zurückgesetzt"}

# ── Ergebnis-Mail ─────────────────────────────────────────────
@app.post("/rennen/{rennen_id}/ergebnismail")
def ergebnismail_senden(rennen_id: int, admin: User = Depends(_require_admin)):
    """Sendet Ergebnis-Mail mit Platzierung an alle Teilnehmer."""
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")

    anmeldungen = db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).all()
    users = {u.id: u for u in db.query(User).all()}

    # Leaderboard berechnen
    result = []
    for a in anmeldungen:
        u = users.get(a.user_id)
        if not u:
            continue
        zeiten  = db.query(Zeit).filter(Zeit.fahrer_id == a.user_id, Zeit.rennen_id == rennen_id).all()
        strafen = db.query(Strafzeit).filter(Strafzeit.fahrer_id == a.user_id, Strafzeit.rennen_id == rennen_id).all()
        beste_runde   = min((z.rundenzeit for z in zeiten), default=None)
        gesamt_strafe = sum(s.strafzeit for s in strafen)
        beste_gesamt  = (beste_runde + gesamt_strafe) if beste_runde is not None else None
        result.append({
            "user": u, "startnummer": a.startnummer, "fahrzeug": a.fahrzeug,
            "beste_runde": beste_runde, "gesamt_strafe": gesamt_strafe,
            "beste_gesamt": beste_gesamt, "anzahl_laeufe": len(zeiten),
        })
    db.close()
    result.sort(key=lambda x: (x["beste_gesamt"] is None, x["beste_gesamt"]))

    def fmt(s):
        if s is None: return "—"
        return f"{s:.3f} s" if s < 60 else f"{int(s//60)}:{(s%60):.3f} min"

    plaetze = ["🥇", "🥈", "🥉"]
    gesendet = 0

    for i, f in enumerate(result):
        u = f["user"]
        if not u.email or "@lokal.rally" in u.email:
            continue
        platz = plaetze[i] if i < 3 else f"{i+1}."
        platz_text = ["1. Platz", "2. Platz", "3. Platz"][i] if i < 3 else f"{i+1}. Platz"
        datum_str = _fmt_datum_de(r.datum, r.uhrzeit)

        html = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#09090B;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:560px;margin:32px auto;background:#18181B;border-radius:14px;overflow:hidden;border:1px solid #3F3F46;">
  <div style="background:#0F172A;padding:28px 32px;text-align:center;border-bottom:1px solid #3F3F46;">
    <div style="font-size:48px;margin-bottom:8px;">{platz}</div>
    <div style="font-size:20px;font-weight:800;color:#FAFAFA;">PMK RC-Car <span style="color:#F59E0B;">Rally</span></div>
    <div style="font-size:13px;color:#71717A;margin-top:4px;">Offizielles Ergebnis</div>
  </div>
  <div style="padding:28px 32px;">
    <p style="color:#FAFAFA;font-size:16px;font-weight:700;margin:0 0 4px;">Hallo {_html_esc(u.name)}!</p>
    <p style="color:#A1A1AA;font-size:14px;margin:0 0 24px;">Das Rennen ist abgeschlossen. Hier ist dein offizielles Ergebnis:</p>
    <div style="background:#09090B;border:1px solid #3F3F46;border-radius:10px;padding:20px;margin-bottom:20px;text-align:center;">
      <div style="font-size:48px;margin-bottom:8px;">{platz}</div>
      <div style="font-size:22px;font-weight:900;color:#F59E0B;margin-bottom:4px;">{platz_text}</div>
      <div style="font-size:13px;color:#A1A1AA;">{_html_esc(r.name)} · {datum_str}</div>
    </div>
    <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
      <tr><td style="padding:8px 0;font-size:12px;color:#71717A;width:120px;">🔢 Startnummer</td>
          <td style="padding:8px 0;font-size:14px;color:#F59E0B;font-weight:900;">#{f['startnummer']}</td></tr>
      <tr><td style="padding:8px 0;font-size:12px;color:#71717A;">🏎️ Fahrzeug</td>
          <td style="padding:8px 0;font-size:14px;color:#FAFAFA;font-weight:600;">{_html_esc(f['fahrzeug'])}</td></tr>
      <tr><td style="padding:8px 0;font-size:12px;color:#71717A;">🏁 Läufe</td>
          <td style="padding:8px 0;font-size:14px;color:#FAFAFA;font-weight:600;">{f['anzahl_laeufe']}</td></tr>
      <tr><td style="padding:8px 0;font-size:12px;color:#71717A;">⭐ Beste Runde</td>
          <td style="padding:8px 0;font-size:18px;color:#F59E0B;font-weight:900;font-family:monospace;">{fmt(f['beste_runde'])}</td></tr>
      {'<tr><td style="padding:8px 0;font-size:12px;color:#71717A;">⚠️ Strafzeiten</td><td style="padding:8px 0;font-size:14px;color:#EF4444;font-weight:600;">+' + str(f['gesamt_strafe']) + 's</td></tr>' if f['gesamt_strafe'] > 0 else ''}
      <tr style="border-top:1px solid #3F3F46;">
          <td style="padding:10px 0 0;font-size:12px;color:#71717A;">🏆 Gesamtzeit</td>
          <td style="padding:10px 0 0;font-size:20px;color:#FAFAFA;font-weight:900;font-family:monospace;">{fmt(f['beste_gesamt'])}</td></tr>
    </table>
    <p style="color:#71717A;font-size:12px;text-align:center;">Vielen Dank für deine Teilnahme! Bis zum nächsten Rennen 🏎️</p>
  </div>
  <div style="padding:14px 32px;border-top:1px solid #3F3F46;text-align:center;">
    <div style="font-size:11px;color:#71717A;">PMK RC-Car Rally · Hochschule Pforzheim</div>
  </div>
</div>
</body></html>"""

        threading.Thread(
            target=_send_mail,
            args=(u.email, f"🏆 Dein Ergebnis: {r.name}", html),
            daemon=True,
        ).start()
        gesendet += 1

    return {"message": f"Ergebnis-Mail an {gesendet} Fahrer gesendet", "gesendet": gesendet}


# ── Urkunden ──────────────────────────────────────────────────
@app.get("/rennen/{rennen_id}/urkunden")
def urkunden(rennen_id: int):
    from fastapi.responses import HTMLResponse
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")

    anmeldungen = db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).all()
    users = {u.id: u for u in db.query(User).all()}
    result = []
    for a in anmeldungen:
        u = users.get(a.user_id)
        if not u: continue
        zeiten  = db.query(Zeit).filter(Zeit.fahrer_id == a.user_id, Zeit.rennen_id == rennen_id).all()
        strafen = db.query(Strafzeit).filter(Strafzeit.fahrer_id == a.user_id, Strafzeit.rennen_id == rennen_id).all()
        beste_runde   = min((z.rundenzeit for z in zeiten), default=None)
        gesamt_strafe = sum(s.strafzeit for s in strafen)
        beste_gesamt  = (beste_runde + gesamt_strafe) if beste_runde is not None else None
        result.append({"name": u.name, "fahrzeug": a.fahrzeug, "startnummer": a.startnummer,
                       "beste_runde": beste_runde, "gesamt_strafe": gesamt_strafe,
                       "beste_gesamt": beste_gesamt, "anzahl_laeufe": len(zeiten)})
    db.close()
    result.sort(key=lambda x: (x["beste_gesamt"] is None, x["beste_gesamt"]))

    def fmt(s):
        if s is None: return "—"
        return f"{s:.3f} s" if s < 60 else f"{int(s//60)}:{(s%60):.3f} min"

    plaetze_emoji = ["🥇", "🥈", "🥉"]
    plaetze_text  = ["1. Platz", "2. Platz", "3. Platz"]
    plaetze_color = ["#C8A415", "#9CA3AF", "#CD7F32"]
    datum_str = _fmt_datum_de(r.datum, r.uhrzeit)

    karten = ""
    for i, f in enumerate(result):
        emoji = plaetze_emoji[i] if i < 3 else f"{i+1}."
        text  = plaetze_text[i]  if i < 3 else f"{i+1}. Platz"
        color = plaetze_color[i] if i < 3 else "#6B7280"
        karten += f"""
        <div class="urkunde" style="border-color:{color}">
          <div class="platz-emoji">{emoji}</div>
          <div class="platz-text" style="color:{color}">{text}</div>
          <div class="name">{_html_esc(f['name'])}</div>
          <div class="fahrzeug">{_html_esc(f['fahrzeug'])} · Startnummer #{f['startnummer']}</div>
          <div class="zeit">{fmt(f['beste_gesamt'])}</div>
          <div class="details">
            Beste Runde: {fmt(f['beste_runde'])}
            {f' · Strafzeit: +{f["gesamt_strafe"]}s' if f['gesamt_strafe'] > 0 else ''}
            · {f['anzahl_laeufe']} Läufe
          </div>
          <div class="rennen">{_html_esc(r.name)} · {datum_str}</div>
          <div class="footer-line">Hochschule Pforzheim · Fakultät für Technik · PMK RC-Car Rally</div>
        </div>"""

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"><title>Urkunden — {_html_esc(r.name)}</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
  .no-print {{ text-align:center; margin-bottom: 24px; }}
  .no-print button {{ background:#1E1E1E;color:white;border:none;padding:12px 28px;border-radius:8px;font-size:14px;cursor:pointer;margin:0 6px; }}
  .urkunde {{
    background: white; border: 3px solid #C8A415; border-radius: 16px;
    padding: 40px; margin: 0 auto 40px; max-width: 600px;
    text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    page-break-after: always;
  }}
  .platz-emoji {{ font-size: 64px; margin-bottom: 8px; }}
  .platz-text {{ font-size: 28px; font-weight: 900; margin-bottom: 16px; }}
  .name {{ font-size: 32px; font-weight: 900; color: #1E1E1E; margin-bottom: 6px; }}
  .fahrzeug {{ font-size: 14px; color: #6B7280; margin-bottom: 20px; }}
  .zeit {{ font-size: 42px; font-weight: 900; color: #1E1E1E; font-family: monospace; margin-bottom: 8px; }}
  .details {{ font-size: 13px; color: #6B7280; margin-bottom: 20px; }}
  .rennen {{ font-size: 14px; font-weight: 700; color: #1E1E1E; padding-top: 16px; border-top: 1px solid #E5E7EB; margin-top: 16px; }}
  .footer-line {{ font-size: 11px; color: #9CA3AF; margin-top: 8px; }}
  @media print {{
    .no-print {{ display: none; }}
    body {{ padding: 0; background: white; }}
    .urkunde {{ box-shadow: none; margin: 0 auto; }}
  }}
</style></head>
<body>
<div class="no-print">
  <button onclick="window.print()">🖨️ Alle drucken</button>
  <span style="color:#6B7280;font-size:13px;margin-left:12px">{len(result)} Urkunden · {_html_esc(r.name)}</span>
</div>
{karten}
</body></html>""")


# ── DSGVO: Daten löschen ──────────────────────────────────────
@app.post("/admin/daten-loeschen")
def daten_loeschen(admin: User = Depends(_require_admin)):
    """Löscht alle Fahrerdaten nach dem Event (DSGVO)."""
    db = SessionLocal()
    # Alle Fahrer-Accounts außer Admins löschen
    fahrer = db.query(User).filter(User.rolle == "fahrer").all()
    anzahl = len(fahrer)
    for u in fahrer:
        db.delete(u)
    # Alle Renndaten löschen
    db.query(RennAnmeldung).delete()
    db.query(Zeit).delete()
    db.query(Strafzeit).delete()
    db.query(TorSignal).delete()
    db.commit()
    db.close()
    return {"message": f"{anzahl} Fahrer-Accounts und alle Renndaten gelöscht", "geloescht": anzahl}


# ── Datenbank Backup ──────────────────────────────────────────
@app.get("/admin/backup")
def datenbank_backup(token: str = None, authorization: str = Header(None)):
    # Token aus Query-Parameter oder Header akzeptieren
    t = token or (authorization or "").replace("Bearer ", "")
    user = _get_user_by_token(t)
    if not user or user.rolle != "admin":
        raise HTTPException(403, "Nur für Admins")
    """Lädt die aktuelle Datenbank als Backup herunter."""
    db_path = os.path.join(os.path.dirname(__file__), "rally.db")
    if not os.path.exists(db_path):
        raise HTTPException(404, "Datenbank nicht gefunden")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"rally_backup_{timestamp}.db"
    def iter_file():
        with open(db_path, "rb") as f:
            yield from f
    return StreamingResponse(
        iter_file(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ── Demo-Modus ────────────────────────────────────────────────
@app.post("/rennen/{rennen_id}/demo")
def demo_daten(rennen_id: int, admin: User = Depends(_require_admin)):
    """Fügt 10 Demo-Fahrer mit zufälligen Zeiten ein."""
    import random
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(404, "Rennen nicht gefunden")

    demo_fahrer = [
        ("Max Mustermann",   "Traxxas Slash 4x4"),
        ("Lisa Schneider",   "Axial SCX10 III"),
        ("Tom Richter",      "Arrma Kraton 6S"),
        ("Anna Becker",      "Tamiya Lunch Box"),
        ("Felix Wagner",     "HPI Racing Savage"),
        ("Julia Hoffmann",   "Kyosho Inferno MP10"),
        ("Lukas Braun",      "Losi 8IGHT-X"),
        ("Sara Klein",       "Team Associated RC8B3"),
        ("Noah Fischer",     "Traxxas E-Revo"),
        ("Emma Schmidt",     "Redcat Racing Volcano"),
    ]

    erstellt = 0
    for name, fahrzeug in demo_fahrer:
        email = f"demo_{name.lower().replace(' ', '_')}@demo.rally"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(name=name, email=email,
                        passwort_hash=_hash(secrets.token_hex(8)), rolle="fahrer")
            db.add(user)
            db.flush()

        if db.query(RennAnmeldung).filter(
            RennAnmeldung.user_id == user.id, RennAnmeldung.rennen_id == rennen_id
        ).first():
            continue

        count = db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).count()
        a = RennAnmeldung(user_id=user.id, rennen_id=rennen_id, fahrzeug=fahrzeug,
                          einwilligung=True, startnummer=count + 1,
                          eingecheckt=True, erinnerung_gesendet=True)
        db.add(a)
        db.flush()

        # 2-3 Läufe mit realistischen Zeiten (40-90s)
        for _ in range(random.randint(2, 3)):
            t = round(random.uniform(40.0, 90.0), 3)
            db.add(Zeit(fahrer_id=user.id, rennen_id=rennen_id,
                        rundenzeit=t, strafzeit=0.0, gesamtzeit=t))

        # 30% Chance auf Strafzeit
        if random.random() < 0.3:
            straf_optionen = [10, 15, 20, 30]
            s = random.choice(straf_optionen)
            db.add(Strafzeit(fahrer_id=user.id, rennen_id=rennen_id,
                             strafzeit=s, grund="Tor berührt / verschoben"))
        erstellt += 1

    db.commit()
    db.close()
    return {"message": f"{erstellt} Demo-Fahrer mit Zeiten erstellt", "erstellt": erstellt}


# ── Root ──────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "PMK RC-Rally API v2", "docs": "/docs", "version": "2.0.0"}
