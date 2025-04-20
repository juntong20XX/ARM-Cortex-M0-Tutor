import os
import uuid
import tempfile
import unittest
import subprocess
from pathlib import Path

from invoke import Context
from ARM_Cortex_M0_Tutor.connector import Config, clean, setup, start_qemu, stop_qemu, build, qemu_processes

project_path = Path(__file__).parent.parent
# 为每个测试用例创建一个临时配置
test_config = Config(PROJECT_DIR=str(project_path / "qemu_m0"), BUILD_DIR=tempfile.mkdtemp(),
                     uuid=str(uuid.uuid4()))
mock_context = Context()

class TestAutomationDebugger(unittest.TestCase):
    def tearDown(self):
        pass


    def test_01_setup(self):
        """测试创建目录结构功能"""
        setup(mock_context, test_config)

        # 验证目录已创建
        self.assertTrue(os.path.exists(test_config.BUILD_DIR))


    def test_02_build(self):
        """测试创建编译功能"""
        build(mock_context, test_config)
        # 验证编译对象已生成
        self.assertTrue(os.path.exists(os.path.join(test_config.BUILD_DIR, test_config.TARGET_NAME)))


    def test_03_start_qemu(self):
        """测试启动 QEMU 功能"""
        # 执行启动 QEMU
        result = start_qemu(mock_context, test_config)

        # 验证 QEMU 启动成功
        self.assertTrue(result)

    def test_04_stop_qemu(self):
        """测试停止 QEMU 功能"""

        if not len(qemu_processes) == 1:
            raise ValueError
        qemu_process: subprocess.Popen = tuple(qemu_processes.values())[0]

        # 执行停止 QEMU
        stop_qemu(mock_context, test_config)

        # 验证发送了终止信号
        self.assertIsInstance(qemu_process.poll(), int)


    def test_05_clean(self):
        """测试清理构建目录功能"""
        if not os.path.exists(test_config.BUILD_DIR):
            self.skipTest("BUILD_DIR not exists, cannot be clean")
        # 执行清理
        clean(mock_context, test_config)

        # 验证目录已被删除
        self.assertFalse(os.path.exists(test_config.BUILD_DIR))


if __name__ == '__main__':

    unittest.main()