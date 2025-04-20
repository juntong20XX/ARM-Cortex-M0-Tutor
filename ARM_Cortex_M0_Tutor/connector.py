#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化调试器：编译、运行和调试一体化工具
使用 invoke 实现事件驱动设计
"""
import os
import time
import signal
import subprocess
from pathlib import Path
from dataclasses import dataclass

from pygdbmi import gdbmiparser, gdbcontroller
from invoke import task, Collection, Context


@dataclass(frozen=True)
class Config:
    # uuid
    uuid: str
    # project config
    SOURCE_DIR: str = os.path.abspath(".")
    BUILD_DIR:str = os.path.join(SOURCE_DIR, "build")
    # QEMU 配置
    QEMU_BIN:str = "qemu-system-arm"  # 根据目标架构修改
    QEMU_ARGS:str = "-M microbit -nographic -s -S"  # -s 启用GDB服务器，-S 启动时暂停CPU
    # GDB 配置
    GDB_BIN:str = "arm-none-eabi-gdb"
    GDB_PORT:str = "tcp::1234"
    # 目标程序
    TARGET_NAME:str = "cortex-m0-microbit.elf"  # 编译生成的对象名称


# qemu process, {"uuid": process}
qemu_processes = {}


@task
def clean(c: Context, config: Config):
    """清理构建目录"""
    if os.path.exists(config.BUILD_DIR):
        c.run(f"rm -rf {config.BUILD_DIR}")
        print(f"the build dir cleaned: {config.BUILD_DIR}")


@task
def setup(c: Context, config: Config):
    """创建必要的目录结构"""
    if not os.path.exists(config.BUILD_DIR):
        os.makedirs(config.BUILD_DIR)
    cmake_build_path = os.path.join(config.BUILD_DIR, f"build-{config.uuid}")
    if not os.path.exists(cmake_build_path):
        os.makedirs(cmake_build_path)
    c.run(f"cp -r '{config.SOURCE_DIR}'/* '{config.BUILD_DIR}'")


@task(pre=[setup])
def build(c: Context, config: Config):
    """使用 CMake 编译项目"""
    cmake_build_path = os.path.join(config.BUILD_DIR, f"build-{config.uuid}")
    with c.cd(cmake_build_path):
        # 配置 CMake 项目
        c.run(f"cmake -DCMAKE_BUILD_TYPE=Debug -S ..")
        # 编译项目
        c.run(f"cmake --build . --target {config.TARGET_NAME}")
    print("编译完成")


@task
def start_qemu(c: Context, config: Config):
    """启动 QEMU 并运行目标程序"""
    target_path = os.path.join(config.BUILD_DIR, f"build-{config.uuid}", config.TARGET_NAME)
    # 检查目标程序是否存在
    if not os.path.exists(target_path):
        print(f"错误: 目标程序不存在 {target_path}")
        return False

    # 启动 QEMU
    cmd = f"{config.QEMU_BIN} {config.QEMU_ARGS} -kernel {target_path}"
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
def stop_qemu(c: Context, config: Config):
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
def debug(c: Context, config: Config):
    """使用 pygdbmi 连接 GDB 到 QEMU 进行调试"""
    cmd = [
        config.GDB_BIN, "--quiet", "--interpreter=mi3",
        os.path.join(config.BUILD_DIR, f"build-{config.uuid}", config.TARGET_NAME)
    ]
    try:
        # 创建 GDB 控制器
        gdbmi = gdbcontroller.GdbController(command=cmd)

        # 等待并处理 GDB 响应
        while True:
            responses = gdbmi.get_gdb_response(timeout_sec=1)
            # fixme: AI is WRONG, but I don't know what I would like to do. So just keep it.
            for response in responses:
                # 根据需要处理不同类型的响应
                if response['type'] == 'console':
                    print(response['payload'])
                elif response['type'] == 'error':
                    print(f"GDB错误: {response['payload']}")
                elif response['type'] == 'stopped':
                    print("程序已停止")
                    # 可以在这里添加更多交互逻辑

            # 添加用户交互或其他控制逻辑
            # 例如，等待用户输入或检查是否需要退出

    except KeyboardInterrupt:
        print("\nGDB 会话已终止")
    finally:
        # 停止 QEMU
        stop_qemu(c, config)


@task(default=True)
def auto_debug(c: Context, config: Config):
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
