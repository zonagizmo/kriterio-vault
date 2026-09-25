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

  function addEmpresa(emp) {
    setEmpresas((prev) => [...prev, emp])
  }

  function removeEmpresa(id) {
    setEmpresas((prev) => prev.filter((e) => e.id !== id))
  }

  return (
    <EmpresaCtx.Provider value={{ empresa, empresas, loading: false, setEmpresa, addEmpresa, removeEmpresa }}>
      {children}
    </EmpresaCtx.Provider>
  )
}

export function useEmpresa() {
  return useContext(EmpresaCtx)
}
