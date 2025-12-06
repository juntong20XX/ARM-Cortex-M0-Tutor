"""
test oauth
"""
from ARM_Cortex_M0_Tutor.connector import debug
from app.core import settings
from app.database import init_database
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
    init_database(setting)
    uvicorn.run(f"test_oauth:app", host="0.0.0.0", port=8000)
