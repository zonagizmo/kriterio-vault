import axios from 'axios'

const BASE = '/api/ajustes'

export const getBackups = () =>
  axios.get(`${BASE}/backups`).then((r) => r.data)

export const crearBackup = () =>
  axios.post(`${BASE}/backup`).then((r) => r.data)

export const eliminarBackup = (nombre) =>
  axios.delete(`${BASE}/backup/${encodeURIComponent(nombre)}`)

export const descargarBackup = (nombre) => {
  window.open(`${BASE}/backup/download/${encodeURIComponent(nombre)}`, '_blank')
}

export const restaurarBackup = (archivo) => {
  const form = new FormData()
  form.append('archivo', archivo)
  return axios.post(`${BASE}/restaurar`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const actualizarConfig = (hora, dias) =>
  axios.put(`${BASE}/config`, { hora, dias }).then((r) => r.data)

export const restaurarBackupExistente = (nombre) =>
  axios.post(`${BASE}/restaurar-backup/${encodeURIComponent(nombre)}`).then((r) => r.data)
