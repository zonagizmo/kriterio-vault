import axios from 'axios'

const BASE = '/api/extras'

export const getExtras = (params) =>
  axios.get(BASE, { params }).then((r) => r.data)

export const getExtra = (id) =>
  axios.get(`${BASE}/${id}`).then((r) => r.data)

export const createExtra = (data) =>
  axios.post(BASE, data).then((r) => r.data)

export const updateExtra = (id, data) =>
  axios.put(`${BASE}/${id}`, data).then((r) => r.data)

export const deleteExtra = (id) =>
  axios.delete(`${BASE}/${id}`)

export const renumerarExtras = (empresa_id, desde_id = null) =>
  axios.post(`${BASE}/renumerar`, { empresa_id, desde_id }).then((r) => r.data)
