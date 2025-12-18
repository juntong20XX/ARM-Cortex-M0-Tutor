# Web 前端开发文档

## 项目概述

本项目是 ARM Cortex-M0 教学系统的前端应用，基于 Vue 3 和 Vite 构建。前端与后端共享相同的二级域名，通过 `/api` 路径前缀访问后端 API。

## 技术栈

- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite 7.x
- **路由**: Vue Router 4.x
- **开发工具**: Vue DevTools

## 项目结构

```
web/
├── public/                 # 静态资源
│   └── favicon.ico
├── src/
│   ├── assets/            # 资源文件
│   │   ├── base.css      # 基础样式
│   │   ├── main.css      # 主样式
│   │   ├── login.css     # 登录页样式
│   │   └── logo.svg      # Logo
│   ├── composables/       # 组合式函数
│   │   └── useSession.js  # 会话管理
│   ├── router/            # 路由配置
│   │   └── index.js
│   ├── views/             # 页面组件
│   │   ├── HomeView.vue  # 首页
│   │   ├── Login.vue     # 登录页
│   │   └── LoginOAuth.vue # OAuth 回调页
│   ├── App.vue           # 根组件
│   └── main.js           # 入口文件
├── index.html            # HTML 模板
├── vite.config.js        # Vite 配置
├── package.json          # 项目依赖
└── develop_zh.md         # 本文档
```

## 开发环境设置

### 前置要求

- Node.js: `^20.19.0` 或 `>=22.12.0`
- npm 或 yarn

### 安装依赖

```bash
npm install
```

### 开发模式

启动开发服务器（支持热重载）：

```bash
npm run dev
```

默认访问地址：`http://localhost:5173`

### 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录。

### 预览生产构建

```bash
npm run preview
```

## 路由配置

### 路由列表

| 路径 | 名称 | 组件 | 说明 |
|------|------|------|------|
| `/` | `home` | `HomeView` | 首页 |
| `/login` | `login` | `Login` | 登录页 |
| `/login-oauth/:providerName` | `login-oauth` | `LoginOAuth` | OAuth 回调页 |
| `/*` | - | - | 404 重定向到首页 |

### 路由参数

- `/login-oauth/:providerName`: 动态路由参数，接收 OAuth 提供商名称（如 `github`、`google` 等）

## 会话管理

### useSession Composable

项目提供了 `useSession` 组合式函数来管理用户会话状态。

**位置**: `src/composables/useSession.js`

### API 说明

```javascript
import { useSession } from '@/composables/useSession'

const {
  session,          // 响应式会话对象（包含 uuid, display_name, timestamp）
  isAuthenticated,  // 计算属性：是否已认证
  userUuid,         // 计算属性：用户 UUID
  userDisplayName,  // 计算属性：用户显示名称
  saveSession,      // 函数：保存会话
  clearSession,     // 函数：清除会话
  loadSession       // 函数：加载会话
} = useSession()
```

### 使用示例

```javascript
<script setup>
import { useSession } from '@/composables/useSession'

const { saveSession, clearSession, isAuthenticated, userUuid } = useSession()

// 保存会话
function handleLogin(userData) {
  saveSession({
    uuid: userData.uuid,
    display_name: userData.display_name
  })
}

// 清除会话（登出）
function handleLogout() {
  clearSession()
}

// 检查登录状态
if (isAuthenticated.value) {
  console.log('用户已登录:', userUuid.value)
}
</script>
```

### 存储机制

- **存储方式**: `localStorage`
- **存储键名**: `user_session`
- **数据结构**:
  ```json
  {
    "uuid": "用户UUID",
    "display_name": "用户显示名称",
    "timestamp": "2025-12-08T10:30:00.000Z"
  }
  ```

## OAuth 登录流程

### 流程说明

1. **用户访问登录页** (`/login`)
   - 前端调用后端 `/api/login` 接口
   - 后端根据配置重定向到 OAuth 提供商

2. **OAuth 认证**
   - 用户在 OAuth 提供商页面完成认证
   - OAuth 提供商回调到前端页面：`/login-oauth/{providerName}?code=xxx&state=xxx`

3. **前端处理回调** (`LoginOAuth.vue`)
   - 读取 URL 查询参数（`code`、`state` 等）
   - 将参数转发到后端 API：`/api/login-oauth/{providerName}?code=xxx&state=xxx`
   - 后端完成 token 交换和用户信息获取

4. **保存会话**
   - 登录成功后，前端自动保存用户的 `uuid` 和 `display_name` 到 `localStorage`
   - 页面显示用户信息

### LoginOAuth 组件

**位置**: `src/views/LoginOAuth.vue`

