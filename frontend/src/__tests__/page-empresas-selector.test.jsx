/** Selector de empresas: listado, selección y administración (configuration). */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../hooks/useAuth.jsx'
import { EmpresaProvider } from '../hooks/useEmpresa.jsx'
import EmpresasSelectorPage from '../pages/EmpresasSelectorPage'
import { mockApi, apiCalls, setSession } from './helpers.jsx'

const EMPRESAS = [
  { id: 1, codigo: 'E1', nombre: 'Empresa 1' },
  { id: 2, codigo: 'E2', nombre: 'Empresa 2' },
]

function renderSelector({ rol = 'admin' } = {}) {
  setSession({ rol, empresa: null })
  return render(
    <MemoryRouter>
      <AuthProvider>
        <EmpresaProvider>
          <EmpresasSelectorPage />
        </EmpresaProvider>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('EmpresasSelectorPage', () => {
  it('lista las empresas y muestra el usuario', async () => {
    mockApi([{ path: '/empresas', data: EMPRESAS }])
    renderSelector()
    expect(await screen.findByText('Empresa 1')).toBeInTheDocument()
    expect(screen.getByText('Empresa 2')).toBeInTheDocument()
    expect(screen.getByText('Tester')).toBeInTheDocument()
  })

  it('al elegir una empresa se guarda como activa', async () => {
    mockApi([{ path: '/empresas', data: EMPRESAS }])
    renderSelector()
    fireEvent.click(await screen.findByText('Empresa 2'))
    await waitFor(() => expect(JSON.parse(localStorage.getItem('empresa_activa')).id).toBe(2))
  })

  it('admin ve "+ Nueva empresa" y el botón de eliminar', async () => {
    mockApi([{ path: '/empresas', data: EMPRESAS }])
    renderSelector()
    await screen.findByText('Empresa 1')
    expect(screen.getByText('+ Nueva empresa')).toBeInTheDocument()
    expect(screen.getAllByTitle('Eliminar empresa')).toHaveLength(2)
  })

  it('operador NO ve controles de administración de empresas', async () => {
    mockApi([{ path: '/empresas', data: EMPRESAS }])
    renderSelector({ rol: 'operador' })
    await screen.findByText('Empresa 1')
    expect(screen.queryByText('+ Nueva empresa')).not.toBeInTheDocument()
    expect(screen.queryByTitle('Eliminar empresa')).not.toBeInTheDocument()
  })

  it('crear empresa: POST con codigo/nombre y la selecciona', async () => {
    mockApi([
      { method: 'POST', path: '/empresas', data: { id: 3, codigo: 'E3', nombre: 'Nueva' } },
      { path: '/empresas', data: EMPRESAS },
    ])
    renderSelector()
    fireEvent.click(await screen.findByText('+ Nueva empresa'))
    fireEvent.change(screen.getByPlaceholderText('Ej: 001'), { target: { value: 'E3' } })
    fireEvent.change(screen.getByPlaceholderText('Nombre de la empresa'), { target: { value: 'Nueva' } })
    fireEvent.click(screen.getByRole('button', { name: 'Crear' }))
    await waitFor(() =>
      expect(apiCalls.some((c) => c.method === 'POST' && c.url === '/empresas' && c.data.codigo === 'E3')).toBe(true),
    )
    await waitFor(() => expect(JSON.parse(localStorage.getItem('empresa_activa')).id).toBe(3))
  })

  it('sin empresas y sin configuration no ofrece crear', async () => {
    mockApi([{ path: '/empresas', data: [] }])
    renderSelector({ rol: 'operador' })
    expect(await screen.findByText('No hay empresas configuradas')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Crear primera empresa' })).not.toBeInTheDocument()
  })

  it('con configuration y sin empresas sí permite crear la primera', async () => {
    mockApi([{ path: '/empresas', data: [] }])
    renderSelector({ rol: 'admin' })
    expect(await screen.findByRole('button', { name: 'Crear primera empresa' })).toBeInTheDocument()
    vi.restoreAllMocks()
  })
})
