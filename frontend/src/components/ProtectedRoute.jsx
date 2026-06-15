import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gold animate-pulse text-2xl">🏁</div>
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && user.rolle !== 'admin') return <Navigate to="/" replace />
  return children
}
