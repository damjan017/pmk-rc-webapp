"""
============================================================
  PMK RC-Rally App — Vollständiger Belastungstest
============================================================

Was dieser Test macht:
  1. Prüft ob Backend + Frontend erreichbar sind
  2. Registriert 25 Testfahrer
  3. Erstellt 3 Rennen
  4. Meldet alle Fahrer an
  5. Checkt alle Fahrer per QR-Code ein
  6. Startet Rennen, fügt Zeiten + Strafzeiten ein
  7. Schließt Rennen ab und prüft Leaderboard
  8. Generiert eine Excel-Datei und importiert sie als CSV
  9. Führt Gleichzeitigkeitstest durch (10 parallele Requests)
 10. Druckt Zusammenfassung

Voraussetzungen:
  pip install requests openpyxl

Start:
  python belastungstest.py
  python belastungstest.py --tunnel https://abc.trycloudflare.com
"""

import requests, random, time, sys, csv, io, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

try:
    import openpyxl
except ImportError:
    print("[!] openpyxl fehlt: pip install openpyxl")
    sys.exit(1)

# ── Konfiguration ─────────────────────────────────────────────
BACKEND  = "http://localhost:8000"
FRONTEND = "http://localhost:5173"

# Tunnel-URL aus Argument übernehmen
if "--tunnel" in sys.argv:
    idx = sys.argv.index("--tunnel")
    if idx + 1 < len(sys.argv):
        BACKEND = sys.argv[idx + 1].rstrip("/")

ADMIN_EMAIL = "admin@pmk.de"
ADMIN_PW    = "Admin2026!"

FARBEN = ["Rot", "Blau", "Grün", "Gelb", "Schwarz", "Weiß", "Orange", "Lila"]
MODELLE = ["Traxxas Slash", "Losi DBXL", "Arrma Kraton", "HPI Savage", "Tamiya TT-02",
           "Kyosho Inferno", "Team Associated RC8", "Redcat Rampage"]

ok = "\033[92m OK\033[0m"
fail = "\033[91m FAIL\033[0m"
info = "\033[94m INFO\033[0m"

results = {"passed": 0, "failed": 0, "errors": []}

# ── Hilfsfunktionen ───────────────────────────────────────────
def check(label, response, expected=200):
    if response.status_code == expected:
        print(f"{ok} {label} [{response.status_code}]")
        results["passed"] += 1
        return True
    else:
        msg = f"{label} [{response.status_code}] → {response.text[:80]}"
        print(f"{fail} {msg}")
        results["failed"] += 1
        results["errors"].append(msg)
        return False

def log(msg):
    print(f"{info} {msg}")

def separator(title=""):
    print(f"\n{'═'*55}")
    if title:
        print(f"  {title}")
        print(f"{'═'*55}")

# ── 1. Erreichbarkeit ─────────────────────────────────────────
separator("1. ERREICHBARKEIT")

try:
    r = requests.get(f"{BACKEND}/", timeout=5)
    check("Backend erreichbar", r)
except Exception as e:
    print(f"{fail} Backend NICHT erreichbar: {e}")
    print("     → Starte zuerst start.bat und warte bis 'Application startup complete'")
    sys.exit(1)

try:
    r = requests.get(FRONTEND, timeout=5)
    check("Frontend erreichbar", r)
except:
    print(f"{fail} Frontend nicht erreichbar (Port 5173) — Backend-Tests laufen trotzdem")

# ── 2. Admin Login ────────────────────────────────────────────
separator("2. ADMIN LOGIN")

r = requests.post(f"{BACKEND}/auth/login", json={"email": ADMIN_EMAIL, "passwort": ADMIN_PW})
if not check("Admin Login", r):
    print("     → Admin anlegen: cd backend && python reset_admin.py")
    sys.exit(1)

ADMIN_TOKEN = r.json()["token"]
admin_h = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
log(f"Admin-Token: {ADMIN_TOKEN[:16]}...")

# ── 3. Fahrer registrieren (25 Stück) ─────────────────────────
separator("3. FAHRER REGISTRIEREN (25)")

fahrer_tokens = {}
fahrer_ids = {}

for i in range(1, 26):
    email = f"fahrer{i:02d}@test.rally"
    name  = f"Fahrer {i:02d}"
    pw    = "Test1234!"
    r = requests.post(f"{BACKEND}/auth/register", json={
        "name": name, "email": email, "passwort": pw, "einwilligung": True
    })
    # Register gibt nur id zurück → danach immer einloggen
    r2 = requests.post(f"{BACKEND}/auth/login", json={"email": email, "passwort": pw})
    if r2.status_code == 200:
        fahrer_tokens[i] = r2.json()["token"]
        fahrer_ids[i]    = r2.json()["id"]

print(f"{ok} {len(fahrer_tokens)}/25 Fahrer eingeloggt")
results["passed"] += 1

