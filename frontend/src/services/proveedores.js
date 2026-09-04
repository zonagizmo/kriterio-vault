import api from './api'

export const getProveedores = (empresaId, { q = '', skip = 0, limit = 50 } = {}) =>
  api.get('/proveedores', { params: { empresa_id: empresaId, q, skip, limit } }).then((r) => r.data)

export const getProveedor = (id) => api.get(`/proveedores/${id}`).then((r) => r.data)

export const createProveedor = (data) => api.post('/proveedores', data).then((r) => r.data)

export const updateProveedor = (id, data) => api.put(`/proveedores/${id}`, data).then((r) => r.data)

export const deleteProveedor = (id) => api.delete(`/proveedores/${id}`)
