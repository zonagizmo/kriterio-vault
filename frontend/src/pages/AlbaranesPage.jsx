import { useEffect, useState, useCallback } from 'react'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import {
  getAlbaranesEmi, createAlbaranEmi, updateAlbaranEmi, deleteAlbaranEmi,
  getAlbaranEmi,
  getAlbaranesRec, createAlbaranRec, updateAlbaranRec, deleteAlbaranRec,
  getAlbaranRec,
} from '../services/albaranes'
import { getClientes } from '../services/clientes'
import { getProveedores } from '../services/proveedores'
import Modal from '../components/Modal'
import Paginacion from '../components/Paginacion'
import LineasDocumento from '../components/LineasDocumento'

const EUR =(v) => Number(v || 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
const FMT = (d) => d ? new Date(d).toLocaleDateString('es-ES') : '—'

const HOY = new Date().toISOString().slice(0, 10)
const VACIO_EMI = { fecha: HOY, cliente: '', cnumalt: '', notas: '', estado: 'P' }
const VACIO_REC = { fecha: HOY, proveedor: '', pralbaran: '', prfecha: '', notas: '', estado: 'P' }

function TablaDocumentos({ items, total, skip, limit, onSkip, onLimitChange, onEditar, onEliminar, esEmitido }) {
  return (
    <div className="card">
      <div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b sticky top-0 z-10">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Nº</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Fecha</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">
                {esEmitido ? 'Cliente' : 'Proveedor'}
              </th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Ref.</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Importe</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Estado</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.length === 0 && (
              <tr><td colSpan={7} className="text-center py-10 text-gray-400">Sin albaranes</td></tr>
            )}
            {items.map((alb) => (
              <tr key={alb.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">
                  {alb.cnumero ? `${alb.cnumero}/${alb.tiponum}` : alb.numero}
                </td>
                <td className="px-4 py-3">{FMT(alb.fecha)}</td>
                <td className="px-4 py-3 font-medium">{esEmitido ? alb.cliente : alb.proveedor}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {alb.cnumalt || (esEmitido ? '' : alb.pralbaran) || '—'}
                </td>
                <td className="px-4 py-3 text-right font-mono font-medium">{EUR(alb.importe)}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                    alb.estado === 'F' ? 'bg-green-100 text-green-700' :
                    alb.estado === 'P' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {alb.estado === 'F' ? 'Facturado' : alb.estado === 'P' ? 'Pendiente' : alb.estado}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2 justify-end">
                    <button onClick={() => onEditar(alb.id)} className="text-mgd-600 hover:text-mgd-800 text-xs font-medium">Ver</button>
                    <button onClick={() => onEliminar(alb.id, alb.numero)} className="text-red-500 hover:text-red-700 text-xs font-medium">Borrar</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Paginacion total={total} skip={skip} limit={limit} onCambiar={onSkip}
        onLimitChange={onLimitChange} />
    </div>
  )
}

export default function AlbaranesPage() {
  const { empresa } = useEmpresa()
  const [tab, setTab]         = useState('emitidos')
  const esEmi = tab === 'emitidos'

  const [datos, setDatos]         = useState({ total: 0, items: [] })
  const [clientes, setClientes]   = useState([])
  const [proveedores, setProv]    = useState([])
  const [q, setQ]                 = useState('')
  const [skip, setSkip]           = useState(0)
  const [limit, setLimit]         = useState(50)
  const [cargando, setCargando]   = useState(false)
  const [error, setError]         = useState(null)
  const [modal, setModal]         = useState(false)
  const [form, setForm]           = useState(VACIO_EMI)
  const [lineas, setLineas]       = useState([])
  const [editId, setEditId]       = useState(null)
  const [guardando, setGuardando] = useState(false)

  const cargar = useCallback(async () => {
    if (!empresa) return
    setCargando(true); setError(null)
    try {
      const fn = esEmi ? getAlbaranesEmi : getAlbaranesRec
      const res = await fn(empresa.id, { q, skip, limit })
      setDatos(res)
    } catch (e) { setError(e.message) }
    finally { setCargando(false) }
  }, [empresa, tab, q, skip, limit])

  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { setSkip(0); setDatos({ total: 0, items: [] }) }, [tab, q, empresa])

  useEffect(() => {
    if (!empresa) return
    getClientes(empresa.id, { limit: 500 }).then((r) => setClientes(r.items)).catch(() => {})
    getProveedores(empresa.id, { limit: 500 }).then((r) => setProv(r.items)).catch(() => {})
  }, [empresa])

  const abrirNuevo = () => {
    setForm(esEmi ? { ...VACIO_EMI } : { ...VACIO_REC })
    setLineas([]); setEditId(null); setModal(true)
  }

  const abrirEditar = async (id) => {
    const fn = esEmi ? getAlbaranEmi : getAlbaranRec
    const alb = await fn(id)
    setForm(alb); setLineas(alb.lineas || []); setEditId(id); setModal(true)
  }

  const cerrar = () => { setModal(false); setError(null) }

  const guardar = async (e) => {
    e.preventDefault(); setGuardando(true); setError(null)
    try {
      const payload = { ...form, lineas, empresa_id: empresa.id }
      if (editId) {
        esEmi ? await updateAlbaranEmi(editId, payload) : await updateAlbaranRec(editId, payload)
      } else {
        esEmi ? await createAlbaranEmi(payload) : await createAlbaranRec(payload)
      }
      cerrar(); cargar()
    } catch (err) { setError(err.message) }
    finally { setGuardando(false) }
  }

  const eliminar = async (id, numero) => {
    if (!confirm(`¿Eliminar el albarán ${numero}?`)) return
    const fn = esEmi ? deleteAlbaranEmi : deleteAlbaranRec
    try { await fn(id); cargar() } catch (e) { alert(e.message) }
  }

  if (!empresa) return <div className="p-8 text-center text-gray-400">Selecciona una empresa.</div>

  return (
    <div className="h-full overflow-y-auto">
      {/* Cabecera */}
      <div className="bg-gray-50 border-b border-gray-200 px-6 pt-5 pb-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Albaranes</h1>
            <p className="text-sm text-gray-500">{empresa.nombre}</p>
          </div>
          <button onClick={abrirNuevo} className="btn-primary">+ Nuevo albarán</button>
        </div>

        <div className="flex gap-1 mb-3 border-b">
          {['emitidos', 'recibidos'].map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                tab === t ? 'border-mgd-600 text-mgd-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        <input type="search" placeholder="Buscar referencia..."
          value={q} onChange={(e) => setQ(e.target.value)} className="input max-w-xs" />
      </div>

      {/* Contenido */}
      <div className="p-6">
        {cargando && <div className="text-center py-8 text-gray-400 text-sm">Cargando...</div>}
        {error && !cargando && <div className="text-center py-8 text-red-500 text-sm">{error}</div>}
        {!cargando && !error && (
          <TablaDocumentos items={datos.items} total={datos.total} skip={skip} limit={limit}
            onSkip={setSkip} onLimitChange={(n) => { setLimit(n); setSkip(0) }}
            onEditar={abrirEditar} onEliminar={eliminar} esEmitido={esEmi} />
        )}
      </div>

      {modal && (
        <Modal titulo={`${editId ? 'Editar' : 'Nuevo'} albarán ${esEmi ? 'emitido' : 'recibido'}`}
          onClose={cerrar} ancho="max-w-4xl">
          <form onSubmit={guardar} className="space-y-5">
            {/* Cabecera */}
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="label">Fecha *</label>
                <input type="date" className="input" required
                  value={form.fecha || HOY}
                  onChange={(e) => setForm({ ...form, fecha: e.target.value })} />
              </div>
              {esEmi ? (
                <div className="col-span-2">
                  <label className="label">Cliente *</label>
                  <select className="input" required
                    value={form.cliente || ''}
                    onChange={(e) => setForm({ ...form, cliente: parseInt(e.target.value) || '' })}>
                    <option value="">— Seleccionar —</option>
                    {clientes.map((c) => (
                      <option key={c.id} value={c.numero}>{c.numero} — {c.nombre}</option>
                    ))}
                  </select>
                </div>
              ) : (
                <>
                  <div className="col-span-2">
                    <label className="label">Proveedor *</label>
                    <select className="input" required
                      value={form.proveedor || ''}
                      onChange={(e) => setForm({ ...form, proveedor: parseInt(e.target.value) || '' })}>
                      <option value="">— Seleccionar —</option>
                      {proveedores.map((p) => (
                        <option key={p.id} value={p.numero}>{p.numero} — {p.nombre}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="label">Albarán proveedor</label>
                    <input className="input" value={form.pralbaran || ''}
                      onChange={(e) => setForm({ ...form, pralbaran: e.target.value })} />
                  </div>
                  <div>
                    <label className="label">Fecha albarán prov.</label>
                    <input type="date" className="input" value={form.prfecha || ''}
                      onChange={(e) => setForm({ ...form, prfecha: e.target.value })} />
                  </div>
                </>
              )}
              <div>
                <label className="label">Referencia</label>
                <input className="input" value={form.cnumalt || ''}
                  onChange={(e) => setForm({ ...form, cnumalt: e.target.value })} />
              </div>
              <div>
                <label className="label">Estado</label>
                <select className="input" value={form.estado || 'P'}
                  onChange={(e) => setForm({ ...form, estado: e.target.value })}>
                  <option value="P">Pendiente</option>
                  <option value="F">Facturado</option>
                </select>
              </div>
              <div className="col-span-3">
                <label className="label">Notas</label>
                <input className="input" value={form.notas || ''}
                  onChange={(e) => setForm({ ...form, notas: e.target.value })} />
              </div>
            </div>

            {/* Líneas */}
            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Líneas
              </h3>
              <LineasDocumento lineas={lineas} onChange={setLineas} />
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
