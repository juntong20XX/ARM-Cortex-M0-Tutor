import os
import uuid
import tempfile
import unittest
import subprocess
from pathlib import Path

from invoke import Context
from ARM_Cortex_M0_Tutor.connector import Config, clean, setup, start_qemu, stop_qemu, build, qemu_processes, debug

# `setUP` cannot be used here, because it will be called before each test case.
project_base = Path(__file__).parent.parent
test_config = Config(SOURCE_DIR=str(project_base / "qemu_m0"), PROJECT_DIR=tempfile.mkdtemp(),
                     uuid=str(uuid.uuid4()))
mock_context = Context()


class TestAutomationDebugger(unittest.TestCase):
    def tearDown(self):
        # I should kill all subprocesses
        # but I don't know how to do it.
        pass

    def test_01_setup(self):
        setup(mock_context, test_config)

        self.assertTrue(os.path.exists(test_config.PROJECT_DIR))

    def test_02_build(self):
        build(mock_context, test_config)
        # check target
        self.assertTrue(
            os.path.exists(os.path.join(test_config.PROJECT_DIR, f"build-{test_config.uuid}", test_config.TARGET_NAME)))

    def test_03_start_qemu(self):
        result = start_qemu(mock_context, test_config)

        self.assertTrue(result)

    def test_04_debug(self):
        """
        I don't know how to check the result.
        """
        debug(mock_context, test_config)

    def test_05_stop_qemu(self):
        if not len(qemu_processes) == 1:
            raise ValueError
        qemu_process: subprocess.Popen = tuple(qemu_processes.values())[0]

        stop_qemu(mock_context, test_config)

        # check process is not running
        self.assertIsInstance(qemu_process.poll(), int)

    def test_06_clean(self):
        if not os.path.exists(test_config.PROJECT_DIR):
            self.skipTest("BUILD_DIR not exists, cannot be clean")
        clean(mock_context, test_config)

        self.assertFalse(os.path.exists(test_config.PROJECT_DIR))


if __name__ == '__main__':
    unittest.main()
