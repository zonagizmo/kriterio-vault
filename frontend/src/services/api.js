import axios from 'axios'
import { getToken, logout } from './auth'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url || ''
      if (!url.includes('/auth/login')) {
        logout()
        window.location.href = '/login'
        return Promise.reject(new Error('Sesión expirada'))
      }
    }
    const detail = err.response?.data?.detail
    const msg = (typeof detail === 'string' ? detail : detail?.mensaje) || err.message || 'Error de red'
    const error = new Error(msg)
    if (detail && typeof detail === 'object') error.detail = detail
    return Promise.reject(error)
  },
)

export default api
