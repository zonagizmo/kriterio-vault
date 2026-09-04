/**
 * Formulario compartido de datos de contacto para Clientes y Proveedores.
 */
export default function FormContacto({ datos, onChange, tipo = 'cliente' }) {
  const campo = (name) => ({
    id: name,
    name,
    value: datos[name] ?? '',
    onChange: (e) => onChange({ ...datos, [name]: e.target.value }),
    className: 'input',
  })

  return (
    <div className="space-y-4">
      {/* Datos principales */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Datos principales
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="label" htmlFor="nombre">Nombre / Razón social *</label>
            <input {...campo('nombre')} required />
          </div>
          <div className="col-span-2">
            <label className="label" htmlFor="comercial">Nombre comercial</label>
            <input {...campo('comercial')} />
          </div>
          <div>
            <label className="label" htmlFor="nif">NIF / CIF</label>
            <input {...campo('nif')} />
          </div>
          <div>
            <label className="label" htmlFor="cuenta">Cuenta contable</label>
            <input {...campo('cuenta')}
              placeholder={tipo === 'proveedor' ? 'Vacío = automática (400xxxx)' : tipo === 'cliente' ? 'Vacío = automática (430xxxx)' : ''} />
          </div>
        </div>
      </div>

      {/* Contacto */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Contacto
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label" htmlFor="telefono">Teléfono</label>
            <input {...campo('telefono')} type="tel" />
          </div>
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input {...campo('email')} type="email" />
          </div>
        </div>
      </div>

      {/* Dirección */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Dirección
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="label" htmlFor="domicilio">Domicilio</label>
            <input {...campo('domicilio')} />
          </div>
          <div>
            <label className="label" htmlFor="localidad">Localidad</label>
            <input {...campo('localidad')} />
          </div>
          <div>
            <label className="label" htmlFor="provincia">Provincia</label>
            <input {...campo('provincia')} />
          </div>
          <div>
            <label className="label" htmlFor="cod_postal">Código postal</label>
            <input {...campo('cod_postal')} />
          </div>
          <div>
            <label className="label" htmlFor="ap_correos">Apartado de correos</label>
            <input {...campo('ap_correos')} />
          </div>
        </div>
      </div>

      {/* Datos bancarios (solo clientes) */}
      {tipo === 'cliente' && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Datos bancarios
          </h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="label" htmlFor="banco_nom">Entidad</label>
              <input {...campo('banco_nom')} maxLength={4} />
            </div>
            <div>
              <label className="label" htmlFor="banco_suc">Sucursal</label>
              <input {...campo('banco_suc')} maxLength={4} />
            </div>
            <div>
              <label className="label" htmlFor="banco_dig">Dígitos control</label>
              <input {...campo('banco_dig')} maxLength={2} />
            </div>
            <div className="col-span-3">
              <label className="label" htmlFor="banco_tit">Titular</label>
              <input {...campo('banco_tit')} />
            </div>
          </div>
        </div>
      )}

      {/* Notas */}
      <div>
        <label className="label" htmlFor="notas">Notas</label>
        <textarea
          id="notas"
          name="notas"
          rows={3}
          value={datos.notas ?? ''}
          onChange={(e) => onChange({ ...datos, notas: e.target.value })}
          className="input resize-none"
        />
      </div>
    </div>
  )
}
