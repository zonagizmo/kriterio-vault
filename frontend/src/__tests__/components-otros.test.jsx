/** Modal, ConfirmModal y Paginacion (comportamiento base). */
import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { render } from '@testing-library/react'
import Modal from '../components/Modal'
import ConfirmModal from '../components/ConfirmModal'
import Paginacion from '../components/Paginacion'

describe('Modal', () => {
  it('muestra título y contenido, y cierra con ×', () => {
    const onClose = vi.fn()
    render(
      <Modal titulo="Editar cliente" onClose={onClose}>
        <p>formulario</p>
      </Modal>,
    )
    expect(screen.getByText('Editar cliente')).toBeInTheDocument()
    expect(screen.getByText('formulario')).toBeInTheDocument()
    fireEvent.click(screen.getByText('×'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('cierra con Escape y con clic en el fondo', () => {
    const onClose = vi.fn()
    const { container } = render(
      <Modal titulo="X" onClose={onClose}>
        <p>c</p>
      </Modal>,
    )
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
    fireEvent.click(container.firstChild.firstChild)
    expect(onClose).toHaveBeenCalledTimes(2)
  })
})

describe('ConfirmModal', () => {
  it('sin open no se pinta', () => {
    render(<ConfirmModal open={false} title="Borrar" message="¿Seguro?" />)
    expect(screen.queryByText('Borrar')).not.toBeInTheDocument()
  })

  it('confirmar y cancelar', () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(
      <ConfirmModal
        open
        title="Eliminar empresa"
        message="¿Seguro?"
        confirmText="Eliminar"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    )
    expect(screen.getByText('Eliminar empresa')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Eliminar'))
    expect(onConfirm).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByText('Cancelar'))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('Escape y clic en el fondo cancelan', () => {
    const onCancel = vi.fn()
    const { container } = render(<ConfirmModal open title="T" message="m" onCancel={onCancel} onConfirm={() => {}} />)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onCancel).toHaveBeenCalledTimes(1)
    fireEvent.click(container.firstChild.firstChild)
    expect(onCancel).toHaveBeenCalledTimes(2)
  })
})

describe('Paginacion', () => {
  it('sin registros no se pinta', () => {
    const { container } = render(
      <Paginacion total={0} skip={0} limit={50} onCambiar={() => {}} onLimitChange={() => {}} />,
    )
    expect(container.innerHTML).toBe('')
  })

  it('un solo rango y "Todo" seleccionable', () => {
    render(<Paginacion total={10} skip={0} limit={9999} onCambiar={() => {}} onLimitChange={() => {}} />)
    expect(screen.getByText(/de 10/)).toBeInTheDocument()
    expect(screen.getByRole('combobox')).toHaveValue('9999')
  })

  it('varias páginas: siguiente/previo y número de página', () => {
    const onCambiar = vi.fn()
    render(<Paginacion total={120} skip={0} limit={50} onCambiar={onCambiar} onLimitChange={() => {}} />)
    expect(screen.getByText('1–50 de 120')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '‹' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: '›' }))
    expect(onCambiar).toHaveBeenCalledWith(50)
    fireEvent.click(screen.getByRole('button', { name: '2' }))
    expect(onCambiar).toHaveBeenCalledWith(50)
    fireEvent.click(screen.getByRole('button', { name: '3' }))
    expect(onCambiar).toHaveBeenCalledWith(100)
  })

  it('cambiar el límite reinicia en la primera página', () => {
    const onLimitChange = vi.fn()
    render(<Paginacion total={300} skip={100} limit={50} onCambiar={() => {}} onLimitChange={onLimitChange} />)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '100' } })
    expect(onLimitChange).toHaveBeenCalledWith(100)
  })
})
