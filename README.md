# ARM-Cortex-M0-Tutor





## Setup

### Config

The config object is at `connector.Config`.

The configured minimum start up setting is to fill in the `uuid` and `PROJECT_DIR` fields.

The `uuid` is the project name, which can be any string. `PROJECT_DIR` is the location where the project and code will be generated, and can be filled with an existing or non-existing directory, such as `/tmp` or `/tmp/example`.

The project is developed on Manjaro Linux, so the gdb used is `arm-none-eabi-gdb`, and for `debian` Linux systems, `GDB_BIN` needs to be configured to `gdb-multiarch`.

If you are in a non-Unix-like environment such as Windows, you will also need to modify `QEMU_GDB_ARGS` and `SOCKETS_PATH` to boot on a port instead of a Unix socket. If `SOCKETS_PATH=':1234'`, and `QEMU_GDB_ARGS =""`, when `QEMU_GDB_ARGS` is not specified, qemu will start gdb-server on port `1234` , and `SOCKETS_PATH` will be passed to gdb to connect to that port remotely.
