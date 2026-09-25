import { Component } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import { EmpresaProvider } from './hooks/useEmpresa.jsx'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import EmpresasSelectorPage from './pages/EmpresasSelectorPage'
import InicioPage from './pages/InicioPage'
import ClientesPage from './pages/ClientesPage'
import ProveedoresPage from './pages/ProveedoresPage'
import ArticulosPage from './pages/ArticulosPage'
import AlbaranesPage from './pages/AlbaranesPage'
import FacturasPage from './pages/FacturasPage'
import BancosPage from './pages/BancosPage'
import MovimientosBancoPage from './pages/MovimientosBancoPage'
import ContabilidadPage from './pages/contabilidad'
import IngresosGastosPage from './pages/IngresosGastosPage'
import EstadisticasPage from './pages/EstadisticasPage'
import ExtrasPage from './pages/ExtrasPage'
import UsuariosPage from './pages/UsuariosPage'
import AjustesPage from './pages/AjustesPage'
import UsuariosSistemaPage from './pages/UsuariosSistemaPage'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }
  static getDerivedStateFromError(error) {
    return { error }
  }
  componentDidCatch(error, info) {
    console.error('[ERROR BOUNDARY]', error, info?.componentStack)
  }
  render() {
    if (this.state.error) {
      return (
        <div
          style={{ padding: 20, background: '#1a1a2e', color: '#ff6b6b', fontFamily: 'monospace', minHeight: '100vh' }}
        >
          <h2 style={{ color: '#ff6b6b' }}>Error en React</h2>
          <pre style={{ whiteSpace: 'pre-wrap', color: '#ffa07a' }}>{this.state.error.message}</pre>
          <pre style={{ whiteSpace: 'pre-wrap', color: '#aaa', fontSize: 12 }}>{this.state.error.stack}</pre>
        </div>
      )
    }
    return this.props.children
  }
}

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

function AuthenticatedRoutes() {
  return (
    <EmpresaProvider>
      <Routes>
        <Route path="/" element={<EmpresasSelectorPage />} />
        <Route path="/empresas" element={<EmpresasSelectorPage />} />
        <Route
          path="/inicio"
          element={
            <Layout>
              <InicioPage />
            </Layout>
          }
        />
        <Route
          path="/clientes"
          element={
            <Layout>
              <ClientesPage />
            </Layout>
          }
        />
        <Route
          path="/proveedores"
          element={
            <Layout>
              <ProveedoresPage />
            </Layout>
          }
        />
        <Route
          path="/articulos"
          element={
            <Layout>
              <ArticulosPage />
            </Layout>
          }
        />
        <Route
          path="/albaranes"
          element={
            <Layout>
              <AlbaranesPage />
            </Layout>
          }
        />
        <Route
          path="/facturas"
          element={
            <Layout>
              <FacturasPage />
            </Layout>
          }
        />
        <Route
          path="/bancos"
          element={
            <Layout>
              <BancosPage />
            </Layout>
          }
        />
        <Route
          path="/bancos/:numero/movimientos"
          element={
            <Layout>
              <MovimientosBancoPage />
            </Layout>
          }
        />
        <Route
          path="/bancos/movimientos"
          element={
            <Layout>
              <MovimientosBancoPage />
            </Layout>
          }
        />
        <Route
          path="/contabilidad"
          element={
            <Layout>
              <ContabilidadPage />
            </Layout>
          }
        />
        <Route
          path="/ingresos-gastos"
          element={
            <Layout>
              <IngresosGastosPage />
            </Layout>
          }
        />
        <Route
          path="/estadisticas"
          element={
            <Layout>
              <EstadisticasPage />
            </Layout>
          }
        />
        <Route
          path="/extras"
          element={
            <Layout>
              <ExtrasPage />
            </Layout>
          }
        />
        <Route
          path="/usuarios"
          element={
            <Layout>
              <UsuariosPage />
            </Layout>
          }
        />
        <Route
          path="/ajustes"
          element={
            <Layout>
              <AjustesPage />
            </Layout>
          }
        />
        <Route
          path="/usuarios-sistema"
          element={
            <Layout>
              <UsuariosSistemaPage />
            </Layout>
          }
        />
        <Route path="*" element={<Navigate to="/inicio" replace />} />
      </Routes>
    </EmpresaProvider>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <AuthenticatedRoutes />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </ErrorBoundary>
  )
}
