"""
ASMStep 转 ADL 测试：asm_step_to_trace_step、asm_steps_to_trace_response 及产出结构.
"""
import unittest

from app.kernel import (
    ASMLine,
    ASMParam,
    ASMStep,
    asm_step_to_trace_step,
    asm_steps_to_trace_response,
    adl_models,
)


def _make_register_values(r15="0x54", n=0, z=1, c=0, v=0):
    """构造 16 个寄存器 + N/Z/C/V，共 20 项."""
    regs = [(f"r{i}", "0x0") for i in range(16)]
    regs[15] = ("r15", r15)
    regs.extend([("N", str(n)), ("Z", str(z)), ("C", str(c)), ("V", str(v))])
    return tuple(regs)


def _make_asm_step(
    line_counter=0,
    addr_pc="0x00000056",
    disassemble=None,
    register_values=None,
    memory_delta=None,
):
    if register_values is None:
        register_values = _make_register_values()
    if disassemble is None:
        asm = ASMLine(
            "add", "s",
            ASMParam("r0", "r"),
            ASMParam("r1", "r"),
            ASMParam("#5", "i"),
        )
        disassemble = (("0x00000054", asm),)
    return ASMStep(
        line_counter=line_counter,
        addr_pc=addr_pc,
        disassemble=disassemble,
        register_values=register_values,
        memory_delta=memory_delta,
    )


class TestAsmStepToTraceStep(unittest.TestCase):
    """单步转换 asm_step_to_trace_step."""

    def test_snapshot_pc_and_line_counter(self):
        step = _make_asm_step(line_counter=1, addr_pc="0x00000058")
        t = asm_step_to_trace_step(step)
        self.assertEqual(t.snapshot.pc, "0x00000058")
        self.assertEqual(t.snapshot.lineCounter, 1)

    def test_snapshot_registers_and_flags(self):
        step = _make_asm_step(register_values=_make_register_values(r15="0x56", z=0))
        t = asm_step_to_trace_step(step)
        self.assertEqual(t.snapshot.registers["r15"], "0x56")
        self.assertEqual(t.snapshot.flags.Z, 0)
        self.assertEqual(t.snapshot.flags.N, 0)

    def test_snapshot_memory_delta(self):
        step = _make_asm_step(memory_delta={"0x20000000": 0x12})
        t = asm_step_to_trace_step(step)
        self.assertEqual(t.snapshot.memoryDelta, {"0x20000000": 0x12})

    def test_snapshot_memory_delta_none(self):
        step = _make_asm_step()
        t = asm_step_to_trace_step(step)
        self.assertIsNone(t.snapshot.memoryDelta)

    def test_events_contain_set_active_line_and_wait(self):
        step = _make_asm_step(line_counter=2)
        t = asm_step_to_trace_step(step)
        types = [e.type for e in t.events]
        self.assertIn("SetActiveLine", types)
        self.assertIn("Wait", types)
        self.assertIn("FocusCanvas", types)

    def test_rejects_non_asm_step(self):
        with self.assertRaises(TypeError):
            asm_step_to_trace_step(None)
        with self.assertRaises(TypeError):
            asm_step_to_trace_step({"addr_pc": "0x0"})


class TestAsmStepsToTraceResponse(unittest.TestCase):
    """多步转换 asm_steps_to_trace_response."""

    def test_empty_steps(self):
        resp = asm_steps_to_trace_response([])
        self.assertEqual(resp.adlVersion, 1)
        self.assertEqual(resp.steps, [])
        self.assertIsNone(resp.code)
        self.assertIsNone(resp.initialState)

    def test_single_step_response_structure(self):
        step = _make_asm_step()
        resp = asm_steps_to_trace_response([step])
        self.assertEqual(resp.adlVersion, 1)
        self.assertEqual(len(resp.steps), 1)
        self.assertIsInstance(resp.steps[0], adl_models.TraceStep)
        self.assertIsNotNone(resp.code)
        self.assertIsNotNone(resp.initialState)

    def test_code_from_first_step_disassemble(self):
        step = _make_asm_step()
        resp = asm_steps_to_trace_response([step])
        self.assertGreater(len(resp.code), 0)
        self.assertIn("text", resp.code[0].model_dump())
        self.assertIn("addr", resp.code[0].model_dump())
        self.assertEqual(resp.code[0].addr, "0x00000054")

    def test_initial_state_r15_is_first_instruction_addr(self):
        step = _make_asm_step(addr_pc="0x00000056")
        resp = asm_steps_to_trace_response([step])
        self.assertEqual(resp.initialState.registers["r15"], "0x00000054")
        self.assertIsNotNone(resp.initialState.flags)

    def test_multiple_steps(self):
        step0 = _make_asm_step(line_counter=0, addr_pc="0x00000056")
        step1 = _make_asm_step(
            line_counter=1,
            addr_pc="0x00000058",
            register_values=_make_register_values(r15="0x58"),
        )
        resp = asm_steps_to_trace_response([step0, step1])
        self.assertEqual(len(resp.steps), 2)
        self.assertEqual(resp.steps[0].snapshot.pc, "0x00000056")
        self.assertEqual(resp.steps[1].snapshot.pc, "0x00000058")

    def test_rejects_non_asm_step_list(self):
        with self.assertRaises(TypeError):
            asm_steps_to_trace_response([None])
        with self.assertRaises(TypeError):
            asm_steps_to_trace_response([_make_asm_step(), None])


class TestTraceResponseSerialization(unittest.TestCase):
    """TraceResponse 可序列化且符合 ADL 结构（与 _example_trace_response 一致）."""

    def test_response_json_roundtrip(self):
        step = _make_asm_step()
        resp = asm_steps_to_trace_response([step])
        data = resp.model_dump()
        self.assertEqual(data["adlVersion"], 1)
        self.assertIsInstance(data["steps"], list)
        parsed = adl_models.TraceResponse.model_validate(data)
        self.assertEqual(parsed.adlVersion, resp.adlVersion)
        self.assertEqual(len(parsed.steps), len(resp.steps))

    def test_snapshot_has_pc_registers_flags(self):
        step = _make_asm_step()
        t = asm_step_to_trace_step(step)
        snap = t.snapshot.model_dump()
        self.assertIn("pc", snap)
        self.assertIn("lineCounter", snap)
        self.assertIn("registers", snap)
        self.assertIn("flags", snap)
        self.assertIn("N", snap["flags"])
        self.assertIn("Z", snap["flags"])


if __name__ == "__main__":
    unittest.main()
