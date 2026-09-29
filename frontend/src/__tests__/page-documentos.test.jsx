/** Páginas de documentos: Albaranes y Facturas (pestañas emitidos/recibidos). */
import { describe, it, expect } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import AlbaranesPage from '../pages/AlbaranesPage'
import FacturasPage from '../pages/FacturasPage'
import { renderWithProviders, mockApi, apiCalls } from './helpers.jsx'

describe('AlbaranesPage', () => {
  it('admin: encabezado, pestañas y Nuevo', async () => {
    mockApi([{ path: '/albaranes/emitidos', data: { total: 0, items: [] } }])
    renderWithProviders(<AlbaranesPage />, { rol: 'admin' })
    expect(screen.getByRole('heading', { name: 'Albaranes' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ Nuevo albarán' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Emitidos' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Recibidos' })).toBeInTheDocument()
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/albaranes/emitidos')).toBe(true))
  })

  it('cambia a recibidos y pide esa lista', async () => {
    mockApi([
      { path: '/albaranes/emitidos', data: { total: 0, items: [] } },
      { path: '/albaranes/recibidos', data: { total: 0, items: [] } },
    ])
    renderWithProviders(<AlbaranesPage />, { rol: 'admin' })
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/albaranes/emitidos')).toBe(true))
    fireEvent.click(screen.getByRole('button', { name: 'Recibidos' }))
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/albaranes/recibidos')).toBe(true))
  })

  it('solo_lectura: sin Nuevo', async () => {
    mockApi([{ path: '/albaranes/emitidos', data: { total: 0, items: [] } }])
    renderWithProviders(<AlbaranesPage />, { rol: 'solo_lectura' })
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/albaranes/emitidos')).toBe(true))
    expect(screen.queryByRole('button', { name: '+ Nuevo albarán' })).not.toBeInTheDocument()
  })
})

describe('FacturasPage', () => {
  it('admin: encabezado, Renumerar, Nueva factura; arranca en recibidas', async () => {
    mockApi([
      { path: '/facturas/recibidas', data: { total: 0, items: [] } },
      { path: '/facturas/emitidas', data: { total: 0, items: [] } },
    ])
    renderWithProviders(<FacturasPage />, { rol: 'admin' })
    expect(screen.getByRole('heading', { name: 'Facturas' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ Nueva factura' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Renumerar' })).toBeInTheDocument()
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/facturas/recibidas')).toBe(true))
  })

  it('cambia a emitidas y pide esa lista', async () => {
    mockApi([
      { path: '/facturas/recibidas', data: { total: 0, items: [] } },
      { path: '/facturas/emitidas', data: { total: 0, items: [] } },
    ])
    renderWithProviders(<FacturasPage />, { rol: 'admin' })
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/facturas/recibidas')).toBe(true))
    fireEvent.click(screen.getByRole('button', { name: 'Emitidas' }))
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/facturas/emitidas')).toBe(true))
  })

  it('solo_lectura: sin Nueva factura ni Renumerar', async () => {
    mockApi([{ path: '/facturas/recibidas', data: { total: 0, items: [] } }])
    renderWithProviders(<FacturasPage />, { rol: 'solo_lectura' })
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/facturas/recibidas')).toBe(true))
    expect(screen.queryByRole('button', { name: '+ Nueva factura' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Renumerar' })).not.toBeInTheDocument()
  })

  it('muestra filas de facturas emitidas con ?tab=emitidas', async () => {
    mockApi([
      {
        path: '/facturas/emitidas',
        data: {
          total: 1,
          items: [{ id: 1, numero: 1, fecha: '2026-03-01', cliente: 'Ana', total: 100, pendiente: 100 }],
        },
      },
      { path: '/facturas/recibidas', data: { total: 0, items: [] } },
      { path: '/clientes', data: { total: 0, items: [] } },
    ])
    renderWithProviders(<FacturasPage />, { path: '/facturas?tab=emitidas', rol: 'admin' })
    expect(await screen.findByText('Ana')).toBeInTheDocument()
  })
})
