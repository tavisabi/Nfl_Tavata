import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' para que el build funcione desde cualquier ruta (el hosting publica en una subruta).
// En desarrollo, Vite y Uvicorn corren por separado: /api se redirige al backend en el puerto 8000.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
