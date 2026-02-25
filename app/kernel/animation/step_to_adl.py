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


def _normalize_reg(name: str) -> str:
    """将 r0/r1/... 规范为 ADL 使用的 R0/R1/..."""
    s = name.strip().lower()
    if s.startswith("r") and s[1:].isdigit():
        return "R" + s[1:]
    return name.strip()


def _get_current_asm_line(step: "ASMStep") -> "ASMLine | None":
    """根据 step.addr_pc 从 step.disassemble 中取出当前指令的 ASMLine。"""
    from ..connector.asm_basic import ASMLine

    try:
        pc = int(step.addr_pc, 16)
    except (ValueError, TypeError):
        return None
    for addr_str, asm_line in step.disassemble:
        if not isinstance(asm_line, ASMLine):
            continue
        try:
            if int(addr_str, 16) == pc:
                return asm_line
        except (ValueError, TypeError):
            continue
    return None


def _registers_and_flags(
    register_values: tuple[tuple[str, str], ...],
) -> tuple[dict[str, str], adl_models.FlagsSnapshot]:
    """Split register_values into registers dict (r0–r15) and FlagsSnapshot (N,Z,C,V)."""
    regs = dict(register_values[:16])
    # Last 4 entries are N, Z, C, V as '0' or '1'
    n, z, c, v = (int(register_values[i][1]) for i in range(16, 20))
    flags = adl_models.FlagsSnapshot(N=n, Z=z, C=c, V=v)
    return regs, flags


def _reg_value(register_values: tuple[tuple[str, str], ...], reg_name: str) -> str | None:
    """从 register_values 中取某寄存器的值，reg_name 为小写 r0..r15。"""
    reg_name = reg_name.strip().lower()
    for name, value in register_values[:16]:
        if name == reg_name:
            return value
    return None


def _events_for_mov(
    step: "ASMStep",
    asm_line: "ASMLine",
) -> list[adl_models.ADLEvent]:
    """
    为 MOV/MOVS 指令生成“数据来源”箭头事件：
    - 源为寄存器：箭头从源寄存器行指向目的寄存器行；
    - 源为立即数：箭头从当前代码行指向目的寄存器行。
    """
    # MOV 格式: mov(s) dest, source  -> param=dest, param_1=source
    dest_param = asm_line.param
    src_param = asm_line.param_1
    if not dest_param or not dest_param.type_name:
        return []
    dest_reg = _normalize_reg(dest_param.text)
    if not src_param or not src_param.type_name:
        return []

    events: list[adl_models.ADLEvent] = [
        adl_models.ADLEventFocusCanvas(target="REG"),
        adl_models.ADLEventMarkRegister(reg=dest_reg, mode="write"),
    ]

    if src_param.type_name == "r":
        # 源是寄存器：箭头 源寄存器 -> 目的寄存器
        src_reg = _normalize_reg(src_param.text)
        src_value = _reg_value(step.register_values, src_param.text.strip().lower())
        text = f"{src_reg} → {dest_reg}"
        if src_value is not None:
            text = f"{src_reg} ({src_value}) → {dest_reg}"
        events.append(adl_models.ADLEventMarkRegister(reg=src_reg, mode="read"))
        events.append(
            adl_models.ADLEventOverlayArrow(
                from_=adl_models.AnchorRefRegisterRow(reg=src_reg),
                to=adl_models.AnchorRefRegisterRow(reg=dest_reg),
                text=text,
            )
        )
    elif src_param.type_name == "i":
        # 源是立即数：箭头 当前代码行 -> 目的寄存器
        imm = src_param.text.strip()
        text = f"{imm} → {dest_reg}"
        events.append(
            adl_models.ADLEventOverlayArrow(
                from_=adl_models.AnchorRefCodeLineAddr(lineIndex=step.line_counter),
                to=adl_models.AnchorRefRegisterRow(reg=dest_reg),
                text=text,
            )
        )
    return events


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

    asm_line = _get_current_asm_line(step)
    if asm_line is not None and asm_line.basic == "mov":
        mov_events = _events_for_mov(step, asm_line)
        # 在 SetActiveLine 之后、Wait 之前插入 MOV 相关事件（替换默认的 FocusCanvas）
        events = [
            adl_models.ADLEventSetActiveLine(by="index", value=step.line_counter),
            *mov_events,
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
