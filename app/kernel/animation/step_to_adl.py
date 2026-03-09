"""
Convert ASMStep (from next(kernel.debug)) to ADL TraceStep / TraceResponse.
See ADL_SPEC and _example_trace_response in apis/routes/trace.py.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import adl_models

if TYPE_CHECKING:
    from ..connector.asm_basic import ASMLine, ASMParam
    from ..connector.connector import ASMStep


def _normalize_reg(name: str) -> str:
    """将 r0/r1/... 规范为 ADL 使用的 R0/R1/..."""
    s = name.strip().lower()
    if s.startswith("r") and s[1:].isdigit():
        return "R" + s[1:]
    return name.strip()


def _fragment_spans(line_text: str, fragment_texts: list[str]) -> list[dict]:
    """
    在 line_text 中查找各 fragment 的字符跨度。
    按顺序查找首次出现位置，返回 [{ text, start, end }, ...]。
    """
    result: list[dict] = []
    search_from = 0
    for frag in fragment_texts:
        idx = line_text.find(frag, search_from)
        if idx < 0:
            continue
        result.append({"text": frag, "start": idx, "end": idx + len(frag)})
        search_from = idx + len(frag)
    return result


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
    - 源为立即数：箭头从 #3 片段指向 R1 寄存器行；操作数边放大边移动至中央后显示 #3→r1 箭头。
    - 新增：高亮操作数、边放大边移动到代码框中央，再在中央显示 #3 → r1 箭头。
    """
    # MOV 格式: mov(s) dest, source  -> param=dest, param_1=source
    dest_param = asm_line.param
    src_param = asm_line.param_1
    if not dest_param or not dest_param.type_name:
        return []
    dest_reg = _normalize_reg(dest_param.text)
    if not src_param or not src_param.type_name:
        return []

    dest_text = dest_param.text.strip()
    src_text = src_param.text.strip()
    line_text = asm_line.to_code(0)
    fragment_texts = [dest_text, src_text]
    spans = _fragment_spans(line_text, fragment_texts)
    fragment_spans_with_ids: list[adl_models.FragmentSpan] = []
    for i, s in enumerate(spans):
        span_id = "dest" if i == 0 else "src"
        fragment_spans_with_ids.append(
            adl_models.FragmentSpan(
                text=s["text"],
                start=s["start"],
                end=s["end"],
                id=span_id,
            )
        )

    events: list[adl_models.ADLEvent] = [
        adl_models.ADLEventFocusCanvas(target="REG"),
        adl_models.ADLEventMarkRegister(reg=dest_reg, mode="write"),
    ]

    if src_param.type_name == "r":
        # 源是寄存器：同时高亮寄存器、MCU 模块、r1/r2、箭头
        src_reg = _normalize_reg(src_param.text)
        src_value = _reg_value(step.register_values, src_param.text.strip().lower())
        text = f"{src_reg} → {dest_reg}"
        if src_value is not None:
            text = f"{src_reg} ({src_value}) → {dest_reg}"
        events.append(adl_models.ADLEventMarkRegister(reg=src_reg, mode="read"))
        if fragment_spans_with_ids:
            events.append(
                adl_models.ADLEventHighlightCodeFragment(
                    lineIndex=step.line_counter,
                    fragments=fragment_spans_with_ids,
                )
            )
        events.append(
            adl_models.ADLEventOverlayArrow(
                from_=adl_models.AnchorRefRegisterRow(reg=src_reg),
                to=adl_models.AnchorRefRegisterRow(reg=dest_reg),
                text=text,
            )
        )
        # 边放大边移动到代码框中央，然后显示 src → dest 箭头
        if fragment_spans_with_ids:
            events.extend([
                adl_models.ADLEventWait(ms=300),
                adl_models.ADLEventAnimateFragmentMove(
                    lineIndex=step.line_counter,
                    fragments=fragment_spans_with_ids,
                    duration=600,
                    target="codeBoxCenter",
                ),
                adl_models.ADLEventOverlayArrow(
                    from_=adl_models.AnchorRefFloatingToken(tokenId="src"),
                    to=adl_models.AnchorRefFloatingToken(tokenId="dest"),
                    text=text,
                ),
            ])
    elif src_param.type_name == "i":
        # 源是立即数：先高亮 r1/#3，再用 CodeFragment 锚点画 #3 → R1 箭头
        imm = src_param.text.strip()
        text = f"{imm} → {dest_reg}"
        # 同时高亮：寄存器、MCU REG 模块、r1 和 #3，箭头从 #3 指向 R1
        if fragment_spans_with_ids:
            events.append(
                adl_models.ADLEventHighlightCodeFragment(
                    lineIndex=step.line_counter,
                    fragments=fragment_spans_with_ids,
                )
            )
            events.append(adl_models.ADLEventWait(ms=50))  # 等待 DOM 更新以便解析 CodeFragment 锚点
            events.append(
                adl_models.ADLEventOverlayArrow(
                    from_=adl_models.AnchorRefCodeFragment(
                        lineIndex=step.line_counter, fragment="src"
                    ),
                    to=adl_models.AnchorRefRegisterRow(reg=dest_reg),
                    text=text,
                )
            )
        else:
            events.append(
                adl_models.ADLEventOverlayArrow(
                    from_=adl_models.AnchorRefCodeLineAddr(lineIndex=step.line_counter),
                    to=adl_models.AnchorRefRegisterRow(reg=dest_reg),
                    text=text,
                )
            )
        # 边放大边移动到代码框中央，然后显示 #3 → r1 箭头
        if fragment_spans_with_ids:
            events.extend([
                adl_models.ADLEventWait(ms=300),
                adl_models.ADLEventAnimateFragmentMove(
                    lineIndex=step.line_counter,
                    fragments=fragment_spans_with_ids,
                    duration=600,
                    target="codeBoxCenter",
                ),
                adl_models.ADLEventOverlayArrow(
                    from_=adl_models.AnchorRefFloatingToken(tokenId="src"),
                    to=adl_models.AnchorRefFloatingToken(tokenId="dest"),
                    text=text,
                ),
            ])
    return events


