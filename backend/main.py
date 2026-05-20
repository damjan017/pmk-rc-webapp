import hashlib
import secrets
import socket
import os
import io
import smtplib
import threading
from datetime import datetime, timedelta
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import qrcode
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler

# ── Konfiguration ──────────────────────────────────────────────
GMAIL_USER  = os.getenv("GMAIL_USER",  "pmkrccarrally@gmail.com")
GMAIL_PW    = os.getenv("GMAIL_APP_PW", "")
APP_URL     = os.getenv("APP_URL",     "http://localhost:8000")
ANZAHL_TORE = 6

# ── Datenbank ─────────────────────────────────────────────────
DATABASE_URL = "sqlite:///./rally.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ── ORM-Modelle ───────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True, nullable=False)
    passwort_hash = Column(String, nullable=False)
    rolle = Column(String, default="fahrer")
    token = Column(String, unique=True, nullable=True)

class Rennen(Base):
    __tablename__ = "rennen"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    datum = Column(String)
    uhrzeit = Column(String)
    ort = Column(String)
    ort_link = Column(String, nullable=True)
    beschreibung = Column(Text, nullable=True)
    max_teilnehmer = Column(Integer, default=50)
    status = Column(String, default="offen")
    erstellt_am = Column(String)

class RennAnmeldung(Base):
    __tablename__ = "renn_anmeldungen"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    rennen_id = Column(Integer, nullable=True)
    fahrzeug = Column(String)
    einwilligung = Column(Boolean, default=False)
    startnummer = Column(Integer)
    eingecheckt = Column(Boolean, default=False)
    erinnerung_gesendet = Column(Boolean, default=False)

class Zeit(Base):
    __tablename__ = "zeiten"
    id = Column(Integer, primary_key=True)
    fahrer_id = Column(Integer)
    rennen_id = Column(Integer, nullable=True)
    rundenzeit = Column(Float)
    strafzeit = Column(Float, default=0.0)
    gesamtzeit = Column(Float)

class Strafzeit(Base):
    __tablename__ = "strafzeiten"
    id = Column(Integer, primary_key=True)
    fahrer_id = Column(Integer)
    rennen_id = Column(Integer, nullable=True)
    strafzeit = Column(Float)
    grund = Column(String)

class TorSignal(Base):
    __tablename__ = "tor_signale"
    id = Column(Integer, primary_key=True)
    fahrer_id = Column(Integer)
    tor_nr = Column(Integer)
    zeitstempel = Column(Float)
    lauf_id = Column(Integer)

Base.metadata.create_all(bind=engine)

# ── DB-Migration ───────────────────────────────────────────────
def _migrate_db():
    import sqlite3
    con = sqlite3.connect("./rally.db")
    cur = con.cursor()
    for table, col in [
        ("renn_anmeldungen", "rennen_id"),
        ("renn_anmeldungen", "erinnerung_gesendet"),
        ("zeiten", "rennen_id"),
        ("strafzeiten", "rennen_id"),
        ("rennen", "ort_link"),
    ]:
        try:
            cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
            if col not in cols:
                default = "0" if col == "erinnerung_gesendet" else "NULL"
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER DEFAULT {default}")
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
    token = authorization.replace("Bearer ", "") if authorization else None
    user = _get_user_by_token(token)
    if not user or user.rolle != "admin":
        raise HTTPException(status_code=403, detail="Nur für Admins")
    return user

