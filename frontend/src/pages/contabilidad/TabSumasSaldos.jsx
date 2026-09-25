import { useState } from 'react'
import { getSumasSaldos, exportarCSV } from '../../services/contabilidad'
import { EUR, anioActual } from './utils'

export default function TabSumasSaldos({ empresa }) {
  const [fechaDesde, setFechaDesde] = useState(`${anioActual - 1}-01-01`)
  const [fechaHasta, setFechaHasta] = useState(`${anioActual - 1}-12-31`)
  const [nivel, setNivel] = useState('')
  const [data, setData] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  const consultar = async () => {
    setCargando(true)
    setError('')
    try {
      const params = { empresa_id: empresa.id }
      if (fechaDesde) params.fecha_desde = fechaDesde
      if (fechaHasta) params.fecha_hasta = fechaHasta
      if (nivel) params.nivel = parseInt(nivel)
      const res = await getSumasSaldos(params)
      setData(res)
    } catch (err) {
      setError(err.message || 'Error al calcular')
    } finally {
      setCargando(false)
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div>
          <label className="label">Desde</label>
          <input type="date" className="input" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} />
        </div>
        <div>
          <label className="label">Hasta</label>
          <input type="date" className="input" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} />
        </div>
        <div>
          <label className="label">Nivel (dígitos)</label>
          <select className="input w-28" value={nivel} onChange={(e) => setNivel(e.target.value)}>
            <option value="">Detalle</option>
            <option value="1">1 dígito</option>
            <option value="2">2 dígitos</option>
            <option value="3">3 dígitos</option>
            <option value="4">4 dígitos</option>
          </select>
        </div>
        <button className="btn btn-primary self-end" onClick={consultar} disabled={cargando}>
          {cargando ? 'Calculando...' : 'Calcular'}
        </button>
        {error && <span className="text-sm text-red-600">{error}</span>}
        {data && (
          <button
            className="btn btn-secondary self-end"
            onClick={() =>
              exportarCSV('sumas-saldos', { empresa_id: empresa.id, fecha_desde: fechaDesde, fecha_hasta: fechaHasta })
            }
          >
            Exportar CSV
          </button>
        )}
      </div>

      {data && (
        <div className="card">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-28">
                  Cuenta
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Descripción
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Debe
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Haber
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Sd. Deudor
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Sd. Acreedor
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.filas.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                    Sin movimientos en el periodo
                  </td>
                </tr>
              )}
              {data.filas.map((f) => (
                <tr key={f.cuenta} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-gray-800 font-medium">{f.cuenta}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{f.texto}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-gray-700">{EUR(f.debe)}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-gray-700">{EUR(f.haber)}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-green-700">
                    {f.saldo_deudor > 0 ? EUR(f.saldo_deudor) : ''}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-red-600">
                    {f.saldo_acreedor > 0 ? EUR(f.saldo_acreedor) : ''}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50 border-t-2 border-gray-300 font-bold text-sm">
              <tr>
                <td colSpan={2} className="px-4 py-3 text-gray-700">
                  TOTAL ({data.filas.length} cuentas)
                </td>
                <td className="px-4 py-3 text-right font-mono text-gray-700">{EUR(data.total_debe)}</td>
                <td className="px-4 py-3 text-right font-mono text-gray-700">{EUR(data.total_haber)}</td>
                <td className="px-4 py-3 text-right font-mono text-green-700">{EUR(data.total_saldo_deudor)}</td>
                <td className="px-4 py-3 text-right font-mono text-red-600">{EUR(data.total_saldo_acreedor)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  )
}
