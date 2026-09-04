import axios from 'axios'

const BASE = '/api/bancos'

// ── Cuentas bancarias ────────────────────────────────────────────────────────

export const getBancos = (empresa_id) =>
  axios.get(BASE, { params: { empresa_id } }).then((r) => r.data)

export const createBanco = (data) =>
  axios.post(BASE, data).then((r) => r.data)

export const updateBanco = (id, data) =>
  axios.put(`${BASE}/${id}`, data).then((r) => r.data)

export const deleteBanco = (id) =>
  axios.delete(`${BASE}/${id}`)

export const repararSaldosBanco = (id) =>
  axios.post(`${BASE}/${id}/reparar_saldos`).then((r) => r.data)

// ── Movimientos ──────────────────────────────────────────────────────────────

export const getMovimientos = (params) =>
  axios.get(`${BASE}/movimientos/lista`, { params }).then((r) => r.data)

export const createMovimiento = (data) =>
  axios.post(`${BASE}/movimientos`, data).then((r) => r.data)

export const updateMovimiento = (id, data) =>
  axios.put(`${BASE}/movimientos/${id}`, data).then((r) => r.data)

export const deleteMovimiento = (id) =>
  axios.delete(`${BASE}/movimientos/${id}`)

export const reordenarMovimiento = (id, direccion) =>
  axios.post(`${BASE}/movimientos/${id}/reordenar`, { direccion }).then((r) => r.data)

// ── Vencimientos ─────────────────────────────────────────────────────────────

export const getVencimientos = (params) =>
  axios.get(`${BASE}/vencimientos/lista`, { params }).then((r) => r.data)

export const createVencimiento = (data) =>
  axios.post(`${BASE}/vencimientos`, data).then((r) => r.data)

export const updateVencimiento = (id, data) =>
  axios.put(`${BASE}/vencimientos/${id}`, data).then((r) => r.data)
