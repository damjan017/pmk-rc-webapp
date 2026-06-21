"""Schnelltest ab Schritt 10 — läuft ohne vorherige Schritte."""
import requests, random, csv, io, sys
import openpyxl

BACKEND     = "http://localhost:8000"
ADMIN_EMAIL = "admin@pmk.de"
ADMIN_PW    = "Admin2026!"
FARBEN      = ["Rot","Blau","Grün","Gelb","Schwarz","Weiß","Orange","Lila"]
MODELLE     = ["Traxxas Slash","Losi DBXL","Arrma Kraton","HPI Savage","Tamiya TT-02"]

ok   = "\033[92m OK\033[0m"
fail = "\033[91m FAIL\033[0m"
info = "\033[94m INFO\033[0m"

# Admin login
r = requests.post(f"{BACKEND}/auth/login", json={"email": ADMIN_EMAIL, "passwort": ADMIN_PW})
if r.status_code != 200:
    print(f"{fail} Admin Login fehlgeschlagen"); sys.exit(1)
admin_h = {"Authorization": f"Bearer {r.json()['token']}"}
print(f"{ok} Admin eingeloggt")

# Erstes offenes Rennen holen oder neues erstellen
rennen = requests.get(f"{BACKEND}/rennen").json()
offene = [x for x in rennen if x.get("status") == "offen"]
if offene:
    rennen_id = offene[0]["id"]
    print(f"{info} Verwende Rennen ID {rennen_id}: {offene[0]['name']}")
else:
    r2 = requests.post(f"{BACKEND}/rennen", headers=admin_h, json={
        "name": "Import-Testrennen", "datum": "2026-06-22", "uhrzeit": "14:00",
        "ort": "Teststrecke", "ort_link": "", "max_teilnehmer": 50, "beschreibung": ""
    })
    rennen_id = r2.json()["id"]
    print(f"{ok} Neues Rennen erstellt (ID {rennen_id})")

# ── 10. Excel → CSV Import ────────────────────────────────────
print(f"\n{'═'*50}\n  10. EXCEL-GENERIERUNG & CSV-IMPORT\n{'═'*50}")

wb = openpyxl.Workbook()
ws = wb.active
ws.append(["name", "email", "fahrzeug"])
excel_fahrer = []
for i in range(51, 71):
    row = (f"Excel-Fahrer {i}", f"excel{i}@import.rally",
           f"{random.choice(FARBEN)} {random.choice(MODELLE)}")
    ws.append(list(row))
    excel_fahrer.append(row)

excel_path = "belastungstest_fahrer.xlsx"
wb.save(excel_path)
print(f"{info} Excel erstellt: {excel_path} ({len(excel_fahrer)} Fahrer)")

csv_buf = io.StringIO()
writer = csv.writer(csv_buf)
writer.writerow(["name", "email", "fahrzeug"])
for row in excel_fahrer:
    writer.writerow(row)

r = requests.post(
    f"{BACKEND}/rennen/{rennen_id}/csv-import",
    headers=admin_h,
    files={"file": ("fahrer.csv", csv_buf.getvalue().encode("utf-8"), "text/csv")}
)
if r.status_code == 200:
    data  = r.json()
    imp   = data.get("imported", [])
    errs  = data.get("errors",   [])
    n_imp = imp  if isinstance(imp,  int) else len(imp)
    n_err = errs if isinstance(errs, int) else len(errs)
    print(f"{ok} Excel→CSV Import [200] — {n_imp} importiert | {n_err} Fehler")
else:
    print(f"{fail} Import [{r.status_code}] → {r.text[:120]}")

# ── 11. Gleichzeitigkeitstest ─────────────────────────────────
print(f"\n{'═'*50}\n  11. GLEICHZEITIGKEITSTEST (50 parallele Requests)\n{'═'*50}")
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_rennen(_):
    try: return requests.get(f"{BACKEND}/rennen", timeout=5).status_code
    except: return 0

start_t = time.time()
with ThreadPoolExecutor(max_workers=10) as ex:
    codes = [f.result() for f in as_completed([ex.submit(get_rennen, i) for i in range(50)])]
elapsed  = time.time() - start_t
ok_count = codes.count(200)
print(f"{info} 50 Requests in {elapsed:.2f}s | {ok_count}/50 OK | Ø {elapsed/50*1000:.0f}ms/req")
print(f"{ok if ok_count >= 45 else fail} Gleichzeitigkeitstest ({'bestanden' if ok_count >= 45 else 'fehlgeschlagen'})")

# ── 12. Profil ────────────────────────────────────────────────
print(f"\n{'═'*50}\n  12. LEADERBOARD & RENNEN-LISTE\n{'═'*50}")
r = requests.get(f"{BACKEND}/rennen/{rennen_id}/leaderboard")
print(f"{ok if r.status_code==200 else fail} Leaderboard [{r.status_code}]")
if r.status_code == 200 and r.json():
    t = r.json()[0]
    print(f"{info} Platz 1: {t.get('name','?')} | Gesamt: {t.get('gesamtzeit','?')}s")

r = requests.get(f"{BACKEND}/rennen")
print(f"{ok if r.status_code==200 else fail} Alle Rennen [{r.status_code}] — {len(r.json())} Einträge")

print(f"\n\033[92m Fertig! Excel-Datei: {excel_path}\033[0m\n")
