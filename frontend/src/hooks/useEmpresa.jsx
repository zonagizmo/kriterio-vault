import { createContext, useContext, useEffect, useState } from 'react'
import { getEmpresas } from '../services/empresas'

const EmpresaCtx = createContext(null)

export function EmpresaProvider({ children }) {
  const [empresas, setEmpresas] = useState([])
  const [empresa, setEmpresa] = useState(() => {
    const s = localStorage.getItem('empresa_activa')
    return s ? JSON.parse(s) : null
  })

  useEffect(() => {
    getEmpresas()
      .then((data) => setEmpresas(data))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (empresa) {
      localStorage.setItem('empresa_activa', JSON.stringify(empresa))
    } else {
      localStorage.removeItem('empresa_activa')
    }
  }, [empresa])

  return (
    <EmpresaCtx.Provider value={{ empresa, empresas, setEmpresa }}>
      {children}
    </EmpresaCtx.Provider>
  )
}

export function useEmpresa() {
  return useContext(EmpresaCtx)
}
