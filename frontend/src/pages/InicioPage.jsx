import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import { getDashboard } from '../services/dashboard'

const EUR = (v) =>
  Number(v ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })

const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
               'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

function mesAnterior() {
  const hoy = new Date()
  const m = hoy.getMonth() === 0 ? 11 : hoy.getMonth() - 1
  return MESES[m]
}

function Delta({ actual, anterior }) {
  if (!anterior) return null
  const pct = ((actual - anterior) / Math.abs(anterior)) * 100
  const up = pct >= 0
  return (
    <span className={`text-xs font-medium ml-1 ${up ? 'text-green-600' : 'text-red-500'}`}>
      {up ? '▲' : '▼'} {Math.abs(pct).toFixed(1)}%
    </span>
  )
}

function Tarjeta({ titulo, valor, subtitulo, color = 'text-gray-900', onClick, children }) {
  return (
    <div
      className={`card px-5 py-4 ${onClick ? 'cursor-pointer hover:ring-2 hover:ring-mgd-400 transition-all' : ''}`}
      onClick={onClick}
    >
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">{titulo}</p>
      <p className={`text-2xl font-bold ${color}`}>{valor}</p>
      {subtitulo && <p className="text-xs text-gray-400 mt-1">{subtitulo}</p>}
      {children}
    </div>
  )
}

const TIPO_VTO = { R: 'Fra. recibida', F: 'Fra. emitida', X: 'Extra', C: 'Cobro', P: 'Pago' }

export default function InicioPage() {
  const { empresa } = useEmpresa()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [cargando, setCargando] = useState(false)

  useEffect(() => {
    if (!empresa) return
    setCargando(true)
    getDashboard(empresa.id)
      .then(setData)
      .catch(() => {})
      .finally(() => setCargando(false))
  }, [empresa])

  if (!empresa) {
    return (
      <div className="p-8 text-center text-gray-400">
        Selecciona una empresa para ver el panel.
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="px-6 pt-5 pb-2 border-b border-gray-200 bg-gray-50 flex-shrink-0">
        <h1 className="text-2xl font-bold text-gray-900">{empresa.nombre}</h1>
        <p className="text-gray-500 text-sm font-mono">{empresa.codigo}</p>
      </div>

      <div className="flex-1 p-6 space-y-6">
        {cargando && <p className="text-sm text-gray-400 text-center py-8">Cargando panel…</p>}

        {data && (
          <>
            {/* ── Bancos ─────────────────────────────────────── */}
            <section>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Tesorería</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {data.bancos.map((b) => (
                  <Tarjeta
                    key={b.numero}
                    titulo={b.nombre}
                    valor={EUR(b.saldo)}
                    color={b.saldo < 0 ? 'text-red-600' : 'text-gray-900'}
                    onClick={() => navigate(`/bancos/${b.numero}/movimientos`)}
                  />
                ))}
                <div className="card px-5 py-4 bg-mgd-50 border-mgd-200">
                  <p className="text-xs text-mgd-600 font-medium uppercase tracking-wide mb-1">Total</p>
                  <p className={`text-2xl font-bold ${data.total_bancos < 0 ? 'text-red-600' : 'text-mgd-800'}`}>
                    {EUR(data.total_bancos)}
                  </p>
                </div>
              </div>
            </section>

            {/* ── Facturación ────────────────────────────────── */}
            <section>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Facturación pendiente</h2>
              <div className="grid grid-cols-2 gap-3">
                <Tarjeta
                  titulo="Por cobrar"
                  valor={EUR(data.cobrar_pendiente)}
                  color={data.cobrar_pendiente > 0 ? 'text-green-700' : 'text-gray-400'}
                  subtitulo="Facturas emitidas y extras de ingreso pendientes"
                  onClick={() => navigate('/facturas?tab=emitidas&estado=P')}
                />
                <Tarjeta
                  titulo="Por pagar"
                  valor={EUR(data.pagar_pendiente)}
                  color={data.pagar_pendiente > 0 ? 'text-red-600' : 'text-gray-400'}
                  subtitulo="Facturas recibidas y extras de gasto pendientes"
                  onClick={() => navigate('/facturas?tab=recibidas&estado=P')}
                />
              </div>
            </section>

            {/* ── Mes en curso ───────────────────────────────── */}
            <section>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Mes en curso — <span className="normal-case font-normal">{data.mes_nombre}</span>
              </h2>
              <div className="grid grid-cols-2 gap-3">
                <div className="card px-5 py-4">
                  <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">Ingresos</p>
                  <p className="text-2xl font-bold text-green-700">{EUR(data.ingresos_mes)}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {mesAnterior()}: {EUR(data.ingresos_mes_anterior)}
                    <Delta actual={data.ingresos_mes} anterior={data.ingresos_mes_anterior} />
                  </p>
                </div>
                <div className="card px-5 py-4">
                  <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">Gastos</p>
                  <p className="text-2xl font-bold text-red-600">{EUR(data.gastos_mes)}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {mesAnterior()}: {EUR(data.gastos_mes_anterior)}
                    <Delta actual={data.gastos_mes} anterior={data.gastos_mes_anterior} />
                  </p>
                </div>
              </div>
            </section>

            {/* ── Vencimientos ───────────────────────────────── */}
            {(data.vencimientos_vencidos > 0 || data.vencimientos_proximos.length > 0) && (
              <section>
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Vencimientos</h2>

                {data.vencimientos_vencidos > 0 && (
                  <div
                    className="mb-3 flex items-center gap-3 px-4 py-3 rounded-lg border border-red-200 bg-red-50 text-red-700 cursor-pointer hover:bg-red-100 transition-colors"
                    onClick={() => navigate('/bancos?tab=vencimientos&solo_pendientes=1')}
                  >
                    <span className="text-lg font-bold">{data.vencimientos_vencidos}</span>
                    <span className="text-sm">
                      {data.vencimientos_vencidos === 1 ? 'vencimiento vencido sin pagar' : 'vencimientos vencidos sin pagar'}
                    </span>
                    <span className="ml-auto text-xs opacity-70">Ver →</span>
                  </div>
                )}

                {data.vencimientos_proximos.length > 0 && (
                  <div className="card overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b border-gray-100">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">Tipo</th>
                          <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">Vence</th>
                          <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">Pendiente</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {data.vencimientos_proximos.map((v) => {
                          const dias = Math.round((new Date(v.fecha) - new Date()) / 86400000)
                          return (
                            <tr key={v.numero} className="hover:bg-gray-50">
                              <td className="px-4 py-2 text-gray-700">
                                {TIPO_VTO[v.tipo] || v.tipo}
                              </td>
                              <td className="px-4 py-2">
                                <span className={`text-sm ${dias <= 2 ? 'text-orange-600 font-semibold' : 'text-gray-600'}`}>
                                  {new Date(v.fecha).toLocaleDateString('es-ES')}
                                </span>
                                {dias === 0 && <span className="ml-2 text-xs text-orange-500">hoy</span>}
                                {dias === 1 && <span className="ml-2 text-xs text-orange-500">mañana</span>}
                                {dias > 1 && <span className="ml-2 text-xs text-gray-400">en {dias}d</span>}
                              </td>
                              <td className="px-4 py-2 text-right font-semibold text-gray-800">
                                {EUR(v.pendiente)}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            )}
          </>
        )}
      </div>
    </div>
  )
}
