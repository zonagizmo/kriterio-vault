import { useState } from 'react'
import api from '../services/api'

export default function BotonApagar({ variant = 'sidebar' }) {
  const [confirmando, setConfirmando] = useState(false)
  const [apagando, setApagando] = useState(false)

  async function apagar() {
    setApagando(true)
    try {
      await api.post('/shutdown')
    } catch {
      // El servidor se cierra antes de responder; ignorar error de red
    }
    // Intentar cerrar la pestaña; si el navegador lo bloquea, mostrar aviso
    window.close()
  }

  if (apagando) {
    return (
      <div className={variant === 'sidebar'
        ? 'px-4 py-3 text-xs text-mgd-100 opacity-60'
        : 'text-sm text-gray-500'
      }>
        Servidor detenido. Puedes cerrar esta ventana.
      </div>
    )
  }

  if (confirmando) {
    return (
      <div className={variant === 'sidebar'
        ? 'px-3 py-3 border-t border-mgd-800'
        : 'flex flex-col items-center gap-2'
      }>
        <p className={variant === 'sidebar'
          ? 'text-xs text-mgd-100 mb-2 opacity-80'
          : 'text-sm text-gray-600 mb-1'
        }>
          ¿Cerrar la aplicación?
        </p>
        <div className="flex gap-2">
          <button
            onClick={apagar}
            className="flex-1 text-xs bg-red-600 hover:bg-red-700 text-white px-3 py-1.5 rounded font-medium transition-colors"
          >
            Sí, cerrar
          </button>
          <button
            onClick={() => setConfirmando(false)}
            className={`flex-1 text-xs px-3 py-1.5 rounded font-medium transition-colors ${
              variant === 'sidebar'
                ? 'bg-mgd-800 hover:bg-mgd-700 text-mgd-100'
                : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
            }`}
          >
            Cancelar
          </button>
        </div>
      </div>
    )
  }

  if (variant === 'sidebar') {
    return (
      <div className="px-3 py-3 border-t border-mgd-800">
        <button
          onClick={() => setConfirmando(true)}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-mgd-100 opacity-60 hover:opacity-100 hover:bg-mgd-800 transition-all"
        >
          <span>⏻</span>
          <span>Apagar</span>
        </button>
      </div>
    )
  }

  // variant === 'selector'
  return (
    <button
      onClick={() => setConfirmando(true)}
      className="flex items-center gap-2 text-sm text-mgd-100 opacity-40 hover:opacity-80 transition-opacity mt-8"
    >
      <span>⏻</span>
      <span>Apagar aplicación</span>
    </button>
  )
}
