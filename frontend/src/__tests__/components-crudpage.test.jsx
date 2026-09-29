/**
 * CrudPage: el reflejo de permisos (§7 de SECURITY.md) — sin create no hay
 * "Nuevo", sin update no hay "Editar", sin delete no hay "Borrar".
 */
import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import CrudPage from '../components/CrudPage'
import { renderWithProviders } from './helpers.jsx'

const ITEMS = [
  { id: 1, numero: 1, nombre: 'Ana López', nif: '111', localidad: 'Sevilla', cuenta: '4300', pendiente: 12.5 },
  { id: 2, numero: 2, nombre: 'Bruno Gil', nif: '', localidad: '', cuenta: '', pendiente: 0 },
]

function servicio(overrides = {}) {
  return {
    getAll: vi.fn(async () => ({ total: ITEMS.length, items: ITEMS })),
    create: vi.fn(async (d) => ({ id: 3, ...d })),
    update: vi.fn(async (d) => d),
    delete: vi.fn(async () => ({})),
    ...overrides,
  }
}

function renderCrud({ rol = 'admin', service = servicio(), empresa, ...props } = {}) {
  const servicioDefecto = servicio()
  const svc = service ?? servicioDefecto
  return {
    service: svc,
    ...renderWithProviders(
      <CrudPage
        titulo="Clientes"
        entityName="el cliente"
        searchPlaceholder="Buscar clientes..."
        service={svc}
        emptyForm={{ nombre: '' }}
        FormBody={({ datos, onChange }) => (
          <input
            aria-label="nombre"
            value={datos.nombre || ''}
            onChange={(e) => onChange({ ...datos, nombre: e.target.value })}
          />
        )}
        {...props}
      />,
      { rol, empresa },
    ),
  }
}

describe('CrudPage — permisos reflejados en la UI', () => {
  it('admin ve Nuevo, Editar y Borrar', async () => {
    renderCrud({ rol: 'admin' })
    expect(screen.getByRole('button', { name: '+ Nuevo cliente' })).toBeInTheDocument()
    expect(await screen.findAllByText('Editar')).toHaveLength(2)
    expect(screen.getAllByText('Borrar')).toHaveLength(2)
  })

  it('operador también puede crear/editar/borrar (CRUD)', async () => {
    renderCrud({ rol: 'operador' })
    expect(screen.getByRole('button', { name: '+ Nuevo cliente' })).toBeInTheDocument()
    expect(await screen.findAllByText('Editar')).toHaveLength(2)
    expect(screen.getAllByText('Borrar')).toHaveLength(2)
  })

  it('solo_lectura: ve los datos pero NINGÚN control de escritura', async () => {
    renderCrud({ rol: 'solo_lectura' })
    expect(await screen.findByText('Ana López')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '+ Nuevo cliente' })).not.toBeInTheDocument()
    expect(screen.queryByText('Editar')).not.toBeInTheDocument()
    expect(screen.queryByText('Borrar')).not.toBeInTheDocument()
  })

  it('sin empresa seleccionada lo indica y no carga datos', () => {
    renderCrud({ empresa: null })
    expect(screen.getByText(/Selecciona una empresa para ver clientes/)).toBeInTheDocument()
    expect(screen.queryByText('Ana López')).not.toBeInTheDocument()
  })
})

describe('CrudPage — ciclo de vida', () => {
  it('muestra las filas devueleltas por el servicio', async () => {
    renderCrud({})
    expect(await screen.findByText('Ana López')).toBeInTheDocument()
    expect(screen.getByText('Bruno Gil')).toBeInTheDocument()
    expect(screen.getByText('Sevilla')).toBeInTheDocument()
  })

  it('abre el modal y crea con la empresa activa', async () => {
    const { service } = renderCrud({})
    fireEvent.click(screen.getByRole('button', { name: '+ Nuevo cliente' }))
    expect(await screen.findByText('Nuevo el cliente')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('nombre'), { target: { value: 'Carla' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(service.create).toHaveBeenCalledWith({ nombre: 'Carla', empresa_id: 1 }))
    await waitFor(() => expect(screen.queryByText('Nuevo el cliente')).not.toBeInTheDocument())
  })

  it('editar actualiza el registro existente', async () => {
    const { service } = renderCrud({})
    fireEvent.click((await screen.findAllByText('Editar'))[0])
    expect(await screen.findByText('Editar el cliente')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    await waitFor(() =>
      expect(service.update).toHaveBeenCalledWith(1, expect.objectContaining({ nombre: 'Ana López' })),
    )
  })

  it('borrar pide confirmación y llama al servicio', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const { service } = renderCrud({})
    fireEvent.click((await screen.findAllByText('Borrar'))[0])
    expect(window.confirm).toHaveBeenCalledWith('¿Eliminar el cliente "Ana López"?')
    await waitFor(() => expect(service.delete).toHaveBeenCalledWith(1))
    await waitFor(() => expect(service.getAll).toHaveBeenCalledTimes(2))
  })

  it('borrar cancelado no llama al servicio', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { service } = renderCrud({})
    fireEvent.click((await screen.findAllByText('Borrar'))[0])
    expect(service.delete).not.toHaveBeenCalled()
  })

  it('el error del servicio se muestra en pantalla', async () => {
    renderCrud({
      service: servicio({
        getAll: vi.fn(async () => {
          throw new Error('boom')
        }),
      }),
    })
    expect(await screen.findByText('boom')).toBeInTheDocument()
  })

  it('la búsqueda se envía al servicio', async () => {
    const { service } = renderCrud({})
    await screen.findByText('Ana López')
    fireEvent.change(screen.getByPlaceholderText('Buscar clientes...'), { target: { value: 'ana' } })
    await waitFor(() => expect(service.getAll).toHaveBeenCalledWith(1, expect.objectContaining({ q: 'ana' })))
  })
})
