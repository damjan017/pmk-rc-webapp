"""
Admin-Passwort zurücksetzen oder neuen Admin anlegen.
Aufruf:
    python reset_admin.py
"""
import hashlib
import sys
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./rally.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    passwort_hash = Column(String)
    rolle = Column(String, default="fahrer")
    token = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def main():
    print("=== PMK RC-Rally — Admin-Reset ===")
    email = input("Admin-E-Mail: ").strip().lower()
    passwort = input("Neues Passwort: ").strip()
    if not email or not passwort:
        print("Abgebrochen — E-Mail und Passwort dürfen nicht leer sein.")
        sys.exit(1)

    db = Session()
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.passwort_hash = sha256(passwort)
        user.rolle = "admin"
        user.token = None
        db.commit()
        print(f"✓ Passwort für '{user.name}' ({email}) zurückgesetzt und Rolle auf 'admin' gesetzt.")
    else:
        name = input("Name für neuen Admin: ").strip()
        if not name:
            print("Abgebrochen.")
            sys.exit(1)
        new_admin = User(name=name, email=email, passwort_hash=sha256(passwort), rolle="admin")
        db.add(new_admin)
        db.commit()
        print(f"✓ Neuer Admin '{name}' ({email}) erstellt.")
    db.close()

if __name__ == "__main__":
    main()
