"""
OAuth 登录示例.
打开 $YourWeb/api/login 登录
"""
from app.apis import main
from app.core import settings
from app import database as db

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key="secret_key",
    max_age=3600  # Session 过期时间(秒)
)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])


app.include_router(main.api_router)

setting = settings.AppSetting(
    database_url="sqlite:///:memory:",
    secret_key="secret_key",
    login_action=settings.LoginAction.direct_oauth)


if __name__ == "__main__":
    db.init_database(setting)
    with db.db_context() as session:
        db.add_group(session, "admin")
        db.add_provider(session,
                        name="authelia",
                        client_id="ACT",
                        client_secret="0sI2SoOidEfjlCi3FnO7j8PeDJ16ABLIf7dRqrlNpJg9rn1F4gwMfarxEgSICr2H",
                        authorize_url="https://fyp-auth.hogwarts.ac/.well-known/openid-configuration",
                        token_url="https://fyp-act.hogwarts.ac/api/login-oauth/authelia",
                        user_info_url="https://exmple.com",
                        group_mapping={"admins": "admin"},
                        unmapped_group_strategy=db.GroupMappingStrategy.REJECT,
                        scope="openid profile email groups")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
