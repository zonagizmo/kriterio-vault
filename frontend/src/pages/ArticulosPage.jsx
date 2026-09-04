import { useEffect, useState, useCallback } from 'react'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import { getArticulos, createArticulo, updateArticulo, deleteArticulo } from '../services/articulos'
import { getFamilias } from '../services/familias'
import Modal from '../components/Modal'
import Paginacion from '../components/Paginacion'

const EUR = (v) => Number(v || 0).toLocaleString('es-ES', { minimumFractionDigits: 2 })
const VACIO = { nombre: '', codigo: '', ean13: '', familia: null, pventa: 0,
                pcompra: 0, dcto: 0, minimo: 0, ubicacion: '', notas: '' }

export default function ArticulosPage() {
  const { empresa } = useEmpresa()
  const [datos, setDatos]         = useState({ total: 0, items: [] })
  const [familias, setFamilias]   = useState([])
  const [q, setQ]                 = useState('')
  const [filtroFam, setFiltroFam] = useState('')
  const [skip, setSkip]           = useState(0)
  const [limit, setLimit]         = useState(50)
  const [cargando, setCargando]   = useState(false)
  const [error, setError]         = useState(null)
  const [modal, setModal]         = useState(null)
  const [form, setForm]           = useState(VACIO)
  const [editId, setEditId]       = useState(null)
  const [guardando, setGuardando] = useState(false)

  const cargar = useCallback(async () => {
    if (!empresa) return
    setCargando(true); setError(null)
    try {
      const res = await getArticulos(empresa.id, {
        q, familia: filtroFam || null, skip, limit,
      })
      setDatos(res)
    } catch (e) { setError(e.message) }
    finally { setCargando(false) }
  }, [empresa, q, filtroFam, skip, limit])

  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { setSkip(0) }, [q, filtroFam, empresa])

  useEffect(() => {
    if (!empresa) return
    getFamilias(empresa.id).then(setFamilias).catch(() => {})
  }, [empresa])

  const abrirNuevo  = () => { setForm(VACIO); setEditId(null); setModal('editar') }
  const abrirEditar = (a) => { setForm({ ...VACIO, ...a }); setEditId(a.id); setModal('editar') }
  const cerrar      = () => { setModal(null); setError(null) }

  const guardar = async (e) => {
    e.preventDefault(); setGuardando(true); setError(null)
    try {
      if (editId) await updateArticulo(editId, form)
      else await createArticulo({ ...form, empresa_id: empresa.id })
      cerrar(); cargar()
    } catch (err) { setError(err.message) }
    finally { setGuardando(false) }
  }

  const eliminar = async (id, nombre) => {
    if (!confirm(`¿Eliminar "${nombre}"?`)) return
    try { await deleteArticulo(id); cargar() }
    catch (e) { alert(e.message) }
  }

  const campo = (name, type = 'text') => ({
    id: name, name, type,
    value: form[name] ?? '',
    onChange: (e) => setForm({ ...form, [name]: type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value }),
    className: 'input',
  })

  if (!empresa) return <div className="p-8 text-center text-gray-400">Selecciona una empresa.</div>

  return (
    <div className="h-full overflow-y-auto">
      {/* Cabecera */}
      <div className="bg-gray-50 border-b border-gray-200 px-6 pt-5 pb-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Artículos</h1>
            <p className="text-sm text-gray-500">{empresa.nombre}</p>
          </div>
          <button onClick={abrirNuevo} className="btn-primary">+ Nuevo artículo</button>
        </div>
        <div className="flex gap-3">
          <input type="search" placeholder="Buscar por nombre, código, EAN..."
            value={q} onChange={(e) => setQ(e.target.value)} className="input max-w-xs" />
          <select value={filtroFam} onChange={(e) => setFiltroFam(e.target.value)} className="input w-48">
            <option value="">Todas las familias</option>
            {familias.map((f) => <option key={f.id} value={f.numero}>{f.texto}</option>)}
          </select>
        </div>
      </div>

      {/* Contenido */}
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
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Código</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Nombre</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">P. Venta</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">P. Compra</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">Stock</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {datos.items.length === 0 && (
                    <tr><td colSpan={7} className="text-center py-10 text-gray-400">Sin artículos</td></tr>
                  )}
                  {datos.items.map((a) => (
                    <tr key={a.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-500">{a.numero}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-600">{a.codigo || '—'}</td>
                      <td className="px-4 py-3 font-medium text-gray-900">{a.nombre}</td>
                      <td className="px-4 py-3 text-right font-mono">{EUR(a.pventa)} €</td>
                      <td className="px-4 py-3 text-right font-mono text-gray-500">{EUR(a.pcompra)} €</td>
                      <td className="px-4 py-3 text-right">
                        {a.qinvent > 0
                          ? <span className="text-green-600 font-medium">{Number(a.qinvent).toFixed(2)}</span>
                          : <span className="text-gray-400">{Number(a.qinvent || 0).toFixed(2)}</span>
                        }
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2 justify-end">
                          <button onClick={() => abrirEditar(a)} className="text-mgd-600 hover:text-mgd-800 text-xs font-medium">Editar</button>
                          <button onClick={() => eliminar(a.id, a.nombre)} className="text-red-500 hover:text-red-700 text-xs font-medium">Borrar</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Paginacion total={datos.total} skip={skip} limit={limit} onCambiar={setSkip}
              onLimitChange={(n) => { setLimit(n); setSkip(0) }} />
          </>
        )}
      </div>
      </div>

      {modal === 'editar' && (
        <Modal titulo={editId ? 'Editar artículo' : 'Nuevo artículo'} onClose={cerrar}>
          <form onSubmit={guardar} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="label">Nombre *</label>
                <input {...campo('nombre')} required />
              </div>
              <div>
                <label className="label">Código</label>
                <input {...campo('codigo')} />
              </div>
              <div>
                <label className="label">EAN-13</label>
                <input {...campo('ean13')} />
              </div>
              <div>
                <label className="label">Familia</label>
                <select
                  className="input"
                  value={form.familia ?? ''}
                  onChange={(e) => setForm({ ...form, familia: e.target.value ? parseInt(e.target.value) : null })}
                >
                  <option value="">Sin familia</option>
                  {familias.map((f) => <option key={f.id} value={f.numero}>{f.texto}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Ubicación</label>
                <input {...campo('ubicacion')} />
              </div>
              <div>
                <label className="label">Precio de venta (€)</label>
                <input {...campo('pventa', 'number')} step="0.01" min="0" />
              </div>
              <div>
                <label className="label">Precio de compra (€)</label>
                <input {...campo('pcompra', 'number')} step="0.01" min="0" />
              </div>
              <div>
                <label className="label">Descuento (%)</label>
                <input {...campo('dcto', 'number')} step="0.01" min="0" max="100" />
              </div>
              <div>
                <label className="label">Stock mínimo</label>
                <input {...campo('minimo', 'number')} step="0.001" min="0" />
              </div>
              <div className="col-span-2">
                <label className="label">Notas</label>
                <textarea className="input resize-none" rows={2}
                  value={form.notas ?? ''}
                  onChange={(e) => setForm({ ...form, notas: e.target.value })} />
              </div>
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
