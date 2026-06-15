import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { useToast, Toaster } from './components/Toast'
import Navbar from './components/Navbar'
import { ProtectedRoute } from './components/ProtectedRoute'

import Landing      from './pages/Landing'
import Login        from './pages/Login'
import Register     from './pages/Register'
import Rennen       from './pages/Rennen'
import RennAnmelden from './pages/RennAnmelden'
import Leaderboard  from './pages/Leaderboard'
import LeaderboardTV from './pages/LeaderboardTV'
import Profil       from './pages/Profil'
import Admin        from './pages/Admin'
import Kamera       from './pages/Kamera'
import FAQ          from './pages/FAQ'
import Impressum    from './pages/Impressum'

function AppInner() {
  const { toasts } = useToast()
  const location = useLocation()
  const isTV = location.pathname.startsWith('/leaderboard/tv')
  return (
    <>
      {!isTV && <Navbar />}
      <main>
        <Routes>
          <Route path="/"                  element={<Landing />} />
          <Route path="/login"             element={<Login />} />
          <Route path="/register"          element={<Register />} />
          <Route path="/rennen"            element={<Rennen />} />
          <Route path="/rennen/:id/anmelden" element={
            <ProtectedRoute><RennAnmelden /></ProtectedRoute>
          } />
          <Route path="/leaderboard"       element={<Leaderboard />} />
          <Route path="/leaderboard/:id"   element={<Leaderboard />} />
          <Route path="/leaderboard/tv/:id" element={<LeaderboardTV />} />
          <Route path="/profil"            element={
            <ProtectedRoute><Profil /></ProtectedRoute>
          } />
          <Route path="/admin"             element={
            <ProtectedRoute adminOnly><Admin /></ProtectedRoute>
          } />
          <Route path="/kamera/:id"        element={
            <ProtectedRoute adminOnly><Kamera /></ProtectedRoute>
          } />
          <Route path="/faq"               element={<FAQ />} />
          <Route path="/impressum"         element={<Impressum />} />
          <Route path="*"                  element={
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
              <div className="text-6xl mb-4">🏁</div>
              <h1 className="text-2xl font-black mb-2">404 — Seite nicht gefunden</h1>
              <a href="/" className="btn-gold mt-4">Zur Startseite</a>
            </div>
          } />
        </Routes>
      </main>
      <Toaster toasts={toasts} />
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppInner />
      </AuthProvider>
    </BrowserRouter>
  )
}
