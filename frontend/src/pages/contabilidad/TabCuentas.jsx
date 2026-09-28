import { useState, useEffect, useCallback } from 'react'
import Modal from '../../components/Modal'
import ConfirmModal from '../../components/ConfirmModal'
import Paginacion from '../../components/Paginacion'
import { getCuentas, createCuenta, updateCuenta, deleteCuenta } from '../../services/contabilidad'
import { EUR } from './utils'
import { usePermissions } from '../../hooks/usePermissions'

export default function TabCuentas({ empresa, onIrAMayor }) {
  const { has } = usePermissions()
  const [q, setQ] = useState('')
  const [qVal, setQVal] = useState('')
  const [soloConSaldo, setSoloConSaldo] = useState(false)
  const [cuentas, setCuentas] = useState([])
  const [total, setTotal] = useState(0)
  const [pagina, setPagina] = useState(1)
  const [limit, setLimit] = useState(100)
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState({})
  const [error, setError] = useState('')
  const [confirmState, setConfirmState] = useState({ open: false, msg: '', action: null })

  const cargar = useCallback(async () => {
    const params = { empresa_id: empresa.id, skip: (pagina - 1) * limit, limit }
    if (q) params.q = q
    if (soloConSaldo) params.solo_con_saldo = true
    const data = await getCuentas(params)
    setCuentas(data.items)
    setTotal(data.total)
  }, [empresa.id, q, soloConSaldo, pagina, limit])

  useEffect(() => {
    cargar()
  }, [cargar])
  useEffect(() => {
    setPagina(1)
  }, [q, soloConSaldo])

  const buscar = () => setQ(qVal)

  const abrirNuevo = () => {
    setForm({ cuenta: '', texto: '' })
    setModal('nuevo')
    setError('')
  }

  const abrirEditar = (c) => {
    setForm({ texto: c.texto || '', marca: c.marca || '' })
    setModal(c)
    setError('')
  }

  const guardar = async () => {
    if (modal === 'nuevo' && !form.cuenta?.trim()) {
      setError('El código de cuenta es obligatorio')
      return
    }
    try {
      if (modal === 'nuevo') {
        await createCuenta({ ...form, empresa_id: empresa.id })
      } else {
        await updateCuenta(modal.id, form)
      }
      setModal(null)
      cargar()
    } catch {
      setError('Error al guardar')
    }
  }

  const eliminar = async (c) => {
    setConfirmState({
      open: true,
      msg: `¿Eliminar la cuenta ${c.cuenta}?`,
      action: async () => {
        try {
          await deleteCuenta(c.id)
          cargar()
        } catch (e) {
          alert(e.message || 'No se puede eliminar (tiene movimientos asociados)')
        }
      },
    })
  }

  return (
    <div>
      <div className="flex gap-3 mb-4 flex-wrap">
        <input
          className="input w-64"
          placeholder="Buscar por código o descripción..."
          value={qVal}
          onChange={(e) => setQVal(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && buscar()}
        />
        <button className="btn btn-secondary" onClick={buscar}>
          Buscar
        </button>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
          <input
            type="checkbox"
            className="w-4 h-4 accent-mgd-600"
            checked={soloConSaldo}
            onChange={(e) => setSoloConSaldo(e.target.checked)}
          />
          Solo con saldo
        </label>
        <span className="text-sm text-gray-500 flex-1 self-center">{total} cuentas</span>
        {has('create') && (
          <button className="btn btn-primary" onClick={abrirNuevo}>
            + Nueva cuenta
          </button>
        )}
      </div>

      <div className="card">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Cuenta
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Descripción
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Debe
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Haber
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Saldo
              </th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {cuentas.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  Sin cuentas
                </td>
              </tr>
            )}
            {cuentas.map((c) => {
              const saldo = (c.debe ?? 0) - (c.haber ?? 0)
              return (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-mono text-gray-800 font-medium">{c.cuenta}</td>
                  <td className="px-4 py-2.5 text-gray-700">{c.texto}</td>
                  <td className="px-4 py-2.5 text-right text-gray-600 font-mono text-xs">{EUR(c.debe)}</td>
                  <td className="px-4 py-2.5 text-right text-gray-600 font-mono text-xs">{EUR(c.haber)}</td>
                  <td
                    className={`px-4 py-2.5 text-right font-mono text-xs font-semibold ${saldo < 0 ? 'text-red-600' : saldo > 0 ? 'text-gray-800' : 'text-gray-400'}`}
                  >
                    {EUR(saldo)}
                  </td>
                  <td className="px-4 py-2.5 text-right whitespace-nowrap">
                    {onIrAMayor && (
                      <button
                        className="btn btn-secondary text-xs mr-2"
                        onClick={() => onIrAMayor(c.cuenta)}
                        title="Ver en Libro mayor"
                      >
                        → Mayor
                      </button>
                    )}
                    {has('update') && (
                      <button className="btn btn-secondary text-xs mr-2" onClick={() => abrirEditar(c)}>
                        Editar
                      </button>
                    )}
                    {has('delete') && (
                      <button className="btn btn-danger text-xs" onClick={() => eliminar(c)}>
                        Eliminar
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <Paginacion
        total={total}
        skip={(pagina - 1) * limit}
        limit={limit}
        onCambiar={(s) => setPagina(Math.floor(s / limit) + 1)}
        onLimitChange={(n) => {
          setLimit(n)
          setPagina(1)
        }}
      />

      {modal && (
        <Modal
          titulo={modal === 'nuevo' ? 'Nueva cuenta' : `Editar cuenta ${modal.cuenta}`}
          onClose={() => setModal(null)}
        >
          {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
          <div className="grid grid-cols-2 gap-4">
            {modal === 'nuevo' && (
              <div>
                <label className="label">Código de cuenta *</label>
                <input
                  className="input font-mono"
                  value={form.cuenta}
                  onChange={(e) => setForm({ ...form, cuenta: e.target.value })}
                />
              </div>
            )}
            <div className={modal === 'nuevo' ? '' : 'col-span-2'}>
              <label className="label">Descripción</label>
              <input
                className="input"
                value={form.texto}
                onChange={(e) => setForm({ ...form, texto: e.target.value })}
              />
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button className="btn btn-secondary" onClick={() => setModal(null)}>
              Cancelar
            </button>
            <button className="btn btn-primary" onClick={guardar}>
              Guardar
            </button>
          </div>
        </Modal>
      )}

      <ConfirmModal
        open={confirmState.open}
        title="Eliminar cuenta"
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
