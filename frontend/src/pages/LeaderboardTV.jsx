import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'

function fmtTime(s) {
  if (s == null) return '—'
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(3)
  return m > 0 ? `${m}:${sec.padStart(6, '0')}` : `${parseFloat(sec).toFixed(3)} s`
}

const MEDALS = ['🥇', '🥈', '🥉']
const PLACE_COLORS = [
  'bg-amber-900/40 border-amber-600/60',
  'bg-zinc-800/60 border-zinc-600/40',
  'bg-orange-900/30 border-orange-700/40',
]

export default function LeaderboardTV() {
  const { id } = useParams()
  const [rennen, setRennen] = useState(null)
  const [board, setBoard] = useState([])
  const [lastUpdate, setLastUpdate] = useState(new Date())
  const [rennenList, setRennenList] = useState([])
  const [rennenId, setRennenId] = useState(id || '')
  const intervalRef = useRef(null)

  useEffect(() => {
    api.getRennen().then(list => {
      setRennenList(list)
      if (!id && list.length > 0) {
        const laufend = list.find(r => r.status === 'laufend') || list[0]
        setRennenId(String(laufend.id))
      }
    })
  }, [])

  useEffect(() => {
    if (!rennenId) return
    load()
    if (intervalRef.current) clearInterval(intervalRef.current)
    intervalRef.current = setInterval(load, 5000)
    return () => clearInterval(intervalRef.current)
  }, [rennenId])

  async function load() {
    if (!rennenId) return
    try {
      const [r, b] = await Promise.all([
        api.getRennenById(rennenId),
        api.getLeaderboard(rennenId),
      ])
      setRennen(r)
      setBoard(b)
      setLastUpdate(new Date())
    } catch {}
  }

  return (
    <div className="min-h-screen bg-bg flex flex-col" style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      {/* Header */}
      <div className="flex items-center justify-between px-8 py-5 border-b border-surface-3">
        <div className="flex items-center gap-4">
          <span className="text-4xl">🏁</span>
          <div>
            <div className="text-xl font-black text-zinc-100">
              PMK RC-Car <span className="text-gold">Rally</span>
            </div>
            {rennen && (
              <div className="text-sm text-zinc-400 font-semibold">{rennen.name}</div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* Race selector */}
          {rennenList.length > 1 && (
            <select
              className="bg-surface border border-surface-3 text-zinc-100 text-sm px-3 py-1.5 rounded-lg outline-none"
              value={rennenId}
              onChange={e => setRennenId(e.target.value)}
            >
              {rennenList.map(r => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          )}

          <div className="text-right">
            <div className="flex items-center gap-2 text-xs text-zinc-400">
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              LIVE · {lastUpdate.toLocaleTimeString('de-DE')}
            </div>
            <div className="text-xs text-zinc-600 mt-0.5">aktualisiert alle 5s</div>
          </div>

          <Link to="/leaderboard" className="text-zinc-500 hover:text-zinc-300 text-xs border border-surface-3 px-3 py-1.5 rounded-lg transition-colors">
            ← Normal
          </Link>
        </div>
      </div>

      {/* Board */}
      <div className="flex-1 px-8 py-6">
        {board.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-8xl mb-6 animate-pulse">🏎️</div>
            <p className="text-zinc-500 text-2xl font-bold">Noch keine Zeiten</p>
            <p className="text-zinc-600 text-base mt-2">Warte auf Ergebnisse…</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3 max-w-4xl mx-auto">
            {/* Top 3 — groß */}
            {board.slice(0, 3).map((f, i) => f.beste_gesamtzeit != null && (
              <div
                key={f.id}
                className={`flex items-center gap-6 px-8 py-5 rounded-2xl border ${PLACE_COLORS[i] || 'bg-surface border-surface-3'} animate-fade-in`}
              >
                <div className="text-5xl w-14 text-center shrink-0">{MEDALS[i]}</div>
                <div className="w-16 text-center shrink-0">
                  <div className="text-3xl font-black text-gold">#{f.startnummer}</div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-2xl font-black truncate">{f.name}</div>
                  <div className="text-zinc-400 text-base">{f.fahrzeug}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className={`font-black font-mono text-4xl ${i === 0 ? 'text-gold' : 'text-zinc-100'}`}>
                    {fmtTime(f.beste_gesamtzeit)}
                  </div>
                  <div className="text-zinc-500 text-sm mt-1">
                    {f.anzahl_laeufe} Lauf{f.anzahl_laeufe !== 1 ? 'e' : ''}
                    {f.gesamt_strafzeit > 0 && (
                      <span className="text-red-400 ml-2">+{f.gesamt_strafzeit}s</span>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {/* Rest — kompakter */}
            {board.slice(3).map((f, i) => (
              <div
                key={f.id}
                className="flex items-center gap-4 px-6 py-3.5 rounded-xl bg-surface border border-surface-3 animate-fade-in"
              >
                <div className="w-10 text-center text-xl font-black text-zinc-500 shrink-0">{i + 4}.</div>
                <div className="w-12 text-center shrink-0">
                  <span className="text-gold font-black text-lg">#{f.startnummer}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-lg font-bold truncate">{f.name}</div>
                  <div className="text-zinc-500 text-sm">{f.fahrzeug}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className="font-black font-mono text-xl text-zinc-100">
                    {f.beste_gesamtzeit != null ? fmtTime(f.beste_gesamtzeit) : '—'}
                  </div>
                  {f.gesamt_strafzeit > 0 && (
                    <div className="text-red-400 text-xs">+{f.gesamt_strafzeit}s Strafzeit</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-8 py-3 border-t border-surface-3 flex items-center justify-between">
        <div className="text-zinc-600 text-xs">Hochschule Pforzheim · Fakultät für Technik · PMK RC-Car Rally</div>
        <div className="text-zinc-600 text-xs">{board.length} Fahrer · {board.filter(f => f.beste_gesamtzeit != null).length} mit Zeit</div>
      </div>
    </div>
  )
}
