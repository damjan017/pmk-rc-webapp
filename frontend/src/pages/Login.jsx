import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [form, setForm] = useState({ email: '', passwort: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await api.login(form)
      login(data)
      navigate(data.rolle === 'admin' ? '/admin' : '/rennen')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm animate-fade-in">
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">🏁</div>
          <h1 className="text-2xl font-black">Anmelden</h1>
          <p className="text-zinc-400 text-sm mt-1">PMK RC-Car Rally Portal</p>
        </div>

        <form onSubmit={handleSubmit} className="card flex flex-col gap-4">
          <div>
            <label className="label">E-Mail</label>
            <input
              className="input"
              type="email"
              placeholder="max@example.de"
              value={form.email}
              onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
              required
            />
          </div>
          <div>
            <label className="label">Passwort</label>
            <input
              className="input"
              type="password"
              placeholder="••••••••"
              value={form.passwort}
              onChange={e => setForm(p => ({ ...p, passwort: e.target.value }))}
              required
            />
          </div>

          {error && (
            <div className="bg-red-900/30 border border-red-800 text-red-400 text-sm px-3 py-2 rounded-lg">
              {error}
            </div>
          )}

          <button type="submit" className="btn-gold w-full py-2.5" disabled={loading}>
            {loading ? 'Wird angemeldet…' : 'Anmelden →'}
          </button>
        </form>

        <p className="text-center text-sm text-zinc-500 mt-4">
          Noch kein Account?{' '}
          <Link to="/register" className="text-gold hover:text-gold-light transition-colors font-semibold">
            Registrieren
          </Link>
        </p>
      </div>
    </div>
  )
}
