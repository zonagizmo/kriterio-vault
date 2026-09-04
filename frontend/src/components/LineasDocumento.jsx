import { useState, useRef } from 'react'
import { getArticulos } from '../services/articulos'
import { useEmpresa } from '../hooks/useEmpresa.jsx'

const EUR = (v) => Number(v || 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })

const LINEA_VACIA = {
  articulo: null, texto: 'Total', cantidad: 1, precio: 0,
  dcto1: 0, dcto2: 0, dcto3: 0, tiva: null, importe: 0,
}

function calcImporte(l) {
  let v = (l.cantidad || 1) * (l.precio || 0)
  if (l.dcto1) v *= (1 - l.dcto1 / 100)
  if (l.dcto2) v *= (1 - l.dcto2 / 100)
  if (l.dcto3) v *= (1 - l.dcto3 / 100)
  return Math.round(v * 100) / 100
}

// Intercepta coma y punto numérico para usarlos como separador decimal
function onDecimalKeyDown(e) {
  if (e.key === ',' || e.code === 'NumpadDecimal') {
    e.preventDefault()
    const el = e.currentTarget
    const s = el.selectionStart ?? el.value.length
    const end = el.selectionEnd ?? el.value.length
    const newVal = el.value.slice(0, s) + '.' + el.value.slice(end)
    el.value = newVal
    el.setSelectionRange(s + 1, s + 1)
    el.dispatchEvent(new Event('input', { bubbles: true }))
  }
}

