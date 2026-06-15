import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'
import RennStatus from '../components/RennStatus'

function fmtTime(s) {
  if (s == null) return '—'
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(3)
  return m > 0 ? `${m}:${sec.padStart(6, '0')} min` : `${parseFloat(sec).toFixed(3)} s`
}

export default function Leaderboard() {
  const { id } = useParams()
  const [rennenList, setRennenList] = useState([])
  const [rennenId, setRennenId] = useState(id || '')
  const [rennen, setRennen] = useState(null)
  const [board, setBoard] = useState([])
  const [countdown, setCountdown] = useState(10)
  const countRef = useRef(null)

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
    if (countRef.current) clearInterval(countRef.current)
    setCountdown(10)
    countRef.current = setInterval(() => {
      setCountdown(c => {
        if (c <= 1) { load(); return 10 }
        return c - 1
      })
    }, 1000)
    return () => clearInterval(countRef.current)
  }, [rennenId])

  async function load() {
    if (!rennenId) return
    try {
      const [r, b] = await Promise.all([api.getRennenById(rennenId), api.getLeaderboard(rennenId)])
      setRennen(r); setBoard(b)
    } catch {}
  }

  const medals = ['🥇', '🥈', '🥉']

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-6 flex-wrap">
        <div>
          <h1 className="text-2xl font-black flex items-center gap-2">
            📊 Live-Rangliste
          </h1>
          {rennen && (
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <RennStatus status={rennen.status} />
              <span className="text-zinc-500 text-xs">{rennen.datum} · {rennen.ort}</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5 text-xs text-zinc-500">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Live · aktualisiert in <span className="text-gold font-bold tabular-nums">{countdown}s</span>
          </div>
          <button onClick={load} className="btn-outline text-xs px-3 py-1.5">↺ Jetzt</button>
        </div>
      </div>

      {/* Race selector */}
      {rennenList.length > 1 && (
        <div className="card mb-5 flex items-center gap-3">
          <span className="text-xs font-bold text-zinc-400 uppercase tracking-wide whitespace-nowrap">Rennen:</span>
          <select className="select" value={rennenId} onChange={e => setRennenId(e.target.value)}>
            {rennenList.map(r => (
              <option key={r.id} value={r.id}>{r.name} ({r.datum})</option>
            ))}
          </select>
        </div>
      )}

      {/* Board */}
      {board.length === 0 ? (
        <div className="card text-center py-16">
          <div className="text-4xl mb-4">🏎️</div>
          <p className="text-zinc-400 text-sm">Noch keine Zeiten eingetragen.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {board.map((f, i) => {
            const hasTime = f.beste_gesamtzeit != null
            return (
              <div
                key={f.id}
                className={`card flex items-center gap-4 transition-all animate-fade-in
                  ${i === 0 && hasTime ? 'border-amber-600/50 bg-amber-900/10' : ''}
                  ${i === 1 && hasTime ? 'border-zinc-500/50' : ''}
                  ${i === 2 && hasTime ? 'border-amber-800/50' : ''}`}
              >
                {/* Platz */}
                <div className="w-10 text-center shrink-0">
                  {hasTime
                    ? i < 3
                      ? <span className="text-2xl">{medals[i]}</span>
                      : <span className="text-lg font-black text-zinc-400">{i + 1}.</span>
                    : <span className="text-zinc-600 text-sm font-bold">—</span>}
                </div>

                {/* Startnummer */}
                <div className="w-8 text-center shrink-0">
                  <span className="text-gold font-black text-sm">#{f.startnummer}</span>
                </div>

                {/* Name & Fahrzeug */}
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-sm truncate">{f.name}</div>
                  <div className="text-zinc-500 text-xs">{f.fahrzeug}</div>
                </div>

                {/* Stats */}
                <div className="text-right shrink-0">
                  <div className={`font-black font-mono text-sm ${i === 0 && hasTime ? 'text-gold' : 'text-zinc-100'}`}>
                    {fmtTime(f.beste_gesamtzeit)}
                  </div>
                  <div className="text-zinc-500 text-xs">
                    {f.anzahl_laeufe} Lauf{f.anzahl_laeufe !== 1 ? 'e' : ''}
                    {f.gesamt_strafzeit > 0 && <span className="text-red-400 ml-1">+{f.gesamt_strafzeit}s Str.</span>}
                  </div>
                </div>

                {/* Check-in */}
                {!f.eingecheckt && (
                  <div className="shrink-0">
                    <span className="text-xs text-zinc-600">nicht eingecheckt</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* PDF Link */}
      {rennenId && (
        <div className="mt-6 text-center">
          <a
            href={api.ergebnissePdf(rennenId)}
            target="_blank"
            rel="noreferrer"
            className="btn-outline text-xs px-4 py-2"
          >
            🖨️ Ergebnisse als PDF
          </a>
        </div>
      )}
    </div>
  )
}
