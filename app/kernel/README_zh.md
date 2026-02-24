# app/kernel 模块说明

本模块负责**连接“执行环境（QEMU/GDB）”与“数据（汇编、寄存器、单步状态）”**，为 ARM Cortex-M0 教学/调试提供：汇编解析、QEMU 仿真、GDB 单步执行，以及前端动画所需的 ADL（Animation Description Language）数据模型。

---

## 目录结构

| 路径 | 职责 |
|------|------|
| `__init__.py` | 模块统一导出：Config、Invoke 任务、汇编/单步类型、`adl_models` |
| `connector/__init__.py` | 配置 `Config`、Invoke 任务（clean/setup/build/start_qemu/stop_qemu/debug）、汇编与单步类型导出 |
| `connector/asm_basic.py` | 汇编行解析：`ASMLine`、`ASMParam`、`ASMLineReader`（指令/参数正则） |
| `connector/connector.py` | GDB 连接与单步：`ALoader`（连 QEMU、单步、反汇编、读寄存器）、`ASMStep` |
| `animation/adl_models.py` | ADL v1 的 Pydantic 模型：`TraceResponse`、`TraceStep`、各类 `ADLEvent` 等 |

对外使用方式不变：所有类型与任务均从 `app.kernel` 导入，无需关心子包路径。

---

## 主要组件

### 1. 配置 `Config`

用于指定工程路径、QEMU/GDB 参数、目标 ELF 等。`*_PATH`、`*_ARGS` 结尾的字段会通过 `get_format_map()` 自动展开（如 `{PROJECT_DIR}`、`{uuid}`）。

```python
from app.kernel import Config

config = Config(uuid="my-session")
mapping = config.get_format_map()
# mapping["build_path"], mapping["sockets_path"] 等可用
```

常用字段：`SOURCE_DIR`、`PROJECT_DIR`、`BUILD_PATH`、`QEMU_BIN`、`GDB_BIN`、`TARGET_NAME`、`SOCKETS_PATH` 等。  
内存变化监视：`MEMORY_WATCH_START`（默认 `0x20000000`，Cortex-M0 microbit RAM 起始）、`MEMORY_WATCH_SIZE`（字节数，默认 512；设为 0 则不读内存，`ASMStep.memory_delta` 恒为 None）。

### 2. 汇编解析：`ASMLine`、`ASMParam`、`ASMLineReader`

- **ASMLine**：表示一行汇编（助记符、条件码、最多三个参数），支持 `to_code()` 写回为 asm 文本。
- **ASMParam**：单个操作数，含 `text` 与 `type_name`（如 `r`、`i`、`c`）。
- **ASMLineReader**：根据已知指令/参数正则，将字符串解析为 `ASMLine`。

```python
from app.kernel import ASMLineReader, ASMLine, ASMParam

reader = ASMLineReader()
line = reader.load("adds r0, r1, #0x5")  # 得到 ASMLine
code = line.to_code()                     # 转回可写入 asm.s 的字符串
```

### 3. 单步执行：`ALoader`、`ASMStep`

- **ALoader**：连接 GDB 与 QEMU 的 GDB 套接字，在汇编范围内单步执行；可迭代，每次返回一个 `ASMStep`。
- **ASMStep**：单步结果，包含：
  - `line_counter`：当前步序号（由 ALoader 维护）
  - `addr_pc`：PC 地址（十六进制字符串）
  - `disassemble`：当前 PC 附近反汇编 `( (address, ASMLine), ... )`
  - `register_values`：r0–r15 及 N/Z/C/V 的 `(name, value)` 元组序列
  - `memory_delta`：本步发生变化的地址（hex 字符串）→ 新字节值（0–255）的映射；未启用内存监视或本步无变化时为 `None`。可直接赋给 ADL `StepSnapshot.memoryDelta`。

```python
from app.kernel import Config, debug, start_qemu, build, ASMLineReader
from invoke import Context

config = Config(uuid="demo")
c = Context()
build(c, config)  # 需已 setup 并写好 asm
start_qemu(c, config)
loader = debug(c, config, asm_reader=ASMLineReader())

for step in loader:
    print(step.addr_pc, step.register_values)
# 离开 .s/.S 或结束时会 StopIteration
```

使用完毕可 `loader.exit()` 或依赖 `__exit__`/`__del__` 关闭 GDB。

### 4. Invoke 任务

在 `Context` 中调用，用于工程与 QEMU 生命周期管理：

| 任务 | 说明 |
|------|------|
| `clean(c, config)` | 删除工程目录 |
| `setup(c, config, asm_list)` | 创建工程/构建目录，复制源码，并根据 `asm_list` 写入 `asm.s` |
| `build(c, config)` | CMake 配置与编译（依赖 setup） |
| `start_qemu(c, config)` | 启动 QEMU，加载 ELF，等待 GDB 连接 |
| `stop_qemu(c, config)` | 停止对应 uuid 的 QEMU 进程 |
| `debug(c, config, asm_reader)` | 启动 GDB、连接 QEMU，返回 `ALoader`（依赖 start_qemu） |

### 5. ADL 模型（`adl_models`）

用于与前端动画约定格式，详见项目内 `ADL_SPEC`。主要类型：

- **TraceResponse**：顶层响应，含 `adlVersion`、`code`、`initialState`、`steps`。
- **TraceStep**：单步，含 `snapshot`（PC、寄存器、标志位等）和 `events`（动画事件列表）。
- **ADLEvent**：如 `SetActiveLine`、`FocusCanvas`、`MarkRegister`、`OverlayArrow`、`AnnotateBus`、`Wait` 等。

在 API 中返回 trace 时，可直接构造并序列化这些模型：

```python
from app.kernel import adl_models

resp = adl_models.TraceResponse(
    adlVersion=1,
    code=[adl_models.CodeLine(text="...", addr="0x...")],
    initialState=adl_models.InitialState(registers={...}, flags=...),
    steps=[adl_models.TraceStep(snapshot=..., events=[...])],
)
# 返回给前端（如 .model_dump()）
```

---

## 依赖与环境

- **QEMU**：需安装 `qemu-system-arm`，且支持 `-M microbit`（Cortex-M0）。
- **GCC**: `arm-none-eabi-gcc` 工具链（用于编译 `.s` 文件）。
- **GDB**：`arm-none-eabi-gdb` (对于 debian, 是 `gdb-multiarch`)，支持 MI 接口。
- **Python**：`pygdbmi`、`invoke`、`pydantic`（adl_models）。

工程源码目录由 `Config.SOURCE_DIR` 指定，默认指向仓库内 `qemu_m0`；构建输出在 `PROJECT_DIR/build-{uuid}/`。

---

## 导出清单

从 `app.kernel` 可直接导入：

- 配置与任务：`Config`, `clean`, `setup`, `build`, `start_qemu`, `stop_qemu`, `debug`
- 汇编与单步：`ASMLine`, `ASMParam`, `ASMLineReader`, `ASMStep`, `ALoader`
- ADL：通过 `from app.kernel import adl_models` 使用各 ADL 类型
