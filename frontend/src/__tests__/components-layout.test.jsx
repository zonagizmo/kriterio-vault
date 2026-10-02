/** Layout: navegación filtrada por rol (§4/§7 de SECURITY.md). */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import Layout from '../components/Layout'
import { renderWithProviders, setSession, mockApi, apiCalls } from './helpers.jsx'

function renderLayout(rol, opts = {}) {
  return renderWithProviders(
    <Layout>
      <div>contenido</div>
    </Layout>,
    { rol, ...opts },
  )
}

describe('Layout — sesión y empresa', () => {
  it('muestra la empresa activa, el usuario y la versión', () => {
    renderLayout('admin')
    expect(screen.getByText('Empresa 1')).toBeInTheDocument()
    expect(screen.getByText('E1')).toBeInTheDocument()
    expect(screen.getByText('Tester')).toBeInTheDocument()
    expect(screen.getByText(/v\d+\.\d+\.\d+/)).toBeInTheDocument()
    expect(screen.getByText('contenido')).toBeInTheDocument()
  })

  it('"Cambiar empresa" limpia la empresa activa', () => {
    renderLayout('admin')
    expect(localStorage.getItem('empresa_activa')).not.toBeNull()
    fireEvent.click(screen.getByText('← Cambiar empresa'))
    expect(localStorage.getItem('empresa_activa')).toBeNull()
  })

  it('"Salir" cierra la sesión', () => {
    renderLayout('admin')
    fireEvent.click(screen.getByTitle('Cerrar sesión'))
    expect(localStorage.getItem('kriterio_token')).toBeNull()
    expect(localStorage.getItem('kriterio_user')).toBeNull()
  })
})

describe('Layout — navegación por rol', () => {
  const navBasica = ['Inicio', 'Bancos', 'Clientes', 'Facturas', 'Estadísticas']

  it('admin global ve Ajustes, Usuarios del sistema y Apagar', () => {
    renderLayout('admin', { empresa: null })
    for (const item of navBasica) expect(screen.getByRole('link', { name: new RegExp(item) })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Ajustes/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Usuarios del sistema/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Apagar/ })).toBeInTheDocument()
  })

  it('admin CON empresa asignada: no ve Apagar (NUE-001)', () => {
    renderLayout('admin') // sesión con empresa_id = 1
    expect(screen.getByRole('link', { name: /Ajustes/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Usuarios del sistema/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Apagar/ })).not.toBeInTheDocument()
  })

  it('operador: sin Ajustes, sin Usuarios del sistema, sin Apagar', () => {
    renderLayout('operador')
    expect(screen.getByRole('link', { name: /Clientes/ })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Ajustes/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Usuarios del sistema/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Apagar/ })).not.toBeInTheDocument()
  })

  it('solo_lectura: mismo menú de operador (solo cambian los controles)', () => {
    renderLayout('solo_lectura')
    expect(screen.getByRole('link', { name: /Facturas/ })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Ajustes/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Usuarios del sistema/ })).not.toBeInTheDocument()
  })

  it('la ruta /ajustes solo aparece con configuration', () => {
    setSession({ rol: 'operador' })
    renderLayout('operador')
    expect(screen.queryByRole('link', { name: /Ajustes/ })).not.toBeInTheDocument()
  })
})

describe('BotonApagar — NUE-001 (solo administrador global)', () => {
  // window.close() en jsdom cierra la ventana de pruebas y rompe el resto
  // del fichero (localStorage/cleanup): se sustituye por un espía.
  let closeReal
  beforeEach(() => {
    closeReal = window.close
    window.close = vi.fn()
  })
  afterEach(() => {
    window.close = closeReal
  })

  it('admin global: confirma y envía POST /shutdown (200)', async () => {
    mockApi([{ method: 'POST', path: '/shutdown', data: { ok: true } }])
    renderLayout('admin', { empresa: null })

    fireEvent.click(screen.getByRole('button', { name: /Apagar/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Sí, cerrar' }))

    expect(await screen.findByText(/Servidor detenido/)).toBeInTheDocument()
    expect(apiCalls.filter((c) => c.method === 'POST' && c.url === '/shutdown')).toHaveLength(1)
  })

  it('403 del backend: muestra el mensaje de error y NO cierra la pestaña', async () => {
    mockApi([
      {
        method: 'POST',
        path: '/shutdown',
        status: 403,
        data: { detail: 'Solo un administrador global puede realizar esta operación' },
      },
    ])
    renderLayout('admin', { empresa: null })

    fireEvent.click(screen.getByRole('button', { name: /Apagar/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Sí, cerrar' }))

    expect(await screen.findByText(/Solo un administrador global/)).toBeInTheDocument()
    expect(screen.queryByText(/Servidor detenido/)).not.toBeInTheDocument()
    expect(window.close).not.toHaveBeenCalled()
  })
})
