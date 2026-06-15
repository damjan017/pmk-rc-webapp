import { useEffect, useState, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import RennStatus from '../components/RennStatus'

const STRAFZEITEN_KATALOG = [
  { grund: 'Tor berührt / verschoben', zeit: 15 },
  { grund: 'Frühstart bis 5 Sek.', zeit: 10 },
  { grund: 'Frühstart mehr als 5 Sek.', zeit: 20 },
  { grund: 'Unerlaubter Service (gemeldet)', zeit: 10 },
  { grund: 'Unerlaubter Service (nicht gemeldet)', zeit: 60 },
  { grund: 'Auto mit Fuß bewegt', zeit: 30 },
  { grund: 'Falsches Zurücksetzen', zeit: 10 },
  { grund: 'Unsportliches Verhalten / Abkürzen', zeit: 30 },
  { grund: 'Technisches Element ausgelassen', zeit: 30 },
  { grund: 'Zu spät zum Startbereich', zeit: 60 },
]

// ── Renn-Timer ────────────────────────────────────────────────
function RennTimer({ status }) {
  const [elapsed, setElapsed] = useState(0)
  const startRef = useRef(null)
  const intervalRef = useRef(null)

  useEffect(() => {
    if (status === 'laufend') {
      if (!startRef.current) startRef.current = Date.now() - elapsed * 1000
      intervalRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startRef.current) / 1000))
      }, 1000)
    } else {
      clearInterval(intervalRef.current)
      if (status !== 'laufend') { startRef.current = null; setElapsed(0) }
    }
    return () => clearInterval(intervalRef.current)
  }, [status])

  if (status !== 'laufend') return null
  const h = Math.floor(elapsed / 3600)
  const m = Math.floor((elapsed % 3600) / 60)
  const s = elapsed % 60
  const fmt = h > 0
    ? `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
    : `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
  return (
    <div className="flex items-center gap-2 bg-green-900/20 border border-green-800/40 px-3 py-1.5 rounded-lg">
      <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
      <span className="text-green-400 font-mono font-bold text-sm">{fmt}</span>
      <span className="text-green-600 text-xs">Renndauer</span>
    </div>
  )
}

// ── Gruppen-Logik ─────────────────────────────────────────────
function erstelleGruppen(teilnehmer) {
  const n = teilnehmer.length
  if (n === 0) return []
  const gruppenGroesse = n > 10 ? 5 : 6
  const gruppen = []
  for (let i = 0; i < n; i += gruppenGroesse) {
    gruppen.push(teilnehmer.slice(i, i + gruppenGroesse))
  }
  return gruppen
}

// ── Gleichstand-Erkennung ─────────────────────────────────────
function findeGleichstand(board) {
  const mitZeit = board.filter(f => f.beste_gesamtzeit != null)
  if (mitZeit.length < 2) return []
  const grouped = {}
  mitZeit.forEach(f => {
    const key = f.beste_gesamtzeit.toFixed(3)
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(f)
  })
  return Object.values(grouped).filter(g => g.length > 1).flat()
}

