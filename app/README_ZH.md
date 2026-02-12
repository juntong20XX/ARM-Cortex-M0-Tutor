# app: 项目后端

项目网络部分, 采用前后端分离架构. 这个是后端文件.

后端框架使用 fastapi.

数据库使用 SQLAlchemy.

## 文件架构

- `__main__.py`

- `app.py`
  - 启动后端

- `apis/`
  - 构建 `api_router: fastapi.APIRouter` 对象

- `core/`
  - Network-independent tools. 

- `database/`

- `services/`
  - Network-dependent tools.
