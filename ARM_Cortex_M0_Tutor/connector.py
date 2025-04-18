#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自动化调试器：编译、运行和调试一体化工具
使用 invoke 实现事件驱动设计
"""

import os
import time
import atexit
import signal
import tempfile
import subprocess
from dataclasses import dataclass

from invoke import task, Collection

# config
@dataclass()
class Config:
    PROJECT_DIR = os.path.abspath(".")
    BUILD_DIR = os.path.join(PROJECT_DIR, "build")

    # QEMU 配置
    QEMU_BIN = "qemu-system-arm"  # 根据目标架构修改
    QEMU_ARGS = "-m 1024 -nographic -s -S"  # -s 启用GDB服务器，-S 启动时暂停CPU

    # GDB 配置
    GDB_BIN = "arm-none-eabi-gdb"
    GDB_PORT = "tcp::1234"

    # 目标程序
    TARGET_NAME = "my_program"  # 替换为实际的目标程序名

    # 临时文件
    GDB_SCRIPT = None

    # uuid
    uuid: str

# qemu process, {"uuid": process}
qemu_processes = {}

@task
def clean(c, config: Config):
    """清理构建目录"""
    if os.path.exists(config.BUILD_DIR):
        c.run(f"rm -rf {config.BUILD_DIR}")
        print(f"the build dir cleaned: {config.BUILD_DIR}")

@task
def setup(c, config: Config):
    """创建必要的目录结构"""
    if not os.path.exists(config.BUILD_DIR):
        os.makedirs(config.BUILD_DIR)
        print(f"已创建构建目录: {config.BUILD_DIR}")

@task(pre=[setup])
def build(c, config: Config):
    """使用 CMake 编译项目"""
    with c.cd(config.BUILD_DIR):
        # 配置 CMake 项目
        c.run(f"cmake ..")

        # 编译项目
        c.run("cmake --build .")

    print("编译完成")

@task
def prepare_gdb_script(c, config: Config):
    """准备 GDB 脚本文件"""
    # 创建临时文件用于 GDB 脚本
    fd, path = tempfile.mkstemp(suffix='.gdb')
    config.GDB_SCRIPT = path

    # 写入 GDB 命令
    with os.fdopen(fd, 'w') as f:
        f.write(f"target remote {config.GDB_PORT}\n")
        f.write("set pagination off\n")
        f.write("set confirm off\n")
        f.write("break main\n")
        f.write("continue\n")

    # 注册退出时删除临时文件
    atexit.register(lambda: os.unlink(path) if os.path.exists(path) else None)

    print(f"GDB 脚本已准备: {path}")
    return path

@task(pre=[build])
def start_qemu(c, config: Config):
    """启动 QEMU 并运行目标程序"""

    target_path = os.path.join(Config.BUILD_DIR, Config.TARGET_NAME)

    # 检查目标程序是否存在
    if not os.path.exists(target_path):
        print(f"错误: 目标程序不存在 {target_path}")
        return

    # 启动 QEMU
    cmd = f"{Config.QEMU_BIN} {Config.QEMU_ARGS} -kernel {target_path}"
    print(f"启动 QEMU: {cmd}")

    # 使用 Popen 而不是 c.run，这样可以不阻塞
    qemu_process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid  # 使用新进程组，便于后续终止
    )

    #  记录 qemu_process
    qemu_processes[config.uuid] = qemu_process

    # 等待 QEMU 启动
    time.sleep(2)

    if qemu_process.poll() is not None:
        # QEMU 已终止
        stdout, stderr = qemu_process.communicate()
        print("QEMU 启动失败:")
        print(f"标准输出: {stdout.decode('utf-8', errors='ignore')}")
        print(f"标准错误: {stderr.decode('utf-8', errors='ignore')}")
        return False

    print("QEMU 已启动，等待 GDB 连接...")
    return True

@task
def stop_qemu(c, config: Config):
    """停止 QEMU 进程"""
    qemu_process = qemu_processes.get(config.uuid)
    if qemu_process and qemu_process.poll() is None:
        print("正在停止 QEMU...")
        # 发送 SIGTERM 信号给整个进程组
        os.killpg(os.getpgid(qemu_process.pid), signal.SIGTERM)

        # 等待进程终止
        try:
            qemu_process.wait(timeout=5)
            print("QEMU 已停止")
        except subprocess.TimeoutExpired:
            print("QEMU 未响应，强制终止...")
            os.killpg(os.getpgid(qemu_process.pid), signal.SIGKILL)
            print("QEMU 已强制终止")
    else:
        print("没有运行中的 QEMU 进程")

@task(pre=[start_qemu])
def debug(c, config: Config):
    """连接 GDB 到 QEMU 进行调试"""
    # 准备 GDB 脚本
    gdb_script = prepare_gdb_script(config)

    try:
        # 启动 GDB 并连接到 QEMU
        print("启动 GDB 并连接到 QEMU...")
        c.run(f"{config.GDB_BIN} -x {gdb_script}", pty=True)
    except KeyboardInterrupt:
        print("\nGDB 会话已终止")
    finally:
        # 停止 QEMU
        stop_qemu(c)

@task(default=True)
def auto_debug(c, config: Config):
    """一键自动化调试流程"""
    print("=== 开始自动化调试流程 ===")

    # 清理旧的构建
    clean(c, config)

    # 编译项目
    build(c, config)

    # 启动 QEMU 并运行目标
    if start_qemu(c, config):
        # 连接 GDB 进行调试
        debug(c, config)

    print("=== 自动化调试流程结束 ===")

# 创建任务集合
ns = Collection()
ns.add_task(clean)
ns.add_task(setup)
ns.add_task(build)
ns.add_task(start_qemu)
ns.add_task(stop_qemu)
ns.add_task(debug)
ns.add_task(auto_debug)
