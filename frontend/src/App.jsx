import { Routes, Route, Navigate } from 'react-router-dom'
import { EmpresaProvider, useEmpresa } from './hooks/useEmpresa.jsx'
import Layout from './components/Layout'
import EmpresasSelectorPage from './pages/EmpresasSelectorPage'
import InicioPage from './pages/InicioPage'
import ClientesPage from './pages/ClientesPage'
import ProveedoresPage from './pages/ProveedoresPage'
import ArticulosPage from './pages/ArticulosPage'
import AlbaranesPage from './pages/AlbaranesPage'
import FacturasPage from './pages/FacturasPage'
import BancosPage from './pages/BancosPage'
import MovimientosBancoPage from './pages/MovimientosBancoPage'
import ContabilidadPage from './pages/ContabilidadPage'
import IngresosGastosPage from './pages/IngresosGastosPage'
import EstadisticasPage from './pages/EstadisticasPage'
import ExtrasPage from './pages/ExtrasPage'
import UsuariosPage from './pages/UsuariosPage'
import AjustesPage from './pages/AjustesPage'

function AppRoutes() {
  const { empresa } = useEmpresa()

  return (
    <Routes>
      <Route path="/" element={<EmpresasSelectorPage />} />
      <Route
        path="/*"
        element={
          empresa ? (
            <Layout>
              <Routes>
                <Route path="/inicio"      element={<InicioPage />} />
                <Route path="/clientes"    element={<ClientesPage />} />
                <Route path="/proveedores" element={<ProveedoresPage />} />
                <Route path="/articulos"   element={<ArticulosPage />} />
                <Route path="/albaranes"   element={<AlbaranesPage />} />
                <Route path="/facturas"    element={<FacturasPage />} />
                <Route path="/bancos"                       element={<BancosPage />} />
                <Route path="/bancos/:numero/movimientos"   element={<MovimientosBancoPage />} />
                <Route path="/bancos/movimientos"           element={<MovimientosBancoPage />} />
                <Route path="/contabilidad" element={<ContabilidadPage />} />
                <Route path="/ingresos-gastos" element={<IngresosGastosPage />} />
                <Route path="/estadisticas" element={<EstadisticasPage />} />
                <Route path="/extras"       element={<ExtrasPage />} />
                <Route path="/usuarios"     element={<UsuariosPage />} />
                <Route path="/ajustes"      element={<AjustesPage />} />
                <Route path="*"             element={<Navigate to="/inicio" replace />} />
              </Routes>
            </Layout>
          ) : (
            <Navigate to="/" replace />
          )
        }
      />
    </Routes>
  )
}

export default function App() {
  return (
    <EmpresaProvider>
      <AppRoutes />
    </EmpresaProvider>
  )
}