def _parse_address_param(
    param: "ASMParam",
) -> tuple[str | None, str | None]:
    """
    解析地址形式参数 `[r1, #4]` / `[r1]`：
    返回 (base_reg, offset_str)，其中 base_reg 已通过 _normalize_reg 规范。
    """
    if not param or not param.type_name:
        return None, None

    text = param.text.strip()
    if not (text.startswith("[") and text.endswith("]")):
        return None, None

    inner = text[1:-1].strip()
    if not inner:
        return None, None

    base_part: str
    offset_part: str | None
    if "," in inner:
        base_part, offset_part = inner.split(",", 1)
        base_part = base_part.strip()
        offset_part = offset_part.strip()
    else:
        base_part = inner
        offset_part = None

    if not base_part:
        return None, None
    base_reg = _normalize_reg(base_part)
    return base_reg, offset_part


def _events_for_add_sub(
    step: "ASMStep",
    asm_line: "ASMLine",
    op_symbol: str,
) -> list[adl_models.ADLEvent]:
    """
    为 ADD/SUB 指令生成事件：
    - 标记源寄存器读、目标寄存器写；
    - 以 ALU 为中心，展示表达式与结果写回。
    """
    dest_param = asm_line.param
    src1_param = asm_line.param_1
    src2_param = asm_line.param_2
    if not dest_param or not dest_param.type_name:
        return []
    if not src1_param or not src1_param.type_name:
        return []
    dest_reg = _normalize_reg(dest_param.text)

    def _operand_display(p: "ASMParam") -> tuple[str, str | None]:
        """返回 (展示文本, 对应寄存器当前值或 None)。"""
        if not p or not p.type_name:
            return "?", None
        if p.type_name == "r":
            reg = _normalize_reg(p.text)
            value = _reg_value(step.register_values, p.text.strip().lower())
            if value is not None:
                return f"{reg} ({value})", value
            return reg, None
        # 立即数或其他，直接用原始文本
        return p.text.strip(), None

    src1_text, _ = _operand_display(src1_param)
    src2_text, _ = _operand_display(src2_param) if src2_param and src2_param.type_name else ("?", None)

    expr = f"{src1_text} {op_symbol} {src2_text}"
    result_value = _reg_value(step.register_values, dest_param.text.strip().lower())
    annotate_text = expr
    if result_value is not None:
        annotate_text = f"{expr} = {result_value}"

    events: list[adl_models.ADLEvent] = [
        adl_models.ADLEventFocusCanvas(target="ALU"),
    ]

    if src1_param.type_name == "r":
        events.append(
            adl_models.ADLEventMarkRegister(
                reg=_normalize_reg(src1_param.text),
                mode="read",
            )
        )
    if src2_param and src2_param.type_name == "r":
        events.append(
            adl_models.ADLEventMarkRegister(
                reg=_normalize_reg(src2_param.text),
                mode="read",
            )
        )

    events.append(
        adl_models.ADLEventMarkRegister(
            reg=dest_reg,
            mode="write",
        )
    )
    events.append(
        adl_models.ADLEventAnnotateBus(
            text=annotate_text,
            at="writeback",
        )
    )
    events.append(
        adl_models.ADLEventOverlayArrow(
            from_=adl_models.AnchorRefCanvasComponent(id="ALU"),
            to=adl_models.AnchorRefRegisterRow(reg=dest_reg),
            text=f"{expr} → {dest_reg}",
        )
    )
    return events


