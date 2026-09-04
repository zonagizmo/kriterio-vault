import { useState, useRef, useEffect } from 'react'

export default function AutocompleteEntidad({ items, value, onChange, placeholder = 'Buscar por nombre o CIF...', tabIndex, clearable = false }) {
  const [query, setQuery]           = useState('')
  const [abierto, setAbierto]       = useState(false)
  const [highlighted, setHighlighted] = useState(-1)
  const ref     = useRef(null)
  const listRef = useRef(null)

  const seleccionado = items.find((i) => i.numero === value)

  const filtrados = query.length >= 1
    ? items
        .filter((i) =>
          i.nombre?.toLowerCase().includes(query.toLowerCase()) ||
          i.nif?.toLowerCase().includes(query.toLowerCase())
        )
        .slice(0, 25)
    : []

  // Cerrar al clicar fuera
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setAbierto(false)
        setQuery('')
        setHighlighted(-1)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Hacer scroll al elemento resaltado
  useEffect(() => {
    if (highlighted >= 0 && listRef.current) {
      const el = listRef.current.children[highlighted]
      el?.scrollIntoView({ block: 'nearest' })
    }
  }, [highlighted])

  const seleccionar = (item) => {
    onChange(item.numero)
    setQuery('')
    setAbierto(false)
    setHighlighted(-1)
  }

  const abrir = () => {
    setQuery('')
    setAbierto(true)
    setHighlighted(-1)
  }

  const onKeyDown = (e) => {
    if (!abierto || filtrados.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlighted((h) => Math.min(h + 1, filtrados.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlighted((h) => Math.max(h - 1, 0))
    } else if (e.key === 'Enter' && highlighted >= 0) {
      e.preventDefault()
      seleccionar(filtrados[highlighted])
    } else if (e.key === 'Escape') {
      setAbierto(false)
      setHighlighted(-1)
    }
  }

  return (
    <div className="relative" ref={ref}>
      {/* Campo visible: nombre seleccionado o input de búsqueda */}
      {!abierto && seleccionado ? (
        <div
          tabIndex={tabIndex ?? 0}
          className="input cursor-pointer flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-mgd-500"
          onClick={abrir}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); abrir() } }}
        >
          <span className="truncate flex-1">{seleccionado.nombre}</span>
          <span className="text-xs text-gray-400 shrink-0">{seleccionado.nif}</span>
          {clearable && (
            <button
              type="button"
              className="text-gray-300 hover:text-gray-600 shrink-0 leading-none"
              onMouseDown={(e) => { e.stopPropagation(); e.preventDefault(); onChange('') }}
            >✕</button>
          )}
        </div>
      ) : (
        <input
          tabIndex={tabIndex}
          className="input"
          placeholder={placeholder}
          value={query}
          onChange={(e) => { setQuery(e.target.value); setAbierto(true); setHighlighted(-1) }}
          onFocus={() => setAbierto(true)}
          onKeyDown={onKeyDown}
        />
      )}

      {/* Dropdown de resultados */}
      {abierto && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-auto" ref={listRef}>
          {filtrados.length === 0 ? (
            <p className="px-3 py-4 text-sm text-gray-400 text-center">
              {query.length < 1 ? 'Escribe para buscar…' : 'Sin resultados'}
            </p>
          ) : (
            filtrados.map((item, i) => (
              <div
                key={item.id}
                className={`px-3 py-2 cursor-pointer flex items-center justify-between gap-2 ${
                  i === highlighted ? 'bg-mgd-600 text-white' : 'hover:bg-blue-50'
                }`}
                onMouseDown={() => seleccionar(item)}
                onMouseEnter={() => setHighlighted(i)}
              >
                <span className={`text-sm font-medium truncate ${i === highlighted ? 'text-white' : ''}`}>
                  {item.nombre}
                </span>
                <span className={`text-xs shrink-0 ${i === highlighted ? 'text-blue-100' : 'text-gray-400'}`}>
                  {item.nif}
                </span>
              </div>
            ))
          )}
        </div>
      )}

      {/* Input oculto para validación required HTML5 */}
      <input
        tabIndex={-1}
        required
        value={value || ''}
        onChange={() => {}}
        className="sr-only"
        aria-hidden="true"
      />
    </div>
  )
}
