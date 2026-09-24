import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// In development every request to /api is proxied to the FastAPI server, so the
// browser only ever talks to the Vite origin and the backend needs no CORS setup.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
