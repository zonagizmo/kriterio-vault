import api from './api'

export const getFamilias = (empresaId) =>
  api.get('/familias', { params: { empresa_id: empresaId } }).then((r) => r.data)

export const createFamilia = (data) => api.post('/familias', data).then((r) => r.data)
export const updateFamilia = (id, data) => api.put(`/familias/${id}`, data).then((r) => r.data)
export const deleteFamilia = (id) => api.delete(`/familias/${id}`)
