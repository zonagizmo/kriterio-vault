import api from './api'

const BASE = '/extras'

export const getExtras = (params) => api.get(BASE, { params }).then((r) => r.data)

export const getExtra = (id) => api.get(`${BASE}/${id}`).then((r) => r.data)

export const createExtra = (data) => api.post(BASE, data).then((r) => r.data)

export const updateExtra = (id, data) => api.put(`${BASE}/${id}`, data).then((r) => r.data)

export const deleteExtra = (id) => api.delete(`${BASE}/${id}`)

export const renumerarExtras = (empresa_id, desde_id = null) =>
  api.post(`${BASE}/renumerar`, { empresa_id, desde_id }).then((r) => r.data)
