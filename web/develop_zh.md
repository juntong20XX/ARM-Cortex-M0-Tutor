# Web 前端开发文档

## 项目概述

本项目是 ARM Cortex-M0 教学系统的前端应用，基于 Vue 3 和 Vite 构建。前端与后端共享相同的二级域名，通过 `/api` 路径前缀访问后端 API。

## 技术栈

- **框架**: Vue 3 (Composition API)
- **语言**: TypeScript
- **UI 组件库**: Element Plus
- **代码编辑器**: Vue Prism Editor + PrismJS
- **构建工具**: Vite 7.x
- **路由**: Vue Router 4.x
- **开发工具**: Vue DevTools

## 项目结构

```
web/
├── public/                 # 静态资源
│   └── favicon.ico
├── src/
│   ├── animation/         # ADL 动画与 Trace 播放
│   │   ├── adl-types.ts   # ADL v1 类型定义
│   │   ├── adl-schema.json # ADL JSON Schema
│   │   ├── ADL_SPEC.md    # ADL 规范与示例
│   │   ├── tracePlayer.ts # Trace 播放器（batch/stream）
│   │   ├── streaming.ts  # SSE 流式消费预留
│   │   └── index.ts       # 统一导出
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
│   │   ├── HomeView.vue      # 首页
│   │   ├── Login.vue         # 登录页
│   │   ├── LoginOAuth.vue    # OAuth 回调页
│   │   ├── DemoWorkspace.vue  # Demo 工作区组件（可复用）
│   │   ├── Demo.vue          # Demo 全屏页面（包装 DemoWorkspace）
│   │   └── DemoEmbedView.vue # Demo iframe 嵌入页面（包装 DemoWorkspace）
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
| `/demo` | `demo` | `Demo` | 原型演示页（全屏） |
| `/demo/embed` | `demo-embed` | `DemoEmbedView` | 用于 iframe 嵌入的 Demo 布局 |
| `/*` | - | - | 404 重定向到首页 |

### 路由参数

- `/login-oauth/:providerName`: 动态路由参数，接收 OAuth 提供商名称（如 `github`、`google` 等）

### Demo iframe 嵌入

为方便在其他系统或页面中复用 Demo 布局，前端提供 `/demo/embed` 路径用于 iframe 嵌入。

#### 在当前应用内部使用

```vue
<iframe
  src="/demo/embed"
  style="width: 100%; height: 600px; border: none;"
></iframe>
```

#### 在外部站点中使用

```html
<iframe
  src="https://your-domain/demo/embed"
  width="100%"
  height="600"
  style="border:none; overflow:hidden;"
  referrerpolicy="strict-origin-when-cross-origin"
></iframe>
```

- **认证**：当前 `/demo/embed` 已加入路由白名单，默认不需要登录即可访问。若未来希望保护该页面，需要同步调整路由守卫逻辑以及部署端的认证配置。
- **高度控制**：推荐由父页面直接设置 iframe 高度（如固定 `600px` 或 `100vh`）。如需自动高度，可在后续通过 `postMessage` 协议扩展，由 iframe 内容向父页面上报实际高度。

## 会话管理

### useSession Composable

项目提供了 `useSession` 组合式函数来管理用户会话状态。

**位置**: `src/composables/useSession.js`

### API 说明

```typescript
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

```typescript
<script setup lang="ts">
import { useSession } from '@/composables/useSession'

interface UserData {
  uuid: string
  display_name: string
}

const { saveSession, clearSession, isAuthenticated, userUuid } = useSession()

// 保存会话
function handleLogin(userData: UserData): void {
  saveSession({
    uuid: userData.uuid,
    display_name: userData.display_name
  })
}

// 清除会话（登出）
function handleLogout(): void {
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
| `/api/trace` | GET | 获取 ADL 动画 Trace（可选；未实现时 Demo 使用本地 fallback） |

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

## ADL 动画与 Trace 播放

Demo 页的指令动画由**动画描述语言（ADL）**驱动：后端返回 Trace（步骤快照 + 事件列表），前端解析并执行。

### 相关文件

| 文件 | 说明 |
|------|------|
| `src/animation/ADL_SPEC.md` | ADL v1 规范、StepSnapshot/AnchorRef/事件类型、示例 payload |
| `src/animation/adl-schema.json` | ADL 的 JSON Schema |
| `src/animation/adl-types.ts` | TraceResponse、StepSnapshot、ADLEvent、AnchorRef 等 TypeScript 类型 |
| `src/animation/tracePlayer.ts` | `playTrace()` 批量播放、`playTraceStream()` 流式播放 |
| `src/animation/streaming.ts` | SSE 流式消费预留（`streamTraceStepsFromSSE`） |

### Trace 响应结构（概要）

- **TraceResponse**: `adlVersion`, `code?`, `initialState?`, `steps[]`
- **每步 (TraceStep)**: `snapshot`（pc、registers、flags、memoryDelta）+ `events[]`
- **事件类型**: `SetActiveLine`、`FocusCanvas`、`MarkRegister`、`OverlayArrow`、`AnnotateBus`、`Wait`
- **锚点 (AnchorRef)**: `CodeLineAddr`、`PC`、`RegisterRow`、`CanvasComponent`

详见 `src/animation/ADL_SPEC.md`。

### Demo 页行为

1. 点击「Run Demo」时先请求 `GET /api/trace`。
2. 若返回合法 Trace（`adlVersion === 1` 且 `steps` 为数组），则用 **TracePlayer** 按 ADL 播放。
3. 若请求失败或无 Trace，则使用**本地 fallback**（硬编码的 ADD 示例动画）。

### 使用 TracePlayer（其他页面）

```typescript
import { playTrace, playTraceStream } from '@/animation'
import type { TraceResponse, TracePlayerDriver } from '@/animation'

const driver: TracePlayerDriver = {
  applySnapshot(snapshot) { /* 更新寄存器/Flags/内存 */ },
  setActiveLine(index) { /* 高亮代码行 */ },
  setCanvasFocus(target) { /* CU | REG | ALU | None */ },
  markRegister(reg, mode) { /* read | write | clear */ },
  setOverlay(from, to, text) { /* 解析锚点坐标并画箭头 */ },
  wait(ms) { return new Promise(r => setTimeout(r, ms)) }
}

