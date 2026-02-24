"""
Tools to connect `server` and `data`.
"""
from app.kernel.connector.asm_basic import ASMLine
from .connector import ALoader

import os
import time
import signal
import subprocess
from typing import Iterable
from dataclasses import dataclass, asdict

from pygdbmi import gdbcontroller
from invoke import task, Collection, Context


@dataclass(frozen=True)
class Config:
    """
    args ends with `_ARGS` or `_PATH` will be auto update, `_PATH` args firstly, then `_ARGS`
    """
    # uuid
    uuid: str
    # project config
    SOURCE_DIR: str = os.path.abspath(os.path.join(__file__, "..", "..", "..", "qemu_m0"))
    PROJECT_DIR: str = os.path.join(SOURCE_DIR, "..", "project-build")
    BUILD_PATH: str = "{PROJECT_DIR}/build-{uuid}"
    # QEMU 配置
    QEMU_BIN: str = "qemu-system-arm"  # 根据目标架构修改
    QEMU_GDB_ARGS: str = '-chardev "socket,path={sockets_path},server=on,wait=off,id=gdb0" -gdb chardev:gdb0'
    QEMU_ADDITION_ARGS: str = "-M microbit -nographic -S -s"  # -s 启用GDB服务器, -S 启动时暂停CPU
    # GDB 配置
    GDB_BIN: str = "arm-none-eabi-gdb"
    # 目标程序
    TARGET_NAME: str = "cortex-m0-microbit.elf"  # 编译生成的对象名称
    SOCKETS_NAME: str = "gdb-socket.sock"
    SOCKETS_PATH: str = "{PROJECT_DIR}/build-{uuid}/{SOCKETS_NAME}"
    # 内存变化监视：步前/步后读该区域并 diff，得到 memory_delta。0 表示不监视
    MEMORY_WATCH_START: str = "0x20000000"  # Cortex-M0 microbit RAM 起始
    MEMORY_WATCH_SIZE: int = 512  # 字节数，0 则不做内存读取

    def get_format_map(self) -> dict:
        ret = asdict(self)
        for k, v in tuple(ret.items()):
            if k.endswith("_PATH") and hasattr(v, "format_map"):
                ret[k.lower()] = v.format_map(ret)
        for k, v in tuple(ret.items()):
            if k.endswith("_ARGS") and hasattr(v, "format_map"):
                ret[k.lower()] = v.format_map(ret)
        return ret


# qemu process, {"uuid": process}
qemu_processes = {}


@task
def clean(c: Context, config: Config):
    """clear the project dir"""
    if os.path.exists(config.PROJECT_DIR):
        c.run(f"rm -rf {config.PROJECT_DIR}")
        print(f"the build dir cleaned: {config.PROJECT_DIR}")


@task
def setup(c: Context, config: Config, asm_list: Iterable[ASMLine]):
    """
    setup project dir
    - make project dir
    - make build dir
    - copy source files to project dir
    - setup asm file
    """
    mapping = config.get_format_map()
    if not os.path.exists(mapping["PROJECT_DIR"]):
        os.makedirs(config.PROJECT_DIR)
    if not os.path.exists(mapping["build_path"]):
        os.makedirs(mapping["build_path"])
    c.run(f"cp -r '{config.SOURCE_DIR}'/* '{config.PROJECT_DIR}'")

    # setup asm file
    asm_file_path = os.path.join(mapping["PROJECT_DIR"], "asm.s")
    with open(asm_file_path, "r", encoding="utf-8") as asm_file:
        asm_file_text = asm_file.read()
    text_list = [line.to_code() for line in asm_list]
    asm_file_text = asm_file_text.format(CODE_HERE="\n".join(text_list))
    with open(asm_file_path, "w", encoding="utf-8") as asm_file:
        asm_file.write(asm_file_text)


@task(pre=[setup])
def build(c: Context, config: Config):
    """CMake build"""
    mapping = config.get_format_map()
    cmake_build_path = mapping["build_path"]
    with c.cd(cmake_build_path):
        # setup CMake
        c.run(f"cmake -DCMAKE_BUILD_TYPE=Debug -S {mapping['PROJECT_DIR']} -B .")
        # build
        c.run(f"cmake --build . --target {config.TARGET_NAME}")


@task
def start_qemu(c: Context, config: Config):
    """start QEMU """
    mapping = config.get_format_map()
    target_path = os.path.join(mapping["build_path"], config.TARGET_NAME)
    # check target
    assert os.path.exists(target_path), "Target file not found"

    # start QEMU
    cmd = f"{config.QEMU_BIN} {mapping['qemu_addition_args']} -kernel {target_path} {mapping['qemu_gdb_args']}"
    qemu_process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid  # Use a new process group, making it easier to terminate later
    )

    qemu_processes[config.uuid] = qemu_process

    # wait for QEMU to start
    time.sleep(1)

    if qemu_process.poll() is not None:
        stdout, stderr = qemu_process.communicate()
        print("QEMU start failed:")
        print(f"stdout: {stdout.decode('utf-8', errors='ignore')}")
        print(f"stderr: {stderr.decode('utf-8', errors='ignore')}")
        raise RuntimeError("QEMU failed to start")

    return True


@task
def stop_qemu(c: Context, config: Config):
    """stop QEMU process"""
    qemu_process = qemu_processes.get(config.uuid)
    if qemu_process and qemu_process.poll() is None:
        # 发送 SIGTERM 信号给整个进程组
        os.killpg(os.getpgid(qemu_process.pid), signal.SIGTERM)
        try:
            qemu_process.wait(timeout=5)
            print("QEMU stopped successfully")
        except subprocess.TimeoutExpired:
            print("QEMU not stopped...")
            os.killpg(os.getpgid(qemu_process.pid), signal.SIGKILL)
            print("QEMU killed")


@task(pre=[start_qemu])
def debug(c: Context, config: Config, asm_reader=None):
    """client GDB connect to QEMU"""
    mapping = config.get_format_map()
    cmd = [
        config.GDB_BIN,
        os.path.join(mapping["build_path"], config.TARGET_NAME),
        "--quiet", "--interpreter=mi2",
    ]
    # setup GDB Controller
    gdbmi = gdbcontroller.GdbController(command=cmd)

    return ALoader(
        gdbmi,
        mapping["sockets_path"],
        asm_reader,
        memory_watch_start=config.MEMORY_WATCH_START,
        memory_watch_size=config.MEMORY_WATCH_SIZE,
    )


# Invoke tasks
ns = Collection()
ns.add_task(clean)
ns.add_task(setup)
ns.add_task(build)
ns.add_task(start_qemu)
ns.add_task(stop_qemu)
ns.add_task(debug)

# --- as a module

from app.kernel.connector.asm_basic import ASMParam, ASMLineReader
from .connector import ASMStep

__all__ = ["Config", "clean", "setup", "start_qemu", "stop_qemu", "build", "debug",
           "ASMLine", "ASMParam", "ASMStep", "ASMLineReader",
           "ALoader"]
