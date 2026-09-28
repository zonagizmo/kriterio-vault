import { useAuth } from './useAuth.jsx'
import { tienePermiso } from '../services/permissions'

/**
 * Reflejo de los permisos del usuario en la UI.
 *
 *   const { has, rol } = usePermissions()
 *   {has('create') && <button>Nuevo</button>}
 *
 * La autorización real la decide el backend (403 si no toca): esto solo
 * evita mostrar controles inútiles a solo_lectura.
 */
export function usePermissions() {
  const { user } = useAuth()
  return {
    user,
    rol: user?.rol || null,
    has: (perm) => tienePermiso(user, perm),
  }
}
