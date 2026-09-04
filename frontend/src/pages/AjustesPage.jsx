import { useEffect, useRef, useState } from 'react'
import { getBackups, crearBackup, eliminarBackup, descargarBackup, restaurarBackup, actualizarConfig, restaurarBackupExistente } from '../services/ajustes'
import { getEmpresa, actualizarEmpresa } from '../services/empresas'
import { useEmpresa } from '../hooks/useEmpresa.jsx'

const FMT_BYTES = (b) => {
  if (b >= 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)} MB`
  if (b >= 1024)        return `${(b / 1024).toFixed(0)} KB`
  return `${b} B`
}
const FMT_DT = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })
}

const DIAS_SEMANA = [
  { id: 0, label: 'Lun' },
  { id: 1, label: 'Mar' },
  { id: 2, label: 'Mié' },
  { id: 3, label: 'Jue' },
  { id: 4, label: 'Vie' },
  { id: 5, label: 'Sáb' },
  { id: 6, label: 'Dom' },
]

function FichaEmpresa() {
  const { empresa, setEmpresa } = useEmpresa()
  const [form,       setForm]       = useState(null)
  const [cargando,   setCargando]   = useState(true)
  const [guardando,  setGuardando]  = useState(false)
  const [msg,        setMsg]        = useState(null)

  useEffect(() => {
    if (!empresa) return
    setCargando(true)
    getEmpresa(empresa.id)
      .then(setForm)
      .catch(() => setMsg({ tipo: 'error', texto: 'Error al cargar los datos de la empresa' }))
      .finally(() => setCargando(false))
  }, [empresa?.id])

  const campo = (key, valor) => setForm((f) => ({ ...f, [key]: valor }))

  const guardar = async () => {
    if (!form.nombre?.trim()) {
      setMsg({ tipo: 'error', texto: 'El nombre es obligatorio' })
      return
    }
    setGuardando(true)
    setMsg(null)
    try {
      const actualizada = await actualizarEmpresa(empresa.id, {
        nombre: form.nombre,
        nif: form.nif || null,
        domicilio: form.domicilio || null,
        localidad: form.localidad || null,
        provincia: form.provincia || null,
        cod_postal: form.cod_postal || null,
        telefono: form.telefono || null,
        email: form.email || null,
      })
      setForm(actualizada)
      setEmpresa((prev) => ({ ...prev, nombre: actualizada.nombre }))
      setMsg({ tipo: 'ok', texto: 'Datos guardados correctamente' })
    } catch {
      setMsg({ tipo: 'error', texto: 'Error al guardar los datos' })
    } finally {
      setGuardando(false)
    }
  }

  if (!empresa) {
    return <p className="text-sm text-gray-400 px-6 py-4">Selecciona una empresa.</p>
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-base font-semibold text-gray-800">Datos de la empresa</h2>
        <p className="text-xs text-gray-500 mt-0.5">Código {empresa.codigo}</p>
      </div>

      {cargando || !form ? (
        <p className="text-sm text-gray-400 px-6 py-4">Cargando…</p>
      ) : (
        <div className="px-6 py-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="label">Nombre *</label>
              <input className="input" value={form.nombre || ''} onChange={(e) => campo('nombre', e.target.value)} />
            </div>
            <div>
              <label className="label">NIF/CIF</label>
              <input className="input" value={form.nif || ''} onChange={(e) => campo('nif', e.target.value)} />
            </div>
            <div>
              <label className="label">Teléfono</label>
              <input className="input" value={form.telefono || ''} onChange={(e) => campo('telefono', e.target.value)} />
            </div>
            <div className="col-span-2">
              <label className="label">Email</label>
              <input type="email" className="input" value={form.email || ''} onChange={(e) => campo('email', e.target.value)} />
            </div>
            <div className="col-span-2">
              <label className="label">Domicilio</label>
              <input className="input" value={form.domicilio || ''} onChange={(e) => campo('domicilio', e.target.value)} />
            </div>
            <div>
              <label className="label">Localidad</label>
              <input className="input" value={form.localidad || ''} onChange={(e) => campo('localidad', e.target.value)} />
            </div>
            <div>
              <label className="label">Provincia</label>
              <input className="input" value={form.provincia || ''} onChange={(e) => campo('provincia', e.target.value)} />
            </div>
            <div>
              <label className="label">Código postal</label>
              <input className="input" value={form.cod_postal || ''} onChange={(e) => campo('cod_postal', e.target.value)} />
            </div>
          </div>

          {msg && (
            <div className={`px-4 py-2.5 rounded-lg text-sm ${
              msg.tipo === 'ok'
                ? 'bg-green-50 text-green-700 border border-green-200'
                : 'bg-red-50 text-red-700 border border-red-200'
            }`}>
              {msg.texto}
            </div>
          )}

          <button className="btn btn-primary text-sm" onClick={guardar} disabled={guardando}>
            {guardando ? 'Guardando…' : 'Guardar datos'}
          </button>
        </div>
      )}
    </div>
  )
}

const TABS = [
  { id: 'empresa', label: 'Empresa' },
  { id: 'backups', label: 'Copias de seguridad' },
]

export default function AjustesPage() {
  const [tab, setTab] = useState('empresa')
  const [backups,        setBackups]        = useState([])
  const [config,         setConfig]         = useState({ hora: '02:00', dias: [0,1,2,3,4,5,6], retencion_dias: 30 })
  const [editHora,       setEditHora]       = useState('02:00')
  const [editDias,       setEditDias]       = useState([0,1,2,3,4,5,6])
  const [cargando,       setCargando]       = useState(true)
  const [haciendoBck,    setHaciendoBck]    = useState(false)
  const [guardandoCfg,   setGuardandoCfg]   = useState(false)
  const [eliminando,     setEliminando]     = useState(null)
  const [restaurandoBck, setRestaurandoBck] = useState(null)
  const [msg,            setMsg]            = useState(null)
  const [msgCfg,         setMsgCfg]         = useState(null)
  const [archivoRest,    setArchivoRest]    = useState(null)
  const [restaurando,    setRestaurando]    = useState(false)
  const inputFileRef = useRef(null)

  const cargar = () => {
    setCargando(true)
    getBackups()
      .then(({ backups: b, hora, dias, retencion_dias }) => {
        setBackups(b)
        const cfg = { hora: hora || '02:00', dias: dias || [0,1,2,3,4,5,6], retencion_dias }
        setConfig(cfg)
        setEditHora(cfg.hora)
        setEditDias(cfg.dias)
      })
      .catch(() => setMsg({ tipo: 'error', texto: 'Error al cargar la lista de backups' }))
      .finally(() => setCargando(false))
  }

  useEffect(() => { cargar() }, [])

  const handleBackup = async () => {
    setHaciendoBck(true)
    setMsg(null)
    try {
      const res = await crearBackup()
      setMsg({ tipo: 'ok', texto: `Backup creado: ${res.backup.nombre} (${FMT_BYTES(res.backup.tamanio)})` })
      cargar()
    } catch {
      setMsg({ tipo: 'error', texto: 'Error al crear el backup' })
    } finally {
      setHaciendoBck(false)
    }
  }

  const handleRestaurarBck = async (nombre) => {
    if (!confirm(
      `¿Restaurar la base de datos con el backup "${nombre}"?\n\n` +
      `Se creará un backup de seguridad de la BD actual antes de reemplazarla.`
    )) return
    setRestaurandoBck(nombre)
    setMsg(null)
    try {
      const res = await restaurarBackupExistente(nombre)
      setMsg({
        tipo: 'ok',
        texto: `BD restaurada correctamente desde ${nombre}. Backup de seguridad: ${res.safety_backup}. Recarga la página para ver los datos actualizados.`,
      })
      cargar()
    } catch (e) {
      const detalle = e?.response?.data?.detail || 'Error al restaurar el backup'
      setMsg({ tipo: 'error', texto: detalle })
    } finally {
      setRestaurandoBck(null)
    }
  }

  const handleEliminar = async (nombre) => {
    if (!confirm(`¿Eliminar el backup ${nombre}?`)) return
    setEliminando(nombre)
    try {
      await eliminarBackup(nombre)
      cargar()
    } catch {
      setMsg({ tipo: 'error', texto: 'Error al eliminar el backup' })
    } finally {
      setEliminando(null)
    }
  }

  const toggleDia = (id) => {
    setEditDias((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id].sort((a, b) => a - b)
    )
  }

  const handleGuardarConfig = async () => {
    if (editDias.length === 0) {
      setMsgCfg({ tipo: 'error', texto: 'Selecciona al menos un día' })
      return
    }
    setGuardandoCfg(true)
    setMsgCfg(null)
    try {
      await actualizarConfig(editHora, editDias)
      setConfig((prev) => ({ ...prev, hora: editHora, dias: editDias }))
      const etiqDias = editDias.map((d) => DIAS_SEMANA[d].label).join(', ')
      setMsgCfg({ tipo: 'ok', texto: `Programación guardada: ${etiqDias} a las ${editHora}` })
    } catch {
      setMsgCfg({ tipo: 'error', texto: 'Error al guardar la configuración' })
    } finally {
      setGuardandoCfg(false)
    }
  }

  const handleRestaurar = async () => {
    if (!archivoRest) return
    if (!confirm(
      `¿Restaurar la base de datos con el archivo "${archivoRest.name}"?\n\n` +
      `Se creará un backup de seguridad de la BD actual antes de reemplazarla.`
    )) return
    setRestaurando(true)
    setMsg(null)
    try {
      const res = await restaurarBackup(archivoRest)
      setArchivoRest(null)
      if (inputFileRef.current) inputFileRef.current.value = ''
      setMsg({
        tipo: 'ok',
        texto: `BD restaurada correctamente. Backup de seguridad guardado: ${res.safety_backup}. Recarga la página para ver los datos actualizados.`,
      })
      cargar()
    } catch (e) {
      const detalle = e?.response?.data?.detail || 'Error al restaurar el backup'
      setMsg({ tipo: 'error', texto: detalle })
    } finally {
      setRestaurando(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Ajustes</h1>

      {/* ── Pestañas ───────────────────────────────────────────── */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t.id
                ? 'border-mgd-600 text-mgd-700'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'empresa' && <FichaEmpresa />}

      {tab === 'backups' && (
      <>
      {/* ── Card programación ─────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-800">Programación del backup automático</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Actualmente: {config.dias.map((d) => DIAS_SEMANA[d].label).join(', ')} a las {config.hora} · Retención {config.retencion_dias} días
          </p>
        </div>
        <div className="px-6 py-5 space-y-4">
          {/* Días */}
          <div>
            <p className="text-xs font-medium text-gray-600 mb-2">Días de la semana</p>
            <div className="flex gap-2 flex-wrap">
              {DIAS_SEMANA.map(({ id, label }) => {
                const activo = editDias.includes(id)
                return (
                  <button
                    key={id}
                    onClick={() => toggleDia(id)}
                    className={`w-12 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                      activo
                        ? 'bg-mgd-600 text-white border-mgd-600'
                        : 'bg-white text-gray-500 border-gray-200 hover:border-mgd-400 hover:text-mgd-600'
                    }`}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
          </div>
          {/* Hora */}
          <div>
            <p className="text-xs font-medium text-gray-600 mb-2">Hora</p>
            <input
              type="time"
              value={editHora}
              onChange={(e) => setEditHora(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-mgd-400"
            />
          </div>
          {/* Mensaje config */}
          {msgCfg && (
            <div className={`px-4 py-2.5 rounded-lg text-sm ${
              msgCfg.tipo === 'ok'
                ? 'bg-green-50 text-green-700 border border-green-200'
                : 'bg-red-50 text-red-700 border border-red-200'
            }`}>
              {msgCfg.texto}
            </div>
          )}
          <button
            className="btn btn-primary text-sm"
            onClick={handleGuardarConfig}
            disabled={guardandoCfg}
          >
            {guardandoCfg ? 'Guardando…' : 'Guardar programación'}
          </button>
        </div>
      </div>

      {/* ── Card backup ───────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-800">Copias de seguridad</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Backup automático: {config.dias.map((d) => DIAS_SEMANA[d].label).join(', ')} a las {config.hora}
            </p>
          </div>
          <button
            className="btn btn-primary text-sm"
            onClick={handleBackup}
            disabled={haciendoBck}
          >
            {haciendoBck ? 'Creando…' : '⬇ Hacer backup ahora'}
          </button>
        </div>

        {/* Mensaje feedback */}
        {msg && (
          <div className={`mx-6 mt-4 px-4 py-2.5 rounded-lg text-sm ${
            msg.tipo === 'ok'
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}>
            {msg.texto}
          </div>
        )}

        {/* Lista de backups */}
        <div className="px-6 py-4">
          {cargando ? (
            <p className="text-sm text-gray-400">Cargando…</p>
          ) : backups.length === 0 ? (
            <p className="text-sm text-gray-400">No hay backups todavía. El primero se creará automáticamente a las {config.hora}.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                  <th className="pb-2 font-medium">Fecha</th>
                  <th className="pb-2 font-medium">Archivo</th>
                  <th className="pb-2 font-medium text-right">Tamaño</th>
                  <th className="pb-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {backups.map((b) => (
                  <tr key={b.nombre} className="hover:bg-gray-50">
                    <td className="py-2 pr-4 text-gray-700 whitespace-nowrap">{FMT_DT(b.fecha)}</td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-500 truncate max-w-xs">{b.nombre}</td>
                    <td className="py-2 pr-4 text-right text-gray-500 whitespace-nowrap">{FMT_BYTES(b.tamanio)}</td>
                    <td className="py-2 flex items-center gap-2 justify-end">
                      <button
                        className="text-xs text-mgd-600 hover:text-mgd-800 font-medium"
                        onClick={() => descargarBackup(b.nombre)}
                      >
                        Descargar
                      </button>
                      <button
                        className="text-xs text-amber-600 hover:text-amber-800 font-medium"
                        onClick={() => handleRestaurarBck(b.nombre)}
                        disabled={restaurandoBck === b.nombre}
                      >
                        {restaurandoBck === b.nombre ? '…' : 'Restaurar'}
                      </button>
                      <button
                        className="text-xs text-red-500 hover:text-red-700 font-medium"
                        onClick={() => handleEliminar(b.nombre)}
                        disabled={eliminando === b.nombre}
                      >
                        {eliminando === b.nombre ? '…' : 'Eliminar'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      {/* ── Card restaurar ────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-800">Restaurar copia de seguridad</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Carga un archivo <span className="font-mono">.db</span> para reemplazar la base de datos actual.
            Se creará un backup de seguridad automático antes de restaurar.
          </p>
        </div>
        <div className="px-6 py-4 space-y-3">
          <div className="flex items-center gap-3">
            <input
              ref={inputFileRef}
              type="file"
              accept=".db"
              className="hidden"
              onChange={(e) => setArchivoRest(e.target.files?.[0] || null)}
            />
            <button
              className="btn btn-secondary text-sm"
              onClick={() => inputFileRef.current?.click()}
            >
              Seleccionar archivo…
            </button>
            {archivoRest && (
              <span className="text-sm text-gray-700 font-mono truncate max-w-xs">
                {archivoRest.name}
                <span className="text-gray-400 ml-2">({FMT_BYTES(archivoRest.size)})</span>
              </span>
            )}
          </div>

          {archivoRest && (
            <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <span className="text-amber-500 text-lg leading-none mt-0.5">⚠</span>
              <div className="flex-1 text-xs text-amber-800">
                Esta acción reemplazará <strong>toda la base de datos actual</strong>.
                Se guardará un backup de seguridad automáticamente antes de proceder.
              </div>
              <button
                className="btn text-sm bg-amber-600 hover:bg-amber-700 text-white shrink-0"
                onClick={handleRestaurar}
                disabled={restaurando}
              >
                {restaurando ? 'Restaurando…' : 'Restaurar'}
              </button>
            </div>
          )}
        </div>
      </div>
      </>
      )}
    </div>
  )
}
