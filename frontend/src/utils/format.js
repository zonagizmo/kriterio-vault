/**
 * Funciones de formato compartidas por todas las páginas.
 * Reemplaza las definiciones duplicadas de EUR, fmtFecha, hoy.
 */

/** Formato moneda EUR: 1.234,56 € */
export const EUR = (v) =>
  Number(v ?? 0).toLocaleString('es-ES', {
    style: 'currency',
    currency: 'EUR',
  })

/** Moneda EUR sin decimales: 1.235 € */
export const EUR0 = (v) =>
  Number(v ?? 0).toLocaleString('es-ES', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  })

/** Número con decimales sin símbolo: 1.234,56 */
export const EURplain = (v) => Number(v ?? 0).toLocaleString('es-ES', { minimumFractionDigits: 2 })

/** Fecha ISO (YYYY-MM-DD) → dd/mm/yyyy */
export const fmtFecha = (f) => {
  if (!f) return ''
  const [y, m, d] = String(f).split('-')
  return `${d}/${m}/${y}`
}

/** Fecha actual como string ISO: YYYY-MM-DD */
export const hoy = () => new Date().toISOString().slice(0, 10)
