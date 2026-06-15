// Point d'entree principal de l'application React.
// Ce script initialise et injecte le composant principal App dans l'element DOM avec l'identifiant 'root'.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Rendu du composant principal avec le mode Strict de React active pour detecter les problemes potentiels.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
