import axios from 'axios'

const BASE = '/api/usuarios'

export const getUsuarios = (params) =>
  axios.get(BASE, { params }).then((r) => r.data)

export const createUsuario = (data) =>
  axios.post(BASE, data).then((r) => r.data)

export const updateUsuario = (id, data) =>
  axios.put(`${BASE}/${id}`, data).then((r) => r.data)

export const deleteUsuario = (id) =>
  axios.delete(`${BASE}/${id}`)

export const getActivosConPaga = (empresa_id) =>
  axios.get(`${BASE}/activos-con-paga`, { params: { empresa_id } }).then((r) => r.data)

export const getPagas = (params) =>
  axios.get(`${BASE}/pagas`, { params }).then((r) => r.data)

export const createPaga = (data) =>
  axios.post(`${BASE}/pagas`, data).then((r) => r.data)

export const deletePaga = (id) =>
  axios.delete(`${BASE}/pagas/${id}`)

export const registrarMes = (data) =>
  axios.post(`${BASE}/pagas/mes`, data).then((r) => r.data)

export const getResumenPagas = (params) =>
  axios.get(`${BASE}/pagas/resumen`, { params }).then((r) => r.data)

export const getAniosPagas = (empresa_id) =>
  axios.get(`${BASE}/pagas/anios`, { params: { empresa_id } }).then((r) => r.data)

export const getResumenPagasAnual = (empresa_id, anio) =>
  axios.get(`${BASE}/pagas/resumen-anual`, { params: { empresa_id, anio } }).then((r) => r.data)

export const exportarResumenPagasAnual = (empresa_id, anio, format = 'xlsx') => {
  const qs = new URLSearchParams({ empresa_id, anio, format })
  window.open(`${BASE}/pagas/resumen-anual/export?${qs}`, '_blank')
}

export const getSaldosNNA = (empresa_id) =>
  axios.get(`${BASE}/saldos`, { params: { empresa_id } }).then((r) => r.data)

export const exportarPagas = (params, format = 'xlsx') => {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') qs.append(k, v) })
  qs.set('format', format)
  window.open(`${BASE}/pagas/export?${qs}`, '_blank')
}
