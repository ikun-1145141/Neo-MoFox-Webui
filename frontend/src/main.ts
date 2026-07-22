import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import Icon from './components/common/Icon.vue'
import './styles/md3-variables.css'

createApp(App).use(router).component('Icon', Icon).mount('#app')

// sys-* 自定义元素（HTML 轨）的注册延迟到首次创建 HTML 沙箱时
// （createHtmlSandbox 内部调用 registerAllPluginUICustomElements），
// 避免在应用启动时就把所有 Sys*.vue + ECharts 等依赖打到主包中。
