import { useState } from 'react'
import { getConciliacion, regenerarAsientoBanco } from '../../services/contabilidad'
import { EUR, fmtFecha } from './utils'
import { usePermissions } from '../../hooks/usePermissions'

function FilaBanco({ b, empresaId, onRefresh }) {
  const { has } = usePermissions()
  const [abierto, setAbierto] = useState(false)
  const [corrigiendo, setCorrigiendo] = useState(null)
  const [avisos, setAvisos] = useState({})

  const sinAsiento = b.detalle.filter((p) => p.tipo === 'sin_asiento')
  const importeDiff = b.detalle.filter((p) => p.tipo === 'importe_diff')
  const huerfanos = b.detalle.filter((p) => p.tipo === 'asiento_huerfano')

  const corregir = async (numero) => {
    setCorrigiendo(numero)
    setAvisos((a) => {
      const n = { ...a }
      delete n[numero]
      return n
    })
    try {
      const res = await regenerarAsientoBanco(empresaId, b.banco, numero)
      if (!res.regenerado) {
        setAvisos((a) => ({ ...a, [numero]: res.motivo }))
      }
      await onRefresh()
    } catch (e) {
      alert('Error al regenerar asiento: ' + (e.response?.data?.detail || e.message))
    } finally {
      setCorrigiendo(null)
    }
  }

  return (
    <>
      <tr
        className={`cursor-pointer hover:bg-gray-50 ${!b.ok ? 'bg-red-50' : ''}`}
        onClick={() => setAbierto(!abierto)}
      >
        <td className="px-4 py-2.5">
          <span
            className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${
              !b.ok ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
            }`}
          >
            {!b.ok ? '✗ Discrepancia' : '✓ OK'}
          </span>
        </td>
        <td className="px-4 py-2.5 font-medium text-gray-800">{b.nombre}</td>
        <td className="px-4 py-2.5 font-mono text-sm text-gray-600">{b.cuenta}</td>
        <td className="px-4 py-2.5 text-right font-mono text-sm text-gray-700">{EUR(b.saldo_banco)}</td>
        <td className="px-4 py-2.5 text-right font-mono text-sm text-gray-700">{EUR(b.saldo_lm)}</td>
        <td
          className={`px-4 py-2.5 text-right font-mono text-sm font-bold ${Math.abs(b.diferencia) >= 0.01 ? 'text-red-600' : 'text-gray-400'}`}
        >
          {Math.abs(b.diferencia) >= 0.01 ? EUR(b.diferencia) : '—'}
        </td>
        <td className="px-4 py-2.5 text-center text-gray-400 text-xs">{abierto ? '▲' : '▼'}</td>
      </tr>

      {abierto && (
        <tr>
          <td colSpan={7} className="bg-gray-50 px-6 pb-4 pt-2">
            {b.ok && <p className="text-green-600 text-sm">Sin discrepancias. Saldo banco y libro mayor coinciden.</p>}

            {!b.ok && Math.abs(b.base_lm) >= 0.01 && (
              <p className="text-xs text-gray-500 mb-3">
                Base libro mayor (apertura / migrados):{' '}
                <span className="font-mono font-semibold">{EUR(b.base_lm)}</span>
              </p>
            )}

            {sinAsiento.length > 0 && (
              <div className="mb-4">
                <p className="text-sm font-semibold text-red-700 mb-1">
                  Movimientos sin asiento contable ({sinAsiento.length})
                </p>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 uppercase border-b">
                      <th className="text-left pb-1 pr-3 w-16">N.º</th>
                      <th className="text-left pb-1 pr-3 w-24">Fecha</th>
                      <th className="text-left pb-1">Texto</th>
                      <th className="text-right pb-1 w-28">Total banco</th>
                      <th className="text-right pb-1 w-28">Saldo banco</th>
                      <th className="w-20"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {sinAsiento.map((p) => (
                      <tr key={p.numero} className="border-t border-gray-200">
                        <td className="py-1 pr-3 font-mono">{p.numero}</td>
                        <td className="py-1 pr-3">{fmtFecha(p.fecha)}</td>
                        <td className="py-1 text-gray-600">
                          {p.texto}
                          {avisos[p.numero] && (
                            <span className="ml-2 text-amber-600 text-xs">⚠ {avisos[p.numero]}</span>
                          )}
                        </td>
                        <td className="py-1 text-right font-mono text-red-600">{EUR(p.total_banco)}</td>
                        <td className="py-1 text-right font-mono text-gray-500">
                          {p.saldo_banco != null ? EUR(p.saldo_banco) : '—'}
                        </td>
                        <td className="py-1 text-right">
                          {p.es_transferencia ? (
                            <span className="text-xs text-amber-600 italic">transferencia</span>
                          ) : has('create') ? (
                            <button
                              className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700 hover:bg-blue-200 disabled:opacity-50"
                              disabled={corrigiendo === p.numero}
                              onClick={() => corregir(p.numero)}
                            >
                              {corrigiendo === p.numero ? '...' : 'Generar'}
                            </button>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {importeDiff.length > 0 && (
              <div className="mb-4">
                <p className="text-sm font-semibold text-amber-700 mb-1">
                  Importes no coinciden ({importeDiff.length})
                </p>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 uppercase border-b">
                      <th className="text-left pb-1 pr-3 w-16">N.º</th>
                      <th className="text-left pb-1 pr-3 w-24">Fecha</th>
                      <th className="text-left pb-1">Texto</th>
                      <th className="text-right pb-1 w-28">Banco</th>
                      <th className="text-right pb-1 w-28">Libro mayor</th>
                      <th className="text-right pb-1 w-24">Diferencia</th>
                      <th className="w-20"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {importeDiff.map((p) => (
                      <tr key={p.numero} className="border-t border-gray-200">
                        <td className="py-1 pr-3 font-mono">{p.numero}</td>
                        <td className="py-1 pr-3">{fmtFecha(p.fecha)}</td>
                        <td className="py-1 text-gray-600">
                          {p.texto}
                          {avisos[p.numero] && (
                            <span className="ml-2 text-amber-600 text-xs">⚠ {avisos[p.numero]}</span>
                          )}
                        </td>
                        <td className="py-1 text-right font-mono">{EUR(p.total_banco)}</td>
                        <td className="py-1 text-right font-mono text-amber-700">{EUR(p.total_lm)}</td>
                        <td className="py-1 text-right font-mono text-red-600">{EUR(p.diferencia)}</td>
                        <td className="py-1 text-right">
                          {has('create') && (
                            <button
                              className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-700 hover:bg-amber-200 disabled:opacity-50"
                              disabled={corrigiendo === p.numero}
                              onClick={() => corregir(p.numero)}
                            >
                              {corrigiendo === p.numero ? '...' : 'Corregir'}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {huerfanos.length > 0 && (
              <div className="mb-2">
                <p className="text-sm font-semibold text-gray-500 mb-1">
                  Asientos sin movimiento bancario ({huerfanos.length})
                </p>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 uppercase border-b">
                      <th className="text-left pb-1 pr-3 w-16">N.º</th>
                      <th className="text-left pb-1">Descripción</th>
                      <th className="text-right pb-1 w-28">Importe LM</th>
                    </tr>
                  </thead>
                  <tbody>
                    {huerfanos.map((p) => (
                      <tr key={p.numero} className="border-t border-gray-200">
                        <td className="py-1 pr-3 font-mono">{p.numero}</td>
                        <td className="py-1 text-gray-500 italic">{p.texto}</td>
                        <td className="py-1 text-right font-mono text-gray-500">{EUR(p.total_lm)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

export default function TabConciliacion({ empresa }) {
  const { has } = usePermissions()
  const [data, setData] = useState(null)
  const [cargando, setCargando] = useState(false)

  const consultar = async () => {
    setCargando(true)
    try {
      const res = await getConciliacion(empresa.id)
      setData(res)
    } finally {
      setCargando(false)
    }
  }

  const nOK = data ? data.filter((b) => b.ok).length : 0
  const nDisc = data ? data.filter((b) => !b.ok).length : 0

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <button className="btn btn-primary" onClick={consultar} disabled={cargando}>
          {cargando ? 'Analizando...' : 'Analizar discrepancias'}
        </button>
        {data && (
          <div className="flex gap-4 text-sm">
            <span className="text-green-700 font-medium">
              {nOK} banco{nOK !== 1 ? 's' : ''} OK
            </span>
            {nDisc > 0 && <span className="text-red-600 font-medium">{nDisc} con discrepancias</span>}
          </div>
        )}
      </div>

      {data && (
        <div className="card">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase w-32">Estado</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Banco</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Cuenta</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Saldo banco</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">
                  Saldo libro mayor
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Diferencia</th>
                <th className="px-4 py-3 w-8"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((b) => (
                <FilaBanco key={b.banco} b={b} empresaId={empresa.id} onRefresh={consultar} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
