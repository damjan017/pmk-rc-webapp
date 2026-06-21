"""
demo_daten.py — Fügt realistische Demo-Daten in die Datenbank ein.
Ausführen: python demo_daten.py
Achtung: Bestehende Fahrer/Rennen/Zeiten bleiben erhalten.
"""

import hashlib, random, sqlite3
from datetime import datetime, timedelta

DB = "./rally.db"
con = sqlite3.connect(DB)
cur = con.cursor()

def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()

# ──────────────────────────────────────────────────────────────
# 1. FAHRER (30 Personen)
# ──────────────────────────────────────────────────────────────
fahrer_liste = [
    ("Max Müller",        "max.mueller@mail.de"),
    ("Laura Schmidt",     "laura.schmidt@mail.de"),
    ("Jonas Weber",       "jonas.weber@mail.de"),
    ("Sophie Fischer",    "sophie.fischer@mail.de"),
    ("Lukas Bauer",       "lukas.bauer@mail.de"),
    ("Emma Wagner",       "emma.wagner@mail.de"),
    ("Finn Hoffmann",     "finn.hoffmann@mail.de"),
    ("Lena Koch",         "lena.koch@mail.de"),
    ("Noah Richter",      "noah.richter@mail.de"),
    ("Mia Klein",         "mia.klein@mail.de"),
    ("Tim Wolf",          "tim.wolf@mail.de"),
    ("Anna Schröder",     "anna.schroeder@mail.de"),
    ("Ben Braun",         "ben.braun@mail.de"),
    ("Lara Zimmermann",   "lara.zimmermann@mail.de"),
    ("Paul Krause",       "paul.krause@mail.de"),
    ("Julia Lange",       "julia.lange@mail.de"),
    ("Leon Schmitt",      "leon.schmitt@mail.de"),
    ("Leonie Werner",     "leonie.werner@mail.de"),
    ("Felix Meier",       "felix.meier@mail.de"),
    ("Hanna Schulz",      "hanna.schulz@mail.de"),
    ("Moritz König",      "moritz.koenig@mail.de"),
    ("Klara Weiß",        "klara.weiss@mail.de"),
    ("Nico Hartmann",     "nico.hartmann@mail.de"),
    ("Sara Vogel",        "sara.vogel@mail.de"),
    ("Elias Beck",        "elias.beck@mail.de"),
    ("Marie Möller",      "marie.moeller@mail.de"),
    ("David Kunze",       "david.kunze@mail.de"),
    ("Hannah Berger",     "hannah.berger@mail.de"),
    ("Tobias Roth",       "tobias.roth@mail.de"),
    ("Amelie Sommer",     "amelie.sommer@mail.de"),
]

fahrer_ids = []
for name, email in fahrer_liste:
    existing = cur.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        fahrer_ids.append(existing[0])
    else:
        cur.execute(
            "INSERT INTO users (name, email, passwort_hash, rolle) VALUES (?,?,?,?)",
            (name, email, sha256("Fahrer123!"), "fahrer")
        )
        fahrer_ids.append(cur.lastrowid)

con.commit()
print(f"✓ {len(fahrer_ids)} Fahrer eingefügt/gefunden")

# ──────────────────────────────────────────────────────────────
# 2. FAHRZEUGE pro Fahrer
# ──────────────────────────────────────────────────────────────
fahrzeuge = [
    "Traxxas Rustler 4x4",
    "Tamiya TA08 Pro",
    "Arrma Typhon 6S",
    "HPI Bullet ST 3.0",
    "Kyosho Inferno MP10",
    "Losi 22S SCT",
    "Team Associated RC8B4",
    "Axial RR10 Bomber",
    "Tekno EB48 2.1",
    "Mugen Seiki MBX8",
]

# ──────────────────────────────────────────────────────────────
# 3. RENNEN (5 Rennen in verschiedenen Zuständen)
# ──────────────────────────────────────────────────────────────
heute = datetime.now()

