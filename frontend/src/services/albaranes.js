import api from './api'

const params = (empresaId, opts = {}) => ({ empresa_id: empresaId, ...opts })

export const getAlbaranesEmi = (empresaId, opts) =>
  api.get('/albaranes/emitidos', { params: params(empresaId, opts) }).then((r) => r.data)
export const getAlbaranEmi   = (id) => api.get(`/albaranes/emitidos/${id}`).then((r) => r.data)
export const createAlbaranEmi = (data) => api.post('/albaranes/emitidos', data).then((r) => r.data)
export const updateAlbaranEmi = (id, data) => api.put(`/albaranes/emitidos/${id}`, data).then((r) => r.data)
export const deleteAlbaranEmi = (id) => api.delete(`/albaranes/emitidos/${id}`)

export const getAlbaranesRec = (empresaId, opts) =>
  api.get('/albaranes/recibidos', { params: params(empresaId, opts) }).then((r) => r.data)
export const getAlbaranRec   = (id) => api.get(`/albaranes/recibidos/${id}`).then((r) => r.data)
export const createAlbaranRec = (data) => api.post('/albaranes/recibidos', data).then((r) => r.data)
export const updateAlbaranRec = (id, data) => api.put(`/albaranes/recibidos/${id}`, data).then((r) => r.data)
export const deleteAlbaranRec = (id) => api.delete(`/albaranes/recibidos/${id}`)
