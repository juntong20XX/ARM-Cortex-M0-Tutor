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
        db.add_provider(session,
                        name="authelia",
                        client_id="ACT",
                        client_secret="XXX",
                        authorize_url="YYY",
                        token_url="ZZZ",
                        user_info_url="https://exmple.com",
                        scope="openid profile email")

    uvicorn.run(f"test_oauth:app", host="0.0.0.0", port=8000)
