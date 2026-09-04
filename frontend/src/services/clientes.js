import api from './api'

export const getClientes = (empresaId, { q = '', skip = 0, limit = 50 } = {}) =>
  api.get('/clientes', { params: { empresa_id: empresaId, q, skip, limit } }).then((r) => r.data)

export const getCliente = (id) => api.get(`/clientes/${id}`).then((r) => r.data)

export const createCliente = (data) => api.post('/clientes', data).then((r) => r.data)

export const updateCliente = (id, data) => api.put(`/clientes/${id}`, data).then((r) => r.data)

export const deleteCliente = (id) => api.delete(`/clientes/${id}`)
