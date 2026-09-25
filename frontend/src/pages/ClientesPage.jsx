import { useNavigate } from 'react-router-dom'
import { getClientes, createCliente, updateCliente, deleteCliente } from '../services/clientes'
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
  banco_nom: '',
  banco_suc: '',
  banco_dig: '',
  banco_tit: '',
  telefono: '',
  email: '',
  notas: '',
}

const service = { getAll: getClientes, create: createCliente, update: updateCliente, delete: deleteCliente }

function FormBody({ datos, onChange }) {
  return <FormContacto datos={datos} onChange={onChange} tipo="cliente" />
}

export default function ClientesPage() {
  const navigate = useNavigate()

  return (
    <CrudPage
      titulo="Clientes"
      entityName="el cliente"
      searchPlaceholder="Buscar por nombre, NIF, localidad..."
      service={service}
      emptyForm={VACIO}
      FormBody={FormBody}
      renderActions={(c) => (
        <>
          <button
            onClick={() => navigate(`/facturas?tab=emitidas&cliente=${c.numero}`)}
            className="text-blue-500 hover:text-blue-700 text-xs font-medium"
          >
            Facturas
          </button>
          {c.cuenta ? (
            <button
              onClick={() => navigate(`/contabilidad?tab=mayor&cuenta=${c.cuenta}`)}
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
