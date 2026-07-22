import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue({
      // sys-components 下的 SFC 需以 customElement 模式编译：
      // <style scoped> 被收集到 component.styles 数组，供 defineCustomElement
      // 注入到各自定义元素的 shadow root —— 否则样式只进 document.head，
      // 无法穿透 shadow DOM，HTML 沙箱内所有 sys-* 组件均无样式。
      // XML 轨在 light DOM 渲染，由 xml-component-registry.ts 额外注入兜底。
      features: {
        customElement: /[/\\]sys-components[/\\]Sys[A-Z][\w-]*\.vue$/,
      },
    }),
  ],
  // 设置基础路径，使打包后的资源路径正确
  base: '/webui/frontend/',
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 9178,
    strictPort: false,
    proxy: {
      // 代理所有 /webui/api 开头的请求
      '/webui/api': {
        target: 'http://localhost:8005', // 代理目标地址
        changeOrigin: true, // 允许跨域
        ws: true, // 转发 WebSocket 日志流
      },
      "/webui/static/": {
        target: 'http://localhost:8005', // 代理目标地址
        changeOrigin: true, // 允许跨域
      },
      "/router": {
        target: 'http://localhost:8005', // 代理目标地址
        changeOrigin: true, // 允许跨域
      },
    },
  },
})
