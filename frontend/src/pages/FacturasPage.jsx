import { useEffect, useRef, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import {
  getFacturasEmi, createFacturaEmi, updateFacturaEmi, deleteFacturaEmi, getFacturaEmi,
  getFacturasRec, createFacturaRec, updateFacturaRec, deleteFacturaRec, getFacturaRec,
  renumerarFacturasEmi, renumerarFacturasRec,
} from '../services/facturas'
import { getClientes } from '../services/clientes'
import { getProveedores } from '../services/proveedores'
import Modal from '../components/Modal'
import Paginacion from '../components/Paginacion'
import LineasDocumento from '../components/LineasDocumento'
import AutocompleteEntidad from '../components/AutocompleteEntidad'

const EUR =(v) => Number(v || 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
const FMT = (d) => d ? new Date(d).toLocaleDateString('es-ES') : '—'
const HOY = new Date().toISOString().slice(0, 10)

const VACIO_EMI = { fecha: HOY, cliente: '', clcuenta: '', cnumalt: '', declterc: '', ccaja: '', notas: '', estado: 'P' }
const VACIO_REC = { fecha: HOY, proveedor: '', prcuenta: '', prfactura: '', prfecha: HOY, cnumalt: '', declterc: '', notas: '', estado: 'P' }

function badgeVto(fechaVto, esEmi) {
  if (!fechaVto) return null
  const hoy = new Date(); hoy.setHours(0,0,0,0)
  const vto = new Date(fechaVto); vto.setHours(0,0,0,0)
  const dias = Math.round((vto - hoy) / 86400000)
  if (dias < 0)
    return <span className="ml-1 inline-block px-1.5 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-700">Vencida</span>
  if (dias <= 7)
    return <span className="ml-1 inline-block px-1.5 py-0.5 rounded text-xs font-semibold bg-orange-100 text-orange-700">Vence {dias === 0 ? 'hoy' : `en ${dias}d`}</span>
  return null
}

export default function FacturasPage() {
  const { empresa } = useEmpresa()
  const [searchParams] = useSearchParams()

  const tabParam = searchParams.get('tab') || 'recibidas'
  const clienteParam = searchParams.get('cliente') ? Number(searchParams.get('cliente')) : ''
  const proveedorParam = searchParams.get('proveedor') ? Number(searchParams.get('proveedor')) : ''
  const estadoParam = searchParams.get('estado') || ''

  const [tab, setTab]         = useState(tabParam)
  const esEmi = tab === 'emitidas'

  const [datos, setDatos]         = useState({ total: 0, items: [] })
  const [clientes, setClientes]   = useState([])
  const [proveedores, setProv]    = useState([])
  const [q, setQ]                 = useState('')
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')
  const [filtroEntidad, setFiltroEntidad] = useState(
    tabParam === 'emitidas' ? clienteParam : proveedorParam
  )
  const [filtroEstado, setFiltroEstado] = useState(estadoParam)
  const [skip, setSkip]           = useState(0)
  const [limit, setLimit]         = useState(50)
  const [cargando, setCargando]   = useState(false)
  const [error, setError]         = useState(null)
  const [modal, setModal]         = useState(false)
  const [form, setForm]           = useState(VACIO_EMI)
  const [lineas, setLineas]       = useState([])
  const [editId, setEditId]       = useState(null)
  const [guardando, setGuardando] = useState(false)
  const [nuevoId, setNuevoId]     = useState(null)
  const filaRef = useRef(null)
  const fechaRef = useRef(null)

  const cargar = useCallback(async () => {
    if (!empresa) return
    setCargando(true); setError(null)
    try {
      const fn = esEmi ? getFacturasEmi : getFacturasRec
      const opts = { q, skip, limit }
      if (filtroEntidad) esEmi ? (opts.cliente = filtroEntidad) : (opts.proveedor = filtroEntidad)
      if (fechaDesde) opts.fecha_desde = fechaDesde
      if (fechaHasta) opts.fecha_hasta = fechaHasta
      if (filtroEstado) opts.estado = filtroEstado
      const res = await fn(empresa.id, opts)
      setDatos(res)
    } catch (e) { setError(e.message) }
    finally { setCargando(false) }
  }, [empresa, tab, q, skip, limit, filtroEntidad, fechaDesde, fechaHasta, filtroEstado])

  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { setSkip(0); setDatos({ total: 0, items: [] }) }, [tab, empresa])
  useEffect(() => { setSkip(0) }, [q, fechaDesde, fechaHasta, filtroEntidad, filtroEstado])

  useEffect(() => {
    if (!empresa) return
    getClientes(empresa.id, { limit: 2000 }).then((r) => setClientes(r.items)).catch(() => {})
    getProveedores(empresa.id, { limit: 2000 }).then((r) => setProv(r.items)).catch(() => {})
  }, [empresa])

  const abrirNuevo = () => {
    setForm(esEmi ? { ...VACIO_EMI } : { ...VACIO_REC })
    setLineas([]); setEditId(null); setModal(true)
  }

  const abrirEditar = async (id) => {
    const fn = esEmi ? getFacturaEmi : getFacturaRec
    const fac = await fn(id)
    setForm(fac); setLineas(fac.lineas || []); setEditId(id); setModal(true)
  }

  const cerrar = () => { setModal(false); setError(null) }

  const enviarFactura = async (payload) => {
    if (editId) {
      esEmi ? await updateFacturaEmi(editId, payload) : await updateFacturaRec(editId, payload)
      cerrar()
    } else {
      const created = esEmi ? await createFacturaEmi(payload) : await createFacturaRec(payload)
      setNuevoId(created.id)
      if (skip !== 0) setSkip(0)  // nueva factura aparece en pág. 1 (orden DESC)
      // Reabrir el formulario en blanco para poder seguir dando de alta facturas seguidas
      setForm(esEmi ? { ...VACIO_EMI } : { ...VACIO_REC })
      setLineas([])
      fechaRef.current?.focus()
    }
    cargar()
  }

  const guardar = async (e) => {
    e.preventDefault(); setError(null)
    const total = lineas.reduce((s, l) => s + (l.importe || 0), 0)
    if (total === 0) {
      if (!confirm('El importe de la factura es 0.\n\n¿Desea continuar guardando?')) return
    }
    setGuardando(true)
    const payload = { ...form, lineas, empresa_id: empresa.id }
    try {
      await enviarFactura(payload)
    } catch (err) {
      if (err.detail?.duplicado) {
        if (confirm(`${err.detail.mensaje}\n\n¿Guardar de todas formas?`)) {
          try { await enviarFactura({ ...payload, forzar: true }) }
          catch (err2) { setError(err2.message) }
        }
      } else {
        setError(err.message)
      }
    }
    finally { setGuardando(false) }
  }

  const eliminar = async (id, numero) => {
    if (!confirm(`¿Eliminar la factura ${numero}?`)) return
    const fn = esEmi ? deleteFacturaEmi : deleteFacturaRec
    try { await fn(id); cargar() } catch (e) { alert(e.message) }
  }

  const renumerar = async (desdeId = null) => {
    const msg = desdeId
      ? '¿Renumerar facturas desde esta en adelante (mismo año)?'
      : `¿Renumerar todas las facturas ${esEmi ? 'emitidas' : 'recibidas'} por orden de fecha?`
    if (!confirm(msg)) return
    try {
      const fn = esEmi ? renumerarFacturasEmi : renumerarFacturasRec
      const res = await fn(empresa.id, desdeId)
      alert(`${res.renumeradas} facturas renumeradas correctamente.`)
      cargar()
    } catch (e) { alert(e.message) }
  }

  useEffect(() => {
    if (!nuevoId || !filaRef.current) return
    filaRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    const t = setTimeout(() => setNuevoId(null), 1800)
    return () => clearTimeout(t)
  }, [nuevoId, datos])

  if (!empresa) return <div className="p-8 text-center text-gray-400">Selecciona una empresa.</div>

  return (
    <div className="h-full overflow-y-auto">
      {/* Cabecera */}
      <div className="bg-gray-50 border-b border-gray-200 px-6 pt-5 pb-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Facturas</h1>
            <p className="text-sm text-gray-500">{empresa.nombre}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => renumerar()} className="btn-secondary text-sm">Renumerar</button>
            <button onClick={abrirNuevo} className="btn-primary">+ Nueva factura</button>
          </div>
        </div>

        <div className="flex gap-1 mb-3 border-b">
          {['emitidas', 'recibidas'].map((t) => (
            <button key={t} onClick={() => { if (t !== tab) { setFiltroEntidad(''); setTab(t) } }}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                tab === t ? 'border-mgd-600 text-mgd-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="label">Referencia</label>
            <input type="search" placeholder="Buscar referencia..."
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
          <div className="w-64">
            <label className="label">{esEmi ? 'Cliente' : 'Proveedor'}</label>
            <AutocompleteEntidad
              items={esEmi ? clientes : proveedores}
              value={filtroEntidad}
              onChange={setFiltroEntidad}
              placeholder={esEmi ? 'Filtrar por cliente…' : 'Filtrar por proveedor…'}
              clearable
            />
          </div>
          <div>
            <label className="label">Estado</label>
            <select className="input w-36" value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)}>
              <option value="">Todos</option>
              <option value="P">Pendientes</option>
              <option value="C">{esEmi ? 'Cobradas' : 'Pagadas'}</option>
              <option value="V">Vencidas</option>
            </select>
          </div>
          {(q || fechaDesde || fechaHasta || filtroEntidad || filtroEstado) && (
            <button
              className="btn-secondary text-sm self-end"
              onClick={() => { setQ(''); setFechaDesde(''); setFechaHasta(''); setFiltroEntidad(''); setFiltroEstado('') }}
            >
              Borrar filtros
            </button>
          )}
        </div>
      </div>

      {/* Contenido con scroll */}
      <div className="p-6">
      <div className="card">
        {cargando && <div className="text-center py-8 text-gray-400 text-sm">Cargando...</div>}
        {error && !cargando && <div className="text-center py-8 text-red-500 text-sm">{error}</div>}
        {!cargando && !error && (
          <>
            <div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b sticky top-0 z-10">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Nº</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Fecha</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      {esEmi ? 'Cliente' : 'Proveedor'}
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Ref.</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">Total</th>
                    <th className="text-center px-4 py-3 font-medium text-gray-600">Estado</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {datos.items.length === 0 && (
                    <tr><td colSpan={7} className="text-center py-10 text-gray-400">Sin facturas</td></tr>
                  )}
                  {datos.items.map((fac) => {
                    const nDoc = fac.cnumero
                      ? `${fac.cnumero}/${(fac.fecha || '').slice(0, 4)}`
                      : fac.numero
                    const nombreEntidad = esEmi
                      ? (clientes.find((c) => c.numero === fac.cliente)?.nombre || fac.cliente)
                      : (proveedores.find((p) => p.numero === fac.proveedor)?.nombre || fac.proveedor)
                    const estadoLabel = fac.estado === 'C'
                      ? (esEmi ? 'Cobrada' : 'Pagada')
                      : fac.estado === 'P' ? 'Pendiente' : (fac.estado || '—')
                    return (
                      <tr
                        key={fac.id}
                        ref={fac.id === nuevoId ? filaRef : null}
                        className={`hover:bg-gray-50 transition-colors ${fac.id === nuevoId ? 'bg-mgd-50 outline outline-1 outline-mgd-300' : ''}`}
                      >
                        <td className="px-4 py-3 font-mono text-xs">{nDoc}</td>
                        <td className="px-4 py-3">{FMT(fac.fecha)}</td>
                        <td className="px-4 py-3 font-medium">{nombreEntidad}</td>
                        <td className="px-4 py-3 text-gray-500 text-xs">
                          {fac.cnumalt || (!esEmi && fac.prfactura) || '—'}
                        </td>
                        <td className="px-4 py-3 text-right font-mono font-semibold">{EUR(fac.total)}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                            fac.estado === 'C' ? 'bg-green-100 text-green-700' :
                            fac.estado === 'P' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-600'
                          }`}>
                            {estadoLabel}
                          </span>
                          {fac.estado === 'P' && badgeVto(fac.fecha_vto, esEmi)}
                          {fac.pago_info && (
                            <div className="text-xs text-gray-400 mt-0.5 truncate max-w-[120px] mx-auto" title={`${fac.pago_info.banco_nombre}${fac.pago_info.fecha ? ' — ' + FMT(fac.pago_info.fecha) : ''}`}>
                              {fac.pago_info.banco_nombre}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2 justify-end">
                            <button onClick={() => abrirEditar(fac.id)} className="text-mgd-600 hover:text-mgd-800 text-xs font-medium">Ver</button>
                            <button onClick={() => eliminar(fac.id, fac.numero)} className="text-red-500 hover:text-red-700 text-xs font-medium">Borrar</button>
                            <button onClick={() => renumerar(fac.id)} className="text-gray-400 hover:text-gray-600 text-xs" title="Renumerar desde aquí">↺</button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}

                </tbody>
              </table>
            </div>
            <Paginacion total={datos.total} skip={skip} limit={limit} onCambiar={setSkip}
              onLimitChange={(n) => { setLimit(n); setSkip(0) }} />
          </>
        )}
      </div>
      </div>

      {modal && (
        <Modal titulo={`${editId ? 'Editar' : 'Nueva'} factura ${esEmi ? 'emitida' : 'recibida'}`}
          onClose={cerrar} ancho="max-w-4xl">
          <form onSubmit={guardar} className="space-y-5">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="label">Fecha *</label>
                <input ref={fechaRef} autoFocus tabIndex={1} type="date" className="input" required value={form.fecha || HOY}
                  onChange={(e) => {
                    const f = e.target.value
                    const updates = { fecha: f }
                    if (!esEmi && (!form.prfecha || form.prfecha === form.fecha)) {
                      updates.prfecha = f
                    }
                    setForm({ ...form, ...updates })
                  }} />
              </div>
              {esEmi ? (
                <div className="col-span-2">
                  <label className="label">Cliente *</label>
                  <AutocompleteEntidad
                    tabIndex={2}
                    items={clientes}
                    value={form.cliente || ''}
                    onChange={(num) => setForm({ ...form, cliente: num })}
                    placeholder="Buscar cliente por nombre o CIF…"
                  />
                </div>
              ) : (
                <>
                  <div className="col-span-2">
                    <label className="label">Proveedor *</label>
                    <AutocompleteEntidad
                      tabIndex={2}
                      items={proveedores}
                      value={form.proveedor || ''}
                      onChange={(num) => {
                        const prov = proveedores.find((p) => p.numero === num)
                        setForm({ ...form, proveedor: num, prcuenta: prov?.cuenta || form.prcuenta || '' })
                      }}
                      placeholder="Buscar proveedor por nombre o CIF…"
                    />
                  </div>
                  <div>
                    <label className="label">Nº factura proveedor</label>
                    <input tabIndex={3} className="input" value={form.prfactura || ''}
                      onChange={(e) => setForm({ ...form, prfactura: e.target.value })} />
                  </div>
                  <div>
                    <label className="label">Fecha factura prov.</label>
                    <input tabIndex={4} type="date" className="input" value={form.prfecha || ''}
                      onChange={(e) => setForm({ ...form, prfecha: e.target.value })} />
                  </div>
                </>
              )}
              <div className="col-span-3">
                <label className="label">Notas</label>
                <input tabIndex={5} className="input" value={form.notas || ''}
                  onChange={(e) => setForm({ ...form, notas: e.target.value })} />
              </div>
              <div>
                <label className="label">Estado</label>
                <select tabIndex={7} className="input" value={form.estado || 'P'}
                  onChange={(e) => setForm({ ...form, estado: e.target.value })}>
                  <option value="P">Pendiente</option>
                  <option value="C">Cobrada / Pagada</option>
                </select>
              </div>
              {editId && form.pago_info && (
                <div className="col-span-2 flex items-center gap-2 text-sm bg-green-50 border border-green-200 rounded px-3 py-2 text-green-700">
                  <span>{esEmi ? 'Cobrada' : 'Pagada'} en <strong>{form.pago_info.banco_nombre}</strong></span>
                  {form.pago_info.fecha && <span>— {FMT(form.pago_info.fecha)}</span>}
                  <span>— {EUR(form.pago_info.importe)}</span>
                </div>
              )}
            </div>

            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Líneas</h3>
              <LineasDocumento lineas={lineas} onChange={setLineas} tabIndexAnadir={6} />
            </div>

            {error && <p className="text-red-500 text-sm">{error}</p>}
            <div className="flex justify-end gap-3 pt-2 border-t">
              <button type="button" onClick={cerrar} className="btn-secondary">Cancelar</button>
              <button type="submit" disabled={guardando} className="btn-primary">
                {guardando ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
