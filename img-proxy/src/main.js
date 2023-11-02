import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { WebSocketPlugin } from '@/plugins/WebPluginSocket';
import {GlobalPlugin} from "@/plugins/GlobalPlugin";
import 'bootstrap/dist/css/bootstrap.css'
import './assets/base.css'
import './assets/main.css'
import 'bootstrap';

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const host = window.location.host;


const app = createApp(App)
app.use(router)
app.use(createPinia())

if (import.meta.env.VITE_DEV !== undefined) {
  app.use(WebSocketPlugin, {url: 'ws://127.0.0.1:8000/ws'})
  app.use(GlobalPlugin, {backendUrl: 'http://127.0.0.1:8000', appName: 'Image Proxy'})
} else {
  app.use(WebSocketPlugin, {url: protocol + '//' + host + '/ws'})
  app.use(GlobalPlugin, {backendUrl: '', appName: 'Image Proxy'})
}
app.mount('#app')
