"""
Admin-Account erstellen oder zuruecksetzen.

Verwendung:
  python reset_admin.py            -> erstellt/setzt Standard-Admin (admin@pmk.de / Admin2026!)
  python reset_admin.py --custom   -> interaktive Eingabe
"""
import hashlib, sys
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Standard-Admin-Zugangsdaten
DEFAULT_EMAIL    = "admin@pmk.de"
DEFAULT_PASSWORT = "Admin2026!"
DEFAULT_NAME     = "PMK Admin"

engine = create_engine("sqlite:///./rally.db", connect_args={"check_same_thread": False})
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    name          = Column(String)
    email         = Column(String, unique=True)
    passwort_hash = Column(String)
    rolle         = Column(String)
    token         = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)

def sha256(s): return hashlib.sha256(s.encode()).hexdigest()

custom = "--custom" in sys.argv

if custom:
    email    = input("Admin E-Mail: ").strip().lower()
    pw       = input("Neues Passwort: ").strip()
    name     = input("Name (leer = 'PMK Admin'): ").strip() or DEFAULT_NAME
else:
    email, pw, name = DEFAULT_EMAIL, DEFAULT_PASSWORT, DEFAULT_NAME
    print(f"Standard-Admin: {email} / {pw}")

if not email or not pw:
    print("Abgebrochen."); sys.exit(1)

db   = Session()
user = db.query(User).filter(User.email == email).first()
if user:
    user.passwort_hash = sha256(pw); user.rolle = "admin"; user.token = None; user.name = name
    db.commit()
    print(f"\nOK Admin aktualisiert: {name} ({email})")
else:
    db.add(User(name=name, email=email, passwort_hash=sha256(pw), rolle="admin"))
    db.commit()
    print(f"\nOK Admin erstellt: {name} ({email})")
db.close()
print(f"\nLogin:       http://localhost:5173/login")
print(f"Admin-Panel: http://localhost:5173/admin")
