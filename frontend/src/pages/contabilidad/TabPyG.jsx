import { useState } from 'react'
import { getPyG, exportarCSV } from '../../services/contabilidad'
import { EUR, anioActual } from './utils'

export default function TabPyG({ empresa }) {
  const [fechaDesde, setFechaDesde] = useState(`${anioActual}-01-01`)
  const [fechaHasta, setFechaHasta] = useState(`${anioActual}-12-31`)
  const [data, setData] = useState(null)
  const [cargando, setCargando] = useState(false)

  const consultar = async () => {
    setCargando(true)
    try {
      const params = { empresa_id: empresa.id }
      if (fechaDesde) params.fecha_desde = fechaDesde
      if (fechaHasta) params.fecha_hasta = fechaHasta
      const res = await getPyG(params)
      setData(res)
    } finally {
      setCargando(false)
    }
  }

  const Seccion = ({ titulo, filas, totalLabel, total, colorTotal }) => (
    <div className="mb-4">
      <div className="bg-gray-100 px-4 py-2 font-semibold text-gray-700 text-sm uppercase tracking-wide rounded-t-lg border border-gray-200">
        {titulo}
      </div>
      <div className="border border-t-0 border-gray-200 rounded-b-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase w-28">Cuenta</th>
              <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase">Descripción</th>
              <th className="px-4 py-2 text-right text-xs text-gray-500 uppercase">Importe</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filas.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-4 py-4 text-center text-gray-400 text-xs">
                  Sin movimientos
                </td>
              </tr>
            ) : (
              filas.map((f) => {
                const imp = f.importe ?? (f.saldo_deudor > 0 ? f.saldo_deudor : f.saldo_acreedor)
                return (
                  <tr key={f.cuenta} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-gray-800">{f.cuenta}</td>
                    <td className="px-4 py-2 text-gray-600 text-xs">{f.texto}</td>
                    <td className="px-4 py-2 text-right font-mono text-xs">{EUR(imp)}</td>
                  </tr>
                )
              })
            )}
          </tbody>
          <tfoot className="bg-gray-50 border-t-2 border-gray-300 font-bold">
            <tr>
              <td colSpan={2} className="px-4 py-2.5 text-gray-700 text-sm">
                {totalLabel}
              </td>
              <td className={`px-4 py-2.5 text-right font-mono text-sm ${colorTotal}`}>{EUR(Math.abs(total))}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )

  return (
    <div>
      <div className="flex flex-wrap items-end gap-3 mb-6">
        <div>
          <label className="label">Desde</label>
          <input type="date" className="input" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} />
        </div>
        <div>
          <label className="label">Hasta</label>
          <input type="date" className="input" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} />
        </div>
        <button className="btn btn-primary self-end" onClick={consultar} disabled={cargando}>
          {cargando ? 'Calculando...' : 'Calcular'}
        </button>
        {data && (
          <button
            className="btn btn-secondary self-end"
            onClick={() =>
              exportarCSV('pyg', { empresa_id: empresa.id, fecha_desde: fechaDesde, fecha_hasta: fechaHasta })
            }
          >
            Exportar CSV
          </button>
        )}
      </div>

      {data && (
        <div className="max-w-3xl">
          <Seccion
            titulo="Ingresos (cuentas 7xx)"
            filas={data.ingresos}
            totalLabel="Total ingresos"
            total={data.total_ingresos}
            colorTotal="text-green-700"
          />
          <Seccion
            titulo="Gastos (cuentas 6xx)"
            filas={data.gastos}
            totalLabel="Total gastos"
            total={data.total_gastos}
            colorTotal="text-red-600"
          />

          {data.saldo_inicial_bancos > 0 && (
            <div className="card p-4 mb-2 flex justify-between items-center border border-blue-200 bg-blue-50">
              <span className="text-sm text-blue-800 font-medium">Saldo inicial en bancos (apertura)</span>
              <span className="font-mono text-sm text-blue-700">+{EUR(data.saldo_inicial_bancos)}</span>
            </div>
          )}

          <div
            className={`card p-5 flex justify-between items-center text-lg font-bold border-2 ${
              data.resultado >= 0 ? 'border-green-400 bg-green-50' : 'border-red-400 bg-red-50'
            }`}
          >
            <span className="text-gray-800">
              {data.resultado >= 0 ? 'Beneficio del ejercicio' : 'Pérdida del ejercicio'}
            </span>
            <span className={data.resultado >= 0 ? 'text-green-700' : 'text-red-600'}>
              {EUR(Math.abs(data.resultado))}
            </span>
          </div>

          {data.saldo_inicial_bancos > 0 && (
            <div
              className={`card p-5 mt-2 flex justify-between items-center text-lg font-bold border-2 ${
                data.resultado_con_saldo_inicial >= 0 ? 'border-blue-400 bg-blue-50' : 'border-orange-400 bg-orange-50'
              }`}
            >
              <span className="text-gray-800">Resultado + saldo inicial</span>
              <span className={data.resultado_con_saldo_inicial >= 0 ? 'text-blue-700' : 'text-orange-600'}>
                {data.resultado_con_saldo_inicial >= 0 ? '' : '−'}
                {EUR(Math.abs(data.resultado_con_saldo_inicial))}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
