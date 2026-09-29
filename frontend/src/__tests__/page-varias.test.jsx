/**
 * Páginas varias: Estadísticas, Ingresos y Gastos, Extras, Usuarios NNA,
 * Ajustes (configuration) y Usuarios del sistema (user_management).
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../hooks/useAuth.jsx'
import { EmpresaProvider } from '../hooks/useEmpresa.jsx'
import EstadisticasPage from '../pages/EstadisticasPage'
import IngresosGastosPage from '../pages/IngresosGastosPage'
import ExtrasPage from '../pages/ExtrasPage'
import UsuariosPage from '../pages/UsuariosPage'
import AjustesPage from '../pages/AjustesPage'
import UsuariosSistemaPage from '../pages/UsuariosSistemaPage'
import { renderWithProviders, mockApi, apiCalls, setSession, EMPRESA } from './helpers.jsx'

describe('EstadisticasPage', () => {
  it('admin: encabezado y petición de años', async () => {
    mockApi([{ path: '/estadisticas/anios', data: { anios: [] } }])
    renderWithProviders(<EstadisticasPage />, { rol: 'admin' })
    expect(screen.getByRole('heading', { name: 'Estadísticas' })).toBeInTheDocument()
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/estadisticas/anios')).toBe(true))
  })

  it('con años disponibles carga las estadísticas del primer año', async () => {
    mockApi([
      { path: '/estadisticas/anios', data: { anios: [2026] } },
      {
        path: '/estadisticas',
        data: {
          anio: 2026,
          meses: [],
          categorias_gasto: [],
          saldos_bancos: [],
          ingresos_total: 1000,
          gastos_total: 400,
        },
      },
    ])
    renderWithProviders(<EstadisticasPage />, { rol: 'admin' })
    expect(await screen.findByText('Ingresos 2026')).toBeInTheDocument()
    expect(screen.getByText('Gastos 2026')).toBeInTheDocument()
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/estadisticas' && c.params.anio === 2026)).toBe(true))
  })

  it('sin empresa lo indica', () => {
    renderWithProviders(<EstadisticasPage />, { empresa: null })
    expect(screen.getByText(/Selecciona una empresa para ver las estadísticas/)).toBeInTheDocument()
  })
})

describe('IngresosGastosPage', () => {
  it('encabezado, rango de fechas y botón Calcular', () => {
    const { container } = renderWithProviders(<IngresosGastosPage />, { rol: 'admin' })
    expect(screen.getByRole('heading', { name: 'Ingresos y Gastos' })).toBeInTheDocument()
    expect(container.querySelectorAll('input[type="date"]')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Calcular' })).toBeInTheDocument()
  })

  it('la consulta pide el periodo al backend y muestra el resultado', async () => {
    renderWithProviders(<IngresosGastosPage />, { rol: 'admin' })
    fireEvent.click(screen.getByRole('button', { name: 'Calcular' }))
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/estadisticas/periodo')).toBe(true))
    expect(await screen.findByRole('button', { name: 'Resumen' })).toBeInTheDocument()
    expect(screen.getAllByText('Ingresos').length).toBeGreaterThan(0)
  })

  it('la exportación usa fetch con token (FE-001), no window.open', async () => {
    URL.createObjectURL = () => 'blob:t'
    URL.revokeObjectURL = () => {}
    const prev = HTMLAnchorElement.prototype.click
    HTMLAnchorElement.prototype.click = function clickSpy() {}
    const fetchMock = vi.fn(async () => ({
      ok: true,
      blob: async () => new Blob(['x']),
      headers: { get: () => null },
    }))
    vi.stubGlobal('fetch', fetchMock)
    renderWithProviders(<IngresosGastosPage />, { rol: 'admin' })
    fireEvent.click(screen.getByRole('button', { name: 'Calcular' }))
    expect(await screen.findByRole('button', { name: 'Ingresos' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Ingresos' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Exportar a Excel' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/estadisticas/periodo/ingresos/export')
    expect(init.headers.Authorization).toBe('Bearer tk-test')
    HTMLAnchorElement.prototype.click = prev
    vi.unstubAllGlobals()
  })
})

describe('ExtrasPage', () => {
  const EXTRA = { id: 1, numero: 1, fecha: '2026-03-01', tipo: 'I', texto: 'Extra A', grupo: 'Obras', apuntes: [] }

  it('admin: encabezado, contador y controles de escritura', async () => {
    mockApi([{ path: '/extras', data: { total: 1, items: [EXTRA] } }])
    renderWithProviders(<ExtrasPage />, { rol: 'admin' })
    expect(screen.getByRole('heading', { name: 'Extras' })).toBeInTheDocument()
    expect(await screen.findByText('Extra A')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ Nuevo extra' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Renumerar' })).toBeInTheDocument()
    expect(screen.getByText('1 extra')).toBeInTheDocument()
  })

  it('solo_lectura: sin Nuevo ni Renumerar', async () => {
    mockApi([{ path: '/extras', data: { total: 0, items: [] } }])
    renderWithProviders(<ExtrasPage />, { rol: 'solo_lectura' })
    expect(await screen.findByText('0 extras')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '+ Nuevo extra' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Renumerar' })).not.toBeInTheDocument()
  })
})

describe('UsuariosPage (NNA)', () => {
  it('admin: encabezado, listado y Nuevo usuario', async () => {
    mockApi([
      {
        path: '/usuarios',
        data: {
          total: 1,
          items: [{ id: 1, numero: 7, nombre: 'Lucía', apellidos: 'Paz', paga_mensual: 50, activo: true }],
        },
      },
      { path: '/usuarios/pagas/anios', data: { anios: [] } },
    ])
    renderWithProviders(<UsuariosPage />, { rol: 'admin' })
    expect(screen.getByRole('heading', { name: 'Usuarios NNA' })).toBeInTheDocument()
    expect(await screen.findByText(/Lucía/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ Nuevo usuario' })).toBeInTheDocument()
  })

  it('solo_lectura: sin Nuevo usuario', async () => {
    mockApi([
      { path: '/usuarios', data: { total: 0, items: [] } },
      { path: '/usuarios/pagas/anios', data: { anios: [] } },
    ])
    renderWithProviders(<UsuariosPage />, { rol: 'solo_lectura' })
    expect(await screen.findByRole('heading', { name: 'Usuarios NNA' })).toBeInTheDocument()
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/usuarios')).toBe(true))
    expect(screen.queryByRole('button', { name: '+ Nuevo usuario' })).not.toBeInTheDocument()
  })
})

describe('AjustesPage', () => {
  it('admin: encabezado, pestañas y datos de la empresa', async () => {
    mockApi([{ path: /^\/empresas\/1$/, data: { id: 1, nombre: 'Empresa 1', codigo: 'E1', nif: '' } }])
    renderWithProviders(<AjustesPage />, { rol: 'admin' })
    expect(screen.getByRole('heading', { name: 'Ajustes' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Empresa' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Copias de seguridad' })).toBeInTheDocument()
    expect(await screen.findByDisplayValue('Empresa 1')).toBeInTheDocument()
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/empresas/1')).toBe(true))
  })

  it('la pestaña de copias pide la lista de backups', async () => {
    mockApi([
      { path: /^\/empresas\/1$/, data: { id: 1, nombre: 'Empresa 1', codigo: 'E1' } },
      {
        path: '/ajustes/backups',
        data: {
          backups: [{ nombre: 'a.db', fecha: '2026-01-01', tamano: 10 }],
          hora: '02:00',
          dias: [0],
          retencion_dias: 30,
        },
      },
    ])
    renderWithProviders(<AjustesPage />, { rol: 'admin' })
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/empresas/1')).toBe(true))
    fireEvent.click(screen.getByRole('button', { name: 'Copias de seguridad' }))
    expect(await screen.findByText('a.db')).toBeInTheDocument()
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/ajustes/backups')).toBe(true))
  })
})

describe('UsuariosSistemaPage', () => {
  function renderPagina(rol = 'admin') {
    setSession({ rol, empresa: EMPRESA })
    return render(
      <MemoryRouter>
        <AuthProvider>
          <EmpresaProvider>
            <UsuariosSistemaPage />
          </EmpresaProvider>
        </AuthProvider>
      </MemoryRouter>,
    )
  }

  it('lista los usuarios del sistema', async () => {
    mockApi([
      {
        path: '/auth/usuarios',
        data: {
          total: 1,
          items: [{ id: 1, username: 'root', nombre: 'Root', rol: 'admin', activo: true, empresa_id: null }],
        },
      },
    ])
    renderPagina()
    expect(screen.getByRole('heading', { name: 'Usuarios del sistema' })).toBeInTheDocument()
    expect(await screen.findByText('root')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ Nuevo usuario' })).toBeInTheDocument()
  })

  it('abre el modal de alta', async () => {
    mockApi([{ path: '/auth/usuarios', data: { total: 0, items: [] } }])
    renderPagina()
    await screen.findByRole('button', { name: '+ Nuevo usuario' })
    fireEvent.click(screen.getByRole('button', { name: '+ Nuevo usuario' }))
    expect(await screen.findByText('Nuevo usuario')).toBeInTheDocument()
  })

  it('error de carga: mensaje de error', async () => {
    mockApi([{ path: '/auth/usuarios', status: 500, data: { detail: 'boom' } }])
    renderPagina()
    expect(await screen.findByText('Error al cargar usuarios')).toBeInTheDocument()
  })
})