rennen_daten = [
    {
        "name": "TechDay Qualifikation 2026",
        "datum": (heute + timedelta(days=4)).strftime("%Y-%m-%d"),
        "uhrzeit": "10:00",
        "ort": "Hochschule Pforzheim, T1-Gebäude",
        "beschreibung": "Offizielle Qualifikation für den TechDay 2026. Alle Fahrerklassen willkommen.",
        "max_teilnehmer": 30,
        "status": "offen",
        "fahrzeug_klasse": "Buggy 1:8",
        "reifen_vorgabe": "Slicks oder M-Compound",
        "max_breite_mm": 320,
        "sonstige_regeln": "Elektro und Verbrenner getrennt gewertet. Mindest-Akkukapazität 4000 mAh.",
    },
    {
        "name": "TechDay Finale 2026",
        "datum": (heute + timedelta(days=6)).strftime("%Y-%m-%d"),
        "uhrzeit": "14:00",
        "ort": "Hochschule Pforzheim, T1-Gebäude",
        "beschreibung": "Das große Finale des TechDay 2026. Top 16 der Qualifikation treten gegeneinander an.",
        "max_teilnehmer": 16,
        "status": "offen",
        "fahrzeug_klasse": "Buggy 1:8",
        "reifen_vorgabe": "Slicks",
        "max_breite_mm": 320,
        "sonstige_regeln": "Nur qualifizierte Fahrer. 5 Runden Pflichtprogramm.",
    },
    {
        "name": "Pforzheim Open Cup — Runde 3",
        "datum": (heute - timedelta(days=3)).strftime("%Y-%m-%d"),
        "uhrzeit": "09:00",
        "ort": "RC Arena Pforzheim, Industriestr. 12",
        "beschreibung": "Dritte Runde des Pforzheim Open Cup. Gewertet wird nach DMSB-Reglement.",
        "max_teilnehmer": 25,
        "status": "abgeschlossen",
        "fahrzeug_klasse": "Truggy 1:8",
        "reifen_vorgabe": "Alle zugelassen",
        "max_breite_mm": 350,
        "sonstige_regeln": "10 Minuten Laufzeit, 3 Läufe pro Fahrer, bestes Ergebnis zählt.",
    },
    {
        "name": "Karlsruhe Night Race",
        "datum": (heute - timedelta(days=10)).strftime("%Y-%m-%d"),
        "uhrzeit": "19:00",
        "ort": "Modellsportzentrum Karlsruhe",
        "beschreibung": "Spektakuläres Nachtrennen mit LED-beleuchteten Fahrzeugen.",
        "max_teilnehmer": 20,
        "status": "abgeschlossen",
        "fahrzeug_klasse": "Short Course 1:10",
        "reifen_vorgabe": "Geländereifen",
        "max_breite_mm": 280,
        "sonstige_regeln": "LED-Beleuchtung am Fahrzeug Pflicht. Mindesthöhe Karosserie 80mm.",
    },
    {
        "name": "PMK Testrennen — Gruppe A",
        "datum": heute.strftime("%Y-%m-%d"),
        "uhrzeit": "15:30",
        "ort": "Hochschule Pforzheim, Parkplatz P3",
        "beschreibung": "Internes Testrennen für den PMK-Kurs zur Softwaredemonstration.",
        "max_teilnehmer": 15,
        "status": "laufend",
        "fahrzeug_klasse": "Alle Klassen",
        "reifen_vorgabe": "Keine Vorgabe",
        "max_breite_mm": None,
        "sonstige_regeln": "Demo-Betrieb. Zeiten werden zu Präsentationszwecken erfasst.",
    },
]

