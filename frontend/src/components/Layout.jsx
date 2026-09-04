import { NavLink, useNavigate } from 'react-router-dom'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import BotonApagar from './BotonApagar'
import { VERSION_DISPLAY } from '../version'

const nav = [
  { to: '/inicio',       label: 'Inicio',       icon: '🏠' },
  { to: '/bancos',       label: 'Bancos',       icon: '🏦' },
  { to: '/usuarios',     label: 'Usuarios NNA', icon: '👦' },
  { to: '/clientes',     label: 'Clientes',     icon: '👥' },
  { to: '/proveedores',  label: 'Proveedores',  icon: '🏭' },
  { to: '/articulos',    label: 'Artículos',    icon: '📦' },
  { to: '/albaranes',    label: 'Albaranes',    icon: '🚚' },
  { to: '/facturas',     label: 'Facturas',     icon: '📄' },
  { to: '/extras',       label: 'Extras',       icon: '🧾' },
  { to: '/contabilidad', label: 'Contabilidad', icon: '📊' },
  { to: '/ingresos-gastos', label: 'Ingresos y Gastos', icon: '💶' },
  { to: '/estadisticas', label: 'Estadísticas', icon: '📈' },
  { to: '/ajustes',      label: 'Ajustes',      icon: '⚙️' },
]

export default function Layout({ children }) {
  const { empresa, setEmpresa } = useEmpresa()
  const navigate = useNavigate()

  function cambiarEmpresa() {
    setEmpresa(null)
    navigate('/')
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 bg-mgd-900 flex flex-col shrink-0">
        <div className="px-5 py-5 border-b border-mgd-800">
          <h1 className="text-white font-bold text-lg leading-tight">Kriterio</h1>
          <p className="text-mgd-100 text-xs mt-0.5 opacity-70">Vault</p>
        </div>

        {/* Empresa activa */}
        <div className="px-3 py-3 border-b border-mgd-800">
          <p className="text-xs text-mgd-100 opacity-60 uppercase tracking-wider mb-1">Empresa</p>
          <p className="text-white text-sm font-medium truncate leading-snug">
            {empresa?.nombre ?? ''}
          </p>
          <p className="text-mgd-100 opacity-50 text-xs font-mono mb-2">{empresa?.codigo ?? ''}</p>
          <button
            onClick={cambiarEmpresa}
            className="text-xs text-mgd-100 opacity-60 hover:opacity-100 hover:text-white transition-opacity"
          >
            ← Cambiar empresa
          </button>
        </div>

        {/* Navegación */}
        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          {nav.map(({ to, label, icon, disabled }) =>
            disabled ? (
              <div
                key={to}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-mgd-100 opacity-30 text-sm cursor-not-allowed select-none"
              >
                <span>{icon}</span>
                <span>{label}</span>
                <span className="ml-auto text-xs">pronto</span>
              </div>
            ) : (
              <NavLink
                key={to}
                to={to}
                end={to === '/inicio'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive
                      ? 'bg-mgd-600 text-white font-medium'
                      : 'text-mgd-100 hover:bg-mgd-800'
                  }`
                }
              >
                <span>{icon}</span>
                <span>{label}</span>
              </NavLink>
            )
          )}
        </nav>

        <BotonApagar variant="sidebar" />

        <div className="px-4 py-2 text-xs text-mgd-100 opacity-30">
          v{VERSION_DISPLAY}
        </div>
      </aside>

      {/* Contenido principal */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
