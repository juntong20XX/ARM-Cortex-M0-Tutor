"""

"""
from ..models import LoginSource
from ... import database as db
from ...core import settings
from .. import models

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from authlib.integrations.starlette_client import OAuth

import datetime
from logging import getLogger


logger = getLogger(__name__)


router = APIRouter(tags=["session"])

oauth = OAuth()
_oauth_initialized = False


def _update_oauth_obj():
    global _oauth_initialized
    if _oauth_initialized:
        return
    with db.db_context() as session:
        for provider in session.query(db.models.OAuthProvider).all():
            oauth.register(name=provider.name,
                           client_id=provider.client_id,
                           client_secret=provider.client_secret,
                           server_metadata_url=provider.authorize_url,
                           client_kwargs={
                               "scope": provider.scope,
                           })
    _oauth_initialized = True


@router.get("/login")
async def login(request: Request):
    """
    登录接口, 根据配置自动重定向
    :raise KeyError: 登录方式找不到
    """
    if request.session.get('user'):
        # 无需登录, 重定向到根目录
        return RedirectResponse(request.url_for('/'))
    s = settings.get_app_setting()
    if s.login_action == settings.LoginAction.oauth:
        _update_oauth_obj()
        raise NotImplementedError
    elif s.login_action == settings.LoginAction.oauth_pw:
        _update_oauth_obj()
        raise NotImplementedError
    elif s.login_action == settings.LoginAction.direct_oauth:
        _update_oauth_obj()
        return RedirectResponse(request.url_for('login_direct_oauth'))
    elif s.login_action == settings.LoginAction.password:
        raise NotImplementedError
    elif s.login_action == settings.LoginAction.username_domain:
        _update_oauth_obj()
        raise NotImplementedError
    else:
        raise KeyError("Unintended settings s.login_action, get", s.login_action)


@router.get("/login/direct_oauth")
async def login_direct_oauth(request: Request):
    """
    s.login_action == settings.LoginAction.direct_oauth
    :param request:
    :return:
    """
    with db.db_context() as session:
        provider_name = session.query(db.models.OAuthProvider).first().name
    provider = getattr(oauth, provider_name)
    redirect_uri = request.url_for('login_oauth', provider_name=provider_name)
    return await provider.authorize_redirect(request, redirect_uri)


@router.get("/login-oauth/{provider_name}", response_model=models.UserBaseInfo)
async def login_oauth(request: Request, provider_name: str):
    """
    OAuth 认证回调接口
    :raise KeyError: More than One user found.
    """
    provider = getattr(oauth, provider_name)
    try:
        # 获取 Token
        token = await provider.authorize_access_token(request)
        # 获取用户信息
        user_info = await provider.userinfo(token=token)
        # Check user info in database
        with db.db_context() as session:
            r = db.find_user_by_provider_and_sub(session, provider_name, user_info["sub"])
            if not r:
                db.add_user(session,
                            username=user_info["name"],
                            email=user_info["email"],
                            oauth_name_sub=(provider_name, user_info["sub"]),
                            oauth_groups=user_info["groups"],
                            )
        with db.db_context() as session:
            r = db.find_user_by_provider_and_sub(session, provider_name, user_info["sub"])
            if len(r) == 1:
                user = r[0]
            else:
                raise KeyError("Unintended settings s.login_action, get", provider_name)

            # 解析用户信息 (Authlib 会自动使用 ID Token 或调用 userinfo 端点), 将用户信息存入 Session
            request.session['user'] = token.get('userinfo')

            return {
                "success": True,
                "uuid": user.uuid,
                "display_name": user.username,
                "email": user.email,
                "groups": [group.name for group in user.groups],
                "join_date": user.created_at,
                "login_source": LoginSource.oauth,
                "msg": ""
            }
    except Exception as e:
        logger.error(e)
        return {
            "success": False,
            "msg": str(e),
            "uuid": "0",
            "display_name": "0",
            "email": "0",
            "groups": [],
            "join_date": datetime.datetime.now(),
            "login_source": LoginSource.oauth,
        }
