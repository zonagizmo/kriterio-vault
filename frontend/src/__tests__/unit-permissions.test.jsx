/**
 * Matriz Rol × Permiso de `services/permissions.js` + hook usePermissions.
 * Debe reflejar backend/app/services/permissions.py (§4 de SECURITY.md).
 */
import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { ROLE_PERMISSIONS, permisosDeRol, tienePermiso } from '../services/permissions'
import { usePermissions } from '../hooks/usePermissions'
import { AuthProvider } from '../hooks/useAuth.jsx'
import { setSession } from './helpers.jsx'

const PERMISOS_TODOS = [
  'read',
  'create',
  'update',
  'delete',
  'admin',
  'backup',
  'restore',
  'user_management',
  'configuration',
  'sync',
]

describe('permisosDeRol', () => {
  it('admin tiene los 10 permisos', () => {
    expect(permisosDeRol('admin').sort()).toEqual([...PERMISOS_TODOS].sort())
  })

  it('operador solo CRUD', () => {
    expect(permisosDeRol('operador').sort()).toEqual(['create', 'delete', 'read', 'update'])
  })

  it('solo_lectura solo read', () => {
    expect(permisosDeRol('solo_lectura')).toEqual(['read'])
  })

  it('rol desconocido o ausente no tiene permisos', () => {
    expect(permisosDeRol('inventado')).toEqual([])
    expect(permisosDeRol(undefined)).toEqual([])
    expect(permisosDeRol(null)).toEqual([])
  })
})

describe('tienePermiso', () => {
  it('admin puede todo', () => {
    const admin = { rol: 'admin' }
    for (const p of PERMISOS_TODOS) expect(tienePermiso(admin, p), p).toBe(true)
    expect(tienePermiso(admin, 'write')).toBe(true)
  })

  it('operador: CRUD sí; administración no', () => {
    const op = { rol: 'operador' }
    for (const p of ['read', 'create', 'update', 'delete', 'write']) {
      expect(tienePermiso(op, p), p).toBe(true)
    }
    for (const p of ['admin', 'backup', 'restore', 'user_management', 'configuration', 'sync']) {
      expect(tienePermiso(op, p), p).toBe(false)
    }
  })

  it('solo_lectura: solo read y write=false', () => {
    const ro = { rol: 'solo_lectura' }
    expect(tienePermiso(ro, 'read')).toBe(true)
    expect(tienePermiso(ro, 'write')).toBe(false)
    expect(tienePermiso(ro, 'create')).toBe(false)
    expect(tienePermiso(ro, 'update')).toBe(false)
    expect(tienePermiso(ro, 'delete')).toBe(false)
  })

  it('"write" es create ∨ update (coincide con la regla del backend)', () => {
    expect(tienePermiso({ rol: 'admin' }, 'write')).toBe(true)
    expect(tienePermiso({ rol: 'operador' }, 'write')).toBe(true)
    expect(tienePermiso({ rol: 'solo_lectura' }, 'write')).toBe(false)
    expect(tienePermiso(null, 'write')).toBe(false)
  })

  it('usuario sin rol no tiene nada', () => {
    for (const p of PERMISOS_TODOS) expect(tienePermiso(undefined, p), p).toBe(false)
  })

  it('la matriz no admite permisos inventados', () => {
    expect(tienePermiso({ rol: 'admin' }, 'superpoder')).toBe(false)
    expect(ROLE_PERMISSIONS.superpoder).toBeUndefined()
  })
})

describe('usePermissions', () => {
  const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>

  it('expone user, rol y has() según la sesión', () => {
    setSession({ rol: 'solo_lectura' })
    const { result } = renderHook(() => usePermissions(), { wrapper })
    expect(result.current.rol).toBe('solo_lectura')
    expect(result.current.user.username).toBe('tester')
    expect(result.current.has('read')).toBe(true)
    expect(result.current.has('delete')).toBe(false)
    expect(result.current.has('configuration')).toBe(false)
  })

  it('admin ve configuration y user_management', () => {
    setSession({ rol: 'admin' })
    const { result } = renderHook(() => usePermissions(), { wrapper })
    expect(result.current.has('configuration')).toBe(true)
    expect(result.current.has('user_management')).toBe(true)
  })

  it('sin sesión: rol null y has() siempre false', () => {
    // sin setSession no hay token ni usuario
    const { result } = renderHook(() => usePermissions(), { wrapper })
    expect(result.current.rol).toBeNull()
    expect(result.current.user).toBeNull()
    expect(result.current.has('read')).toBe(false)
  })
})
