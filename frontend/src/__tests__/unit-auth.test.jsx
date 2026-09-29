/**
 * useAuth + interceptores del cliente axios (`services/api.js`):
 * token en Authorization, 401 → logout + redirect, traducción de `detail`.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { AuthProvider, useAuth } from '../hooks/useAuth.jsx'
import api from '../services/api'
import { getToken, getUsuario } from '../services/auth'
import { mockApi, apiCalls, setSession } from './helpers.jsx'

describe('useAuth', () => {
  const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>

  it('arranca con la sesión de localStorage', () => {
    setSession({ rol: 'operador' })
    const { result } = renderHook(() => useAuth(), { wrapper })
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user.rol).toBe('operador')
  })

  it('sin sesión: user null y isAuthenticated false', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('login guarda token + usuario y actualiza el contexto', async () => {
    mockApi([
      {
        method: 'POST',
        path: '/auth/login',
        data: { access_token: 'tk-real', usuario: { id: 7, username: 'ana', rol: 'admin' } },
      },
    ])
    const { result } = renderHook(() => useAuth(), { wrapper })
    await act(async () => {
      await result.current.login('ana', 'secret')
    })
    expect(getToken()).toBe('tk-real')
    expect(getUsuario().username).toBe('ana')
    expect(result.current.user.username).toBe('ana')
    expect(apiCalls).toContainEqual({
      method: 'POST',
      url: '/auth/login',
      params: undefined,
      data: { username: 'ana', password: 'secret' },
    })
  })

  it('login con error no guarda nada', async () => {
    mockApi([
      { method: 'POST', path: '/auth/login', status: 401, data: { detail: 'Usuario o contraseña incorrectos' } },
    ])
    const { result } = renderHook(() => useAuth(), { wrapper })
    await expect(act(() => result.current.login('ana', 'mala'))).rejects.toThrow('Usuario o contraseña incorrectos')
    expect(getToken()).toBeNull()
    expect(result.current.user).toBeNull()
  })

  it('logout limpia localStorage y el contexto', async () => {
    setSession()
    const { result } = renderHook(() => useAuth(), { wrapper })
    expect(result.current.isAuthenticated).toBe(true)
    act(() => result.current.logout())
    expect(result.current.isAuthenticated).toBe(false)
    expect(getToken()).toBeNull()
    expect(getUsuario()).toBeNull()
  })
})

describe('interceptores de services/api.js', () => {
  beforeEach(() => setSession())

  it('añade el header Authorization con el token vigente', async () => {
    mockApi([{ path: '/algo', data: { ok: true } }])
    await api.get('/algo')
    const call = apiCalls.at(-1)
    expect(call.url).toBe('/algo')
    // el header lo pone el interceptor de request sobre config.headers
    expect(localStorage.getItem('kriterio_token')).toBe('tk-test')
  })

  it('401 fuera de login: cierra sesión (token borrado)', async () => {
    mockApi([{ path: '/protegido', status: 401, data: { detail: 'Sesión expirada' } }])
    await expect(api.get('/protegido')).rejects.toThrow('Sesión expirada')
    expect(localStorage.getItem('kriterio_token')).toBeNull()
    expect(localStorage.getItem('kriterio_user')).toBeNull()
  })

  it('traduce detail de error a Error(message)', async () => {
    mockApi([{ path: '/x', status: 404, data: { detail: 'Recurso no encontrado' } }])
    await expect(api.get('/x')).rejects.toThrow('Recurso no encontrado')
  })

  it('detail objeto (validación 422) conserva .detail', async () => {
    mockApi([{ path: '/x', status: 422, data: { detail: { mensaje: 'Nombre obligatorio', campo: 'nombre' } } }])
    const err = await api.post('/x', {}).catch((e) => e)
    expect(err.message).toBe('Nombre obligatorio')
    expect(err.detail.campo).toBe('nombre')
  })

  it('el login con 401 NO cierra sesión (permite reintentar)', async () => {
    mockApi([{ method: 'POST', path: '/auth/login', status: 401, data: { detail: 'Credenciales inválidas' } }])
    await expect(api.post('/auth/login', { username: 'x', password: 'y' })).rejects.toThrow('Credenciales inválidas')
    // sigue habiendo sesión (la anterior) → no se ha deslogueado
    expect(localStorage.getItem('kriterio_token')).toBe('tk-test')
    vi.restoreAllMocks()
  })
})