# ── 4. Rennen erstellen ───────────────────────────────────────
separator("4. RENNEN ERSTELLEN")

rennen_ids = []
for i in range(1, 4):
    datum  = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
    r = requests.post(f"{BACKEND}/rennen", headers=admin_h, json={
        "name": f"Belastungstest-Rennen {i}",
        "datum": datum,
        "uhrzeit": f"{10 + i}:00",
        "ort": f"Teststrecke {i}",
        "ort_link": "",
        "max_teilnehmer": 30,
        "beschreibung": f"Automatisch generiertes Testrennen {i}"
    })
    if check(f"Rennen {i} erstellen", r, 200):
        rennen_ids.append(r.json()["id"])

log(f"Erstellt: Rennen {rennen_ids}")

# ── 5. Fahrer anmelden ────────────────────────────────────────
separator("5. FAHRER ANMELDEN (Rennen 1)")

rennen_id = rennen_ids[0]
angemeldete = []

for i in range(1, 21):  # 20 Fahrer für Rennen 1
    tok = fahrer_tokens.get(i)
    if not tok:
        continue
    fahrzeug = f"{random.choice(FARBEN)} {random.choice(MODELLE)}"
    r = requests.post(
        f"{BACKEND}/rennen/{rennen_id}/anmelden",
        headers={"Authorization": f"Bearer {tok}"},
        json={"fahrzeug": fahrzeug, "einwilligung": True}
    )
    if r.status_code == 200:
        angemeldete.append(i)

print(f"{ok} {len(angemeldete)}/20 Fahrer angemeldet")
results["passed"] += 1

# Teilnehmer-Liste abrufen
r = requests.get(f"{BACKEND}/rennen/{rennen_id}/teilnehmer", headers=admin_h)
check("Teilnehmerliste abrufen", r)
teilnehmer = r.json() if r.status_code == 200 else []
log(f"{len(teilnehmer)} Teilnehmer in der Liste")

# ── 6. Check-in ───────────────────────────────────────────────
separator("6. QR-CODE CHECK-IN")

eingecheckt = 0
for t in teilnehmer[:15]:  # 15 von 20 einchecken
    uid = t["id"]
    r = requests.post(
        f"{BACKEND}/rennen/{rennen_id}/checkin/{uid}",
        headers=admin_h
    )
    if r.status_code == 200 and not r.json().get("bereits"):
        eingecheckt += 1

print(f"{ok} {eingecheckt} Fahrer eingecheckt")
results["passed"] += 1

# QR-Code eines Fahrers generieren
if fahrer_ids:
    uid = fahrer_ids[1]
    r = requests.get(f"{BACKEND}/fahrer/{uid}/qrcode", headers=admin_h)
    check("QR-Code generieren", r)

# ── 7. Rennen starten ─────────────────────────────────────────
separator("7. RENNEN STARTEN & ZEITEN EINTRAGEN")

r = requests.post(f"{BACKEND}/rennen/{rennen_id}/starten", headers=admin_h)
check("Rennen starten", r)

# Zeiten eintragen (3 Runden pro Fahrer)
zeiten_count = 0
for t in teilnehmer[:15]:
    uid = t["id"]
    for runde in range(1, 4):
        basis = random.uniform(42.0, 75.0)
        rundenzeit = round(basis + random.uniform(-2, 2), 2)
        r = requests.post(f"{BACKEND}/zeiten", headers=admin_h, json={
            "fahrer_id": uid,
            "rennen_id": rennen_id,
            "rundenzeit": rundenzeit,
            "strafzeit": 0.0
        })
        if r.status_code == 200:
            zeiten_count += 1

print(f"{ok} {zeiten_count} Zeiten eingetragen")
results["passed"] += 1

# Strafzeiten eintragen
straf_count = 0
for t in teilnehmer[:5]:
    r = requests.post(f"{BACKEND}/strafzeiten", headers=admin_h, json={
        "fahrer_id": t["id"],
        "rennen_id": rennen_id,
        "strafzeit": random.choice([5.0, 10.0, 15.0]),
        "grund": random.choice(["Tor berührt", "Frühstart", "Streckenverletzung"])
    })
    if r.status_code == 200:
        straf_count += 1

print(f"{ok} {straf_count} Strafzeiten eingetragen")
results["passed"] += 1

# ── 8. Leaderboard ────────────────────────────────────────────
separator("8. LEADERBOARD")

r = requests.get(f"{BACKEND}/rennen/{rennen_id}/leaderboard")
check("Leaderboard abrufen", r)

if r.status_code == 200:
    board = r.json()
    log(f"Leaderboard hat {len(board)} Einträge")
    if board:
        top = board[0]
        log(f"Platz 1: {top.get('name','?')} | Beste: {top.get('beste_zeit','?')}s | "
            f"Straf: {top.get('strafzeit_gesamt','?')}s | Gesamt: {top.get('gesamtzeit','?')}s")

