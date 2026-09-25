import api from './api'

const BASE = '/contabilidad'

// ── Plan de cuentas ──────────────────────────────────────────────────────────

export const getCuentas = (params) => api.get(`${BASE}/cuentas`, { params }).then((r) => r.data)

export const createCuenta = (data) => api.post(`${BASE}/cuentas`, data).then((r) => r.data)

export const updateCuenta = (id, data) => api.put(`${BASE}/cuentas/${id}`, data).then((r) => r.data)

export const deleteCuenta = (id) => api.delete(`${BASE}/cuentas/${id}`)

// ── Asientos del diario ──────────────────────────────────────────────────────

export const getAsientos = (params) => api.get(`${BASE}/asientos`, { params }).then((r) => r.data)

export const getAsiento = (num, empresa_id) =>
  api.get(`${BASE}/asientos/${num}`, { params: { empresa_id } }).then((r) => r.data)

export const createAsiento = (data) => api.post(`${BASE}/asientos`, data).then((r) => r.data)

export const updateAsiento = (num, data) => api.put(`${BASE}/asientos/${num}`, data).then((r) => r.data)

export const deleteAsiento = (num, empresa_id, force = false) =>
  api.delete(`${BASE}/asientos/${num}`, { params: { empresa_id, force } })

// ── Libro mayor ──────────────────────────────────────────────────────────────

export const getMayor = (params) => api.get(`${BASE}/mayor`, { params }).then((r) => r.data)

// ── Generación automática ─────────────────────────────────────────────────────

export const generarPendientes = (empresa_id) =>
  api.post(`${BASE}/generar-pendientes`, null, { params: { empresa_id } }).then((r) => r.data)

export const getDiagnostico = (empresa_id) =>
  api.get(`${BASE}/diagnostico`, { params: { empresa_id } }).then((r) => r.data)

// ── Informes ──────────────────────────────────────────────────────────────────

export const getSumasSaldos = (params) => api.get(`${BASE}/sumas-saldos`, { params }).then((r) => r.data)

export const getPyG = (params) => api.get(`${BASE}/pyg`, { params }).then((r) => r.data)

export const getConciliacion = (empresa_id) =>
  api.get(`${BASE}/conciliacion-bancos`, { params: { empresa_id } }).then((r) => r.data)

export const regenerarAsientoBanco = (empresa_id, banco, numero) =>
  api.post(`${BASE}/regenerar-asiento-banco`, null, { params: { empresa_id, banco, numero } }).then((r) => r.data)

// ── Balance de situación ──────────────────────────────────────────────────────

export const getBalance = (params) => api.get(`${BASE}/balance`, { params }).then((r) => r.data)

// ── Cierre de ejercicio ───────────────────────────────────────────────────────

export const realizarCierre = (empresa_id, anio, crear_apertura = true) =>
  api.post(`${BASE}/cierre`, null, { params: { empresa_id, anio, crear_apertura } }).then((r) => r.data)

// ── Exportar CSV ──────────────────────────────────────────────────────────────

export const exportarCSV = (tipo, params) => {
  const url = new URL(`${window.location.origin}${BASE}/export/${tipo}`)
  Object.entries(params).forEach(([k, v]) => {
    if (v != null) url.searchParams.set(k, v)
  })
  window.open(url.toString(), '_blank')
}
