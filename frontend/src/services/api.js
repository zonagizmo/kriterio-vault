import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let _redirectingToLogin = false

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !_redirectingToLogin) {
      _redirectingToLogin = true
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_refresh_token')
      localStorage.removeItem('auth_user')
      localStorage.removeItem('empresa_activa')
      window.location.href = '/login'
      return Promise.reject(err)
    }

    const detail = err.response?.data?.detail
    const msg = (typeof detail === 'string' ? detail : detail?.mensaje) || err.message || 'Error de red'
    const error = new Error(msg)
    if (detail && typeof detail === 'object') error.detail = detail
    return Promise.reject(error)
  }
)

export default api
