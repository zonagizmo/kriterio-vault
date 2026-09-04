import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import { getClientes, createCliente, updateCliente, deleteCliente } from '../services/clientes'
import Modal from '../components/Modal'
import Paginacion from '../components/Paginacion'
import FormContacto from '../components/FormContacto'

const VACIO ={ nombre: '', comercial: '', nif: '', cuenta: '', domicilio: '',
                localidad: '', provincia: '', cod_postal: '', banco_nom: '',
                banco_suc: '', banco_dig: '', banco_tit: '', telefono: '', email: '', notas: '' }

export default function ClientesPage() {
  const { empresa } = useEmpresa()
  const navigate = useNavigate()
  const [datos, setDatos]       = useState({ total: 0, items: [] })
  const [q, setQ]               = useState('')
  const [skip, setSkip]         = useState(0)
  const [limit, setLimit]       = useState(50)
  const [cargando, setCargando] = useState(false)
  const [error, setError]       = useState(null)
  const [modal, setModal]       = useState(null) // null | 'nuevo' | 'editar'
  const [form, setForm]         = useState(VACIO)
  const [editId, setEditId]     = useState(null)
  const [guardando, setGuardando] = useState(false)

  const cargar = useCallback(async () => {
    if (!empresa) return
    setCargando(true)
    setError(null)
    try {
      const res = await getClientes(empresa.id, { q, skip, limit })
      setDatos(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }, [empresa, q, skip, limit])

  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { setSkip(0) }, [q, empresa])

  const abrirNuevo = () => { setForm(VACIO); setEditId(null); setModal('editar') }
  const abrirEditar = (c) => {
    setForm({ ...VACIO, ...c })
    setEditId(c.id)
    setModal('editar')
  }
  const cerrar = () => { setModal(null); setError(null) }

  const guardar = async (e) => {
    e.preventDefault()
    setGuardando(true)
    setError(null)
    try {
      if (editId) {
        await updateCliente(editId, form)
      } else {
        await createCliente({ ...form, empresa_id: empresa.id })
      }
      cerrar()
      cargar()
    } catch (err) {
      setError(err.message)
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async (id, nombre) => {
    if (!confirm(`¿Eliminar el cliente "${nombre}"?`)) return
    try {
      await deleteCliente(id)
      cargar()
    } catch (e) {
      alert(e.message)
    }
  }

  if (!empresa) {
    return (
      <div className="p-8 text-center text-gray-400">
        Selecciona una empresa para ver los clientes.
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto">
      {/* Cabecera */}
      <div className="bg-gray-50 border-b border-gray-200 px-6 pt-5 pb-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
            <p className="text-sm text-gray-500">{empresa.nombre}</p>
          </div>
          <button onClick={abrirNuevo} className="btn-primary">
            + Nuevo cliente
          </button>
        </div>
        <input
          type="search"
          placeholder="Buscar por nombre, NIF, localidad..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="input max-w-sm"
        />
      </div>

      {/* Contenido */}
      <div className="p-6">
      <div className="card">
        {cargando && (
          <div className="text-center py-8 text-gray-400 text-sm">Cargando...</div>
        )}
        {error && !cargando && (
          <div className="text-center py-8 text-red-500 text-sm">{error}</div>
        )}
        {!cargando && !error && (
          <>
            <div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b sticky top-0 z-10">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Nº</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Nombre</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">NIF</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Localidad</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Cuenta</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">Pendiente</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {datos.items.length === 0 && (
                    <tr>
                      <td colSpan={7} className="text-center py-10 text-gray-400">
                        No se encontraron clientes
                      </td>
                    </tr>
                  )}
                  {datos.items.map((c) => (
                    <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-gray-500">{c.numero}</td>
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {c.nombre}
                        {c.comercial && (
                          <span className="block text-xs text-gray-400 font-normal">{c.comercial}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-600 font-mono text-xs">{c.nif || '—'}</td>
                      <td className="px-4 py-3 text-gray-600">{c.localidad || '—'}</td>
                      <td className="px-4 py-3 text-gray-600 font-mono text-xs">{c.cuenta || '—'}</td>
                      <td className="px-4 py-3 text-right font-mono">
                        {c.pendiente > 0 ? (
                          <span className="text-red-600 font-semibold">
                            {Number(c.pendiente).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2 justify-end">
                          <button
                            onClick={() => navigate(`/facturas?tab=emitidas&cliente=${c.numero}`)}
                            className="text-blue-500 hover:text-blue-700 text-xs font-medium"
                          >
                            Facturas
                          </button>
                          {c.cuenta ? (
                            <button
                              onClick={() => navigate(`/contabilidad?tab=mayor&cuenta=${c.cuenta}`)}
                              className="text-purple-500 hover:text-purple-700 text-xs font-medium"
                            >
                              Mayor
                            </button>
                          ) : (
                            <span className="text-gray-300 text-xs cursor-default" title="Sin cuenta asignada">Mayor</span>
                          )}
                          <button
                            onClick={() => abrirEditar(c)}
                            className="text-mgd-600 hover:text-mgd-800 text-xs font-medium"
                          >
                            Editar
                          </button>
                          <button
                            onClick={() => eliminar(c.id, c.nombre)}
                            className="text-red-500 hover:text-red-700 text-xs font-medium"
                          >
                            Borrar
                          </button>
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

      {/* Modal edición */}
      {modal === 'editar' && (
        <Modal
          titulo={editId ? 'Editar cliente' : 'Nuevo cliente'}
          onClose={cerrar}
        >
          <form onSubmit={guardar} className="space-y-4">
            <FormContacto datos={form} onChange={setForm} tipo="cliente" />
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <div className="flex justify-end gap-3 pt-2 border-t">
              <button type="button" onClick={cerrar} className="btn-secondary">
                Cancelar
              </button>
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
