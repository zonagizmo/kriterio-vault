// FE-001: `window.open` no envía el header Authorization → 401 en los exports
// y en la descarga de backups. Se descarga con `fetch` + Bearer y se guarda el
// blob con un <a download> (el Content-Disposition del backend da el nombre).
import { getToken } from './auth'

export async function descargar(url, nombrePorDefecto) {
  const token = getToken()
  const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!res.ok) {
    let detalle = `Error ${res.status}`
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') detalle = body.detail
    } catch {
      /* respuesta sin JSON */
    }
    throw new Error(detalle)
  }
  const blob = await res.blob()
  const cd = res.headers.get('Content-Disposition') || ''
  const match = /filename="?([^";]+)"?/i.exec(cd)
  const nombre = match ? decodeURIComponent(match[1]) : nombrePorDefecto
  const href = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = href
  a.download = nombre
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(href)
}

/** Descarga con token; avisa con alert si falla (patrón de la app). */
export function descargarOVisar(url, nombrePorDefecto) {
  return descargar(url, nombrePorDefecto).catch((e) => {
    alert(e.message || 'Error al descargar')
  })
}
