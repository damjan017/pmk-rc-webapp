const FAQS = [
  {
    frage: 'Wie melde ich mich für ein Rennen an?',
    antwort: 'Registriere dich zuerst mit E-Mail und Passwort. Danach findest du unter "Rennen" alle verfügbaren Events und kannst dich mit einem Klick anmelden. Du erhältst eine Bestätigungs-E-Mail mit deinem QR-Code.',
  },
  {
    frage: 'Was mache ich mit dem QR-Code?',
    antwort: 'Dein QR-Code ist dein digitales Ticket. Beim Check-in vor Ort scannst du ihn und wirst automatisch als eingecheckt markiert. Du bekommst ihn per E-Mail und findest ihn jederzeit in deinem Profil.',
  },
  {
    frage: 'Wie wird die Zeit gemessen?',
    antwort: 'Entlang der Strecke sind 6 Tore aufgestellt. Beim Passieren jedes Tors wird ein Zeitstempel erfasst. Die Gesamtzeit ist die Zeit zwischen Tor 1 (Start) und Tor 6 (Ziel). Du kannst mehrere Läufe absolvieren — die beste Zeit zählt.',
  },
  {
    frage: 'Wie funktionieren Strafzeiten?',
    antwort: 'Strafzeiten werden vom Rennleiter manuell eingetragen, wenn ein Regelverstoß beobachtet wird (z.B. Tor berührt, Frühstart). Sie werden zu deiner besten Rundenzeit addiert. Die Gesamtzeit entscheidet über die Platzierung.',
  },
  {
    frage: 'Was passiert, wenn ich ein Tor auslasse?',
    antwort: 'Ein ausgelassenes technisches Element wird mit +30 Sekunden bestraft. Alle Tore müssen korrekt durchfahren werden.',
  },
  {
    frage: 'Kann ich mich wieder abmelden?',
    antwort: 'Ja, du kannst dich bis zum Start des Rennens abmelden. Sobald das Rennen gestartet ist, ist keine Abmeldung mehr möglich.',
  },
  {
    frage: 'Welche Strafzeiten gibt es?',
    antwort: 'Tor berührt/verschoben: +15s · Frühstart bis 5 Sek: +10s · Frühstart mehr als 5 Sek: +20s · Unerlaubter Service: +10s bis +60s · Auto mit Fuß bewegt: +30s · Falsches Zurücksetzen: +10s · Unsportliches Verhalten: +30s · Element ausgelassen: +30s · Zu spät zum Start: +60s',
  },
  {
    frage: 'Was sind die Fahrzeugvoraussetzungen?',
    antwort: 'Die genauen Vorgaben (Klasse, Reifentyp, max. Breite) werden pro Rennen vom Administrator festgelegt und auf der Rennen-Detailseite angezeigt. Dein Fahrzeug muss beim Check-in fahrbereit sein.',
  },
  {
    frage: 'Wie werden meine Daten gespeichert?',
    antwort: 'Wir speichern nur die für die Durchführung notwendigen Daten (Name, E-Mail, Fahrzeug). Alle Daten werden nach dem Event gelöscht. Dein Passwort wird sicher gehasht gespeichert — wir sehen es nie im Klartext.',
  },
  {
    frage: 'Was brauche ich vor Ort mit?',
    antwort: 'Dein Fahrzeug (fahrbereit), mindestens 2 vollgeladene Akkus, Ladegerät, Fernsteuerung und Sender. Erscheine mindestens 30 Minuten vor dem Start. Das Fahrermeeting findet 15 Minuten vor dem Start statt — Anwesenheit ist Pflicht.',
  },
]

export default function FAQ() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-black mb-2">Häufige Fragen</h1>
      <p className="text-zinc-400 text-sm mb-8">Alles was du über die RC-Car Rally wissen musst.</p>

      <div className="flex flex-col gap-3">
        {FAQS.map((f, i) => (
          <details key={i} className="card group cursor-pointer">
            <summary className="flex items-center justify-between font-semibold text-sm list-none cursor-pointer">
              {f.frage}
              <span className="text-gold ml-2 shrink-0">+</span>
            </summary>
            <div className="text-zinc-400 text-sm leading-relaxed mt-3 pt-3 border-t border-surface-3">
              {f.antwort}
            </div>
          </details>
        ))}
      </div>
    </div>
  )
}
