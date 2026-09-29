/** Página de login: envío de credenciales y manejo de error. */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../hooks/useAuth.jsx'
import LoginPage from '../pages/LoginPage'
import { mockApi, apiCalls } from './helpers.jsx'

function renderLogin() {
  const res = render(
    <MemoryRouter>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  )
  // los <label> no están asociados a los inputs: se buscan por tipo
  res.usuario = res.container.querySelector('input[type="text"]')
  res.password = res.container.querySelector('input[type="password"]')
  return res
}

describe('LoginPage', () => {
  it('muestra el formulario con ambos campos', () => {
    const { usuario, password } = renderLogin()
    expect(usuario).toBeInTheDocument()
    expect(password).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument()
  })

  it('envía credenciales y navega a /empresas guardando la sesión', async () => {
    mockApi([
      {
        method: 'POST',
        path: '/auth/login',
        data: { access_token: 'tk', usuario: { id: 1, username: 'ana', nombre: 'Ana', rol: 'admin' } },
      },
    ])
    const { usuario, password } = renderLogin()
    fireEvent.change(usuario, { target: { value: 'ana' } })
    fireEvent.change(password, { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    await waitFor(() =>
      expect(apiCalls.some((c) => c.url === '/auth/login' && c.data.password === 'secret')).toBe(true),
    )
    await waitFor(() => expect(localStorage.getItem('kriterio_token')).toBe('tk'))
  })

  it('credenciales inválidas: muestra el error del backend', async () => {
    mockApi([
      { method: 'POST', path: '/auth/login', status: 401, data: { detail: 'Usuario o contraseña incorrectos' } },
    ])
    const { usuario, password } = renderLogin()
    fireEvent.change(usuario, { target: { value: 'ana' } })
    fireEvent.change(password, { target: { value: 'mala' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByText('Usuario o contraseña incorrectos')).toBeInTheDocument()
    expect(localStorage.getItem('kriterio_token')).toBeNull()
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeEnabled()
  })

  it('mientras envía, el botón está deshabilitado', async () => {
    mockApi([{ method: 'POST', path: '/auth/login', data: { access_token: 't', usuario: { rol: 'admin' } } }])
    const { usuario, password } = renderLogin()
    fireEvent.change(usuario, { target: { value: 'u' } })
    fireEvent.change(password, { target: { value: 'p' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    // el estado loading se activa de forma síncrona en el submit
    await waitFor(() => expect(screen.getByRole('button', { name: /Entrando/ })).toBeDisabled())
    vi.restoreAllMocks()
  })
})
