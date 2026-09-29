import '@testing-library/jest-dom/vitest'
import { beforeEach, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import { mockApi } from './helpers.jsx'

beforeEach(() => {
  localStorage.clear()
  mockApi()
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})
