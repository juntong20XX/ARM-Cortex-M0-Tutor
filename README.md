# ARM Cortex-M0 Visual Simulator

A web-based, open-source visual simulator for the ARM Cortex-M0 processor, designed to help students understand microprocessor internals through step-by-step, animated execution of assembly code.

> **Motivation:** When learning microprocessors, students face a "black box" — code goes in, results come out, but register changes and instruction flow are invisible. This project makes the processor transparent: every step shows data flowing between registers, the ALU, and memory in real time, in a browser, with zero installation.

---

## Features

- **Visual step-by-step debugging** — Watch registers, flags, and memory change after each instruction, similar to [pythontutor.com](https://pythontutor.com/python-compiler.html) for Python.
- **100% web-based** — No IDE or local toolchain required for end users; just open a browser.
- **Real ARM Cortex-M0 execution** — Powered by QEMU + GDB under the hood, so the simulation is cycle-accurate at the instruction level.
- **ADL animation layer** — An Animation Description Language (ADL) translates raw execution traces into frontend animation events (arrows, highlights, bus annotations).
- **Multi-user platform** — User accounts, project management, OAuth and password authentication, announcements, and user-group-based access control.
- **Open Core** — Core simulation is free and open-source; institutional features (class management, analytics) can be built on top.

---

## Architecture

```
┌─────────────────────────────────────────┐
│              Web Frontend               │
│          (Vue.js, web/)                 │
└────────────────┬────────────────────────┘
                 │ REST API (ADL JSON)
┌────────────────▼────────────────────────┐
│           FastAPI Backend               │
│   /api/trace  /api/project              │
│   /api/session  /api/user               │
│   /api/announcements                    │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │         app/kernel               │   │
│  │  ASMLineReader → QEMU → GDB      │   │
│  │  ALoader (step iterator)         │   │
│  │  ADL model builder               │   │
│  └──────────────────────────────────┘   │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │       SQLAlchemy Database        │   │
│  │  Users, Projects, UserGroups     │   │
│  │  OAuthProviders, Announcements   │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Key Components

| Path | Role |
|------|------|
| `app/kernel/` | Emulation core: assembly parsing, QEMU/GDB lifecycle, step iterator, ADL models |
| `app/apis/` | FastAPI routers: trace, project, session, user, announcements |
| `app/database/` | SQLAlchemy ORM models and DB utilities |
| `app/core/` | Settings, security, logging (network-independent) |
| `app/services/` | Business logic that depends on the network layer |
| `web/` | Vue.js frontend |
| `example/` | Deployment examples (Authelia auth, Traefik reverse proxy) |

---

## Prerequisites

### System dependencies

| Tool | Package (Debian/Ubuntu) | Notes |
|------|------------------------|-------|
| QEMU | `qemu-system-arm` | Must support `-M microbit` (Cortex-M0) |
| ARM GDB | `gdb-multiarch` (Debian) / `arm-none-eabi-gdb` (Arch/Manjaro) | MI interface required |
| ARM GCC | `gcc-arm-none-eabi`, `binutils-arm-none-eabi` | Assembles `.s` files |
| CMake | `cmake` | Builds the ELF binary |
| Python | `python3` (3.11+) | Backend runtime |

Install on Debian/Ubuntu:

```bash
sudo apt-get install qemu-system-arm gdb-multiarch gcc-arm-none-eabi \
    binutils-arm-none-eabi cmake python3 python3-pip
```

### Python dependencies

```bash
pip install -r app/requirements.txt
```

Core packages: `fastapi[all]`, `SQLAlchemy`, `pygdbmi`, `invoke`, `pydantic`, `authlib`, `passlib[argon2,bcrypt]`, `python-jose[cryptography]`.

---

## Configuration

### Application (`config.toml`)

Create `config.toml` in the working directory before starting the server:

```toml
database_url = "sqlite:///./app.db"
secret_key   = "your-secret-key-here"
login_action = "oauth_pw"   # password | oauth | oauth_pw | username_domain | direct_oauth
```

The file is optional; `database_url` can also be set via the environment variable `database_url`.

### Kernel (`connector.Config`)

The kernel is configured through `app.kernel.Config`. Minimum required fields:

```python
from app.kernel import Config

config = Config(
    uuid="my-session",        # project / session identifier (any string)
    PROJECT_DIR="/tmp/proj",  # where build artefacts are written
)
```

Important fields:

| Field | Default | Description |
|-------|---------|-------------|
| `uuid` | — | **Required.** Session/project identifier |
| `PROJECT_DIR` | — | **Required.** Directory for build artefacts |
| `GDB_BIN` | `arm-none-eabi-gdb` | Change to `gdb-multiarch` on Debian |
| `QEMU_BIN` | `qemu-system-arm` | QEMU executable |
| `SOCKETS_PATH` | Unix socket path | Set to `":1234"` on Windows (uses TCP port) |
| `QEMU_GDB_ARGS` | `""` | Extra QEMU GDB server args |
| `MEMORY_WATCH_START` | `0x20000000` | RAM start for memory-delta tracking |
| `MEMORY_WATCH_SIZE` | `512` | Bytes to watch; `0` disables memory tracking |

**Windows note:** Unix sockets are not available on Windows. Set:

```python
config = Config(
    uuid="demo",
    PROJECT_DIR="C:/tmp/proj",
    SOCKETS_PATH=":1234",
    QEMU_GDB_ARGS="",        # QEMU will listen on port 1234
)
```

---

## Running the Server

```bash
cd /path/to/ARM-Cortex-M0-Tutor
python -m app
```

The API will be available at `http://localhost:8000`. Interactive docs: `http://localhost:8000/docs`.

---

## Docker

A `Dockerfile` is provided based on Debian with all system dependencies pre-installed.

```bash
# Build
docker build \
  --build-arg AUTHORIZED_KEYS_PATH=~/.ssh/authorized_keys \
  -t arm-m0-tutor .

# Run (development mode with SSH)
docker run -p 8888:8888 -p 22:22 \
  -e develop=true \
  arm-m0-tutor

# Run (production)
docker run -p 8888:8888 arm-m0-tutor
```

See `example/reverse-proxy/` for a Traefik reverse-proxy setup and `example/auth-system/` for an Authelia authentication layer.

---

## API Overview

All routes are prefixed with `/api`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/trace` | Static example ADL trace (for demos) |
| `GET` | `/api/trace/{project_uuid}` | Execute and return ADL trace for a project |
| `GET` | `/api/project/trace?uuid=…` | Same as above, query-param variant |
| `GET/POST` | `/api/project` | List / create projects |
| `GET/PUT/DELETE` | `/api/project/{uuid}` | Read / update / delete a project |
| `POST` | `/api/session/login` | Login (password or OAuth) |
| `DELETE` | `/api/session/logout` | Logout |
| `GET` | `/api/user/me` | Current user info |
| `GET` | `/api/announcements` | List visible announcements |

The trace endpoint returns an **ADL v1** `TraceResponse` JSON object consumed by the frontend animator.

---

## Kernel Usage (Python API)

```python
from app.kernel import Config, setup, build, start_qemu, stop_qemu, debug, ASMLineReader
from invoke import Context

config = Config(uuid="demo", PROJECT_DIR="/tmp/demo", GDB_BIN="gdb-multiarch")
reader = ASMLineReader()

# Parse assembly lines
asm_list = [reader.load(line) for line in [
    "movs r0, #1",
    "movs r1, #2",
    "adds r2, r0, r1",
]]

c = Context()
setup(c, config, asm_list)   # create project directory and write asm.s
build(c, config)              # compile with CMake + arm-none-eabi-gcc
start_qemu(c, config)         # launch QEMU, wait for GDB

loader = debug(c, config)     # connect GDB, return step iterator
for step in loader:
    print(step.addr_pc, dict(step.register_values))

loader.exit()
stop_qemu(c, config)
```

### `ASMStep` fields

| Field | Type | Description |
|-------|------|-------------|
| `line_counter` | `int` | Step sequence number |
| `addr_pc` | `str` | Program counter (hex string) |
| `disassemble` | tuple | `((address, ASMLine), …)` near current PC |
| `register_values` | tuple | `(name, value)` for r0–r15 and N/Z/C/V flags |
| `memory_delta` | `dict \| None` | `{hex_addr: byte_value}` for changed bytes this step |

---

## Project Structure

```
ARM-Cortex-M0-Tutor/
├── app/
│   ├── kernel/
│   │   ├── connector/       # Config, ALoader, ASMLine parser, GDB/QEMU tasks
│   │   ├── animation/       # ADL Pydantic models, step→ADL conversion
│   │   └── qemu_m0/         # CMake project, startup.c, linker script (microbit board)
│   ├── apis/
│   │   └── routes/          # trace, project, session, user, announcements
│   ├── database/            # SQLAlchemy models and DB helpers
│   ├── core/                # Settings, security, logging
│   └── services/            # Business-logic utilities
├── web/                     # Vue.js frontend
├── example/
│   ├── auth-system/         # Authelia docker-compose example
│   └── reverse-proxy/       # Traefik docker-compose example
├── test/                    # Unit tests
├── Dockerfile
└── config.toml              # (create this; not committed)
```

---

## License

See [LICENSE](LICENSE).
