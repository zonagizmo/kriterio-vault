import api from './api'

export const getAniosEstadisticas = (empresaId) =>
  api.get('/estadisticas/anios', { params: { empresa_id: empresaId } }).then((r) => r.data)

export const getEstadisticas = (empresaId, anio) =>
  api.get('/estadisticas', { params: { empresa_id: empresaId, anio } }).then((r) => r.data)

export const getIngresosGastosPeriodo = (empresaId, fechaDesde, fechaHasta) =>
  api.get('/estadisticas/periodo', {
    params: { empresa_id: empresaId, fecha_desde: fechaDesde, fecha_hasta: fechaHasta },
  }).then((r) => r.data)

export const getListadoIngresos = (empresaId, fechaDesde, fechaHasta) =>
  api.get('/estadisticas/periodo/ingresos', {
    params: { empresa_id: empresaId, fecha_desde: fechaDesde, fecha_hasta: fechaHasta },
  }).then((r) => r.data)

export const getListadoGastos = (empresaId, fechaDesde, fechaHasta) =>
  api.get('/estadisticas/periodo/gastos', {
    params: { empresa_id: empresaId, fecha_desde: fechaDesde, fecha_hasta: fechaHasta },
  }).then((r) => r.data)

export const exportarListadoIngresos = (empresaId, fechaDesde, fechaHasta, format = 'xlsx') => {
  const qs = new URLSearchParams({ empresa_id: empresaId, fecha_desde: fechaDesde, fecha_hasta: fechaHasta, format })
  window.open(`/api/estadisticas/periodo/ingresos/export?${qs}`, '_blank')
}

export const exportarListadoGastos = (empresaId, fechaDesde, fechaHasta, format = 'xlsx') => {
  const qs = new URLSearchParams({ empresa_id: empresaId, fecha_desde: fechaDesde, fecha_hasta: fechaHasta, format })
  window.open(`/api/estadisticas/periodo/gastos/export?${qs}`, '_blank')
}
