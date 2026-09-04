import { useNavigate } from 'react-router-dom'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import BotonApagar from '../components/BotonApagar'

export default function EmpresasSelectorPage() {
  const { empresas, setEmpresa } = useEmpresa()
  const navigate = useNavigate()

  function seleccionar(emp) {
    setEmpresa(emp)
    navigate('/inicio')
  }

  return (
    <div className="min-h-screen bg-mgd-900 flex flex-col items-center justify-center p-8">
      <div className="mb-10 text-center">
        <h1 className="text-3xl font-bold text-white tracking-tight">Kriterio Vault</h1>
        <p className="text-mgd-100 opacity-60 mt-1 text-sm">Selecciona una empresa para continuar</p>
      </div>

      {empresas.length === 0 ? (
        <p className="text-mgd-100 opacity-40 text-sm">Cargando empresas…</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full max-w-3xl">
          {empresas.map((emp) => (
            <button
              key={emp.id}
              onClick={() => seleccionar(emp)}
              className="bg-mgd-900 hover:bg-mgd-800 border border-mgd-700 hover:border-mgd-500 rounded-xl p-6 text-left transition-all group"
            >
              <div className="text-xs font-mono text-mgd-100 opacity-50 mb-1 uppercase tracking-widest">
                {emp.codigo}
              </div>
              <div className="text-white font-semibold text-base group-hover:text-mgd-100 leading-snug">
                {emp.nombre}
              </div>
            </button>
          ))}
        </div>
      )}

      <BotonApagar variant="selector" />
    </div>
  )
}
