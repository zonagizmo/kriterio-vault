import { useState } from 'react'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import {
  getIngresosGastosPeriodo, getListadoIngresos, getListadoGastos,
  exportarListadoIngresos, exportarListadoGastos,
} from '../services/estadisticas'

const EUR = (v) =>
  Number(v ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })

const fmtFecha = (f) => {
  if (!f) return ''
  const [y, m, d] = String(f).split('-')
  return `${d}/${m}/${y}`
}

const COLORES_INGRESO = ['#2a78d6', '#1baf7a']
const COLORES_GASTO = ['#e34948', '#eb6834', '#eda100', '#4a3aa7']

const anioActual = new Date().getFullYear()
const hoy = () => new Date().toISOString().slice(0, 10)

function Desglose({ categorias, colores }) {
  const conDatos = categorias.filter((c) => c.importe !== 0)
  if (conDatos.length === 0) {
    return <p className="text-sm text-gray-400">Sin movimientos en el período</p>
  }
  const ordenadas = [...conDatos].sort((a, b) => b.importe - a.importe)
  const max = Math.max(1, ...ordenadas.map((c) => c.importe))
  const total = ordenadas.reduce((s, c) => s + c.importe, 0)

  return (
    <div className="space-y-3">
      {ordenadas.map((c, i) => {
        const pct = total > 0 ? (c.importe / total) * 100 : 0
        return (
          <div key={c.categoria}>
            <div className="flex justify-between text-xs text-gray-600 mb-1">
              <span className="font-medium text-gray-700">{c.categoria}</span>
              <span>{EUR(c.importe)} · {pct.toFixed(1)}%</span>
            </div>
            <div className="h-3 rounded-full bg-gray-100 overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${(c.importe / max) * 100}%`, background: colores[i % colores.length] }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function Panel({ titulo, children, accion }) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-700">{titulo}</h2>
        {accion}
      </div>
      {children}
    </div>
  )
}

function TablaListado({ items, colorImporte, variante = 'ingresos' }) {
  if (!items || items.length === 0) {
    return <p className="text-sm text-gray-400">Sin movimientos en el período</p>
  }
  const total = items.reduce((s, it) => s + (it.importe ?? 0), 0)
  const esGastos = variante === 'gastos'
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
            <th className="py-2 pr-3">Fecha</th>
            <th className="py-2 pr-3">Origen</th>
            {esGastos ? (
              <>
                <th className="py-2 pr-3">Proveedor</th>
                <th className="py-2 pr-3">Nº Factura</th>
              </>
            ) : (
              <th className="py-2 pr-3">Concepto</th>
            )}
            <th className="py-2 text-right">Importe</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {items.map((it, i) => (
            <tr key={i}>
              <td className="py-2 pr-3 text-gray-600 whitespace-nowrap">{fmtFecha(it.fecha)}</td>
              <td className="py-2 pr-3 text-gray-500">{it.origen}</td>
              {esGastos ? (
                <>
                  <td className="py-2 pr-3 text-gray-900">{it.proveedor}</td>
                  <td className="py-2 pr-3 text-gray-500">{it.nfactura}</td>
                </>
              ) : (
                <td className="py-2 pr-3 text-gray-900">{it.concepto}</td>
              )}
              <td className={`py-2 text-right font-medium ${colorImporte}`}>{EUR(it.importe)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-gray-300">
            <td colSpan={esGastos ? 4 : 3} className="py-2 pr-3 text-right font-semibold text-gray-700">Total</td>
            <td className={`py-2 text-right font-bold ${colorImporte}`}>{EUR(total)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

export default function IngresosGastosPage() {
  const { empresa } = useEmpresa()
  const [tab, setTab] = useState('resumen')
  const [fechaDesde, setFechaDesde] = useState(`${anioActual}-01-01`)
  const [fechaHasta, setFechaHasta] = useState(hoy())
  const [data, setData]         = useState(null)
  const [ingresos, setIngresos] = useState([])
  const [gastos, setGastos]     = useState([])
  const [cargando, setCargando] = useState(false)
  const [error, setError]       = useState('')

  const consultar = async () => {
    if (!fechaDesde || !fechaHasta) return
    if (fechaDesde > fechaHasta) {
      setError('La fecha "Desde" no puede ser posterior a "Hasta"')
      return
    }
    setError('')
    setCargando(true)
    try {
      const [res, resIngresos, resGastos] = await Promise.all([
        getIngresosGastosPeriodo(empresa.id, fechaDesde, fechaHasta),
        getListadoIngresos(empresa.id, fechaDesde, fechaHasta),
        getListadoGastos(empresa.id, fechaDesde, fechaHasta),
      ])
      setData(res)
      setIngresos(resIngresos.items || [])
      setGastos(resGastos.items || [])
    } catch {
      setError('Error al calcular el período')
    } finally {
      setCargando(false)
    }
  }

  if (!empresa) {
    return <div className="p-8 text-center text-gray-400">Selecciona una empresa.</div>
  }

  const tabs = [
    { id: 'resumen', label: 'Resumen' },
    { id: 'ingresos', label: 'Ingresos' },
    { id: 'gastos', label: 'Gastos' },
  ]

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="px-6 pt-5 pb-4 border-b border-gray-200 bg-gray-50 flex-shrink-0">
        <h1 className="text-2xl font-bold text-gray-900">Ingresos y Gastos</h1>
        <p className="text-gray-500 text-sm">{empresa.nombre}</p>
      </div>

      <div className="flex-1 p-6 space-y-6">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="label">Desde</label>
            <input type="date" className="input" value={fechaDesde}
              onChange={(e) => setFechaDesde(e.target.value)} />
          </div>
          <div>
            <label className="label">Hasta</label>
            <input type="date" className="input" value={fechaHasta}
              onChange={(e) => setFechaHasta(e.target.value)} />
          </div>
          <button className="btn btn-primary self-end" onClick={consultar} disabled={cargando}>
            {cargando ? 'Calculando…' : 'Calcular'}
          </button>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {data && !cargando && (
          <>
            <div className="border-b border-gray-200">
              <nav className="flex gap-1">
                {tabs.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setTab(t.id)}
                    className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                      tab === t.id
                        ? 'border-mgd-600 text-mgd-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </nav>
            </div>

            {tab === 'resumen' && (
              <div className="space-y-6">
                <div className="grid grid-cols-3 gap-3">
                  <div className="card px-5 py-4">
                    <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">Ingresos</p>
                    <p className="text-2xl font-bold text-green-700">{EUR(data.ingresos_total)}</p>
                  </div>
                  <div className="card px-5 py-4">
                    <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">Gastos</p>
                    <p className="text-2xl font-bold text-red-600">{EUR(data.gastos_total)}</p>
                  </div>
                  <div className={`card px-5 py-4 border-2 ${data.resultado >= 0 ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50'}`}>
                    <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">
                      {data.resultado >= 0 ? 'Resultado (beneficio)' : 'Resultado (pérdida)'}
                    </p>
                    <p className={`text-2xl font-bold ${data.resultado >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                      {EUR(Math.abs(data.resultado))}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Panel titulo="Ingresos por categoría">
                    <Desglose categorias={data.categorias_ingreso} colores={COLORES_INGRESO} />
                  </Panel>
                  <Panel titulo="Gastos por categoría">
                    <Desglose categorias={data.categorias_gasto} colores={COLORES_GASTO} />
                  </Panel>
                </div>
              </div>
            )}

            {tab === 'ingresos' && (
              <Panel
                titulo={`Listado de ingresos (${ingresos.length})`}
                accion={
                  <button className="btn btn-secondary text-xs"
                    onClick={() => exportarListadoIngresos(empresa.id, fechaDesde, fechaHasta)}>
                    Exportar a Excel
                  </button>
                }
              >
                <TablaListado items={ingresos} colorImporte="text-green-700" />
              </Panel>
            )}

            {tab === 'gastos' && (
              <Panel
                titulo={`Listado de gastos (${gastos.length})`}
                accion={
                  <button className="btn btn-secondary text-xs"
                    onClick={() => exportarListadoGastos(empresa.id, fechaDesde, fechaHasta)}>
                    Exportar a Excel
                  </button>
                }
              >
                <TablaListado items={gastos} colorImporte="text-red-600" variante="gastos" />
              </Panel>
            )}
          </>
        )}

        {!data && !cargando && !error && (
          <p className="text-sm text-gray-400">Elige un rango de fechas y pulsa "Calcular".</p>
        )}
      </div>
    </div>
  )
}
