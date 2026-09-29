import { useState } from 'react'
import Modal from '../../components/Modal'
import ConfirmModal from '../../components/ConfirmModal'
import { getBalance, realizarCierre, exportarCSV } from '../../services/contabilidad'
import { usePermissions } from '../../hooks/usePermissions'
import { EUR, anioActual } from './utils'

function ModalCierre({ empresa, onClose, onDone }) {
  const [anio, setAnio] = useState(anioActual - 1)
  const [apertura, setApertura] = useState(true)
  const [cargando, setCargando] = useState(false)
  const [resultado, setResultado] = useState(null)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const ejecutar = async () => {
    setConfirmOpen(true)
  }

  const confirmarCierre = async () => {
    setConfirmOpen(false)
    setCargando(true)
    try {
      const res = await realizarCierre(empresa.id, anio, apertura)
      setResultado(res)
      onDone()
    } catch (e) {
      alert('Error: ' + (e.response?.data?.detail || e.message))
    } finally {
      setCargando(false)
    }
  }

  return (
    <Modal title="Cierre de ejercicio" onClose={onClose} size="sm">
      <div className="space-y-4">
        {resultado ? (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-800 space-y-1">
            <div className="font-semibold">Cierre realizado correctamente</div>
            <div>Regularización: {resultado.regularizacion} apuntes</div>
            <div>Cierre: {resultado.cierre} apuntes</div>
            {resultado.apertura > 0 && <div>Apertura: {resultado.apertura} apuntes</div>}
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-600">
              Se generarán los asientos contables de fin de año para el ejercicio seleccionado: regularización (cuentas
              6/7 → 129), cierre (saldo a cero) y, opcionalmente, apertura del ejercicio siguiente.
            </p>
            <div>
              <label className="label">Ejercicio a cerrar</label>
              <input
                type="number"
                className="input w-32"
                value={anio}
                min={2000}
                max={2099}
                onChange={(e) => setAnio(parseInt(e.target.value))}
              />
            </div>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={apertura}
                onChange={(e) => setApertura(e.target.checked)}
                className="rounded"
              />
              Crear también asiento de apertura ({anio + 1})
            </label>
            <div className="flex gap-2 justify-end pt-2">
              <button className="btn btn-secondary" onClick={onClose}>
                Cancelar
              </button>
              <button className="btn bg-amber-600 hover:bg-amber-700 text-white" onClick={ejecutar} disabled={cargando}>
                {cargando ? 'Procesando...' : `Cerrar ejercicio ${anio}`}
              </button>
            </div>
          </>
        )}
        {resultado && (
          <div className="flex justify-end">
            <button className="btn btn-primary" onClick={onClose}>
              Cerrar
            </button>
          </div>
        )}
      </div>

      <ConfirmModal
        open={confirmOpen}
        title="Cierre de ejercicio"
        message={`¿Realizar cierre del ejercicio ${anio}?\n\nEsto creará los asientos de regularización, cierre${apertura ? ' y apertura' : ''}.\nEsta acción no se puede deshacer fácilmente.`}
        confirmText="Cerrar ejercicio"
        variant="warning"
        onConfirm={confirmarCierre}
        onCancel={() => setConfirmOpen(false)}
      />
    </Modal>
  )
}