def _require_auth(authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
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

# ── E-Mail ────────────────────────────────────────────────────
def _send_mail(to: str, subject: str, html: str, qr_png: bytes = None):
    """Sendet eine HTML-E-Mail, optional mit eingebettetem QR-Code."""
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
        print(f"[Mail] ✗ Fehler beim Senden an {to}: {e}")

def _mail_bestaetigung(user_name: str, user_email: str, user_id: int,
                        rennen: Rennen, startnummer: int):
    """Sendet die Anmelde-Bestätigung mit QR-Code."""
    datum_str = _fmt_datum_de(rennen.datum, rennen.uhrzeit)
    ort_link  = f'<a href="{rennen.ort_link}" style="color:#F59E0B">{rennen.ort}</a>' \
                if rennen.ort_link else rennen.ort

    html = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Anmeldebestätigung</title></head>
<body style="margin:0;padding:0;background:#09090B;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:560px;margin:32px auto;background:#18181B;border-radius:14px;overflow:hidden;border:1px solid #3F3F46;">

  <!-- Header -->
  <div style="background:#0F172A;padding:28px 32px;text-align:center;border-bottom:1px solid #3F3F46;">
    <div style="font-size:28px;margin-bottom:6px;">🏁</div>
    <div style="font-size:20px;font-weight:800;color:#FAFAFA;">PMK RC-Car <span style="color:#F59E0B;">Rally</span></div>
    <div style="font-size:12px;color:#71717A;margin-top:4px;">Anmeldebestätigung</div>
  </div>

  <!-- Body -->
  <div style="padding:28px 32px;">
    <p style="color:#FAFAFA;font-size:16px;font-weight:700;margin:0 0 6px;">Hallo {user_name}! 👋</p>
    <p style="color:#A1A1AA;font-size:14px;margin:0 0 24px;line-height:1.6;">
      Du bist erfolgreich für das folgende Rennen angemeldet. Zeige deinen QR-Code beim Check-in vor.
    </p>

    <!-- Race card -->
    <div style="background:#09090B;border:1px solid #3F3F46;border-radius:10px;padding:18px 20px;margin-bottom:20px;">
      <div style="font-size:16px;font-weight:800;color:#FAFAFA;margin-bottom:12px;">{rennen.name}</div>
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="padding:5px 0;font-size:12px;color:#71717A;width:90px;">📅 Datum</td>
          <td style="padding:5px 0;font-size:13px;color:#FAFAFA;font-weight:600;">{datum_str}</td>
        </tr>
        <tr>
          <td style="padding:5px 0;font-size:12px;color:#71717A;">📍 Ort</td>
          <td style="padding:5px 0;font-size:13px;color:#FAFAFA;font-weight:600;">{ort_link}</td>
        </tr>
        <tr>
          <td style="padding:5px 0;font-size:12px;color:#71717A;">🏎️ Fahrzeug</td>
          <td style="padding:5px 0;font-size:13px;color:#FAFAFA;font-weight:600;">{_html_esc("–")}</td>
        </tr>
        <tr>
          <td style="padding:5px 0;font-size:12px;color:#71717A;">🔢 Startnummer</td>
          <td style="padding:5px 0;font-size:22px;font-weight:900;color:#F59E0B;">#{startnummer}</td>
        </tr>
      </table>
    </div>

    <!-- QR Code -->
    <div style="text-align:center;margin-bottom:24px;">
      <div style="font-size:12px;color:#71717A;margin-bottom:10px;text-transform:uppercase;letter-spacing:0.5px;">Dein Check-in QR-Code</div>
      <img src="cid:qrcode" alt="QR-Code" width="180" height="180"
           style="border-radius:10px;background:white;padding:12px;display:block;margin:0 auto;">
      <div style="font-size:11px;color:#71717A;margin-top:8px;">Beim Check-in vorzeigen</div>
    </div>

    <!-- Info box -->
    <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);border-radius:8px;padding:14px 16px;margin-bottom:20px;">
      <div style="font-size:12px;font-weight:700;color:#F59E0B;margin-bottom:6px;">📋 Wichtige Hinweise</div>
      <ul style="margin:0;padding-left:16px;color:#A1A1AA;font-size:12px;line-height:1.8;">
        <li>Mindestens 30 Minuten vor Start erscheinen</li>
        <li>Vollgeladene Akkus (mind. 2) mitbringen</li>
        <li>Fahrzeug muss fahrbereit sein</li>
        <li>Fahrermeeting 15 Min. vor Start — Anwesenheit Pflicht</li>
      </ul>
    </div>

    <!-- CTA -->
    <div style="text-align:center;">
      <a href="{APP_URL}/app/index.html"
         style="display:inline-block;background:#F59E0B;color:#09090B;font-weight:700;font-size:14px;padding:12px 28px;border-radius:9px;text-decoration:none;">
        Zur Rangliste →
      </a>
    </div>
  </div>

  <!-- Footer -->
  <div style="padding:16px 32px;border-top:1px solid #3F3F46;text-align:center;">
    <div style="font-size:11px;color:#71717A;">
      PMK RC-Car Rally · <a href="{APP_URL}/app/faq.html" style="color:#71717A;">FAQ</a> ·
      <a href="{APP_URL}/app/impressum.html" style="color:#71717A;">Impressum</a>
    </div>
  </div>
</div>
</body></html>"""

    qr_png = _make_qr_png(user_id)
    threading.Thread(
        target=_send_mail,
        args=(user_email, f"✅ Anmeldung bestätigt: {rennen.name}", html, qr_png),
        daemon=True,
    ).start()


def _mail_erinnerung(user_name: str, user_email: str, user_id: int,
                      rennen: Rennen, startnummer: int):
    """Sendet den 2h-Vorher-Reminder."""
    datum_str = _fmt_datum_de(rennen.datum, rennen.uhrzeit)
    ort_link  = f'<a href="{rennen.ort_link}" style="color:#F59E0B">{rennen.ort}</a>' \
                if rennen.ort_link else rennen.ort

    html = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#09090B;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:560px;margin:32px auto;background:#18181B;border-radius:14px;overflow:hidden;border:1px solid #3F3F46;">

  <!-- Header -->
  <div style="background:#0F172A;padding:28px 32px;text-align:center;border-bottom:1px solid #3F3F46;">
    <div style="font-size:28px;margin-bottom:6px;">⏰</div>
    <div style="font-size:20px;font-weight:800;color:#FAFAFA;">Startet in <span style="color:#F59E0B;">2 Stunden!</span></div>
    <div style="font-size:12px;color:#71717A;margin-top:4px;">PMK RC-Car Rally — Erinnerung</div>
  </div>

  <!-- Body -->
  <div style="padding:28px 32px;">
    <p style="color:#FAFAFA;font-size:16px;font-weight:700;margin:0 0 6px;">Hey {user_name}! 🏎️</p>
    <p style="color:#A1A1AA;font-size:14px;margin:0 0 24px;line-height:1.6;">
      In <strong style="color:#F59E0B;">2 Stunden</strong> startet dein Rennen. Brich jetzt auf, damit du rechtzeitig zum Check-in da bist!
    </p>

    <!-- Race card -->
    <div style="background:#09090B;border:1px solid rgba(245,158,11,0.3);border-radius:10px;padding:18px 20px;margin-bottom:20px;">
      <div style="font-size:16px;font-weight:800;color:#FAFAFA;margin-bottom:12px;">{rennen.name}</div>
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="padding:5px 0;font-size:12px;color:#71717A;width:90px;">📅 Wann</td>
          <td style="padding:5px 0;font-size:13px;color:#FAFAFA;font-weight:600;">{datum_str}</td>
        </tr>
        <tr>
          <td style="padding:5px 0;font-size:12px;color:#71717A;">📍 Wo</td>
          <td style="padding:5px 0;font-size:13px;color:#FAFAFA;font-weight:600;">{ort_link}</td>
        </tr>
        <tr>
          <td style="padding:5px 0;font-size:12px;color:#71717A;">🔢 Deine Nr.</td>
          <td style="padding:5px 0;font-size:22px;font-weight:900;color:#F59E0B;">#{startnummer}</td>
        </tr>
      </table>
    </div>

    <!-- QR Code -->
    <div style="text-align:center;margin-bottom:24px;">
      <div style="font-size:12px;color:#71717A;margin-bottom:10px;">Check-in QR-Code — bereit halten!</div>
      <img src="cid:qrcode" alt="QR-Code" width="160" height="160"
           style="border-radius:10px;background:white;padding:10px;display:block;margin:0 auto;">
    </div>

    <!-- Checklist -->
    <div style="background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);border-radius:8px;padding:14px 16px;margin-bottom:20px;">
      <div style="font-size:12px;font-weight:700;color:#22C55E;margin-bottom:8px;">✅ Letzte Checkliste</div>
      <div style="font-size:12px;color:#A1A1AA;line-height:2;">
        ☐ Fahrzeug fahrbereit?<br>
        ☐ Akkus voll geladen? (mind. 2)<br>
        ☐ Ladegerät eingepackt?<br>
        ☐ Fernsteuerung + Sender dabei?<br>
        ☐ Werkzeug & Ersatzteile?
      </div>
    </div>

    <div style="text-align:center;">
      <a href="{APP_URL}/app/leaderboard.html"
         style="display:inline-block;background:#F59E0B;color:#09090B;font-weight:700;font-size:14px;padding:12px 28px;border-radius:9px;text-decoration:none;">
        Live-Rangliste →
      </a>
    </div>
  </div>

  <div style="padding:16px 32px;border-top:1px solid #3F3F46;text-align:center;">
    <div style="font-size:11px;color:#71717A;">PMK RC-Car Rally · Diese Mail wurde automatisch versandt</div>
  </div>
</div>
</body></html>"""

    qr_png = _make_qr_png(user_id)
    threading.Thread(
        target=_send_mail,
        args=(user_email, f"⏰ Startet in 2h: {rennen.name}", html, qr_png),
        daemon=True,
    ).start()


