/** Layout: navegación filtrada por rol (§4/§7 de SECURITY.md). */
import { describe, it, expect } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import Layout from '../components/Layout'
import { renderWithProviders, setSession } from './helpers.jsx'

function renderLayout(rol) {
  return renderWithProviders(
    <Layout>
      <div>contenido</div>
    </Layout>,
    { rol },
  )
}

describe('Layout — sesión y empresa', () => {
  it('muestra la empresa activa, el usuario y la versión', () => {
    renderLayout('admin')
    expect(screen.getByText('Empresa 1')).toBeInTheDocument()
    expect(screen.getByText('E1')).toBeInTheDocument()
    expect(screen.getByText('Tester')).toBeInTheDocument()
    expect(screen.getByText(/v\d+\.\d+\.\d+/)).toBeInTheDocument()
    expect(screen.getByText('contenido')).toBeInTheDocument()
  })

  it('"Cambiar empresa" limpia la empresa activa', () => {
    renderLayout('admin')
    expect(localStorage.getItem('empresa_activa')).not.toBeNull()
    fireEvent.click(screen.getByText('← Cambiar empresa'))
    expect(localStorage.getItem('empresa_activa')).toBeNull()
  })

  it('"Salir" cierra la sesión', () => {
    renderLayout('admin')
    fireEvent.click(screen.getByTitle('Cerrar sesión'))
    expect(localStorage.getItem('kriterio_token')).toBeNull()
    expect(localStorage.getItem('kriterio_user')).toBeNull()
  })
})

describe('Layout — navegación por rol', () => {
  const navBasica = ['Inicio', 'Bancos', 'Clientes', 'Facturas', 'Estadísticas']

  it('admin ve Ajustes, Usuarios del sistema y Apagar', () => {
    renderLayout('admin')
    for (const item of navBasica) expect(screen.getByRole('link', { name: new RegExp(item) })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Ajustes/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Usuarios del sistema/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Apagar/ })).toBeInTheDocument()
  })

  it('operador: sin Ajustes, sin Usuarios del sistema, sin Apagar', () => {
    renderLayout('operador')
    expect(screen.getByRole('link', { name: /Clientes/ })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Ajustes/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Usuarios del sistema/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Apagar/ })).not.toBeInTheDocument()
  })

  it('solo_lectura: mismo menú de operador (solo cambian los controles)', () => {
    renderLayout('solo_lectura')
    expect(screen.getByRole('link', { name: /Facturas/ })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Ajustes/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Usuarios del sistema/ })).not.toBeInTheDocument()
  })

  it('la ruta /ajustes solo aparece con configuration', () => {
    setSession({ rol: 'operador' })
    renderLayout('operador')
    expect(screen.queryByRole('link', { name: /Ajustes/ })).not.toBeInTheDocument()
  })
})
