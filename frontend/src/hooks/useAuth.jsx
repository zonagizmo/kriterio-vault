import { createContext, useContext, useState } from 'react'
import { isAuthenticated, getUsuario, login as authLogin, logout as authLogout } from '../services/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => (isAuthenticated() ? getUsuario() : null))

  const login = async (username, password) => {
    const data = await authLogin(username, password)
    setUser(data.usuario)
    return data
  }

  const logout = () => {
    authLogout()
    setUser(null)
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
