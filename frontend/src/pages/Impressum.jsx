export default function Impressum() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-black mb-2">Impressum & Datenschutz</h1>
      <p className="text-zinc-400 text-sm mb-8">Rechtliche Informationen</p>

      <div className="flex flex-col gap-5">
        <div className="card">
          <h2 className="font-bold mb-3">Angaben gemäß § 5 TMG</h2>
          <div className="text-zinc-400 text-sm space-y-1">
            <p>Hochschule Pforzheim — Fakultät für Technik</p>
            <p>PMK-Projektgruppe RC-Car Rally</p>
            <p>Tiefenbronner Str. 65, 75175 Pforzheim</p>
          </div>
        </div>

        <div className="card">
          <h2 className="font-bold mb-3">Projektverantwortliche</h2>
          <div className="text-zinc-400 text-sm space-y-0.5">
            <p>Damjan Besarovic (Teamleitung)</p>
            <p>David Dumke · Daniel Richter</p>
            <p>Dino Telalovic · Philip Graff</p>
          </div>
        </div>

        <div className="card">
          <h2 className="font-bold mb-3">Datenschutzerklärung (DSGVO)</h2>
          <div className="text-zinc-400 text-sm space-y-3 leading-relaxed">
            <div>
              <strong className="text-zinc-200">Erhobene Daten</strong>
              <p className="mt-1">Wir erheben ausschließlich die für die Durchführung der RC-Car Rally notwendigen Daten: Name, E-Mail-Adresse, Fahrzeugbezeichnung und Rundenzeiten.</p>
            </div>
            <div>
              <strong className="text-zinc-200">Einwilligung</strong>
              <p className="mt-1">Die Verarbeitung erfolgt nur nach aktiver Einwilligung bei der Anmeldung (Art. 6 Abs. 1 lit. a DSGVO).</p>
            </div>
            <div>
              <strong className="text-zinc-200">Speicherung & Löschung</strong>
              <p className="mt-1">Alle personenbezogenen Daten werden spätestens 30 Tage nach Abschluss des Events gelöscht. Du kannst jederzeit die Löschung deiner Daten per E-Mail beantragen.</p>
            </div>
            <div>
              <strong className="text-zinc-200">Kameraüberwachung</strong>
              <p className="mt-1">Auf dem Veranstaltungsgelände wird eine KI-Kamera zur automatischen Zeiterfassung eingesetzt. Diese erkennt ausschließlich die Fahrzeuge, nicht die Personen. Entsprechende Hinweisschilder sind vor Ort sichtbar.</p>
            </div>
            <div>
              <strong className="text-zinc-200">Passwörter</strong>
              <p className="mt-1">Passwörter werden ausschließlich als kryptografischer Hash (SHA-256) gespeichert und können nicht rückgewonnen werden.</p>
            </div>
            <div>
              <strong className="text-zinc-200">Deine Rechte</strong>
              <p className="mt-1">Du hast das Recht auf Auskunft, Berichtigung, Löschung und Einschränkung der Verarbeitung deiner Daten gemäß DSGVO Art. 15–21.</p>
            </div>
            <div>
              <strong className="text-zinc-200">Hosting</strong>
              <p className="mt-1">Diese Software wird lokal auf einem Server des Veranstalters betrieben. Alle Daten verbleiben in Europa.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
