"""
ADL trace 路由：返回符合 ADL v1 的 TraceResponse。
见 web/src/animation/ADL_SPEC.md。

设计约定：
- Project.source：仅保存原始汇编源代码文本。
- Project.code：保存由 Project.source 解析得到的 ASMLine 序列化缓存（list[dict]），由本模块等逻辑在解析成功后写回。
"""
import asyncio
import logging
from dataclasses import asdict
from tempfile import TemporaryDirectory

from ...kernel import (
    adl_models,
    Config,
    setup,
    build,
    stop_qemu,
    debug,
    ASMLineReader,
    ASMLine,
    ASMParam,
    ASMStep,
    asm_steps_to_trace_response, start_qemu,
)
from ... import database as db

from fastapi import APIRouter, HTTPException
from invoke import Context

logger = logging.getLogger(__name__)
router = APIRouter(tags=["trace"])

# 单次 trace 最大步数，防止过长或死循环
MAX_TRACE_STEPS = 1000


def _source_to_asm_list(source: str) -> list[ASMLine] | None:
    """
    将 project.source 解析为 ASMLine 列表；失败或空返回 None。

    成功解析后会在上层逻辑中将 ASMLine 列表序列化写入 Project.code 作为缓存。
    """
    if not source or not source.strip():
        return None
    reader = ASMLineReader()
    lines: list[ASMLine] = []
    for raw in source.strip().splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("//"):
            continue
        try:
            lines.append(reader.load(line))
        except Exception:
            return None
    return lines if lines else None


def _asm_list_to_serializable(asm_list: list[ASMLine]) -> list[dict]:
    """将 ASMLine 列表转换为可 JSON 序列化的结构，用于存入 Project.code。"""
    return [asdict(asm) for asm in asm_list]


def _code_to_asm_list(code: list) -> list[ASMLine] | None:
    """
    将存储在 Project.code 中的序列化 ASMLine 列表还原为 ASMLine 对象列表。
    预期结构来自 dataclasses.asdict(ASMLine)，字段名需与 ASMLine / ASMParam 一致。

    - code 为空或结构不兼容时返回 None，不抛异常，交由上层决定是否回退到 source。
    """
    if not code:
        return None
    try:
        asm_list: list[ASMLine] = []
        for item in code:
            p = item.get("param") or {"text": "", "type_name": ""}
            p1 = item.get("param_1") or {"text": "", "type_name": ""}
            p2 = item.get("param_2") or {"text": "", "type_name": ""}
            asm = ASMLine(
                basic=item["basic"],
                condition=item["condition"],
                param=ASMParam(**p),
                param_1=ASMParam(**p1),
                param_2=ASMParam(**p2),
            )
            asm_list.append(asm)
        return asm_list if asm_list else None
    except Exception:
        return None


def _run_trace_pipeline_sync(project_uuid: str, asm_list: list[ASMLine], max_steps: int = MAX_TRACE_STEPS) -> list:
    """
    同步执行 kernel 流水线并收集 ASMStep（阻塞）。
    顺序：setup → build → debug(pre=start_qemu) → 迭代 ALoader → stop_qemu，返回 steps。

    这里将 PROJECT_DIR 配置为临时目录，trace 结束后自动清理，避免在磁盘上残留构建产物。
    """
    with TemporaryDirectory(prefix="trace-") as project_dir:
        config = Config(
            GDB_BIN="gdb-multiarch",
            uuid=project_uuid,
            PROJECT_DIR=project_dir,
        )
        c = Context()
        loader = None
        try:
            setup(c, config, asm_list)
            build(c, config)
            # debug: 任务自身带有 pre=[start_qemu]，此处无需显式调用 start_qemu, 但是不显示调用则会连接错误.
            start_qemu(c, config)
            loader = debug(c, config)
            steps: list[ASMStep] = []
            for _ in range(max_steps):
                try:
                    step = next(loader)
                except StopIteration:
                    # 已离开 ASM 文件，正常结束
                    break
                steps.append(step)
            return steps
        finally:
            if loader is not None:
                try:
                    loader.exit()
                except Exception:
                    pass
            try:
                stop_qemu(c, config)
            except Exception:
                pass


