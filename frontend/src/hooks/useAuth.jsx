import { createContext, useContext, useState, useEffect } from 'react'
import { isAuthenticated, getUsuario, login as authLogin, logout as authLogout } from '../services/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isAuthenticated()) {
      setUser(getUsuario())
    }
    setLoading(false)
  }, [])

  const login = async (username, password) => {
    const data = await authLogin(username, password)
    setUser(data.usuario)
    return data
  }

  const logout = () => {
    authLogout()
    setUser(null)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-mgd-900 flex items-center justify-center">
        <div className="text-mgd-100 opacity-60">Cargando...</div>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user }}>{children}</AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth debe usarse dentro de AuthProvider')
  }
  return context
}
