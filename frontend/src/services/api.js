import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const detail = err.response?.data?.detail
    const msg = (typeof detail === 'string' ? detail : detail?.mensaje) || err.message || 'Error de red'
    const error = new Error(msg)
    if (detail && typeof detail === 'object') error.detail = detail
    return Promise.reject(error)
  }
)

export default api
