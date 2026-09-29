import api from './api'
import { descargarOVisar } from './descargas'

const BASE = '/usuarios'

export const getUsuarios = (params) => api.get(BASE, { params }).then((r) => r.data)

export const createUsuario = (data) => api.post(BASE, data).then((r) => r.data)

export const updateUsuario = (id, data) => api.put(`${BASE}/${id}`, data).then((r) => r.data)

export const deleteUsuario = (id) => api.delete(`${BASE}/${id}`)

export const getActivosConPaga = (empresa_id) =>
  api.get(`${BASE}/activos-con-paga`, { params: { empresa_id } }).then((r) => r.data)

export const getPagas = (params) => api.get(`${BASE}/pagas`, { params }).then((r) => r.data)

export const createPaga = (data) => api.post(`${BASE}/pagas`, data).then((r) => r.data)

export const deletePaga = (id) => api.delete(`${BASE}/pagas/${id}`)

export const registrarMes = (data) => api.post(`${BASE}/pagas/mes`, data).then((r) => r.data)

export const getResumenPagas = (params) => api.get(`${BASE}/pagas/resumen`, { params }).then((r) => r.data)

export const getAniosPagas = (empresa_id) =>
  api.get(`${BASE}/pagas/anios`, { params: { empresa_id } }).then((r) => r.data)

export const getResumenPagasAnual = (empresa_id, anio) =>
  api.get(`${BASE}/pagas/resumen-anual`, { params: { empresa_id, anio } }).then((r) => r.data)

export const exportarResumenPagasAnual = (empresa_id, anio, format = 'xlsx') => {
  const qs = new URLSearchParams({ empresa_id, anio, format })
  return descargarOVisar(`/api${BASE}/pagas/resumen-anual/export?${qs}`, `resumen_pagas_${anio}.${format}`)
}

export const getSaldosNNA = (empresa_id) => api.get(`${BASE}/saldos`, { params: { empresa_id } }).then((r) => r.data)

export const exportarPagas = (params, format = 'xlsx') => {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== '') qs.append(k, v)
  })
  qs.set('format', format)
  return descargarOVisar(`/api${BASE}/pagas/export?${qs}`, `pagas.${format}`)
}
