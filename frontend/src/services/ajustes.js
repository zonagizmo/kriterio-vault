import api from './api'
import { descargarOVisar } from './descargas'

const BASE = '/ajustes'

export const getBackups = () => api.get(`${BASE}/backups`).then((r) => r.data)

export const crearBackup = () => api.post(`${BASE}/backup`).then((r) => r.data)

export const eliminarBackup = (nombre) => api.delete(`${BASE}/backup/${encodeURIComponent(nombre)}`)

export const descargarBackup = (nombre) =>
  descargarOVisar(`/api${BASE}/backup/download/${encodeURIComponent(nombre)}`, nombre)

export const restaurarBackup = (archivo) => {
  const form = new FormData()
  form.append('archivo', archivo)
  return api
    .post(`${BASE}/restaurar`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data)
}

export const actualizarConfig = (hora, dias) => api.put(`${BASE}/config`, { hora, dias }).then((r) => r.data)

export const restaurarBackupExistente = (nombre) =>
  api.post(`${BASE}/restaurar-backup/${encodeURIComponent(nombre)}`).then((r) => r.data)