const SeccionBalance = ({ titulo, filas, total, colorTotal, colorFondo }) => (
  <div className="mb-3">
    <div className={`px-4 py-2 font-semibold text-sm uppercase tracking-wide rounded-t-lg border ${colorFondo}`}>
      {titulo}
    </div>
    <div className="border border-t-0 border-gray-200 rounded-b-lg overflow-hidden">
      <table className="w-full text-sm">
        <tbody className="divide-y divide-gray-100">
          {filas.length === 0 ? (
            <tr>
              <td colSpan={2} className="px-4 py-3 text-center text-gray-400 text-xs">
                Sin movimientos
              </td>
            </tr>
          ) : (
            filas.map((f) => (
              <tr key={f.cuenta} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-gray-800 w-32">{f.cuenta}</td>
                <td className="px-4 py-2 text-gray-600 text-xs">{f.texto}</td>
                <td className="px-4 py-2 text-right font-mono text-xs">{EUR(f.importe)}</td>
              </tr>
            ))
          )}
        </tbody>
        <tfoot className="bg-gray-50 border-t-2 border-gray-300 font-bold">
          <tr>
            <td colSpan={2} className="px-4 py-2 text-gray-700 text-sm">
              Total
            </td>
            <td className={`px-4 py-2 text-right font-mono text-sm ${colorTotal}`}>{EUR(total)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
)

export default function TabBalance({ empresa }) {
  const { has } = usePermissions()
  const [fechaDesde, setFechaDesde] = useState(`${anioActual - 1}-01-01`)
  const [fechaHasta, setFechaHasta] = useState(`${anioActual - 1}-12-31`)
  const [data, setData] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [modalCierre, setModalCierre] = useState(false)

  const consultar = async () => {
    setCargando(true)
    try {
      const params = { empresa_id: empresa.id }
      if (fechaDesde) params.fecha_desde = fechaDesde
      if (fechaHasta) params.fecha_hasta = fechaHasta
      const res = await getBalance(params)
      setData(res)
    } finally {
      setCargando(false)
    }
  }

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
              exportarCSV('balance', { empresa_id: empresa.id, fecha_desde: fechaDesde, fecha_hasta: fechaHasta })
            }
          >
            Exportar CSV
          </button>
        )}
        {has('create') && (
          <button
            className="btn self-end bg-amber-600 hover:bg-amber-700 text-white"
            onClick={() => setModalCierre(true)}
          >
            Cierre de ejercicio
          </button>
        )}
      </div>

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-5xl">
          <div>
            <h3 className="text-base font-bold text-gray-800 mb-3">ACTIVO</h3>
            <SeccionBalance
              titulo="Activo No Corriente"
              filas={data.activo_no_corriente}
              total={data.total_anc}
              colorTotal="text-blue-700"
              colorFondo="bg-blue-50 border-blue-200 text-blue-800"
            />
            <SeccionBalance
              titulo="Activo Corriente"
              filas={data.activo_corriente}
              total={data.total_ac}
              colorTotal="text-blue-700"
              colorFondo="bg-blue-50 border-blue-200 text-blue-800"
            />
            <div className="card p-4 flex justify-between items-center font-bold text-base border-2 border-blue-400 bg-blue-50 mt-2">
              <span>TOTAL ACTIVO</span>
              <span className="text-blue-700">{EUR(data.total_activo)}</span>
            </div>
          </div>

          <div>
            <h3 className="text-base font-bold text-gray-800 mb-3">PASIVO Y PATRIMONIO NETO</h3>
            <SeccionBalance
              titulo="Patrimonio Neto"
              filas={[
                ...data.patrimonio_neto,
                { cuenta: '1290000', texto: 'Resultado del ejercicio', importe: Math.abs(data.resultado_ejercicio) },
              ]}
              total={data.total_pn}
              colorTotal="text-purple-700"
              colorFondo="bg-purple-50 border-purple-200 text-purple-800"
            />
            <SeccionBalance
              titulo="Pasivo No Corriente"
              filas={data.pasivo_no_corriente}
              total={data.total_pnc}
              colorTotal="text-red-700"
              colorFondo="bg-red-50 border-red-200 text-red-800"
            />
            <SeccionBalance
              titulo="Pasivo Corriente"
              filas={data.pasivo_corriente}
              total={data.total_pc}
              colorTotal="text-red-700"
              colorFondo="bg-red-50 border-red-200 text-red-800"
            />
            <div className="card p-4 flex justify-between items-center font-bold text-base border-2 border-red-400 bg-red-50 mt-2">
              <span>TOTAL PASIVO + PN</span>
              <span
                className={Math.abs(data.total_activo - data.total_pasivo_pn) > 0.5 ? 'text-red-600' : 'text-red-700'}
              >
                {EUR(data.total_pasivo_pn)}
              </span>
            </div>
            {Math.abs(data.total_activo - data.total_pasivo_pn) > 0.5 && (
              <div className="mt-2 text-xs text-red-600 font-semibold text-right">
                Diferencia: {EUR(Math.abs(data.total_activo - data.total_pasivo_pn))}
              </div>
            )}
          </div>
        </div>
      )}

      {modalCierre && <ModalCierre empresa={empresa} onClose={() => setModalCierre(false)} onDone={consultar} />}
    </div>
  )
}
