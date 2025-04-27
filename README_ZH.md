# ARM-Cortex-M0-Tutor





## Setup

### Config

The config object is at `connector.Config`.

配置的最小启动设置是填写 `uuid` 和 `PROJECT_DIR` 字段。

其中 `uuid` 是项目名称, 可以填写任何字符串。`PROJECT_DIR` 是项目和代码生成的位置，可以填写存在或不存在的目录, 如 `/tmp` 或 `/tmp/example`.

该项目开发于 Manjaro Linux, 因此使用的 gdb 为 `arm-none-eabi-gdb`, 对于 `debian` 系 Linux 系统, 还需要配置 `GDB_BIN` 为 `gdb-multiarch`.

若你的系统环境为 Windows 等 non-Unix-like 环境, 还需要修改 `QEMU_GDB_ARGS` 和 `SOCKETS_PATH`, 将其改为端口启动而不是 Unix Socket. 如 `SOCKETS_PATH=":1234"`, 以及 `QEMU_GDB_ARGS=""`, 当不指定 `QEMU_GDB_ARGS` 时,  qemu 会在 `1234` 端口启动 gdb-server , 而 `SOCKETS_PATH` 将传递给 gdb 远程连接该端口.

