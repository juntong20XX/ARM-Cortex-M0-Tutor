"""
ADL trace 路由：返回符合 ADL v1 的 TraceResponse。
见 web/src/animation/ADL_SPEC.md。
"""
from .. import models
from ...kernel import adl_models
from ... import database as db

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["trace"])


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


@router.get("/trace/{project_uuid}", response_model=adl_models.TraceResponse)
async def get_trace(project_uuid: str):
    """
    返回 ADL v1 的 TraceResponse（当前为静态示例）。
    前端 Demo 据此驱动代码高亮、寄存器、画布与箭头动画。
    """
    with db.db_context() as session:
        projects = db.find_project_by_uuid(session, project_uuid)
        if not projects:
            return _example_trace_response()
        project = projects[0]


@router.get("/trace/stream")
async def get_trace_stream():
    """
    预留：SSE 流式返回 TraceStep。后续可按 ADL 规范逐条发送 TraceStep。
    """
    raise HTTPException(
        status_code=501,
        detail="Streaming trace not implemented yet. Use GET /api/trace for batch.",
    )
