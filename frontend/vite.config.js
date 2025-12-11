import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,      // Permite usar 'describe', 'it', 'expect' sem importar
    environment: 'jsdom', // Simula o browser
    setupFiles: './src/setupTests.js', // Arquivo de configuração inicial
    css: true,
  },
})