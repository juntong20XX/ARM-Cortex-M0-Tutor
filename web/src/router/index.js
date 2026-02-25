import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import ProjectList from '../views/ProjectList.vue'
import ConfigView from '../views/ConfigView.vue'
import LoginView from '../views/Login.vue'
import LoginOAuthView from '../views/LoginOAuth.vue'
import DemoView from '../views/Demo.vue'
import DemoEmbedView from '../views/DemoEmbedView.vue'
import ProjectWorkspaceView from '../views/ProjectWorkspaceView.vue'
import { useSession } from '../composables/useSession'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/project/list', name: 'project', component: ProjectList },
    { path: '/project/workspace', name: 'project-workspace', component: ProjectWorkspaceView, props: true },
    { path: '/project', redirect: '/project/list' },
    { path: '/config', name: 'config', component: ConfigView },
    { path: '/demo', name: 'demo', component: DemoView },
    { path: '/demo/embed', name: 'demo-embed', component: DemoEmbedView },
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

// Global navigation guard: all routes except whitelist require authentication
router.beforeEach((to, from, next) => {
  const whiteList = ['/login', '/login-oauth', '/demo/embed']

  // Whitelisted paths (including all subpaths under /login-oauth) are always allowed
  if (whiteList.some((path) => to.path === path || to.path.startsWith(`${path}/`))) {
    next()
    return
  }

  const { isAuthenticated, loadSession } = useSession()
  // Ensure session is restored from localStorage
  loadSession()

  if (isAuthenticated.value) {
    next()
    return
  }

  // If not logged in, redirect to backend login endpoint
  window.location.href = '/api/login'
})

export default router

