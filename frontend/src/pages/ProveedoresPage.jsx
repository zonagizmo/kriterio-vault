import { useNavigate } from 'react-router-dom'
import { getProveedores, createProveedor, updateProveedor, deleteProveedor } from '../services/proveedores'
import FormContacto from '../components/FormContacto'
import CrudPage from '../components/CrudPage'

const VACIO = {
  nombre: '',
  comercial: '',
  nif: '',
  cuenta: '',
  domicilio: '',
  localidad: '',
  provincia: '',
  cod_postal: '',
  ctairpf: '',
  ccaja: '',
  telefono: '',
  email: '',
  notas: '',
}

const service = { getAll: getProveedores, create: createProveedor, update: updateProveedor, delete: deleteProveedor }

function FormBody({ datos, onChange }) {
  return <FormContacto datos={datos} onChange={onChange} tipo="proveedor" />
}

export default function ProveedoresPage() {
  const navigate = useNavigate()

  return (
    <CrudPage
      titulo="Proveedores"
      entityName="el proveedor"
      nuevoLabel="+ Nuevo proveedor"
      searchPlaceholder="Buscar por nombre, NIF, localidad..."
      service={service}
      emptyForm={VACIO}
      FormBody={FormBody}
      renderActions={(p) => (
        <>
          <button
            onClick={() => navigate(`/facturas?tab=recibidas&proveedor=${p.numero}`)}
            className="text-blue-500 hover:text-blue-700 text-xs font-medium"
          >
            Facturas
          </button>
          {p.cuenta ? (
            <button
              onClick={() => navigate(`/contabilidad?tab=mayor&cuenta=${p.cuenta}`)}
              className="text-purple-500 hover:text-purple-700 text-xs font-medium"
            >
              Mayor
            </button>
          ) : (
            <span className="text-gray-300 text-xs cursor-default" title="Sin cuenta asignada">
              Mayor
            </span>
          )}
        </>
      )}
    />
  )
}
