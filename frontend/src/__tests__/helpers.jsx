/**
 * Utilidades compartidas de los tests de frontend.
 *
 * En lugar de mockear los services (uno por uno), se sustituye el *adapter*
 * del cliente axios real (`services/api.js`): así también se ejercitan los
 * interceptores de Authorization/401 y todas las capas intermedias.
 */
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../hooks/useAuth.jsx'
import { EmpresaProvider } from '../hooks/useEmpresa.jsx'
import api from '../services/api'

export const EMPRESA = { id: 1, nombre: 'Empresa 1', codigo: 'E1' }

/** Registro de peticiones (método, url, params, body) para aserciones. */
export const apiCalls = []

let rutas = []
let fallbackData = { total: 0, items: [] }

const RUTAS_POR_DEFECTO = [
  { method: 'GET', path: '/empresas', data: [] },
  { method: 'GET', path: '/estadisticas/anios', data: { anios: [] } },
  { method: 'GET', path: '/estadisticas', data: {} },
  {
    method: 'GET',
    path: '/estadisticas/periodo',
    data: {
      fecha_desde: '',
      fecha_hasta: '',
      ingresos_total: 0,
      gastos_total: 0,
      resultado: 0,
      categorias_ingreso: [],
      categorias_gasto: [],
    },
  },
  { method: 'GET', path: '/estadisticas/periodo/ingresos', data: { items: [] } },
  { method: 'GET', path: '/estadisticas/periodo/gastos', data: { items: [] } },
  { method: 'GET', path: '/bancos', data: [] },
  { method: 'GET', path: '/familias', data: [] },
  { method: 'GET', path: '/usuarios/pagas/anios', data: { anios: [] } },
  { method: 'GET', path: '/usuarios/saldos', data: {} },
  { method: 'GET', path: '/usuarios/pagas', data: { total: 0, items: [] } },
  { method: 'GET', path: '/usuarios/pagas/resumen', data: [] },
  { method: 'GET', path: '/usuarios/activos-con-paga', data: [] },
  {
    method: 'GET',
    path: '/contabilidad/sumas-saldos',
    data: { filas: [], total_debe: 0, total_haber: 0, total_saldo_deudor: 0, total_saldo_acreedor: 0 },
  },
  {
    method: 'GET',
    path: '/contabilidad/pyg',
    data: {
      ingresos: [],
      total_ingresos: 0,
      gastos: [],
      total_gastos: 0,
      saldo_inicial_bancos: 0,
      resultado: 0,
      resultado_con_saldo_inicial: 0,
    },
  },
  {
    method: 'GET',
    path: '/contabilidad/balance',
    data: {
      activo_no_corriente: [],
      total_anc: 0,
      activo_corriente: [],
      total_ac: 0,
      total_activo: 0,
      patrimonio_neto: [],
      total_pn: 0,
      pasivo_no_corriente: [],
      total_pnc: 0,
      pasivo_corriente: [],
      total_pc: 0,
      total_pasivo_pn: 0,
    },
  },
  { method: 'GET', path: '/contabilidad/conciliacion-bancos', data: [] },
  {
    method: 'GET',
    path: '/contabilidad/diagnostico',
    data: { total_problemas: 0, extras_sin_asiento: [], movimientos_sin_asiento: [], cuentas_desequilibradas: [] },
  },
  { method: 'GET', path: '/contabilidad/mayor', data: { total: 0, saldo_anterior: 0, items: [] } },
  { method: 'GET', path: '/contabilidad/diario', data: { total: 0, saldo_anterior: 0, items: [] } },
  { method: 'GET', path: '/contabilidad/cuentas', data: { total: 0, items: [] } },
  { method: 'GET', path: '/contabilidad/asientos', data: { total: 0, items: [] } },
  {
    method: 'GET',
    path: '/ajustes/backups',
    data: { backups: [], hora: '02:00', dias: [0, 1, 2, 3, 4, 5, 6], retencion_dias: 30 },
  },
  {
    method: 'GET',
    path: '/dashboard',
    data: {
      bancos: [],
      total_bancos: 0,
      cobrar_pendiente: 0,
      pagar_pendiente: 0,
      mes_nombre: 'Enero',
      ingresos_mes: 0,
      ingresos_mes_anterior: 0,
      gastos_mes: 0,
      gastos_mes_anterior: 0,
      vencimientos_vencidos: 0,
      vencimientos_proximos: [],
    },
  },
]

function coincide(path, url) {
  if (path instanceof RegExp) return path.test(url)
  if (typeof path === 'string' && path.endsWith('*')) return url.startsWith(path.slice(0, -1))
  return url === path
}

async function adapter(config) {
  const method = (config.method || 'get').toUpperCase()
  const url = config.url || ''
  let body = null
  if (typeof config.data === 'string') {
    try {
      body = JSON.parse(config.data)
    } catch {
      body = config.data
    }
  } else body = config.data
  apiCalls.push({ method, url, params: config.params, data: body })

  const ruta = rutas.find((r) => (r.method === undefined || r.method === method) && coincide(r.path, url))
  const status = ruta?.status ?? 200
  let data = ruta ? ruta.data : fallbackData
  if (typeof data === 'function') data = data(config)
  const response = { data, status, statusText: status < 400 ? 'OK' : 'Error', headers: {}, config }
  if (status >= 400) {
    const err = new Error(`Request failed with status code ${status}`)
    err.response = response
    err.config = config
    err.isAxiosError = true
    throw err
  }
  return response
}

/**
 * Instala el adapter falso con rutas personalizadas.
 * `rutasNuevas` tiene prioridad sobre las de por defecto.
 * Formato: `{ method?, path (string exacto | string con '*' final | RegExp), data | (config)=>data, status? }`
 */
export function mockApi(rutasNuevas = [], fallback = { total: 0, items: [] }) {
  rutas = [...rutasNuevas, ...RUTAS_POR_DEFECTO]
  fallbackData = fallback
  apiCalls.length = 0
  api.defaults.adapter = adapter
}

/** Establece la sesión (token + usuario + empresa activa) en localStorage. */
export function setSession({ rol = 'admin', empresa = EMPRESA, username = 'tester' } = {}) {
  localStorage.setItem('kriterio_token', 'tk-test')
  localStorage.setItem(
    'kriterio_user',
    JSON.stringify({ id: 1, username, nombre: 'Tester', rol, empresa_id: empresa?.id ?? null }),
  )
  if (empresa) localStorage.setItem('empresa_activa', JSON.stringify(empresa))
  else localStorage.removeItem('empresa_activa')
}

/** Renderiza un árbol con AuthProvider + EmpresaProvider + Router. */
export function renderWithProviders(ui, { path = '/', rol = 'admin', empresa = EMPRESA } = {}) {
  setSession({ rol, empresa })
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <EmpresaProvider>{ui}</EmpresaProvider>
      </AuthProvider>
    </MemoryRouter>,
  )
}
