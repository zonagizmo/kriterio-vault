import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import { useAuth } from '../hooks/useAuth.jsx'
import { usePermissions } from '../hooks/usePermissions'
import { createEmpresa, deleteEmpresa } from '../services/empresas.js'
import BotonApagar from '../components/BotonApagar'
import ConfirmModal from '../components/ConfirmModal'

export default function EmpresasSelectorPage() {
  const { empresas, setEmpresa, addEmpresa, removeEmpresa } = useEmpresa()
  const { user, logout } = useAuth()
  const { has } = usePermissions()
  const navigate = useNavigate()
  // D-03: el alta de empresas es solo de admin global (el backend devuelve 403)
  const puedeCrearEmpresa = has('configuration') && !user?.empresa_id

  const [showForm, setShowForm] = useState(false)
  const [codigo, setCodigo] = useState('')
  const [nombre, setNombre] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [eliminando, setEliminando] = useState(null)
  const [confirmState, setConfirmState] = useState({ open: false, msg: '', action: null })

  function seleccionar(emp) {
    setEmpresa(emp)
    navigate('/inicio')
  }

  async function handleCreate(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const newEmp = await createEmpresa({ codigo, nombre })
      addEmpresa(newEmp)
      setEmpresa(newEmp)
      navigate('/inicio')
    } catch (err) {
      setError(err.message || 'Error al crear empresa')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(emp) {
    setConfirmState({
      open: true,
      msg: `¿Eliminar la empresa "${emp.nombre}"?\n\nSolo se puede eliminar si no tiene datos.`,
      action: async () => {
        setEliminando(emp.id)
        try {
          await deleteEmpresa(emp.id)
          removeEmpresa(emp.id)
        } catch (err) {
          alert(err.message || 'Error al eliminar')
        } finally {
          setEliminando(null)
        }
      },
    })
  }

  return (
    <div className="min-h-screen bg-mgd-900 flex flex-col items-center justify-center p-8">
      <div className="mb-10 text-center">
        <h1 className="text-3xl font-bold text-white tracking-tight">Kriterio Vault</h1>
        <p className="text-mgd-100 opacity-60 mt-1 text-sm">Selecciona una empresa para continuar</p>
        {user && (
          <div className="mt-4 flex items-center justify-center gap-4">
            <span className="text-xs text-mgd-100 opacity-50">{user.nombre}</span>
            <button
              onClick={logout}
              className="text-xs text-mgd-100 opacity-50 hover:opacity-100 hover:text-red-400 transition-opacity"
            >
              Salir
            </button>
          </div>
        )}
      </div>

      {empresas.length === 0 && !showForm ? (
        <div className="text-center">
          <p className="text-mgd-100 opacity-40 text-sm mb-4">No hay empresas configuradas</p>
          {puedeCrearEmpresa && (
            <button
              onClick={() => setShowForm(true)}
              className="px-4 py-2 bg-mgd-600 hover:bg-mgd-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Crear primera empresa
            </button>
          )}
        </div>
      ) : showForm ? (
        <form
          onSubmit={handleCreate}
          className="bg-mgd-900 border border-mgd-700 rounded-xl p-6 w-full max-w-sm space-y-4"
        >
          <h2 className="text-white font-semibold text-sm">Nueva empresa</h2>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-2 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-mgd-100 mb-1">Código</label>
            <input
              type="text"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value)}
              required
              autoFocus
              placeholder="Ej: 001"
              className="w-full px-3 py-2 bg-mgd-800 border border-mgd-600 rounded-lg text-white text-sm focus:outline-none focus:border-mgd-400"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-mgd-100 mb-1">Nombre</label>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              required
              placeholder="Nombre de la empresa"
              className="w-full px-3 py-2 bg-mgd-800 border border-mgd-600 rounded-lg text-white text-sm focus:outline-none focus:border-mgd-400"
            />
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="flex-1 py-2 bg-mgd-800 hover:bg-mgd-700 text-mgd-100 text-sm rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2 bg-mgd-600 hover:bg-mgd-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {loading ? 'Creando...' : 'Crear'}
            </button>
          </div>
        </form>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full max-w-3xl">
          {empresas.map((emp) => (
            <div
              key={emp.id}
              className="bg-mgd-900 border border-mgd-700 hover:border-mgd-500 rounded-xl p-6 transition-all group relative"
            >
              <button onClick={() => seleccionar(emp)} className="text-left w-full">
                <div className="text-xs font-mono text-mgd-100 opacity-50 mb-1 uppercase tracking-widest">
                  {emp.codigo}
                </div>
                <div className="text-white font-semibold text-base group-hover:text-mgd-100 leading-snug">
                  {emp.nombre}
                </div>
              </button>

              {has('configuration') && (
                <button
                  onClick={() => handleDelete(emp)}
                  disabled={eliminando === emp.id}
                  className="absolute top-3 right-3 text-xs text-mgd-100 opacity-0 group-hover:opacity-40 hover:!opacity-100 hover:text-red-400 transition-opacity disabled:opacity-50"
                  title="Eliminar empresa"
                >
                  {eliminando === emp.id ? '...' : '×'}
                </button>
              )}
            </div>
          ))}

          {puedeCrearEmpresa && (
            <button
              onClick={() => setShowForm(true)}
              className="border border-dashed border-mgd-700 hover:border-mgd-500 rounded-xl p-6 text-center transition-all group"
            >
              <div className="text-mgd-100 opacity-40 group-hover:opacity-70 text-sm">+ Nueva empresa</div>
            </button>
          )}
        </div>
      )}

      <BotonApagar variant="selector" />

      <ConfirmModal
        open={confirmState.open}
        title="Eliminar empresa"
        message={confirmState.msg}
        confirmText="Eliminar"
        variant="danger"
        onConfirm={async () => {
          await confirmState.action()
          setConfirmState({ open: false, msg: '', action: null })
        }}
        onCancel={() => setConfirmState({ open: false, msg: '', action: null })}
      />
    </div>
  )
}
