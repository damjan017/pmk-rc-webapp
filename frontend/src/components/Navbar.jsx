import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useState } from 'react'

export default function Navbar() {
  const { user, logout, isAdmin } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/')
  }

  const isActive = (path) =>
    location.pathname === path ? 'text-zinc-100' : 'text-zinc-400 hover:text-zinc-100'

  return (
    <nav className="sticky top-0 z-50 bg-bg/90 backdrop-blur-md border-b border-surface-3 h-14 flex items-center px-4 md:px-6 gap-6">
      {/* Brand */}
      <Link to="/" className="flex items-center gap-2 font-black text-base shrink-0">
        🏁 PMK <span className="text-gold">Rally</span>
      </Link>

      {/* Desktop Links */}
      <div className="hidden md:flex items-center gap-1 flex-1">
        <Link to="/rennen" className={`text-sm font-semibold px-3 py-1.5 rounded-lg transition-colors ${isActive('/rennen')}`}>
          Rennen
        </Link>
        <Link to="/leaderboard" className={`text-sm font-semibold px-3 py-1.5 rounded-lg transition-colors ${isActive('/leaderboard')}`}>
          Rangliste
        </Link>
        <Link to="/faq" className={`text-sm font-semibold px-3 py-1.5 rounded-lg transition-colors ${isActive('/faq')}`}>
          FAQ
        </Link>
        {isAdmin && (
          <Link to="/admin" className={`text-sm font-semibold px-3 py-1.5 rounded-lg transition-colors ${isActive('/admin')}`}>
            <span className="text-gold">⚙ Admin</span>
          </Link>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2 ml-auto">
        {user ? (
          <>
            <Link to="/profil" className="hidden md:flex items-center gap-2 text-sm font-semibold text-zinc-300 hover:text-white transition-colors">
              <div className="w-7 h-7 rounded-full bg-gold-dim flex items-center justify-center text-gold font-bold text-xs">
                {user.name[0].toUpperCase()}
              </div>
              <span className="hidden lg:block">{user.name}</span>
            </Link>
            <button onClick={handleLogout} className="btn-outline text-xs px-3 py-1.5">
              Abmelden
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className="btn-ghost text-xs">Anmelden</Link>
            <Link to="/register" className="btn-gold text-xs">Registrieren</Link>
          </>
        )}

        {/* Mobile menu button */}
        <button
          className="md:hidden p-1.5 rounded-lg hover:bg-surface-2 transition-colors"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {menuOpen
              ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            }
          </svg>
        </button>
      </div>

      {/* Mobile Menu */}
      {menuOpen && (
        <div className="absolute top-14 left-0 right-0 bg-bg border-b border-surface-3 p-4 flex flex-col gap-2 md:hidden">
          <Link to="/rennen" onClick={() => setMenuOpen(false)} className="text-sm font-semibold py-2 text-zinc-300">Rennen</Link>
          <Link to="/leaderboard" onClick={() => setMenuOpen(false)} className="text-sm font-semibold py-2 text-zinc-300">Rangliste</Link>
          <Link to="/faq" onClick={() => setMenuOpen(false)} className="text-sm font-semibold py-2 text-zinc-300">FAQ</Link>
          {isAdmin && <Link to="/admin" onClick={() => setMenuOpen(false)} className="text-sm font-semibold py-2 text-gold">⚙ Admin-Dashboard</Link>}
          {user && <Link to="/profil" onClick={() => setMenuOpen(false)} className="text-sm font-semibold py-2 text-zinc-300">Mein Profil</Link>}
        </div>
      )}
    </nav>
  )
}
