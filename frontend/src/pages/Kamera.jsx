import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'

export default function Kamera() {
  const { id: rennenId } = useParams()
  const [rennen, setRennen]     = useState(null)
  const [teilnehmer, setTeilnehmer] = useState([])
  const [fahrerId, setFahrerId] = useState('')
  const [anzahlTore, setAnzahlTore] = useState(6)
  const [naechstesTor, setNaechstesTor] = useState(1)
  const [laufId, setLaufId]     = useState(null)
  const [timer, setTimer]       = useState('00.000')
  const [running, setRunning]   = useState(false)
  const [zeiten, setZeiten]     = useState([])
  const [log, setLog]           = useState([])
  const [zwischenzeiten, setZwischenzeiten] = useState([])
  const [status, setStatus]     = useState({ msg: 'Fahrer wählen, dann Tor 1 drücken', type: 'idle' })
  const timerRef = useRef(null)
  const startRef = useRef(null)

  useEffect(() => {
    Promise.all([
      api.getRennenById(rennenId),
      api.getTeilnehmer(rennenId),
      api.kameraConfig(),
    ]).then(([r, t, cfg]) => {
      setRennen(r); setTeilnehmer(t); setAnzahlTore(cfg.anzahl_tore)
    })
  }, [rennenId])

  function addLog(msg, type = 'info') {
    const ts = new Date().toTimeString().slice(0, 8)
    setLog(p => [{ ts, msg, type }, ...p].slice(0, 50))
  }

  function startTimer() {
    startRef.current = Date.now()
    setRunning(true)
    timerRef.current = setInterval(() => {
      const elapsed = (Date.now() - startRef.current) / 1000
      setTimer(elapsed.toFixed(3).padStart(6, '0'))
    }, 50)
  }

  function stopTimer(val) {
    clearInterval(timerRef.current)
    setRunning(false)
    if (val !== undefined) setTimer(val.toFixed(3).padStart(6, '0'))
  }

  function resetState() {
    stopTimer()
    setNaechstesTor(1)
    setLaufId(null)
    setZwischenzeiten([])
    setTimer('00.000')
    setStatus({ msg: 'Bereit', type: 'idle' })
  }

  async function handleTor(torNr) {
    if (!fahrerId) return
    try {
      const data = await api.torSignal({
        fahrer_id: Number(fahrerId), rennen_id: Number(rennenId),
        tor_nr: torNr, zeitstempel: Date.now() / 1000,
      })

      if (data.status === 'start') {
        startTimer()
        setNaechstesTor(2)
        setLaufId(data.lauf_id)
        setZwischenzeiten([])
        setStatus({ msg: `🚦 START! Lauf ${data.lauf_id}`, type: 'start' })
        addLog(`START Lauf ${data.lauf_id}`, 'ok')
      } else if (data.status === 'zwischen') {
        setZwischenzeiten(p => [...p, { tor: torNr, zeit: data.zwischenzeit }])
        setNaechstesTor(data.naechstes_tor)
        setStatus({ msg: `Tor ${torNr} — ${data.zwischenzeit.toFixed(3)}s`, type: 'zwischen' })
        addLog(`Tor ${torNr}: ${data.zwischenzeit.toFixed(3)}s`, 'info')
      } else if (data.status === 'ziel') {
        stopTimer(data.gesamtzeit)
        setStatus({ msg: `🏁 ZIEL! ${data.gesamtzeit.toFixed(3)}s`, type: 'ziel' })
        addLog(`ZIEL! ${data.gesamtzeit.toFixed(3)}s`, 'ok')
        setZeiten(p => [data.gesamtzeit, ...p])
        setTimeout(() => resetState(), 5000)
      }
    } catch (err) {
      setStatus({ msg: `✗ ${err.message}`, type: 'error' })
      addLog(err.message, 'err')
    }
  }

  async function handleReset() {
    if (!fahrerId || !laufId) return
    if (!confirm('Lauf abbrechen?')) return
    try {
      await api.laufReset(fahrerId, rennenId)
      resetState()
      addLog('Lauf abgebrochen', 'err')
    } catch {}
  }

  async function loadZeiten() {
    try {
      const lb = await api.getLeaderboard(rennenId)
      const f = lb.find(x => x.id === Number(fahrerId))
      if (f) setZeiten(f.alle_zeiten || [])
    } catch {}
  }

  function onFahrerChange(e) {
    setFahrerId(e.target.value)
    resetState()
    if (e.target.value) {
      api.getLeaderboard(rennenId).then(lb => {
        const f = lb.find(x => x.id === Number(e.target.value))
        if (f) setZeiten(f.alle_zeiten || [])
      }).catch(() => {})
    }
  }

  const statusColors = {
    idle:     'bg-surface-2 text-zinc-400',
    start:    'bg-green-900/40 text-green-300 border border-green-800',
    zwischen: 'bg-amber-900/30 text-gold border border-amber-800',
    ziel:     'bg-green-900/40 text-green-300 border border-green-800',
    error:    'bg-red-900/40 text-red-300 border border-red-800',
  }

  const bestZeit = zeiten.length ? Math.min(...zeiten) : null

  return (
    <div className="max-w-xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-black text-lg flex items-center gap-2">
            <span className="text-red-500 animate-pulse">●</span> KI-Kamera Simulator
          </h1>
          {rennen && <p className="text-zinc-400 text-xs">{rennen.name} · {anzahlTore} Tore</p>}
        </div>
        <Link to="/admin" className="btn-outline text-xs">← Admin</Link>
      </div>

      {/* Fahrer */}
      <div className="card mb-4">
        <label className="label">🏎️ Aktiver Fahrer</label>
        <select className="select" value={fahrerId} onChange={onFahrerChange}>
          <option value="">— Fahrer wählen —</option>
          {teilnehmer.map(f => (
            <option key={f.id} value={f.id}>#{f.startnummer} {f.name} ({f.fahrzeug})</option>
          ))}
        </select>
      </div>

      {/* Timer */}
      <div className="card mb-4 text-center">
        <div className={`text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wide`}>
          {running ? '⏱ Läuft…' : naechstesTor === 1 ? 'Tor 1 drücken zum Start' : 'Fertig'}
        </div>
        <div className={`text-5xl font-black font-mono mb-2 transition-colors ${running ? 'text-gold' : 'text-zinc-100'}`}>
          {timer}
        </div>
        {zwischenzeiten.length > 0 && (
          <div className="flex flex-wrap gap-2 justify-center mt-2">
            {zwischenzeiten.map(z => (
              <span key={z.tor} className="text-xs bg-surface-2 px-2 py-1 rounded text-gold">
                Tor {z.tor}: {z.zeit.toFixed(3)}s
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Status */}
      <div className={`px-4 py-3 rounded-xl text-sm font-semibold mb-4 ${statusColors[status.type] || statusColors.idle}`}>
        {status.msg}
      </div>

      {/* Tor Buttons */}
      <div className="card mb-4">
        <div className="grid grid-cols-3 gap-2 mb-3">
          {Array.from({ length: anzahlTore }, (_, i) => i + 1).map(tor => {
            const isNext    = tor === naechstesTor
            const isPassed  = tor < naechstesTor && naechstesTor > 1
            const isZiel    = tor === anzahlTore
            const disabled  = !fahrerId || tor !== naechstesTor

            return (
              <button
                key={tor}
                onClick={() => handleTor(tor)}
                disabled={disabled}
                className={`py-4 rounded-xl font-bold text-sm transition-all border
                  ${disabled && !isPassed ? 'opacity-30 cursor-not-allowed border-surface-3 text-zinc-600' :
                    isPassed ? 'border-green-800 bg-green-900/20 text-green-400' :
                    isNext && isZiel ? 'border-red-600 bg-red-900/40 text-red-300 shadow-lg shadow-red-900/20 scale-105 cursor-pointer' :
                    isNext ? 'border-gold bg-amber-900/30 text-gold shadow-lg shadow-amber-900/20 scale-105 cursor-pointer' :
                    'border-surface-3 text-zinc-600'}`}
              >
                {tor === 1 ? '🚦 START' : tor === anzahlTore ? `🏁 ZIEL` : `📡 Tor ${tor}`}
              </button>
            )
          })}
        </div>

        {laufId && (
          <button onClick={handleReset} className="btn-danger w-full text-xs py-2">
            ✕ Lauf abbrechen
          </button>
        )}
      </div>

      {/* Zeiten des Fahrers */}
      {zeiten.length > 0 && (
        <div className="card mb-4">
          <h3 className="font-bold text-sm mb-3">🏁 Zeiten — {teilnehmer.find(f => f.id === Number(fahrerId))?.name}</h3>
          <div className="flex flex-col gap-1.5">
            {zeiten.map((z, i) => (
              <div key={i} className="flex justify-between items-center py-1.5 border-b border-surface-3 last:border-0">
                <span className="text-zinc-400 text-xs">Lauf {i + 1}</span>
                <span className={`font-mono font-bold text-sm ${z === bestZeit ? 'text-gold' : 'text-zinc-100'}`}>
                  {z === bestZeit && '⭐ '}{z.toFixed(3)} s
                </span>
              </div>
            ))}
          </div>
          {bestZeit && (
            <div className="mt-2 text-center text-gold font-black text-sm">
              Beste: {bestZeit.toFixed(3)} s
            </div>
          )}
        </div>
      )}

      {/* Log */}
      <div className="card">
        <h3 className="font-bold text-xs text-zinc-400 uppercase tracking-wide mb-2">📋 Event-Log</h3>
        <div className="font-mono text-xs max-h-32 overflow-y-auto space-y-0.5">
          {log.length === 0 ? (
            <div className="text-zinc-600">Bereit.</div>
          ) : log.map((l, i) => (
            <div key={i} className={l.type === 'ok' ? 'text-green-400' : l.type === 'err' ? 'text-red-400' : 'text-zinc-500'}>
              [{l.ts}] {l.msg}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
