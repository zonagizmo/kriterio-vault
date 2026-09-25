import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(username, password)
      navigate('/empresas')
    } catch (err) {
      setError(err.message || 'Error al iniciar sesión')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-mgd-900 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white tracking-tight">Kriterio Vault</h1>
          <p className="text-mgd-100 opacity-60 mt-1 text-sm">Inicia sesión para continuar</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-mgd-900 border border-mgd-700 rounded-xl p-6 space-y-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-2 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-mgd-100 mb-1">Usuario</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              className="w-full px-3 py-2 bg-mgd-800 border border-mgd-600 rounded-lg text-white text-sm focus:outline-none focus:border-mgd-400"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-mgd-100 mb-1">Contraseña</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 bg-mgd-800 border border-mgd-600 rounded-lg text-white text-sm focus:outline-none focus:border-mgd-400"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-mgd-600 hover:bg-mgd-500 disabled:opacity-50 text-white font-medium rounded-lg text-sm transition-colors"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}
