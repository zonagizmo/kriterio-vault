import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const s = localStorage.getItem('auth_user')
      return s ? JSON.parse(s) : null
    } catch {
      return null
    }
  })
  const [token, setToken] = useState(() => localStorage.getItem('auth_token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      api.get('/auth/me')
        .then(r => {
          setUser(r.data)
          localStorage.setItem('auth_user', JSON.stringify(r.data))
        })
        .catch(() => {
          logout()
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = useCallback(async (username, password) => {
    const r = await api.post('/auth/login', { username, password })
    const { access_token, refresh_token, user: userData } = r.data
    localStorage.setItem('auth_token', access_token)
    localStorage.setItem('auth_refresh_token', refresh_token)
    localStorage.setItem('auth_user', JSON.stringify(userData))
    setToken(access_token)
    setUser(userData)
    return userData
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_refresh_token')
    localStorage.removeItem('auth_user')
    setToken(null)
    setUser(null)
  }, [])

  const cambiarPassword = useCallback(async (passwordActual, passwordNuevo) => {
    await api.put('/auth/cambiar-password', {
      password_actual: passwordActual,
      password_nuevo: passwordNuevo,
    })
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, cambiarPassword }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
