import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import Icon from './components/common/Icon.vue'

createApp(App).use(router).component('Icon', Icon).mount('#app')