def _html_esc(s: str) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ── 2h-Reminder Scheduler ─────────────────────────────────────
def _check_reminders():
    """Läuft alle 5 Minuten und sendet Reminder für Rennen die in ~2h starten."""
    now    = datetime.now()
    w_low  = now + timedelta(hours=2) - timedelta(minutes=5)
    w_high = now + timedelta(hours=2) + timedelta(minutes=5)
    try:
        db = SessionLocal()
        rennen_list = db.query(Rennen).filter(Rennen.status != "abgeschlossen").all()
        for r in rennen_list:
            rt = _parse_rennen_dt(r.datum, r.uhrzeit)
            if not rt or not (w_low <= rt <= w_high):
                continue
            anmeldungen = db.query(RennAnmeldung).filter(
                RennAnmeldung.rennen_id == r.id,
                RennAnmeldung.erinnerung_gesendet == False,
            ).all()
            for a in anmeldungen:
                user = db.query(User).filter(User.id == a.user_id).first()
                if user and user.email:
                    uname, uemail, uid, snr = user.name, user.email, user.id, a.startnummer
                    _mail_erinnerung(uname, uemail, uid, r, snr)
                a.erinnerung_gesendet = True
        db.commit()
        db.close()
    except Exception as e:
        print(f"[Reminder] Fehler: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(_check_reminders, "interval", minutes=5, id="reminder_check")
scheduler.start()

# ── App ───────────────────────────────────────────────────────
app = FastAPI(title="PMK RC-Rally API")

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

class RennAnmeldungSchema(BaseModel):
    fahrzeug: str
    einwilligung: bool

class ZeitSchema(BaseModel):
    fahrer_id: int
    rennen_id: int
    rundenzeit: float
    strafzeit: float = 0.0

class StrafzeitSchema(BaseModel):
    fahrer_id: int
    rennen_id: int
    strafzeit: float
    grund: str

class TorSignalSchema(BaseModel):
    fahrer_id: int
    tor_nr: int
    zeitstempel: float

# ── Auth ──────────────────────────────────────────────────────
@app.post("/auth/register")
def register(data: RegisterSchema):
    if not data.name.strip() or not data.email.strip() or not data.passwort.strip():
        raise HTTPException(status_code=400, detail="Alle Felder erforderlich")
    db = SessionLocal()
    if db.query(User).filter(User.email == data.email.lower()).first():
        db.close()
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert")
    user = User(
        name=data.name.strip(), email=data.email.lower().strip(),
        passwort_hash=_hash(data.passwort), rolle="fahrer", token=None,
    )
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
        raise HTTPException(status_code=401, detail="E-Mail oder Passwort falsch")
    token = _new_token()
    user.token = token
    db.commit()
    uid, uname, uemail, urolle = user.id, user.name, user.email, user.rolle
    db.close()
    return {"token": token, "rolle": urolle, "name": uname, "email": uemail, "id": uid}

@app.post("/auth/logout")
def logout(user: User = Depends(_require_auth)):
    db = SessionLocal()
    u = db.query(User).filter(User.id == user.id).first()
    u.token = None
    db.commit()
    db.close()
    return {"message": "Ausgeloggt"}

@app.get("/auth/me")
def me(user: User = Depends(_require_auth)):
    db = SessionLocal()
    anmeldungen_count = db.query(RennAnmeldung).filter(RennAnmeldung.user_id == user.id).count()
    db.close()
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "rolle": user.rolle, "anmeldungen_count": anmeldungen_count,
    }

