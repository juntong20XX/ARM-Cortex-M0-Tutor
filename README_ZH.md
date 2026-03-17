# ARM Cortex-M0 可视化模拟器

一个基于 Web 的开源 ARM Cortex-M0 处理器可视化模拟器，通过逐步动画演示汇编代码的执行过程，帮助学生理解微处理器内部原理。

> **项目动机：** 学习微处理器时，学生面对的是一个"黑盒"——代码输入，结果输出，但寄存器变化和指令流向完全不可见。本项目让处理器变得透明：每一步都能实时看到数据在寄存器、ALU 与内存之间的流动，只需一个浏览器，无需安装任何工具。

---

## 功能特性

- **可视化单步调试** — 每条指令执行后，寄存器、标志位和内存的变化一目了然，类似 [pythontutor.com](https://pythontutor.com/python-compiler.html) 对 Python 的可视化调试。
- **100% 基于 Web** — 终端用户无需安装 IDE 或本地工具链，打开浏览器即可使用。
- **真实 ARM Cortex-M0 执行** — 底层由 QEMU + GDB 驱动，在指令级别实现精确仿真。
- **ADL 动画层** — 动画描述语言（ADL）将原始执行轨迹转化为前端动画事件（箭头、高亮、总线标注）。
- **多用户平台** — 支持用户账户、项目管理、OAuth 与密码认证、公告系统以及基于用户组的访问控制。
- **开放核心（Open Core）** — 核心仿真功能免费开源；可在此基础上构建机构级功能（课堂管理、学情分析）。

---

## 架构总览

```
┌─────────────────────────────────────────┐
│              Web 前端                   │
│          (Vue.js, web/)                 │
└────────────────┬────────────────────────┘
                 │ REST API (ADL JSON)
┌────────────────▼────────────────────────┐
│           FastAPI 后端                  │
│   /api/trace  /api/project              │
│   /api/session  /api/user               │
│   /api/announcements                    │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │         app/kernel               │   │
│  │  ASMLineReader → QEMU → GDB      │   │
│  │  ALoader（单步迭代器）           │   │
│  │  ADL 模型构建器                  │   │
│  └──────────────────────────────────┘   │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │       SQLAlchemy 数据库          │   │
│  │  用户、项目、用户组              │   │
│  │  OAuth 提供商、公告              │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### 核心模块说明

| 路径 | 职责 |
|------|------|
| `app/kernel/` | 仿真核心：汇编解析、QEMU/GDB 生命周期、单步迭代器、ADL 模型 |
| `app/apis/` | FastAPI 路由：trace、project、session、user、user_groups、announcements |
| `app/database/` | SQLAlchemy ORM 模型与数据库工具 |
| `app/core/` | 配置、安全、日志（defender，与网络无关） |
| `app/services/` | 依赖网络层的业务逻辑 |
| `web/` | Vue.js 前端 |
| `example/` | 部署示例（Authelia 认证、Traefik 反向代理） |

---

## 环境依赖

### 系统依赖

| 工具 | 包名（Debian/Ubuntu） | 说明 |
|------|----------------------|------|
| QEMU | `qemu-system-arm` | 需支持 `-M microbit`（Cortex-M0） |
| ARM GDB | `gdb-multiarch`（Debian）/ `arm-none-eabi-gdb`（Arch/Manjaro） | 需支持 MI 接口 |
| ARM GCC | `gcc-arm-none-eabi`、`binutils-arm-none-eabi` | 用于编译 `.s` 汇编文件 |
| CMake | `cmake` | 构建 ELF 二进制文件 |
| Python | `python3`（3.11+） | 后端运行时 |

Debian/Ubuntu 一键安装：

```bash
sudo apt-get install qemu-system-arm gdb-multiarch gcc-arm-none-eabi \
    binutils-arm-none-eabi cmake python3 python3-pip
```

### Python 依赖

```bash
pip install -r app/requirements.txt
```

核心包：`fastapi[all]`、`SQLAlchemy`、`pygdbmi`、`invoke`、`pydantic`、`authlib`、`passlib[argon2,bcrypt]`、`python-jose[cryptography]`。

---

## 配置说明

### 应用配置（`config.toml`）

在工作目录下创建 `config.toml`，然后再启动服务：

```toml
database_url = "sqlite:///./app.db"
secret_key   = "your-secret-key-here"
login_action = "oauth_pw"   # password | oauth | oauth_pw | username_domain | direct_oauth
```

该文件为可选项；`database_url` 也可通过环境变量 `database_url` 设置。

### 仿真核心配置（`connector.Config`）

核心通过 `app.kernel.Config` 配置，最少需要填写以下字段：

```python
from app.kernel import Config

config = Config(
    uuid="my-session",        # 项目/会话标识符（任意字符串）
    PROJECT_DIR="/tmp/proj",  # 构建产物输出目录
)
```

常用字段说明：

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `uuid` | — | **必填。** 会话/项目标识符 |
| `PROJECT_DIR` | — | **必填。** 构建产物输出目录 |
| `GDB_BIN` | `arm-none-eabi-gdb` | Debian 系统下需改为 `gdb-multiarch` |
| `QEMU_BIN` | `qemu-system-arm` | QEMU 可执行文件路径 |
| `SOCKETS_PATH` | Unix Socket 路径 | Windows 下设为 `":1234"`（使用 TCP 端口） |
| `QEMU_GDB_ARGS` | `""` | QEMU GDB Server 额外参数 |
| `MEMORY_WATCH_START` | `0x20000000` | 内存变化监视起始地址（Cortex-M0 microbit RAM 起始） |
| `MEMORY_WATCH_SIZE` | `512` | 监视字节数；设为 `0` 则禁用内存追踪 |

**Windows 说明：** Windows 不支持 Unix Socket，需按如下方式配置：

```python
config = Config(
    uuid="demo",
    PROJECT_DIR="C:/tmp/proj",
    SOCKETS_PATH=":1234",
    QEMU_GDB_ARGS="",   # QEMU 将在 1234 端口启动 GDB Server
)
```

---

## 启动应用

### 后端

后端没有内置启动脚本，需使用配置了 Session 中间件和数据库的启动器。可参考 `prototyping/login-demo.py`：

生产环境请在工作目录创建 `config.toml`（或通过环境变量设置 `database_url`）。API 地址：`http://localhost:8000`；交互式文档（Swagger UI）：`http://localhost:8000/docs`。

### 前端

```bash
cd web
npm install
npm run dev        # 开发服务器 http://localhost:5173
npm run build      # 生产构建 → dist/
npm run preview    # 预览生产构建
```

Vite 开发服务器**不会**代理到后端，需单独启动后端，必要时配置 CORS (参考 example 中的反向代理和正向代理示例)。

---

## Docker 部署

（已过期）

---

## 测试

测试代码在 `test/` 路径下。 使用 unitest 构建。

---

## API 接口概览

所有路由均以 `/api` 为前缀。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/trace` | 返回静态示例 ADL Trace（供演示使用） |
| `GET` | `/api/trace/{project_uuid}` | 执行项目并返回 ADL Trace |
| `GET` | `/api/project/trace?uuid=…` | 同上，使用查询参数版本 |
| `GET/POST` | `/api/project` | 列出 / 创建项目 |
| `GET/PUT/DELETE` | `/api/project/{uuid}` | 读取 / 更新 / 删除项目 |
| `GET` | `/api/login` | 登录（重定向至 OAuth 或密码表单） |
| `GET` | `/api/logout` | 登出 |
| `GET` | `/api/user/me` | 获取当前用户信息 |
| `GET/POST/PUT/DELETE` | `/api/user-groups` | 列出 / 创建 / 更新 / 删除用户组 |
| `GET` | `/api/announcements` | 列出可见公告 |

Trace 接口返回符合 **ADL v1** 规范的 `TraceResponse` JSON，由前端动画引擎消费。

---

## Kernel Python API 使用示例

```python
from app.kernel import Config, setup, build, start_qemu, stop_qemu, debug, ASMLineReader
from invoke import Context

config = Config(uuid="demo", PROJECT_DIR="/tmp/demo", GDB_BIN="gdb-multiarch")
reader = ASMLineReader()

# 解析汇编行
asm_list = [reader.load(line) for line in [
    "movs r0, #1",
    "movs r1, #2",
    "adds r2, r0, r1",
]]

c = Context()
setup(c, config, asm_list)   # 创建项目目录并写入 asm.s
build(c, config)              # 用 CMake + arm-none-eabi-gcc 编译
start_qemu(c, config)         # 启动 QEMU，等待 GDB 连接

loader = debug(c, config)     # 连接 GDB，返回单步迭代器
for step in loader:
    print(step.addr_pc, dict(step.register_values))

loader.exit()
stop_qemu(c, config)
```

### `ASMStep` 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `line_counter` | `int` | 步骤序号 |
| `addr_pc` | `str` | 程序计数器（十六进制字符串） |
| `disassemble` | tuple | 当前 PC 附近的反汇编 `((地址, ASMLine), …)` |
| `register_values` | tuple | r0–r15 及 N/Z/C/V 标志位的 `(名称, 值)` 元组序列 |
| `memory_delta` | `dict \| None` | 本步变化的内存字节 `{十六进制地址: 字节值}`；未启用时为 `None` |

---

## 项目结构

```
ARM-Cortex-M0-Tutor/
├── app/
│   ├── app.py               # 裸 FastAPI 实例（中间件由调用方配置）
│   ├── kernel/
│   │   ├── connector/       # Config、ALoader、ASMLine 解析器、GDB/QEMU 任务
│   │   ├── animation/       # ADL Pydantic 模型、step→ADL 转换（step_to_adl.py）
│   │   └── qemu_m0/         # CMake 工程、startup.c、链接脚本（microbit 板）
│   ├── apis/
│   │   ├── main.py          # 聚合所有路由 → api_router（前缀 /api）
│   │   └── routes/          # trace、project、session、user、user_groups、announcements
│   ├── database/            # SQLAlchemy 模型、dbtools、enter（db_context）
│   ├── core/                # 配置、安全、defender（日志）
│   └── services/            # 业务逻辑工具
├── web/                     # Vue 3 前端（Vite、Element Plus）
├── prototyping/             # 演示启动器（如 login-demo.py）
├── example/
│   ├── auth-system/         # Authelia docker-compose 示例
│   └── reverse-proxy/       # Traefik docker-compose 示例
├── test/                    # 单元测试
├── Dockerfile               # Debian + QEMU/ARM 工具链 + Jupyter
└── config.toml              # （需自行创建，不提交到版本库）
```

---

## 许可证

详见 [LICENSE](LICENSE)。
