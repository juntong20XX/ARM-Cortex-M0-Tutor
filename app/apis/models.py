"""
FastApi Models
"""
from pydantic import BaseModel, Field

from enum import Enum
from typing import Any, Literal, Union
from datetime import datetime

# ---------------------------------------------------------------------------
# ADL v1 (Animation Description Language) – see web/src/animation/ADL_SPEC.md
# ---------------------------------------------------------------------------

ADL_VERSION = 1


class CodeLine(BaseModel):
    """Source line with optional address."""
    text: str
    addr: str | None = None


class FlagsSnapshot(BaseModel):
    """N, Z, C, V each 0 or 1."""
    N: Literal[0, 1]
    Z: Literal[0, 1]
    C: Literal[0, 1]
    V: Literal[0, 1]


# AnchorRef variants (discriminated by "kind")
class AnchorRefCodeLineAddr(BaseModel):
    kind: Literal["CodeLineAddr"] = "CodeLineAddr"
    lineIndex: int


class AnchorRefPC(BaseModel):
    kind: Literal["PC"] = "PC"
    pc: str


class AnchorRefRegisterRow(BaseModel):
    kind: Literal["RegisterRow"] = "RegisterRow"
    reg: str


class AnchorRefCanvasComponent(BaseModel):
    kind: Literal["CanvasComponent"] = "CanvasComponent"
    id: Literal["CU", "REG", "ALU"]


AnchorRef = Union[
    AnchorRefCodeLineAddr,
    AnchorRefPC,
    AnchorRefRegisterRow,
    AnchorRefCanvasComponent,
]


# ADL event variants (discriminated by "type")
class ADLEventSetActiveLine(BaseModel):
    type: Literal["SetActiveLine"] = "SetActiveLine"
    by: Literal["pc", "index"]
    value: int | str


class ADLEventFocusCanvas(BaseModel):
    type: Literal["FocusCanvas"] = "FocusCanvas"
    target: Literal["CU", "REG", "ALU", "None"]


class ADLEventMarkRegister(BaseModel):
    type: Literal["MarkRegister"] = "MarkRegister"
    reg: str
    mode: Literal["read", "write", "clear"]


class ADLEventOverlayArrow(BaseModel):
    type: Literal["OverlayArrow"] = "OverlayArrow"
    from_: AnchorRef = Field(alias="from")
    to: AnchorRef
    text: str

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class ADLEventAnnotateBus(BaseModel):
    type: Literal["AnnotateBus"] = "AnnotateBus"
    text: str
    at: Literal["aluInputA", "aluInputB", "writeback"]


class ADLEventWait(BaseModel):
    type: Literal["Wait"] = "Wait"
    ms: int


ADLEvent = Union[
    ADLEventSetActiveLine,
    ADLEventFocusCanvas,
    ADLEventMarkRegister,
    ADLEventOverlayArrow,
    ADLEventAnnotateBus,
    ADLEventWait,
]


class StepSnapshot(BaseModel):
    """Per-step state."""
    pc: str
    lineCounter: int
    activeInstructionIndex: int | None = None
    registers: dict[str, str] = Field(default_factory=dict)
    flags: FlagsSnapshot
    memoryDelta: dict[str, int] | None = None


class TraceStep(BaseModel):
    """Single step: snapshot + events."""
    snapshot: StepSnapshot
    events: list[ADLEvent] = Field(default_factory=list)


class InitialState(BaseModel):
    """Initial registers/flags/memory delta."""
    registers: dict[str, str] | None = None
    flags: FlagsSnapshot | None = None
    memoryDelta: dict[str, int] | None = None


class TraceResponse(BaseModel):
    """ADL v1 top-level trace response."""
    adlVersion: Literal[1] = ADL_VERSION
    code: list[CodeLine] | None = None
    disassembly: list[Any] | None = None
    initialState: InitialState | None = None
    steps: list[TraceStep]

    model_config = {"serialize_by_alias": True}


class LoginSource(str, Enum):
    oauth = "oauth"
    passwd = "passwd"


class Login(BaseModel):
    """

    """
    login_source: LoginSource

class UserBaseInfo(BaseModel):
    success: bool
    msg: str
    uuid: str
    display_name: str
    email: str
    groups: list[str]
    join_date: datetime
    last_login: datetime
    login_source: LoginSource


class ProjectInfo(BaseModel):
    """
    项目信息响应模型
    """
    success: bool
    msg: str
    uuid: str
    name: str
    content: str
    description: str | None
    source: str
    code: list
    executed: list
    owner_id: str
    owner_name: str
    created_at: datetime
    updated_at: datetime


class ProjectSourceUpdate(BaseModel):
    """
    更新项目源代码的请求模型
    """
    source: str


class BaseResponse(BaseModel):
    """
    通用响应模型
    """
    success: bool
    msg: str
