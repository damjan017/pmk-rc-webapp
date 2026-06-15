import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import RennStatus from '../components/RennStatus'

function fmtTime(s) {
  if (s == null) return '—'
  return s < 60 ? `${s.toFixed(3)} s` : `${Math.floor(s / 60)}:${(s % 60).toFixed(3).padStart(6, '0')} min`
}

export default function Profil() {
  const { user } = useAuth()
  const [anmeldungen, setAnmeldungen] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getAnmeldungen().then(setAnmeldungen).finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex justify-center items-center min-h-[40vh]">
      <div className="text-gold animate-pulse text-3xl">🏁</div>
    </div>
  )

  const qrUrl = api.getQrCode(user.id)

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-black mb-6">Mein Profil</h1>

      {/* User Card */}
      <div className="card mb-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-gold-dim flex items-center justify-center text-gold font-black text-xl">
            {user.name[0].toUpperCase()}
          </div>
          <div>
            <div className="font-black text-lg">{user.name}</div>
            <div className="text-zinc-400 text-sm">{user.email}</div>
            {user.rolle === 'admin' && (
              <span className="badge-gold mt-1">⚙ Admin</span>
            )}
          </div>
          {anmeldungen.length > 0 && (
            <div className="ml-auto text-right">
              <div className="text-2xl font-black text-gold">{anmeldungen.length}</div>
              <div className="text-zinc-500 text-xs">Rennen</div>
            </div>
          )}
        </div>
      </div>

      {/* QR Code */}
      {anmeldungen.length > 0 && (
        <div className="card mb-6 text-center">
          <h3 className="font-bold mb-1">Check-in QR-Code</h3>
          <p className="text-zinc-400 text-xs mb-4">Beim Rennen vorzeigen</p>
          <img
            src={qrUrl}
            alt="QR-Code"
            className="w-40 h-40 mx-auto bg-white p-2 rounded-xl"
            onError={e => { e.target.style.display = 'none' }}
          />
          <p className="text-zinc-500 text-xs mt-3">Fahrer-ID: #{user.id}</p>
        </div>
      )}

      {/* Meine Rennen */}
      <h2 className="font-bold text-sm uppercase tracking-wide text-zinc-400 mb-3">Meine Rennen</h2>

      {anmeldungen.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-zinc-400 mb-4">Du bist noch bei keinem Rennen angemeldet.</p>
          <Link to="/rennen" className="btn-gold">Rennen ansehen →</Link>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {anmeldungen.map(a => (
            <div key={a.anmeldung_id} className="card">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <div className="font-bold">{a.rennen_name}</div>
                  <div className="text-zinc-400 text-xs mt-0.5">
                    {a.rennen_datum} · {a.fahrzeug}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <RennStatus status={a.rennen_status} />
                  <span className="text-gold font-black">#{a.startnummer}</span>
                  {a.eingecheckt
                    ? <span className="badge-green">✓ Eingecheckt</span>
                    : <span className="badge-gray">Ausstehend</span>}
                </div>
              </div>
              {a.anzahl_laeufe > 0 && (
                <div className="mt-3 flex items-center gap-4 text-xs text-zinc-400 border-t border-surface-3 pt-3">
                  <span>{a.anzahl_laeufe} Lauf{a.anzahl_laeufe !== 1 ? 'e' : ''}</span>
                  <span>⭐ Beste: <strong className="text-gold">{fmtTime(a.beste_zeit)}</strong></span>
                  <Link to={`/leaderboard/${a.rennen_id}`} className="ml-auto text-gold hover:underline">Rangliste →</Link>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
