import api from './api'

const params = (empresaId, opts = {}) => ({ empresa_id: empresaId, ...opts })

export const getFacturasEmi = (empresaId, opts) =>
  api.get('/facturas/emitidas', { params: params(empresaId, opts) }).then((r) => r.data)
export const getFacturaEmi   = (id) => api.get(`/facturas/emitidas/${id}`).then((r) => r.data)
export const createFacturaEmi = (data) => api.post('/facturas/emitidas', data).then((r) => r.data)
export const updateFacturaEmi = (id, data) => api.put(`/facturas/emitidas/${id}`, data).then((r) => r.data)
export const deleteFacturaEmi = (id) => api.delete(`/facturas/emitidas/${id}`)

export const getFacturasRec = (empresaId, opts) =>
  api.get('/facturas/recibidas', { params: params(empresaId, opts) }).then((r) => r.data)
export const getFacturaRec   = (id) => api.get(`/facturas/recibidas/${id}`).then((r) => r.data)
export const createFacturaRec = (data) => api.post('/facturas/recibidas', data).then((r) => r.data)
export const updateFacturaRec = (id, data) => api.put(`/facturas/recibidas/${id}`, data).then((r) => r.data)
export const deleteFacturaRec = (id) => api.delete(`/facturas/recibidas/${id}`)

export const renumerarFacturasEmi = (empresaId, desdeId = null) =>
  api.post('/facturas/emitidas/renumerar', { empresa_id: empresaId, desde_id: desdeId }).then((r) => r.data)
export const renumerarFacturasRec = (empresaId, desdeId = null) =>
  api.post('/facturas/recibidas/renumerar', { empresa_id: empresaId, desde_id: desdeId }).then((r) => r.data)
