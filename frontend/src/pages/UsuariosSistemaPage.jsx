import { useEffect, useState } from 'react'
import {
  getUsuariosSistema,
  createUsuarioSistema,
  updateUsuarioSistema,
  resetPasswordUsuario,
  deleteUsuarioSistema,
} from '../services/auth'
import { useAuth } from '../hooks/useAuth'
import Modal from '../components/Modal'
import ConfirmModal from '../components/ConfirmModal'

const ROLES = [
  { value: 'admin', label: 'Administrador' },
  { value: 'operador', label: 'Operador' },
  { value: 'solo_lectura', label: 'Solo lectura' },
]

export default function UsuariosSistemaPage() {
  const { user } = useAuth()
  const [usuarios, setUsuarios] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editando, setEditando] = useState(null)
  const [msg, setMsg] = useState(null)
  const [confirmState, setConfirmState] = useState({ open: false, msg: '', action: null })

  const cargar = () => {
    setLoading(true)
    getUsuariosSistema()
      .then((d) => setUsuarios(d.items || []))
      .catch(() => setMsg({ tipo: 'error', texto: 'Error al cargar usuarios' }))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    cargar()
  }, [])

  const handleCreate = async (data) => {
    try {
      await createUsuarioSistema(data)
      setShowForm(false)
      setMsg({ tipo: 'ok', texto: 'Usuario creado correctamente' })
      cargar()
    } catch (e) {
      setMsg({ tipo: 'error', texto: e.message })
    }
  }

  const handleUpdate = async (id, data) => {
    try {
      await updateUsuarioSistema(id, data)
      setEditando(null)
      setMsg({ tipo: 'ok', texto: 'Usuario actualizado' })
      cargar()
    } catch (e) {
      setMsg({ tipo: 'error', texto: e.message })
    }
  }

  const handleResetPassword = async (id, nuevaPassword) => {
    try {
      await resetPasswordUsuario(id, nuevaPassword)
      setMsg({ tipo: 'ok', texto: 'Contraseña reseteada' })
    } catch (e) {
      setMsg({ tipo: 'error', texto: e.message })
    }
  }

  const handleDelete = async (id) => {
    setConfirmState({
      open: true,
      msg: '¿Eliminar este usuario?',
      action: async () => {
        try {
          await deleteUsuarioSistema(id)
          setMsg({ tipo: 'ok', texto: 'Usuario eliminado' })
          cargar()
        } catch (e) {
          setMsg({ tipo: 'error', texto: e.message })
        }
      },
    })
  }

  if (user?.rol !== 'admin') {
    return (
      <div className="p-8 text-center text-mgd-100 opacity-60">
        Solo los administradores pueden gestionar usuarios del sistema.
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-white">Usuarios del sistema</h1>
        <button
          onClick={() => {
            setEditando(null)
            setShowForm(true)
          }}
          className="px-4 py-2 bg-mgd-600 hover:bg-mgd-500 text-white text-sm font-medium rounded-lg"
        >
          + Nuevo usuario
        </button>
      </div>

      {msg && (
        <div
          className={`mb-4 px-4 py-2 rounded-lg text-sm ${
            msg.tipo === 'ok'
              ? 'bg-green-500/10 border border-green-500/30 text-green-400'
              : 'bg-red-500/10 border border-red-500/30 text-red-400'
          }`}
        >
          {msg.texto}
          <button onClick={() => setMsg(null)} className="ml-2 opacity-60 hover:opacity-100">
            ×
          </button>
        </div>
      )}

      {loading ? (
        <p className="text-mgd-100 opacity-40 text-sm">Cargando...</p>
      ) : usuarios.length === 0 ? (
        <p className="text-mgd-100 opacity-40 text-sm">No hay usuarios creados</p>
      ) : (
        <div className="bg-mgd-900 border border-mgd-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-mgd-800">
                <th className="text-left px-4 py-3 text-mgd-100 opacity-60 font-medium">Usuario</th>
                <th className="text-left px-4 py-3 text-mgd-100 opacity-60 font-medium">Nombre</th>
                <th className="text-left px-4 py-3 text-mgd-100 opacity-60 font-medium">Rol</th>
                <th className="text-left px-4 py-3 text-mgd-100 opacity-60 font-medium">Estado</th>
                <th className="text-right px-4 py-3 text-mgd-100 opacity-60 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id} className="border-b border-mgd-800/50 hover:bg-mgd-800/30">
                  <td className="px-4 py-3 text-white font-mono">{u.username}</td>
                  <td className="px-4 py-3 text-white">{u.nombre}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-1 rounded-full ${
                        u.rol === 'admin'
                          ? 'bg-purple-500/20 text-purple-300'
                          : u.rol === 'operador'
                            ? 'bg-blue-500/20 text-blue-300'
                            : 'bg-mgd-600/30 text-mgd-100'
                      }`}
                    >
                      {ROLES.find((r) => r.value === u.rol)?.label || u.rol}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs ${u.activo ? 'text-green-400' : 'text-red-400'}`}>
                      {u.activo ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button
                      onClick={() => setEditando(u)}
                      className="text-xs text-mgd-100 opacity-60 hover:opacity-100"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() => {
                        const pw = prompt(`Nueva contraseña para ${u.username}:`)
                        if (pw) handleResetPassword(u.id, pw)
                      }}
                      className="text-xs text-mgd-100 opacity-60 hover:opacity-100"
                    >
                      Reset pw
                    </button>
                    {u.id !== user?.id && (
                      <button
                        onClick={() => handleDelete(u.id)}
                        className="text-xs text-red-400 opacity-60 hover:opacity-100"
                      >
                        Eliminar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && (
        <Modal titulo="Nuevo usuario" onClose={() => setShowForm(false)}>
          <FormUsuario onSubmit={handleCreate} onCancel={() => setShowForm(false)} />
        </Modal>
      )}

      {editando && (
        <Modal titulo="Editar usuario" onClose={() => setEditando(null)}>
          <FormUsuario
            usuario={editando}
            onSubmit={(data) => handleUpdate(editando.id, data)}
            onCancel={() => setEditando(null)}
          />
        </Modal>
      )}

      <ConfirmModal
        open={confirmState.open}
        title="Eliminar usuario"
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

function FormUsuario({ usuario, onSubmit, onCancel }) {
  const [form, setForm] = useState({
    username: usuario?.username || '',
    password: '',
    nombre: usuario?.nombre || '',
    email: usuario?.email || '',
    rol: usuario?.rol || 'operador',
    activo: usuario?.activo ?? true,
  })
  const [error, setError] = useState('')

  const campo = (key, val) => setForm((f) => ({ ...f, [key]: val }))

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    if (!form.username.trim() || !form.nombre.trim()) {
      setError('Usuario y nombre son obligatorios')
      return
    }
    if (!usuario && !form.password) {
      setError('La contraseña es obligatoria para nuevos usuarios')
      return
    }
    const data = { ...form }
    if (usuario && !data.password) delete data.password
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-2 rounded-lg">{error}</div>
      )}

      <div>
        <label className="block text-xs font-medium text-mgd-100 mb-1">Usuario</label>
        <input
          type="text"
          value={form.username}
          onChange={(e) => campo('username', e.target.value)}
          disabled={!!usuario}
          required
          className="w-full px-3 py-2 bg-mgd-800 border border-mgd-600 rounded-lg text-white text-sm disabled:opacity-50"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-mgd-100 mb-1">
          {usuario ? 'Nueva contraseña (dejar vacío para no cambiar)' : 'Contraseña'}
        </label>
        <input
          type="password"
          value={form.password}
          onChange={(e) => campo('password', e.target.value)}
          className="w-full px-3 py-2 bg-mgd-800 border border-mgd-600 rounded-lg text-white text-sm"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-mgd-100 mb-1">Nombre completo</label>
        <input
          type="text"
          value={form.nombre}
          onChange={(e) => campo('nombre', e.target.value)}
          required
          className="w-full px-3 py-2 bg-mgd-800 border border-mgd-600 rounded-lg text-white text-sm"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-mgd-100 mb-1">Email</label>
        <input
          type="email"
          value={form.email}
          onChange={(e) => campo('email', e.target.value)}
          className="w-full px-3 py-2 bg-mgd-800 border border-mgd-600 rounded-lg text-white text-sm"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-mgd-100 mb-1">Rol</label>
        <select
          value={form.rol}
          onChange={(e) => campo('rol', e.target.value)}
          className="w-full px-3 py-2 bg-mgd-800 border border-mgd-600 rounded-lg text-white text-sm"
        >
          {ROLES.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </div>

      {usuario && (
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.activo}
            onChange={(e) => campo('activo', e.target.checked)}
            id="activo"
            className="rounded"
          />
          <label htmlFor="activo" className="text-sm text-mgd-100">
            Activo
          </label>
        </div>
      )}

      <div className="flex gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 py-2 bg-mgd-800 hover:bg-mgd-700 text-mgd-100 text-sm rounded-lg"
        >
          Cancelar
        </button>
        <button
          type="submit"
          className="flex-1 py-2 bg-mgd-600 hover:bg-mgd-500 text-white text-sm font-medium rounded-lg"
        >
          {usuario ? 'Guardar' : 'Crear'}
        </button>
      </div>
    </form>
  )
}
