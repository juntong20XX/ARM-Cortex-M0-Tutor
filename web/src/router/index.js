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

// 全局路由守卫：除白名单外必须已登录
router.beforeEach((to, from, next) => {
  const whiteList = ['/login', '/login-oauth', '/demo/embed']

  // 白名单路径（含 /login-oauth 下的所有子路径）直接放行
  if (whiteList.some((path) => to.path === path || to.path.startsWith(`${path}/`))) {
    next()
    return
  }

  const { isAuthenticated, loadSession } = useSession()
  // 确保从 localStorage 恢复会话
  loadSession()

  if (isAuthenticated.value) {
    next()
    return
  }

  // 未登录则跳转到后端登录入口
  window.location.href = '/api/login'
})

export default router

