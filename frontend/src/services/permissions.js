/**
 * Permisos del frontend — reflejo de la política del backend.
 *
 * ÚNICA fuente de verdad: backend/app/services/permissions.py (matriz
 * Rol × Permiso). Este módulo solo sirve para ocultar controles que el
 * usuario no podrá usar: NUNCA es una medida de seguridad (el backend
 * devuelve 401/403 aunque se manipulen las peticiones a mano).
 */

export const ROLE_PERMISSIONS = {
  admin: [
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
  ],
  operador: ['read', 'create', 'update', 'delete'],
  solo_lectura: ['read'],
}

export function permisosDeRol(rol) {
  return ROLE_PERMISSIONS[rol] || []
}

export function tienePermiso(user, perm) {
  const perms = permisosDeRol(user?.rol)
  if (perm === 'write') return perms.includes('create') || perms.includes('update')
  if (perm === 'admin') return perms.includes('admin')
  return perms.includes(perm)
}
