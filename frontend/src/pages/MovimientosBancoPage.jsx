import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useEmpresa } from '../hooks/useEmpresa.jsx'
import Modal from '../components/Modal'
import Paginacion from '../components/Paginacion'
import VtosSelector from '../components/VtosSelector'
import AutocompleteCuenta from '../components/AutocompleteCuenta'
import {
  getBancos,
  getMovimientos,
  createMovimiento,
  updateMovimiento,
  deleteMovimiento,
  reordenarMovimiento,
  repararSaldosBanco,
} from '../services/bancos'
import { getCuentas } from '../services/contabilidad'

const EUR = (v) =>
  (v ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
const hoy = () => new Date().toISOString().slice(0, 10)
const fmtFecha = (f) => {
  if (!f) return ''
  const [y, m, d] = String(f).split('-')
  return `${d}/${m}/${y}`
}

const mapPagoFromApi = (p) => {
  const hasVto   = p.vto   != null && p.vto   !== 0
  const hasBanco = p.bancot != null && p.bancot !== 0
  return {
    _tipo:              hasVto ? 'V' : hasBanco ? 'B' : 'D',
    importe:            p.importe ?? '',
    vto:                hasVto  ? p.vto   : null,
    bancot:             hasBanco ? p.bancot : null,
    dirsubcta:          p.dirsubcta || '',
    dirsubcta_nombre:   p.dirsubcta_nombre || '',
    declterc:           p.declterc  || '',
    _desc:              hasVto ? `Vto. ${p.vto}` : '',
    vto_tipo:           p.vto_tipo           ?? null,
    vto_tpnumero:       p.vto_tpnumero       ?? null,
    doc_numero_externo: p.doc_numero_externo  ?? null,
    doc_entidad_nombre: p.doc_entidad_nombre  ?? null,
    doc_fecha:          p.doc_fecha           ?? null,
    bancot_nombre:      p.bancot_nombre       ?? null,
  }
}

export default function MovimientosBancoPage() {
  const { numero } = useParams()
  const { empresa } = useEmpresa()
  const navigate = useNavigate()

  const [bancos, setBancos]   = useState([])
  const [movs, setMovs]       = useState([])
  const [total, setTotal]     = useState(0)
  const [skip, setSkip]       = useState(0)
  const [limit, setLimit]     = useState(50)
  const [filtroBanco, setFiltroBanco] = useState(numero ?? '')
  const [soloNoConciliados, setSoloNoConciliados] = useState(false)

  const [modal, setModal]         = useState(null)   // null | 'nuevo' | movObj
  const [form, setForm]           = useState({})
  const [pagos, setPagos]         = useState([])
  const [error, setError]         = useState('')
  const [guardando, setGuardando] = useState(false)
  const [cuentaNombres, setCuentaNombres] = useState({}) // código → nombre
  const [mostrarVtos, setMostrarVtos]     = useState(false)
  const [menuAnadir, setMenuAnadir]       = useState(false)
  const [menuIndice, setMenuIndice]       = useState(-1)
  const [menuCuadrar, setMenuCuadrar]     = useState(false)
  const menuRef = useRef(null)
  const cuadrarRef = useRef(null)
  const fechaRef = useRef(null)
  const filaRef = useRef(null)
  const [nuevoId, setNuevoId] = useState(null)
  const saltarUltima = useRef(true)   // flag: en la primera carga saltar a última página

  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuAnadir(false)
        setMenuIndice(-1)
      }
      if (cuadrarRef.current && !cuadrarRef.current.contains(e.target)) {
        setMenuCuadrar(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (!empresa) return
    getBancos(empresa.id).then(setBancos).catch(() => {})
  }, [empresa])

  const toggleConciliado = async (mov) => {
    try {
      await updateMovimiento(mov.id, { conciliado: !mov.conciliado })
      cargar()
    } catch { alert('Error al actualizar conciliación') }
  }

  const cargar = useCallback(async () => {
    if (!empresa) return
    const params = { empresa_id: empresa.id, skip, limit }
    if (filtroBanco) params.banco = filtroBanco
    if (soloNoConciliados) params.solo_no_conciliados = true
    const data = await getMovimientos(params)
    // En la primera carga saltar directamente a la última página
    if (saltarUltima.current && skip === 0 && data.total > limit) {
      saltarUltima.current = false
      const lastSkip = Math.floor((data.total - 1) / limit) * limit
      setSkip(lastSkip)
      return
    }
    saltarUltima.current = false
    setMovs(data.items)
    setTotal(data.total)
  }, [empresa, filtroBanco, skip, limit, soloNoConciliados])

  useEffect(() => { cargar() }, [cargar])
  useEffect(() => {
    saltarUltima.current = true   // resetear al cambiar de banco
    setSkip(0)
  }, [filtroBanco, soloNoConciliados])

  useEffect(() => {
    if (!nuevoId || !filaRef.current) return
    filaRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    const t = setTimeout(() => setNuevoId(null), 1800)
    return () => clearTimeout(t)
  }, [nuevoId, movs])

  const bancoActual = bancos.find((b) => String(b.numero) === String(filtroBanco))

  const formVacio = () => ({
    banco: filtroBanco || (bancos[0]?.numero ?? ''),
    fecha: hoy(),
    texto: '',
    total: '',
    notas: '',
    estado: '',
  })

  const abrirNuevo = () => {
    setForm(formVacio())
    setPagos([])
    setModal('nuevo')
    setError('')
  }

  const resolverNombreCuenta = async (codigo, empresaId) => {
    if (!codigo || !empresaId || cuentaNombres[codigo]) return
    try {
      const data = await getCuentas({ empresa_id: empresaId, q: codigo, limit: 1 })
      const match = data.items?.find((c) => c.cuenta === codigo)
      if (match) setCuentaNombres((prev) => ({ ...prev, [codigo]: match.texto }))
    } catch (_) {}
  }

  const abrirEditar = (mov) => {
    setForm({
      banco: mov.banco,
      fecha: mov.fecha,
      texto: mov.texto || '',
      total: mov.total ?? '',
      notas: mov.notas || '',
      estado: mov.estado || '',
    })
    const pagosMapped = mov.pagos?.length ? mov.pagos.map(mapPagoFromApi) : []
    setPagos(pagosMapped)
    setModal(mov)
    setError('')
    // Pre-cargar nombres desde la API y resolver los que falten
    const nombresIniciales = {}
    pagosMapped.forEach((p) => {
      if (p.dirsubcta && p.dirsubcta_nombre) {
        nombresIniciales[p.dirsubcta] = p.dirsubcta_nombre
      }
    })
    if (Object.keys(nombresIniciales).length) {
      setCuentaNombres((prev) => ({ ...prev, ...nombresIniciales }))
    }
    if (empresa?.id) {
      pagosMapped.forEach((p) => {
        if (p.dirsubcta && !p.dirsubcta_nombre) resolverNombreCuenta(p.dirsubcta, empresa.id)
      })
    }
  }

  const removePago = (i) => setPagos(pagos.filter((_, idx) => idx !== i))

  const setPagoField = (i, field, val) => {
    const arr = [...pagos]
    arr[i] = { ...arr[i], [field]: val }
    setPagos(arr)
  }

  const setPagoCobro = (i, val) => {
    const arr = [...pagos]
    arr[i] = { ...arr[i], importe: val === '' ? '' : Math.abs(parseFloat(val) || 0) }
    setPagos(arr)
  }

  const setPagoPago = (i, val) => {
    const arr = [...pagos]
    arr[i] = { ...arr[i], importe: val === '' ? '' : -Math.abs(parseFloat(val) || 0) }
    setPagos(arr)
  }

  const addOtroBanco = () => {
    const diff = Math.round((totalNum - sumLineas) * 100) / 100
    setPagos([...pagos, {
      _tipo: 'B',
      importe: diff !== 0 ? diff : '',
      vto: null,
      bancot: null,
      dirsubcta: null,
      declterc: null,
      _desc: '',
      vto_tipo: null, vto_tpnumero: null,
      doc_numero_externo: null, doc_entidad_nombre: null, doc_fecha: null,
      bancot_nombre: null,
    }])
    setMenuAnadir(false)
  }

  const addDirectoSubcuenta = () => {
    const diff = Math.round((totalNum - sumLineas) * 100) / 100
    setPagos([...pagos, {
      _tipo: 'D',
      importe: diff !== 0 ? diff : '',
      vto: null,
      bancot: null,
      dirsubcta: '',
      declterc: '',
      _desc: '',
      vto_tipo: null, vto_tpnumero: null,
      doc_numero_externo: null, doc_entidad_nombre: null, doc_fecha: null,
      bancot_nombre: null,
    }])
    setMenuAnadir(false)
    setMenuIndice(-1)
  }

  const seleccionarVto = (vtos) => {
    const nuevos = vtos.map((vto) => {
      const raw = vto.pendiente ?? vto.importe
      // R = factura recibida (pago, salida) → negativo
      // X + G = extra gasto (pago, salida) → negativo
      // N = paga NNA (pago, salida) → negativo
      // F = factura emitida (cobro, entrada) → positivo
      // X + I = extra ingreso (cobro, entrada) → positivo
      // El importe/pendiente del vencimiento ya viene en negativo cuando es un
      // abono (factura de abono, extra de abono...): no forzar el signo con
      // Math.abs, solo invertirlo según el sentido normal del tipo — así un
      // abono de un tipo "salida" se convierte correctamente en una entrada,
      // y viceversa.
      const importe = (vto.tipo === 'R' || vto.tipo === 'N' || (vto.tipo === 'X' && vto.extra_tipo === 'G'))
        ? -raw
        : raw
      return {
        _tipo: 'V',
        importe,
        vto: vto.numero,
        dirsubcta: vto.cuentadef || vto.cuenta || null,
        declterc: null,
        _desc: vto.tpnumero ? `Doc. ${vto.tpnumero}` : `Vto. ${vto.numero}`,
        vto_tipo:           vto.tipo       ?? null,
        vto_tpnumero:       vto.tpnumero   ?? null,
        doc_numero_externo: null,
        doc_entidad_nombre: null,
        doc_fecha:          null,
        bancot_nombre:      null,
      }
    })
    const nuevosPagos = [...pagos, ...nuevos]
    setPagos(nuevosPagos)
    const nuevoTotal = Math.round(
      nuevosPagos.reduce((s, p) => s + (parseFloat(p.importe) || 0), 0) * 100
    ) / 100
    setForm((f) => ({ ...f, total: nuevoTotal }))
    setMostrarVtos(false)
  }

  const esNuevo = modal === 'nuevo'
  const totalNum = parseFloat(form.total) || 0
  const saldoBase = bancoActual
    ? (bancoActual.saldoini ?? 0) + (bancoActual.saldoact ?? 0)
    : 0
  const saldoNuevo = esNuevo
    ? saldoBase + totalNum
    : saldoBase - (modal?.total ?? 0) + totalNum
  const sumLineas = pagos.reduce((s, p) => s + (parseFloat(p.importe) || 0), 0)
  const cuadrado = pagos.length > 0 && Math.abs(sumLineas - totalNum) < 0.005

  const anadirLineaAjuste = () => {
    const diff = Math.round((totalNum - sumLineas) * 100) / 100
    if (Math.abs(diff) < 0.005) return
    setPagos([...pagos, {
      _tipo: 'D',
      importe: diff,
      vto: null,
      bancot: null,
      dirsubcta: '',
      declterc: '',
      _desc: 'Ajuste',
      vto_tipo: null, vto_tpnumero: null,
      doc_numero_externo: null, doc_entidad_nombre: null, doc_fecha: null,
      bancot_nombre: null,
    }])
  }

  const ajustarTotalASuma = () => {
    setForm((f) => ({ ...f, total: Math.round(sumLineas * 100) / 100 }))
  }

  const guardar = async () => {
    if (!form.fecha) { setError('La fecha es obligatoria'); return }
    const totalN = parseFloat(form.total)
    if (isNaN(totalN)) { setError('El importe total no es válido'); return }
    const vtosRotos = pagos.filter((p) => p._tipo === 'V' && p.vto_existe === false)
    if (vtosRotos.length > 0) {
      const nums = vtosRotos.map((p) => `nº ${p.vto}`).join(', ')
      if (!confirm(`Aviso: los vencimientos ${nums} no existen actualmente.\n\nEs posible que el documento correspondiente haya sido eliminado. El pago quedará sin vincular a ningún documento; revisa la línea o selecciona un vencimiento válido.\n\n¿Continuar guardando?`)) return
    }
    setGuardando(true)
    try {
      const pagosClean = pagos
        .filter((p) => p.importe !== '' && !isNaN(parseFloat(p.importe)) && parseFloat(p.importe) !== 0)
        .map((p) => ({
          importe: parseFloat(p.importe),
          vto: p.vto ? parseInt(p.vto) : null,
          dirsubcta: p.dirsubcta || null,
          declterc: p.declterc || null,
          bancot: p.bancot ?? null,
        }))

      if (esNuevo) {
        if (!form.banco) { setError('Selecciona un banco'); setGuardando(false); return }
        const created = await createMovimiento({
          empresa_id: empresa.id,
          banco: parseInt(form.banco),
          fecha: form.fecha,
          texto: form.texto || null,
          total: totalN,
          notas: form.notas || null,
          estado: form.estado || null,
          pagos: pagosClean,
        })
        setNuevoId(created.id)
        // Reabrir el formulario en blanco para poder seguir dando de alta movimientos seguidos
        setForm(formVacio())
        setPagos([])
        fechaRef.current?.focus()
        // El nuevo movimiento cae en la última página (orden por fecha/número).
        // Si ya estamos en skip=0, cargar() ahora mismo (con el total fresco) decide si saltar.
        // Si no, solo cambiamos skip: el efecto disparará cargar() con el closure correcto,
        // evitando la carrera que resetea saltarUltima con un skip desactualizado.
        saltarUltima.current = true
        if (skip === 0) {
          cargar()
        } else {
          setSkip(0)
        }
      } else {
        await updateMovimiento(modal.id, {
          fecha: form.fecha,
          texto: form.texto || null,
          total: totalN,
          notas: form.notas || null,
          estado: form.estado || null,
          pagos: pagosClean,
        })
        setModal(null)
        cargar()
      }
      getBancos(empresa.id).then(setBancos).catch(() => {})
    } catch {
      setError('Error al guardar el movimiento')
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async (mov) => {
    if (!confirm('¿Eliminar este movimiento? Se revertirán los pagos asociados.')) return
    try {
      await deleteMovimiento(mov.id)
      cargar()
      getBancos(empresa.id).then(setBancos).catch(() => {})
    } catch {
      alert('Error al eliminar')
    }
  }

  const reordenar = async (mov, direccion) => {
    try {
      await reordenarMovimiento(mov.id, direccion)
      cargar()
      getBancos(empresa.id).then(setBancos).catch(() => {})
    } catch {
      alert('Error al reordenar')
    }
  }

  if (!empresa) {
    return <div className="p-8 text-center text-gray-400">Selecciona una empresa.</div>
  }

  return (
    <div className="h-full overflow-y-auto">
      {/* Cabecera */}
      <div className="bg-gray-50 border-b border-gray-200 px-6 pt-5 pb-3 shadow-sm">
        {/* Breadcrumb + título */}
        <div className="flex items-center gap-3 mb-3">
          <button
            onClick={() => navigate('/bancos')}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            title="Volver a Bancos"
          >
            ← Bancos
          </button>
          <span className="text-gray-300">/</span>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {bancoActual ? bancoActual.nombre : 'Movimientos'}
            </h1>
            {bancoActual && (
              <p className="text-sm text-gray-500 flex items-center gap-3">
                {empresa.nombre}
                {bancoActual.saldoact != null && (
                  <span className={`font-medium ${((bancoActual.saldoini ?? 0) + (bancoActual.saldoact ?? 0)) < 0 ? 'text-red-600' : 'text-green-700'}`}>
                    Saldo: {EUR((bancoActual.saldoini ?? 0) + (bancoActual.saldoact ?? 0))}
                  </span>
                )}
                <button
                  className="text-xs text-gray-400 hover:text-mgd-600 underline"
                  title="Recalcula saldonue de cada movimiento y sincroniza el saldo total"
                  onClick={async () => {
                    try {
                      const actualizado = await repararSaldosBanco(bancoActual.id)
                      setBancos((bs) => bs.map((b) => b.id === actualizado.id ? actualizado : b))
                      await cargar()
                    } catch (e) { alert(e.message) }
                  }}
                >
                  Reparar saldos
                </button>
              </p>
            )}
          </div>
        </div>

        {/* Filtro + botón nuevo */}
        <div className="flex items-center gap-3">
          <select
            className="input w-64"
            value={filtroBanco}
            onChange={(e) => {
              setFiltroBanco(e.target.value)
              const n = e.target.value
              navigate(n ? `/bancos/${n}/movimientos` : '/bancos/movimientos', { replace: true })
            }}
          >
            <option value="">Todos los bancos</option>
            {bancos.map((b) => (
              <option key={b.id} value={b.numero}>{b.nombre}</option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={soloNoConciliados}
              onChange={(e) => { setSoloNoConciliados(e.target.checked); setSkip(0) }}
              className="rounded"
            />
            Solo no conciliados
          </label>
          <span className="text-sm text-gray-500 flex-1">{total} movimiento{total !== 1 ? 's' : ''}</span>
          <button className="btn btn-primary" onClick={abrirNuevo}>+ Nuevo movimiento</button>
        </div>
      </div>

      {/* Tabla de movimientos */}
      <div className="p-6">
      <div className="card">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Nº</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Fecha</th>
              {!filtroBanco && (
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Banco</th>
              )}
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Concepto</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Importe</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Saldo</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider" title="Conciliado con extracto bancario">Conc.</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {bancoActual && skip === 0 && (
              <tr className="bg-gray-50 border-b-2 border-gray-200">
                <td className="px-4 py-3 text-gray-400 font-mono text-xs">—</td>
                <td className="px-4 py-3 text-gray-400 text-xs italic">Apertura</td>
                <td className="px-4 py-3 text-gray-500 italic text-xs" colSpan={2}>Saldo inicial</td>
                <td className={`px-4 py-3 text-right font-semibold text-sm ${(bancoActual.saldoini ?? 0) < 0 ? 'text-red-500' : 'text-gray-700'}`}>
                  {EUR(bancoActual.saldoini)}
                </td>
                <td></td>
                <td></td>
              </tr>
            )}
            {movs.length === 0 && (
              <tr>
                <td colSpan={filtroBanco ? 6 : 7} className="px-4 py-10 text-center text-gray-400">
                  Sin movimientos
                </td>
              </tr>
            )}
            {movs.map((m, idx) => {
              const bancoDelMov = bancos.find((b) => b.numero === m.banco)
              const saldoReal = (bancoDelMov?.saldoini ?? 0) + (m.saldonue ?? 0)
              const puedeSubir = idx > 0 && movs[idx - 1].fecha === m.fecha && movs[idx - 1].banco === m.banco
              const puedeBajar = idx < movs.length - 1 && movs[idx + 1].fecha === m.fecha && movs[idx + 1].banco === m.banco
              return (
                <tr key={m.id} ref={m.id === nuevoId ? filaRef : null}
                  className={`hover:bg-gray-50 transition-colors ${m.id === nuevoId ? 'bg-mgd-50 outline outline-1 outline-mgd-300' : ''}`}>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{m.numero}</td>
                  <td className="px-4 py-3 text-gray-600">{fmtFecha(m.fecha)}</td>
                  {!filtroBanco && (
                    <td className="px-4 py-3 text-gray-600 text-xs">{bancoDelMov?.nombre ?? m.banco}</td>
                  )}
                  <td className="px-4 py-3 text-gray-900">
                    {m.texto}
                    {m.notas && (
                      <span
                        className="ml-1.5 inline-block text-amber-500 cursor-help align-middle"
                        title={m.notas}
                      >
                        📝
                      </span>
                    )}
                    {m.pagos?.some((p) => p.bancot) && (() => {
                      const p = m.pagos.find((p) => p.bancot)
                      const nb = bancos.find((b) => b.numero === p.bancot)?.nombre ?? `Banco ${p.bancot}`
                      return (
                        <span className="ml-2 text-xs font-medium text-blue-500">
                          {(p.importe ?? 0) < 0 ? '→' : '←'} {nb}
                        </span>
                      )
                    })()}
                  </td>
                  <td className={`px-4 py-3 text-right font-medium ${(m.total ?? 0) < 0 ? 'text-red-600' : 'text-green-700'}`}>
                    {EUR(m.total)}
                  </td>
                  <td className={`px-4 py-3 text-right text-sm ${saldoReal < 0 ? 'text-red-500' : 'text-gray-600'}`}>
                    {EUR(saldoReal)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      title={m.conciliado ? 'Marcar como no conciliado' : 'Marcar como conciliado'}
                      onClick={() => toggleConciliado(m)}
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center mx-auto transition-colors ${
                        m.conciliado
                          ? 'bg-green-500 border-green-500 text-white'
                          : 'border-gray-300 hover:border-green-400'
                      }`}
                    >
                      {m.conciliado && <span className="text-xs leading-none">✓</span>}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <div className="inline-flex items-center gap-1">
                      <button
                        title="Subir"
                        disabled={!puedeSubir}
                        onClick={() => reordenar(m, 'arriba')}
                        className="text-gray-400 hover:text-gray-700 disabled:opacity-20 disabled:cursor-default text-sm px-1"
                      >▲</button>
                      <button
                        title="Bajar"
                        disabled={!puedeBajar}
                        onClick={() => reordenar(m, 'abajo')}
                        className="text-gray-400 hover:text-gray-700 disabled:opacity-20 disabled:cursor-default text-sm px-1"
                      >▼</button>
                      <button className="btn btn-secondary text-xs ml-1" onClick={() => abrirEditar(m)}>
                        Editar
                      </button>
                      <button className="text-red-500 hover:text-red-700 text-xs font-medium ml-1" onClick={() => eliminar(m)}>
                        Eliminar
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <Paginacion total={total} skip={skip} limit={limit} onCambiar={setSkip}
        onLimitChange={(n) => { setLimit(n); setSkip(0) }} />

      {/* Modal nuevo / editar */}
      {modal && (
        <Modal
          titulo={esNuevo ? 'Nuevo movimiento' : `Editar movimiento #${modal.numero}`}
          onClose={() => setModal(null)}
          ancho="max-w-3xl"
        >
          {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

          {/* Cabecera */}
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div>
              <label className="label">Banco</label>
              {esNuevo ? (
                <select
                  className="input"
                  value={form.banco}
                  onChange={(e) => setForm({ ...form, banco: e.target.value })}
                >
                  {bancos.map((b) => (
                    <option key={b.id} value={b.numero}>{b.nombre}</option>
                  ))}
                </select>
              ) : (
                <input
                  className="input bg-gray-50 text-gray-500"
                  readOnly
                  value={bancos.find((b) => b.numero === modal.banco)?.nombre ?? modal.banco}
                />
              )}
            </div>
            <div>
              <label className="label">Fecha *</label>
              <input
                ref={fechaRef}
                autoFocus
                type="date"
                className="input"
                value={form.fecha}
                onChange={(e) => setForm({ ...form, fecha: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Total *</label>
              <input
                type="number"
                step="0.01"
                className="input"
                value={form.total}
                placeholder="+ ingreso / − gasto"
                onChange={(e) => setForm({ ...form, total: e.target.value })}
              />
            </div>
            <div className="flex flex-col justify-end pb-1">
              <div className="text-xs text-gray-400 mb-0.5">Saldo nuevo</div>
              <div className={`text-base font-bold ${saldoNuevo < 0 ? 'text-red-600' : 'text-green-700'}`}>
                {EUR(saldoNuevo)}
              </div>
            </div>
          </div>

          <div className="mb-4">
            <label className="label">Concepto</label>
            <input
              className="input"
              value={form.texto}
              onChange={(e) => setForm({ ...form, texto: e.target.value })}
            />
          </div>

          {/* Líneas */}
          <div className="border-t pt-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <h3 className="text-sm font-semibold text-gray-700">Líneas</h3>
                {pagos.length > 0 && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    cuadrado
                      ? 'bg-green-100 text-green-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {cuadrado ? '✓ Cuadrado' : `Dif. ${EUR(totalNum - sumLineas)}`}
                  </span>
                )}
                {pagos.length > 0 && !cuadrado && (
                  <div className="relative" ref={cuadrarRef}>
                    <button className="btn btn-secondary text-xs flex items-center gap-1"
                      onClick={() => setMenuCuadrar((v) => !v)}>
                      Cuadrar <span className="text-xs">▾</span>
                    </button>
                    {menuCuadrar && (
                      <div className="absolute left-0 top-full mt-1 bg-white rounded-lg shadow-lg border border-gray-200 z-20 min-w-64 py-1">
                        <button
                          className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                          onClick={() => { anadirLineaAjuste(); setMenuCuadrar(false) }}>
                          Añadir línea de ajuste ({EUR(totalNum - sumLineas)})
                        </button>
                        <button
                          className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                          onClick={() => { ajustarTotalASuma(); setMenuCuadrar(false) }}>
                          Ajustar el Total a la suma de líneas
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div className="relative" ref={menuRef}>
                <button
                  className="btn btn-secondary text-xs"
                  onClick={() => { setMenuAnadir((v) => !v); setMenuIndice(-1) }}
                  onKeyDown={(e) => {
                    const opciones = [
                      () => { setMostrarVtos(true); setMenuAnadir(false); setMenuIndice(-1) },
                      () => { addDirectoSubcuenta(); setMenuIndice(-1) },
                      () => { addOtroBanco(); setMenuIndice(-1) },
                    ]
                    if (e.key === 'ArrowDown') {
                      e.preventDefault()
                      if (!menuAnadir) { setMenuAnadir(true); setMenuIndice(0) }
                      else setMenuIndice((i) => (i + 1) % opciones.length)
                    } else if (e.key === 'ArrowUp') {
                      e.preventDefault()
                      if (!menuAnadir) { setMenuAnadir(true); setMenuIndice(opciones.length - 1) }
                      else setMenuIndice((i) => (i - 1 + opciones.length) % opciones.length)
                    } else if (e.key === 'Enter' && menuAnadir && menuIndice >= 0) {
                      e.preventDefault()
                      opciones[menuIndice]()
                    } else if (e.key === 'Escape') {
                      setMenuAnadir(false); setMenuIndice(-1)
                    }
                  }}
                >
                  + Añadir ▾
                </button>
                {menuAnadir && (
                  <div className="absolute right-0 top-full mt-1 bg-white rounded-lg shadow-lg border border-gray-200 z-20 min-w-48 py-1">
                    {[
                      { label: 'Vtos. pendientes',     accion: () => { setMostrarVtos(true); setMenuAnadir(false); setMenuIndice(-1) } },
                      { label: 'Directo a subcuenta',  accion: addDirectoSubcuenta },
                      { label: 'Otro banco',           accion: () => { addOtroBanco(); setMenuIndice(-1) } },
                    ].map(({ label, accion }, idx) => (
                      <button
                        key={idx}
                        className={`w-full text-left px-4 py-2 text-sm ${menuIndice === idx ? 'bg-mgd-50 text-mgd-700 font-medium' : 'hover:bg-gray-50'}`}
                        onMouseEnter={() => setMenuIndice(idx)}
                        onClick={accion}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-400 uppercase border-b border-gray-100">
                  <th className="text-left pb-2 pl-2 w-24">Tipo</th>
                  <th className="text-right pb-2 w-24">Cobro</th>
                  <th className="text-right pb-2 w-24">Pago</th>
                  <th className="text-right pb-2 pr-2 w-16">Número</th>
                  <th className="text-left pb-2 pl-2">Descripción</th>
                  <th className="text-left pb-2 pl-2 w-24">Fecha</th>
                  <th className="pb-2 w-6"></th>
                </tr>
              </thead>
              <tbody>
                {pagos.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-5 text-center text-gray-400 text-xs">
                      Sin líneas — usa "Añadir" para agregar vencimientos o cuentas directas
                    </td>
                  </tr>
                )}
                {pagos.map((p, i) => {
                  const imp = parseFloat(p.importe)
                  const cobro = (!isNaN(imp) && imp > 0) ? imp : ''
                  const pago  = (!isNaN(imp) && imp < 0) ? -imp : ''
                  const tipoLabel = p._tipo === 'B' ? 'Tr. Banco'
                    : p._tipo === 'D' ? 'Directo'
                    : p.vto_tipo === 'R' ? 'Recibida'
                    : p.vto_tipo === 'F' ? 'Enviada'
                    : p.vto_tipo === 'X' ? 'Extra'
                    : p.vto_tipo === 'N' ? 'Paga NNA'
                    : 'Vto.'
                  const tipoBadge = p._tipo === 'B' ? 'bg-blue-100 text-blue-700'
                    : p._tipo === 'D' ? 'bg-gray-100 text-gray-600'
                    : p.vto_tipo === 'R' ? 'bg-red-100 text-red-700'
                    : p.vto_tipo === 'F' ? 'bg-green-100 text-green-700'
                    : p.vto_tipo === 'X' ? 'bg-purple-100 text-purple-700'
                    : p.vto_tipo === 'N' ? 'bg-yellow-100 text-yellow-700'
                    : 'bg-gray-100 text-gray-500'
                  const numero = p._tipo === 'B' ? (p.bancot ?? '') : (p.vto_tpnumero ?? '')
                  const fecha = p.doc_fecha ? fmtFecha(String(p.doc_fecha)) : ''
                  return (
                    <tr key={i} className="border-b border-gray-50 last:border-0">
                      <td className="py-1.5 px-2">
                        <div className="flex items-center gap-1">
                          <span className={`text-xs px-1.5 py-0.5 rounded font-medium whitespace-nowrap ${tipoBadge}`}>
                            {tipoLabel}
                          </span>
                          {p._tipo === 'V' && p.vto_existe === false && (
                            <span
                              className="text-amber-500 text-xs font-bold"
                              title={`Vencimiento nº ${p.vto} no encontrado — el extra o factura puede haber sido eliminado y recreado`}
                            >
                              ⚠
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-1.5 pr-1">
                        <input
                          type="number" step="0.01" min="0"
                          className="input text-sm text-right"
                          placeholder="—"
                          value={cobro}
                          onChange={(e) => setPagoCobro(i, e.target.value)}
                        />
                      </td>
                      <td className="py-1.5 pr-1">
                        <input
                          type="number" step="0.01" min="0"
                          className="input text-sm text-right"
                          placeholder="—"
                          value={pago}
                          onChange={(e) => setPagoPago(i, e.target.value)}
                        />
                      </td>
                      <td className="py-1.5 pr-2 text-right text-xs font-mono text-gray-500">
                        {numero}
                      </td>
                      <td className="py-1.5 px-2">
                        {p._tipo === 'V' && (
                          <div className="flex flex-col gap-0.5">
                            {(p.doc_numero_externo || p.doc_entidad_nombre) ? (
                              <>
                                {p.doc_numero_externo && (
                                  <span className="text-xs font-mono text-gray-700">{p.doc_numero_externo}</span>
                                )}
                                {p.doc_entidad_nombre && (
                                  <span className="text-xs text-gray-500">{p.doc_entidad_nombre}</span>
                                )}
                              </>
                            ) : (
                              p._desc && <span className="text-xs text-gray-400">{p._desc}</span>
                            )}
                          </div>
                        )}
                        {p._tipo === 'B' && (
                          <select
                            className="input text-sm w-full"
                            value={p.bancot ?? ''}
                            onChange={(e) => {
                              const num = parseInt(e.target.value) || null
                              const b = bancos.find((b) => b.numero === num)
                              const arr = [...pagos]
                              arr[i] = { ...arr[i], bancot: num, dirsubcta: b?.cuenta || null, bancot_nombre: b?.nombre || null }
                              setPagos(arr)
                            }}
                          >
                            <option value="">— Seleccionar banco —</option>
                            {bancos
                              .filter((b) => String(b.numero) !== String(form.banco))
                              .map((b) => <option key={b.id} value={b.numero}>{b.nombre}</option>)
                            }
                          </select>
                        )}
                        {p._tipo === 'D' && (
                          <div className="flex flex-col gap-0.5">
                            <AutocompleteCuenta
                              empresaId={empresa?.id}
                              className="text-sm w-full"
                              placeholder="Cuenta contable"
                              value={p.dirsubcta || ''}
                              onChange={(v) => setPagoField(i, 'dirsubcta', v)}
                              onSelect={(c) => setCuentaNombres((prev) => ({ ...prev, [c.cuenta]: c.texto }))}
                              onBlur={(e) => {
                                const cod = e.target.value.trim()
                                if (cod && empresa?.id) resolverNombreCuenta(cod, empresa.id)
                              }}
                            />
                            {p.dirsubcta && cuentaNombres[p.dirsubcta] && (
                              <span className="text-xs text-gray-400 truncate">
                                {cuentaNombres[p.dirsubcta]}
                              </span>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="py-1.5 px-2 text-xs text-gray-500 whitespace-nowrap">
                        {fecha}
                      </td>
                      <td className="py-1.5 pl-1">
                        <button
                          className="text-red-400 hover:text-red-600 px-1"
                          onClick={() => removePago(i)}
                        >✕</button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-4">
            <label className="label">Observaciones</label>
            <input
              className="input"
              value={form.notas}
              onChange={(e) => setForm({ ...form, notas: e.target.value })}
            />
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancelar</button>
            <button className="btn btn-primary" disabled={guardando} onClick={guardar}>
              {guardando ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </Modal>
      )}

      {/* Selector de vencimientos — se monta encima del modal de movimiento */}
      {mostrarVtos && empresa && (
        <VtosSelector
          empresaId={empresa.id}
          onSelect={seleccionarVto}
          onClose={() => setMostrarVtos(false)}
        />
      )}
      </div>
    </div>
  )
}
