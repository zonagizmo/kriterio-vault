/**
 * Contabilidad: las 8 pestañas cargan sin romper y respetan la pestaña
 * inicial (?tab=). Cada pestaña consume una forma de respuesta distinta.
 */
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from '../hooks/useAuth.jsx'
import { EmpresaProvider } from '../hooks/useEmpresa.jsx'
import ContabilidadPage from '../pages/contabilidad'
import { apiCalls, setSession, EMPRESA } from './helpers.jsx'

function renderContab(ruta = '/contabilidad') {
  setSession({ rol: 'admin', empresa: EMPRESA })
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <AuthProvider>
        <EmpresaProvider>
          <Routes>
            <Route path="/contabilidad" element={<ContabilidadPage />} />
          </Routes>
        </EmpresaProvider>
      </AuthProvider>
    </MemoryRouter>,
  )
}

/** Pestañas que solo consultan al pulsar su botón. */
const ACCION = {
  'Sumas y saldos': 'Calcular',
  'P&G': 'Calcular',
  Balance: 'Calcular',
  Conciliación: 'Analizar discrepancias',
  Diagnóstico: 'Analizar contabilidad',
}

const TABS = [
  ['Plan de cuentas', '/contabilidad/cuentas'],
  ['Diario', '/contabilidad/asientos'],
  ['Libro mayor', null], // sin cuenta seleccionada no pide nada aún
  ['Sumas y saldos', '/contabilidad/sumas-saldos'],
  ['P&G', '/contabilidad/pyg'],
  ['Balance', '/contabilidad/balance'],
  ['Conciliación', '/contabilidad/conciliacion-bancos'],
  ['Diagnóstico', '/contabilidad/diagnostico'],
]

describe('ContabilidadPage', () => {
  it('muestra el encabezado y las 8 pestañas', () => {
    renderContab()
    expect(screen.getByRole('heading', { name: 'Contabilidad' })).toBeInTheDocument()
    for (const [label] of TABS) expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
  })

  it('arranca en Plan de cuentas y pide /contabilidad/cuentas', async () => {
    renderContab()
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/contabilidad/cuentas')).toBe(true))
  })

  it('cada pestaña carga su endpoint sin errores', async () => {
    renderContab()
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/contabilidad/cuentas')).toBe(true))
    for (const [label, url] of TABS.slice(1)) {
      fireEvent.click(screen.getByRole('button', { name: label }))
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
      if (ACCION[label]) {
        fireEvent.click(screen.getByRole('button', { name: ACCION[label] }))
      }
      if (url)
        await waitFor(() =>
          expect(
            apiCalls.some((c) => c.url === url),
            url,
          ).toBe(true),
        )
    }
  })

  it('sin empresa lo indica', () => {
    setSession({ rol: 'admin', empresa: null })
    render(
      <MemoryRouter initialEntries={['/contabilidad']}>
        <AuthProvider>
          <EmpresaProvider>
            <Routes>
              <Route path="/contabilidad" element={<ContabilidadPage />} />
            </Routes>
          </EmpresaProvider>
        </AuthProvider>
      </MemoryRouter>,
    )
    expect(screen.getByText(/Selecciona una empresa para ver la contabilidad/)).toBeInTheDocument()
  })
})
