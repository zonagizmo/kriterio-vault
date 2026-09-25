import api from './api'

const TOKEN_KEY = 'kriterio_token'
const USER_KEY = 'kriterio_user'

export const login = async (username, password) => {
  const { data } = await api.post('/auth/login', { username, password })
  localStorage.setItem(TOKEN_KEY, data.access_token)
  localStorage.setItem(USER_KEY, JSON.stringify(data.usuario))
  return data
}

export const logout = () => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export const getToken = () => localStorage.getItem(TOKEN_KEY)

export const getUsuario = () => {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY))
  } catch {
    return null
  }
}

export const isAuthenticated = () => !!getToken()

// ── Password ────────────────────────────────────────────────────────────────

export const cambiarPassword = (password_actual, password_nuevo) =>
  api.post('/auth/cambiar-password', { password_actual, password_nuevo }).then((r) => r.data)

// ── Gestión de usuarios (admin) ─────────────────────────────────────────────

export const getUsuariosSistema = () => api.get('/auth/usuarios').then((r) => r.data)

export const createUsuarioSistema = (data) => api.post('/auth/usuarios', data).then((r) => r.data)

export const updateUsuarioSistema = (id, data) => api.put(`/auth/usuarios/${id}`, data).then((r) => r.data)

export const resetPasswordUsuario = (id, password_nuevo) =>
  api.post(`/auth/usuarios/${id}/reset-password`, { password_nuevo }).then((r) => r.data)

export const deleteUsuarioSistema = (id) => api.delete(`/auth/usuarios/${id}`).then((r) => r.data)
