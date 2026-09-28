import { useState, useEffect, useRef } from 'react'
import Modal from '../../components/Modal'
import Paginacion from '../../components/Paginacion'
import AutocompleteCuenta from '../../components/AutocompleteCuenta'
import { getMayor, exportarCSV } from '../../services/contabilidad'
import { EUR, fmtFecha, anioActual } from './utils'

const hoy = () => new Date().toISOString().slice(0, 10)

const COLS_MAYOR = [
  { id: 'fecha', label: 'Fecha' },
  { id: 'asiento', label: 'N.º Asiento' },
  { id: 'tipo', label: 'Tipo asiento' },
  { id: 'tipo_doc', label: 'Tipo documento', desc: 'X=extra · F=factura · B=banco' },
  { id: 'numero_doc', label: 'N.º documento', desc: 'N.º de factura, movimiento bancario o extra' },
  { id: 'referencia', label: 'Referencia' },
  { id: 'desc_cuenta', label: 'Descripción cuenta', desc: 'Nombre completo de la cuenta contable' },
  { id: 'concepto', label: 'Concepto tercero', desc: 'Nombre del cliente / proveedor / trabajador (extras)' },
  { id: 'notas', label: 'Notas', desc: 'Texto libre de notas del extra' },
  { id: 'cuenta_contra', label: 'Cuenta contrapartida', desc: 'Código de la cuenta del lado contrario del asiento' },
  { id: 'desc_contra', label: 'Descripción contrapartida', desc: 'Nombre de la cuenta contrapartida' },
  { id: 'debe', label: 'Debe' },
  { id: 'haber', label: 'Haber' },
  { id: 'saldo', label: 'Saldo acumulado' },
]

const COLS_MAYOR_DEFAULT = new Set(['fecha', 'asiento', 'tipo', 'referencia', 'debe', 'haber', 'saldo'])

const PLANTILLAS_KEY = 'gestion_mgd_mayor_plantillas'

function leerPlantillas() {
  try {
    return JSON.parse(localStorage.getItem(PLANTILLAS_KEY) || '[]')
  } catch {
    return []
  }
}

