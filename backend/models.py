from sqlalchemy import Column, Integer, String, Float, Boolean
from database import Base

class Fahrer(Base):
    __tablename__ = "fahrer"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True)
    startnummer = Column(Integer)
    fahrzeug = Column(String)
    einwilligung = Column(Boolean, default=False)

class Zeit(Base):
    __tablename__ = "zeiten"

    id = Column(Integer, primary_key=True, index=True)
    fahrer_id = Column(Integer)
    rundenzeit = Column(Float)
    strafzeit = Column(Float, default=0.0)
    gesamtzeit = Column(Float)