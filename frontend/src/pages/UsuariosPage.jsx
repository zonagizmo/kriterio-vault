import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import Modal from '../components/Modal'
import Paginacion from '../components/Paginacion'
import {
  getUsuarios, createUsuario, updateUsuario, deleteUsuario,
  getPagas, createPaga, deletePaga,
  registrarMes, getSaldosNNA, exportarPagas,
  getAniosPagas, getResumenPagasAnual, exportarResumenPagasAnual,
} from '../services/usuarios'

const cuentaNNA = (numero) => `4001${String(numero).padStart(3, '0')}`

const EUR = (v) =>
  (v ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })

const fmtFecha = (f) => {
  if (!f) return ''
  const [y, m, d] = String(f).split('-')
  return `${d}/${m}/${y}`
}

const MESES_ABR = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

const hoy = () => new Date().toISOString().slice(0, 10)

function calcularEdad(fechaNac) {
  if (!fechaNac) return null
  const hoy = new Date()
  const nac = new Date(fechaNac)
  let edad = hoy.getFullYear() - nac.getFullYear()
  const m = hoy.getMonth() - nac.getMonth()
  if (m < 0 || (m === 0 && hoy.getDate() < nac.getDate())) edad--
  return edad
}

// ── Pestaña Usuarios ──────────────────────────────────────────────────────────

