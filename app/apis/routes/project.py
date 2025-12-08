"""
项目相关路由
"""
from ... import database as db
from .. import models

from fastapi import APIRouter, HTTPException

from logging import getLogger


logger = getLogger(__name__)


router = APIRouter(tags=["project"])


@router.get("/project/info/{project_name}", response_model=models.ProjectInfo)
async def get_project_info(project_name: str):
    """
    获取项目信息
    :param project_name: 项目名称
    :return: 项目信息
    :raise HTTPException: 项目未找到
    """
    with db.db_context() as session:
        projects = db.find_project_by_name(session, project_name)
        if not projects:
            raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
        
        project = projects[0]
        
        return models.ProjectInfo(
            success=True,
            msg="",
            uuid=project.uuid,
            name=project.name,
            content=project.content,
            description=project.description,
            source=project.source,
            code=project.code,
            executed=project.executed,
            owner_id=project.owner_id,
            owner_name=project.owner.username,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


@router.put("/project/source/{project_uuid}", response_model=models.BaseResponse)
async def update_project_source(project_uuid: str, body: models.ProjectSourceUpdate):
    """
    更新项目源代码
    :param project_uuid: 项目 UUID
    :param body: 包含新源代码的请求体
    :return: 操作结果
    :raise HTTPException: 项目未找到
    """
    with db.db_context() as session:
        try:
            db.update_project(session, project_uuid, source=body.source, commit=True)
            return models.BaseResponse(success=True, msg="Source updated successfully")
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
