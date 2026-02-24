import os
import uuid
import tempfile
import unittest
import subprocess
from pathlib import Path

from invoke import Context
from app.kernel import Config, clean, setup, start_qemu, stop_qemu, build, qemu_processes, debug, \
    ASMLine, ASMParam

# setUp cannot be used here, because it would be called before each test case.
project_base = Path(__file__).parent.parent
test_config = Config(
    SOURCE_DIR=str(project_base / "app" / "kernel" / "qemu_m0"),
    PROJECT_DIR=tempfile.mkdtemp(),
    GDB_BIN="gdb-multiarch",
    uuid=str(uuid.uuid4()),
    MEMORY_WATCH_START="0x20000000",
    MEMORY_WATCH_SIZE=512,
)
mock_context = Context()

# Assembly: load address 0x20000000 into r0, store byte 0x11 at [r0] so memory_delta is observable.
asm_code_list = [
    ASMLine("ldr", "", ASMParam("r0", "r"), ASMParam("=0x20000000", "c")),
    ASMLine("mov", "s", ASMParam("r1", "r"), ASMParam("#0x11", "i")),
    ASMLine("strb", "", ASMParam("r1", "r"), ASMParam("[r0]", "m")),
]


class TestAutomationDebugger(unittest.TestCase):
    def tearDown(self):
        # I should kill all subprocesses, but I don't know how to do it.
        pass

    def test_01_setup(self):
        setup(mock_context, test_config, asm_code_list)

        self.assertTrue(os.path.exists(test_config.PROJECT_DIR))

    def test_02_build(self):
        build(mock_context, test_config)
        self.assertTrue(
            os.path.exists(os.path.join(test_config.PROJECT_DIR, f"build-{test_config.uuid}", test_config.TARGET_NAME)),
            "ELF target should exist after build",
        )

    def test_03_start_qemu(self):
        result = start_qemu(mock_context, test_config)

        self.assertTrue(result)

    def test_04_debug(self):
        asm_steps = debug(mock_context, test_config)
        steps_ls = list(asm_steps)
        self.assertGreaterEqual(len(steps_ls), 1, "At least one step should be executed")

        for step in steps_ls:
            self.assertTrue(
                step.memory_delta is None or isinstance(step.memory_delta, dict),
                "memory_delta must be None or dict",
            )
            if step.memory_delta:
                for addr, val in step.memory_delta.items():
                    self.assertIsInstance(addr, str, f"Address must be str: {addr!r}")
                    self.assertIsInstance(val, int, f"Byte value must be int: {val!r}")
                    self.assertGreaterEqual(val, 0, f"Byte value 0-255: {val}")
                    self.assertLessEqual(val, 255, f"Byte value 0-255: {val}")
                    self.assertTrue(addr.startswith("0x"), f"Address must be hex string: {addr!r}")

        # At least one step must show the store we did: strb r1, [r0] with r0=0x20000000, value 0x11
        store_addr = "0x20000000"
        store_value = 0x11
        steps_with_store = [s for s in steps_ls if s.memory_delta and store_addr in s.memory_delta]
        self.assertGreater(
            len(steps_with_store),
            0,
            f"Expected at least one step with memory_delta containing {store_addr} (strb r1, [r0] store)",
        )
        self.assertEqual(
            steps_with_store[0].memory_delta[store_addr],
            store_value,
            f"Address {store_addr} should contain byte 0x{store_value:02x} after strb r1, [r0]",
        )

    def test_05_stop_qemu(self):
        if len(qemu_processes) != 1:
            raise ValueError("Expected exactly one QEMU process")
        qemu_process: subprocess.Popen = tuple(qemu_processes.values())[0]

        stop_qemu(mock_context, test_config)
        self.assertIsInstance(qemu_process.poll(), int, "QEMU process should be stopped")

    def test_06_clean(self):
        if not os.path.exists(test_config.PROJECT_DIR):
            self.skipTest("PROJECT_DIR does not exist, cannot clean")
        clean(mock_context, test_config)
        self.assertFalse(os.path.exists(test_config.PROJECT_DIR))


if __name__ == '__main__':
    unittest.main()
