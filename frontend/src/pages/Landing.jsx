import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Landing() {
  const { user } = useAuth()

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-amber-900/20 via-transparent to-transparent pointer-events-none" />
        <div className="max-w-5xl mx-auto px-6 pt-20 pb-24 text-center">
          <div className="inline-flex items-center gap-2 bg-amber-900/30 border border-amber-700/50 text-gold text-xs font-bold px-3 py-1.5 rounded-full mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-gold animate-pulse" />
            Hobby RC-Car Rally Management
          </div>
          <h1 className="text-5xl md:text-6xl font-black tracking-tight mb-6 leading-tight">
            RC-Car Rally<br />
            <span className="text-gold">digital verwalten</span>
          </h1>
          <p className="text-lg text-zinc-400 max-w-xl mx-auto mb-10 leading-relaxed">
            Von der Anmeldung bis zur Siegerehrung — vollständig digital.
            Kein Papierkram, Live-Rangliste, automatische Zeiterfassung.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {user ? (
              <>
                <Link to="/rennen" className="btn-gold text-base px-8 py-3">Zu den Rennen →</Link>
                <Link to="/profil" className="btn-outline text-base px-8 py-3">Mein Profil</Link>
              </>
            ) : (
              <>
                <Link to="/register" className="btn-gold text-base px-8 py-3">Jetzt registrieren</Link>
                <Link to="/rennen" className="btn-outline text-base px-8 py-3">Rennen ansehen</Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 pb-20">
        <div className="grid md:grid-cols-3 gap-4">
          {[
            { icon: '📋', title: 'Online-Anmeldung', desc: 'Fahrer registrieren sich online, erhalten QR-Code per E-Mail und checken vor Ort ein.' },
            { icon: '⏱️', title: 'Live-Zeiterfassung', desc: 'KI-Kamera-Simulator erfasst Zeiten an 6 Toren. Leaderboard aktualisiert sich in Echtzeit.' },
            { icon: '🏆', title: 'Automatische Rangliste', desc: 'Bestzeiten + Strafzeiten werden automatisch berechnet. PDF-Export für die Siegerehrung.' },
            { icon: '⚠️', title: 'Strafzeiten-System', desc: '10 vordefinierte Vergehen mit automatischer Zeitaddition. Manuell vom Rennleiter eingetragen.' },
            { icon: '🔒', title: 'DSGVO-konform', desc: 'Aktive Einwilligung, nur notwendige Daten, EU-Server, Löschung nach dem Event.' },
            { icon: '📦', title: 'Self-Hosted', desc: 'Einmal herunterladen, Docker starten — fertig. Kein Cloud-Abo, keine laufenden Kosten.' },
          ].map(f => (
            <div key={f.title} className="card hover:border-zinc-600 transition-colors">
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="font-bold text-sm mb-2">{f.title}</h3>
              <p className="text-zinc-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Flow */}
      <section className="border-t border-surface-3 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-center mb-10">Ablauf eines Rally-Events</h2>
          <div className="flex flex-col md:flex-row items-start gap-6 md:gap-0">
            {[
              { n: '1', title: 'Online-Registrierung', desc: 'Fahrer meldet sich an, stimmt DSGVO zu' },
              { n: '2', title: 'Aufbau & Check-in', desc: 'QR-Code scannen, Startnummer erhalten' },
              { n: '3', title: 'Renndurchführung', desc: 'Einzelstart, KI-Kamera misst Zeiten' },
              { n: '4', title: 'Siegerehrung', desc: 'PDF-Export, Ergebnis-Mail an alle' },
            ].map((s, i) => (
              <div key={s.n} className="flex md:flex-col items-start md:items-center md:flex-1 gap-4">
                <div className="w-10 h-10 rounded-full bg-gold flex items-center justify-center font-black text-bg text-sm shrink-0">
                  {s.n}
                </div>
                <div className="md:text-center">
                  <div className="font-bold text-sm mb-1">{s.title}</div>
                  <div className="text-zinc-400 text-xs leading-relaxed">{s.desc}</div>
                </div>
                {i < 3 && (
                  <div className="hidden md:block h-px bg-surface-3 flex-1 mt-5" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-surface-3 py-8">
        <div className="max-w-5xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="text-zinc-500 text-sm">
            PMK RC-Car Rally · Hochschule Pforzheim · Fakultät für Technik
          </div>
          <div className="flex items-center gap-4 text-sm">
            <Link to="/faq" className="text-zinc-500 hover:text-gold transition-colors">FAQ</Link>
            <Link to="/impressum" className="text-zinc-500 hover:text-gold transition-colors">Impressum</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