# ── Rennen CRUD ───────────────────────────────────────────────
@app.get("/rennen")
def alle_rennen():
    db = SessionLocal()
    rennen = db.query(Rennen).order_by(Rennen.datum.asc()).all()
    result = []
    for r in rennen:
        count = db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == r.id).count()
        result.append(_rennen_dict(r, count))
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
        raise HTTPException(status_code=404, detail="Rennen nicht gefunden")
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
        raise HTTPException(status_code=404, detail="Rennen nicht gefunden")
    r.name = data.name.strip()
    r.datum = data.datum
    r.uhrzeit = data.uhrzeit
    r.ort = data.ort.strip()
    r.ort_link = data.ort_link or None
    r.beschreibung = data.beschreibung
    r.max_teilnehmer = data.max_teilnehmer
    db.commit()
    db.close()
    return {"message": "Rennen aktualisiert"}

@app.delete("/rennen/{rennen_id}")
def rennen_loeschen(rennen_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(status_code=404, detail="Rennen nicht gefunden")
    db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).delete()
    db.query(Zeit).filter(Zeit.rennen_id == rennen_id).delete()
    db.query(Strafzeit).filter(Strafzeit.rennen_id == rennen_id).delete()
    db.delete(r)
    db.commit()
    db.close()
    return {"message": "Rennen gelöscht"}

@app.post("/rennen/{rennen_id}/anmelden")
def fuer_rennen_anmelden(rennen_id: int, data: RennAnmeldungSchema, user: User = Depends(_require_auth)):
    if not data.einwilligung:
        raise HTTPException(status_code=400, detail="DSGVO-Einwilligung erforderlich")
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(status_code=404, detail="Rennen nicht gefunden")
    if r.status == "abgeschlossen":
        db.close()
        raise HTTPException(status_code=403, detail="Rennen ist abgeschlossen")
    if db.query(RennAnmeldung).filter(
        RennAnmeldung.user_id == user.id, RennAnmeldung.rennen_id == rennen_id
    ).first():
        db.close()
        raise HTTPException(status_code=400, detail="Bereits für dieses Rennen angemeldet")
    count = db.query(RennAnmeldung).filter(RennAnmeldung.rennen_id == rennen_id).count()
    if r.max_teilnehmer and count >= r.max_teilnehmer:
        db.close()
        raise HTTPException(status_code=400, detail="Rennen ist voll")
    startnummer = count + 1
    a = RennAnmeldung(
        user_id=user.id, rennen_id=rennen_id, fahrzeug=data.fahrzeug.strip(),
        einwilligung=True, startnummer=startnummer, eingecheckt=False,
        erinnerung_gesendet=False,
    )
    db.add(a)
    db.commit()

    # Werte vor db.close() sichern
    uid, uname, uemail, snr = user.id, user.name, user.email, a.startnummer
    rname = r.name

    # Snapshot von r für den Mail-Thread
    import copy
    r_snap = copy.copy(r)

    db.close()

    # Bestätigungs-Mail im Hintergrund
    _mail_bestaetigung(uname, uemail, uid, r_snap, snr)

    return {
        "message": f"Erfolgreich für '{rname}' angemeldet!",
        "startnummer": snr,
        "qr_code_url": f"/fahrer/{uid}/qrcode",
    }

@app.delete("/rennen/{rennen_id}/abmelden")
def von_rennen_abmelden(rennen_id: int, user: User = Depends(_require_auth)):
    db = SessionLocal()
    a = db.query(RennAnmeldung).filter(
        RennAnmeldung.user_id == user.id, RennAnmeldung.rennen_id == rennen_id,
    ).first()
    if not a:
        db.close()
        raise HTTPException(status_code=404, detail="Nicht für dieses Rennen angemeldet")
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if r and r.status != "offen":
        db.close()
        raise HTTPException(status_code=403, detail="Abmeldung nicht mehr möglich")
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
            result.append({
                "id": a.user_id, "name": u.name, "fahrzeug": a.fahrzeug,
                "startnummer": a.startnummer, "eingecheckt": a.eingecheckt,
            })
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
        })
    db.close()
    result.sort(key=lambda x: (x["beste_gesamtzeit"] is None, x["beste_gesamtzeit"]))
    return result

