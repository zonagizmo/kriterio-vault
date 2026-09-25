import { useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useEmpresa } from '../../hooks/useEmpresa.jsx'
import TabCuentas from './TabCuentas'
import TabDiario from './TabDiario'
import TabMayor from './TabMayor'
import TabSumasSaldos from './TabSumasSaldos'
import TabPyG from './TabPyG'
import TabBalance from './TabBalance'
import TabConciliacion from './TabConciliacion'
import TabDiagnostico from './TabDiagnostico'

export default function ContabilidadPage() {
  const { empresa } = useEmpresa()
  const [searchParams] = useSearchParams()
  const tabParam = searchParams.get('tab') || 'cuentas'
  const cuentaParam = searchParams.get('cuenta') || ''
  const [tab, setTab] = useState(tabParam)
  const [cuentaMayor, setCuentaMayor] = useState(cuentaParam)

  const irAMayor = useCallback((cuenta) => {
    setCuentaMayor(cuenta)
    setTab('mayor')
  }, [])

  if (!empresa) {
    return <div className="p-8 text-center text-gray-400">Selecciona una empresa para ver la contabilidad.</div>
  }

  const tabs = [
    { id: 'cuentas', label: 'Plan de cuentas' },
    { id: 'diario', label: 'Diario' },
    { id: 'mayor', label: 'Libro mayor' },
    { id: 'sumas', label: 'Sumas y saldos' },
    { id: 'pyg', label: 'P&G' },
    { id: 'balance', label: 'Balance' },
    { id: 'conciliacion', label: 'Conciliación' },
    { id: 'diagnostico', label: 'Diagnóstico' },
  ]

  return (
    <div className="h-full overflow-y-auto">
      <div className="bg-gray-50 border-b border-gray-200 px-6 pt-5 pb-0">
        <div className="mb-3">
          <h1 className="text-2xl font-bold text-gray-900">Contabilidad</h1>
          <p className="text-gray-500 text-sm mt-1">{empresa.nombre}</p>
        </div>
        <nav className="flex gap-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === t.id ? 'border-mgd-600 text-mgd-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="p-6">
        {tab === 'cuentas' && <TabCuentas empresa={empresa} onIrAMayor={irAMayor} />}
        {tab === 'diario' && <TabDiario empresa={empresa} />}
        {tab === 'mayor' && <TabMayor empresa={empresa} cuentaInicial={cuentaMayor} />}
        {tab === 'sumas' && <TabSumasSaldos empresa={empresa} />}
        {tab === 'pyg' && <TabPyG empresa={empresa} />}
        {tab === 'balance' && <TabBalance empresa={empresa} />}
        {tab === 'conciliacion' && <TabConciliacion empresa={empresa} />}
        {tab === 'diagnostico' && <TabDiagnostico empresa={empresa} />}
      </div>
    </div>
  )
}
