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
with db.db_context() as session:
    for provider in session.query(db.models.OAuthProvider).all():
        oauth.register(name=provider.name,
                       client_id=provider.client_id,
                       client_secret=provider.client_secret,
                       server_metadata_url=provider.authorize_url,
                       client_kwargs={
                           "scope": provider.scope,
                       })


@router.post("/login")
async def login(request: Request):
    """
    登录接口, 根据配置自动重定向
    """
    if request.session.get('user'):
        # 无需登录, 重定向到根目录
        return RedirectResponse(request.url_for('/'))

    redirect_uri = request.url_for('auth')
    print(request.url_for('auth'))
    return await oauth.authelia.authorize_redirect(request, redirect_uri)


@router.post("/login-oauth")
async def login_oauth(request: Request):
    """回调接口：Authelia 验证完成后跳回这里"""
    try:
        # 1. 获取 Token
        token = await oauth.authelia.authorize_access_token(request)
        # 2. 解析用户信息 (Authlib 会自动使用 ID Token 或调用 userinfo 端点)
        user = token.get('userinfo')

        # 3. 将用户信息存入 Session
        if user:
            request.session['user'] = user

        return {"message": "Login successful", "user": user}
    except Exception as e:
        return {"error": str(e)}


@router.post("/login/access-token")
def login_access_token(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = security.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    user = security.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )
    send_email(
        email_to=user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Password recovery email sent")


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = security.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    hashed_password = get_password_hash(password=body.new_password)
    user.hashed_password = hashed_password
    session.add(user)
    session.commit()
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = security.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )