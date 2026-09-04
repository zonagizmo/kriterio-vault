import { useState, useEffect, useCallback, useRef } from 'react'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import Modal from '../components/Modal'
import Paginacion from '../components/Paginacion'
import { getExtras, createExtra, updateExtra, deleteExtra, renumerarExtras } from '../services/extras'
import { getCuentas } from '../services/contabilidad'

const EUR = (v) =>
  (v ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
const hoy = () => new Date().toISOString().slice(0, 10)
const fmtFecha = (f) => {
  if (!f) return ''
  const [y, m, d] = String(f).split('-')
  return `${d}/${m}/${y}`
}

const TIPOS = { G: 'Gasto', I: 'Ingreso', M: 'Gasto', A: 'Apertura', R: 'Regulariz.', Z: 'Cierre' }

function badgeVto(fechaVto) {
  if (!fechaVto) return null
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0)
  const vto = new Date(fechaVto); vto.setHours(0, 0, 0, 0)
  const dias = Math.round((vto - hoy) / 86400000)
  if (dias < 0)
    return <span className="ml-1 inline-block px-1.5 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-700">Vencido</span>
  if (dias <= 7)
    return <span className="ml-1 inline-block px-1.5 py-0.5 rounded text-xs font-semibold bg-orange-100 text-orange-700">Vence {dias === 0 ? 'hoy' : `en ${dias}d`}</span>
  return null
}

const totalExtras = (apuntes, tipo) =>
  apuntes
    .filter((a) => (tipo === 'I' ? a.dh === 'H' : a.dh === 'D'))
    .reduce((s, a) => s + (a.importe ?? 0), 0)

const mapApunteFromApi = (a) => ({
  cuenta: a.cuenta || '',
  ayuda: a.ayuda || '',
  dh: a.dh || 'D',
  importe: a.importe ?? '',
  declterc: a.declterc || '',
})

const apunteVacio = (dh = 'D') => ({ cuenta: '', ayuda: '', dh, importe: '', declterc: '' })

// ── Fila de apunte contable con autocomplete cuenta↔descripción ───────────────
function FilaApunte({ apunte, onChange, onRemove, empresaId, focusCuenta }) {
  const [resultados, setResultados]     = useState([])
  const [foco, setFoco]                 = useState(null) // 'cuenta' | 'ayuda'
  const [highlighted, setHighlighted]   = useState(-1)
  const trRef    = useRef(null)
  const listRef  = useRef(null)
  const timerRef = useRef(null)

  useEffect(() => {
    if (highlighted >= 0 && listRef.current) {
      listRef.current.children[highlighted]?.scrollIntoView({ block: 'nearest' })
    }
  }, [highlighted])

  const buscar = (q) => {
    clearTimeout(timerRef.current)
    if (!q || q.length < 1) { setResultados([]); setHighlighted(-1); return }
    timerRef.current = setTimeout(async () => {
      try {
        const data = await getCuentas({ empresa_id: empresaId, q, limit: 15 })
        setResultados(data.items || [])
        setHighlighted(-1)
      } catch {}
    }, 200)
  }

  const seleccionar = (c) => {
    onChange({ ...apunte, cuenta: c.cuenta, ayuda: c.texto })
    setResultados([])
    setFoco(null)
    setHighlighted(-1)
  }

  const onKeyDown = (e) => {
    if (resultados.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault(); setHighlighted((h) => Math.min(h + 1, resultados.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault(); setHighlighted((h) => Math.max(h - 1, 0))
    } else if (e.key === 'Enter' && highlighted >= 0) {
      e.preventDefault(); seleccionar(resultados[highlighted])
    } else if (e.key === 'Escape') {
      setResultados([]); setFoco(null)
    }
  }

  const onBlur = () => {
    setTimeout(() => {
      if (!trRef.current?.contains(document.activeElement)) {
        setResultados([]); setFoco(null); setHighlighted(-1)
      }
    }, 150)
  }

  const dropdown = (
    <div
      ref={listRef}
      className="absolute z-50 left-0 top-full mt-0.5 w-80 bg-white border border-gray-200 rounded-lg shadow-lg max-h-52 overflow-auto"
    >
      {resultados.map((c, i) => (
        <div
          key={c.id ?? c.cuenta}
          onMouseDown={(e) => { e.preventDefault(); seleccionar(c) }}
          onMouseEnter={() => setHighlighted(i)}
          className={`px-3 py-2 cursor-pointer flex items-center gap-2 ${
            i === highlighted ? 'bg-mgd-600 text-white' : 'hover:bg-blue-50'
          }`}
        >
          <span className={`font-mono text-xs shrink-0 ${i === highlighted ? 'text-blue-100' : 'text-gray-400'}`}>
            {c.cuenta}
          </span>
          <span className={`text-sm truncate ${i === highlighted ? 'text-white' : 'text-gray-800'}`}>
            {c.texto}
          </span>
        </div>
      ))}
    </div>
  )

  return (
    <tr ref={trRef} className="border-b border-gray-50 last:border-0">
      <td className="py-1.5 pr-2 relative">
        <input
          ref={(el) => { if (el && focusCuenta) el.focus() }}
          className="input text-sm font-mono"
          placeholder="570.0.000"
          value={apunte.cuenta}
          onFocus={() => setFoco('cuenta')}
          onBlur={onBlur}
          onChange={(e) => { onChange({ ...apunte, cuenta: e.target.value }); buscar(e.target.value) }}
          onKeyDown={onKeyDown}
        />
        {resultados.length > 0 && foco === 'cuenta' && dropdown}
      </td>
      <td className="py-1.5 pr-2 pl-2 relative">
        <input
          className="input text-sm"
          placeholder="Descripción cuenta"
          value={apunte.ayuda}
          onFocus={() => setFoco('ayuda')}
          onBlur={onBlur}
          onChange={(e) => { onChange({ ...apunte, ayuda: e.target.value }); buscar(e.target.value) }}
          onKeyDown={onKeyDown}
        />
        {resultados.length > 0 && foco === 'ayuda' && dropdown}
      </td>
      <td className="py-1.5 pr-2">
        <select
          className="input text-sm text-center"
          value={apunte.dh}
          onChange={(e) => onChange({ ...apunte, dh: e.target.value })}
        >
          <option value="D">D</option>
          <option value="H">H</option>
        </select>
      </td>
      <td className="py-1.5 pr-2">
        <input
          type="number"
          step="0.01"
          className="input text-sm text-right"
          placeholder="0,00"
          value={apunte.importe}
          onChange={(e) => onChange({ ...apunte, importe: e.target.value })}
        />
      </td>
      <td className="py-1.5 pl-1">
        <button className="text-red-400 hover:text-red-600 px-1" onClick={onRemove}>✕</button>
      </td>
    </tr>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────
export default function ExtrasPage() {
  const { empresa } = useEmpresa()

  const [extras, setExtras]   = useState([])
  const [total, setTotal]     = useState(0)
  const [skip, setSkip]       = useState(0)
  const [limit, setLimit]     = useState(50)
  const [filtroTipo, setFiltroTipo]     = useState('')
  const [fechaDesde, setFechaDesde]     = useState('')
  const [fechaHasta, setFechaHasta]     = useState('')
  const [filtroEstado, setFiltroEstado] = useState('')
  const [q, setQ]                       = useState('')

  const [modal, setModal]         = useState(null)
  const [form, setForm]           = useState({})
  const [apuntes, setApuntes]     = useState([])
  const [genVto, setGenVto]       = useState(false)
  const [vtoForm, setVtoForm]     = useState({ importe: '', cuenta: '', fecha: '' })
  const [error, setError]         = useState('')
  const [guardando, setGuardando] = useState(false)
  const justAddedLine = useRef(false)
  const fechaRef = useRef(null)
  const [nuevoId, setNuevoId] = useState(null)
  const filaRef = useRef(null)

  const cargar = useCallback(async () => {
    if (!empresa) return
    const params = { empresa_id: empresa.id, skip, limit }
    if (filtroTipo) params.tipo = filtroTipo
    if (fechaDesde) params.fecha_desde = fechaDesde
    if (fechaHasta) params.fecha_hasta = fechaHasta
    if (filtroEstado) params.estado = filtroEstado
    if (q) params.q = q
    const data = await getExtras(params)
    setExtras(data.items)
    setTotal(data.total)
  }, [empresa, filtroTipo, fechaDesde, fechaHasta, filtroEstado, q, skip, limit])

  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { setSkip(0) }, [filtroTipo, fechaDesde, fechaHasta, filtroEstado, q])

  useEffect(() => {
    if (!nuevoId || !filaRef.current) return
    filaRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    const t = setTimeout(() => setNuevoId(null), 1800)
    return () => clearTimeout(t)
  }, [nuevoId, extras])

  const formVacio = () => ({
    fecha: hoy(), tipo: 'G', texto: '', grupo: '', clave: '', estado: 'P', notas: '',
  })

  const abrirNuevo = () => {
    setForm(formVacio())
    setApuntes([apunteVacio('D')])
    setGenVto(false)
    setVtoForm({ importe: '', cuenta: '', fecha: '' })
    setModal('nuevo')
    setError('')
  }

  const abrirEditar = (extra) => {
    setForm({
      fecha: extra.fecha, tipo: extra.tipo || 'G', texto: extra.texto || '',
      grupo: extra.grupo || '', clave: extra.clave || '',
      estado: extra.estado || '', notas: extra.notas || '',
    })
    setApuntes(extra.apuntes?.length ? extra.apuntes.map(mapApunteFromApi) : [apunteVacio('D')])
    setGenVto(false)
    setVtoForm({ importe: '', cuenta: '', fecha: '' })
    setModal(extra)
    setError('')
  }

  const setApunte = (i, newApunte) => {
    const arr = [...apuntes]
    arr[i] = newApunte
    setApuntes(arr)
  }

  const addApunte = () => {
    const lastDh = apuntes.length > 0 ? apuntes[apuntes.length - 1].dh : 'D'
    setApuntes([...apuntes, apunteVacio(lastDh === 'D' ? 'H' : 'D')])
    justAddedLine.current = true
  }

  const removeApunte = (i) => setApuntes(apuntes.filter((_, idx) => idx !== i))

  const totalApuntes = apuntes
    .filter((a) => (form.tipo === 'I' ? a.dh === 'H' : a.dh === 'D'))
    .reduce((s, a) => s + (parseFloat(a.importe) || 0), 0)

  const totalDebe  = apuntes.reduce((s, a) => a.dh === 'D' ? s + (parseFloat(a.importe) || 0) : s, 0)
  const totalHaber = apuntes.reduce((s, a) => a.dh === 'H' ? s + (parseFloat(a.importe) || 0) : s, 0)
  const descuadre  = Math.round((totalDebe - totalHaber) * 100) / 100

  const toggleGenVto = (checked) => {
    setGenVto(checked)
    if (checked) {
      const cuentaHaber = apuntes.find((a) => a.dh === 'H')?.cuenta || ''
      setVtoForm((v) => ({
        importe: v.importe || totalApuntes,
        cuenta: v.cuenta || cuentaHaber,
        fecha: v.fecha || form.fecha,
      }))
    }
  }

  const guardar = async () => {
    if (!form.fecha)    { setError('La fecha es obligatoria'); return }
    if (!form.tipo)     { setError('El tipo es obligatorio'); return }
    if (descuadre !== 0) { setError(`El asiento no está cuadrado — Debe: ${EUR(totalDebe)} · Haber: ${EUR(totalHaber)} · Diferencia: ${EUR(Math.abs(descuadre))}`); return }
    setGuardando(true)
    try {
      const apuntesClean = apuntes
        .filter((a) => parseFloat(a.importe) !== 0 && !isNaN(parseFloat(a.importe)))
        .map((a) => ({
          cuenta: a.cuenta || null,
          ayuda: a.ayuda || null,
          dh: a.dh || 'D',
          importe: parseFloat(a.importe),
          declterc: a.declterc || null,
        }))

      const payload = {
        fecha: form.fecha, tipo: form.tipo,
        texto: form.texto || null, grupo: form.grupo || null,
        clave: form.clave || null, estado: form.estado || null,
        notas: form.notas || null, apuntes: apuntesClean,
        generar_vto: genVto,
        vto_importe: genVto && vtoForm.importe ? parseFloat(vtoForm.importe) : null,
        vto_cuenta: genVto && vtoForm.cuenta ? vtoForm.cuenta : null,
        vto_fecha: genVto && vtoForm.fecha ? vtoForm.fecha : null,
      }

      if (modal === 'nuevo') {
        const created = await createExtra({ ...payload, empresa_id: empresa.id })
        setNuevoId(created.id)
        if (skip !== 0) setSkip(0)  // nuevo extra aparece en pág. 1 (orden DESC)
        // Reabrir el formulario en blanco para poder seguir dando de alta extras seguidos
        setForm(formVacio())
        setApuntes([apunteVacio('D')])
        setGenVto(false)
        setVtoForm({ importe: '', cuenta: '', fecha: '' })
        fechaRef.current?.focus()
        cargar()
      } else {
        await updateExtra(modal.id, payload)
        setModal(null)
        cargar()
      }
    } catch {
      setError('Error al guardar')
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async (extra) => {
    if (!confirm(`¿Eliminar el extra #${extra.numero}?`)) return
    try {
      await deleteExtra(extra.id)
      cargar()
    } catch (e) {
      alert(e.message || 'Error al eliminar')
    }
  }

  const renumerar = async (desdeId = null) => {
    const msg = desdeId
      ? '¿Renumerar extras desde este en adelante (mismo año)?'
      : '¿Renumerar todos los extras por orden de fecha?'
    if (!confirm(msg)) return
    try {
      const res = await renumerarExtras(empresa.id, desdeId)
      alert(`${res.renumeradas} extras renumerados correctamente.`)
      cargar()
    } catch (e) { alert(e.message) }
  }

  if (!empresa) {
    return <div className="p-8 text-center text-gray-400">Selecciona una empresa.</div>
  }

  const esNuevo = modal === 'nuevo'

  return (
    <div className="h-full overflow-y-auto">
      {/* Cabecera */}
      <div className="bg-gray-50 border-b border-gray-200 px-6 pt-5 pb-4">
        <div className="mb-2">
          <h1 className="text-2xl font-bold text-gray-900">Extras</h1>
          <p className="text-sm text-gray-500">{empresa.nombre} — Gastos e ingresos sin factura</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="label">Concepto</label>
            <input type="search" placeholder="Buscar concepto..."
              value={q} onChange={(e) => setQ(e.target.value)} className="input w-44" />
          </div>
          <div>
            <label className="label">Desde</label>
            <input type="date" value={fechaDesde}
              onChange={(e) => setFechaDesde(e.target.value)} className="input w-38" />
          </div>
          <div>
            <label className="label">Hasta</label>
            <input type="date" value={fechaHasta}
              onChange={(e) => setFechaHasta(e.target.value)} className="input w-38" />
          </div>
          <div>
            <label className="label">Tipo</label>
            <select className="input w-36" value={filtroTipo} onChange={(e) => setFiltroTipo(e.target.value)}>
              <option value="">Todos</option>
              <option value="G">Gastos</option>
              <option value="I">Ingresos</option>
            </select>
          </div>
          <div>
            <label className="label">Estado</label>
            <select className="input w-36" value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)}>
              <option value="">Todos</option>
              <option value="P">Pendiente</option>
              <option value="C">Cobrado / Pagado</option>
            </select>
          </div>
          {(q || fechaDesde || fechaHasta || filtroTipo || filtroEstado) && (
            <button
              className="btn btn-secondary text-sm"
              onClick={() => { setQ(''); setFechaDesde(''); setFechaHasta(''); setFiltroTipo(''); setFiltroEstado('') }}
            >
              Borrar filtros
            </button>
          )}
          <span className="text-sm text-gray-500 ml-auto self-center">{total} extra{total !== 1 ? 's' : ''}</span>
          <button onClick={() => renumerar()} className="btn btn-secondary text-sm">Renumerar</button>
          <button className="btn btn-primary" onClick={abrirNuevo}>+ Nuevo extra</button>
        </div>
      </div>

      {/* Contenido */}
      <div className="p-6">
      <div className="card">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Nº</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Fecha</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Tipo</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Concepto</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Grupo</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Total</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Estado</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {extras.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-10 text-center text-gray-400">Sin extras registrados</td></tr>
            )}
            {extras.map((e) => {
              const tot = totalExtras(e.apuntes, e.tipo)
              return (
                <tr
                  key={e.id}
                  ref={e.id === nuevoId ? filaRef : null}
                  className={`hover:bg-gray-50 transition-colors ${e.id === nuevoId ? 'bg-mgd-50 outline outline-1 outline-mgd-300' : ''}`}
                >
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs whitespace-nowrap">
                    {(e.cnumero ?? e.numero)}/{(e.fecha || '').slice(0, 4)}
                    <button onClick={() => renumerar(e.id)} className="ml-1 text-gray-300 hover:text-gray-500 text-xs" title="Renumerar desde aquí">↺</button>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{fmtFecha(e.fecha)}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      e.tipo === 'I' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>{TIPOS[e.tipo] ?? e.tipo}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-900">{e.texto}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{e.grupo}</td>
                  <td className={`px-4 py-3 text-right font-medium ${e.tipo === 'I' ? 'text-green-700' : 'text-red-600'}`}>
                    {EUR(e.tipo === 'I' ? tot : -tot)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {(() => {
                      const label = e.estado === 'C' ? (e.tipo === 'I' ? 'Cobrado' : 'Pagado') : 'Pendiente'
                      const cls = e.estado === 'C' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                      return (
                        <>
                          <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>{label}</span>
                          {e.estado === 'P' && badgeVto(e.fecha_vto)}
                          {e.pago_info && (
                            <div
                              className="text-xs text-gray-400 mt-0.5 truncate max-w-[120px] mx-auto"
                              title={`${e.pago_info.banco_nombre}${e.pago_info.fecha ? ' — ' + fmtFecha(e.pago_info.fecha) : ''}`}
                            >
                              {e.pago_info.banco_nombre}
                            </div>
                          )}
                        </>
                      )
                    })()}
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button className="btn btn-secondary text-xs mr-2" onClick={() => abrirEditar(e)}>Editar</button>
                    <button className="text-red-500 hover:text-red-700 text-xs font-medium" onClick={() => eliminar(e)}>Eliminar</button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <Paginacion total={total} skip={skip} limit={limit} onCambiar={setSkip}
        onLimitChange={(n) => { setLimit(n); setSkip(0) }} />
      </div>

      {modal && (
        <Modal
          titulo={esNuevo ? 'Nuevo extra' : `Editar extra #${modal.numero}`}
          onClose={() => setModal(null)}
          ancho="max-w-3xl"
        >
          {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="label">Fecha *</label>
              <input
                ref={fechaRef}
                autoFocus
                type="date"
                className="input"
                value={form.fecha}
                onChange={(e) => setForm({ ...form, fecha: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Tipo *</label>
              <select className="input" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
                <option value="G">Gasto</option>
                <option value="I">Ingreso</option>
              </select>
            </div>
            <div>
              <label className="label">Estado</label>
              <select className="input" value={form.estado || 'P'} onChange={(e) => setForm({ ...form, estado: e.target.value })}>
                <option value="P">Pendiente</option>
                <option value="C">Cobrado / Pagado</option>
              </select>
            </div>
            {!esNuevo && modal?.pago_info && (
              <div className="col-span-3">
                <p className="text-xs text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">
                  {form.tipo === 'I' ? 'Cobrado' : 'Pagado'} en <strong>{modal.pago_info.banco_nombre}</strong>
                  {modal.pago_info.fecha ? ` — ${fmtFecha(modal.pago_info.fecha)}` : ''}
                  {` — ${EUR(modal.pago_info.importe)}`}
                </p>
              </div>
            )}
            <div className="col-span-2">
              <label className="label">Concepto</label>
              <input className="input" value={form.texto} onChange={(e) => setForm({ ...form, texto: e.target.value })} />
            </div>
            <div>
              <label className="label">Grupo</label>
              <input className="input" value={form.grupo} onChange={(e) => setForm({ ...form, grupo: e.target.value })} />
            </div>
            <div className="col-span-3">
              <label className="label">Notas</label>
              <input className="input" value={form.notas} onChange={(e) => setForm({ ...form, notas: e.target.value })} />
            </div>
          </div>

          {/* Apuntes contables */}
          <div className="border-t pt-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <h3 className="text-sm font-semibold text-gray-700">Apuntes contables</h3>
                <span className={`text-xs font-semibold ${form.tipo === 'G' ? 'text-red-600' : 'text-green-700'}`}>
                  Total: {EUR(totalApuntes)}
                </span>
              </div>
              <button className="btn btn-secondary text-xs" onClick={addApunte}>+ Añadir línea</button>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-400 uppercase border-b border-gray-100">
                  <th className="text-left pb-2">Cuenta</th>
                  <th className="text-left pb-2 pl-2">Descripción</th>
                  <th className="text-center pb-2 w-16">D/H</th>
                  <th className="text-right pb-2 w-28">Importe</th>
                  <th className="pb-2 w-6"></th>
                </tr>
              </thead>
              <tbody>
                {apuntes.map((a, i) => {
                  const esUltima = i === apuntes.length - 1
                  const foco = esUltima && justAddedLine.current
                  if (foco) justAddedLine.current = false
                  return (
                    <FilaApunte
                      key={i}
                      apunte={a}
                      onChange={(newA) => setApunte(i, newA)}
                      onRemove={() => removeApunte(i)}
                      empresaId={empresa?.id}
                      focusCuenta={foco}
                    />
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Aviso descuadre */}
          {descuadre !== 0 && (
            <div className="mt-3 flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              <span className="text-base leading-none">⚠</span>
              <span>Asiento descuadrado — Debe: <strong>{EUR(totalDebe)}</strong> · Haber: <strong>{EUR(totalHaber)}</strong> · Diferencia: <strong>{EUR(Math.abs(descuadre))}</strong></span>
            </div>
          )}

          {/* Vencimiento: al crear, o al editar si el extra aún no tiene uno */}
          {(esNuevo || !modal?.tiene_vencimiento) && (
            <div className="border-t pt-4 mt-4">
              <label className="flex items-center gap-2 cursor-pointer select-none mb-3">
                <input type="checkbox" checked={genVto} onChange={(e) => toggleGenVto(e.target.checked)} />
                <span className="text-sm font-medium text-gray-700">Generar vencimiento de pago</span>
              </label>
              {genVto && (
                <div className="grid grid-cols-3 gap-4 pl-6">
                  <div>
                    <label className="label">Importe pendiente</label>
                    <input type="number" step="0.01" className="input"
                      value={vtoForm.importe}
                      onChange={(e) => setVtoForm({ ...vtoForm, importe: e.target.value })}
                      onBlur={(e) => {
                        const v = parseFloat(e.target.value)
                        if (!isNaN(v)) setVtoForm((f) => ({ ...f, importe: v.toFixed(2) }))
                      }} />
                  </div>
                  <div>
                    <label className="label">Cuenta contrapartida</label>
                    <input className="input font-mono" placeholder="570.0.000"
                      value={vtoForm.cuenta} onChange={(e) => setVtoForm({ ...vtoForm, cuenta: e.target.value })} />
                  </div>
                  <div>
                    <label className="label">Fecha de vencimiento</label>
                    <input type="date" className="input"
                      value={vtoForm.fecha} onChange={(e) => setVtoForm({ ...vtoForm, fecha: e.target.value })} />
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end gap-3 mt-6">
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancelar</button>
            <button className="btn btn-primary" disabled={guardando} onClick={guardar}>
              {guardando ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
