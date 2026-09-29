/** Formatos compartidos (utils/format.js). */
import { describe, it, expect } from 'vitest'
import { EUR, EUR0, EURplain, fmtFecha, hoy } from '../utils/format'

describe('EUR', () => {
  it('formatea moneda con decimales', () => {
    expect(EUR(1234.56)).toBe(new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(1234.56))
  })
  it('null/undefined → 0', () => {
    expect(EUR(null)).toContain('0,00')
    expect(EUR(undefined)).toContain('0,00')
  })
})

describe('EUR0', () => {
  it('sin decimales y con símbolo €', () => {
    const s = EUR0(1234.56)
    expect(s).toContain('1235')
    expect(s).not.toContain('1235,')
    expect(s.endsWith('€')).toBe(true)
  })
  it('agrupa millares a partir de 5 cifras', () => {
    expect(EUR0(12345.4)).toContain('12.345')
  })
})

describe('EURplain', () => {
  it('solo número con 2 decimales', () => {
    expect(EURplain(12345.5)).toBe('12.345,50')
  })
  it('null → 0,00', () => {
    expect(EURplain(null)).toBe('0,00')
  })
})

describe('fmtFecha', () => {
  it('ISO → dd/mm/yyyy', () => {
    expect(fmtFecha('2026-03-05')).toBe('05/03/2026')
  })
  it('vacío → cadena vacía', () => {
    expect(fmtFecha('')).toBe('')
    expect(fmtFecha(null)).toBe('')
    expect(fmtFecha(undefined)).toBe('')
  })
})

describe('hoy', () => {
  it('devuelve YYYY-MM-DD', () => {
    expect(hoy()).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})
