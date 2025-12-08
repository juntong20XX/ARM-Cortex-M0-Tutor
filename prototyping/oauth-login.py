import os
from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth

app = FastAPI()

# --- 配置部分 ---
# 用于加密 Session 的密钥，生产环境请使用随机长字符串
SECRET_KEY = "4BlbAaGdPohrERFfDeb4oIhg3jY9G4lWsjoe1OpMClxGfqJfoSQAKJOs3Fp1S6KK"

# Authelia 配置
AUTHELIA_BASE_URL = "https://fyp-auth.hogwarts.ac"
CLIENT_ID = "ACT"  # 必须与 Authelia 配置文件中的 id 一致
CLIENT_SECRET = "0sI2SoOidEfjlCi3FnO7j8PeDJ16ABLIf7dRqrlNpJg9rn1F4gwMfarxEgSICr2H"  # Authelia 中配置的 secret 的明文

# --- 初始化 ---
# 1. 添加 Session 中间件 (Authlib 需要用它来存储临时状态 state)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# 2. 配置 OAuth
oauth = OAuth()
oauth.register(
    name='authelia',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url=f'{AUTHELIA_BASE_URL}/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email'
    }
)


# --- 路由 ---

@app.get("/")
async def homepage(request: Request):
    """首页：显示当前用户信息"""
    user = request.session.get('user')
    if user:
        return {"status": "Logged in", "user": user}
    return {"status": "Guest", "link": "Go to /login to authenticate"}


@app.get("/login")
async def login(request: Request):
    """登录接口：重定向到 Authelia"""
    # redirect_uri 必须与 Authelia 配置中的 redirect_uris 完全一致
    redirect_uri = request.url_for('auth')
    return await oauth.authelia.authorize_redirect(request, redirect_uri)


@app.get("/auth")
async def auth(request: Request):
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


@app.get("/logout")
async def logout(request: Request):
    """登出：清除 Session"""
    request.session.pop('user', None)
    return {"message": "Logged out"}


if __name__ == "__main__":
    import uvicorn

    # 本地运行
    uvicorn.run(app, host="0.0.0.0", port=8000)