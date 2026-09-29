/**
 * Páginas CRUD básicas: Clientes y Proveedores (CrudPage) y Artículos
 * (página propia). Comprueba encabezado, carga de datos y control por rol.
 */
import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import ClientesPage from '../pages/ClientesPage'
import ProveedoresPage from '../pages/ProveedoresPage'
import ArticulosPage from '../pages/ArticulosPage'
import { renderWithProviders, mockApi, apiCalls } from './helpers.jsx'

const ITEM = { id: 1, numero: 1, nombre: 'Ana López', nif: '111', localidad: 'Sevilla' }

describe('ClientesPage', () => {
  it('admin: encabezado, filas y botón Nuevo', async () => {
    mockApi([{ path: '/clientes', data: { total: 1, items: [ITEM] } }])
    renderWithProviders(<ClientesPage />, { rol: 'admin' })
    expect(screen.getByRole('heading', { name: 'Clientes' })).toBeInTheDocument()
    expect(await screen.findByText('Ana López')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ Nuevo cliente' })).toBeInTheDocument()
  })

  it('solo_lectura: sin controles de escritura', async () => {
    mockApi([{ path: '/clientes', data: { total: 1, items: [ITEM] } }])
    renderWithProviders(<ClientesPage />, { rol: 'solo_lectura' })
    expect(await screen.findByText('Ana López')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '+ Nuevo cliente' })).not.toBeInTheDocument()
    expect(screen.queryByText('Borrar')).not.toBeInTheDocument()
  })

  it('lista vacía: mensaje de "no se encontraron"', async () => {
    mockApi([{ path: '/clientes', data: { total: 0, items: [] } }])
    renderWithProviders(<ClientesPage />, { rol: 'admin' })
    expect(await screen.findByText('No se encontraron clientes')).toBeInTheDocument()
  })
})

describe('ProveedoresPage', () => {
  it('admin: encabezado y Nuevo', async () => {
    mockApi([{ path: '/proveedores', data: { total: 0, items: [] } }])
    renderWithProviders(<ProveedoresPage />, { rol: 'admin' })
    expect(screen.getByRole('heading', { name: 'Proveedores' })).toBeInTheDocument()
    expect(await screen.findByText('No se encontraron proveedores')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ Nuevo proveedor' })).toBeInTheDocument()
  })

  it('operador: puede crear (CRUD)', async () => {
    mockApi([{ path: '/proveedores', data: { total: 0, items: [] } }])
    renderWithProviders(<ProveedoresPage />, { rol: 'operador' })
    expect(await screen.findByRole('button', { name: '+ Nuevo proveedor' })).toBeInTheDocument()
  })
})

describe('ArticulosPage', () => {
  const ART = { id: 1, numero: 1, nombre: 'Tornillo', codigo: 'T-01', pventa: 0.5, pcompra: 0.3, qinvent: 10 }

  it('admin: encabezado, filas, Nuevo y edición por fila', async () => {
    mockApi([
      { path: '/articulos', data: { total: 1, items: [ART] } },
      { path: '/familias', data: [] },
    ])
    renderWithProviders(<ArticulosPage />, { rol: 'admin' })
    expect(screen.getByRole('heading', { name: 'Artículos' })).toBeInTheDocument()
    expect(await screen.findByText('Tornillo')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ Nuevo artículo' })).toBeInTheDocument()
    expect(screen.getAllByText('Editar').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Borrar').length).toBeGreaterThan(0)
  })

  it('solo_lectura: sin Nuevo/Editar/Borrar', async () => {
    mockApi([
      { path: '/articulos', data: { total: 1, items: [ART] } },
      { path: '/familias', data: [] },
    ])
    renderWithProviders(<ArticulosPage />, { rol: 'solo_lectura' })
    expect(await screen.findByText('Tornillo')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '+ Nuevo artículo' })).not.toBeInTheDocument()
    expect(screen.queryByText('Editar')).not.toBeInTheDocument()
    expect(screen.queryByText('Borrar')).not.toBeInTheDocument()
  })

  it('carga las familias del selector', async () => {
    mockApi([
      { path: '/articulos', data: { total: 0, items: [] } },
      { path: '/familias', data: [{ id: 1, numero: 1, texto: 'Ferro' }] },
    ])
    renderWithProviders(<ArticulosPage />, { rol: 'admin' })
    expect(await screen.findByRole('heading', { name: 'Artículos' })).toBeInTheDocument()
    await waitFor(() => expect(apiCalls.some((c) => c.url === '/familias')).toBe(true))
  })
})
