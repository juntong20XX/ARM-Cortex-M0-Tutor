import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import LoginView from '../views/Login.vue'
import LoginOAuthView from '../views/LoginOAuth.vue'
import DemoView from '../views/Demo.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/demo', name: 'demo', component: DemoView },
    { path: '/login', name: 'login', component: LoginView },
    {
      path: '/login-oauth/:providerName',
      name: 'login-oauth',
      component: LoginOAuthView,
      props: true,
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router