@app.post("/rennen/{rennen_id}/starten")
def rennen_starten(rennen_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(status_code=404, detail="Rennen nicht gefunden")
    r.status = "laufend"
    rname = r.name
    db.commit()
    db.close()
    return {"message": f"Rennen '{rname}' gestartet"}

@app.post("/rennen/{rennen_id}/abschliessen")
def rennen_per_id_abschliessen(rennen_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(status_code=404, detail="Rennen nicht gefunden")
    r.status = "abgeschlossen"
    rname = r.name
    db.commit()
    db.close()
    return {"message": f"Rennen '{rname}' abgeschlossen"}

@app.post("/rennen/{rennen_id}/reset")
def rennen_per_id_reset(rennen_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(status_code=404, detail="Rennen nicht gefunden")
    r.status = "offen"
    rname = r.name
    db.commit()
    db.close()
    return {"message": f"Rennen '{rname}' wieder geöffnet"}

# ── Profil ────────────────────────────────────────────────────
@app.get("/profil/anmeldungen")
def meine_anmeldungen(user: User = Depends(_require_auth)):
    db = SessionLocal()
    anmeldungen = db.query(RennAnmeldung).filter(RennAnmeldung.user_id == user.id).all()
    rennen_map  = {r.id: r for r in db.query(Rennen).all()}
    result = []
    for a in anmeldungen:
        r = rennen_map.get(a.rennen_id) if a.rennen_id else None
        zeiten = (
            db.query(Zeit).filter(Zeit.fahrer_id == user.id, Zeit.rennen_id == a.rennen_id).all()
            if a.rennen_id else []
        )
        beste = min((z.rundenzeit for z in zeiten), default=None)
        result.append({
            "anmeldung_id": a.id, "rennen_id": a.rennen_id,
            "rennen_name": r.name if r else "Unbekanntes Rennen",
            "rennen_datum": r.datum if r else None,
            "rennen_uhrzeit": r.uhrzeit if r else None,
            "rennen_ort": r.ort if r else None,
            "rennen_status": r.status if r else "unbekannt",
            "fahrzeug": a.fahrzeug, "startnummer": a.startnummer,
            "eingecheckt": a.eingecheckt, "beste_zeit": beste,
            "anzahl_laeufe": len(zeiten),
        })
    db.close()
    result.sort(key=lambda x: (x["rennen_datum"] or ""), reverse=True)
    return result

# ── Admin: Zeiten / Strafzeiten ───────────────────────────────
@app.post("/zeiten")
def zeit_eintragen(z: ZeitSchema, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == z.rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(status_code=404, detail="Rennen nicht gefunden")
    if r.status == "abgeschlossen":
        db.close()
        raise HTTPException(status_code=403, detail="Rennen ist abgeschlossen")
    if not db.query(RennAnmeldung).filter(
        RennAnmeldung.user_id == z.fahrer_id, RennAnmeldung.rennen_id == z.rennen_id,
    ).first():
        db.close()
        raise HTTPException(status_code=404, detail="Fahrer nicht für dieses Rennen angemeldet")
    neue_zeit = Zeit(
        fahrer_id=z.fahrer_id, rennen_id=z.rennen_id,
        rundenzeit=z.rundenzeit, strafzeit=z.strafzeit,
        gesamtzeit=z.rundenzeit + z.strafzeit,
    )
    db.add(neue_zeit)
    db.commit()
    gesamtzeit = neue_zeit.gesamtzeit
    db.close()
    return {"message": "Zeit eingetragen", "gesamtzeit": gesamtzeit}

@app.post("/strafzeiten")
def strafzeit_hinzufuegen(s: StrafzeitSchema, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == s.rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(status_code=404, detail="Rennen nicht gefunden")
    if r.status == "abgeschlossen":
        db.close()
        raise HTTPException(status_code=403, detail="Rennen ist abgeschlossen")
    u = db.query(User).filter(User.id == s.fahrer_id).first()
    name = u.name if u else str(s.fahrer_id)
    db.add(Strafzeit(fahrer_id=s.fahrer_id, rennen_id=s.rennen_id, strafzeit=s.strafzeit, grund=s.grund))
    db.commit()
    db.close()
    return {"message": f"Strafzeit +{s.strafzeit}s für {name}", "grund": s.grund}

@app.get("/zeiten/{fahrer_id}")
def zeiten_von_fahrer(fahrer_id: int):
    db = SessionLocal()
    z = db.query(Zeit).filter(Zeit.fahrer_id == fahrer_id).all()
    db.close()
    return z

# ── Check-in ──────────────────────────────────────────────────
@app.post("/checkin/{user_id}")
def checkin(user_id: int):
    db = SessionLocal()
    a = (
        db.query(RennAnmeldung).filter(RennAnmeldung.user_id == user_id)
        .order_by(RennAnmeldung.id.desc()).first()
    )
    if not a:
        db.close()
        raise HTTPException(status_code=404, detail="Fahrer nicht angemeldet")
    if a.eingecheckt:
        db.close()
        raise HTTPException(status_code=400, detail="Fahrer bereits eingecheckt")
    a.eingecheckt = True
    db.commit()
    u = db.query(User).filter(User.id == user_id).first()
    uname, snr = (u.name if u else str(user_id)), a.startnummer
    db.close()
    return {"message": f"{uname} eingecheckt!", "startnummer": snr}

@app.post("/rennen/{rennen_id}/checkin/{user_id}")
def checkin_fuer_rennen(rennen_id: int, user_id: int, admin: User = Depends(_require_admin)):
    db = SessionLocal()
    a = db.query(RennAnmeldung).filter(
        RennAnmeldung.user_id == user_id, RennAnmeldung.rennen_id == rennen_id,
    ).first()
    if not a:
        db.close()
        raise HTTPException(status_code=404, detail="Fahrer nicht für dieses Rennen angemeldet")
    a.eingecheckt = True
    db.commit()
    u = db.query(User).filter(User.id == user_id).first()
    uname, snr = (u.name if u else str(user_id)), a.startnummer
    db.close()
    return {"message": f"{uname} eingecheckt!", "startnummer": snr}

# ── Fahrer ────────────────────────────────────────────────────
@app.get("/fahrer")
def alle_fahrer():
    db = SessionLocal()
    anmeldungen = db.query(RennAnmeldung).all()
    users = {u.id: u for u in db.query(User).all()}
    db.close()
    result = []
    for a in anmeldungen:
        u = users.get(a.user_id)
        if u:
            result.append({
                "id": a.user_id, "name": u.name, "email": u.email,
                "fahrzeug": a.fahrzeug, "startnummer": a.startnummer,
                "eingecheckt": a.eingecheckt, "rennen_id": a.rennen_id,
            })
    result.sort(key=lambda x: x["startnummer"])
    return result

@app.get("/fahrer/{user_id}/qrcode")
def qrcode_generieren(user_id: int):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    anmeldung = (
        db.query(RennAnmeldung).filter(RennAnmeldung.user_id == user_id)
        .order_by(RennAnmeldung.id.desc()).first()
    )
    db.close()
    if not user or not anmeldung:
        raise HTTPException(status_code=404, detail="Fahrer nicht gefunden")
    buf = io.BytesIO(_make_qr_png(user_id))
    return StreamingResponse(buf, media_type="image/png")

# ── Netzwerk-Info ─────────────────────────────────────────────
@app.get("/netzwerk-info")
def netzwerk_info():
    ip = _local_ip()
    return {
        "local_ip": ip,
        "portal_url": f"http://{ip}:8000/app/index.html",
        "leaderboard_url": f"http://{ip}:8000/app/leaderboard.html",
        "simulator_url": f"http://{ip}:8000/simulator",
    }

# ── Ergebnisse PDF ────────────────────────────────────────────
@app.get("/rennen/{rennen_id}/ergebnisse/pdf", response_class=HTMLResponse)
def ergebnisse_pdf(rennen_id: int):
    db = SessionLocal()
    r = db.query(Rennen).filter(Rennen.id == rennen_id).first()
    if not r:
        db.close()
        raise HTTPException(status_code=404, detail="Rennen nicht gefunden")
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
    status_str = "Abgeschlossen" if r.status == "abgeschlossen" else "Rennen läuft noch"
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"><title>Ergebnisse — {_html_esc(r.name)}</title>
<style>body{{font-family:'Segoe UI',sans-serif;padding:40px;color:#1E1E1E;background:#fff}}
h1{{font-size:26px;margin-bottom:4px}}.sub{{color:#888;font-size:13px;margin-bottom:28px}}
table{{width:100%;border-collapse:collapse}}
th{{background:#1E1E1E;color:white;padding:11px 14px;font-size:12px;text-align:left}}
td{{padding:11px 14px;border-bottom:1px solid #F0F0F0;font-size:13px}}
@media print{{.no-print{{display:none}}}}</style></head>
<body>
<h1>🏁 {_html_esc(r.name)}</h1>
<p class="sub">{_html_esc(r.datum or '')} · {_html_esc(r.ort or '')} &nbsp;|&nbsp; {status_str} &nbsp;|&nbsp; {len(result)} Fahrer</p>
<button class="no-print" onclick="window.print()"
  style="background:#1E1E1E;color:white;border:none;padding:10px 22px;border-radius:8px;font-size:13px;cursor:pointer;margin-bottom:22px">
  🖨️ Drucken / Als PDF speichern</button>
<table><thead><tr>
  <th>Platz</th><th>Name</th><th>Fahrzeug</th>
  <th>Nr.</th><th>Läufe</th><th>Strafzeit</th>
  <th>Beste Runde</th><th>Beste Gesamt</th>
</tr></thead><tbody>{zeilen}</tbody></table>
</body></html>""")

# ── Kamera-System ─────────────────────────────────────────────
@app.post("/kamera/tor")
def tor_signal(signal: TorSignalSchema):
    db = SessionLocal()
    anmeldung = (
        db.query(RennAnmeldung).filter(RennAnmeldung.user_id == signal.fahrer_id)
        .order_by(RennAnmeldung.id.desc()).first()
    )
    if not anmeldung:
        db.close()
        raise HTTPException(status_code=404, detail="Fahrer nicht angemeldet")
    user = db.query(User).filter(User.id == signal.fahrer_id).first()
    user_name = user.name if user else str(signal.fahrer_id)
    rennen_id = anmeldung.rennen_id

    letzter_lauf = (
        db.query(TorSignal).filter(TorSignal.fahrer_id == signal.fahrer_id)
        .order_by(TorSignal.lauf_id.desc()).first()
    )
    if signal.tor_nr == 1:
        lauf_id = (letzter_lauf.lauf_id + 1) if letzter_lauf else 1
        db.add(TorSignal(fahrer_id=signal.fahrer_id, tor_nr=1,
                         zeitstempel=signal.zeitstempel, lauf_id=lauf_id))
        db.commit()
        db.close()
        return {"status": "start", "message": f"START {user_name} — Lauf {lauf_id}",
                "lauf_id": lauf_id, "naechstes_tor": 2}

    lauf_id = letzter_lauf.lauf_id if letzter_lauf else None
    if not lauf_id:
        db.close()
        raise HTTPException(status_code=400, detail="Kein aktiver Lauf — Tor 1 zuerst")

    start_signal = db.query(TorSignal).filter(
        TorSignal.fahrer_id == signal.fahrer_id,
        TorSignal.lauf_id == lauf_id,
        TorSignal.tor_nr == 1,
    ).first()
    if not start_signal:
        db.close()
        raise HTTPException(status_code=400, detail="Startzeit fehlt")

    zwischenzeit = round(signal.zeitstempel - start_signal.zeitstempel, 3)
    db.add(TorSignal(fahrer_id=signal.fahrer_id, tor_nr=signal.tor_nr,
                     zeitstempel=signal.zeitstempel, lauf_id=lauf_id))

    if signal.tor_nr >= ANZAHL_TORE:
        db.add(Zeit(fahrer_id=signal.fahrer_id, rennen_id=rennen_id,
                    rundenzeit=zwischenzeit, strafzeit=0.0, gesamtzeit=zwischenzeit))
        db.commit()
        db.close()
        return {"status": "ziel", "message": f"ZIEL! {zwischenzeit:.3f}s",
                "gesamtzeit": zwischenzeit, "zwischenzeit": zwischenzeit,
                "tor_nr": signal.tor_nr, "lauf_id": lauf_id}

    db.commit()
    db.close()
    return {"status": "zwischen", "message": f"Tor {signal.tor_nr} — {zwischenzeit:.3f}s",
            "zwischenzeit": zwischenzeit, "tor_nr": signal.tor_nr,
            "naechstes_tor": signal.tor_nr + 1, "lauf_id": lauf_id}

@app.get("/kamera/config")
def kamera_config():
    return {"anzahl_tore": ANZAHL_TORE}

@app.delete("/kamera/lauf/{fahrer_id}/reset")
def lauf_reset(fahrer_id: int):
    db = SessionLocal()
    db.query(TorSignal).filter(TorSignal.fahrer_id == fahrer_id).delete()
    db.commit()
    db.close()
    return {"message": "Lauf zurückgesetzt"}

# ── Kamera-Simulator ──────────────────────────────────────────
@app.get("/simulator", response_class=HTMLResponse)
def simulator():
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KI-Kamera Simulator — PMK RC-Rally</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',sans-serif;background:#0d0d1a;min-height:100vh;padding:20px;color:white}}
  .header{{max-width:660px;margin:0 auto 20px;text-align:center}}
  .badge{{display:inline-block;background:#C62828;color:white;font-size:11px;font-weight:700;padding:3px 12px;border-radius:20px;margin-bottom:8px;animation:blink 1.5s infinite}}
  @keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0.4}}}}
  h1{{font-size:20px}}
  .card{{background:#16213e;border-radius:12px;padding:20px;max-width:660px;margin:0 auto 14px;border:1px solid #0f3460}}
  .card h2{{font-size:13px;font-weight:700;color:#C8A415;margin-bottom:14px}}
  select{{width:100%;padding:9px 12px;background:#0f3460;border:1.5px solid #1a4a8a;border-radius:8px;font-size:13px;color:white;outline:none}}
  .timer{{text-align:center;padding:18px;background:#0a1628;border-radius:10px;margin:12px 0;border:1px solid #1a4a8a}}
  .timer-label{{font-size:12px;color:#888;margin-bottom:6px}}
  .timer-zahl{{font-size:46px;font-weight:800;color:#C8A415;font-family:'Courier New',monospace}}
  .timer-zahl.run{{animation:pulse 1s infinite}} @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.7}}}}
  .tore-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}}
  .tor-btn{{padding:12px 6px;border:none;border-radius:9px;font-size:13px;font-weight:700;cursor:pointer;background:#0f3460;color:#888;border:1.5px solid #1a4a8a;white-space:pre;transition:all 0.15s}}
  .tor-btn.aktiv{{background:#2E7D32;color:white;border-color:#2E7D32}}
  .tor-btn.passiert{{background:#1a4a8a;color:#69F0AE}}
  .tor-btn.ziel{{background:#C62828;border-color:#C62828;color:white}}
  .tor-btn:disabled{{opacity:0.3;cursor:not-allowed}}
  .status{{padding:11px;border-radius:8px;margin-top:10px;font-size:13px;font-weight:600;text-align:center;display:none}}
  .status.ok{{background:#1B5E20;color:#69F0AE}} .status.err{{background:#4a0000;color:#FF5252}}
  .status.info{{background:#0d2b5e;color:#82B1FF}} .status.zw{{background:#1a3060;color:#FFD740}}
  .zeit-row{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #1a3060;font-size:12px;color:#888}}
  .zeit-val{{color:#69F0AE;font-family:monospace;font-weight:700}}
  .log{{background:#0a0a1a;border-radius:8px;padding:10px;font-family:monospace;font-size:10px;color:#555;max-height:120px;overflow-y:auto}}
  .log .ok{{color:#69F0AE}} .log .err{{color:#FF5252}} .log .info{{color:#82B1FF}}
  .nav{{text-align:center;margin-top:14px;font-size:12px}}
  .nav a{{color:#C8A415;text-decoration:none;margin:0 8px;font-weight:600}}
</style></head>
<body>
<div class="header">
  <div class="badge">● KI-KAMERA SIMULATOR</div>
  <h1>Mehrtor-Simulator — {ANZAHL_TORE} Tore</h1>
</div>
<div class="card">
  <h2>🏎️ Fahrer</h2>
  <select id="sel" onchange="onFahrer()"><option value="">— wird geladen —</option></select>
</div>
<div class="card">
  <h2>📡 Tore</h2>
  <div class="timer"><div class="timer-label" id="tlabel">Fahrer wählen</div>
    <div class="timer-zahl" id="tzahl">00.000</div></div>
  <div class="tore-grid" id="grid"></div>
  <div id="zwischen"></div>
  <div class="status" id="st"></div>
  <button id="resetBtn" onclick="doReset()" style="display:none;width:100%;margin-top:8px;padding:7px;background:none;border:1px solid #4a0000;color:#FF5252;border-radius:6px;cursor:pointer;font-size:12px">✕ Lauf abbrechen</button>
</div>
<div class="card"><h2>🏁 Zeiten</h2><div id="zeiten"><p style="color:#555;font-size:12px">Keine Zeiten.</p></div></div>
<div class="card"><h2>📋 Log</h2><div class="log" id="log"><div class="info">Bereit.</div></div></div>
<div class="nav">
  <a href="/app/index.html">Portal</a>
  <a href="/app/leaderboard.html">Leaderboard</a>
  <a href="/app/admin.html">Admin</a>
</div>
<script>
const API='';const TORE={ANZAHL_TORE};
let fahrer=null,naechstes=1,startTs=null,tint=null,zw=[];
function lg(t,c='info'){{const el=document.getElementById('log'),d=new Date().toTimeString().slice(0,8);el.innerHTML=`<div class="${{c}}">[${{d}}] ${{t}}</div>`+el.innerHTML}}
function st(t,c){{const e=document.getElementById('st');e.textContent=t;e.className='status '+c;e.style.display='block'}}
function fmt(s){{return s.toFixed(3).padStart(6,'0')}}
function aufbauen(){{
  const g=document.getElementById('grid');g.innerHTML='';
  for(let i=1;i<=TORE;i++){{
    const b=document.createElement('button');
    b.className='tor-btn'+(i===TORE?' ziel':'');b.id='t'+i;b.disabled=true;
    b.textContent=i===1?'🚦 Tor 1\\nSTART':i===TORE?`🏁 Tor ${{i}}\\nZIEL`:`📡 Tor ${{i}}`;
    b.onclick=()=>send(i);g.appendChild(b);
  }}
}}
function updTore(n){{
  for(let i=1;i<=TORE;i++){{
    const b=document.getElementById('t'+i);if(!b)continue;
    b.disabled=true;b.classList.remove('aktiv','passiert');
    if(i<n)b.classList.add('passiert');
    if(i===n){{b.classList.add('aktiv');b.disabled=false;}}
  }}
}}
function timerStart(){{startTs=Date.now();zw=[];document.getElementById('tzahl').classList.add('run');document.getElementById('tlabel').textContent='⏱️ läuft...';document.getElementById('resetBtn').style.display='block';tint=setInterval(()=>{{document.getElementById('tzahl').textContent=fmt((Date.now()-startTs)/1000)}},50)}}
function timerStop(v){{if(tint){{clearInterval(tint);tint=null}}document.getElementById('tzahl').classList.remove('run');if(v!==undefined)document.getElementById('tzahl').textContent=fmt(v);document.getElementById('tlabel').textContent='Fertig';document.getElementById('resetBtn').style.display='none'}}
async function loadFahrer(){{
  try{{const r=await fetch(API+'/fahrer'),d=await r.json();
  const s=document.getElementById('sel');
  s.innerHTML='<option value="">— Fahrer wählen —</option>'+d.map(f=>`<option value="${{f.id}}">#${{f.startnummer}} ${{f.name}} (${{f.fahrzeug}})</option>`).join('');
  lg('Fahrer: '+d.length,'ok')}}catch(e){{lg(e.message,'err')}}
}}
function onFahrer(){{
  fahrer=parseInt(document.getElementById('sel').value)||null;
  if(!fahrer){{updTore(0);return}}
  naechstes=1;updTore(1);document.getElementById('tlabel').textContent='Tor 1 drücken';document.getElementById('tzahl').textContent='00.000';st('Bereit','info');loadZeiten();
}}
async function send(nr){{
  if(!fahrer)return;
  const ts=Date.now()/1000;document.getElementById('t'+nr).disabled=true;
  try{{
    const r=await fetch(API+'/kamera/tor',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{fahrer_id:fahrer,tor_nr:nr,zeitstempel:ts}})}});
    const d=await r.json();
    if(!r.ok){{st('Fehler: '+d.detail,'err');lg(d.detail,'err');document.getElementById('t'+nr).disabled=false;return}}
    lg(d.message,'ok');
    if(d.status==='start'){{timerStart();naechstes=2;updTore(2);st('START!','info')}}
    else if(d.status==='zwischen'){{zw.push({{t:nr,z:d.zwischenzeit}});document.getElementById('zwischen').innerHTML=zw.map(x=>`<div style="font-size:12px;color:#FFD740;padding:3px 0">Tor ${{x.t}}: ${{x.z.toFixed(3)}}s</div>`).join('');naechstes=d.naechstes_tor;updTore(naechstes);st(`Tor ${{nr}} — ${{d.zwischenzeit.toFixed(3)}}s`,'zw')}}
    else if(d.status==='ziel'){{timerStop(d.gesamtzeit);updTore(0);st(`ZIEL! ${{d.gesamtzeit.toFixed(3)}}s`,'ok');setTimeout(()=>{{updTore(1);document.getElementById('zwischen').innerHTML='';document.getElementById('tlabel').textContent='Nächster Lauf'}},4000);loadZeiten()}}
  }}catch(e){{lg(e.message,'err');st('Netzwerkfehler','err');document.getElementById('t'+nr).disabled=false}}
}}
async function doReset(){{
  if(!fahrer||!confirm('Abbrechen?'))return;
  await fetch(API+'/kamera/lauf/'+fahrer+'/reset',{{method:'DELETE'}});
  if(tint){{clearInterval(tint);tint=null}}naechstes=1;updTore(1);document.getElementById('tzahl').textContent='00.000';document.getElementById('tlabel').textContent='Abgebrochen';document.getElementById('zwischen').innerHTML='';document.getElementById('resetBtn').style.display='none';st('Zurückgesetzt','info');
}}
async function loadZeiten(){{
  if(!fahrer)return;
  try{{const r=await fetch(API+'/zeiten/'+fahrer),d=await r.json();
  const box=document.getElementById('zeiten');
  if(!d.length){{box.innerHTML='<p style="color:#555;font-size:12px">Keine Zeiten.</p>';return}}
  const best=Math.min(...d.map(z=>z.gesamtzeit));
  box.innerHTML=d.map((z,i)=>`<div class="zeit-row"><span>Lauf ${{i+1}}</span><span class="zeit-val">${{z.gesamtzeit.toFixed(3)}}s</span></div>`).join('')+`<div style="color:#C8A415;font-weight:700;margin-top:8px;font-size:13px">⭐ Beste: ${{best.toFixed(3)}}s</div>`
  }}catch(e){{}}
}}
aufbauen();loadFahrer();
</script>
</body></html>"""
    return HTMLResponse(content=html)

# ── Root ──────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "PMK RC-Rally API", "docs": "/docs"}

# ── Static Files (/app/) ──────────────────────────────────────
_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend):
    app.mount("/app", StaticFiles(directory=_frontend, html=True), name="frontend")