function TabUsuarios({ empresa, usuarios, saldos, reload }) {
  const navigate = useNavigate()
  const [filtroActivo, setFiltroActivo] = useState(true)
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState({})
  const [error, setError] = useState('')
  const [bajaModal, setBajaModal] = useState(null)
  const [fechaBaja, setFechaBaja] = useState(hoy())

  const usuariosFiltrados = usuarios.filter((u) =>
    filtroActivo === null ? true : u.activo === filtroActivo
  )

  const abrirNuevo = () => {
    setForm({
      nombre: '', fecha_nacimiento: '', fecha_ingreso: hoy(),
      fecha_salida: '', paga_mensual: '', activo: true, notas: '',
    })
    setModal('nuevo')
    setError('')
  }

  const abrirEditar = (u) => {
    setForm({
      nombre: `${u.nombre || ''} ${u.apellidos || ''}`.trim(),
      fecha_nacimiento: u.fecha_nacimiento || '',
      fecha_ingreso: u.fecha_ingreso || '',
      fecha_salida: u.fecha_salida || '',
      paga_mensual: u.paga_mensual ?? '',
      activo: u.activo ?? true,
      notas: u.notas || '',
    })
    setModal(u)
    setError('')
  }

  const guardar = async () => {
    if (!form.nombre?.trim()) { setError('El nombre es obligatorio'); return }
    try {
      const payload = {
        ...form,
        apellidos: '',
        paga_mensual: parseFloat(form.paga_mensual) || 0,
        fecha_nacimiento: form.fecha_nacimiento || null,
        fecha_ingreso: form.fecha_ingreso || null,
        fecha_salida: form.fecha_salida || null,
      }
      if (modal === 'nuevo') {
        await createUsuario({ ...payload, empresa_id: empresa.id })
      } else {
        await updateUsuario(modal.id, payload)
      }
      setModal(null)
      reload()
    } catch {
      setError('Error al guardar')
    }
  }

  const eliminar = async (u) => {
    if (!confirm(`¿Eliminar a ${u.nombre} ${u.apellidos || ''}?`)) return
    try {
      await deleteUsuario(u.id)
      reload()
    } catch (e) {
      alert(e.message || 'No se puede eliminar (tiene pagas registradas)')
    }
  }

  const abrirBaja = (u) => {
    setFechaBaja(hoy())
    setBajaModal(u)
  }

  const confirmarBaja = async () => {
    await updateUsuario(bajaModal.id, { fecha_salida: fechaBaja || null, activo: false })
    setBajaModal(null)
    reload()
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
          {[{ val: true, label: 'Activos' }, { val: false, label: 'Baja' }, { val: null, label: 'Todos' }].map((opt) => (
            <button
              key={String(opt.val)}
              onClick={() => setFiltroActivo(opt.val)}
              className={`px-3 py-1.5 ${filtroActivo === opt.val ? 'bg-mgd-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <span className="text-sm text-gray-500 flex-1">{usuariosFiltrados.length} usuarios</span>
        <button className="btn btn-primary" onClick={abrirNuevo}>+ Nuevo usuario</button>
      </div>

      <div className="card">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Cuenta</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Nombre</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Edad</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Ingreso</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Paga mes</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Saldo</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Estado</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {usuariosFiltrados.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Sin usuarios</td></tr>
            )}
            {usuariosFiltrados.map((u) => {
              const edad = calcularEdad(u.fecha_nacimiento)
              const saldo = saldos?.[u.numero]
              return (
                <tr key={u.id} className={`hover:bg-gray-50 ${!u.activo ? 'opacity-60' : ''}`}>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{cuentaNNA(u.numero)}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{u.nombre} {u.apellidos}</p>
                    {u.notas && <p className="text-xs text-gray-400 truncate max-w-xs">{u.notas}</p>}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {edad !== null ? `${edad} años` : '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{u.fecha_ingreso || '—'}</td>
                  <td className="px-4 py-3 text-right font-medium text-gray-800">
                    {(u.paga_mensual ?? 0) > 0 ? EUR(u.paga_mensual) : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-sm">
                    {saldo !== undefined
                      ? <span className={saldo < -0.005 ? 'text-red-600' : saldo > 0.005 ? 'text-green-700' : 'text-gray-400'}>{EUR(saldo)}</span>
                      : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${u.activo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {u.activo ? 'Activo' : 'Baja'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button className="btn btn-secondary text-xs"
                      onClick={() => navigate(`/contabilidad?tab=mayor&cuenta=${cuentaNNA(u.numero)}`)}
                      title="Ver en Libro Mayor">Mayor</button>
                    <button className="btn btn-secondary text-xs" onClick={() => abrirEditar(u)}>Editar</button>
                    {u.activo && (
                      <button className="btn btn-secondary text-xs" onClick={() => abrirBaja(u)}>Baja</button>
                    )}
                    <button className="btn btn-danger text-xs" onClick={() => eliminar(u)}>X</button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {modal && (
        <Modal titulo={modal === 'nuevo' ? 'Nuevo usuario NNA' : `Editar: ${modal.nombre}`} onClose={() => setModal(null)}>
          {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="label">Nombre y apellidos *</label>
              <input className="input" value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value })} />
            </div>
            <div>
              <label className="label">Fecha de nacimiento</label>
              <input type="date" className="input" value={form.fecha_nacimiento}
                onChange={(e) => setForm({ ...form, fecha_nacimiento: e.target.value })} />
            </div>
            <div>
              <label className="label">Paga mensual</label>
              <input type="number" step="0.01" min="0" className="input" value={form.paga_mensual}
                onChange={(e) => setForm({ ...form, paga_mensual: e.target.value })} />
            </div>
            <div>
              <label className="label">Fecha de ingreso</label>
              <input type="date" className="input" value={form.fecha_ingreso}
                onChange={(e) => setForm({ ...form, fecha_ingreso: e.target.value })} />
            </div>
            <div>
              <label className="label">Fecha de salida</label>
              <input type="date" className="input" value={form.fecha_salida}
                onChange={(e) => setForm({ ...form, fecha_salida: e.target.value })} />
            </div>
            <div className="col-span-2">
              <label className="label">Notas</label>
              <textarea className="input" rows={2} value={form.notas}
                onChange={(e) => setForm({ ...form, notas: e.target.value })} />
            </div>
            <div className="col-span-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.activo}
                  onChange={(e) => setForm({ ...form, activo: e.target.checked })} />
                <span className="text-sm text-gray-700">Usuario activo</span>
              </label>
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancelar</button>
            <button className="btn btn-primary" onClick={guardar}>Guardar</button>
          </div>
        </Modal>
      )}

      {bajaModal && (
        <Modal titulo={`Dar de baja a ${bajaModal.nombre}`} onClose={() => setBajaModal(null)}>
          <div>
            <label className="label">Fecha de baja</label>
            <input type="date" className="input w-40" value={fechaBaja}
              onChange={(e) => setFechaBaja(e.target.value)} />
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button className="btn btn-secondary" onClick={() => setBajaModal(null)}>Cancelar</button>
            <button className="btn btn-primary" onClick={confirmarBaja}>Registrar baja</button>
          </div>
        </Modal>
      )}
    </div>
  )
}

// ── Modal registro mensual ────────────────────────────────────────────────────

function ModalMes({ empresa, onClose, onGuardado }) {
  const [fecha, setFecha] = useState(hoy())
  const [todosItems, setTodosItems] = useState([])   // lista completa cargada
  const [items, setItems] = useState([])             // lista activa (los que no se han quitado)
  const [cargando, setCargando] = useState(true)
  const [busqueda, setBusqueda] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    getUsuarios({ empresa_id: empresa.id, activo: true, limit: 500 })
      .then((data) => {
        const lista = data.items.map((u) => ({
          usuario: u.numero,
          nombre: `${u.nombre} ${u.apellidos || ''}`.trim(),
          importe: u.paga_mensual ?? 0,
          notas: '',
        }))
        setTodosItems(lista)
        setItems(lista)
        setCargando(false)
      })
  }, [empresa.id])

  const setItem = (usuario, field, val) => {
    setItems((prev) => prev.map((it) => it.usuario === usuario ? { ...it, [field]: val } : it))
  }

  const quitar = (usuario) => setItems((prev) => prev.filter((it) => it.usuario !== usuario))

  const restaurar = () => setItems(todosItems)

  const itemsVisibles = busqueda
    ? items.filter((it) => it.nombre.toLowerCase().includes(busqueda.toLowerCase()))
    : items

  const total = items.reduce((s, i) => s + (parseFloat(i.importe) || 0), 0)
  const conImporte = items.filter((i) => parseFloat(i.importe) > 0).length

  const guardar = async () => {
    const seleccionados = items.filter((i) => parseFloat(i.importe) > 0)
    if (!seleccionados.length) { setError('Ningún usuario tiene importe mayor de 0'); return }
    try {
      await registrarMes({
        empresa_id: empresa.id,
        fecha,
        items: seleccionados.map((i) => ({
          usuario: i.usuario,
          importe: parseFloat(i.importe),
          notas: i.notas || null,
        })),
      })
      onGuardado()
      onClose()
    } catch {
      setError('Error al registrar las pagas')
    }
  }

  return (
    <Modal titulo="Registrar pagas mensuales" onClose={onClose} ancho="max-w-3xl">
      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

      <div className="flex flex-wrap items-end gap-4 mb-4">
        <div>
          <label className="label">Fecha</label>
          <input type="date" className="input w-44" value={fecha}
            onChange={(e) => setFecha(e.target.value)} />
        </div>
        <div className="flex-1 min-w-48">
          <label className="label">Buscar NNA</label>
          <input className="input" placeholder="Filtrar por nombre..."
            value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
        </div>
        <div className="text-sm text-gray-500 self-end pb-2">
          {items.length} usuarios · {conImporte} con importe
          {items.length < todosItems.length && (
            <button className="ml-2 text-mgd-600 underline text-xs" onClick={restaurar}>
              Restaurar todos
            </button>
          )}
        </div>
      </div>

      {cargando ? (
        <p className="text-gray-400 text-sm py-4">Cargando usuarios...</p>
      ) : (
        <div className="border rounded-lg overflow-hidden mb-4 max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b sticky top-0">
              <tr>
                <th className="px-3 py-2 text-left text-xs text-gray-500 uppercase">NNA</th>
                <th className="px-3 py-2 text-right text-xs text-gray-500 uppercase w-32">Importe</th>
                <th className="px-3 py-2 text-left text-xs text-gray-500 uppercase">Nota</th>
                <th className="px-3 py-2 w-8"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {itemsVisibles.length === 0 && (
                <tr><td colSpan={4} className="px-3 py-6 text-center text-gray-400">Sin resultados</td></tr>
              )}
              {itemsVisibles.map((item) => (
                <tr key={item.usuario} className={parseFloat(item.importe) <= 0 ? 'bg-gray-50' : ''}>
                  <td className="px-3 py-2 font-medium text-gray-800">
                    <span className="font-mono text-xs text-gray-400 mr-1">{cuentaNNA(item.usuario)}</span>
                    {item.nombre}
                  </td>
                  <td className="px-3 py-2">
                    <input type="number" step="0.01" min="0" className="input text-right w-full text-sm"
                      value={item.importe}
                      onChange={(e) => setItem(item.usuario, 'importe', e.target.value)} />
                  </td>
                  <td className="px-3 py-2">
                    <input className="input text-sm" placeholder="Opcional..."
                      value={item.notas}
                      onChange={(e) => setItem(item.usuario, 'notas', e.target.value)} />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button className="text-gray-400 hover:text-red-500 text-lg leading-none"
                      title="Quitar de este registro" onClick={() => quitar(item.usuario)}>×</button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50 border-t font-semibold sticky bottom-0">
              <tr>
                <td className="px-3 py-2 text-gray-600">Total ({conImporte} pagas)</td>
                <td className="px-3 py-2 text-right text-gray-900">{EUR(total)}</td>
                <td colSpan={2}></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      <div className="flex justify-end gap-3">
        <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
        <button className="btn btn-primary" onClick={guardar} disabled={cargando || conImporte === 0}>
          Confirmar y registrar ({conImporte} pagas)
        </button>
      </div>
    </Modal>
  )
}

// ── Pestaña Resumen ───────────────────────────────────────────────────────────

function TabResumen({ empresa }) {
  const [anios, setAnios] = useState([])
  const [anio, setAnio] = useState(null)
  const [datos, setDatos] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [menuExport, setMenuExport] = useState(false)

  useEffect(() => {
    getAniosPagas(empresa.id).then((r) => {
      setAnios(r.anios)
      setAnio((prev) => prev ?? r.anios[0])
    })
  }, [empresa.id])

  useEffect(() => {
    if (!anio) return
    setCargando(true)
    getResumenPagasAnual(empresa.id, anio)
      .then(setDatos)
      .finally(() => setCargando(false))
  }, [empresa.id, anio])

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <label className="label mb-0">Año</label>
        {anios.length > 0 && (
          <select className="input w-32" value={anio ?? ''} onChange={(e) => setAnio(Number(e.target.value))}>
            {anios.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        )}
        {datos && (
          <div className="relative ml-auto">
            <button className="btn btn-secondary flex items-center gap-1"
              onClick={() => setMenuExport((v) => !v)}>
              Exportar <span className="text-xs">▾</span>
            </button>
            {menuExport && (
              <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 min-w-36"
                onMouseLeave={() => setMenuExport(false)}>
                {[{ fmt: 'xlsx', label: 'Excel (.xlsx)' }, { fmt: 'csv', label: 'CSV (.csv)' }].map(({ fmt, label }) => (
                  <button key={fmt}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg"
                    onClick={() => {
                      exportarResumenPagasAnual(empresa.id, anio, fmt)
                      setMenuExport(false)
                    }}>
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {cargando && <p className="text-gray-400 text-sm py-4">Cargando...</p>}

      {!cargando && datos && (
        <>
          <div className="card px-5 py-4 bg-mgd-50 border-mgd-200 inline-block">
            <p className="text-xs text-mgd-600 font-medium uppercase tracking-wide">Total pagas recibidas en {anio}</p>
            <p className="text-2xl font-bold text-mgd-800 mt-0.5">{EUR(datos.total_anual)}</p>
          </div>

          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase sticky left-0 bg-gray-50">NNA</th>
                  {MESES_ABR.map((m) => (
                    <th key={m} className="px-2 py-2 text-right text-xs font-semibold text-gray-500 uppercase">{m}</th>
                  ))}
                  <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {datos.usuarios.length === 0 && (
                  <tr><td colSpan={14} className="px-3 py-6 text-center text-gray-400">Sin pagas registradas en {anio}</td></tr>
                )}
                {datos.usuarios.map((u) => (
                  <tr key={u.usuario} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium text-gray-800 sticky left-0 bg-white">
                      <span className="font-mono text-xs text-gray-400 mr-1">{cuentaNNA(u.usuario)}</span>
                      {u.nombre}
                    </td>
                    {u.meses.map((m, i) => (
                      <td key={i} className={`px-2 py-2 text-right ${m > 0 ? 'text-gray-800' : 'text-gray-300'}`}>
                        {m > 0 ? EUR(m) : '—'}
                      </td>
                    ))}
                    <td className="px-3 py-2 text-right font-semibold text-gray-900">{EUR(u.total)}</td>
                  </tr>
                ))}
              </tbody>
              {datos.usuarios.length > 0 && (
                <tfoot className="bg-gray-50 border-t font-semibold sticky bottom-0">
                  <tr>
                    <td className="px-3 py-2 text-gray-600 sticky left-0 bg-gray-50">Total mes</td>
                    {datos.totales_mes.map((m, i) => (
                      <td key={i} className="px-2 py-2 text-right text-gray-900">{EUR(m)}</td>
                    ))}
                    <td className="px-3 py-2 text-right text-gray-900">{EUR(datos.total_anual)}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </>
      )}
    </div>
  )
}

// ── Pestaña Pagas ─────────────────────────────────────────────────────────────

function TabPagas({ empresa, usuarios }) {
  const anio = new Date().getFullYear()
  const mes = String(new Date().getMonth() + 1).padStart(2, '0')

  const [filtroUsuario, setFiltroUsuario] = useState('')
  const [fechaDesde, setFechaDesde] = useState(`${anio}-${mes}-01`)
  const [fechaHasta, setFechaHasta] = useState(hoy())
  const [pagas, setPagas] = useState([])
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [limit, setLimit] = useState(50)
  const [modalSemana, setModalSemana] = useState(false)
  const [modalPaga, setModalPaga] = useState(false)
  const [formPaga, setFormPaga] = useState({})
  const [error, setError] = useState('')
  const [menuExport, setMenuExport] = useState(false)
  const [sortBy, setSortBy] = useState('fecha')
  const [sortDir, setSortDir] = useState('desc')

  const nombreUsuario = (num) => {
    const u = usuarios.find((x) => x.numero === num)
    return u ? `${u.nombre} ${u.apellidos || ''}`.trim() : `#${num}`
  }

  const ordenarPor = (campo) => {
    if (sortBy === campo) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(campo)
      setSortDir(campo === 'fecha' ? 'desc' : 'asc')
    }
  }

  const flecha = (campo) => sortBy === campo ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''

  const cargar = useCallback(async () => {
    const params = {
      empresa_id: empresa.id,
      skip,
      limit,
      sort_by: sortBy,
      sort_dir: sortDir,
    }
    if (filtroUsuario) params.usuario = filtroUsuario
    if (fechaDesde) params.fecha_desde = fechaDesde
    if (fechaHasta) params.fecha_hasta = fechaHasta
    const data = await getPagas(params)
    setPagas(data.items)
    setTotal(data.total)
  }, [empresa.id, filtroUsuario, fechaDesde, fechaHasta, skip, limit, sortBy, sortDir])

  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { setSkip(0) }, [filtroUsuario, fechaDesde, fechaHasta])

  const totalImporte = pagas.reduce((s, p) => s + (p.importe || 0), 0)

  const abrirPagaIndividual = () => {
    setFormPaga({
      usuario: usuarios.find((u) => u.activo)?.numero ?? '',
      fecha: hoy(),
      importe: '',
      notas: '',
    })
    setModalPaga(true)
    setError('')
  }

  const guardarPagaIndividual = async () => {
    if (!formPaga.usuario) { setError('Selecciona un usuario'); return }
    const imp = parseFloat(formPaga.importe)
    if (!imp || imp <= 0) { setError('Introduce un importe válido'); return }
    try {
      await createPaga({
        empresa_id: empresa.id,
        usuario: parseInt(formPaga.usuario),
        fecha: formPaga.fecha,
        importe: imp,
        notas: formPaga.notas || null,
      })
      setModalPaga(false)
      cargar()
    } catch {
      setError('Error al guardar')
    }
  }

  const eliminar = async (p) => {
    if (!confirm('¿Eliminar este registro de paga?')) return
    try {
      await deletePaga(p.id)
      cargar()
    } catch (e) {
      alert(e.message || 'Error al eliminar la paga')
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div>
          <label className="label">Usuario</label>
          <select className="input w-48" value={filtroUsuario}
            onChange={(e) => setFiltroUsuario(e.target.value)}>
            <option value="">Todos</option>
            {usuarios.filter((u) => u.activo).map((u) => (
              <option key={u.id} value={u.numero}>
                {u.nombre} {u.apellidos || ''}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Desde</label>
          <input type="date" className="input" value={fechaDesde}
            onChange={(e) => setFechaDesde(e.target.value)} />
        </div>
        <div>
          <label className="label">Hasta</label>
          <input type="date" className="input" value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)} />
        </div>
        <span className="text-sm text-gray-500 flex-1 self-end pb-2">{total} registros</span>
        <div className="relative self-end">
          <button className="btn btn-secondary flex items-center gap-1"
            onClick={() => setMenuExport((v) => !v)}>
            Exportar <span className="text-xs">▾</span>
          </button>
          {menuExport && (
            <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 min-w-36"
              onMouseLeave={() => setMenuExport(false)}>
              {[{ fmt: 'xlsx', label: 'Excel (.xlsx)' }, { fmt: 'csv', label: 'CSV (.csv)' }].map(({ fmt, label }) => (
                <button key={fmt}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg"
                  onClick={() => {
                    exportarPagas({ empresa_id: empresa.id, usuario: filtroUsuario || undefined, fecha_desde: fechaDesde || undefined, fecha_hasta: fechaHasta || undefined, sort_by: sortBy, sort_dir: sortDir }, fmt)
                    setMenuExport(false)
                  }}>
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
        <button className="btn btn-secondary self-end" onClick={abrirPagaIndividual}>+ Paga individual</button>
        <button className="btn btn-primary self-end" onClick={() => setModalSemana(true)}>Registrar mes</button>
      </div>

      <div className="card">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700"
                onClick={() => ordenarPor('fecha')}>Fecha{flecha('fecha')}</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700"
                onClick={() => ordenarPor('usuario')}>Usuario{flecha('usuario')}</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700"
                onClick={() => ordenarPor('importe')}>Importe{flecha('importe')}</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Nota</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {pagas.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Sin pagas en el periodo seleccionado</td></tr>
            )}
            {pagas.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 text-gray-600">{fmtFecha(p.fecha)}</td>
                <td className="px-4 py-2.5 font-medium text-gray-900">{nombreUsuario(p.usuario)}</td>
                <td className="px-4 py-2.5 text-right font-semibold text-gray-800">{EUR(p.importe)}</td>
                <td className="px-4 py-2.5 text-gray-500 text-xs">{p.notas}</td>
                <td className="px-4 py-2.5 text-right">
                  <button className="btn btn-danger text-xs" onClick={() => eliminar(p)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
          {pagas.length > 0 && (
            <tfoot className="bg-gray-50 border-t-2 border-gray-200">
              <tr>
                <td colSpan={2} className="px-4 py-2.5 text-sm font-semibold text-gray-600">
                  Total mostrado ({pagas.length} registros)
                </td>
                <td className="px-4 py-2.5 text-right font-bold text-gray-900">{EUR(totalImporte)}</td>
                <td colSpan={2}></td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      <Paginacion total={total} skip={skip} limit={limit} onCambiar={setSkip}
        onLimitChange={(n) => { setLimit(n); setSkip(0) }} />

      {modalSemana && (
        <ModalMes empresa={empresa} onClose={() => setModalSemana(false)} onGuardado={cargar} />
      )}

      {modalPaga && (
        <Modal titulo="Paga individual" onClose={() => setModalPaga(false)}>
          {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="label">Usuario *</label>
              <select className="input" value={formPaga.usuario}
                onChange={(e) => setFormPaga({ ...formPaga, usuario: e.target.value })}>
                <option value="">— Selecciona —</option>
                {usuarios.filter((u) => u.activo).map((u) => (
                  <option key={u.id} value={u.numero}>
                    {u.nombre} {u.apellidos || ''}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Fecha *</label>
              <input type="date" className="input" value={formPaga.fecha}
                onChange={(e) => setFormPaga({ ...formPaga, fecha: e.target.value })} />
            </div>
            <div>
              <label className="label">Importe *</label>
              <input type="number" step="0.01" min="0" className="input" value={formPaga.importe}
                onChange={(e) => setFormPaga({ ...formPaga, importe: e.target.value })} />
            </div>
            <div className="col-span-2">
              <label className="label">Nota</label>
              <input className="input" placeholder="Motivo, adelanto, etc."
                value={formPaga.notas}
                onChange={(e) => setFormPaga({ ...formPaga, notas: e.target.value })} />
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button className="btn btn-secondary" onClick={() => setModalPaga(false)}>Cancelar</button>
            <button className="btn btn-primary" onClick={guardarPagaIndividual}>Guardar</button>
          </div>
        </Modal>
      )}
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function UsuariosPage() {
  const { empresa } = useEmpresa()
  const [tab, setTab] = useState('usuarios')
  const [usuarios, setUsuarios] = useState([])
  const [saldos, setSaldos] = useState({})

  const cargarUsuarios = useCallback(async () => {
    if (!empresa) return
    const data = await getUsuarios({ empresa_id: empresa.id, limit: 500 })
    setUsuarios(data.items)
    getSaldosNNA(empresa.id).then(setSaldos).catch(() => {})
  }, [empresa])

  useEffect(() => { cargarUsuarios() }, [cargarUsuarios])

  if (!empresa) {
    return (
      <div className="p-8 text-center text-gray-400">
        Selecciona una empresa para ver los usuarios.
      </div>
    )
  }

  const activos = usuarios.filter((u) => u.activo)
  const totalPagaMensual = activos.reduce((s, u) => s + (u.paga_mensual ?? 0), 0)

  const tabs = [
    { id: 'usuarios', label: 'Usuarios NNA' },
    { id: 'pagas', label: 'Pagas' },
    { id: 'resumen', label: 'Resumen' },
  ]

  return (
    <div className="h-full overflow-y-auto">
      {/* Cabecera */}
      <div className="bg-gray-50 border-b border-gray-200 px-6 pt-5 pb-4">
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-gray-900">Usuarios NNA</h1>
          <p className="text-gray-500 text-sm mt-1">{empresa.nombre}</p>
        </div>

        {/* Resumen */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="card px-4 py-3">
            <p className="text-xs text-gray-500">Usuarios activos</p>
            <p className="text-2xl font-bold text-gray-900 mt-0.5">{activos.length}</p>
          </div>
          <div className="card px-4 py-3">
            <p className="text-xs text-gray-500">Con paga mensual</p>
            <p className="text-2xl font-bold text-gray-900 mt-0.5">
              {activos.filter((u) => (u.paga_mensual ?? 0) > 0).length}
            </p>
          </div>
          <div className="card px-4 py-3 bg-mgd-50 border-mgd-200">
            <p className="text-xs text-mgd-600 font-medium">Total mensual de caja</p>
            <p className="text-xl font-bold text-mgd-800 mt-0.5">{totalPagaMensual.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}</p>
          </div>
        </div>

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

      {/* Contenido con scroll */}
      <div className="p-6">
        {tab === 'usuarios' && <TabUsuarios empresa={empresa} usuarios={usuarios} saldos={saldos} reload={cargarUsuarios} />}
        {tab === 'pagas' && <TabPagas empresa={empresa} usuarios={usuarios} />}
        {tab === 'resumen' && <TabResumen empresa={empresa} />}
      </div>
    </div>
  )
}
