"""Admin-Passwort zurücksetzen: python reset_admin.py"""
import hashlib, sys
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

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

Session = sessionmaker(bind=engine)
db = Session()

email = input("Admin E-Mail: ").strip().lower()
user  = db.query(User).filter(User.email == email).first()

if not user:
    print(f"Kein User mit E-Mail '{email}' gefunden.")
    sys.exit(1)

pw = input("Neues Passwort: ").strip()
if not pw:
    print("Passwort darf nicht leer sein.")
    sys.exit(1)

user.passwort_hash = hashlib.sha256(pw.encode()).hexdigest()
user.rolle         = "admin"
user.token         = None
db.commit()
print(f"✅ {user.name} ({email}) ist jetzt Admin.")