// 批量播放
await playTrace(traceResponse, { driver, speed: 1 })

// 流式播放（预留，需后端 SSE）
// const steps = streamTraceStepsFromSSE(new EventSource('/api/trace/stream'))
// await playTraceStream(steps, { driver, speed: 1 })
```

### 流式 (SSE) 预留

单步数据结构与 `TraceResponse.steps[]` 中元素一致。后端若提供 SSE（如 `EventSource('/api/trace/stream')`），前端可用 `streamTraceStepsFromSSE(es)` 得到 `AsyncIterable<TraceStep>`，再传入 `playTraceStream()`。

## 开发指南

### 添加新页面

1. 在 `src/views/` 目录下创建新的 Vue 组件（推荐使用 TypeScript）
2. 在 `src/router/index.js` 中添加路由配置：

```javascript
import NewView from '../views/NewView.vue'

{
  path: '/new-page',
  name: 'new-page',
  component: NewView
}
```

### 新页面模板示例

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { HomeFilled } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref<boolean>(false)

const handleAction = async (): Promise<void> => {
  loading.value = true
  try {
    // 业务逻辑
    ElMessage.success('操作成功')
  } catch (err) {
    ElMessage.error((err as Error).message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="hover">
      <template #header>
        <h1>页面标题</h1>
      </template>
      
      <el-button
        type="primary"
        :loading="loading"
        @click="handleAction"
      >
        操作按钮
      </el-button>
      
      <el-button :icon="HomeFilled" @click="router.push('/')">
        返回首页
      </el-button>
    </el-card>
  </div>
</template>

<style scoped>
.page-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
</style>
```

### 使用会话信息

在任何组件中使用会话信息：

```vue
<script setup lang="ts">
import { useSession } from '@/composables/useSession'

const { isAuthenticated, userUuid, userDisplayName } = useSession()
</script>

<template>
  <el-card v-if="isAuthenticated">
    <el-descriptions :column="1" border>
      <el-descriptions-item label="Welcome">
        <el-text type="success">{{ userDisplayName }}</el-text>
      </el-descriptions-item>
      <el-descriptions-item label="UUID">
        <el-text type="primary" tag="code">{{ userUuid }}</el-text>
      </el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>
```

