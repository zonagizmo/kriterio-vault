import { useState } from 'react'
import { getDiagnostico, generarPendientes, regenerarAsientoBanco } from '../../services/contabilidad'
import { EUR, fmtFecha } from './utils'
import ConfirmModal from '../../components/ConfirmModal'

export default function TabDiagnostico({ empresa }) {
  const [data, setData] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [reparando, setReparando] = useState(false)
  const [resultado, setResultado] = useState(null)
  const [regenInfo, setRegenInfo] = useState({})
  const [confirmState, setConfirmState] = useState({ open: false, msg: '', action: null })

  const analizar = async () => {
    setCargando(true)
    setResultado(null)
    try {
      const res = await getDiagnostico(empresa.id)
      setData(res)
    } finally {
      setCargando(false)
    }
  }

  const reparar = async () => {
    setConfirmState({
      open: true,
      msg: '¿Generar todos los asientos pendientes? Esta acción no es reversible.',
      action: async () => {
        setReparando(true)
        try {
          const res = await generarPendientes(empresa.id)
          setResultado(res)
          await analizar()
        } catch (e) {
          alert('Error al generar asientos: ' + (e.response?.data?.detail || e.message))
        } finally {
          setReparando(false)
        }
      },
    })
  }

  const regenerarMov = async (banco, numero) => {
    setRegenInfo((r) => ({ ...r, [`${banco}-${numero}`]: 'generando...' }))
    try {
      const res = await regenerarAsientoBanco(empresa.id, banco, numero)
      const msg = res.regenerado ? `Asiento ${res.asiento} creado` : `No generado: ${res.motivo}`
      setRegenInfo((r) => ({ ...r, [`${banco}-${numero}`]: msg }))
      if (res.regenerado) await analizar()
    } catch (e) {
      setRegenInfo((r) => ({ ...r, [`${banco}-${numero}`]: 'Error: ' + (e.response?.data?.detail || e.message) }))
    }
  }

  const total = data ? data.total_problemas : null

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button className="btn btn-primary" onClick={analizar} disabled={cargando}>
          {cargando ? 'Analizando...' : 'Analizar contabilidad'}
        </button>
        {data && total === 0 && (
          <span className="inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1 rounded-full bg-green-100 text-green-700">
            ✓ Sin problemas detectados
          </span>
        )}
        {data && total > 0 && (
          <button className="btn btn-warning" onClick={reparar} disabled={reparando}>
            {reparando ? 'Reparando...' : `Reparar todo (${total} problemas)`}
          </button>
        )}
      </div>

      {resultado && (
        <div className="p-3 rounded-lg bg-blue-50 border border-blue-200 text-sm text-blue-800">
          Generados: <strong>{resultado.extras}</strong> asientos de extras, <strong>{resultado.banco}</strong> de
          banco, <strong>{resultado.facturas_rec}</strong> de facturas recibidas,{' '}
          <strong>{resultado.facturas_emi}</strong> de facturas emitidas. Total: <strong>{resultado.total}</strong>
        </div>
      )}

      {data && (
        <>
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Extras con apuntes completos sin asiento contable{' '}
              <span
                className={`ml-1 px-2 py-0.5 rounded-full text-xs font-bold ${
                  data.extras_sin_asiento.length > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                }`}
              >
                {data.extras_sin_asiento.length}
              </span>
            </h3>
            {data.extras_sin_asiento.length === 0 ? (
              <p className="text-sm text-gray-400">Ninguno. Todos los extras con apuntes D+H tienen asiento.</p>
            ) : (
              <table className="w-full text-xs border border-gray-200 rounded">
                <thead>
                  <tr className="bg-gray-50 text-gray-500 uppercase">
                    <th className="text-left px-3 py-2 w-16">N.º</th>
                    <th className="text-left px-3 py-2 w-24">Fecha</th>
                    <th className="text-left px-3 py-2 w-16">Estado</th>
                    <th className="text-left px-3 py-2">Descripción</th>
                  </tr>
                </thead>
                <tbody>
                  {data.extras_sin_asiento.map((x) => (
                    <tr key={x.numero} className="border-t border-gray-200">
                      <td className="px-3 py-1.5 font-mono">{x.numero}</td>
                      <td className="px-3 py-1.5">{fmtFecha(x.fecha)}</td>
                      <td className="px-3 py-1.5">
                        <span
                          className={`px-1.5 py-0.5 rounded text-xs font-semibold ${
                            x.estado === 'C' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                          }`}
                        >
                          {x.estado || '—'}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-gray-600">{x.texto}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Movimientos bancarios con pagos pero sin asiento{' '}
              <span
                className={`ml-1 px-2 py-0.5 rounded-full text-xs font-bold ${
                  data.movimientos_sin_asiento.length > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                }`}
              >
                {data.movimientos_sin_asiento.length}
              </span>
            </h3>
            {data.movimientos_sin_asiento.length === 0 ? (
              <p className="text-sm text-gray-400">
                Ninguno. Todos los movimientos tienen asiento o no tienen pagos asociados.
              </p>
            ) : (
              <table className="w-full text-xs border border-gray-200 rounded">
                <thead>
                  <tr className="bg-gray-50 text-gray-500 uppercase">
                    <th className="text-left px-3 py-2 w-16">N.º</th>
                    <th className="text-left px-3 py-2 w-24">Fecha</th>
                    <th className="text-left px-3 py-2">Banco</th>
                    <th className="text-left px-3 py-2">Texto</th>
                    <th className="text-right px-3 py-2 w-28">Total</th>
                    <th className="px-3 py-2 w-24"></th>
                  </tr>
                </thead>
                <tbody>
                  {data.movimientos_sin_asiento.map((m) => {
                    const key = `${m.banco}-${m.numero}`
                    const info = regenInfo[key]
                    return (
                      <tr key={key} className="border-t border-gray-200">
                        <td className="px-3 py-1.5 font-mono">{m.numero}</td>
                        <td className="px-3 py-1.5">{fmtFecha(m.fecha)}</td>
                        <td className="px-3 py-1.5 text-gray-600">{m.banco_nombre}</td>
                        <td className="px-3 py-1.5 text-gray-600">
                          {m.texto}
                          {info && (
                            <span
                              className={`ml-2 text-xs ${info.startsWith('Error') ? 'text-red-600' : 'text-blue-600'}`}
                            >
                              {info}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-1.5 text-right font-mono">{EUR(m.total)}</td>
                        <td className="px-3 py-1.5 text-right">
                          <button
                            className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700 hover:bg-blue-200"
                            onClick={() => regenerarMov(m.banco, m.numero)}
                            disabled={info === 'generando...'}
                          >
                            Generar
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </section>

          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Cuentas de proveedor desequilibradas{' '}
              <span
                className={`ml-1 px-2 py-0.5 rounded-full text-xs font-bold ${
                  data.cuentas_desequilibradas.length > 0
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-green-100 text-green-700'
                }`}
              >
                {data.cuentas_desequilibradas.length}
              </span>
            </h3>
            <p className="text-xs text-gray-400 mb-2">
              Un saldo deudor en cuentas de proveedor indica que se han registrado más pagos que deudas — síntoma
              habitual de asientos de extras incompletos.
            </p>
            {data.cuentas_desequilibradas.length === 0 ? (
              <p className="text-sm text-gray-400">
                Ninguna. Todas las cuentas de proveedor tienen saldo normal (acreedor o cero).
              </p>
            ) : (
              <table className="w-full text-xs border border-gray-200 rounded">
                <thead>
                  <tr className="bg-gray-50 text-gray-500 uppercase">
                    <th className="text-left px-3 py-2 w-32">Cuenta</th>
                    <th className="text-left px-3 py-2">Descripción</th>
                    <th className="text-right px-3 py-2 w-28">Saldo deudor</th>
                  </tr>
                </thead>
                <tbody>
                  {data.cuentas_desequilibradas.map((c) => (
                    <tr key={c.cuenta} className="border-t border-gray-200">
                      <td className="px-3 py-1.5 font-mono text-amber-700">{c.cuenta}</td>
                      <td className="px-3 py-1.5 text-gray-600">{c.texto}</td>
                      <td className="px-3 py-1.5 text-right font-mono font-semibold text-amber-700">
                        {EUR(c.saldo_deudor)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}

      {!data && !cargando && (
        <p className="text-sm text-gray-400">
          Pulsa &quot;Analizar contabilidad&quot; para detectar posibles inconsistencias: extras sin asiento,
          movimientos bancarios pendientes y cuentas de proveedor desequilibradas.
        </p>
      )}

      <ConfirmModal
        open={confirmState.open}
        title="Generar asientos"
        message={confirmState.msg}
        confirmText="Generar"
        variant="warning"
        onConfirm={async () => {
          await confirmState.action()
          setConfirmState({ open: false, msg: '', action: null })
        }}
        onCancel={() => setConfirmState({ open: false, msg: '', action: null })}
      />
    </div>
  )
}