def _example_trace_response() -> adl_models.TraceResponse:
    """静态示例 TraceResponse（与 ADL_SPEC.md 示例一致）。"""
    return adl_models.TraceResponse(
        adlVersion=1,
        code=[
            adl_models.CodeLine(text="ldr r1, =0x255", addr="0x00000054"),
            adl_models.CodeLine(text="adds r0, r1, #0x5", addr="0x00000056"),
            adl_models.CodeLine(text="MOVS r1, #5", addr="0x00000058"),
        ],
        initialState=adl_models.InitialState(
            registers={
                "r0": "0x0",
                "r1": "0x0",
                "r2": "0x0",
                "r13": "0x200003f0",
                "r14": "0x51",
                "r15": "0x54",
            },
            flags=adl_models.FlagsSnapshot(N=0, Z=1, C=0, V=0),
        ),
        steps=[
            adl_models.TraceStep(
                snapshot=adl_models.StepSnapshot(
                    pc="0x00000056",
                    lineCounter=1,
                    registers={"r0": "0x0", "r1": "0x255", "r15": "0x56"},
                    flags=adl_models.FlagsSnapshot(N=0, Z=1, C=0, V=0),
                ),
                events=[
                    adl_models.ADLEventSetActiveLine(by="index", value=1),
                    adl_models.ADLEventFocusCanvas(target="CU"),
                    adl_models.ADLEventOverlayArrow(
                        from_=adl_models.AnchorRefCodeLineAddr(lineIndex=1),
                        to=adl_models.AnchorRefCanvasComponent(id="CU"),
                        text="Decode: adds r0, r1, #5",
                    ),
                    adl_models.ADLEventMarkRegister(reg="R1", mode="read"),
                    adl_models.ADLEventOverlayArrow(
                        from_=adl_models.AnchorRefCodeLineAddr(lineIndex=1),
                        to=adl_models.AnchorRefRegisterRow(reg="R1"),
                        text="Read R1 = 0x255",
                    ),
                    adl_models.ADLEventWait(ms=800),
                ],
            ),
            adl_models.TraceStep(
                snapshot=adl_models.StepSnapshot(
                    pc="0x00000058",
                    lineCounter=2,
                    registers={"r0": "0x25a", "r1": "0x255", "r15": "0x58"},
                    flags=adl_models.FlagsSnapshot(N=0, Z=0, C=0, V=0),
                ),
                events=[
                    adl_models.ADLEventSetActiveLine(by="index", value=2),
                    adl_models.ADLEventFocusCanvas(target="ALU"),
                    adl_models.ADLEventMarkRegister(reg="R1", mode="clear"),
                    adl_models.ADLEventMarkRegister(reg="R0", mode="write"),
                    adl_models.ADLEventAnnotateBus(
                        text="0x255 + 5 = 0x25a",
                        at="writeback",
                    ),
                    adl_models.ADLEventOverlayArrow(
                        from_=adl_models.AnchorRefCanvasComponent(id="ALU"),
                        to=adl_models.AnchorRefRegisterRow(reg="R0"),
                        text="Write R0 = 0x25a",
                    ),
                    adl_models.ADLEventWait(ms=800),
                ],
            ),
        ],
    )


def _error_trace_response(message: str) -> adl_models.TraceResponse:
    """
    将编译/运行时错误包装为一个简单的 ADL TraceResponse，前端可在统一视图中展示错误信息。
    """
    return adl_models.TraceResponse(
        adlVersion=1,
        code=[adl_models.CodeLine(text="/* trace error */", addr=None)],
        initialState=adl_models.InitialState(
            registers={},
            flags=adl_models.FlagsSnapshot(N=0, Z=0, C=0, V=0),
        ),
        steps=[
            adl_models.TraceStep(
                snapshot=adl_models.StepSnapshot(
                    pc="0x00000000",
                    lineCounter=0,
                    registers={},
                    flags=adl_models.FlagsSnapshot(N=0, Z=0, C=0, V=0),
                ),
                events=[
                    adl_models.ADLEventSetActiveLine(by="index", value=0),
                    adl_models.ADLEventFocusCanvas(target="None"),
                    adl_models.ADLEventAnnotateBus(
                        text=message,
                        at="writeback",
                    ),
                ],
            )
        ],
    )


