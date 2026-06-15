import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../lib/api'
import RennStatus from '../components/RennStatus'

export default function RennAnmelden() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [rennen, setRennen] = useState(null)
  const [form, setForm] = useState({ fahrzeug: '', einwilligung: false })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(null)

  useEffect(() => {
    api.getRennenById(id).then(setRennen).catch(() => navigate('/rennen'))
  }, [id])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.einwilligung) { setError('Bitte stimme der Datenschutzerklärung zu.'); return }
    setError(''); setLoading(true)
    try {
      const data = await api.anmelden(id, form)
      setSuccess(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!rennen) return <div className="flex justify-center items-center min-h-[40vh]"><div className="text-gold animate-pulse text-3xl">🏁</div></div>

  if (success) return (
    <div className="max-w-md mx-auto px-6 py-16 text-center animate-fade-in">
      <div className="text-5xl mb-4">🎉</div>
      <h2 className="text-2xl font-black mb-2">Angemeldet!</h2>
      <p className="text-zinc-400 mb-6">Du hast die Startnummer <span className="text-gold font-black text-2xl">#{success.startnummer}</span></p>
      <p className="text-zinc-500 text-sm mb-8">Du erhältst eine Bestätigungs-E-Mail mit deinem QR-Code.</p>
      <div className="flex flex-col gap-3">
        <Link to="/profil" className="btn-gold w-full py-3">Zum Profil & QR-Code</Link>
        <Link to="/rennen" className="btn-outline w-full py-3">Zurück zu den Rennen</Link>
      </div>
    </div>
  )

  return (
    <div className="max-w-lg mx-auto px-6 py-10">
      <Link to="/rennen" className="text-zinc-400 hover:text-gold text-sm flex items-center gap-1 mb-6 transition-colors">
        ← Zurück
      </Link>

      <div className="card mb-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <h2 className="font-black text-lg">{rennen.name}</h2>
          <RennStatus status={rennen.status} />
        </div>
        <div className="text-zinc-400 text-sm space-y-1">
          <div>📅 {rennen.datum} {rennen.uhrzeit && `· ${rennen.uhrzeit} Uhr`}</div>
          <div>📍 {rennen.ort}</div>
          <div>👥 {rennen.teilnehmer_count} / {rennen.max_teilnehmer} Fahrer</div>
        </div>
        {(rennen.fahrzeug_klasse || rennen.reifen_vorgabe || rennen.max_breite_mm) && (
          <div className="mt-3 p-3 bg-amber-900/10 border border-amber-800/30 rounded-lg">
            <div className="text-gold text-xs font-bold mb-2">📋 Fahrzeugvorgaben</div>
            <div className="text-xs text-zinc-300 space-y-1">
              {rennen.fahrzeug_klasse && <div>Klasse: {rennen.fahrzeug_klasse}</div>}
              {rennen.reifen_vorgabe && <div>Reifen: {rennen.reifen_vorgabe}</div>}
              {rennen.max_breite_mm && <div>Max. Breite: {rennen.max_breite_mm} mm</div>}
              {rennen.sonstige_regeln && <div className="text-zinc-400">{rennen.sonstige_regeln}</div>}
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="card flex flex-col gap-4">
        <h3 className="font-bold">Für dieses Rennen anmelden</h3>
        <div>
          <label className="label">Fahrzeugbezeichnung</label>
          <input className="input" type="text" placeholder="z.B. Traxxas Slash 4x4"
            value={form.fahrzeug}
            onChange={e => setForm(p => ({ ...p, fahrzeug: e.target.value }))} required />
          <p className="text-xs text-zinc-500 mt-1">Marke und Modell deines RC-Cars</p>
        </div>

        <label className="flex gap-3 cursor-pointer">
          <input type="checkbox" checked={form.einwilligung}
            onChange={e => setForm(p => ({ ...p, einwilligung: e.target.checked }))}
            className="mt-0.5 accent-amber-500" />
          <span className="text-xs text-zinc-400 leading-relaxed">
            Ich stimme der Verarbeitung meiner Daten für die Durchführung der RC-Car Rally zu.
            Die Daten werden nach dem Event gelöscht (DSGVO).
          </span>
        </label>

        {error && <div className="bg-red-900/30 border border-red-800 text-red-400 text-sm px-3 py-2 rounded-lg">{error}</div>}

        <button type="submit" className="btn-gold w-full py-2.5" disabled={loading}>
          {loading ? 'Wird angemeldet…' : 'Jetzt anmelden →'}
        </button>
      </form>
    </div>
  )
}
