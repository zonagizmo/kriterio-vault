export { fmtFecha, hoy } from '../../utils/format'

/** Formato contable sin símbolo: 1.234,56 */
export const EUR = (v) => Number(v ?? 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const anioActual = new Date().getFullYear()
