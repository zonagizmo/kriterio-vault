/** Panel de inicio: dashboard por empresa. */
import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import InicioPage from '../pages/InicioPage'
import { renderWithProviders, mockApi } from './helpers.jsx'

const DASHBOARD = {
  bancos: [{ numero: 1, nombre: 'BBVA', saldo: 1500 }],
  total_bancos: 1500,
  cobrar_pendiente: 300,
  pagar_pendiente: 120,
  mes_nombre: 'Marzo',
  ingresos_mes: 1000,
  ingresos_mes_anterior: 800,
  gastos_mes: 400,
  gastos_mes_anterior: 500,
  vencimientos_vencidos: 2,
  vencimientos_proximos: [{ numero: 7, tipo: 'F', fecha: '2026-01-05', pendiente: 99 }],
}

describe('InicioPage', () => {
  it('sin empresa lo indica', () => {
    renderWithProviders(<InicioPage />, { empresa: null })
    expect(screen.getByText(/Selecciona una empresa para ver el panel/)).toBeInTheDocument()
  })

  it('muestra la empresa y las tarjetas del dashboard', async () => {
    mockApi([{ path: '/dashboard', data: DASHBOARD }])
    renderWithProviders(<InicioPage />)
    expect(screen.getByRole('heading', { name: 'Empresa 1' })).toBeInTheDocument()
    expect(await screen.findByText('Tesorería')).toBeInTheDocument()
    expect(screen.getByText('BBVA')).toBeInTheDocument()
    expect(screen.getByText('Por cobrar')).toBeInTheDocument()
    expect(screen.getByText('Por pagar')).toBeInTheDocument()
    expect(screen.getByText(/Mes en curso/)).toBeInTheDocument()
    expect(screen.getByText(/vencimientos vencidos sin pagar/)).toBeInTheDocument()
  })

  it('tarjetas sin datos: renderiza importes en cero', async () => {
    mockApi([
      {
        path: '/dashboard',
        data: { ...DASHBOARD, bancos: [], vencimientos_vencidos: 0, vencimientos_proximos: [] },
      },
    ])
    renderWithProviders(<InicioPage />)
    await waitFor(() => expect(screen.getByText('Por cobrar')).toBeInTheDocument())
    expect(screen.queryByText(/vencimientos vencidos/)).not.toBeInTheDocument()
  })
})