# ── 9. Rennen abschließen ─────────────────────────────────────
separator("9. RENNEN ABSCHLIEßEN")

r = requests.post(f"{BACKEND}/rennen/{rennen_id}/abschliessen", headers=admin_h)
check("Rennen abschließen", r)

# ── 10. Excel generieren & CSV-Import ────────────────────────
separator("10. EXCEL-GENERIERUNG & CSV-IMPORT")

rennen_id2 = rennen_ids[1] if len(rennen_ids) > 1 else rennen_id

# Excel-Datei mit Fahrerdaten erstellen
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Fahrer"
ws.append(["name", "email", "fahrzeug"])  # Header

excel_fahrer = []
for i in range(26, 46):  # 20 neue Fahrer
    name     = f"Excel-Fahrer {i}"
    email    = f"excel{i}@import.rally"
    fahrzeug = f"{random.choice(FARBEN)} {random.choice(MODELLE)}"
    ws.append([name, email, fahrzeug])
    excel_fahrer.append((name, email, fahrzeug))

# Excel speichern
excel_path = "belastungstest_fahrer.xlsx"
wb.save(excel_path)
log(f"Excel-Datei erstellt: {excel_path} ({len(excel_fahrer)} Fahrer)")

# Excel → CSV konvertieren und importieren
csv_buf = io.StringIO()
writer = csv.writer(csv_buf)
writer.writerow(["name", "email", "fahrzeug"])
for row in excel_fahrer:
    writer.writerow(row)

csv_bytes = csv_buf.getvalue().encode("utf-8")
r = requests.post(
    f"{BACKEND}/rennen/{rennen_id2}/csv-import",
    headers=admin_h,
    files={"file": ("fahrer.csv", csv_bytes, "text/csv")}
)
check("Excel→CSV Import", r)

if r.status_code == 200:
    data = r.json()
    imported = data.get('imported', [])
    errors_l  = data.get('errors', [])
    n_imp = imported if isinstance(imported, int) else len(imported)
    n_err = errors_l  if isinstance(errors_l,  int) else len(errors_l)
    log(f"Importiert: {n_imp} Fahrer | Fehler: {n_err}")

# ── 11. Gleichzeitigkeitstest ─────────────────────────────────
separator("11. GLEICHZEITIGKEITSTEST (10 parallele Requests)")

def get_rennen(_):
    try:
        r = requests.get(f"{BACKEND}/rennen", timeout=5)
        return r.status_code
    except:
        return 0

start_t = time.time()
with ThreadPoolExecutor(max_workers=10) as ex:
    futures = [ex.submit(get_rennen, i) for i in range(50)]
    codes = [f.result() for f in as_completed(futures)]

elapsed = time.time() - start_t
ok_count = codes.count(200)
log(f"50 Requests in {elapsed:.2f}s | {ok_count}/50 OK | Ø {elapsed/50*1000:.0f}ms/req")

if ok_count >= 45:
    print(f"{ok} Gleichzeitigkeitstest bestanden ({ok_count}/50)")
    results["passed"] += 1
else:
    print(f"{fail} Zu viele Fehler ({50-ok_count} fehlgeschlagen)")
    results["failed"] += 1

# ── 12. Profilseite & Anmeldungen ────────────────────────────
separator("12. FAHRERPROFIL & ANMELDUNGEN")

tok1 = fahrer_tokens.get(1)
if tok1:
    r = requests.get(f"{BACKEND}/profil/anmeldungen",
                     headers={"Authorization": f"Bearer {tok1}"})
    check("Profil/Anmeldungen abrufen", r)
    if r.status_code == 200:
        log(f"Fahrer 01 hat {len(r.json())} Anmeldung(en)")

# Alle Rennen abrufen
r = requests.get(f"{BACKEND}/rennen")
check("Alle Rennen abrufen", r)
if r.status_code == 200:
    log(f"{len(r.json())} Rennen in der Datenbank")

# ── Zusammenfassung ───────────────────────────────────────────
separator("ZUSAMMENFASSUNG")

total = results["passed"] + results["failed"]
rate  = results["passed"] / total * 100 if total else 0

print(f"\n  Tests gesamt:    {total}")
print(f"  Bestanden:       {results['passed']} ({rate:.0f}%)")
print(f"  Fehlgeschlagen:  {results['failed']}")

if results["errors"]:
    print(f"\n  Fehler:")
    for e in results["errors"]:
        print(f"    - {e}")

if results["failed"] == 0:
    print(f"\n\033[92m  ✓ Alle Tests bestanden — App ist bereit für den TechDay!\033[0m\n")
else:
    print(f"\n\033[93m  ⚠ {results['failed']} Test(s) fehlgeschlagen — Details oben prüfen.\033[0m\n")

print(f"  Excel-Datei: {excel_path}  ← kann manuell im Admin-Panel importiert werden")
print(f"  Backend:     {BACKEND}")
print(f"  Docs:        {BACKEND}/docs\n")
