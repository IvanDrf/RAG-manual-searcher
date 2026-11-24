import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'AUTH_API_')
  const project = fileURLToPath(new URL('.', import.meta.url))
  const pdfDirectory = fileURLToPath(new URL('../data/student_book_pdf', import.meta.url))
  const proxy = {
    '/api/v1': {
      target: env.AUTH_API_TARGET || 'http://127.0.0.1:8080',
      changeOrigin: true,
    },
  }

  return {
    plugins: [react()],
    server: { fs: { allow: [project, pdfDirectory] }, proxy },
    preview: { proxy },
  }
})