function BuscadorArticulo({ empresaId, onSeleccionar }) {
  const [q, setQ] = useState('')
  const [resultados, setResultados] = useState([])
  const [buscando, setBuscando] = useState(false)

  const buscar = async (texto) => {
    setQ(texto)
    if (texto.length < 2) { setResultados([]); return }
    setBuscando(true)
    try {
      const data = await getArticulos(empresaId, { q: texto, limit: 10 })
      setResultados(data.items)
    } finally {
      setBuscando(false)
    }
  }

  return (
    <div className="relative">
      <input
        className="input text-xs"
        placeholder="Buscar artículo..."
        value={q}
        onChange={(e) => buscar(e.target.value)}
        autoFocus
      />
      {resultados.length > 0 && (
        <ul className="absolute z-50 bg-white border rounded-lg shadow-lg mt-1 w-72 max-h-48 overflow-y-auto text-sm">
          {resultados.map((a) => (
            <li
              key={a.id}
              className="px-3 py-2 hover:bg-mgd-50 cursor-pointer"
              onClick={() => { onSeleccionar(a); setResultados([]) }}
            >
              <span className="font-medium">{a.nombre}</span>
              {a.codigo && <span className="text-gray-400 text-xs ml-2">{a.codigo}</span>}
              <span className="block text-gray-500 text-xs">{EUR(a.pventa)} / ud.</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function LineasDocumento({ lineas, onChange, tabIndexAnadir }) {
  const { empresa } = useEmpresa()
  const [buscandoIdx, setBuscandoIdx] = useState(null)
  const justAdded = useRef(false)

  const actualizar = (idx, campo, valor) => {
    const nuevas = lineas.map((l, i) => {
      if (i !== idx) return l
      const updated = { ...l, [campo]: valor }
      updated.importe = calcImporte(updated)
      return updated
    })
    onChange(nuevas)
  }

  const seleccionarArticulo = (idx, articulo) => {
    const nuevas = lineas.map((l, i) => {
      if (i !== idx) return l
      const updated = {
        ...l,
        articulo: articulo.numero,
        texto: articulo.nombre,
        precio: articulo.pventa || 0,
        dcto1: articulo.dcto || 0,
        tiva: articulo.tipoivav,
      }
      updated.importe = calcImporte(updated)
      return updated
    })
    onChange(nuevas)
    setBuscandoIdx(null)
  }

  const agregarLinea = () => {
    onChange([...lineas, { ...LINEA_VACIA }])
    justAdded.current = true
  }

  const eliminarLinea = (idx) => onChange(lineas.filter((_, i) => i !== idx))

  const total = lineas.reduce((s, l) => s + (l.importe || 0), 0)

  return (
    <div>
      <div className="overflow-x-auto border rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-3 py-2 font-medium text-gray-600 w-56">Artículo / Descripción</th>
              <th className="text-right px-3 py-2 font-medium text-gray-600 w-20">Cantidad</th>
              <th className="text-right px-3 py-2 font-medium text-gray-600 w-24">Precio</th>
              <th className="text-right px-3 py-2 font-medium text-gray-600 w-16">Dto %</th>
              <th className="text-right px-3 py-2 font-medium text-gray-600 w-24">Importe</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {lineas.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-6 text-gray-400 text-xs">
                  Sin líneas — pulsa «+ Añadir línea»
                </td>
              </tr>
            )}
            {lineas.map((linea, idx) => (
              <tr key={idx} className="group">
                <td className="px-3 py-2">
                  {buscandoIdx === idx ? (
                    <BuscadorArticulo
                      empresaId={empresa?.id}
                      onSeleccionar={(a) => seleccionarArticulo(idx, a)}
                    />
                  ) : (
                    <div
                      className="flex items-center gap-1 cursor-pointer"
                      onClick={() => setBuscandoIdx(idx)}
                    >
                      <input
                        ref={(el) => {
                          if (el && justAdded.current && idx === lineas.length - 1) {
                            el.focus()
                            el.select()
                            justAdded.current = false
                          }
                        }}
                        className="input text-xs flex-1"
                        value={linea.texto || ''}
                        onChange={(e) => actualizar(idx, 'texto', e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        placeholder="Descripción..."
                      />
                      <button
                        type="button"
                        onClick={() => setBuscandoIdx(idx)}
                        className="text-gray-400 hover:text-mgd-600 text-xs shrink-0"
                        title="Buscar artículo"
                      >
                        🔍
                      </button>
                    </div>
                  )}
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number" step="0.001" min="0"
                    className="input text-xs text-right"
                    value={linea.cantidad}
                    onChange={(e) => actualizar(idx, 'cantidad', parseFloat(e.target.value) || 0)}
                  />
                </td>
                <td className="px-3 py-2">
                  {/* Uncontrolled: key cambia al seleccionar artículo, forzando re-mount con defaultValue actualizado */}
                  <input
                    key={`p-${idx}-${linea.articulo ?? 'x'}`}
                    type="text"
                    inputMode="decimal"
                    className="input text-xs text-right"
                    defaultValue={linea.precio || 0}
                    onKeyDown={onDecimalKeyDown}
                    onChange={(e) => actualizar(idx, 'precio', parseFloat(e.target.value.replace(',', '.')) || 0)}
                    onBlur={(e) => {
                      const num = parseFloat(e.target.value.replace(',', '.')) || 0
                      e.target.value = String(num)
                      actualizar(idx, 'precio', num)
                    }}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number" step="0.01" min="0" max="100"
                    className="input text-xs text-right"
                    value={linea.dcto1}
                    onChange={(e) => actualizar(idx, 'dcto1', parseFloat(e.target.value) || 0)}
                  />
                </td>
                <td className="px-3 py-2 text-right font-mono text-xs font-medium">
                  {EUR(linea.importe)}
                </td>
                <td className="px-3 py-2">
                  <button
                    type="button"
                    onClick={() => eliminarLinea(idx)}
                    className="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-3">
        <button
          type="button"
          tabIndex={tabIndexAnadir}
          onClick={agregarLinea}
          className="btn-secondary text-xs"
        >
          + Añadir línea
        </button>
        <div className="text-right">
          <span className="text-sm text-gray-500 mr-3">Total:</span>
          <span className="text-lg font-bold text-gray-900">{EUR(total)}</span>
        </div>
      </div>
    </div>
  )
}