rennen_ids = []
for r in rennen_daten:
    cur.execute("""
        INSERT INTO rennen
        (name, datum, uhrzeit, ort, beschreibung, max_teilnehmer, status,
         erstellt_am, fahrzeug_klasse, reifen_vorgabe, max_breite_mm, sonstige_regeln)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        r["name"], r["datum"], r["uhrzeit"], r["ort"], r["beschreibung"],
        r["max_teilnehmer"], r["status"], heute.strftime("%Y-%m-%d %H:%M"),
        r["fahrzeug_klasse"], r["reifen_vorgabe"], r["max_breite_mm"], r["sonstige_regeln"]
    ))
    rennen_ids.append(cur.lastrowid)

con.commit()
print(f"✓ {len(rennen_ids)} Rennen eingefügt")

# ──────────────────────────────────────────────────────────────
# 4. ANMELDUNGEN + ZEITEN
# ──────────────────────────────────────────────────────────────
def anmelden_und_zeiten(rennen_id, teilnehmer_ids, mit_zeiten=False):
    for i, uid in enumerate(teilnehmer_ids):
        fz = random.choice(fahrzeuge)
        existing = cur.execute(
            "SELECT id FROM renn_anmeldungen WHERE user_id=? AND rennen_id=?",
            (uid, rennen_id)
        ).fetchone()
        if not existing:
            cur.execute("""
                INSERT INTO renn_anmeldungen
                (user_id, rennen_id, fahrzeug, einwilligung, startnummer, eingecheckt)
                VALUES (?,?,?,1,?,?)
            """, (uid, rennen_id, fz, i + 1, 1 if mit_zeiten else 0))

        if mit_zeiten:
            # 2–3 Rundenzeiten pro Fahrer (40–90 Sek, realistisch)
            basis = random.uniform(42.0, 78.0)
            for lauf in range(random.randint(2, 3)):
                rz = round(basis + random.uniform(-1.5, 4.0), 3)
                straf = round(random.choice([0, 0, 0, 2.0, 5.0]), 1)
                gz = round(rz + straf, 3)
                cur.execute("""
                    INSERT INTO zeiten (fahrer_id, rennen_id, rundenzeit, strafzeit, gesamtzeit)
                    VALUES (?,?,?,?,?)
                """, (uid, rennen_id, rz, straf, gz))

# Rennen 1 (offen): 18 angemeldete Fahrer, keine Zeiten
anmelden_und_zeiten(rennen_ids[0], random.sample(fahrer_ids, 18), mit_zeiten=False)

# Rennen 2 (offen / Finale): 10 angemeldete Fahrer
anmelden_und_zeiten(rennen_ids[1], random.sample(fahrer_ids, 10), mit_zeiten=False)

# Rennen 3 (abgeschlossen): 22 Fahrer mit Zeiten
anmelden_und_zeiten(rennen_ids[2], random.sample(fahrer_ids, 22), mit_zeiten=True)

# Rennen 4 (abgeschlossen): 17 Fahrer mit Zeiten
anmelden_und_zeiten(rennen_ids[3], random.sample(fahrer_ids, 17), mit_zeiten=True)

# Rennen 5 (laufend): 12 Fahrer, einige schon mit Zeiten
teilnehmer_laufend = random.sample(fahrer_ids, 12)
anmelden_und_zeiten(rennen_ids[4], teilnehmer_laufend, mit_zeiten=True)

con.commit()
print("✓ Anmeldungen und Zeiten eingefügt")

# ──────────────────────────────────────────────────────────────
# 5. ZUSAMMENFASSUNG
# ──────────────────────────────────────────────────────────────
print("\n" + "="*45)
print("  DEMO-DATEN ERFOLGREICH EINGEFÜGT")
print("="*45)
print(f"  Fahrer:  {len(fahrer_ids)}")
print(f"  Rennen:  {len(rennen_ids)}")
print()
for i, r in enumerate(rennen_daten):
    print(f"  [{r['status'].upper():12}] {r['name']}")
print()
print("  Fahrer-Login: beliebige Email aus der Liste")
print("  Passwort:     Fahrer123!")
print("="*45)

con.close()
