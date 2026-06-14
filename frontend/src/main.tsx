import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './styles/Explorer.css'
import AppNew from './AppNew.tsx'
import { ErrorBoundary } from './components/ErrorBoundary'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary label="the app">
      <AppNew />
    </ErrorBoundary>
  </StrictMode>,
)
