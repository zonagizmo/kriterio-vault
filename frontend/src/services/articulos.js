import api from './api'

export const getArticulos = (empresaId, { q = '', familia = null, skip = 0, limit = 50 } = {}) =>
  api.get('/articulos', { params: { empresa_id: empresaId, q, familia, skip, limit } }).then((r) => r.data)

export const getArticulo = (id) => api.get(`/articulos/${id}`).then((r) => r.data)
export const createArticulo = (data) => api.post('/articulos', data).then((r) => r.data)
export const updateArticulo = (id, data) => api.put(`/articulos/${id}`, data).then((r) => r.data)
export const deleteArticulo = (id) => api.delete(`/articulos/${id}`)
