import api from './api'

const BASE = '/bancos'

// ── Cuentas bancarias ────────────────────────────────────────────────────────

export const getBancos = (empresa_id) => api.get(BASE, { params: { empresa_id } }).then((r) => r.data)

export const createBanco = (data) => api.post(BASE, data).then((r) => r.data)

export const updateBanco = (id, data) => api.put(`${BASE}/${id}`, data).then((r) => r.data)

export const deleteBanco = (id) => api.delete(`${BASE}/${id}`)

export const repararSaldosBanco = (id) => api.post(`${BASE}/${id}/reparar_saldos`).then((r) => r.data)

// ── Movimientos ──────────────────────────────────────────────────────────────

export const getMovimientos = (params) => api.get(`${BASE}/movimientos/lista`, { params }).then((r) => r.data)

export const createMovimiento = (data) => api.post(`${BASE}/movimientos`, data).then((r) => r.data)

export const updateMovimiento = (id, data) => api.put(`${BASE}/movimientos/${id}`, data).then((r) => r.data)

export const deleteMovimiento = (id) => api.delete(`${BASE}/movimientos/${id}`)

export const reordenarMovimiento = (id, direccion) =>
  api.post(`${BASE}/movimientos/${id}/reordenar`, { direccion }).then((r) => r.data)

// ── Vencimientos ─────────────────────────────────────────────────────────────

export const getVencimientos = (params) => api.get(`${BASE}/vencimientos/lista`, { params }).then((r) => r.data)

export const createVencimiento = (data) => api.post(`${BASE}/vencimientos`, data).then((r) => r.data)

export const updateVencimiento = (id, data) => api.put(`${BASE}/vencimientos/${id}`, data).then((r) => r.data)