### 样式规范

- 使用 scoped CSS 避免样式污染
- 使用 Element Plus 组件库进行 UI 开发
- Element Plus 主题色：`#409EFF` (蓝色)
- 背景渐变：`linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- 卡片圆角：`16px`
- 间距：使用 `12px`、`16px`、`20px`、`24px` 等

### Element Plus 常用组件

| 组件 | 用途 |
|------|------|
| `el-card` | 卡片容器 |
| `el-button` | 按钮 |
| `el-alert` | 提示/状态信息 |
| `el-descriptions` | 描述列表 |
| `el-tag` | 标签 |
| `el-text` | 文本 |
| `el-link` | 链接 |
| `el-icon` | 图标 |
| `el-space` | 间距容器 |
| `el-divider` | 分割线 |
| `el-message` | 消息提示 |
| `el-collapse-transition` | 折叠过渡动画 |

### Element Plus 图标使用

图标来自 `@element-plus/icons-vue` 包：

```typescript
import {
  User,
  Lock,
  Loading,
  CircleCheckFilled,
  CircleCloseFilled,
  Clock,
  Refresh,
  HomeFilled,
  SwitchButton
} from '@element-plus/icons-vue'
```

在模板中使用：

```vue
<el-icon><User /></el-icon>
<el-button :icon="Refresh">刷新</el-button>
```

### 路径别名

项目配置了路径别名 `@`，指向 `src/` 目录：

```javascript
import { useSession } from '@/composables/useSession'
import HomeView from '@/views/HomeView.vue'
```

## 构建优化

### 体积优化策略

项目采用了以下策略来优化构建产物体积：

1. **组件按需加载**
   - 使用 `unplugin-vue-components` 和 `unplugin-auto-import` 插件
   - 自动按需引入 Element Plus 组件，避免全量打包
   - `vite.config.js` 中配置相应的 resolvers

2. **代码分包 (Code Splitting)**
   - 在 `vite.config.js` 的 `rollupOptions` 中配置 `manualChunks`
   - 将第三方依赖拆分为独立 chunk：
     - `element-plus`: UI 库单独打包
     - `prism`: 代码高亮库单独打包
     - `vue-vendor`: Vue 核心库
     - `vendor`: 其他依赖

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

### 2026-02-17
- **ADL 动画与 Trace 播放**
  - 新增 `src/animation/`：ADL v1 类型、JSON Schema、规范文档（`ADL_SPEC.md`）
  - 实现 Trace 播放器：`playTrace()` 批量播放、`playTraceStream()` 流式预留
  - Demo 页支持 ADL 驱动：请求 `GET /api/trace`，有则按 Trace 播放，否则走本地 fallback
  - 锚点解析（CodeLineAddr / RegisterRow / CanvasComponent / PC）与 overlay 箭头
  - 预留 SSE 消费：`streamTraceStepsFromSSE()`，与后端流式协议一致

### 2025-12-18
- 新增 `/demo` 原型演示页面
  - 集成 `vue-prism-editor` 实现代码编辑（带行号、高亮）
  - 实现寄存器 (R0-R13) 和内存可视化展示
- 构建与性能优化
  - 配置 `unplugin-vue-components` 和 `unplugin-auto-import` 实现 Element Plus 按需加载
  - 优化 Vite 构建配置，实施 Manual Chunks 代码分包策略，大幅减小打包体积
- 引入 Element Plus UI 组件库
- 使用 TypeScript 重写 `Login.vue` 和 `LoginOAuth.vue`
- 使用 `el-card`、`el-alert`、`el-descriptions`、`el-button` 等组件重构 UI
- 添加 `ElMessage` 消息提示功能
- 添加响应式布局支持移动端
- 添加过渡动画效果 (`el-collapse-transition`)
- 更新入口文件 `main.js`，全局注册 Element Plus

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
- [Element Plus 文档](https://element-plus.org/)
- [Element Plus 图标](https://element-plus.org/zh-CN/component/icon.html)
- [TypeScript 文档](https://www.typescriptlang.org/docs/)