**功能**:
- 接收 OAuth 回调参数
- 转发参数到后端 API
- 显示登录状态和用户信息
- 自动保存会话信息

**状态**:
- `idle`: 等待处理
- `loading`: 正在验证授权
- `success`: 登录成功
- `error`: 登录失败

## API 集成

### API 基础路径

前端通过 `/api` 路径访问后端 API，需要配置反向代理（如 Nginx、Traefik）将请求转发到后端服务。

### 主要 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/login` | GET | 登录入口，根据配置重定向 |
| `/api/login-oauth/{providerName}` | GET | OAuth 回调处理 |

### API 请求示例

```javascript
// OAuth 登录回调
const res = await fetch(`/api/login-oauth/${providerName}?code=${code}&state=${state}`, {
  method: 'GET',
  credentials: 'include'  // 包含 cookies（用于会话）
})

const data = await res.json()
```

### 响应格式

**成功响应**:
```json
{
  "success": true,
  "uuid": "用户UUID",
  "display_name": "用户显示名称",
  "email": "user@example.com",
  "groups": ["group1", "group2"],
  "join_date": "2025-01-01T00:00:00",
  "last_login": "2025-12-08T10:30:00",
  "login_source": "oauth",
  "msg": "登录成功"
}
```

**失败响应**:
```json
{
  "success": false,
  "msg": "错误信息",
  "uuid": "0",
  "display_name": "0",
  "email": "0",
  "groups": [],
  "join_date": "2025-12-08T10:30:00",
  "last_login": "2025-12-08T10:30:00",
  "login_source": "oauth"
}
```

## 开发指南

### 添加新页面

1. 在 `src/views/` 目录下创建新的 Vue 组件
2. 在 `src/router/index.js` 中添加路由配置：

```javascript
import NewView from '../views/NewView.vue'

{
  path: '/new-page',
  name: 'new-page',
  component: NewView
}
```

### 使用会话信息

在任何组件中使用会话信息：

```javascript
<script setup>
import { useSession } from '@/composables/useSession'

const { isAuthenticated, userUuid, userDisplayName } = useSession()
</script>

<template>
  <div v-if="isAuthenticated">
    <p>欢迎, {{ userDisplayName }}!</p>
    <p>UUID: {{ userUuid }}</p>
  </div>
</template>
```

### 样式规范

- 使用 scoped CSS 避免样式污染
- 主要颜色：`#2563eb` (蓝色)
- 圆角：`10px` - `14px`
- 间距：使用 `12px`、`16px`、`18px` 等

### 路径别名

项目配置了路径别名 `@`，指向 `src/` 目录：

```javascript
import { useSession } from '@/composables/useSession'
import HomeView from '@/views/HomeView.vue'
```

## 部署说明

### 构建配置

生产构建会生成静态文件到 `dist/` 目录，需要配置 Web 服务器（如 Nginx）来：

1. 提供静态文件服务
2. 将 `/api/*` 请求代理到后端服务
3. 配置 SPA 路由回退（所有路由回退到 `index.html`）

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 静态文件
    root /path/to/web/dist;
    index index.html;

    # SPA 路由回退
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 常见问题

### Q: 如何清除用户会话？

A: 调用 `clearSession()` 函数：

```javascript
import { useSession } from '@/composables/useSession'
const { clearSession } = useSession()
clearSession()
```

### Q: OAuth 回调失败怎么办？

A: 检查以下几点：
1. 后端 OAuth 配置是否正确
2. 回调 URL 是否与 OAuth 提供商配置一致
3. 网络请求是否正常（查看浏览器控制台）

### Q: 如何调试会话状态？

A: 在浏览器开发者工具中：
1. 打开 Application/Storage → Local Storage
2. 查看 `user_session` 键的值
3. 或在组件中使用 `console.log(session.value)` 查看当前会话

## 开发工具推荐

### IDE 插件

- **VS Code**: [Vue Language Features (Volar)](https://marketplace.visualstudio.com/items?itemName=Vue.volar)
- 禁用 Vetur（如果已安装）

### 浏览器扩展

- **Chrome/Edge**: [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
- **Firefox**: [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)

## 更新日志

### 2025-12-08
- 添加前端会话管理机制（`useSession` composable）
- OAuth 回调地址改为前端路径 `/login-oauth/{providerName}`
- 登录成功后自动保存用户 UUID 和显示名称
- 添加 `last_login` 字段显示

## 参考资源

- [Vue 3 文档](https://vuejs.org/)
- [Vue Router 文档](https://router.vuejs.org/)
- [Vite 文档](https://vite.dev/)
- [Composition API 指南](https://vuejs.org/guide/extras/composition-api-faq.html)
