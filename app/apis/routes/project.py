"""
项目相关路由.

XXX: 跳过权限认证.

设计约定：
- DBProject.source：仅保存原始汇编源代码文本；
- DBProject.code：保存根据 source 解析得到的 ASMLine 序列化缓存（list[dict]）；
- DBProject.executed：保存与当前 source/code 对应的执行轨迹缓存。
"""
from dataclasses import asdict

from ... import database as db
from ... import services
from .. import models
from ...kernel import ASMLineReader, ASMLine, ASMParam

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from logging import getLogger

logger = getLogger(__name__)

router = APIRouter(tags=["project"])


def _setup_project_info(project: db.models.DBProject, simplified=False) -> models.ProjectInfo:
    return models.ProjectInfo(
        success=True,
        msg="",
        uuid=project.uuid,
        name=project.name,
        content=project.content,
        description=project.description,
        source=project.source if not simplified else "",
        code=project.code if not simplified else [],
        executed=project.executed if not simplified else [],
        owner_id=project.owner_id,
        owner_name=project.owner.username,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _source_to_asm_list_for_project(source: str) -> list[ASMLine]:
    """
    将项目的 source 文本解析为 ASMLine 列表。

    - 忽略空行与以 ';' / '//' 开头的注释行；
    - 任一有效代码行解析失败即抛出异常，由上层转换为 4xx 错误；
    - 若无有效代码行，返回空列表（视为合法但无指令的程序）。
    """
    reader = ASMLineReader()
    lines: list[ASMLine] = []

    if not source:
        return []

    for raw in source.splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("//"):
            continue
        # ASMLineReader.load 可能抛出 AssertionError / ValueError，交由调用方处理
        asm = reader.load(line)
        lines.append(asm)

    return lines


def _asm_list_to_serializable(asm_list: list[ASMLine]) -> list[dict]:
    """
    将 ASMLine 列表转换为可 JSON 序列化的结构，用于存入 DBProject.code。
    """
    return [asdict(asm) for asm in asm_list]


@router.get("/project/info/{project_uuid}", response_model=models.ProjectInfo)
async def get_project_info(project_uuid: str):
    """
    获取项目信息
    :param project_uuid: 项目 UUID
    :return: 项目信息
    :raise HTTPException: 项目未找到
    """
    with db.db_context() as session:
        projects = db.find_project_by_uuid(session, project_uuid)
        if not projects:
            raise HTTPException(status_code=404, detail=f"Project '{project_uuid}' not found")

        project = projects[0]
        return _setup_project_info(project)


@router.put("/project/source/{project_uuid}", response_model=models.BaseResponse)
async def update_project_source(request: Request, project_uuid: str, body: models.ProjectSourceUpdate):
    """
    更新项目源代码；解析成功后同步刷新 code（ASMLine 序列化缓存），并清空 executed。
    需已登录且为项目属主或 administrator 组用户。

    :param project_uuid: 项目 UUID
    :param body: 包含新源代码的请求体
    :return: 操作结果
    :raise HTTPException: 项目未找到或无权操作
    """
    try:
        asm_list = _source_to_asm_list_for_project(body.source)
    except (AssertionError, ValueError) as e:
        # 源码无法解析为合法 ASM 序列：返回 400，保持 source/code/executed 不变
        logger.exception("invalid assembly source when updating project %s", project_uuid)
        raise HTTPException(status_code=400, detail="Invalid assembly source") from e

    code_payload = _asm_list_to_serializable(asm_list)

    user = request.session.get("user")
    with db.db_context() as session:
        projects = db.find_project_by_uuid(session, project_uuid)
        if not projects:
            raise HTTPException(status_code=404, detail=f"Project '{project_uuid}' not found")
        project = projects[0]
        if not services.can_manage_project(session, user, project):
            raise HTTPException(status_code=403, detail="You can only update your own project")
        try:
            db.update_project(
                session,
                project_uuid,
                source=body.source,
                code=code_payload,
                executed=[],  # 旧执行轨迹与新代码不再对应
                commit=True,
            )
            return models.BaseResponse(success=True, msg="Source and code updated successfully")
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.post("/project/create")
async def create_project(request: Request, project_info: models.ProjectInfo):
    """
    创建新项目，需要已登录会话。
    """
    user = request.session.get("user")
    if not user or not isinstance(user, dict):
        raise HTTPException(status_code=401, detail="Please login first")
    user_uuid = user.get("uuid")
    if not user_uuid:
        raise HTTPException(status_code=401, detail="Please login first")
    # 先根据 source 解析并生成 code 缓存；解析失败时直接返回 400，不创建项目
    code_payload: list = []
    try:
        asm_list = _source_to_asm_list_for_project(project_info.source)
        code_payload = _asm_list_to_serializable(asm_list)
    except (AssertionError, ValueError) as e:
        logger.exception("invalid assembly source when creating project %s", project_info.name)
        raise HTTPException(status_code=400, detail="Invalid assembly source") from e

    with db.db_context() as session:
        user_list = db.find_user_by_uuid(session, user_uuid)
        if not user_list:
            raise HTTPException(status_code=401, detail="Please login first")
        user_obj = user_list[0]
        db.add_project(
            session,
            project_info.name,
            project_info.content,
            user_obj.uuid,
            project_info.description,
            project_info.source,
            code_payload,
        )
    return JSONResponse(
        status_code=201,
        content={"success": True, "msg": "Project created successfully"},
    )


@router.put("/project/update/{project_uuid}", response_model=models.BaseResponse)
async def update_project_meta(request: Request, project_uuid: str, body: models.ProjectUpdateRequest):
    """
    更新项目元信息（名称、描述、content）。需已登录且只能修改自己拥有的项目。
    """
    user = request.session.get("user")
    if not user or not isinstance(user, dict):
        raise HTTPException(status_code=401, detail="Please login first")
    user_uuid = user.get("uuid")
    if not user_uuid:
        raise HTTPException(status_code=401, detail="Please login first")

    with db.db_context() as session:
        projects = db.find_project_by_uuid(session, project_uuid)
        if not projects:
            raise HTTPException(status_code=404, detail=f"Project '{project_uuid}' not found")
        project = projects[0]
        if not services.can_manage_project(session, user, project):
            raise HTTPException(status_code=403, detail="You can only update your own project")

        kwargs = {}
        if body.name is not None:
            kwargs["name"] = body.name
        if body.description is not None:
            kwargs["description"] = body.description
        if body.content is not None:
            kwargs["content"] = body.content
        if not kwargs:
            return models.BaseResponse(success=True, msg="Nothing to update")

        try:
            db.update_project(session, project_uuid, commit=True, **kwargs)
            return models.BaseResponse(success=True, msg="Project updated successfully")
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.delete("/project/delete/{project_uuid}", response_model=models.BaseResponse)
async def delete_project_endpoint(request: Request, project_uuid: str):
    """
    删除项目。需已登录且只能删除自己拥有的项目。
    """
    user = request.session.get("user")
    if not user or not isinstance(user, dict):
        raise HTTPException(status_code=401, detail="Please login first")
    user_uuid = user.get("uuid")
    if not user_uuid:
        raise HTTPException(status_code=401, detail="Please login first")

    with db.db_context() as session:
        projects = db.find_project_by_uuid(session, project_uuid)
        if not projects:
            raise HTTPException(status_code=404, detail=f"Project '{project_uuid}' not found")
        project = projects[0]
        if not services.can_manage_project(session, user, project):
            raise HTTPException(status_code=403, detail="You can only delete your own project")

        try:
            db.delete_project(session, project_uuid, commit=True)
            return models.BaseResponse(success=True, msg="Project deleted successfully")
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.get("/project/list", response_model=list[models.ProjectInfo])
async def get_project_list(request: Request):
    """
    获取可见的项目.
    :return:
    """
    user = request.session.get('user')
    # TODO: check permission, just return all projects here
    with db.db_context() as session:
        all_projects = db.find_all_projects(session)
        return [_setup_project_info(p, simplified=True) for p in all_projects]
