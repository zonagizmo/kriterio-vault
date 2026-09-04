import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import Modal from '../components/Modal'
import Paginacion from '../components/Paginacion'
import {
  getBancos, createBanco, updateBanco, deleteBanco,
  getVencimientos, updateVencimiento,
} from '../services/bancos'

const EUR = (v) =>
  (v ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })

const hoy = () => new Date().toISOString().slice(0, 10)

// ── Pestaña Cuentas ───────────────────────────────────────────────────────────

function TabCuentas({ empresa, bancos, reload, onVerMovimientos }) {
  const [modal, setModal] = useState(null) // null | 'nuevo' | banco
  const [form, setForm] = useState({})
  const [error, setError] = useState('')

  const abrirNuevo = () => {
    setForm({ nombre: '', sucursal: '', numcta: '', cuenta: '', notas: '', saldoini: 0 })
    setModal('nuevo')
    setError('')
  }

  const abrirEditar = (b) => {
    setForm({ numero: b.numero, nombre: b.nombre || '', sucursal: b.sucursal || '',
      numcta: b.numcta || '', cuenta: b.cuenta || '', notas: b.notas || '', saldoini: b.saldoini || 0 })
    setModal(b)
    setError('')
  }

  const guardar = async () => {
    if (!form.nombre?.trim()) { setError('El nombre es obligatorio'); return }
    try {
      if (modal === 'nuevo') {
        await createBanco({ ...form, empresa_id: empresa.id, saldoini: Number(form.saldoini) || 0 })
      } else {
        await updateBanco(modal.id, {
          ...form,
          numero: Number(form.numero),
          saldoini: Number(form.saldoini) || 0,
        })
      }
      setModal(null)
      reload()
    } catch {
      setError('Error al guardar')
    }
  }

  const eliminar = async (b) => {
    if (!confirm(`¿Eliminar el banco "${b.nombre}"?`)) return
    try {
      await deleteBanco(b.id)
      reload()
    } catch (e) {
      alert(e.message || 'No se puede eliminar (tiene movimientos u otros registros asociados)')
    }
  }

  return (
    <div>
      <div className="flex justify-end mb-4">
        <button className="btn btn-primary" onClick={abrirNuevo}>+ Nueva cuenta</button>
      </div>

      <div className="card">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Nº</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Nombre</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Cuenta contable</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Notas</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Saldo inicial</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Saldo actual</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {bancos.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Sin cuentas bancarias</td></tr>
            )}
            {bancos.map((b) => (
              <tr key={b.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500">{b.numero}</td>
                <td className="px-4 py-3 font-medium text-gray-900">{b.nombre}</td>
                <td className="px-4 py-3 text-gray-600 font-mono text-xs">{b.cuenta}</td>
                <td className="px-4 py-3 text-gray-600">{b.notas}</td>
                <td className="px-4 py-3 text-right text-gray-600">{EUR(b.saldoini)}</td>
                <td className={`px-4 py-3 text-right font-semibold ${((b.saldoini ?? 0) + (b.saldoact ?? 0)) < 0 ? 'text-red-600' : 'text-green-700'}`}>
                  {EUR((b.saldoini ?? 0) + (b.saldoact ?? 0))}
                </td>
                <td className="px-4 py-3 text-right">
                  <button className="btn btn-secondary text-xs mr-2" onClick={() => onVerMovimientos(b.numero)}>Movimientos</button>
                  <button className="btn btn-secondary text-xs mr-2" onClick={() => abrirEditar(b)}>Editar</button>
                  <button className="btn btn-danger text-xs" onClick={() => eliminar(b)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modal && (
        <Modal titulo={modal === 'nuevo' ? 'Nueva cuenta bancaria' : 'Editar cuenta'} onClose={() => setModal(null)}>
          {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
          <div className="grid grid-cols-2 gap-4">
            {modal !== 'nuevo' && (
              <div>
                <label className="label">Nº (orden)</label>
                <input type="number" min="1" className="input w-24 font-mono" value={form.numero}
                  onChange={(e) => setForm({ ...form, numero: e.target.value })} />
              </div>
            )}
            <div className={modal !== 'nuevo' ? '' : 'col-span-2'}>
              <label className="label">Nombre *</label>
              <input className="input" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} />
            </div>
            <div>
              <label className="label">Sucursal</label>
              <input className="input" value={form.sucursal} onChange={(e) => setForm({ ...form, sucursal: e.target.value })} />
            </div>
            <div>
              <label className="label">N.º cuenta (IBAN/CCC)</label>
              <input className="input font-mono" value={form.numcta} onChange={(e) => setForm({ ...form, numcta: e.target.value })} />
            </div>
            <div>
              <label className="label">Cuenta contable</label>
              <input className="input" value={form.cuenta} onChange={(e) => setForm({ ...form, cuenta: e.target.value })} />
            </div>
            <div>
              <label className="label">Saldo inicial</label>
              <input type="number" step="0.01" className="input" value={form.saldoini}
                onChange={(e) => setForm({ ...form, saldoini: e.target.value })} />
            </div>
            <div className="col-span-2">
              <label className="label">Notas</label>
              <textarea className="input" rows={2} value={form.notas} onChange={(e) => setForm({ ...form, notas: e.target.value })} />
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancelar</button>
            <button className="btn btn-primary" onClick={guardar}>Guardar</button>
          </div>
        </Modal>
      )}
    </div>
  )
}


// ── Pestaña Vencimientos ──────────────────────────────────────────────────────

function TabVencimientos({ empresa }) {
  const [tipo, setTipo] = useState('')
  const [soloPendientes, setSoloPendientes] = useState(false)
  const [vtos, setVtos] = useState([])
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [limit, setLimit] = useState(50)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState({})

  const cargar = useCallback(async () => {
    const params = {
      empresa_id: empresa.id,
      skip,
      limit,
    }
    if (tipo) params.tipo = tipo
    if (soloPendientes) params.solo_pendientes = true
    const data = await getVencimientos(params)
    setVtos(data.items)
    setTotal(data.total)
  }, [empresa.id, tipo, soloPendientes, skip, limit])

  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { setSkip(0) }, [tipo, soloPendientes])

  const abrirEditar = (v) => {
    setForm({ fecha: v.fecha ?? '', pendiente: v.pendiente ?? 0 })
    setEditando(v)
  }

  const guardar = async () => {
    try {
      await updateVencimiento(editando.id, {
        fecha: form.fecha || null,
        pendiente: parseFloat(form.pendiente) || 0,
      })
      setEditando(null)
      cargar()
    } catch {
      alert('Error al guardar')
    }
  }

  const tipoLabel = (v) => {
    if (v.tipo === 'X') return v.extra_tipo === 'I' ? 'Extra (Ingreso)' : 'Extra (Gasto)'
    return ({ R: 'Factura recibida', F: 'Factura emitida', N: 'Paga NNA' }[v.tipo] ?? v.tipo)
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <select className="input w-40" value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="">Todos los tipos</option>
          <option value="R">Facturas recibidas</option>
          <option value="X">Extra / Gastos</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input type="checkbox" checked={soloPendientes}
            onChange={(e) => setSoloPendientes(e.target.checked)} />
          Solo pendientes
        </label>
        <span className="text-sm text-gray-500 flex-1">{total} vencimientos</span>
      </div>

      <div className="card">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Nº</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Tipo</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Fecha</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Cuenta</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Importe</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Pendiente</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {vtos.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Sin vencimientos</td></tr>
            )}
            {vtos.map((v) => (
              <tr key={v.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500">{v.numero}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                    v.tipo === 'X' ? (v.extra_tipo === 'I' ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800') :
                    v.tipo === 'R' ? 'bg-red-100 text-red-800' :
                    v.tipo === 'F' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-700'
                  }`}>
                    {tipoLabel(v)}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">{v.fecha}</td>
                <td className="px-4 py-3 text-gray-600">{v.cuenta}</td>
                <td className="px-4 py-3 text-right text-gray-700">{EUR(v.importe)}</td>
                <td className={`px-4 py-3 text-right font-medium ${(v.pendiente ?? 0) > 0 ? 'text-amber-600' : 'text-gray-400'}`}>
                  {EUR(v.pendiente)}
                </td>
                <td className="px-4 py-3 text-right">
                  <button className="btn btn-secondary text-xs" onClick={() => abrirEditar(v)}>Editar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Paginacion total={total} skip={skip} limit={limit} onCambiar={setSkip}
        onLimitChange={(n) => { setLimit(n); setSkip(0) }} />

      {editando && (
        <Modal titulo={`Vencimiento #${editando.numero}`} onClose={() => setEditando(null)}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Fecha vencimiento</label>
              <input type="date" className="input" value={form.fecha}
                onChange={(e) => setForm({ ...form, fecha: e.target.value })} />
            </div>
            <div>
              <label className="label">Pendiente</label>
              <input type="number" step="0.01" className="input" value={form.pendiente}
                onChange={(e) => setForm({ ...form, pendiente: e.target.value })} />
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-500">
            <span>Importe original: {EUR(editando.importe)}</span>
            {editando.cuenta && <span className="ml-4">Cuenta: {editando.cuenta}</span>}
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button className="btn btn-secondary" onClick={() => setEditando(null)}>Cancelar</button>
            <button className="btn btn-primary" onClick={guardar}>Guardar</button>
          </div>
        </Modal>
      )}
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function BancosPage() {
  const { empresa } = useEmpresa()
  const navigate = useNavigate()
  const [tab, setTab] = useState('cuentas')
  const [bancos, setBancos] = useState([])

  const cargarBancos = useCallback(async () => {
    if (!empresa) return
    const data = await getBancos(empresa.id)
    setBancos(data)
  }, [empresa])

  useEffect(() => { cargarBancos() }, [cargarBancos])

  const irAMovimientos = (numeroB) => {
    navigate(`/bancos/${numeroB}/movimientos`)
  }

  if (!empresa) {
    return (
      <div className="p-8 text-center text-gray-400">
        Selecciona una empresa para ver los datos bancarios.
      </div>
    )
  }

  const tabs = [
    { id: 'cuentas', label: 'Cuentas bancarias' },
    { id: 'vencimientos', label: 'Vencimientos' },
  ]

  return (
    <div className="h-full overflow-y-auto">
      {/* Cabecera */}
      <div className="bg-gray-50 border-b border-gray-200 px-6 pt-5 pb-4">
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-gray-900">Bancos y Tesorería</h1>
          <p className="text-gray-500 text-sm mt-1">{empresa.nombre}</p>
        </div>

        {/* Tarjetas de saldo */}
        {bancos.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            {bancos.map((b) => (
              <button
                key={b.id}
                onClick={() => irAMovimientos(b.numero)}
                className="card px-4 py-3 text-left hover:ring-2 hover:ring-mgd-400 transition-all cursor-pointer group"
              >
                <p className="text-xs text-gray-500 truncate">{b.nombre}</p>
                <p className={`text-lg font-bold mt-0.5 ${((b.saldoini ?? 0) + (b.saldoact ?? 0)) < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                  {EUR((b.saldoini ?? 0) + (b.saldoact ?? 0))}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  Saldo inicial: {EUR(b.saldoini)}
                </p>
                <p className="text-xs text-mgd-500 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  Ver movimientos →
                </p>
              </button>
            ))}
            <div className="card px-4 py-3 bg-mgd-50 border-mgd-200">
              <p className="text-xs text-mgd-600 font-medium">Total</p>
              <p className="text-lg font-bold mt-0.5 text-mgd-800">
                {EUR(bancos.reduce((s, b) => s + (b.saldoini ?? 0) + (b.saldoact ?? 0), 0))}
              </p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="flex gap-1">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  tab === t.id
                    ? 'border-mgd-600 text-mgd-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Contenido */}
      <div className="p-6">
        {tab === 'cuentas' && <TabCuentas empresa={empresa} bancos={bancos} reload={cargarBancos} onVerMovimientos={irAMovimientos} />}
        {tab === 'vencimientos' && <TabVencimientos empresa={empresa} />}
      </div>
    </div>
  )
}
