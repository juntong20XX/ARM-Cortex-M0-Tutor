"""
test oauth
"""
from app.core import settings
from app import database as db
from app.apis.routes.session import router

import uvicorn
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

app = FastAPI()
app.include_router(router)
app.add_middleware(
    SessionMiddleware,
    secret_key="secret_key",
    max_age=3600  # Session 过期时间(秒)
)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

setting = settings.AppSetting(
    database_url="sqlite:///:memory:",
    secret_key="secret_key",
    login_action=settings.LoginAction.direct_oauth)

if __name__ == "__main__":
    db.init_database(setting)
    with db.db_context() as session:
        db.add_user_group(session, name="admin")
        db.add_provider(session,
                        name="authelia",
                        client_id="ACT",
                        client_secret="0sI2SoOidEfjlCi3FnO7j8PeDJ16ABLIf7dRqrlNpJg9rn1F4gwMfarxEgSICr2H",
                        authorize_url="https://fyp-auth.hogwarts.ac/.well-known/openid-configuration",
                        token_url="https://fyp-act.hogwarts.ac/login-oauth/test",
                        user_info_url="https://exmple.com",
                        group_mapping={"admins": "admin"},
                        scope="openid profile email groups")

    uvicorn.run(f"test_oauth:app", host="0.0.0.0", port=8000)
