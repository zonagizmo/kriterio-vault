import { useEmpresa } from '../hooks/useEmpresa.jsx'
import Modal from './Modal'
import Paginacion from './Paginacion'
import useCrud from '../hooks/useCrud'

const DEFAULT_COLUMNS = [
  { key: 'numero', header: 'Nº', className: 'text-gray-500' },
  {
    key: 'nombre',
    header: 'Nombre',
    className: 'font-medium text-gray-900',
    render: (item) => (
      <>
        {item.nombre}
        {item.comercial && <span className="block text-xs text-gray-400 font-normal">{item.comercial}</span>}
      </>
    ),
  },
  { key: 'nif', header: 'NIF', className: 'text-gray-600 font-mono text-xs', render: (item) => item.nif || '—' },
  { key: 'localidad', header: 'Localidad', className: 'text-gray-600', render: (item) => item.localidad || '—' },
  {
    key: 'cuenta',
    header: 'Cuenta',
    className: 'text-gray-600 font-mono text-xs',
    render: (item) => item.cuenta || '—',
  },
  {
    key: 'pendiente',
    header: 'Pendiente',
    align: 'right',
    className: 'font-mono',
    render: (item) => {
      const EUR = (v) => Number(v ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
      return item.pendiente > 0 ? (
        <span className="text-red-600 font-semibold">{EUR(item.pendiente)}</span>
      ) : (
        <span className="text-gray-400">—</span>
      )
    },
  },
]

/**
 * Página CRUD genérica con tabla, búsqueda, paginación y modal de edición.
 *
 * @param {Object} opts
 * @param {string} opts.titulo — "Clientes", "Proveedores", etc.
 * @param {string} opts.entityName — "el cliente", "el proveedor"
 * @param {string} opts.searchPlaceholder
 * @param {Object} opts.service — { getAll, create, update, delete }
 * @param {Object} opts.emptyForm — plantilla del formulario vacío
 * @param {ReactNode} opts.FormBody — contenido del modal (recibe { datos, onChange, error })
 * @param {Function} opts.renderActions — (item, { abrirEditar, eliminar }) → JSX
 * @param {Function} opts.renderEmpty — mensaje cuando no hay items
 * @param {Array} opts.columns — definiciones de columna [{ key, header, render, className, align }]
 * @param {Array} opts.items — datos externos (si se proveen, no usa useCrud internamente)
 * @param {string} opts nuevoLabel — texto del botón nuevo (default: "+ Nuevo X")
 */
export default function CrudPage({
  titulo,
  entityName,
  searchPlaceholder = 'Buscar...',
  service,
  emptyForm,
  FormBody,
  renderActions,
  renderEmpty,
  columns = DEFAULT_COLUMNS,
  items,
  nuevoLabel,
}) {
  const { empresa } = useEmpresa()

  const crud = useCrud({
    service,
    empresaId: empresa?.id,
    emptyForm,
    entityName,
  })

  const datos = items !== undefined ? { total: items.length, items } : crud.datos

  const q = crud.q
  const setQ = crud.setQ
  const skip = crud.skip
  const setSkip = crud.setSkip
  const limit = crud.limit
  const setLimit = crud.setLimit
  const cargando = crud.cargando
  const error = crud.error
  const modal = items !== undefined ? null : crud.modal
  const form = crud.form
  const setForm = crud.setForm
  const editId = crud.editId
  const guardando = crud.guardando
  const _cargar = crud.cargar
  const abrirNuevo = crud.abrirNuevo
  const abrirEditar = crud.abrirEditar
  const cerrar = crud.cerrar
  const guardar = crud.guardar
  const eliminar = crud.eliminar

  if (!empresa) {
    return <div className="p-8 text-center text-gray-400">Selecciona una empresa para ver {titulo.toLowerCase()}.</div>
  }

  const colSpan = columns.length + 1 // +1 for actions column

  return (
    <div className="h-full overflow-y-auto">
      <div className="bg-gray-50 border-b border-gray-200 px-6 pt-5 pb-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{titulo}</h1>
            <p className="text-sm text-gray-500">{empresa.nombre}</p>
          </div>
          {abrirNuevo && (
            <button onClick={abrirNuevo} className="btn-primary">
              {nuevoLabel || `+ Nuevo ${titulo.toLowerCase().slice(0, -1)}`}
            </button>
          )}
        </div>
        {setQ && (
          <input
            type="search"
            placeholder={searchPlaceholder}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="input max-w-sm"
          />
        )}
      </div>

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
                      {columns.map((col) => (
                        <th
                          key={col.key}
                          className={`px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider ${
                            col.align === 'right' ? 'text-right' : 'text-left'
                          }`}
                        >
                          {col.header}
                        </th>
                      ))}
                      <th className="px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {datos.items.length === 0 && (
                      <tr>
                        <td colSpan={colSpan} className="text-center py-10 text-gray-400">
                          {renderEmpty ? renderEmpty() : `No se encontraron ${titulo.toLowerCase()}`}
                        </td>
                      </tr>
                    )}
                    {datos.items.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                        {columns.map((col) => (
                          <td
                            key={col.key}
                            className={`px-4 py-3 ${col.align === 'right' ? 'text-right' : ''} ${col.className || ''}`}
                          >
                            {col.render ? col.render(item) : (item[col.key] ?? '—')}
                          </td>
                        ))}
                        <td className="px-4 py-3">
                          <div className="flex gap-2 justify-end">
                            {renderActions && renderActions(item, { abrirEditar, eliminar })}
                            {abrirEditar && (
                              <button
                                onClick={() => abrirEditar(item)}
                                className="text-mgd-600 hover:text-mgd-800 text-xs font-medium"
                              >
                                Editar
                              </button>
                            )}
                            {eliminar && (
                              <button
                                onClick={() => eliminar(item.id, item.nombre)}
                                className="text-red-500 hover:text-red-700 text-xs font-medium"
                              >
                                Borrar
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {setSkip && (
                <Paginacion
                  total={datos.total}
                  skip={skip}
                  limit={limit}
                  onCambiar={setSkip}
                  onLimitChange={(n) => {
                    setLimit(n)
                    setSkip(0)
                  }}
                />
              )}
            </>
          )}
        </div>
      </div>

      {modal === 'editar' && FormBody && (
        <Modal titulo={editId ? `Editar ${entityName}` : `Nuevo ${entityName}`} onClose={cerrar}>
          <form onSubmit={guardar} className="space-y-4">
            <FormBody datos={form} onChange={setForm} error={error} />
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
