import { useEffect, useState } from 'react'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import { getAniosEstadisticas, getEstadisticas } from '../services/estadisticas'

const EUR = (v) =>
  Number(v ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
const EUR0 = (v) =>
  Number(v ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })

const MESES_ABR = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

const COLOR_INGRESO = '#16a34a'
const COLOR_GASTO = '#dc2626'
const COLORES_CATEGORIA = ['#2a78d6', '#008300', '#e87ba4', '#eda100']

const W = 760
const H = 260
const PAD = { top: 16, right: 16, bottom: 28, left: 48 }

function escala(valores) {
  const max = Math.max(1, ...valores)
  // redondea el techo del eje a un múltiplo "bonito"
  const magnitud = Math.pow(10, Math.floor(Math.log10(max)))
  const techo = Math.ceil(max / magnitud) * magnitud
  return techo
}

function Tooltip({ x, y, children }) {
  return (
    <div
      className="absolute z-10 px-2.5 py-1.5 rounded-md bg-gray-900 text-white text-xs shadow-lg pointer-events-none whitespace-nowrap"
      style={{ left: x, top: y, transform: 'translate(-50%, -110%)' }}
    >
      {children}
    </div>
  )
}

function GraficoMensual({ meses }) {
  const [hover, setHover] = useState(null)
  const techo = escala(meses.flatMap((m) => [m.ingresos, m.gastos]))
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom
  const grupoW = plotW / meses.length
  const barW = Math.min(18, grupoW / 2 - 4)

  const y = (v) => PAD.top + plotH - (v / techo) * plotH

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
        {/* gridlines */}
        {[0, 0.25, 0.5, 0.75, 1].map((f) => (
          <g key={f}>
            <line
              x1={PAD.left} x2={W - PAD.right}
              y1={PAD.top + plotH * (1 - f)} y2={PAD.top + plotH * (1 - f)}
              stroke="#e5e7eb" strokeWidth="1"
            />
            <text x={PAD.left - 8} y={PAD.top + plotH * (1 - f) + 3} textAnchor="end" fontSize="10" fill="#9ca3af">
              {EUR0(techo * f)}
            </text>
          </g>
        ))}

        {meses.map((m, i) => {
          const cx = PAD.left + grupoW * i + grupoW / 2
          const hIng = (m.ingresos / techo) * plotH
          const hGas = (m.gastos / techo) * plotH
          return (
            <g key={m.mes}>
              <rect
                x={cx - barW - 1} y={y(m.ingresos)} width={barW} height={hIng}
                rx={3} fill={COLOR_INGRESO}
                onMouseEnter={() => setHover({ i, cx, y: y(m.ingresos) })}
                onMouseLeave={() => setHover(null)}
              />
              <rect
                x={cx + 1} y={y(m.gastos)} width={barW} height={hGas}
                rx={3} fill={COLOR_GASTO}
                onMouseEnter={() => setHover({ i, cx, y: y(m.gastos) })}
                onMouseLeave={() => setHover(null)}
              />
              <text x={cx} y={H - 8} textAnchor="middle" fontSize="10" fill="#6b7280">
                {MESES_ABR[m.mes - 1]}
              </text>
            </g>
          )
        })}
      </svg>

      {hover && (
        <Tooltip x={`${(hover.cx / W) * 100}%`} y={`${(hover.y / H) * 100}%`}>
          <div className="font-semibold mb-0.5">{MESES_ABR[meses[hover.i].mes - 1]}</div>
          <div>Ingresos: {EUR(meses[hover.i].ingresos)}</div>
          <div>Gastos: {EUR(meses[hover.i].gastos)}</div>
        </Tooltip>
      )}

      <div className="flex items-center gap-4 mt-2 text-xs text-gray-600">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: COLOR_INGRESO }} /> Ingresos
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: COLOR_GASTO }} /> Gastos
        </span>
      </div>
    </div>
  )
}

