import { useState, useEffect, useCallback } from 'react'

/**
 * Hook genérico para páginas CRUD con tabla + paginación + modal de edición.
 *
 * @param {Object} opts
 * @param {Object} opts.service  — { getAll, create, update, delete }
 * @param {number} opts.empresaId
 * @param {Object} opts.emptyForm — plantilla del formulario vacío
 * @param {string} [opts.entityName='registro'] — nombre para confirmación de eliminación
 * @param {number} [opts.defaultLimit=50]
 * @param {Function} [opts.extraParams] — () => Object, parámetros adicionales para getAll
 * @param {Array} [opts.extraDeps] — dependencias adicionales para recargar
 *
 * @returns {Object} estado y operaciones del CRUD
 */
export default function useCrud({
  service,
  empresaId,
  emptyForm,
  entityName = 'registro',
  defaultLimit = 50,
  extraParams,
  extraDeps = [],
}) {
  const [datos, setDatos] = useState({ total: 0, items: [] })
  const [q, setQ] = useState('')
  const [skip, setSkip] = useState(0)
  const [limit, setLimit] = useState(defaultLimit)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [editId, setEditId] = useState(null)
  const [guardando, setGuardando] = useState(false)

  const cargar = useCallback(async () => {
    if (!empresaId) return
    setCargando(true)
    setError(null)
    try {
      const params = { q, skip, limit, ...(extraParams ? extraParams() : {}) }
      const res = await service.getAll(empresaId, params)
      setDatos(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }, [service, empresaId, q, skip, limit, ...extraDeps])

  useEffect(() => {
    cargar()
  }, [cargar])
  useEffect(() => {
    setSkip(0)
  }, [q, empresaId, ...extraDeps])

  const abrirNuevo = () => {
    setForm(emptyForm)
    setEditId(null)
    setModal('editar')
  }

  const abrirEditar = (item) => {
    setForm({ ...emptyForm, ...item })
    setEditId(item.id)
    setModal('editar')
  }

  const cerrar = () => {
    setModal(null)
    setError(null)
  }

  const guardar = async (e) => {
    e.preventDefault()
    setGuardando(true)
    setError(null)
    try {
      if (editId) {
        await service.update(editId, form)
      } else {
        await service.create({ ...form, empresa_id: empresaId })
      }
      cerrar()
      cargar()
    } catch (err) {
      setError(err.message)
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async (id, nombre) => {
    if (!confirm(`¿Eliminar ${entityName} "${nombre}"?`)) return
    try {
      await service.delete(id)
      cargar()
    } catch (e) {
      alert(e.message)
    }
  }

  return {
    datos,
    setDatos,
    q,
    setQ,
    skip,
    setSkip,
    limit,
    setLimit,
    cargando,
    error,
    setError,
    modal,
    setModal,
    form,
    setForm,
    editId,
    guardando,
    cargar,
    abrirNuevo,
    abrirEditar,
    cerrar,
    guardar,
    eliminar,
  }
}