def _events_for_ldr(
    step: "ASMStep",
    asm_line: "ASMLine",
) -> list[adl_models.ADLEvent]:
    """
    为 LDR 指令生成事件：
    - 从内存/常量池加载到寄存器；
    - 地址形式：[Rn] / [Rn, #imm] / =imm。
    """
    dest_param = asm_line.param
    src_param = asm_line.param_1
    if not dest_param or not dest_param.type_name:
        return []
    if not src_param or not src_param.type_name:
        return []

    dest_reg = _normalize_reg(dest_param.text)
    events: list[adl_models.ADLEvent] = [
        adl_models.ADLEventFocusCanvas(target="REG"),
        adl_models.ADLEventMarkRegister(reg=dest_reg, mode="write"),
    ]

    # 地址形式：[Rn, #imm] / [Rn]
    if src_param.type_name in {"a", "m"}:
        base_reg, offset = _parse_address_param(src_param)
        if base_reg is None:
            return events
        events.append(
            adl_models.ADLEventMarkRegister(
                reg=base_reg,
                mode="read",
            )
        )
        addr_text = f"[{base_reg}"
        if offset:
            addr_text += f", {offset}"
        addr_text += "]"
        events.append(
            adl_models.ADLEventAnnotateBus(
                text=f"Load {addr_text}",
                at="writeback",
            )
        )
        events.append(
            adl_models.ADLEventOverlayArrow(
                from_=adl_models.AnchorRefRegisterRow(reg=base_reg),
                to=adl_models.AnchorRefRegisterRow(reg=dest_reg),
                text=f"{addr_text} → {dest_reg}",
            )
        )
        return events

    # 常量池形式：=imm 或立即数，视为“字面量 → 寄存器”
    if src_param.type_name in {"c", "i"}:
        imm = src_param.text.strip()
        events.append(
            adl_models.ADLEventOverlayArrow(
                from_=adl_models.AnchorRefCodeLineAddr(lineIndex=step.line_counter),
                to=adl_models.AnchorRefRegisterRow(reg=dest_reg),
                text=f"{imm} → {dest_reg}",
            )
        )
        return events

    return events


def _events_for_str(
    step: "ASMStep",
    asm_line: "ASMLine",
) -> list[adl_models.ADLEvent]:
    """
    为 STR/STRB 指令生成事件：
    - 将寄存器值写入内存地址（[Rn] / [Rn, #imm]）。
    """
    value_param = asm_line.param
    addr_param = asm_line.param_1
    if not value_param or not value_param.type_name:
        return []
    if not addr_param or not addr_param.type_name:
        return []

    value_reg = _normalize_reg(value_param.text) if value_param.type_name == "r" else value_param.text.strip()
    events: list[adl_models.ADLEvent] = [
        adl_models.ADLEventFocusCanvas(target="REG"),
    ]

    if value_param.type_name == "r":
        events.append(
            adl_models.ADLEventMarkRegister(
                reg=value_reg,
                mode="read",
            )
        )

    if addr_param.type_name in {"a", "m"}:
        base_reg, offset = _parse_address_param(addr_param)
        addr_text = ""
        if base_reg is not None:
            events.append(
                adl_models.ADLEventMarkRegister(
                    reg=base_reg,
                    mode="read",
                )
            )
            addr_text = f"[{base_reg}"
            if offset:
                addr_text += f", {offset}"
            addr_text += "]"
        else:
            addr_text = addr_param.text.strip()

        events.append(
            adl_models.ADLEventAnnotateBus(
                text=f"Store {value_reg} → {addr_text}",
                at="writeback",
            )
        )
        events.append(
            adl_models.ADLEventOverlayArrow(
                from_=adl_models.AnchorRefRegisterRow(reg=value_reg)
                if value_param.type_name == "r"
                else adl_models.AnchorRefCodeLineAddr(lineIndex=step.line_counter),
                to=adl_models.AnchorRefCodeLineAddr(lineIndex=step.line_counter),
                text=f"{value_reg} → {addr_text}",
            )
        )
        return events

    # 其他地址形式，降级为简单箭头
    addr_text = addr_param.text.strip()
    events.append(
        adl_models.ADLEventOverlayArrow(
            from_=adl_models.AnchorRefRegisterRow(reg=value_reg)
            if value_param.type_name == "r"
            else adl_models.AnchorRefCodeLineAddr(lineIndex=step.line_counter),
            to=adl_models.AnchorRefCodeLineAddr(lineIndex=step.line_counter),
            text=f"{value_reg} → {addr_text}",
        )
    )
    return events


