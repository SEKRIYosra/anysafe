// Configuration de Vite pour le developpement et la production.
// Definit les plugins utilises par l'outil de build, notamment React.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
})
