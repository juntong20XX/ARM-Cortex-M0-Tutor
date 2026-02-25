"""
Convert ASMStep (from next(kernel.debug)) to ADL TraceStep / TraceResponse.
See ADL_SPEC and _example_trace_response in apis/routes/trace.py.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import adl_models

if TYPE_CHECKING:
    from ..connector.asm_basic import ASMLine
    from ..connector.connector import ASMStep


def _registers_and_flags(
    register_values: tuple[tuple[str, str], ...],
) -> tuple[dict[str, str], adl_models.FlagsSnapshot]:
    """Split register_values into registers dict (r0–r15) and FlagsSnapshot (N,Z,C,V)."""
    regs = dict(register_values[:16])
    # Last 4 entries are N, Z, C, V as '0' or '1'
    n, z, c, v = (int(register_values[i][1]) for i in range(16, 20))
    flags = adl_models.FlagsSnapshot(N=n, Z=z, C=c, V=v)
    return regs, flags


def asm_step_to_trace_step(step: "ASMStep") -> adl_models.TraceStep:
    """Convert a single ASMStep to ADL TraceStep (snapshot + minimal events)."""
    from ..connector.connector import ASMStep

    if not isinstance(step, ASMStep):
        raise TypeError("step must be an ASMStep")

    registers, flags = _registers_and_flags(step.register_values)
    snapshot = adl_models.StepSnapshot(
        pc=step.addr_pc,
        lineCounter=step.line_counter,
        registers=registers,
        flags=flags,
        memoryDelta=step.memory_delta,
    )
    events: list[adl_models.ADLEvent] = [
        adl_models.ADLEventSetActiveLine(by="index", value=step.line_counter),
        adl_models.ADLEventFocusCanvas(target="CU"),
        adl_models.ADLEventWait(ms=800),
    ]
    return adl_models.TraceStep(snapshot=snapshot, events=events)


def _disassemble_to_code(
    disassemble: tuple[tuple[str, "ASMLine"], ...],
) -> list[adl_models.CodeLine]:
    """Build list[CodeLine] from disassemble (addr, ASMLine) tuples."""
    from ..connector.asm_basic import ASMLine

    code: list[adl_models.CodeLine] = []
    for addr, asm_line in disassemble:
        if not isinstance(asm_line, ASMLine):
            continue
        text = asm_line.to_code(0)
        code.append(adl_models.CodeLine(text=text, addr=addr))
    return code


def asm_steps_to_trace_response(steps: list["ASMStep"]) -> adl_models.TraceResponse:
    """Convert a list of ASMStep (e.g. from iterating kernel.debug) to ADL TraceResponse."""
    from ..connector.connector import ASMStep

    if not steps:
        return adl_models.TraceResponse(
            adlVersion=1,
            code=None,
            initialState=None,
            steps=[],
        )

    first = steps[0]
    if not isinstance(first, ASMStep):
        raise TypeError("steps must be a list of ASMStep")

    code = _disassemble_to_code(first.disassemble)
    trace_steps = [asm_step_to_trace_step(s) for s in steps]

    # Initial state: use first step's registers/flags, with r15 set to first instruction addr
    registers, flags = _registers_and_flags(first.register_values)
    first_addr = code[0].addr if code else first.addr_pc
    initial_regs = {**registers, "r15": first_addr}
    initialState = adl_models.InitialState(
        registers=initial_regs,
        flags=flags,
        memoryDelta=first.memory_delta if first.memory_delta else None,
    )

    return adl_models.TraceResponse(
        adlVersion=1,
        code=code if code else None,
        initialState=initialState,
        steps=trace_steps,
    )
