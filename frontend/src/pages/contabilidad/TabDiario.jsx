import { useState, useEffect, useCallback } from 'react'
import Modal from '../../components/Modal'
import ConfirmModal from '../../components/ConfirmModal'
import Paginacion from '../../components/Paginacion'
import AutocompleteCuenta from '../../components/AutocompleteCuenta'
import {
  getAsientos,
  createAsiento,
  updateAsiento,
  deleteAsiento,
  generarPendientes,
  exportarCSV,
} from '../../services/contabilidad'
import { EUR, fmtFecha, anioActual } from './utils'

const hoy = () => new Date().toISOString().slice(0, 10)

const TIPOS_ASIENTO = [
  { value: '', label: '— Tipo —' },
  { value: 'A', label: 'A — Apertura' },
  { value: 'D', label: 'D — Diario' },
  { value: 'ENV', label: 'ENV — Facturas enviadas' },
  { value: 'REC', label: 'REC — Facturas recibidas' },
  { value: 'EXT', label: 'EXT — Extras' },
  { value: 'R', label: 'R — Regularización' },
  { value: 'Z', label: 'Z — Cierre' },
  { value: 'M', label: 'M — Migración' },
]

function FilaAsiento({ asiento, _empresa, onDelete, onEdit }) {
  const [abierto, setAbierto] = useState(false)

  const cuadrado = asiento.cuadrado
  const diff = Math.abs(asiento.total_debe - asiento.total_haber)

  return (
    <>
      <tr className="hover:bg-gray-50 cursor-pointer select-none" onClick={() => setAbierto(!abierto)}>
        <td className="px-4 py-2.5 text-gray-500 font-mono">{asiento.asiento}</td>
        <td className="px-4 py-2.5 text-gray-600">{fmtFecha(asiento.fecha)}</td>
        <td className="px-4 py-2.5">
          <span className="inline-flex px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600 font-medium">
            {asiento.tpasiento || '—'}
          </span>
        </td>
        <td className="px-4 py-2.5 text-gray-700">{asiento.clave}</td>
        <td className="px-4 py-2.5 text-right font-mono text-xs text-gray-700">{EUR(asiento.total_debe)}</td>
        <td className="px-4 py-2.5 text-right font-mono text-xs text-gray-700">{EUR(asiento.total_haber)}</td>
        <td className="px-4 py-2.5 text-center">
          <span
            className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${cuadrado ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}
          >
            {cuadrado ? '✓' : `${EUR(diff)}`}
          </span>
        </td>
        <td className="px-4 py-2.5 text-right">
          <span className="text-gray-400 text-xs mr-2">{asiento.lineas.length} líneas</span>
          <button
            className="btn btn-secondary text-xs mr-1"
            onClick={(e) => {
              e.stopPropagation()
              onEdit(asiento)
            }}
          >
            Editar
          </button>
          <button
            className="btn btn-danger text-xs"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(asiento)
            }}
          >
            Eliminar
          </button>
        </td>
      </tr>
      {abierto && (
        <tr>
          <td colSpan={8} className="bg-blue-50 px-6 pb-3 pt-1">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 uppercase">
                  <th className="text-left pb-1 pr-4">Cuenta</th>
                  <th className="text-right pb-1 pr-4">Debe</th>
                  <th className="text-right pb-1">Haber</th>
                </tr>
              </thead>
              <tbody>
                {asiento.lineas.map((l) => (
                  <tr key={l.id} className="border-t border-blue-100">
                    <td className="pr-4 py-1 font-mono text-gray-700">{l.cuenta}</td>
                    <td className="pr-4 py-1 text-right font-mono text-green-700">
                      {(l.importe ?? 0) > 0 ? EUR(l.importe) : ''}
                    </td>
                    <td className="py-1 text-right font-mono text-red-600">
                      {(l.importe ?? 0) < 0 ? EUR(Math.abs(l.importe)) : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </td>
        </tr>
      )}
    </>
  )
}

function AsientoModal({ empresa, onClose, onGuardado, asientoEditar = null }) {
  const esEdicion = asientoEditar !== null

  const [form, setForm] = useState(() =>
    esEdicion
      ? { fecha: asientoEditar.fecha, tpasiento: asientoEditar.tpasiento || '', clave: asientoEditar.clave || '' }
      : { fecha: hoy(), tpasiento: '', clave: '' },
  )
  const [lineas, setLineas] = useState(() =>
    esEdicion
      ? asientoEditar.lineas.map((l) => ({
          cuenta: l.cuenta || '',
          debe: (l.importe ?? 0) > 0 ? String(l.importe) : '',
          haber: (l.importe ?? 0) < 0 ? String(Math.abs(l.importe)) : '',
        }))
      : [
          { cuenta: '', debe: '', haber: '' },
          { cuenta: '', debe: '', haber: '' },
        ],
  )
  const [error, setError] = useState('')

  const setLinea = (i, field, val) => {
    const arr = [...lineas]
    arr[i] = { ...arr[i], [field]: val }
    if (field === 'debe' && val) arr[i].haber = ''
    if (field === 'haber' && val) arr[i].debe = ''
    setLineas(arr)
  }

  const addLinea = () => setLineas([...lineas, { cuenta: '', debe: '', haber: '' }])
  const removeLinea = (i) => setLineas(lineas.filter((_, idx) => idx !== i))

  const totalDebe = lineas.reduce((s, l) => s + (parseFloat(l.debe) || 0), 0)
  const totalHaber = lineas.reduce((s, l) => s + (parseFloat(l.haber) || 0), 0)
  const cuadrado = Math.abs(totalDebe - totalHaber) < 0.01 && totalDebe > 0

  const guardar = async () => {
    if (!form.fecha) {
      setError('La fecha es obligatoria')
      return
    }
    if (!cuadrado) {
      setError(`El asiento no está cuadrado (D: ${EUR(totalDebe)} / H: ${EUR(totalHaber)})`)
      return
    }
    const lineasValidas = lineas.filter((l) => l.cuenta && (l.debe || l.haber))
    if (lineasValidas.length < 2) {
      setError('Mínimo 2 líneas con cuenta e importe')
      return
    }
    try {
      const payload = {
        empresa_id: empresa.id,
        fecha: form.fecha,
        tpasiento: form.tpasiento || null,
        clave: form.clave || null,
        lineas: lineasValidas.map((l) => ({
          cuenta: l.cuenta,
          importe: l.debe ? parseFloat(l.debe) : -parseFloat(l.haber),
        })),
      }
      if (esEdicion) {
        await updateAsiento(asientoEditar.asiento, payload)
      } else {
        await createAsiento(payload)
      }
      onGuardado()
      onClose()
    } catch {
      setError('Error al guardar el asiento')
    }
  }

  return (
    <Modal
      titulo={esEdicion ? `Editar asiento #${asientoEditar.asiento}` : 'Nuevo asiento contable'}
      onClose={onClose}
      ancho="max-w-3xl"
    >
      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div>
          <label className="label">Fecha *</label>
          <input
            type="date"
            className="input"
            value={form.fecha}
            onChange={(e) => setForm({ ...form, fecha: e.target.value })}
          />
        </div>
        <div>
          <label className="label">Tipo asiento</label>
          <select
            className="input"
            value={form.tpasiento}
            onChange={(e) => setForm({ ...form, tpasiento: e.target.value })}
          >
            {TIPOS_ASIENTO.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Referencia</label>
          <input className="input" value={form.clave} onChange={(e) => setForm({ ...form, clave: e.target.value })} />
        </div>
      </div>

      <div className="border rounded-lg overflow-hidden mb-3">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Cuenta</th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500 uppercase w-32">Debe</th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500 uppercase w-32">Haber</th>
              <th className="px-3 py-2 w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {lineas.map((l, i) => (
              <tr key={i}>
                <td className="px-3 py-1.5">
                  <AutocompleteCuenta
                    empresaId={empresa.id}
                    value={l.cuenta}
                    onChange={(v) => setLinea(i, 'cuenta', v)}
                    className="w-full"
                  />
                </td>
                <td className="px-3 py-1.5">
                  <input
                    className="input text-right font-mono text-xs"
                    value={l.debe}
                    onChange={(e) => setLinea(i, 'debe', e.target.value)}
                    placeholder="0,00"
                  />
                </td>
                <td className="px-3 py-1.5">
                  <input
                    className="input text-right font-mono text-xs"
                    value={l.haber}
                    onChange={(e) => setLinea(i, 'haber', e.target.value)}
                    placeholder="0,00"
                  />
                </td>
                <td className="px-3 py-1.5 text-center">
                  {lineas.length > 2 && (
                    <button className="text-red-400 hover:text-red-600 text-xs" onClick={() => removeLinea(i)}>
                      ✕
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-3 mb-3">
        <button className="btn btn-secondary text-xs" onClick={addLinea}>
          + Añadir línea
        </button>
        <div className="flex-1" />
        <span className="text-sm font-mono mr-3">
          D: {EUR(totalDebe)} / H: {EUR(totalHaber)}
        </span>
        {cuadrado ? (
          <span className="text-green-600 text-xs">✓ Cuadrado</span>
        ) : (
          <span className="text-amber-600 text-xs">Diferencia: {EUR(Math.abs(totalDebe - totalHaber))}</span>
        )}
      </div>

      <div className="flex justify-end gap-3 mt-6">
        <button className="btn btn-secondary" onClick={onClose}>
          Cancelar
        </button>
        <button className="btn btn-primary" onClick={guardar} disabled={!cuadrado}>
          Guardar asiento
        </button>
      </div>
    </Modal>
  )
}

export default function TabDiario({ empresa }) {
  const [fechaDesde, setFechaDesde] = useState(`${anioActual}-01-01`)
  const [fechaHasta, setFechaHasta] = useState(hoy())
  const [cuentaFiltro, setCuentaFiltro] = useState('')
  const [orden, setOrden] = useState('fecha')
  const [asientos, setAsientos] = useState([])
  const [total, setTotal] = useState(0)
  const [pagina, setPagina] = useState(1)
  const [limit, setLimit] = useState(30)
  const [modalNuevo, setModalNuevo] = useState(false)
  const [modalEditar, setModalEditar] = useState(null)
  const [generando, setGenerando] = useState(false)
  const [confirmState, setConfirmState] = useState({ open: false, msg: '', action: null, variant: 'danger', title: '' })

  const cargar = useCallback(async () => {
    const params = { empresa_id: empresa.id, skip: (pagina - 1) * limit, limit }
    if (fechaDesde) params.fecha_desde = fechaDesde
    if (fechaHasta) params.fecha_hasta = fechaHasta
    if (cuentaFiltro) params.cuenta = cuentaFiltro
    params.orden = orden
    const data = await getAsientos(params)
    setAsientos(data.items)
    setTotal(data.total)
  }, [empresa.id, fechaDesde, fechaHasta, cuentaFiltro, orden, pagina, limit])

  useEffect(() => {
    cargar()
  }, [cargar])
  useEffect(() => {
    setPagina(1)
  }, [fechaDesde, fechaHasta, cuentaFiltro, orden])

  const eliminar = async (a) => {
    setConfirmState({
      open: true,
      title: 'Eliminar asiento',
      msg: `¿Eliminar el asiento #${a.asiento}? Esta acción es irreversible.`,
      confirmText: 'Eliminar',
      variant: 'danger',
      action: async () => {
        try {
          await deleteAsiento(a.asiento, empresa.id)
          cargar()
        } catch (err) {
          if (err.response?.status === 409) {
            const detalle = err.response?.data?.detail || 'El asiento está vinculado a un documento.'
            setConfirmState({
              open: true,
              title: 'Eliminar asiento',
              msg: `AVISO: ${detalle}\n\n¿Eliminar de todas formas?`,
              confirmText: 'Forzar eliminación',
              variant: 'danger',
              action: async () => {
                try {
                  await deleteAsiento(a.asiento, empresa.id, true)
                  cargar()
                } catch {
                  alert('Error al eliminar el asiento')
                }
              },
            })
          } else {
            alert('Error al eliminar el asiento')
          }
        }
      },
    })
  }

  const generarTodos = async () => {
    setConfirmState({
      open: true,
      title: 'Generar asientos',
      msg: '¿Generar asientos pendientes para todos los movimientos y facturas?',
      confirmText: 'Generar',
      variant: 'warning',
      action: async () => {
        setGenerando(true)
        try {
          const res = await generarPendientes(empresa.id)
          alert(
            `Asientos creados: ${res.total} (banco: ${res.banco}, facturas rec: ${res.facturas_rec}, facturas emi: ${res.facturas_emi})`,
          )
          cargar()
        } catch {
          alert('Error al generar asientos')
        } finally {
          setGenerando(false)
        }
      },
    })
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
          <label className="label">Cuenta</label>
          <AutocompleteCuenta empresaId={empresa.id} value={cuentaFiltro} onChange={setCuentaFiltro} className="w-72" />
        </div>
        <div>
          <label className="label">Ordenar por</label>
          <select className="input" value={orden} onChange={(e) => setOrden(e.target.value)}>
            <option value="fecha">Fecha</option>
            <option value="asiento">N.º asiento</option>
          </select>
        </div>
        <span className="text-sm text-gray-500 flex-1 self-end pb-2">{total} asientos</span>
        <button className="btn btn-secondary self-end" onClick={generarTodos} disabled={generando}>
          {generando ? 'Generando...' : 'Generar pendientes'}
        </button>
        <button
          className="btn btn-secondary self-end"
          onClick={() =>
            exportarCSV('diario', { empresa_id: empresa.id, fecha_desde: fechaDesde, fecha_hasta: fechaHasta })
          }
        >
          Exportar CSV
        </button>
        <button className="btn btn-primary self-end" onClick={() => setModalNuevo(true)}>
          + Nuevo asiento
        </button>
      </div>

      <div className="card">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">N.º</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Fecha
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Tipo</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Referencia
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Debe
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Haber
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Cuadre
              </th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {asientos.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                  Sin asientos en el periodo seleccionado
                </td>
              </tr>
            )}
            {asientos.map((a) => (
              <FilaAsiento key={a.asiento} asiento={a} empresa={empresa} onDelete={eliminar} onEdit={setModalEditar} />
            ))}
          </tbody>
        </table>
      </div>

      <Paginacion
        total={total}
        skip={(pagina - 1) * limit}
        limit={limit}
        onCambiar={(s) => setPagina(Math.floor(s / limit) + 1)}
        onLimitChange={(n) => {
          setLimit(n)
          setPagina(1)
        }}
      />

      {modalNuevo && <AsientoModal empresa={empresa} onClose={() => setModalNuevo(false)} onGuardado={cargar} />}
      {modalEditar && (
        <AsientoModal
          empresa={empresa}
          asientoEditar={modalEditar}
          onClose={() => setModalEditar(null)}
          onGuardado={cargar}
        />
      )}

      <ConfirmModal
        open={confirmState.open}
        title={confirmState.title}
        message={confirmState.msg}
        confirmText={confirmState.confirmText}
        variant={confirmState.variant}
        onConfirm={async () => {
          await confirmState.action()
          setConfirmState({ open: false, msg: '', action: null, variant: 'danger', title: '' })
        }}
        onCancel={() => setConfirmState({ open: false, msg: '', action: null, variant: 'danger', title: '' })}
      />
    </div>
  )
}
