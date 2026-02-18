"""
ADL trace 路由：返回符合 ADL v1 的 TraceResponse。
见 web/src/animation/ADL_SPEC.md。
"""
from .. import models

from fastapi import APIRouter, HTTPException


router = APIRouter(tags=["trace"])


def _example_trace_response() -> models.TraceResponse:
    """静态示例 TraceResponse（与 ADL_SPEC.md 示例一致）。"""
    return models.TraceResponse(
        adlVersion=1,
        code=[
            models.CodeLine(text="ldr r1, =0x255", addr="0x00000054"),
            models.CodeLine(text="adds r0, r1, #0x5", addr="0x00000056"),
            models.CodeLine(text="MOVS r1, #5", addr="0x00000058"),
        ],
        initialState=models.InitialState(
            registers={
                "r0": "0x0",
                "r1": "0x0",
                "r2": "0x0",
                "r13": "0x200003f0",
                "r14": "0x51",
                "r15": "0x54",
            },
            flags=models.FlagsSnapshot(N=0, Z=1, C=0, V=0),
        ),
        steps=[
            models.TraceStep(
                snapshot=models.StepSnapshot(
                    pc="0x00000056",
                    lineCounter=1,
                    registers={"r0": "0x0", "r1": "0x255", "r15": "0x56"},
                    flags=models.FlagsSnapshot(N=0, Z=1, C=0, V=0),
                ),
                events=[
                    models.ADLEventSetActiveLine(by="index", value=1),
                    models.ADLEventFocusCanvas(target="CU"),
                    models.ADLEventOverlayArrow(
                        from_=models.AnchorRefCodeLineAddr(lineIndex=1),
                        to=models.AnchorRefCanvasComponent(id="CU"),
                        text="Decode: adds r0, r1, #5",
                    ),
                    models.ADLEventMarkRegister(reg="R1", mode="read"),
                    models.ADLEventOverlayArrow(
                        from_=models.AnchorRefCodeLineAddr(lineIndex=1),
                        to=models.AnchorRefRegisterRow(reg="R1"),
                        text="Read R1 = 0x255",
                    ),
                    models.ADLEventWait(ms=800),
                ],
            ),
            models.TraceStep(
                snapshot=models.StepSnapshot(
                    pc="0x00000058",
                    lineCounter=2,
                    registers={"r0": "0x25a", "r1": "0x255", "r15": "0x58"},
                    flags=models.FlagsSnapshot(N=0, Z=0, C=0, V=0),
                ),
                events=[
                    models.ADLEventSetActiveLine(by="index", value=2),
                    models.ADLEventFocusCanvas(target="ALU"),
                    models.ADLEventMarkRegister(reg="R1", mode="clear"),
                    models.ADLEventMarkRegister(reg="R0", mode="write"),
                    models.ADLEventAnnotateBus(
                        text="0x255 + 5 = 0x25a",
                        at="writeback",
                    ),
                    models.ADLEventOverlayArrow(
                        from_=models.AnchorRefCanvasComponent(id="ALU"),
                        to=models.AnchorRefRegisterRow(reg="R0"),
                        text="Write R0 = 0x25a",
                    ),
                    models.ADLEventWait(ms=800),
                ],
            ),
        ],
    )


@router.get("/trace", response_model=models.TraceResponse)
async def get_trace():
    """
    返回 ADL v1 的 TraceResponse（当前为静态示例）。
    前端 Demo 据此驱动代码高亮、寄存器、画布与箭头动画。
    """
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