function ModalExportMayor({ empresa, cuenta, fechaDesde, fechaHasta, onClose }) {
  const colById = Object.fromEntries(COLS_MAYOR.map((c) => [c.id, c]))
  const labelsDefault = Object.fromEntries(COLS_MAYOR.map((c) => [c.id, c.label]))

  const [orden, setOrden] = useState(() => COLS_MAYOR.map((c) => c.id))
  const [sel, setSel] = useState(() => new Set(COLS_MAYOR_DEFAULT))
  const [labels, setLabels] = useState(() => ({ ...labelsDefault }))
  const [editando, setEditando] = useState(null)
  const [editVal, setEditVal] = useState('')
  const [plantillas, setPlantillas] = useState(leerPlantillas)
  const [inputVisible, setInputVisible] = useState(false)
  const [nombreInput, setNombreInput] = useState('')
  const [plantillaActiva, setPlantillaActiva] = useState(null)

  const dragIdx = useRef(null)
  const inputRef = useRef(null)
  const editRef = useRef(null)

  const toggle = (id) => {
    const s = new Set(sel)
    if (s.has(id)) s.delete(id)
    else s.add(id)
    setSel(s)
    setPlantillaActiva(null)
  }

  const esTodas = sel.size === COLS_MAYOR.length
  const toggleTodo = () => {
    setSel(esTodas ? new Set() : new Set(COLS_MAYOR.map((c) => c.id)))
    setPlantillaActiva(null)
  }
  const resetDefault = () => {
    setSel(new Set(COLS_MAYOR_DEFAULT))
    setOrden(COLS_MAYOR.map((c) => c.id))
    setLabels({ ...labelsDefault })
    setPlantillaActiva(null)
  }

  const onDragStart = (i) => {
    dragIdx.current = i
  }
  const onDragOver = (e, i) => {
    e.preventDefault()
    if (dragIdx.current === null || dragIdx.current === i) return
    const next = [...orden]
    const [moved] = next.splice(dragIdx.current, 1)
    next.splice(i, 0, moved)
    dragIdx.current = i
    setOrden(next)
    setPlantillaActiva(null)
  }
  const onDragEnd = () => {
    dragIdx.current = null
  }

  const iniciarEdicion = (id, e) => {
    e.stopPropagation()
    setEditando(id)
    setEditVal(labels[id])
    setTimeout(() => {
      editRef.current?.select()
    }, 30)
  }
  const confirmarEdicion = () => {
    if (editando) {
      setLabels((prev) => ({ ...prev, [editando]: editVal.trim() || labelsDefault[editando] }))
      setPlantillaActiva(null)
    }
    setEditando(null)
  }
  const cancelarEdicion = () => {
    setEditando(null)
  }

  const abrirInput = () => {
    setNombreInput(plantillaActiva || '')
    setInputVisible(true)
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  const guardarPlantilla = () => {
    const nombre = nombreInput.trim()
    if (!nombre) return
    const cols = orden.filter((id) => sel.has(id))
    if (!cols.length) {
      alert('Selecciona al menos una columna')
      return
    }
    const nueva = { nombre, cols, orden: [...orden], labels: { ...labels } }
    const lista = [...plantillas.filter((p) => p.nombre !== nombre), nueva]
    localStorage.setItem(PLANTILLAS_KEY, JSON.stringify(lista))
    setPlantillas(lista)
    setPlantillaActiva(nombre)
    setInputVisible(false)
  }

  const cargarPlantilla = (p) => {
    const colsValidas = p.cols.filter((id) => colById[id])
    const ordenValido = (p.orden || []).filter((id) => colById[id])
    const ordenFinal = ordenValido.length
      ? [...ordenValido, ...COLS_MAYOR.map((c) => c.id).filter((id) => !ordenValido.includes(id))]
      : [...colsValidas, ...COLS_MAYOR.map((c) => c.id).filter((id) => !colsValidas.includes(id))]
    setSel(new Set(colsValidas))
    setOrden(ordenFinal)
    setLabels(p.labels ? { ...labelsDefault, ...p.labels } : { ...labelsDefault })
    setPlantillaActiva(p.nombre)
  }

  const eliminarPlantilla = (nombre, e) => {
    e.stopPropagation()
    const lista = plantillas.filter((p) => p.nombre !== nombre)
    localStorage.setItem(PLANTILLAS_KEY, JSON.stringify(lista))
    setPlantillas(lista)
    if (plantillaActiva === nombre) setPlantillaActiva(null)
  }

  const doExport = (fmt) => {
    const cols = orden.filter((id) => sel.has(id))
    if (!cols.length) {
      alert('Selecciona al menos una columna')
      return
    }
    const labelsCustom = cols.map((id) => labels[id] || labelsDefault[id])
    const tieneCustom = cols.some((id) => labels[id] !== labelsDefault[id])
    exportarCSV('mayor', {
      empresa_id: empresa.id,
      cuenta,
      fecha_desde: fechaDesde,
      fecha_hasta: fechaHasta,
      columnas: cols.join(','),
      formato: fmt,
      ...(tieneCustom ? { cabeceras_custom: labelsCustom.join('|') } : {}),
      ...(plantillaActiva ? { nombre: plantillaActiva } : {}),
    })
    onClose()
  }

  const selCount = orden.filter((id) => sel.has(id)).length

  return (
    <Modal titulo={`Exportar Libro Mayor — ${cuenta}`} onClose={onClose}>
      <p className="text-sm text-gray-500 mb-3">
        Marca, arrastra para reordenar y haz clic en el nombre para editarlo:
      </p>

      <div className="border rounded-lg overflow-hidden mb-3">
        <div className="bg-gray-50 border-b px-4 py-2 flex items-center gap-3">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex-1">Columnas</span>
          <button className="text-xs text-gray-500 hover:text-gray-700" onClick={resetDefault}>
            Por defecto
          </button>
          <button className="text-xs text-blue-600 hover:text-blue-800" onClick={toggleTodo}>
            {esTodas ? 'Ninguna' : 'Todas'}
          </button>
        </div>
        <div className="divide-y divide-gray-100 max-h-64 overflow-y-auto">
          {orden.map((id, i) => {
            const c = colById[id]
            const esEditando = editando === id
            const labelMod = labels[id] !== labelsDefault[id]
            return (
              <div
                key={id}
                draggable={!esEditando}
                onDragStart={() => onDragStart(i)}
                onDragOver={(e) => onDragOver(e, i)}
                onDragEnd={onDragEnd}
                className="flex items-center gap-3 px-4 py-2 hover:bg-blue-50 select-none"
              >
                <span className="text-gray-300 shrink-0 text-base leading-none cursor-grab active:cursor-grabbing">
                  ⠿
                </span>
                <input
                  type="checkbox"
                  checked={sel.has(id)}
                  onChange={() => toggle(id)}
                  className="rounded accent-blue-600 shrink-0"
                />
                <div className="flex-1 min-w-0">
                  {esEditando ? (
                    <input
                      ref={editRef}
                      type="text"
                      value={editVal}
                      onChange={(e) => setEditVal(e.target.value)}
                      onBlur={confirmarEdicion}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') confirmarEdicion()
                        if (e.key === 'Escape') cancelarEdicion()
                      }}
                      className="w-full text-sm border-b border-blue-400 bg-transparent outline-none py-0.5"
                    />
                  ) : (
                    <span
                      onClick={(e) => iniciarEdicion(id, e)}
                      title="Clic para editar el nombre del encabezado"
                      className={`text-sm cursor-text block truncate ${labelMod ? 'text-blue-700 font-medium' : 'text-gray-800'}`}
                    >
                      {labels[id]}
                      {labelMod && <span className="ml-1 text-xs text-blue-400">(↩ {labelsDefault[id]})</span>}
                    </span>
                  )}
                  {c.desc && !esEditando && <span className="text-xs text-gray-400">{c.desc}</span>}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="border rounded-lg overflow-hidden mb-3">
        <div className="bg-gray-50 border-b px-4 py-2 flex items-center gap-3">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex-1">
            Plantillas
            {plantillaActiva && <span className="ml-2 normal-case font-normal text-blue-600">— {plantillaActiva}</span>}
          </span>
          {!inputVisible && (
            <button
              className="text-xs text-blue-600 hover:text-blue-800"
              onClick={abrirInput}
              disabled={!selCount}
              title="Guardar la selección actual como plantilla"
            >
              {plantillaActiva ? '↑ Actualizar' : '+ Guardar actual'}
            </button>
          )}
        </div>

        {inputVisible && (
          <div className="px-4 py-2.5 flex items-center gap-2 border-b bg-blue-50">
            <input
              ref={inputRef}
              type="text"
              value={nombreInput}
              onChange={(e) => setNombreInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') guardarPlantilla()
                if (e.key === 'Escape') setInputVisible(false)
              }}
              placeholder="Nombre de la plantilla…"
              className="flex-1 text-sm border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <button
              className="text-sm text-white bg-blue-600 hover:bg-blue-700 rounded px-3 py-1"
              onClick={guardarPlantilla}
            >
              Guardar
            </button>
            <button className="text-sm text-gray-500 hover:text-gray-700" onClick={() => setInputVisible(false)}>
              ✕
            </button>
          </div>
        )}

        <div className="px-4 py-2.5 flex flex-wrap gap-2 min-h-[2.5rem] items-center">
          {plantillas.length === 0 && <span className="text-xs text-gray-400 italic">Sin plantillas guardadas</span>}
          {plantillas.map((p) => (
            <button
              key={p.nombre}
              onClick={() => cargarPlantilla(p)}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs hover:bg-blue-100 ${
                plantillaActiva === p.nombre
                  ? 'border-blue-500 bg-blue-100 text-blue-800 font-semibold'
                  : 'border-blue-200 bg-blue-50 text-blue-700'
              }`}
            >
              {p.nombre}
              <span
                role="button"
                tabIndex={0}
                onClick={(e) => eliminarPlantilla(p.nombre, e)}
                onKeyDown={(e) => e.key === 'Enter' && eliminarPlantilla(p.nombre, e)}
                className="text-blue-400 hover:text-red-500 font-bold leading-none"
              >
                ×
              </span>
            </button>
          ))}
        </div>
      </div>

      <p className="text-xs text-gray-400 mb-4">
        {selCount} de {COLS_MAYOR.length} columnas · fecha <code>dd/mm/aaaa</code>
        {plantillaActiva && (
          <span className="ml-2 text-blue-500">
            · fichero: <em>{plantillaActiva}</em>
          </span>
        )}
      </p>

      <div className="flex gap-3 justify-end">
        <button className="btn btn-secondary" onClick={onClose}>
          Cancelar
        </button>
        <button
          className="btn btn-secondary"
          onClick={() => doExport('csv')}
          disabled={!selCount}
          title="Separador ; · decimal ,"
        >
          Descargar CSV
        </button>
        <button className="btn btn-primary" onClick={() => doExport('xlsx')} disabled={!selCount}>
          Descargar Excel
        </button>
      </div>
    </Modal>
  )
}

export default function TabMayor({ empresa, cuentaInicial = '' }) {
  const [cuenta, setCuenta] = useState(cuentaInicial)
  const [cuentaVal, setCuentaVal] = useState(cuentaInicial)
  const [fechaDesde, setFechaDesde] = useState(`${anioActual}-01-01`)
  const [fechaHasta, setFechaHasta] = useState(hoy())
  const [lineas, setLineas] = useState([])
  const [total, setTotal] = useState(0)
  const [saldoAnterior, setSaldoAnterior] = useState(0)
  const [skip, setSkip] = useState(0)
  const [limitMayor, setLimitMayor] = useState(100)
  const [buscado, setBuscado] = useState(false)
  const [modalExport, setModalExport] = useState(false)

  const buscar = async (newSkip = 0, newLimit = limitMayor) => {
    if (!cuentaVal) return
    setCuenta(cuentaVal)
    setSkip(newSkip)
    const params = { empresa_id: empresa.id, cuenta: cuentaVal, skip: newSkip, limit: newLimit }
    if (fechaDesde) params.fecha_desde = fechaDesde
    if (fechaHasta) params.fecha_hasta = fechaHasta
    const data = await getMayor(params)
    setLineas(data.items)
    setTotal(data.total)
    setSaldoAnterior(data.saldo_anterior ?? 0)
    setBuscado(true)
  }

  useEffect(() => {
    if (cuentaInicial) buscar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const lineasConSaldo = lineas.reduce((acc, l) => {
    const prev = acc.length > 0 ? acc[acc.length - 1].saldoAcum : Number(saldoAnterior || 0)
    acc.push({ ...l, saldoAcum: prev + Number(l.importe || 0) })
    return acc
  }, [])
  const saldoFinal =
    lineasConSaldo.length > 0 ? lineasConSaldo[lineasConSaldo.length - 1].saldoAcum : Number(saldoAnterior || 0)

  const totalDebe = lineas.reduce((s, l) => s + (Number(l.importe) > 0 ? Number(l.importe) : 0), 0)
  const totalHaber = lineas.reduce((s, l) => s + (Number(l.importe) < 0 ? Math.abs(Number(l.importe)) : 0), 0)

  return (
    <div>
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div>
          <label className="label">Cuenta *</label>
          <AutocompleteCuenta
            empresaId={empresa.id}
            value={cuentaVal}
            onChange={setCuentaVal}
            className="w-80"
            onKeyDown={(e) => e.key === 'Enter' && buscar()}
          />
        </div>
        <div>
          <label className="label">Desde</label>
          <input type="date" className="input" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} />
        </div>
        <div>
          <label className="label">Hasta</label>
          <input type="date" className="input" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} />
        </div>
        <button className="btn btn-primary self-end" onClick={() => buscar(0)}>
          Consultar
        </button>
        {buscado && cuenta && (
          <button className="btn btn-secondary self-end" onClick={() => setModalExport(true)}>
            Exportar CSV...
          </button>
        )}
      </div>

      {buscado && (
        <>
          {lineas.length === 0 ? (
            <div className="card p-8 text-center text-gray-400">
              Sin movimientos para la cuenta <span className="font-mono font-semibold">{cuenta}</span>
            </div>
          ) : (
            <div className="card">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Fecha
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Asiento
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Tipo
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Ref.
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Debe
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Haber
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Saldo
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {skip > 0 && (
                    <tr className="bg-gray-50 text-xs text-gray-400 italic">
                      <td colSpan={6} className="px-4 py-1.5">
                        Saldo anterior ({skip} movimientos)
                      </td>
                      <td
                        className={`px-4 py-1.5 text-right font-mono font-semibold ${saldoAnterior < 0 ? 'text-red-400' : 'text-gray-500'}`}
                      >
                        {EUR(saldoAnterior)}
                      </td>
                    </tr>
                  )}
                  {lineasConSaldo.map((l) => (
                    <tr key={l.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5 text-gray-600">{fmtFecha(l.fecha)}</td>
                      <td className="px-4 py-2.5 text-gray-500 font-mono">{l.asiento}</td>
                      <td className="px-4 py-2.5 text-gray-500">{l.tpasiento}</td>
                      <td className="px-4 py-2.5 text-gray-600">{l.clave}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs text-green-700">
                        {(l.importe ?? 0) > 0 ? EUR(l.importe) : ''}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs text-red-600">
                        {(l.importe ?? 0) < 0 ? EUR(Math.abs(l.importe)) : ''}
                      </td>
                      <td
                        className={`px-4 py-2.5 text-right font-mono text-xs font-semibold ${l.saldoAcum < 0 ? 'text-red-600' : 'text-gray-800'}`}
                      >
                        {EUR(l.saldoAcum)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-gray-50 border-t-2 border-gray-200 font-semibold">
                  <tr>
                    <td colSpan={4} className="px-4 py-2.5 text-gray-600 text-sm">
                      {lineas.length} movimiento{lineas.length !== 1 ? 's' : ''}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-xs text-green-700">{EUR(totalDebe)}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-xs text-red-600">{EUR(totalHaber)}</td>
                    <td
                      className={`px-4 py-2.5 text-right font-mono text-xs font-bold ${saldoFinal < 0 ? 'text-red-600' : 'text-gray-900'}`}
                    >
                      {EUR(saldoFinal)}
                    </td>
                  </tr>
                </tfoot>
              </table>
              <Paginacion
                total={total}
                skip={skip}
                limit={limitMayor}
                onCambiar={(s) => buscar(s)}
                onLimitChange={(n) => {
                  setLimitMayor(n)
                  buscar(0, n)
                }}
              />
            </div>
          )}
        </>
      )}

      {modalExport && (
        <ModalExportMayor
          empresa={empresa}
          cuenta={cuenta}
          fechaDesde={fechaDesde}
          fechaHasta={fechaHasta}
          onClose={() => setModalExport(false)}
        />
      )}
    </div>
  )
}
