import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import BenchmarkAdmin from './BenchmarkAdmin.vue'

createApp(window.location.pathname === '/admin/benchmark' ? BenchmarkAdmin : App).mount('#app')
