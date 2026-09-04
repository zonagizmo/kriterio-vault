import api from './api'

export const getDashboard = (empresaId) =>
  api.get('/dashboard', { params: { empresa_id: empresaId } }).then((r) => r.data)
