import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import RennStatus from '../components/RennStatus'

export default function Rennen() {
  const [rennen, setRennen] = useState([])
  const [loading, setLoading] = useState(true)
  const { user } = useAuth()

  useEffect(() => {
    api.getRennen().then(setRennen).finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex justify-center items-center min-h-[40vh]">
      <div className="text-gold animate-pulse text-3xl">🏁</div>
    </div>
  )

  return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-black">Rennen</h1>
          <p className="text-zinc-400 text-sm mt-1">Alle geplanten RC-Car Rally Events</p>
        </div>
        {!user && (
          <Link to="/register" className="btn-gold">Registrieren</Link>
        )}
      </div>

      {rennen.length === 0 ? (
        <div className="card text-center py-16">
          <div className="text-4xl mb-4">🏎️</div>
          <p className="text-zinc-400">Noch keine Rennen geplant.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {rennen.map(r => (
            <RennCard key={r.id} rennen={r} />
          ))}
        </div>
      )}
    </div>
  )
}

function RennCard({ rennen: r }) {
  const { user } = useAuth()
  const belegt = r.max_teilnehmer ? Math.round((r.teilnehmer_count / r.max_teilnehmer) * 100) : 0
  const voll = r.max_teilnehmer && r.teilnehmer_count >= r.max_teilnehmer

  return (
    <div className="card hover:border-zinc-600 transition-colors animate-fade-in">
      <div className="flex flex-col md:flex-row md:items-start gap-4">
        <div className="flex-1">
          <div className="flex items-start gap-3 mb-3 flex-wrap">
            <h2 className="font-black text-lg">{r.name}</h2>
            <RennStatus status={r.status} />
            {voll && r.status === 'offen' && (
              <span className="badge-red">Voll</span>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm mb-3">
            <div className="flex items-center gap-1.5 text-zinc-400">
              <span>📅</span>
              <span>{r.datum} {r.uhrzeit && `· ${r.uhrzeit} Uhr`}</span>
            </div>
            <div className="flex items-center gap-1.5 text-zinc-400">
              <span>📍</span>
              {r.ort_link
                ? <a href={r.ort_link} target="_blank" rel="noreferrer" className="hover:text-gold transition-colors">{r.ort}</a>
                : <span>{r.ort}</span>
              }
            </div>
            <div className="flex items-center gap-1.5 text-zinc-400">
              <span>👥</span>
              <span>{r.teilnehmer_count} / {r.max_teilnehmer || '∞'} Fahrer</span>
            </div>
          </div>

          {/* Fahrzeugvorgaben */}
          {(r.fahrzeug_klasse || r.reifen_vorgabe || r.max_breite_mm) && (
            <div className="flex flex-wrap gap-2 mb-3">
              {r.fahrzeug_klasse && <span className="badge-gray text-xs">🏎️ {r.fahrzeug_klasse}</span>}
              {r.reifen_vorgabe && <span className="badge-gray text-xs">🔘 {r.reifen_vorgabe}</span>}
              {r.max_breite_mm && <span className="badge-gray text-xs">📐 max. {r.max_breite_mm}mm</span>}
            </div>
          )}

          {r.beschreibung && (
            <p className="text-zinc-400 text-sm leading-relaxed line-clamp-2">{r.beschreibung}</p>
          )}

          {/* Kapazitätsbalken */}
          {r.max_teilnehmer && r.status === 'offen' && (
            <div className="mt-3">
              <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${belegt >= 90 ? 'bg-red-500' : belegt >= 70 ? 'bg-amber-500' : 'bg-green-500'}`}
                  style={{ width: `${Math.min(belegt, 100)}%` }}
                />
              </div>
              <div className="text-xs text-zinc-500 mt-1">{belegt}% belegt</div>
            </div>
          )}
        </div>

        <div className="flex flex-row md:flex-col gap-2 shrink-0">
          <Link to={`/leaderboard/${r.id}`} className="btn-outline text-xs">
            📊 Rangliste
          </Link>
          {user && r.status === 'offen' && !voll && (
            <Link to={`/rennen/${r.id}/anmelden`} className="btn-gold text-xs">
              Anmelden →
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}
