import api from './api'

export const getEmpresas = () => api.get('/empresas').then((r) => r.data)

export const getEmpresa = (id) => api.get(`/empresas/${id}`).then((r) => r.data)

export const actualizarEmpresa = (id, data) =>
  api.put(`/empresas/${id}`, data).then((r) => r.data)