function TablaMensual({ meses }) {
  return (
    <div className="overflow-x-auto mt-4">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
            <th className="py-2 pr-3">Mes</th>
            <th className="py-2 pr-3 text-right">Ingresos</th>
            <th className="py-2 pr-3 text-right">Gastos</th>
            <th className="py-2 text-right">Resultado</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {meses.map((m) => {
            const resultado = (m.ingresos ?? 0) - (m.gastos ?? 0)
            return (
              <tr key={m.mes}>
                <td className="py-1.5 pr-3 text-gray-700">{MESES_ABR[m.mes - 1]}</td>
                <td className="py-1.5 pr-3 text-right text-green-700">{EUR(m.ingresos)}</td>
                <td className="py-1.5 pr-3 text-right text-red-600">{EUR(m.gastos)}</td>
                <td className={`py-1.5 text-right font-medium ${resultado >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                  {EUR(resultado)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function GraficoSaldo({ meses }) {
  const [hover, setHover] = useState(null)
  const valores = meses.map((m) => m.saldo)
  const min = Math.min(0, ...valores)
  const max = Math.max(1, ...valores)
  const rango = max - min || 1
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom

  const x = (i) => PAD.left + (plotW * i) / Math.max(1, meses.length - 1)
  const y = (v) => PAD.top + plotH - ((v - min) / rango) * plotH

  const puntos = meses.map((m, i) => `${x(i)},${y(m.saldo)}`).join(' ')

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + plotH * (1 - f)} y2={PAD.top + plotH * (1 - f)} stroke="#e5e7eb" strokeWidth="1" />
            <text x={PAD.left - 8} y={PAD.top + plotH * (1 - f) + 3} textAnchor="end" fontSize="10" fill="#9ca3af">
              {EUR0(min + rango * f)}
            </text>
          </g>
        ))}

        <polyline points={puntos} fill="none" stroke="#2563eb" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />

        {meses.map((m, i) => (
          <g key={m.mes}>
            <circle
              cx={x(i)} cy={y(m.saldo)} r={hover === i ? 5 : 3.5}
              fill="#2563eb" stroke="white" strokeWidth="1.5"
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
            />
            <text x={x(i)} y={H - 8} textAnchor="middle" fontSize="10" fill="#6b7280">
              {MESES_ABR[m.mes - 1]}
            </text>
          </g>
        ))}
      </svg>

      {hover !== null && (
        <Tooltip x={`${(x(hover) / W) * 100}%`} y={`${(y(meses[hover].saldo) / H) * 100}%`}>
          <div className="font-semibold mb-0.5">{MESES_ABR[meses[hover].mes - 1]}</div>
          <div>Saldo: {EUR(meses[hover].saldo)}</div>
        </Tooltip>
      )}
    </div>
  )
}

function GraficoCategorias({ categorias }) {
  const ordenadas = [...categorias].sort((a, b) => b.importe - a.importe)
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
                style={{ width: `${(c.importe / max) * 100}%`, background: COLORES_CATEGORIA[i % COLORES_CATEGORIA.length] }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function Panel({ titulo, subtitulo, children }) {
  return (
    <div className="card p-5">
      <h2 className="text-sm font-semibold text-gray-700 mb-0.5">{titulo}</h2>
      {subtitulo && <p className="text-xs text-gray-400 mb-4">{subtitulo}</p>}
      {!subtitulo && <div className="mb-4" />}
      {children}
    </div>
  )
}

export default function EstadisticasPage() {
  const { empresa } = useEmpresa()
  const [anios, setAnios] = useState([])
  const [anio, setAnio] = useState(null)
  const [data, setData] = useState(null)
  const [cargando, setCargando] = useState(false)

  useEffect(() => {
    if (!empresa) return
    getAniosEstadisticas(empresa.id).then((r) => {
      setAnios(r.anios)
      setAnio((prev) => prev ?? r.anios[0])
    })
  }, [empresa])

  useEffect(() => {
    if (!empresa || !anio) return
    setCargando(true)
    getEstadisticas(empresa.id, anio)
      .then(setData)
      .catch(() => {})
      .finally(() => setCargando(false))
  }, [empresa, anio])

  if (!empresa) {
    return <div className="p-8 text-center text-gray-400">Selecciona una empresa para ver las estadísticas.</div>
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="px-6 pt-5 pb-4 border-b border-gray-200 bg-gray-50 flex-shrink-0 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Estadísticas</h1>
          <p className="text-gray-500 text-sm">{empresa.nombre}</p>
        </div>
        {anios.length > 0 && (
          <select
            className="input w-32"
            value={anio ?? ''}
            onChange={(e) => setAnio(Number(e.target.value))}
          >
            {anios.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        )}
      </div>

      <div className="flex-1 p-6 space-y-6">
        {cargando && <p className="text-sm text-gray-400 text-center py-8">Cargando estadísticas…</p>}

        {data && !cargando && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div className="card px-5 py-4">
                <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">Ingresos {anio}</p>
                <p className="text-2xl font-bold text-green-700">{EUR(data.ingresos_total)}</p>
              </div>
              <div className="card px-5 py-4">
                <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">Gastos {anio}</p>
                <p className="text-2xl font-bold text-red-600">{EUR(data.gastos_total)}</p>
              </div>
            </div>

            <Panel titulo="Ingresos y gastos por mes">
              <GraficoMensual meses={data.meses} />
              <TablaMensual meses={data.meses} />
            </Panel>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Panel titulo="Gastos por categoría" subtitulo={`Año ${anio}`}>
                <GraficoCategorias categorias={data.categorias_gasto} />
              </Panel>
              <Panel titulo="Saldo bancario total" subtitulo="Fin de cada mes">
                <GraficoSaldo meses={data.saldos_bancos} />
              </Panel>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