export default function Admin() {
  const [rennen, setRennen]         = useState([])
  const [showCreate, setShowCreate] = useState(false)
  const [activeRennen, setActiveRennen] = useState(null)
  const [netzwerk, setNetzwerk]     = useState(null)
  const [loading, setLoading]       = useState(true)

  const [showTools, setShowTools] = useState(false)

  useEffect(() => {
    load()
    api.netzwerkInfo().then(setNetzwerk).catch(() => {})
  }, [])

  async function load() {
    const data = await api.getRennen()
    setRennen(data)
    setLoading(false)
  }

  if (loading) return (
    <div className="flex justify-center items-center min-h-[40vh]">
      <div className="text-gold animate-pulse text-3xl">🏁</div>
    </div>
  )

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-black flex items-center gap-2">⚙ Admin-Dashboard</h1>
          <p className="text-zinc-400 text-sm mt-1">Rennen verwalten · Zeiten eintragen · Teilnehmer</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowTools(p => !p)} className="btn-outline text-xs">🛠 Tools</button>
          <button onClick={() => setShowCreate(true)} className="btn-gold">+ Rennen erstellen</button>
        </div>
      </div>

      {/* Admin Tools Panel */}
      {showTools && <AdminToolsPanel onClose={() => setShowTools(false)} />}

      {/* Netzwerk-Info */}
      {netzwerk && <NetzwerkCard netzwerk={netzwerk} />}

      {showCreate && (
        <CreateRennenModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); load() }} />
      )}

      {activeRennen && (
        <RennDetailPanel
          rennenId={activeRennen}
          onClose={() => { setActiveRennen(null); load() }}
        />
      )}

      {rennen.length === 0 ? (
        <div className="card text-center py-16">
          <div className="text-4xl mb-4">📋</div>
          <p className="text-zinc-400 mb-4">Noch keine Rennen angelegt.</p>
          <button onClick={() => setShowCreate(true)} className="btn-gold">Erstes Rennen erstellen</button>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {rennen.map(r => (
            <div key={r.id} className="card animate-fade-in">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <h2 className="font-black text-lg">{r.name}</h2>
                    <RennStatus status={r.status} />
                  </div>
                  <div className="text-zinc-400 text-sm space-y-0.5">
                    <div>📅 {r.datum} {r.uhrzeit && `· ${r.uhrzeit} Uhr`}</div>
                    <div>📍 {r.ort} · 👥 {r.teilnehmer_count} Teilnehmer</div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 items-center">
                  <RennTimer status={r.status} />
                  <button onClick={() => setActiveRennen(r.id)} className="btn-gold text-xs">🎯 Renndurchführung</button>
                  <Link to={`/kamera/${r.id}`} className="btn-outline text-xs">📡 Kamera</Link>
                  <Link to={`/leaderboard/tv/${r.id}`} className="btn-outline text-xs">📺 TV</Link>
                  <a href={api.ergebnissePdf(r.id)} target="_blank" rel="noreferrer" className="btn-outline text-xs">🖨️ PDF</a>
                  <a href={api.urkunden(r.id)} target="_blank" rel="noreferrer" className="btn-outline text-xs">🏆 Urkunden</a>
                  <StatusButtons rennen={r} onChanged={load} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Netzwerk QR-Card ─────────────────────────────────────────
function NetzwerkCard({ netzwerk }) {
  const [expanded, setExpanded] = useState(false)
  const leaderboardUrl = `http://${netzwerk.local_ip}:5173/leaderboard`

  return (
    <div className="card mb-6 border-amber-800/30">
      <button
        onClick={() => setExpanded(p => !p)}
        className="w-full flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-gold">📡</span>
          <span className="font-bold text-sm">Netzwerk & Zuschauer-QR</span>
          <span className="text-zinc-500 text-xs">{netzwerk.local_ip}</span>
        </div>
        <span className="text-zinc-500 text-sm">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="mt-4 grid md:grid-cols-2 gap-4 animate-fade-in">
          <div>
            <p className="text-xs text-zinc-400 mb-3">
              QR-Code scannen → Rangliste auf dem Smartphone der Zuschauer.
              Alle müssen im <strong className="text-zinc-200">gleichen WLAN</strong> sein.
            </p>
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-zinc-500">Frontend:</span>
                <code className="text-gold bg-surface-2 px-2 py-0.5 rounded">{`http://${netzwerk.local_ip}:5173`}</code>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-zinc-500">API:</span>
                <code className="text-gold bg-surface-2 px-2 py-0.5 rounded">{netzwerk.api_url}</code>
              </div>
            </div>
          </div>
          <div className="text-center">
            <p className="text-xs text-zinc-500 mb-2">Leaderboard QR-Code</p>
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(leaderboardUrl)}&bgcolor=18181B&color=F59E0B&margin=8`}
              alt="QR Code Leaderboard"
              className="w-32 h-32 mx-auto rounded-xl"
              onError={e => { e.target.style.display = 'none' }}
            />
            <p className="text-xs text-zinc-600 mt-1">{leaderboardUrl}</p>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Status Buttons ────────────────────────────────────────────
function StatusButtons({ rennen: r, onChanged }) {
  async function doAction(fn) {
    try { await fn(); onChanged() } catch (e) { alert(e.message) }
  }
  if (r.status === 'offen')
    return <button onClick={() => doAction(() => api.startenRennen(r.id))} className="btn-outline text-xs text-green-400 border-green-800">▶ Starten</button>
  if (r.status === 'laufend')
    return <button onClick={() => doAction(() => api.abschliessenRennen(r.id))} className="btn-outline text-xs text-red-400 border-red-800">■ Abschließen</button>
  return <button onClick={() => doAction(() => api.resetRennen(r.id))} className="btn-outline text-xs">↺ Wieder öffnen</button>
}

// ── Rennen Erstellen Modal ────────────────────────────────────
function CreateRennenModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    name: '', datum: '', uhrzeit: '', ort: '', ort_link: '',
    beschreibung: '', max_teilnehmer: 50,
    fahrzeug_klasse: '', reifen_vorgabe: '', max_breite_mm: '', sonstige_regeln: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  function set(k, v) { setForm(p => ({ ...p, [k]: v })) }

  async function submit(e) {
    e.preventDefault(); setLoading(true); setError('')
    try {
      await api.createRennen({
        ...form,
        max_teilnehmer: Number(form.max_teilnehmer),
        max_breite_mm: form.max_breite_mm ? Number(form.max_breite_mm) : null,
        ort_link: form.ort_link || null,
      })
      onCreated()
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="bg-surface border border-surface-3 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto animate-slide-up">
        <div className="p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-black text-lg">Neues Rennen erstellen</h2>
            <button onClick={onClose} className="text-zinc-500 hover:text-zinc-100 text-xl">×</button>
          </div>
          <form onSubmit={submit} className="flex flex-col gap-4">
            <div><label className="label">Rennenname *</label><input className="input" value={form.name} onChange={e => set('name', e.target.value)} placeholder="z.B. Frühjahrs-Rally 2026" required /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="label">Datum *</label><input className="input" type="date" value={form.datum} onChange={e => set('datum', e.target.value)} required /></div>
              <div><label className="label">Uhrzeit</label><input className="input" type="time" value={form.uhrzeit} onChange={e => set('uhrzeit', e.target.value)} /></div>
            </div>
            <div><label className="label">Ort *</label><input className="input" value={form.ort} onChange={e => set('ort', e.target.value)} placeholder="z.B. Parkplatz Hochschule Pforzheim" required /></div>
            <div><label className="label">Google Maps Link</label><input className="input" value={form.ort_link} onChange={e => set('ort_link', e.target.value)} placeholder="https://maps.google.com/..." /></div>
            <div><label className="label">Beschreibung</label><textarea className="input h-20 resize-none" value={form.beschreibung} onChange={e => set('beschreibung', e.target.value)} /></div>
            <div><label className="label">Max. Teilnehmer</label><input className="input" type="number" min="1" max="500" value={form.max_teilnehmer} onChange={e => set('max_teilnehmer', e.target.value)} /></div>
            <div className="border-t border-surface-3 pt-4">
              <p className="text-xs font-bold text-zinc-400 uppercase tracking-wide mb-3">📋 Fahrzeugvorgaben</p>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Fahrzeugklasse</label><input className="input" value={form.fahrzeug_klasse} onChange={e => set('fahrzeug_klasse', e.target.value)} placeholder="z.B. 1:10 Offroad" /></div>
                <div><label className="label">Reifenvorgabe</label><input className="input" value={form.reifen_vorgabe} onChange={e => set('reifen_vorgabe', e.target.value)} placeholder="z.B. Standardbereifung" /></div>
                <div><label className="label">Max. Breite (mm)</label><input className="input" type="number" value={form.max_breite_mm} onChange={e => set('max_breite_mm', e.target.value)} placeholder="190" /></div>
              </div>
              <div className="mt-3"><label className="label">Sonstige Regeln</label><textarea className="input h-16 resize-none" value={form.sonstige_regeln} onChange={e => set('sonstige_regeln', e.target.value)} /></div>
            </div>
            {error && <div className="bg-red-900/30 border border-red-800 text-red-400 text-sm px-3 py-2 rounded-lg">{error}</div>}
            <div className="flex gap-3">
              <button type="button" onClick={onClose} className="btn-outline flex-1">Abbrechen</button>
              <button type="submit" className="btn-gold flex-1" disabled={loading}>{loading ? 'Wird erstellt…' : 'Erstellen'}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

// ── Renn Detail Panel ─────────────────────────────────────────
function RennDetailPanel({ rennenId, onClose }) {
  const [rennen, setRennen]         = useState(null)
  const [teilnehmer, setTeilnehmer] = useState([])
  const [board, setBoard]           = useState([])
  const [tab, setTab]               = useState('teilnehmer')
  const [zeitForm, setZeitForm]     = useState({ fahrer_id: '', rundenzeit: '' })
  const [strafForm, setStrafForm]   = useState({ fahrer_id: '', strafzeit: 15, grund: STRAFZEITEN_KATALOG[0].grund })
  const [manForm, setManForm]       = useState({ name: '', email: '', fahrzeug: '' })
  const [csvFile, setCsvFile]       = useState(null)
  const [msg, setMsg]               = useState('')
  const [startzeit, setStartzeit]   = useState('10:00')
  const [intervall, setIntervall]   = useState(30)
  const [showQrScanner, setShowQrScanner] = useState(false)
  const [finalFahrer, setFinalFahrer] = useState([])

  useEffect(() => { load() }, [rennenId])

  async function load() {
    const [r, t, b] = await Promise.all([
      api.getRennenById(rennenId),
      api.getTeilnehmer(rennenId),
      api.getLeaderboard(rennenId),
    ])
    setRennen(r); setTeilnehmer(t); setBoard(b)
    setFinalFahrer(findeGleichstand(b))
  }

  function showMsg(text) { setMsg(text); setTimeout(() => setMsg(''), 3500) }

  async function handleCheckin(userId) {
    try { const d = await api.checkin(rennenId, userId); showMsg(`✓ ${d.message}`); load() }
    catch (e) { showMsg(`✗ ${e.message}`) }
  }

  async function handleQrCheckin(userId) {
    setShowQrScanner(false)
    await handleCheckin(userId)
  }

  async function handleZeit(e) {
    e.preventDefault()
    try {
      await api.zeitEintragen({ fahrer_id: Number(zeitForm.fahrer_id), rennen_id: rennenId, rundenzeit: Number(zeitForm.rundenzeit) })
      showMsg('✓ Zeit eingetragen'); setZeitForm({ fahrer_id: '', rundenzeit: '' }); load()
    } catch (e) { showMsg(`✗ ${e.message}`) }
  }

  async function handleStraf(e) {
    e.preventDefault()
    try {
      await api.strafzeitHinzufuegen({ fahrer_id: Number(strafForm.fahrer_id), rennen_id: rennenId, strafzeit: Number(strafForm.strafzeit), grund: strafForm.grund })
      showMsg('✓ Strafzeit eingetragen'); load()
    } catch (e) { showMsg(`✗ ${e.message}`) }
  }

  async function handleManuell(e) {
    e.preventDefault()
    try {
      const d = await api.manuellAnmelden(rennenId, manForm)
      showMsg(`✓ ${d.message}`); setManForm({ name: '', email: '', fahrzeug: '' }); load()
    } catch (e) { showMsg(`✗ ${e.message}`) }
  }

  async function handleCsv(e) {
    e.preventDefault()
    if (!csvFile) return
    const form = new FormData(); form.append('file', csvFile)
    try {
      const d = await api.csvImport(rennenId, form)
      showMsg(`✓ ${d.imported} Fahrer importiert`); setCsvFile(null); load()
    } catch (e) { showMsg(`✗ ${e.message}`) }
  }

  async function handleFinalErstellen() {
    if (finalFahrer.length < 2) return
    const namen = finalFahrer.map(f => f.name).join(', ')
    if (!confirm(`Final-Rennen erstellen für:\n${namen}\n\nDiese Fahrer werden automatisch angemeldet.`)) return
    try {
      const r = await api.createRennen({
        name: `⚡ FINAL — ${rennen.name}`,
        datum: rennen.datum, uhrzeit: rennen.uhrzeit,
        ort: rennen.ort, ort_link: rennen.ort_link,
        beschreibung: `Final-Rennen wegen Gleichstand bei ${namen}.`,
        max_teilnehmer: finalFahrer.length,
        fahrzeug_klasse: rennen.fahrzeug_klasse,
        reifen_vorgabe: rennen.reifen_vorgabe,
        max_breite_mm: rennen.max_breite_mm,
      })
      for (const f of finalFahrer) {
        await api.manuellAnmelden(r.id, { name: f.name, email: `final_${f.id}@lokal.rally`, fahrzeug: f.fahrzeug })
      }
      showMsg(`✓ Final-Rennen erstellt! Kamera: /kamera/${r.id}`)
    } catch (e) { showMsg(`✗ ${e.message}`) }
  }

  function fmtTime(s) {
    if (s == null) return '—'
    return s < 60 ? `${s.toFixed(3)} s` : `${Math.floor(s / 60)}:${(s % 60).toFixed(3).padStart(6, '0')} min`
  }

  // Startliste berechnen
  function berechnStartliste() {
    const [h, m] = startzeit.split(':').map(Number)
    const basisMs = (h * 3600 + m * 60) * 1000
    return [...teilnehmer].sort((a, b) => a.startnummer - b.startnummer).map((f, i) => {
      const startMs = basisMs + i * intervall * 1000
      const sh = Math.floor(startMs / 3600000)
      const sm = Math.floor((startMs % 3600000) / 60000)
      const ss = Math.floor((startMs % 60000) / 1000)
      return { ...f, startzeit: `${String(sh).padStart(2, '0')}:${String(sm).padStart(2, '0')}:${String(ss).padStart(2, '0')}` }
    })
  }

  const gruppen = erstelleGruppen(teilnehmer)

  if (!rennen) return <div className="card mb-6 p-8 text-center text-gold animate-pulse">Wird geladen…</div>

  const tabs = ['teilnehmer', 'zeiten', 'leaderboard', 'startliste', 'import']

  return (
    <div className="card mb-6 animate-fade-in border-gold/30">
      <div className="flex items-start justify-between mb-4 flex-wrap gap-3">
        <div>
          <h2 className="font-black text-lg">{rennen.name}</h2>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <RennStatus status={rennen.status} />
            <span className="text-zinc-500 text-xs">Renndurchführung</span>
          </div>
        </div>
        <button onClick={onClose} className="text-zinc-500 hover:text-zinc-100 text-xl px-2">×</button>
      </div>

      {msg && (
        <div className={`text-sm px-3 py-2 rounded-lg mb-4 border ${msg.startsWith('✓') ? 'bg-green-900/30 border-green-800 text-green-400' : 'bg-red-900/30 border-red-800 text-red-400'}`}>
          {msg}
        </div>
      )}

      {/* Gleichstand-Warnung */}
      {finalFahrer.length >= 2 && (
        <div className="mb-4 p-4 bg-amber-900/20 border border-amber-700/50 rounded-xl">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div>
              <div className="text-gold font-bold text-sm mb-1">⚡ Gleichstand erkannt!</div>
              <div className="text-zinc-300 text-xs">
                {finalFahrer.map(f => `#${f.startnummer} ${f.name}`).join(' · ')} — gleiche Gesamtzeit
              </div>
            </div>
            <button onClick={handleFinalErstellen} className="btn-gold text-xs shrink-0">
              🏁 Final-Rennen erstellen
            </button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-5 border-b border-surface-3 overflow-x-auto">
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-2 text-xs font-bold border-b-2 transition-colors whitespace-nowrap ${tab === t ? 'border-gold text-gold' : 'border-transparent text-zinc-400 hover:text-zinc-200'}`}>
            {t === 'teilnehmer' ? `👥 Teilnehmer (${teilnehmer.length})`
              : t === 'zeiten' ? '⏱ Zeiten & Strafen'
              : t === 'leaderboard' ? '🏆 Rangliste'
              : t === 'startliste' ? '📋 Startliste'
              : '📥 Import'}
          </button>
        ))}
      </div>

      {/* ── Teilnehmer Tab ── */}
      {tab === 'teilnehmer' && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-zinc-400">{teilnehmer.length} Teilnehmer</span>
            <button
              onClick={() => setShowQrScanner(true)}
              className="btn-outline text-xs flex items-center gap-1.5"
            >
              📷 QR-Scanner
            </button>
          </div>

          {showQrScanner && (
            <QrScannerModal
              onClose={() => setShowQrScanner(false)}
              onCheckin={handleQrCheckin}
            />
          )}

          {teilnehmer.length === 0 ? (
            <p className="text-zinc-400 text-sm text-center py-6">Noch keine Teilnehmer.</p>
          ) : (
            <>
              <div className="flex flex-col gap-2 mb-4">
                {teilnehmer.map(f => (
                  <div key={f.id} className="flex items-center gap-3 p-3 bg-surface-2 rounded-lg text-sm">
                    <span className="text-gold font-black w-8">#{f.startnummer}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold truncate">{f.name}</div>
                      <div className="text-zinc-500 text-xs truncate">{f.fahrzeug}</div>
                    </div>
                    {f.eingecheckt
                      ? <span className="badge-green">✓ Eingecheckt</span>
                      : <button onClick={() => handleCheckin(f.id)} className="btn-outline text-xs px-2 py-1">Check-in</button>}
                  </div>
                ))}
              </div>

              {/* Gruppenaufteilung */}
              {gruppen.length > 1 && (
                <div className="border-t border-surface-3 pt-4">
                  <p className="text-xs font-bold text-zinc-400 uppercase tracking-wide mb-3">
                    🏎️ Gruppenaufteilung ({gruppen.length} Gruppen)
                  </p>
                  <div className="grid md:grid-cols-2 gap-3">
                    {gruppen.map((gruppe, gi) => (
                      <div key={gi} className="p-3 bg-surface-2 rounded-lg">
                        <div className="text-xs font-bold text-gold mb-2">Gruppe {gi + 1} ({gruppe.length} Fahrer)</div>
                        {gruppe.map(f => (
                          <div key={f.id} className="flex items-center gap-2 py-1 text-xs">
                            <span className="text-gold font-bold w-6">#{f.startnummer}</span>
                            <span className="text-zinc-300">{f.name}</span>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Zeiten Tab ── */}
      {tab === 'zeiten' && (
        <div className="grid md:grid-cols-2 gap-5">
          <div>
            <h3 className="font-bold text-sm mb-3">⏱ Zeit eintragen</h3>
            <form onSubmit={handleZeit} className="flex flex-col gap-3">
              <div>
                <label className="label">Fahrer</label>
                <select className="select" value={zeitForm.fahrer_id} onChange={e => setZeitForm(p => ({ ...p, fahrer_id: e.target.value }))} required>
                  <option value="">— Fahrer wählen —</option>
                  {teilnehmer.map(f => <option key={f.id} value={f.id}>#{f.startnummer} {f.name}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Rundenzeit (Sekunden)</label>
                <input className="input" type="number" step="0.001" min="0" placeholder="z.B. 48.120"
                  value={zeitForm.rundenzeit} onChange={e => setZeitForm(p => ({ ...p, rundenzeit: e.target.value }))} required />
              </div>
              <button type="submit" className="btn-gold w-full">Zeit speichern</button>
            </form>
          </div>

          <div>
            <h3 className="font-bold text-sm mb-3">⚠️ Strafzeit eintragen</h3>
            <form onSubmit={handleStraf} className="flex flex-col gap-3">
              <div>
                <label className="label">Fahrer</label>
                <select className="select" value={strafForm.fahrer_id} onChange={e => setStrafForm(p => ({ ...p, fahrer_id: e.target.value }))} required>
                  <option value="">— Fahrer wählen —</option>
                  {teilnehmer.map(f => <option key={f.id} value={f.id}>#{f.startnummer} {f.name}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Vergehen</label>
                <select className="select" value={strafForm.grund} onChange={e => {
                  const k = STRAFZEITEN_KATALOG.find(s => s.grund === e.target.value)
                  setStrafForm(p => ({ ...p, grund: e.target.value, strafzeit: k?.zeit || p.strafzeit }))
                }}>
                  {STRAFZEITEN_KATALOG.map(s => <option key={s.grund} value={s.grund}>{s.grund} (+{s.zeit}s)</option>)}
                </select>
              </div>
              <div>
                <label className="label">Strafzeit (Sek.)</label>
                <input className="input" type="number" step="0.5" min="0"
                  value={strafForm.strafzeit} onChange={e => setStrafForm(p => ({ ...p, strafzeit: e.target.value }))} required />
              </div>
              <button type="submit" className="bg-red-900/40 border border-red-800 text-red-300 font-bold py-2 rounded-lg text-sm hover:bg-red-800/50 transition-colors">
                Strafzeit eintragen
              </button>
            </form>

            <div className="mt-4 p-3 bg-surface-2 rounded-lg">
              <p className="text-xs font-bold text-zinc-400 mb-2">Strafzeiten-Übersicht</p>
              <div className="space-y-1">
                {STRAFZEITEN_KATALOG.map(s => (
                  <div key={s.grund} className="flex justify-between text-xs">
                    <span className="text-zinc-400 truncate mr-2">{s.grund}</span>
                    <span className="text-red-400 font-bold shrink-0">+{s.zeit}s</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Leaderboard Tab ── */}
      {tab === 'leaderboard' && (
        <div>
          <div className="flex justify-between items-center mb-3 flex-wrap gap-2">
            <span className="text-sm font-bold">{board.length} Fahrer</span>
            <div className="flex gap-2 flex-wrap">
              <button onClick={async () => { if(confirm('10 Demo-Fahrer mit Zufallszeiten einfügen?')) { try { const d = await api.demoErstellen(rennenId); showMsg(`✓ ${d.message}`); load() } catch(e) { showMsg(`✗ ${e.message}`) }}}} className="btn-outline text-xs">🎭 Demo</button>
              <button onClick={async () => { try { const d = await api.ergebnismail(rennenId); showMsg(`✓ ${d.message}`) } catch(e) { showMsg(`✗ ${e.message}`) }}} className="btn-outline text-xs">📧 Ergebnis-Mail</button>
              <a href={api.urkunden(rennenId)} target="_blank" rel="noreferrer" className="btn-outline text-xs">🏆 Urkunden</a>
              <Link to={`/leaderboard/tv/${rennenId}`} target="_blank" className="btn-outline text-xs">📺 TV</Link>
              <button onClick={load} className="btn-outline text-xs">↺</button>
              <a href={api.ergebnissePdf(rennenId)} target="_blank" rel="noreferrer" className="btn-outline text-xs">🖨️ PDF</a>
            </div>
          </div>
          {board.length === 0 ? (
            <p className="text-zinc-400 text-sm text-center py-6">Noch keine Zeiten.</p>
          ) : (
            <div className="flex flex-col gap-1.5">
              {board.map((f, i) => {
                const istGleichstand = finalFahrer.some(x => x.id === f.id)
                return (
                  <div key={f.id} className={`flex items-center gap-3 p-2.5 rounded-lg text-sm ${istGleichstand ? 'bg-amber-900/20 border border-amber-700/40' : 'bg-surface-2'}`}>
                    <span className="w-6 text-center text-xs font-bold text-zinc-400">{i + 1}.</span>
                    <span className="text-gold font-black w-8">#{f.startnummer}</span>
                    <span className="flex-1 truncate font-semibold">{f.name}</span>
                    {istGleichstand && <span className="text-gold text-xs">⚡ Gleichstand</span>}
                    <span className="font-mono text-xs font-bold text-gold">{f.beste_gesamtzeit != null ? `${f.beste_gesamtzeit.toFixed(3)} s` : '—'}</span>
                    {f.gesamt_strafzeit > 0 && <span className="text-red-400 text-xs">+{f.gesamt_strafzeit}s</span>}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Startliste Tab ── */}
      {tab === 'startliste' && (
        <div>
          <div className="flex items-center gap-4 mb-4 flex-wrap">
            <div>
              <label className="label">Startzeit</label>
              <input className="input w-32" type="time" value={startzeit} onChange={e => setStartzeit(e.target.value)} />
            </div>
            <div>
              <label className="label">Intervall (Sek.)</label>
              <input className="input w-24" type="number" min="10" max="120" value={intervall} onChange={e => setIntervall(Number(e.target.value))} />
            </div>
          </div>

          {teilnehmer.length === 0 ? (
            <p className="text-zinc-400 text-sm text-center py-6">Keine Teilnehmer angemeldet.</p>
          ) : (
            <>
              {gruppen.length > 1 && (
                <p className="text-xs text-zinc-500 mb-3">
                  {gruppen.length} Gruppen · {teilnehmer.length} Fahrer · {intervall}s Intervall
                </p>
              )}
              <div className="flex flex-col gap-1.5">
                {berechnStartliste().map((f, i) => (
                  <div key={f.id} className={`flex items-center gap-3 p-2.5 rounded-lg text-sm ${gruppen.length > 1 && Math.floor(i / (teilnehmer.length > 10 ? 5 : 6)) % 2 === 0 ? 'bg-surface-2' : 'bg-surface'}`}>
                    <span className="font-mono text-gold font-bold w-20 shrink-0">{f.startzeit}</span>
                    <span className="text-gold font-black w-8">#{f.startnummer}</span>
                    <span className="flex-1 font-semibold truncate">{f.name}</span>
                    <span className="text-zinc-500 text-xs truncate">{f.fahrzeug}</span>
                    {f.eingecheckt
                      ? <span className="badge-green shrink-0">✓</span>
                      : <span className="badge-gray shrink-0">—</span>}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Import Tab ── */}
      {tab === 'import' && (
        <div className="grid md:grid-cols-2 gap-5">
          <div>
            <h3 className="font-bold text-sm mb-3">➕ Manuell anmelden</h3>
            <p className="text-zinc-400 text-xs mb-3">Für Personen ohne Smartphone / PC vor Ort</p>
            <form onSubmit={handleManuell} className="flex flex-col gap-3">
              <div><label className="label">Name *</label><input className="input" placeholder="Max Mustermann" value={manForm.name} onChange={e => setManForm(p => ({ ...p, name: e.target.value }))} required /></div>
              <div><label className="label">E-Mail (optional)</label><input className="input" type="email" placeholder="max@example.de" value={manForm.email} onChange={e => setManForm(p => ({ ...p, email: e.target.value }))} /></div>
              <div><label className="label">Fahrzeug *</label><input className="input" placeholder="Traxxas Slash 4x4" value={manForm.fahrzeug} onChange={e => setManForm(p => ({ ...p, fahrzeug: e.target.value }))} required /></div>
              <button type="submit" className="btn-gold w-full">Anmelden</button>
            </form>
          </div>

          <div>
            <h3 className="font-bold text-sm mb-3">📁 CSV-Import</h3>
            <p className="text-zinc-400 text-xs mb-3">
              CSV-Datei mit Spalten: <code className="text-gold bg-surface-2 px-1 rounded">name,email,fahrzeug</code>
            </p>
            <form onSubmit={handleCsv} className="flex flex-col gap-3">
              <div>
                <label className="label">CSV-Datei</label>
                <input type="file" accept=".csv"
                  className="w-full text-sm text-zinc-400 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-surface-2 file:text-gold file:font-semibold file:text-xs hover:file:bg-surface-3 cursor-pointer"
                  onChange={e => setCsvFile(e.target.files[0])} required />
              </div>
              <div className="p-3 bg-surface-2 rounded-lg text-xs text-zinc-400">
                <div className="font-bold text-zinc-300 mb-1">Beispiel:</div>
                <pre className="text-gold">name,email,fahrzeug{'\n'}Max M.,max@mail.de,Traxxas Slash{'\n'}Lisa K.,,Axial SCX10</pre>
              </div>
              <button type="submit" className="btn-gold w-full" disabled={!csvFile}>Importieren</button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Admin Tools Panel ─────────────────────────────────────────
function AdminToolsPanel({ onClose }) {
  const [msg, setMsg] = useState('')

  function showMsg(text) { setMsg(text); setTimeout(() => setMsg(''), 4000) }

  async function handleLoeschen() {
    if (!confirm('⚠️ ALLE Fahrerdaten und Rennergebnisse unwiderruflich löschen?\n\nNur nach dem Event zur DSGVO-Erfüllung verwenden!')) return
    if (!confirm('Bist du wirklich sicher? Diese Aktion kann nicht rückgängig gemacht werden.')) return
    try {
      const d = await api.datenLoeschen()
      showMsg(`✓ ${d.message}`)
    } catch(e) { showMsg(`✗ ${e.message}`) }
  }

  return (
    <div className="card mb-6 border-zinc-600 animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold">🛠 Admin-Tools</h3>
        <button onClick={onClose} className="text-zinc-500 hover:text-zinc-100">×</button>
      </div>

      {msg && (
        <div className={`text-sm px-3 py-2 rounded-lg mb-4 border ${msg.startsWith('✓') ? 'bg-green-900/30 border-green-800 text-green-400' : 'bg-red-900/30 border-red-800 text-red-400'}`}>
          {msg}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        {/* Backup */}
        <div className="p-4 bg-surface-2 rounded-xl">
          <div className="font-bold text-sm mb-1">💾 Datenbank-Backup</div>
          <p className="text-zinc-400 text-xs mb-3">Lädt die aktuelle rally.db als Sicherungskopie herunter.</p>
          <a href={api.backup()} className="btn-outline text-xs inline-block">
            ⬇️ Backup herunterladen
          </a>
        </div>

        {/* DSGVO Löschen */}
        <div className="p-4 bg-red-900/10 border border-red-900/30 rounded-xl">
          <div className="font-bold text-sm mb-1 text-red-400">🗑️ DSGVO-Datenlöschung</div>
          <p className="text-zinc-400 text-xs mb-3">
            Löscht alle Fahrer-Accounts und Rennergebnisse nach dem Event. Admins bleiben erhalten.
          </p>
          <button onClick={handleLoeschen} className="btn-danger text-xs">
            Alle Daten löschen
          </button>
        </div>
      </div>
    </div>
  )
}

// ── QR-Scanner Modal ──────────────────────────────────────────
function QrScannerModal({ onClose, onCheckin }) {
  const videoRef    = useRef(null)
  const streamRef   = useRef(null)
  const [status, setStatus] = useState('Kamera wird gestartet…')
  const [error, setError]   = useState('')
  const scanningRef = useRef(true)

  useEffect(() => {
    startCamera()
    return () => {
      scanningRef.current = false
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop())
    }
  }, [])

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play()
        setStatus('Kamera aktiv — QR-Code in den Rahmen halten')
        scanLoop()
      }
    } catch (e) {
      setError(`Kamera nicht verfügbar: ${e.message}`)
    }
  }

  async function scanLoop() {
    if (!('BarcodeDetector' in window)) {
      setError('BarcodeDetector nicht unterstützt. Bitte Fahrer-ID manuell eingeben.')
      return
    }
    const detector = new window.BarcodeDetector({ formats: ['qr_code'] })
    async function tick() {
      if (!scanningRef.current || !videoRef.current) return
      try {
        const codes = await detector.detect(videoRef.current)
        if (codes.length > 0) {
          const val = codes[0].rawValue
          const match = val.match(/^CHECKIN:(\d+)$/)
          if (match) {
            scanningRef.current = false
            setStatus(`✓ QR erkannt! Fahrer-ID: ${match[1]}`)
            onCheckin(Number(match[1]))
            return
          }
        }
      } catch {}
      if (scanningRef.current) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
      <div className="bg-surface border border-surface-3 rounded-2xl w-full max-w-sm animate-slide-up">
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold">📷 QR-Scanner</h3>
            <button onClick={onClose} className="text-zinc-500 hover:text-zinc-100 text-xl">×</button>
          </div>

          {error ? (
            <div className="bg-red-900/30 border border-red-800 text-red-400 text-sm px-3 py-3 rounded-lg mb-3">
              {error}
            </div>
          ) : (
            <div className="relative mb-3 rounded-xl overflow-hidden bg-black aspect-square">
              <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />
              {/* Scan-Rahmen */}
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-48 h-48 border-2 border-gold rounded-lg opacity-70" />
              </div>
            </div>
          )}

          <p className="text-zinc-400 text-xs text-center">{status}</p>

          <button onClick={onClose} className="btn-outline w-full mt-3 text-xs">Abbrechen</button>
        </div>
      </div>
    </div>
  )
}
