/** Páginas de bancos: listado de cuentas y movimientos por banco. */
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from '../hooks/useAuth.jsx'
import { EmpresaProvider } from '../hooks/useEmpresa.jsx'
import BancosPage from '../pages/BancosPage'
import MovimientosBancoPage from '../pages/MovimientosBancoPage'
import { mockApi, apiCalls, setSession, EMPRESA } from './helpers.jsx'

const BANCOS = [
  { id: 1, numero: 1, nombre: 'BBVA', empresa_id: 1, saldoini: 100, saldoact: 1500 },
  { id: 2, numero: 2, nombre: 'Santander', empresa_id: 1, saldoini: 0, saldoact: -200 },
]

function envoltura(ui, { rol = 'admin' } = {}) {
  setSession({ rol, empresa: EMPRESA })
  return render(
    <MemoryRouter initialEntries={['/bancos']}>
      <AuthProvider>
        <EmpresaProvider>{ui}</EmpresaProvider>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('BancosPage', () => {
  it('admin: encabezado, cuentas listadas y Nueva cuenta', async () => {
    mockApi([{ path: '/bancos', data: BANCOS }])
    envoltura(<BancosPage />)
    expect(screen.getByRole('heading', { name: 'Bancos y Tesorería' })).toBeInTheDocument()
    expect((await screen.findAllByText('BBVA')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Santander').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: '+ Nueva cuenta' })).toBeInTheDocument()
  })

  it('solo_lectura: sin Nueva cuenta ni acciones de fila', async () => {
    mockApi([{ path: '/bancos', data: BANCOS }])
    envoltura(<BancosPage />, { rol: 'solo_lectura' })
    expect((await screen.findAllByText('BBVA')).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: '+ Nueva cuenta' })).not.toBeInTheDocument()
    expect(screen.queryByText('Editar')).not.toBeInTheDocument()
    expect(screen.queryByText('Borrar')).not.toBeInTheDocument()
  })
})

function envolturaMovimientos(ui, rol = 'admin') {
  setSession({ rol, empresa: EMPRESA })
  return render(
    <MemoryRouter initialEntries={['/bancos/1/movimientos']}>
      <AuthProvider>
        <EmpresaProvider>
          <Routes>
            <Route path="/bancos/:numero/movimientos" element={ui} />
          </Routes>
        </EmpresaProvider>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('MovimientosBancoPage', () => {
  it('muestra el banco de la ruta y su lista de movimientos', async () => {
    mockApi([
      { path: '/bancos', data: BANCOS },
      {
        path: '/bancos/movimientos/lista',
        data: {
          total: 1,
          items: [{ id: 1, fecha: '2026-03-02', texto: 'Nómina', importe: 50, banco: 1 }],
        },
      },
    ])
    envolturaMovimientos(<MovimientosBancoPage />)
    expect(await screen.findByRole('heading', { name: 'BBVA' })).toBeInTheDocument()
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/bancos/movimientos/lista')).toBe(true))
    expect(screen.getByText('Nómina')).toBeInTheDocument()
    expect(screen.getByText('1 movimiento')).toBeInTheDocument()
  })

  it('admin ve "+ Nuevo movimiento"; solo_lectura no', async () => {
    mockApi([
      { path: '/bancos', data: BANCOS },
      { path: '/bancos/movimientos/lista', data: { total: 0, items: [] } },
    ])
    envolturaMovimientos(<MovimientosBancoPage />, 'admin')
    expect(await screen.findByRole('button', { name: '+ Nuevo movimiento' })).toBeInTheDocument()
  })

  it('solo_lectura sin botón de nuevo', async () => {
    mockApi([
      { path: '/bancos', data: BANCOS },
      { path: '/bancos/movimientos/lista', data: { total: 0, items: [] } },
    ])
    envolturaMovimientos(<MovimientosBancoPage />, 'solo_lectura')
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/bancos/movimientos/lista')).toBe(true))
    expect(screen.queryByRole('button', { name: '+ Nuevo movimiento' })).not.toBeInTheDocument()
  })
})
