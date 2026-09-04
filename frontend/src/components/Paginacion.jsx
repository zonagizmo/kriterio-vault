const OPCIONES = [50, 100, 150, 9999]

export default function Paginacion({ total, skip, limit, onCambiar, onLimitChange }) {
  const paginado = limit < 9999
  const pagActual = paginado ? Math.floor(skip / limit) : 0
  const totalPags = paginado ? Math.ceil(total / limit) : 1

  if (total === 0) return null
  if (totalPags <= 1 && !onLimitChange) return null

  const ir = (pag) => onCambiar(pag * limit)

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t bg-white">
      <span className="text-sm text-gray-500">
        {skip + 1}–{Math.min(skip + limit, total)} de {total}
      </span>
      <div className="flex items-center gap-2">
        {paginado && totalPags > 1 && (
          <div className="flex gap-1">
            <button
              disabled={pagActual === 0}
              onClick={() => ir(pagActual - 1)}
              className="px-3 py-1 rounded border text-sm disabled:opacity-40 hover:bg-gray-50"
            >
              ‹
            </button>
            {Array.from({ length: Math.min(totalPags, 7) }, (_, i) => {
              const p = totalPags <= 7 ? i : i + Math.max(0, pagActual - 3)
              if (p >= totalPags) return null
              return (
                <button
                  key={p}
                  onClick={() => ir(p)}
                  className={`px-3 py-1 rounded border text-sm ${
                    p === pagActual
                      ? 'bg-mgd-600 text-white border-mgd-600'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  {p + 1}
                </button>
              )
            })}
            <button
              disabled={pagActual >= totalPags - 1}
              onClick={() => ir(pagActual + 1)}
              className="px-3 py-1 rounded border text-sm disabled:opacity-40 hover:bg-gray-50"
            >
              ›
            </button>
          </div>
        )}
        {onLimitChange && (
          <select
            value={limit}
            onChange={(e) => onLimitChange(Number(e.target.value))}
            className="text-sm border rounded px-2 py-1 text-gray-600 bg-white cursor-pointer"
          >
            {OPCIONES.map((o) => (
              <option key={o} value={o}>{o >= 9999 ? 'Todo' : o}</option>
            ))}
          </select>
        )}
      </div>
    </div>
  )
}