@router.get("/project/trace", response_model=adl_models.TraceResponse)
async def get_project_trace(uuid: str | None = None):
    """
    兼容前端请求路径：/api/project/trace?uuid=...
    - 未提供 uuid 时返回静态示例；
    - 提供 uuid 时复用下方 get_trace 的逻辑。
    """
    if not uuid:
        return _example_trace_response()
    return await get_trace(uuid)


@router.get("/trace", response_model=adl_models.TraceResponse)
async def get_trace_example():
    """无 project_uuid 时返回静态示例，供前端 Demo 与测试使用。"""
    return _example_trace_response()


@router.get("/trace/stream")
async def get_trace_stream():
    """
    预留：SSE 流式返回 TraceStep。后续可按 ADL 规范逐条发送 TraceStep。
    """
    raise HTTPException(
        status_code=501,
        detail="Streaming trace not implemented yet. Use GET /api/trace for batch.",
    )


@router.get("/trace/{project_uuid}", response_model=adl_models.TraceResponse)
async def get_trace(project_uuid: str):
    """
    返回 ADL v1 的 TraceResponse。

    - 正常情况下优先使用 Project.code（由 project 路由维护的 ASMLine 序列化缓存）恢复 ASMLine；
    - 当 code 为空或结构不兼容时，回退使用 Project.source 解析，并在成功后刷新 Project.code；
    - 若均不可用，则回退为静态示例。
    """
    # 先在 Session 中读取所需字段，避免在 Session 关闭后访问懒加载属性导致 DetachedInstanceError
    with db.db_context() as session:
        projects = db.find_project_by_uuid(session, project_uuid)
        if not projects:
            return _example_trace_response()
        project = projects[0]
        project_uuid_value = project.uuid
        project_code = project.code
        project_source = project.source
        project_executed = project.executed

    # 0. 若有 project.executed 缓存且结构合法，直接返回 ADL，避免重复执行流水线
    if project_executed and isinstance(project_executed, list) and len(project_executed) > 0:
        cached = project_executed[0]
        if isinstance(cached, dict) and "adlVersion" in cached and "steps" in cached:
            try:
                return adl_models.TraceResponse.model_validate(cached)
            except Exception:
                pass  # 缓存结构不兼容时忽略，继续走流水线

    # 1. 优先从 Project.code 反序列化 ASMLine 列表
    asm_list = _code_to_asm_list(project_code)

    # 2. 若 code 不可用，再回退使用 source 解析，并顺便刷新 code 缓存
    if asm_list is None:
        asm_list = _source_to_asm_list(project_source or "")
        if asm_list is None:
            return _example_trace_response()
        try:
            with db.db_context() as session:
                db.update_project(
                    session,
                    project_uuid,
                    code=_asm_list_to_serializable(asm_list),
                    commit=True,
                )
        except Exception:
            logger.exception(
                "failed to refresh cached ASM code for project %s", project_uuid
            )

    try:
        steps = await asyncio.to_thread(
            _run_trace_pipeline_sync,
            project_uuid_value,
            asm_list,
            MAX_TRACE_STEPS,
        )
    except Exception as e:
        logger.exception("trace pipeline failed for project %s: %s", project_uuid, e)
        return _error_trace_response(str(e))

    if not steps:
        return _example_trace_response()

    trace_response = asm_steps_to_trace_response(steps)
    try:
        with db.db_context() as session:
            db.update_project(
                session,
                project_uuid,
                executed=[trace_response.model_dump()],
                commit=True,
            )
    except Exception:
        logger.exception(
            "failed to cache executed trace for project %s", project_uuid
        )
    return trace_response
