/**
 * Enrutado global de App: ProtectedRoute, RequierePermiso y comodines.
 * Reflejo de la política: /ajustes exige configuration y /usuarios-sistema
 * exige user_management (el backend devuelve 403 de verdad).
 */
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'
import { setSession } from './helpers.jsx'

function renderEn(ruta, { rol = 'admin', empresa = { id: 1, nombre: 'Empresa 1', codigo: 'E1' }, sesion = true } = {}) {
  if (sesion) setSession({ rol, empresa })
  else localStorage.clear()
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <App />
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  it('sin sesión redirige a /login', () => {
    renderEn('/clientes', { sesion: false })
    expect(screen.getByText('Inicia sesión para continuar')).toBeInTheDocument()
    expect(screen.queryByText('Clientes')).not.toBeInTheDocument()
  })

  it('con sesión muestra la página pedida', async () => {
    renderEn('/clientes', { rol: 'admin' })
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Clientes' })).toBeInTheDocument())
  })
})

describe('RequierePermiso', () => {
  it('admin accede a /ajustes', async () => {
    renderEn('/ajustes', { rol: 'admin' })
    expect(await screen.findByRole('heading', { name: 'Ajustes' })).toBeInTheDocument()
    expect(screen.queryByText('Inicia sesión para continuar')).not.toBeInTheDocument()
  })

  it('operador en /ajustes vuelve a /inicio', async () => {
    renderEn('/ajustes', { rol: 'operador' })
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Empresa 1' })).toBeInTheDocument())
    expect(screen.queryByRole('heading', { level: 1, name: /Ajustes/ })).not.toBeInTheDocument()
  })

  it('solo_lectura en /usuarios-sistema vuelve a /inicio', async () => {
    renderEn('/usuarios-sistema', { rol: 'solo_lectura' })
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Empresa 1' })).toBeInTheDocument())
  })

  it('admin accede a /usuarios-sistema', async () => {
    renderEn('/usuarios-sistema', { rol: 'admin' })
    expect(await screen.findByRole('heading', { name: 'Usuarios del sistema' })).toBeInTheDocument()
  })
})

describe('rutas comodín', () => {
  it('ruta desconocida → /inicio', async () => {
    renderEn('/ruta-que-no-existe', { rol: 'admin' })
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Empresa 1' })).toBeInTheDocument())
  })

  it('/login siempre muestra el formulario (con o sin sesión)', () => {
    renderEn('/login', { rol: 'admin' })
    expect(screen.getByText('Inicia sesión para continuar')).toBeInTheDocument()
  })
})
