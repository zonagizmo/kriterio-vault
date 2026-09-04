import { useState, useEffect } from 'react'
import Modal from './Modal'
import { getVencimientos } from '../services/bancos'

const EUR = (v) => (v ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
const fmtFecha = (f) => {
  if (!f) return ''
  const [y, m, d] = String(f).split('-')
  return `${d}/${m}/${y}`
}

export default function VtosSelector({ empresaId, onSelect, onClose }) {
  const [items, setItems]                 = useState([])
  const [total, setTotal]                 = useState(0)
  const [tipos, setTipos]                 = useState([])
  const [filtroTipo, setFiltroTipo]       = useState('')
  const [soloPendientes, setSoloPendientes] = useState(true)
  const [seleccionados, setSeleccionados] = useState(new Set())

  useEffect(() => {
    const params = { empresa_id: empresaId, solo_pendientes: soloPendientes, skip: 0, limit: 200 }
    if (filtroTipo) params.tipo = filtroTipo
    getVencimientos(params)
      .then((d) => {
        setItems(d.items)
        setTotal(d.total)
        setSeleccionados(new Set())
        const ts = [...new Set(d.items.map((v) => v.tipo))].filter(Boolean).sort()
        setTipos(ts)
      })
      .catch(() => {})
  }, [empresaId, filtroTipo, soloPendientes])

  const toggleItem = (id) => {
    setSeleccionados((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleTodos = () => {
    if (seleccionados.size === items.length) {
      setSeleccionados(new Set())
    } else {
      setSeleccionados(new Set(items.map((v) => v.id)))
    }
  }

  const confirmar = () => {
    const elegidos = items.filter((v) => seleccionados.has(v.id))
    if (elegidos.length === 0) return
    onSelect(elegidos)
  }

  const totalSeleccionado = items
    .filter((v) => seleccionados.has(v.id))
    .reduce((s, v) => s + (v.pendiente ?? v.importe ?? 0), 0)

  const todosSeleccionados = items.length > 0 && seleccionados.size === items.length

  return (
    <Modal titulo="Seleccionar vencimientos" onClose={onClose} ancho="max-w-3xl">
      <div className="flex items-center gap-3 mb-4">
        <select
          className="input w-36"
          value={filtroTipo}
          onChange={(e) => setFiltroTipo(e.target.value)}
        >
          <option value="">Todos los tipos</option>
          {tipos.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
          <input
            type="checkbox"
            checked={soloPendientes}
            onChange={(e) => setSoloPendientes(e.target.checked)}
          />
          Solo pendientes
        </label>
        <span className="text-sm text-gray-500 flex-1">
          {total} vencimiento{total !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="overflow-auto max-h-80 border border-gray-200 rounded">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 sticky top-0 border-b border-gray-200">
            <tr className="text-xs text-gray-500 uppercase">
              <th className="px-3 py-2 w-8">
                <input
                  type="checkbox"
                  checked={todosSeleccionados}
                  onChange={toggleTodos}
                  className="cursor-pointer"
                />
              </th>
              <th className="px-3 py-2 text-left">Nº</th>
              <th className="px-3 py-2 text-left">Tipo</th>
              <th className="px-3 py-2 text-left">Doc.</th>
              <th className="px-3 py-2 text-left">Fecha</th>
              <th className="px-3 py-2 text-right">Importe</th>
              <th className="px-3 py-2 text-right">Pendiente</th>
              <th className="px-3 py-2 text-left">Cuenta</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-gray-400">
                  Sin vencimientos
                </td>
              </tr>
            )}
            {items.map((v) => {
              const sel = seleccionados.has(v.id)
              return (
                <tr
                  key={v.id}
                  className={`cursor-pointer transition-colors ${sel ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
                  onClick={() => toggleItem(v.id)}
                >
                  <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={sel}
                      onChange={() => toggleItem(v.id)}
                      className="cursor-pointer"
                    />
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{v.numero}</td>
                  <td className="px-3 py-2 text-xs font-medium">{v.tipo}</td>
                  <td className="px-3 py-2 text-xs">{v.tpnumero ?? '—'}</td>
                  <td className="px-3 py-2">{fmtFecha(v.fecha)}</td>
                  <td className="px-3 py-2 text-right">{EUR(v.importe)}</td>
                  <td className={`px-3 py-2 text-right font-semibold ${(v.pendiente ?? 0) <= 0 ? 'text-gray-400' : 'text-green-700'}`}>
                    {EUR(v.pendiente)}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-500">
                    {v.cuentadef || v.cuenta || '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-4 pt-3 border-t">
        <span className="text-sm text-gray-500">
          {seleccionados.size > 0
            ? <><strong>{seleccionados.size}</strong> seleccionado{seleccionados.size !== 1 ? 's' : ''} · <strong>{EUR(totalSeleccionado)}</strong></>
            : 'Marca las filas que quieres añadir'}
        </span>
        <div className="flex gap-2">
          <button type="button" onClick={onClose} className="btn-secondary text-sm">Cancelar</button>
          <button
            type="button"
            onClick={confirmar}
            disabled={seleccionados.size === 0}
            className="btn-primary text-sm disabled:opacity-40"
          >
            Añadir {seleccionados.size > 0 ? seleccionados.size : ''} vencimiento{seleccionados.size !== 1 ? 's' : ''}
          </button>
        </div>
      </div>
    </Modal>
  )
}
