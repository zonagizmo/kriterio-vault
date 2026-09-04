import { useState, useRef, useEffect } from 'react'
import { getCuentas } from '../services/contabilidad'

export default function AutocompleteCuenta({
  empresaId,
  value,
  onChange,
  onSelect,
  placeholder = 'Ej: 430',
  className = '',
  onKeyDown: onKeyDownExterno,
  onBlur,
  tabIndex,
}) {
  const [sugerencias, setSugerencias] = useState([])
  const [abierto, setAbierto]         = useState(false)
  const [highlighted, setHighlighted] = useState(-1)
  const ref     = useRef(null)
  const listRef = useRef(null)
  const timer   = useRef(null)

  useEffect(() => {
    clearTimeout(timer.current)
    if (!value || value.length < 1) {
      setSugerencias([])
      setAbierto(false)
      return
    }
    timer.current = setTimeout(async () => {
      try {
        const data = await getCuentas({ empresa_id: empresaId, q: value, limit: 10, skip: 0 })
        setSugerencias(data.items || [])
        setAbierto(true)
        setHighlighted(-1)
      } catch {
        setSugerencias([])
      }
    }, 150)
    return () => clearTimeout(timer.current)
  }, [value, empresaId])

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setAbierto(false)
        setHighlighted(-1)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (highlighted >= 0 && listRef.current) {
      listRef.current.children[highlighted]?.scrollIntoView({ block: 'nearest' })
    }
  }, [highlighted])

  const seleccionar = (c) => {
    onChange(c.cuenta)
    onSelect?.(c)
    setSugerencias([])
    setAbierto(false)
    setHighlighted(-1)
  }

  const handleKeyDown = (e) => {
    if (abierto && sugerencias.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setHighlighted((h) => Math.min(h + 1, sugerencias.length - 1))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setHighlighted((h) => Math.max(h - 1, 0))
        return
      }
      if (e.key === 'Enter' && highlighted >= 0) {
        e.preventDefault()
        seleccionar(sugerencias[highlighted])
        return
      }
      if (e.key === 'Escape') {
        setAbierto(false)
        setHighlighted(-1)
        return
      }
    }
    onKeyDownExterno?.(e)
  }

  return (
    <div className="relative" ref={ref}>
      <input
        tabIndex={tabIndex}
        className={`input font-mono ${className}`}
        placeholder={placeholder}
        value={value}
        autoComplete="off"
        onChange={(e) => { onChange(e.target.value); setHighlighted(-1) }}
        onKeyDown={handleKeyDown}
        onBlur={onBlur}
      />
      {abierto && sugerencias.length > 0 && (
        <div
          ref={listRef}
          className="absolute z-50 left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-52 overflow-auto min-w-[560px]"
        >
          {sugerencias.map((c, i) => (
            <div
              key={c.id}
              className={`px-3 py-2 cursor-pointer flex items-center gap-3 ${
                i === highlighted ? 'bg-mgd-600 text-white' : 'hover:bg-blue-50'
              }`}
              onMouseDown={() => seleccionar(c)}
              onMouseEnter={() => setHighlighted(i)}
            >
              <span className={`font-mono text-sm font-semibold shrink-0 w-24 ${i === highlighted ? 'text-white' : 'text-gray-800'}`}>
                {c.cuenta}
              </span>
              <span className={`text-sm truncate ${i === highlighted ? 'text-blue-100' : 'text-gray-500'}`}>
                {c.texto}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
