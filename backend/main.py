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