def _events_for_bx(
    step: "ASMStep",
    asm_line: "ASMLine",
) -> list[adl_models.ADLEvent]:
    """
    为 BX 指令生成事件：
    - 源寄存器读；
    - PC（R15）写；
    - 箭头：源寄存器 → PC。
    """
    src_param = asm_line.param
    if not src_param or not src_param.type_name:
        return []

    src_reg = _normalize_reg(src_param.text)
    events: list[adl_models.ADLEvent] = [
        adl_models.ADLEventFocusCanvas(target="CU"),
        adl_models.ADLEventMarkRegister(reg=src_reg, mode="read"),
        adl_models.ADLEventMarkRegister(reg="R15", mode="write"),
        adl_models.ADLEventOverlayArrow(
            from_=adl_models.AnchorRefRegisterRow(reg=src_reg),
            to=adl_models.AnchorRefRegisterRow(reg="R15"),
            text=f"{src_reg} → PC",
        ),
    ]
    return events


def _events_for_bl(
    step: "ASMStep",
    asm_line: "ASMLine",
) -> list[adl_models.ADLEvent]:
    """
    为 BL 指令生成事件：
    - 强调“调用目标”和“保存返回地址”；
    - 近似展示 PC/LR 写入。
    """
    target_param = asm_line.param
    if not target_param or not target_param.type_name:
        return []

    target_text = target_param.text.strip()
    events: list[adl_models.ADLEvent] = [
        adl_models.ADLEventFocusCanvas(target="CU"),
        adl_models.ADLEventMarkRegister(reg="R15", mode="write"),
        adl_models.ADLEventMarkRegister(reg="R14", mode="write"),
        adl_models.ADLEventOverlayArrow(
            from_=adl_models.AnchorRefCodeLineAddr(lineIndex=step.line_counter),
            to=adl_models.AnchorRefRegisterRow(reg="R15"),
            text=f"PC ← {target_text}",
        ),
        adl_models.ADLEventOverlayArrow(
            from_=adl_models.AnchorRefCodeLineAddr(lineIndex=step.line_counter),
            to=adl_models.AnchorRefRegisterRow(reg="R14"),
            text="Save return addr",
        ),
    ]
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
    if asm_line is not None:
        basic = asm_line.basic
        if basic == "mov":
            mov_events = _events_for_mov(step, asm_line)
            # 在 SetActiveLine 之后、Wait 之前插入 MOV 相关事件（替换默认的 FocusCanvas）
            events = [
                adl_models.ADLEventSetActiveLine(by="index", value=step.line_counter),
                *mov_events,
                adl_models.ADLEventWait(ms=800),
            ]
        elif basic in {"add", "sub"}:
            add_sub_events = _events_for_add_sub(
                step,
                asm_line,
                op_symbol="+" if basic == "add" else "-",
            )
            if add_sub_events:
                events = [
                    adl_models.ADLEventSetActiveLine(by="index", value=step.line_counter),
                    *add_sub_events,
                    adl_models.ADLEventWait(ms=800),
                ]
        elif basic == "ldr":
            ldr_events = _events_for_ldr(step, asm_line)
            if ldr_events:
                events = [
                    adl_models.ADLEventSetActiveLine(by="index", value=step.line_counter),
                    *ldr_events,
                    adl_models.ADLEventWait(ms=800),
                ]
        elif basic in {"str", "strb"}:
            str_events = _events_for_str(step, asm_line)
            if str_events:
                events = [
                    adl_models.ADLEventSetActiveLine(by="index", value=step.line_counter),
                    *str_events,
                    adl_models.ADLEventWait(ms=800),
                ]
        elif basic == "bx":
            bx_events = _events_for_bx(step, asm_line)
            if bx_events:
                events = [
                    adl_models.ADLEventSetActiveLine(by="index", value=step.line_counter),
                    *bx_events,
                    adl_models.ADLEventWait(ms=800),
                ]
        elif basic == "bl":
            bl_events = _events_for_bl(step, asm_line)
            if bl_events:
                events = [
                    adl_models.ADLEventSetActiveLine(by="index", value=step.line_counter),
                    *bl_events,
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

    # 尝试过滤掉模板中的尾部 `bx lr` 指令对应的最后一步：
    # - 该指令固定由运行时模板追加；
    # - 为了避免误删用户手写的 `bx lr`，仅当它出现在最后一条反汇编指令且 basic == "bx" 时才过滤。
    last = steps[-1]
    last_asm_line = _get_current_asm_line(last)
    # if last_asm_line is not None and last_asm_line.basic == "bx":
    #     steps = steps[:-1]

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
