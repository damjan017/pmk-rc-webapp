import { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('rally_token')
    if (!token) { setLoading(false); return }
    api.me()
      .then(setUser)
      .catch(() => localStorage.removeItem('rally_token'))
      .finally(() => setLoading(false))
  }, [])

  function login(data) {
    localStorage.setItem('rally_token', data.token)
    setUser({ id: data.id, name: data.name, email: data.email, rolle: data.rolle })
  }

  function logout() {
    api.logout().catch(() => {})
    localStorage.removeItem('rally_token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAdmin: user?.rolle === 'admin' }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
