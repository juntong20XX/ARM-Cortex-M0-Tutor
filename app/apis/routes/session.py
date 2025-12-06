"""

"""
from ... import database as db
from ...core import settings

from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from authlib.integrations.starlette_client import OAuth


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
    s = settings.load_config()
    if not _oauth_initialized:
        _update_oauth_obj()
    if s.login_action == settings.LoginAction.oauth:
        raise NotImplementedError
    elif s.login_action == settings.LoginAction.oauth_pw:
        raise NotImplementedError
    elif s.login_action == settings.LoginAction.direct_oauth:
        return RedirectResponse(request.url_for('/login/direct_oauth'))
    elif s.login_action == settings.LoginAction.password:
        raise NotImplementedError
    elif s.login_action == settings.LoginAction.username_domain:
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
    redirect_uri = request.url_for('/login-oauth')
    with db.db_context() as session:
        provider_name = session.query(db.models.OAuthProvider).first().name
    provider = getattr(oauth, provider_name)
    return await provider.authorize_redirect(request, redirect_uri)


@router.get("/login-oauth/{provider_name}")
async def login_oauth(request: Request, provider_name: str):
    """
    OAuth 认证回调接口
    """
    # TODO: 设计回复模型
    provider = getattr(oauth, provider_name)
    try:
        # 1. 获取 Token
        token = await provider.authorize_access_token(request)
        # 2. 解析用户信息 (Authlib 会自动使用 ID Token 或调用 userinfo 端点)
        user = token.get('userinfo')
        # 3. 将用户信息存入 Session
        if user:
            request.session['user'] = user

        return {"message": "Login successful", "user": user}
    except Exception as e:
        return {"error": str(e)}

