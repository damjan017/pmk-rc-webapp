import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

export default function Register() {
  const [form, setForm] = useState({ name: '', email: '', passwort: '', dsgvo: false })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.dsgvo) { setError('Bitte stimme der Datenschutzerklärung zu.'); return }
    setError('')
    setLoading(true)
    try {
      await api.register({ name: form.name, email: form.email, passwort: form.passwort })
      navigate('/login?registered=1')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm animate-fade-in">
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">🏎️</div>
          <h1 className="text-2xl font-black">Registrieren</h1>
          <p className="text-zinc-400 text-sm mt-1">Erstelle deinen Rally-Account</p>
        </div>

        <form onSubmit={handleSubmit} className="card flex flex-col gap-4">
          <div>
            <label className="label">Vollständiger Name</label>
            <input className="input" type="text" placeholder="Max Mustermann"
              value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} required />
          </div>
          <div>
            <label className="label">E-Mail-Adresse</label>
            <input className="input" type="email" placeholder="max@example.de"
              value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} required />
          </div>
          <div>
            <label className="label">Passwort</label>
            <input className="input" type="password" placeholder="Mindestens 6 Zeichen"
              value={form.passwort} onChange={e => setForm(p => ({ ...p, passwort: e.target.value }))}
              minLength={6} required />
          </div>

          {/* DSGVO */}
          <label className="flex gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={form.dsgvo}
              onChange={e => setForm(p => ({ ...p, dsgvo: e.target.checked }))}
              className="mt-0.5 accent-amber-500"
            />
            <span className="text-xs text-zinc-400 leading-relaxed">
              Ich stimme der Verarbeitung meiner Daten für die Durchführung der RC-Car Rally zu.
              Die Daten werden nach dem Event gelöscht.{' '}
              <Link to="/impressum" className="text-gold hover:underline">Datenschutz</Link>
            </span>
          </label>

          {error && (
            <div className="bg-red-900/30 border border-red-800 text-red-400 text-sm px-3 py-2 rounded-lg">
              {error}
            </div>
          )}

          <button type="submit" className="btn-gold w-full py-2.5" disabled={loading}>
            {loading ? 'Wird erstellt…' : 'Account erstellen →'}
          </button>
        </form>

        <p className="text-center text-sm text-zinc-500 mt-4">
          Bereits registriert?{' '}
          <Link to="/login" className="text-gold hover:text-gold-light transition-colors font-semibold">Anmelden</Link>
        </p>
      </div>
    </div>
  )
}
