import axios from 'axios'

const BASE = '/api/contabilidad'

// ── Plan de cuentas ──────────────────────────────────────────────────────────

export const getCuentas = (params) =>
  axios.get(`${BASE}/cuentas`, { params }).then((r) => r.data)

export const createCuenta = (data) =>
  axios.post(`${BASE}/cuentas`, data).then((r) => r.data)

export const updateCuenta = (id, data) =>
  axios.put(`${BASE}/cuentas/${id}`, data).then((r) => r.data)

export const deleteCuenta = (id) =>
  axios.delete(`${BASE}/cuentas/${id}`)

// ── Asientos del diario ──────────────────────────────────────────────────────

export const getAsientos = (params) =>
  axios.get(`${BASE}/asientos`, { params }).then((r) => r.data)

export const getAsiento = (num, empresa_id) =>
  axios.get(`${BASE}/asientos/${num}`, { params: { empresa_id } }).then((r) => r.data)

export const createAsiento = (data) =>
  axios.post(`${BASE}/asientos`, data).then((r) => r.data)

export const updateAsiento = (num, data) =>
  axios.put(`${BASE}/asientos/${num}`, data).then((r) => r.data)

export const deleteAsiento = (num, empresa_id, force = false) =>
  axios.delete(`${BASE}/asientos/${num}`, { params: { empresa_id, force } })

// ── Libro mayor ──────────────────────────────────────────────────────────────

export const getMayor = (params) =>
  axios.get(`${BASE}/mayor`, { params }).then((r) => r.data)

// ── Generación automática ─────────────────────────────────────────────────────

export const generarPendientes = (empresa_id) =>
  axios.post(`${BASE}/generar-pendientes`, null, { params: { empresa_id } }).then((r) => r.data)

export const getDiagnostico = (empresa_id) =>
  axios.get(`${BASE}/diagnostico`, { params: { empresa_id } }).then((r) => r.data)

// ── Informes ──────────────────────────────────────────────────────────────────

export const getSumasSaldos = (params) =>
  axios.get(`${BASE}/sumas-saldos`, { params }).then((r) => r.data)

export const getPyG = (params) =>
  axios.get(`${BASE}/pyg`, { params }).then((r) => r.data)

export const getConciliacion = (empresa_id) =>
  axios.get(`${BASE}/conciliacion-bancos`, { params: { empresa_id } }).then((r) => r.data)

export const regenerarAsientoBanco = (empresa_id, banco, numero) =>
  axios.post(`${BASE}/regenerar-asiento-banco`, null, { params: { empresa_id, banco, numero } }).then((r) => r.data)

// ── Balance de situación ──────────────────────────────────────────────────────

export const getBalance = (params) =>
  axios.get(`${BASE}/balance`, { params }).then((r) => r.data)

// ── Cierre de ejercicio ───────────────────────────────────────────────────────

export const realizarCierre = (empresa_id, anio, crear_apertura = true) =>
  axios.post(`${BASE}/cierre`, null, { params: { empresa_id, anio, crear_apertura } }).then((r) => r.data)

// ── Exportar CSV ──────────────────────────────────────────────────────────────

export const exportarCSV = (tipo, params) => {
  const url = new URL(`${window.location.origin}${BASE}/export/${tipo}`)
  Object.entries(params).forEach(([k, v]) => { if (v != null) url.searchParams.set(k, v) })
  window.open(url.toString(), '_blank')
}
