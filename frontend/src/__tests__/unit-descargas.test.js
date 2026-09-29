/**
 * Regresión FE-001: los exports/descargas usan fetch con Bearer + blob
 * (nunca window.open, que no envía Authorization).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { descargar, descargarOVisar } from '../services/descargas'
import { setSession } from './helpers.jsx'

let clickSpy

beforeEach(() => {
  setSession()
  URL.createObjectURL = vi.fn(() => 'blob:demo')
  URL.revokeObjectURL = vi.fn()
  clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
})

afterEach(() => {
  delete URL.createObjectURL
  delete URL.revokeObjectURL
})

function respuestaOk({ blob, cd } = {}) {
  return {
    ok: true,
    status: 200,
    blob: async () => blob ?? new Blob(['contenido']),
    headers: { get: (h) => (h === 'Content-Disposition' ? (cd ?? null) : null) },
  }
}

describe('descargar', () => {
  it('envía el Authorization con el token vigente', async () => {
    const fetchMock = vi.fn(async () => respuestaOk())
    vi.stubGlobal('fetch', fetchMock)
    await descargar('/api/estadisticas/export', 'estadisticas.csv')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/estadisticas/export')
    expect(init.headers.Authorization).toBe('Bearer tk-test')
  })

  it('sin token no lleva cabecera Authorization', async () => {
    localStorage.removeItem('kriterio_token')
    const fetchMock = vi.fn(async () => respuestaOk())
    vi.stubGlobal('fetch', fetchMock)
    await descargar('/api/x', 'x.csv')
    expect(fetchMock.mock.calls[0][1].headers).toEqual({})
  })

  it('usa el nombre del Content-Disposition del backend', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => respuestaOk({ cd: 'attachment; filename="informe-2026.csv"' })),
    )
    await descargar('/api/x', 'por-defecto.csv')
    expect(clickSpy).toHaveBeenCalledTimes(1)
    // el <a> temporal se crea, se pulsa y se elimina del DOM
    expect(document.querySelectorAll('a[download]')).toHaveLength(0)
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:demo')
  })

  it('usa el nombre por defecto si no hay Content-Disposition', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => respuestaOk()),
    )
    await descargar('/api/backups/descargar', 'backup.db')
    expect(clickSpy).toHaveBeenCalledTimes(1)
  })

  it('respuesta 404 con detail del backend → Error(detail)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Recurso no encontrado' }),
      })),
    )
    await expect(descargar('/api/x', 'x')).rejects.toThrow('Recurso no encontrado')
    expect(clickSpy).not.toHaveBeenCalled()
  })

  it('respuesta 500 sin detail → Error("Error 500")', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('no json')
        },
      })),
    )
    await expect(descargar('/api/x', 'x')).rejects.toThrow('Error 500')
  })
})

describe('descargarOVisar', () => {
  it('en éxito no avisa', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => respuestaOk()),
    )
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    await descargarOVisar('/api/x', 'x')
    expect(alertSpy).not.toHaveBeenCalled()
  })

  it('en fallo avisa con alert (patrón de la app)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 403,
        json: async () => ({ detail: 'Sin permiso' }),
      })),
    )
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    await descargarOVisar('/api/x', 'x')
    expect(alertSpy).toHaveBeenCalledWith('Sin permiso')
  })
})
