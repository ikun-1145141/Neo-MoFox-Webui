import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 9178,
    strictPort: false,
    proxy: {
      // 代理所有 /api 开头的请求
      '/api': {
        target: 'http://localhost:8005', // 代理目标地址
        changeOrigin: true, // 允许跨域
      },
    },
  },
})
