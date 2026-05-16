import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { spawn } from 'child_process'
import path from 'path'

const backendPlugin = () => ({
  name: 'start-backend',
  configureServer() {
    const backendDir = path.resolve(__dirname, '..')
    const proc = spawn('python', ['-m', 'uvicorn', 'backend.app:app', '--reload'], {
      cwd: backendDir,
      stdio: 'inherit',
    })
    proc.on('error', (err) => console.error('Backend failed to start:', err))
    process.on('exit', () => proc.kill())
  },
})

export default defineConfig({
  plugins: [react(), tailwindcss(), backendPlugin()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
