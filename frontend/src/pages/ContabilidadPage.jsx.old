import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import Modal from '../components/Modal'
import Paginacion from '../components/Paginacion'
import AutocompleteCuenta from '../components/AutocompleteCuenta'
import {
  getCuentas, createCuenta, updateCuenta, deleteCuenta,
  getAsientos, createAsiento, updateAsiento, deleteAsiento,
  getMayor, generarPendientes, getDiagnostico, getSumasSaldos, getPyG, getConciliacion, regenerarAsientoBanco,
  getBalance, realizarCierre, exportarCSV,
} from '../services/contabilidad'

const EUR = (v) =>
  (v ?? 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const fmtFecha = (iso) => {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

const anioActual = new Date().getFullYear()
const hoy = () => new Date().toISOString().slice(0, 10)

// ── Pestaña Plan de Cuentas ───────────────────────────────────────────────────

function TabCuentas({ empresa, onIrAMayor }) {
  const [q, setQ] = useState('')
  const [qVal, setQVal] = useState('')
  const [soloConSaldo, setSoloConSaldo] = useState(false)
  const [cuentas, setCuentas] = useState([])
  const [total, setTotal] = useState(0)
  const [pagina, setPagina] = useState(1)
  const [limit, setLimit] = useState(100)
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState({})
  const [error, setError] = useState('')

  const cargar = useCallback(async () => {
    const params = { empresa_id: empresa.id, skip: (pagina - 1) * limit, limit }
    if (q) params.q = q
    if (soloConSaldo) params.solo_con_saldo = true
    const data = await getCuentas(params)
    setCuentas(data.items)
    setTotal(data.total)
  }, [empresa.id, q, soloConSaldo, pagina, limit])

  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { setPagina(1) }, [q, soloConSaldo])

  const buscar = () => setQ(qVal)

  const abrirNuevo = () => {
    setForm({ cuenta: '', texto: '' })
    setModal('nuevo')
    setError('')
  }

  const abrirEditar = (c) => {
    setForm({ texto: c.texto || '', marca: c.marca || '' })
    setModal(c)
    setError('')
  }

  const guardar = async () => {
    if (modal === 'nuevo' && !form.cuenta?.trim()) { setError('El código de cuenta es obligatorio'); return }
    try {
      if (modal === 'nuevo') {
        await createCuenta({ ...form, empresa_id: empresa.id })
      } else {
        await updateCuenta(modal.id, form)
      }
      setModal(null)
      cargar()
    } catch {
      setError('Error al guardar')
    }
  }

  const eliminar = async (c) => {
    if (!confirm(`¿Eliminar la cuenta ${c.cuenta}?`)) return
    try {
      await deleteCuenta(c.id)
      cargar()
    } catch (e) {
      alert(e.message || 'No se puede eliminar (tiene movimientos asociados)')
    }
  }

  return (
    <div>
      <div className="flex gap-3 mb-4 flex-wrap">
        <input className="input w-64" placeholder="Buscar por código o descripción..."
          value={qVal} onChange={(e) => setQVal(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && buscar()} />
        <button className="btn btn-secondary" onClick={buscar}>Buscar</button>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
          <input type="checkbox" className="w-4 h-4 accent-mgd-600"
            checked={soloConSaldo} onChange={(e) => setSoloConSaldo(e.target.checked)} />
          Solo con saldo
        </label>
        <span className="text-sm text-gray-500 flex-1 self-center">{total} cuentas</span>
        <button className="btn btn-primary" onClick={abrirNuevo}>+ Nueva cuenta</button>
      </div>

      <div className="card">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Cuenta</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Descripción</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Debe</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Haber</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Saldo</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {cuentas.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Sin cuentas</td></tr>
            )}
            {cuentas.map((c) => {
              const saldo = (c.debe ?? 0) - (c.haber ?? 0)
              return (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-mono text-gray-800 font-medium">{c.cuenta}</td>
                  <td className="px-4 py-2.5 text-gray-700">{c.texto}</td>
                  <td className="px-4 py-2.5 text-right text-gray-600 font-mono text-xs">{EUR(c.debe)}</td>
                  <td className="px-4 py-2.5 text-right text-gray-600 font-mono text-xs">{EUR(c.haber)}</td>
                  <td className={`px-4 py-2.5 text-right font-mono text-xs font-semibold ${saldo < 0 ? 'text-red-600' : saldo > 0 ? 'text-gray-800' : 'text-gray-400'}`}>
                    {EUR(saldo)}
                  </td>
                  <td className="px-4 py-2.5 text-right whitespace-nowrap">
                    {onIrAMayor && (
                      <button className="btn btn-secondary text-xs mr-2" onClick={() => onIrAMayor(c.cuenta)}
                        title="Ver en Libro mayor">→ Mayor</button>
                    )}
                    <button className="btn btn-secondary text-xs mr-2" onClick={() => abrirEditar(c)}>Editar</button>
                    <button className="btn btn-danger text-xs" onClick={() => eliminar(c)}>Eliminar</button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <Paginacion total={total} skip={(pagina - 1) * limit} limit={limit}
        onCambiar={(s) => setPagina(Math.floor(s / limit) + 1)}
        onLimitChange={(n) => { setLimit(n); setPagina(1) }} />

      {modal && (
        <Modal titulo={modal === 'nuevo' ? 'Nueva cuenta' : `Editar cuenta ${modal.cuenta}`} onClose={() => setModal(null)}>
          {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
          <div className="grid grid-cols-2 gap-4">
            {modal === 'nuevo' && (
              <div>
                <label className="label">Código de cuenta *</label>
                <input className="input font-mono" value={form.cuenta}
                  onChange={(e) => setForm({ ...form, cuenta: e.target.value })} />
              </div>
            )}
            <div className={modal === 'nuevo' ? '' : 'col-span-2'}>
              <label className="label">Descripción</label>
              <input className="input" value={form.texto}
                onChange={(e) => setForm({ ...form, texto: e.target.value })} />
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancelar</button>
            <button className="btn btn-primary" onClick={guardar}>Guardar</button>
          </div>
        </Modal>
      )}
    </div>
  )
}

// ── Pestaña Diario ────────────────────────────────────────────────────────────

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

function FilaAsiento({ asiento, empresa, onDelete, onEdit }) {
  const [abierto, setAbierto] = useState(false)

  const cuadrado = asiento.cuadrado
  const diff = Math.abs(asiento.total_debe - asiento.total_haber)

  return (
    <>
      <tr
        className="hover:bg-gray-50 cursor-pointer select-none"
        onClick={() => setAbierto(!abierto)}
      >
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
          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${cuadrado ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {cuadrado ? '✓' : `${EUR(diff)}`}
          </span>
        </td>
        <td className="px-4 py-2.5 text-right">
          <span className="text-gray-400 text-xs mr-2">{asiento.lineas.length} líneas</span>
          <button
            className="btn btn-secondary text-xs mr-1"
            onClick={(e) => { e.stopPropagation(); onEdit(asiento) }}
          >
            Editar
          </button>
          <button
            className="btn btn-danger text-xs"
            onClick={(e) => { e.stopPropagation(); onDelete(asiento) }}
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

  const [form, setForm] = useState(() => esEdicion
    ? { fecha: asientoEditar.fecha, tpasiento: asientoEditar.tpasiento || '', clave: asientoEditar.clave || '' }
    : { fecha: hoy(), tpasiento: '', clave: '' }
  )
  const [lineas, setLineas] = useState(() => esEdicion
    ? asientoEditar.lineas.map((l) => ({
        cuenta: l.cuenta || '',
        debe: (l.importe ?? 0) > 0 ? String(l.importe) : '',
        haber: (l.importe ?? 0) < 0 ? String(Math.abs(l.importe)) : '',
      }))
    : [{ cuenta: '', debe: '', haber: '' }, { cuenta: '', debe: '', haber: '' }]
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
    if (!form.fecha) { setError('La fecha es obligatoria'); return }
    if (!cuadrado) { setError(`El asiento no está cuadrado (D: ${EUR(totalDebe)} / H: ${EUR(totalHaber)})`); return }
    const lineasValidas = lineas.filter((l) => l.cuenta && (l.debe || l.haber))
    if (lineasValidas.length < 2) { setError('Mínimo 2 líneas con cuenta e importe'); return }
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
    <Modal titulo={esEdicion ? `Editar asiento #${asientoEditar.asiento}` : 'Nuevo asiento contable'} onClose={onClose} ancho="max-w-3xl">
      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div>
          <label className="label">Fecha *</label>
          <input type="date" className="input" value={form.fecha}
            onChange={(e) => setForm({ ...form, fecha: e.target.value })} />
        </div>
        <div>
          <label className="label">Tipo</label>
          <select className="input" value={form.tpasiento}
            onChange={(e) => setForm({ ...form, tpasiento: e.target.value })}>
            {TIPOS_ASIENTO.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Referencia / clave</label>
          <input className="input" value={form.clave}
            onChange={(e) => setForm({ ...form, clave: e.target.value })} />
        </div>
      </div>

      <div className="border rounded-lg overflow-hidden mb-3">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-3 py-2 text-left text-xs text-gray-500 uppercase">Cuenta</th>
              <th className="px-3 py-2 text-right text-xs text-gray-500 uppercase">Debe</th>
              <th className="px-3 py-2 text-right text-xs text-gray-500 uppercase">Haber</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {lineas.map((l, i) => (
              <tr key={i}>
                <td className="px-2 py-1">
                  <AutocompleteCuenta empresaId={empresa.id} value={l.cuenta}
                    onChange={(v) => setLinea(i, 'cuenta', v)} className="text-sm" />
                </td>
                <td className="px-2 py-1">
                  <input type="number" step="0.01" min="0" className="input text-right text-sm"
                    placeholder="0,00"
                    value={l.debe} onChange={(e) => setLinea(i, 'debe', e.target.value)} />
                </td>
                <td className="px-2 py-1">
                  <input type="number" step="0.01" min="0" className="input text-right text-sm"
                    placeholder="0,00"
                    value={l.haber} onChange={(e) => setLinea(i, 'haber', e.target.value)} />
                </td>
                <td className="px-2 py-1 text-center">
                  {lineas.length > 2 && (
                    <button className="text-red-400 hover:text-red-600" onClick={() => removeLinea(i)}>✕</button>
                  )}
                </td>
              </tr>
            ))}
            <tr className="bg-gray-50 font-semibold text-sm">
              <td className="px-3 py-2 text-gray-500">TOTALES</td>
              <td className="px-3 py-2 text-right font-mono text-green-700">{EUR(totalDebe)}</td>
              <td className="px-3 py-2 text-right font-mono text-red-600">{EUR(totalHaber)}</td>
              <td></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-4">
        <button className="btn btn-secondary text-xs" onClick={addLinea}>+ Añadir línea</button>
        {cuadrado
          ? <span className="text-green-600 text-xs font-medium">✓ Asiento cuadrado</span>
          : <span className="text-amber-600 text-xs">Diferencia: {EUR(Math.abs(totalDebe - totalHaber))}</span>}
      </div>

      <div className="flex justify-end gap-3 mt-6">
        <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
        <button className="btn btn-primary" onClick={guardar} disabled={!cuadrado}>Guardar asiento</button>
      </div>
    </Modal>
  )
}

function TabDiario({ empresa }) {
  const [fechaDesde, setFechaDesde] = useState(`${anioActual}-01-01`)
  const [fechaHasta, setFechaHasta] = useState(hoy())
  const [cuentaFiltro, setCuentaFiltro] = useState('')
  const [orden, setOrden] = useState('fecha')
  const [asientos, setAsientos] = useState([])
  const [total, setTotal] = useState(0)
  const [pagina, setPagina] = useState(1)
  const [limit, setLimit] = useState(30)
  const [modalNuevo, setModalNuevo]     = useState(false)
  const [modalEditar, setModalEditar]   = useState(null)
  const [generando, setGenerando]       = useState(false)

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

  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { setPagina(1) }, [fechaDesde, fechaHasta, cuentaFiltro, orden])

  const eliminar = async (a) => {
    if (!confirm(`¿Eliminar el asiento #${a.asiento}? Esta acción es irreversible.`)) return
    try {
      await deleteAsiento(a.asiento, empresa.id)
      cargar()
    } catch (err) {
      // 409: el asiento pertenece a un documento — pedir confirmación extra
      if (err.response?.status === 409) {
        const detalle = err.response?.data?.detail || 'El asiento está vinculado a un documento.'
        if (!confirm(`AVISO: ${detalle}\n\n¿Eliminar de todas formas?`)) return
        try {
          await deleteAsiento(a.asiento, empresa.id, true)
          cargar()
        } catch {
          alert('Error al eliminar el asiento')
        }
      } else {
        alert('Error al eliminar el asiento')
      }
    }
  }

  const generarTodos = async () => {
    if (!confirm('¿Generar asientos pendientes para todos los movimientos y facturas?')) return
    setGenerando(true)
    try {
      const res = await generarPendientes(empresa.id)
      alert(`Asientos creados: ${res.total} (banco: ${res.banco}, facturas rec: ${res.facturas_rec}, facturas emi: ${res.facturas_emi})`)
      cargar()
    } catch {
      alert('Error al generar asientos')
    } finally {
      setGenerando(false)
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-end gap-3 mb-4">
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
        <div>
          <label className="label">Cuenta</label>
          <AutocompleteCuenta empresaId={empresa.id} value={cuentaFiltro}
            onChange={setCuentaFiltro} className="w-72" />
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
        <button className="btn btn-secondary self-end"
          onClick={() => exportarCSV('diario', { empresa_id: empresa.id, fecha_desde: fechaDesde, fecha_hasta: fechaHasta })}>
          Exportar CSV
        </button>
        <button className="btn btn-primary self-end" onClick={() => setModalNuevo(true)}>+ Nuevo asiento</button>
      </div>

      <div className="card">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">N.º</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Fecha</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Tipo</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Referencia</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Debe</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Haber</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Cuadre</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {asientos.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Sin asientos en el periodo seleccionado</td></tr>
            )}
            {asientos.map((a) => (
              <FilaAsiento key={a.asiento} asiento={a} empresa={empresa} onDelete={eliminar} onEdit={setModalEditar} />
            ))}
          </tbody>
        </table>
      </div>

      <Paginacion total={total} skip={(pagina - 1) * limit} limit={limit}
        onCambiar={(s) => setPagina(Math.floor(s / limit) + 1)}
        onLimitChange={(n) => { setLimit(n); setPagina(1) }} />

      {modalNuevo && (
        <AsientoModal empresa={empresa} onClose={() => setModalNuevo(false)} onGuardado={cargar} />
      )}
      {modalEditar && (
        <AsientoModal empresa={empresa} asientoEditar={modalEditar} onClose={() => setModalEditar(null)} onGuardado={cargar} />
      )}
    </div>
  )
}

// ── Modal exportación Libro Mayor ─────────────────────────────────────────────

const COLS_MAYOR = [
  { id: 'fecha',       label: 'Fecha' },
  { id: 'asiento',    label: 'N.º Asiento' },
  { id: 'tipo',       label: 'Tipo asiento' },
  { id: 'tipo_doc',   label: 'Tipo documento',     desc: 'X=extra · F=factura · B=banco' },
  { id: 'numero_doc', label: 'N.º documento',      desc: 'N.º de factura, movimiento bancario o extra' },
  { id: 'referencia', label: 'Referencia' },
  { id: 'desc_cuenta', label: 'Descripción cuenta', desc: 'Nombre completo de la cuenta contable' },
  { id: 'concepto',      label: 'Concepto tercero',        desc: 'Nombre del cliente / proveedor / trabajador (extras)' },
  { id: 'notas',         label: 'Notas',                   desc: 'Texto libre de notas del extra' },
  { id: 'cuenta_contra', label: 'Cuenta contrapartida',    desc: 'Código de la cuenta del lado contrario del asiento' },
  { id: 'desc_contra',   label: 'Descripción contrapartida', desc: 'Nombre de la cuenta contrapartida' },
  { id: 'debe',          label: 'Debe' },
  { id: 'haber',      label: 'Haber' },
  { id: 'saldo',      label: 'Saldo acumulado' },
]

const COLS_MAYOR_DEFAULT = new Set(['fecha', 'asiento', 'tipo', 'referencia', 'debe', 'haber', 'saldo'])

const PLANTILLAS_KEY = 'gestion_mgd_mayor_plantillas'

function leerPlantillas() {
  try { return JSON.parse(localStorage.getItem(PLANTILLAS_KEY) || '[]') } catch { return [] }
}

function ModalExportMayor({ empresa, cuenta, fechaDesde, fechaHasta, onClose }) {
  const colById = Object.fromEntries(COLS_MAYOR.map((c) => [c.id, c]))
  const labelsDefault = Object.fromEntries(COLS_MAYOR.map((c) => [c.id, c.label]))

  const [orden,     setOrden]     = useState(() => COLS_MAYOR.map((c) => c.id))
  const [sel,       setSel]       = useState(() => new Set(COLS_MAYOR_DEFAULT))
  const [labels,    setLabels]    = useState(() => ({ ...labelsDefault }))   // encabezados editables
  const [editando,  setEditando]  = useState(null)   // id de columna en edición
  const [editVal,   setEditVal]   = useState('')
  const [plantillas,    setPlantillas]    = useState(leerPlantillas)
  const [inputVisible,  setInputVisible]  = useState(false)
  const [nombreInput,   setNombreInput]   = useState('')
  const [plantillaActiva, setPlantillaActiva] = useState(null)

  const dragIdx  = useRef(null)
  const inputRef = useRef(null)
  const editRef  = useRef(null)

  const toggle = (id) => {
    const s = new Set(sel)
    if (s.has(id)) s.delete(id); else s.add(id)
    setSel(s)
    setPlantillaActiva(null)
  }

  const esTodas = sel.size === COLS_MAYOR.length
  const toggleTodo = () => { setSel(esTodas ? new Set() : new Set(COLS_MAYOR.map((c) => c.id))); setPlantillaActiva(null) }
  const resetDefault = () => {
    setSel(new Set(COLS_MAYOR_DEFAULT))
    setOrden(COLS_MAYOR.map((c) => c.id))
    setLabels({ ...labelsDefault })
    setPlantillaActiva(null)
  }

  // ── drag-and-drop ──────────────────────────────────────────────────────────
  const onDragStart = (i) => { dragIdx.current = i }
  const onDragOver  = (e, i) => {
    e.preventDefault()
    if (dragIdx.current === null || dragIdx.current === i) return
    const next = [...orden]
    const [moved] = next.splice(dragIdx.current, 1)
    next.splice(i, 0, moved)
    dragIdx.current = i
    setOrden(next)
    setPlantillaActiva(null)
  }
  const onDragEnd = () => { dragIdx.current = null }

  // ── edición de encabezados ─────────────────────────────────────────────────
  const iniciarEdicion = (id, e) => {
    e.stopPropagation()
    setEditando(id)
    setEditVal(labels[id])
    setTimeout(() => { editRef.current?.select() }, 30)
  }
  const confirmarEdicion = () => {
    if (editando) {
      setLabels((prev) => ({ ...prev, [editando]: editVal.trim() || labelsDefault[editando] }))
      setPlantillaActiva(null)
    }
    setEditando(null)
  }
  const cancelarEdicion = () => { setEditando(null) }

  // ── plantillas ─────────────────────────────────────────────────────────────
  const abrirInput = () => {
    setNombreInput(plantillaActiva || '')
    setInputVisible(true)
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  const guardarPlantilla = () => {
    const nombre = nombreInput.trim()
    if (!nombre) return
    const cols = orden.filter((id) => sel.has(id))
    if (!cols.length) { alert('Selecciona al menos una columna'); return }
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
  // ────────────────────────────────────────────────────────────────────────────

  const doExport = (fmt) => {
    const cols = orden.filter((id) => sel.has(id))
    if (!cols.length) { alert('Selecciona al menos una columna'); return }
    const labelsCustom = cols.map((id) => labels[id] || labelsDefault[id])
    const tieneCustom  = cols.some((id) => labels[id] !== labelsDefault[id])
    exportarCSV('mayor', {
      empresa_id:      empresa.id,
      cuenta,
      fecha_desde:     fechaDesde,
      fecha_hasta:     fechaHasta,
      columnas:        cols.join(','),
      formato:         fmt,
      ...(tieneCustom  ? { cabeceras_custom: labelsCustom.join('|') } : {}),
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

      {/* ── Lista de columnas ─────────────────────────────────────────────── */}
      <div className="border rounded-lg overflow-hidden mb-3">
        <div className="bg-gray-50 border-b px-4 py-2 flex items-center gap-3">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex-1">Columnas</span>
          <button className="text-xs text-gray-500 hover:text-gray-700" onClick={resetDefault}>Por defecto</button>
          <button className="text-xs text-blue-600 hover:text-blue-800" onClick={toggleTodo}>
            {esTodas ? 'Ninguna' : 'Todas'}
          </button>
        </div>
        <div className="divide-y divide-gray-100 max-h-64 overflow-y-auto">
          {orden.map((id, i) => {
            const c = colById[id]
            const esEditando = editando === id
            const labelMod   = labels[id] !== labelsDefault[id]
            return (
              <div
                key={id}
                draggable={!esEditando}
                onDragStart={() => onDragStart(i)}
                onDragOver={(e) => onDragOver(e, i)}
                onDragEnd={onDragEnd}
                className="flex items-center gap-3 px-4 py-2 hover:bg-blue-50 select-none"
              >
                <span className="text-gray-300 shrink-0 text-base leading-none cursor-grab active:cursor-grabbing">⠿</span>
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
                      onKeyDown={(e) => { if (e.key === 'Enter') confirmarEdicion(); if (e.key === 'Escape') cancelarEdicion() }}
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

      {/* ── Plantillas ────────────────────────────────────────────────────── */}
      <div className="border rounded-lg overflow-hidden mb-3">
        <div className="bg-gray-50 border-b px-4 py-2 flex items-center gap-3">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex-1">
            Plantillas
            {plantillaActiva && (
              <span className="ml-2 normal-case font-normal text-blue-600">— {plantillaActiva}</span>
            )}
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
              onKeyDown={(e) => { if (e.key === 'Enter') guardarPlantilla(); if (e.key === 'Escape') setInputVisible(false) }}
              placeholder="Nombre de la plantilla…"
              className="flex-1 text-sm border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <button className="text-sm text-white bg-blue-600 hover:bg-blue-700 rounded px-3 py-1" onClick={guardarPlantilla}>
              Guardar
            </button>
            <button className="text-sm text-gray-500 hover:text-gray-700" onClick={() => setInputVisible(false)}>✕</button>
          </div>
        )}

        <div className="px-4 py-2.5 flex flex-wrap gap-2 min-h-[2.5rem] items-center">
          {plantillas.length === 0 && (
            <span className="text-xs text-gray-400 italic">Sin plantillas guardadas</span>
          )}
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
              >×</span>
            </button>
          ))}
        </div>
      </div>

      <p className="text-xs text-gray-400 mb-4">
        {selCount} de {COLS_MAYOR.length} columnas · fecha <code>dd/mm/aaaa</code>
        {plantillaActiva && <span className="ml-2 text-blue-500">· fichero: <em>{plantillaActiva}</em></span>}
      </p>

      <div className="flex gap-3 justify-end">
        <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
        <button
          className="btn btn-secondary"
          onClick={() => doExport('csv')}
          disabled={!selCount}
          title="Separador ; · decimal ,"
        >
          Descargar CSV
        </button>
        <button
          className="btn btn-primary"
          onClick={() => doExport('xlsx')}
          disabled={!selCount}
        >
          Descargar Excel
        </button>
      </div>
    </Modal>
  )
}

// ── Pestaña Libro Mayor ───────────────────────────────────────────────────────

function TabMayor({ empresa, cuentaInicial = '' }) {
  const [cuenta, setCuenta]               = useState(cuentaInicial)
  const [cuentaVal, setCuentaVal]         = useState(cuentaInicial)
  const [fechaDesde, setFechaDesde]       = useState(`${anioActual}-01-01`)
  const [fechaHasta, setFechaHasta]       = useState(hoy())
  const [lineas, setLineas]               = useState([])
  const [total, setTotal]                 = useState(0)
  const [saldoAnterior, setSaldoAnterior] = useState(0)
  const [skip, setSkip]                   = useState(0)
  const [limitMayor, setLimitMayor]       = useState(100)
  const [buscado, setBuscado]             = useState(false)
  const [modalExport, setModalExport]     = useState(false)

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

  // Auto-búsqueda cuando se llega desde un enlace externo con cuenta pre-cargada
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (cuentaInicial) buscar() }, [])

  // Cálculo de saldo acumulado continuando desde la última fila de la página anterior
  let saldoAcum = saldoAnterior
  const lineasConSaldo = lineas.map((l) => {
    saldoAcum = saldoAcum + (l.importe || 0)
    return { ...l, saldoAcum: saldoAcum }
  })

  const totalDebe = lineas.reduce((s, l) => s + ((l.importe || 0) > 0 ? (l.importe || 0) : 0), 0)
  const totalHaber = lineas.reduce((s, l) => s + ((l.importe || 0) < 0 ? Math.abs(l.importe || 0) : 0), 0)

  return (
    <div>
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div>
          <label className="label">Cuenta *</label>
          <AutocompleteCuenta empresaId={empresa.id} value={cuentaVal}
            onChange={setCuentaVal} className="w-80"
            onKeyDown={(e) => e.key === 'Enter' && buscar()} />
        </div>
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
        <button className="btn btn-primary self-end" onClick={() => buscar(0)}>Consultar</button>
        {buscado && cuenta && (
          <button className="btn btn-secondary self-end" onClick={() => setModalExport(true)}>
            Exportar CSV...
          </button>
        )}
      </div>

      {buscado && (
        <>
          {lineas.length === 0 ? (
            <div className="card p-8 text-center text-gray-400">Sin movimientos para la cuenta <span className="font-mono font-semibold">{cuenta}</span></div>
          ) : (
            <div className="card">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Fecha</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Asiento</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Tipo</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Ref.</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Debe</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Haber</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Saldo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {skip > 0 && (
                    <tr className="bg-gray-50 text-xs text-gray-400 italic">
                      <td colSpan={6} className="px-4 py-1.5">Saldo anterior ({skip} movimientos)</td>
                      <td className={`px-4 py-1.5 text-right font-mono font-semibold ${saldoAnterior < 0 ? 'text-red-400' : 'text-gray-500'}`}>
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
                      <td className={`px-4 py-2.5 text-right font-mono text-xs font-semibold ${l.saldoAcum < 0 ? 'text-red-600' : 'text-gray-800'}`}>
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
                    <td className={`px-4 py-2.5 text-right font-mono text-xs font-bold ${saldoAcum < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                      {EUR(saldoAcum)}
                    </td>
                  </tr>
                </tfoot>
              </table>
              <Paginacion total={total} skip={skip} limit={limitMayor} onCambiar={(s) => buscar(s)}
                onLimitChange={(n) => { setLimitMayor(n); buscar(0, n) }} />
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

// ── Pestaña Sumas y Saldos ────────────────────────────────────────────────────

function TabSumasSaldos({ empresa }) {
  const [fechaDesde, setFechaDesde] = useState(`${anioActual - 1}-01-01`)
  const [fechaHasta, setFechaHasta] = useState(`${anioActual - 1}-12-31`)
  const [nivel, setNivel]           = useState('')
  const [data, setData]             = useState(null)
  const [cargando, setCargando]     = useState(false)

  const consultar = async () => {
    setCargando(true)
    try {
      const params = { empresa_id: empresa.id }
      if (fechaDesde) params.fecha_desde = fechaDesde
      if (fechaHasta) params.fecha_hasta = fechaHasta
      if (nivel) params.nivel = parseInt(nivel)
      const res = await getSumasSaldos(params)
      setData(res)
    } finally {
      setCargando(false)
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-end gap-3 mb-4">
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
        {data && (
          <button className="btn btn-secondary self-end"
            onClick={() => exportarCSV('sumas-saldos', { empresa_id: empresa.id, fecha_desde: fechaDesde, fecha_hasta: fechaHasta })}>
            Exportar CSV
          </button>
        )}
      </div>

      {data && (
        <div className="card">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-28">Cuenta</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Descripción</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Debe</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Haber</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Sd. Deudor</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Sd. Acreedor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.filas.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Sin movimientos en el periodo</td></tr>
              )}
              {data.filas.map((f) => (
                <tr key={f.cuenta} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-gray-800 font-medium">{f.cuenta}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{f.texto}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-gray-700">{EUR(f.debe)}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-gray-700">{EUR(f.haber)}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-green-700">{f.saldo_deudor > 0 ? EUR(f.saldo_deudor) : ''}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-red-600">{f.saldo_acreedor > 0 ? EUR(f.saldo_acreedor) : ''}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50 border-t-2 border-gray-300 font-bold text-sm">
              <tr>
                <td colSpan={2} className="px-4 py-3 text-gray-700">TOTAL ({data.filas.length} cuentas)</td>
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

// ── Pestaña P&G ───────────────────────────────────────────────────────────────

function TabPyG({ empresa }) {
  const [fechaDesde, setFechaDesde] = useState(`${anioActual}-01-01`)
  const [fechaHasta, setFechaHasta] = useState(`${anioActual}-12-31`)
  const [data, setData]             = useState(null)
  const [cargando, setCargando]     = useState(false)

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
            {filas.length === 0
              ? <tr><td colSpan={3} className="px-4 py-4 text-center text-gray-400 text-xs">Sin movimientos</td></tr>
              : filas.map((f) => {
                  // importe neto del backend (una cuenta 6 con abonos puede ser negativa)
                  const imp = f.importe ?? (f.saldo_deudor > 0 ? f.saldo_deudor : f.saldo_acreedor)
                  return (
                    <tr key={f.cuenta} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-gray-800">{f.cuenta}</td>
                      <td className="px-4 py-2 text-gray-600 text-xs">{f.texto}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{EUR(imp)}</td>
                    </tr>
                  )
                })
            }
          </tbody>
          <tfoot className="bg-gray-50 border-t-2 border-gray-300 font-bold">
            <tr>
              <td colSpan={2} className="px-4 py-2.5 text-gray-700 text-sm">{totalLabel}</td>
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
          <input type="date" className="input" value={fechaDesde}
            onChange={(e) => setFechaDesde(e.target.value)} />
        </div>
        <div>
          <label className="label">Hasta</label>
          <input type="date" className="input" value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)} />
        </div>
        <button className="btn btn-primary self-end" onClick={consultar} disabled={cargando}>
          {cargando ? 'Calculando...' : 'Calcular'}
        </button>
        {data && (
          <button className="btn btn-secondary self-end"
            onClick={() => exportarCSV('pyg', { empresa_id: empresa.id, fecha_desde: fechaDesde, fecha_hasta: fechaHasta })}>
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

          <div className={`card p-5 flex justify-between items-center text-lg font-bold border-2 ${
            data.resultado >= 0 ? 'border-green-400 bg-green-50' : 'border-red-400 bg-red-50'
          }`}>
            <span className="text-gray-800">
              {data.resultado >= 0 ? 'Beneficio del ejercicio' : 'Pérdida del ejercicio'}
            </span>
            <span className={data.resultado >= 0 ? 'text-green-700' : 'text-red-600'}>
              {EUR(Math.abs(data.resultado))}
            </span>
          </div>

          {data.saldo_inicial_bancos > 0 && (
            <div className={`card p-5 mt-2 flex justify-between items-center text-lg font-bold border-2 ${
              data.resultado_con_saldo_inicial >= 0 ? 'border-blue-400 bg-blue-50' : 'border-orange-400 bg-orange-50'
            }`}>
              <span className="text-gray-800">Resultado + saldo inicial</span>
              <span className={data.resultado_con_saldo_inicial >= 0 ? 'text-blue-700' : 'text-orange-600'}>
                {data.resultado_con_saldo_inicial >= 0 ? '' : '−'}{EUR(Math.abs(data.resultado_con_saldo_inicial))}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Pestaña Balance de situación ─────────────────────────────────────────────

function TabBalance({ empresa }) {
  const [fechaDesde, setFechaDesde] = useState(`${anioActual - 1}-01-01`)
  const [fechaHasta, setFechaHasta] = useState(`${anioActual - 1}-12-31`)
  const [data, setData]             = useState(null)
  const [cargando, setCargando]     = useState(false)
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

  const SeccionBalance = ({ titulo, filas, total, colorTotal, colorFondo }) => (
    <div className="mb-3">
      <div className={`px-4 py-2 font-semibold text-sm uppercase tracking-wide rounded-t-lg border ${colorFondo}`}>
        {titulo}
      </div>
      <div className="border border-t-0 border-gray-200 rounded-b-lg overflow-hidden">
        <table className="w-full text-sm">
          <tbody className="divide-y divide-gray-100">
            {filas.length === 0
              ? <tr><td colSpan={2} className="px-4 py-3 text-center text-gray-400 text-xs">Sin movimientos</td></tr>
              : filas.map((f) => (
                  <tr key={f.cuenta} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-gray-800 w-32">{f.cuenta}</td>
                    <td className="px-4 py-2 text-gray-600 text-xs">{f.texto}</td>
                    <td className="px-4 py-2 text-right font-mono text-xs">{EUR(f.importe)}</td>
                  </tr>
                ))
            }
          </tbody>
          <tfoot className="bg-gray-50 border-t-2 border-gray-300 font-bold">
            <tr>
              <td colSpan={2} className="px-4 py-2 text-gray-700 text-sm">Total</td>
              <td className={`px-4 py-2 text-right font-mono text-sm ${colorTotal}`}>{EUR(total)}</td>
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
          <input type="date" className="input" value={fechaDesde}
            onChange={(e) => setFechaDesde(e.target.value)} />
        </div>
        <div>
          <label className="label">Hasta</label>
          <input type="date" className="input" value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)} />
        </div>
        <button className="btn btn-primary self-end" onClick={consultar} disabled={cargando}>
          {cargando ? 'Calculando...' : 'Calcular'}
        </button>
        {data && (
          <button className="btn btn-secondary self-end"
            onClick={() => exportarCSV('balance', { empresa_id: empresa.id, fecha_desde: fechaDesde, fecha_hasta: fechaHasta })}>
            Exportar CSV
          </button>
        )}
        <button className="btn self-end bg-amber-600 hover:bg-amber-700 text-white"
          onClick={() => setModalCierre(true)}>
          Cierre de ejercicio
        </button>
      </div>

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-5xl">
          {/* ACTIVO */}
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

          {/* PASIVO + PN */}
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
              <span className={Math.abs(data.total_activo - data.total_pasivo_pn) > 0.5 ? 'text-red-600' : 'text-red-700'}>
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

      {modalCierre && (
        <ModalCierre empresa={empresa} onClose={() => setModalCierre(false)} onDone={consultar} />
      )}
    </div>
  )
}


function ModalCierre({ empresa, onClose, onDone }) {
  const [anio, setAnio]         = useState(anioActual - 1)
  const [apertura, setApertura] = useState(true)
  const [cargando, setCargando] = useState(false)
  const [resultado, setResultado] = useState(null)

  const ejecutar = async () => {
    if (!confirm(`¿Realizar cierre del ejercicio ${anio}?\n\nEsto creará los asientos de regularización, cierre${apertura ? ' y apertura' : ''}.\nEsta acción no se puede deshacer fácilmente.`)) return
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
              Se generarán los asientos contables de fin de año para el ejercicio seleccionado:
              regularización (cuentas 6/7 → 129), cierre (saldo a cero) y, opcionalmente, apertura del ejercicio siguiente.
            </p>
            <div>
              <label className="label">Ejercicio a cerrar</label>
              <input type="number" className="input w-32" value={anio}
                min={2000} max={2099}
                onChange={(e) => setAnio(parseInt(e.target.value))} />
            </div>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={apertura} onChange={(e) => setApertura(e.target.checked)}
                className="rounded" />
              Crear también asiento de apertura ({anio + 1})
            </label>
            <div className="flex gap-2 justify-end pt-2">
              <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
              <button className="btn bg-amber-600 hover:bg-amber-700 text-white" onClick={ejecutar} disabled={cargando}>
                {cargando ? 'Procesando...' : `Cerrar ejercicio ${anio}`}
              </button>
            </div>
          </>
        )}
        {resultado && (
          <div className="flex justify-end">
            <button className="btn btn-primary" onClick={onClose}>Cerrar</button>
          </div>
        )}
      </div>
    </Modal>
  )
}


// ── Pestaña Conciliación ──────────────────────────────────────────────────────

function FilaBanco({ b, empresaId, onRefresh }) {
  const [abierto,     setAbierto]     = useState(false)
  const [corrigiendo, setCorrigiendo] = useState(null)
  const [avisos,      setAvisos]      = useState({})   // numero → mensaje de aviso

  const sinAsiento  = b.detalle.filter((p) => p.tipo === 'sin_asiento')
  const importeDiff = b.detalle.filter((p) => p.tipo === 'importe_diff')
  const huerfanos   = b.detalle.filter((p) => p.tipo === 'asiento_huerfano')

  const corregir = async (numero) => {
    setCorrigiendo(numero)
    setAvisos((a) => { const n = {...a}; delete n[numero]; return n })
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
          <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${
            !b.ok ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
          }`}>
            {!b.ok ? '✗ Discrepancia' : '✓ OK'}
          </span>
        </td>
        <td className="px-4 py-2.5 font-medium text-gray-800">{b.nombre}</td>
        <td className="px-4 py-2.5 font-mono text-sm text-gray-600">{b.cuenta}</td>
        <td className="px-4 py-2.5 text-right font-mono text-sm text-gray-700">{EUR(b.saldo_banco)}</td>
        <td className="px-4 py-2.5 text-right font-mono text-sm text-gray-700">{EUR(b.saldo_lm)}</td>
        <td className={`px-4 py-2.5 text-right font-mono text-sm font-bold ${Math.abs(b.diferencia) >= 0.01 ? 'text-red-600' : 'text-gray-400'}`}>
          {Math.abs(b.diferencia) >= 0.01 ? EUR(b.diferencia) : '—'}
        </td>
        <td className="px-4 py-2.5 text-center text-gray-400 text-xs">{abierto ? '▲' : '▼'}</td>
      </tr>

      {abierto && (
        <tr>
          <td colSpan={7} className="bg-gray-50 px-6 pb-4 pt-2">
            {b.ok && (
              <p className="text-green-600 text-sm">Sin discrepancias. Saldo banco y libro mayor coinciden.</p>
            )}

            {!b.ok && Math.abs(b.base_lm) >= 0.01 && (
              <p className="text-xs text-gray-500 mb-3">
                Base libro mayor (apertura / migrados): <span className="font-mono font-semibold">{EUR(b.base_lm)}</span>
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
                        <td className="py-1 text-right font-mono text-gray-500">{p.saldo_banco != null ? EUR(p.saldo_banco) : '—'}</td>
                        <td className="py-1 text-right">
                          {p.es_transferencia ? (
                            <span className="text-xs text-amber-600 italic">transferencia</span>
                          ) : (
                            <button
                              className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700 hover:bg-blue-200 disabled:opacity-50"
                              disabled={corrigiendo === p.numero}
                              onClick={() => corregir(p.numero)}
                            >
                              {corrigiendo === p.numero ? '...' : 'Generar'}
                            </button>
                          )}
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
                          <button
                            className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-700 hover:bg-amber-200 disabled:opacity-50"
                            disabled={corrigiendo === p.numero}
                            onClick={() => corregir(p.numero)}
                          >
                            {corrigiendo === p.numero ? '...' : 'Corregir'}
                          </button>
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

function TabConciliacion({ empresa }) {
  const [data, setData]         = useState(null)
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

  const nOK   = data ? data.filter((b) => b.ok).length : 0
  const nDisc = data ? data.filter((b) => !b.ok).length : 0

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <button className="btn btn-primary" onClick={consultar} disabled={cargando}>
          {cargando ? 'Analizando...' : 'Analizar discrepancias'}
        </button>
        {data && (
          <div className="flex gap-4 text-sm">
            <span className="text-green-700 font-medium">{nOK} banco{nOK !== 1 ? 's' : ''} OK</span>
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
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Saldo libro mayor</th>
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

// ── Pestaña Diagnóstico ───────────────────────────────────────────────────────

function TabDiagnostico({ empresa }) {
  const [data,       setData]       = useState(null)
  const [cargando,   setCargando]   = useState(false)
  const [reparando,  setReparando]  = useState(false)
  const [resultado,  setResultado]  = useState(null)
  const [regenInfo,  setRegenInfo]  = useState({})   // numero → mensaje

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
    if (!confirm('¿Generar todos los asientos pendientes? Esta acción no es reversible.')) return
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
          <button
            className="btn btn-warning"
            onClick={reparar}
            disabled={reparando}
          >
            {reparando ? 'Reparando...' : `Reparar todo (${total} problemas)`}
          </button>
        )}
      </div>

      {resultado && (
        <div className="p-3 rounded-lg bg-blue-50 border border-blue-200 text-sm text-blue-800">
          Generados: <strong>{resultado.extras}</strong> asientos de extras,{' '}
          <strong>{resultado.banco}</strong> de banco,{' '}
          <strong>{resultado.facturas_rec}</strong> de facturas recibidas,{' '}
          <strong>{resultado.facturas_emi}</strong> de facturas emitidas.
          Total: <strong>{resultado.total}</strong>
        </div>
      )}

      {data && (
        <>
          {/* ── Extras sin asiento ──────────────────────────────────────── */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Extras con apuntes completos sin asiento contable
              {' '}
              <span className={`ml-1 px-2 py-0.5 rounded-full text-xs font-bold ${
                data.extras_sin_asiento.length > 0
                  ? 'bg-red-100 text-red-700'
                  : 'bg-green-100 text-green-700'
              }`}>
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
                        <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${
                          x.estado === 'C' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                        }`}>{x.estado || '—'}</span>
                      </td>
                      <td className="px-3 py-1.5 text-gray-600">{x.texto}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {/* ── Movimientos bancarios sin asiento ──────────────────────── */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Movimientos bancarios con pagos pero sin asiento
              {' '}
              <span className={`ml-1 px-2 py-0.5 rounded-full text-xs font-bold ${
                data.movimientos_sin_asiento.length > 0
                  ? 'bg-red-100 text-red-700'
                  : 'bg-green-100 text-green-700'
              }`}>
                {data.movimientos_sin_asiento.length}
              </span>
            </h3>
            {data.movimientos_sin_asiento.length === 0 ? (
              <p className="text-sm text-gray-400">Ninguno. Todos los movimientos tienen asiento o no tienen pagos asociados.</p>
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
                            <span className={`ml-2 text-xs ${info.startsWith('Error') ? 'text-red-600' : 'text-blue-600'}`}>
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

          {/* ── Cuentas de proveedor desequilibradas ───────────────────── */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Cuentas de proveedor (4xxxx) con saldo deudor
              {' '}
              <span className={`ml-1 px-2 py-0.5 rounded-full text-xs font-bold ${
                data.cuentas_desequilibradas.length > 0
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-green-100 text-green-700'
              }`}>
                {data.cuentas_desequilibradas.length}
              </span>
            </h3>
            <p className="text-xs text-gray-400 mb-2">
              Un saldo deudor en cuentas de proveedor indica que se han registrado más pagos que deudas
              — síntoma habitual de asientos de extras incompletos.
            </p>
            {data.cuentas_desequilibradas.length === 0 ? (
              <p className="text-sm text-gray-400">Ninguna. Todas las cuentas de proveedor tienen saldo normal (acreedor o cero).</p>
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
                      <td className="px-3 py-1.5 text-right font-mono font-semibold text-amber-700">{EUR(c.saldo_deudor)}</td>
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
          Pulsa "Analizar contabilidad" para detectar posibles inconsistencias: extras sin asiento,
          movimientos bancarios pendientes y cuentas de proveedor desequilibradas.
        </p>
      )}
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function ContabilidadPage() {
  const { empresa } = useEmpresa()
  const [searchParams] = useSearchParams()
  const tabParam    = searchParams.get('tab')    || 'cuentas'
  const cuentaParam = searchParams.get('cuenta') || ''
  const [tab, setTab] = useState(tabParam)
  const [cuentaMayor, setCuentaMayor] = useState(cuentaParam)

  const irAMayor = useCallback((cuenta) => {
    setCuentaMayor(cuenta)
    setTab('mayor')
  }, [])

  if (!empresa) {
    return (
      <div className="p-8 text-center text-gray-400">
        Selecciona una empresa para ver la contabilidad.
      </div>
    )
  }

  const tabs = [
    { id: 'cuentas',      label: 'Plan de cuentas' },
    { id: 'diario',       label: 'Diario' },
    { id: 'mayor',        label: 'Libro mayor' },
    { id: 'sumas',        label: 'Sumas y saldos' },
    { id: 'pyg',          label: 'P&G' },
    { id: 'balance',      label: 'Balance' },
    { id: 'conciliacion', label: 'Conciliación' },
    { id: 'diagnostico',  label: 'Diagnóstico' },
  ]

  return (
    <div className="h-full overflow-y-auto">
      {/* Cabecera */}
      <div className="bg-gray-50 border-b border-gray-200 px-6 pt-5 pb-0">
        <div className="mb-3">
          <h1 className="text-2xl font-bold text-gray-900">Contabilidad</h1>
          <p className="text-gray-500 text-sm mt-1">{empresa.nombre}</p>
        </div>
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

      {/* Contenido */}
      <div className="p-6">
        {tab === 'cuentas'      && <TabCuentas empresa={empresa} onIrAMayor={irAMayor} />}
        {tab === 'diario'       && <TabDiario empresa={empresa} />}
        {tab === 'mayor'        && <TabMayor empresa={empresa} cuentaInicial={cuentaMayor} />}
        {tab === 'sumas'        && <TabSumasSaldos empresa={empresa} />}
        {tab === 'pyg'          && <TabPyG empresa={empresa} />}
        {tab === 'balance'      && <TabBalance empresa={empresa} />}
        {tab === 'conciliacion' && <TabConciliacion empresa={empresa} />}
        {tab === 'diagnostico'  && <TabDiagnostico empresa={empresa} />}
      </div>
    </div>
  )
}
