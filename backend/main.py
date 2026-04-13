from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./rally.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Fahrer(Base):
    __tablename__ = "fahrer"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    startnummer = Column(Integer)
    fahrzeug = Column(String)
    einwilligung = Column(Boolean, default=False)

class Zeit(Base):
    __tablename__ = "zeiten"
    id = Column(Integer, primary_key=True)
    fahrer_id = Column(Integer)
    rundenzeit = Column(Float)
    strafzeit = Column(Float, default=0.0)
    gesamtzeit = Column(Float)

Base.metadata.create_all(bind=engine)
app = FastAPI()

class FahrerCreate(BaseModel):
    name: str
    email: str
    fahrzeug: str
    einwilligung: bool

@app.get("/")
def root():
    return {"message": "PMK RC-Rally API läuft!"}

@app.post("/fahrer")
def fahrer_registrieren(fahrer: FahrerCreate):
    if not fahrer.einwilligung:
        raise HTTPException(status_code=400, detail="Einwilligung erforderlich")
    db = SessionLocal()
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
    return {"message": f"Fahrer {fahrer.name} registriert!", "startnummer": neuer_fahrer.startnummer}

@app.get("/fahrer")
def alle_fahrer():
    db = SessionLocal()
    fahrer = db.query(Fahrer).all()
    db.close()
    return fahrer

class ZeitCreate(BaseModel):
    fahrer_id: int
    rundenzeit: float
    strafzeit: float = 0.0

@app.post("/zeiten")
def zeit_eintragen(z: ZeitCreate):
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
    return {"message": f"Zeit eingetragen", "gesamtzeit": neue_zeit.gesamtzeit}

@app.get("/zeiten/{fahrer_id}")
def zeiten_von_fahrer(fahrer_id: int):
    db = SessionLocal()
    zeiten = db.query(Zeit).filter(Zeit.fahrer_id == fahrer_id).all()
    db.close()
    return zeiten