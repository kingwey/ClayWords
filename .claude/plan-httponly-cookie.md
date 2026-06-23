# 计划：Token 迁移到 HttpOnly Cookie

## 背景与动机
报告「八、2」高价值、低风险：当前 token 存 localStorage，易受 XSS 攻击窃取。
迁移到 HttpOnly Cookie 后，JavaScript 无法读取，XSS 无法窃取 token，显著提升安全性。

## 当前架构
- **Frontend**: axios client 从 `localStorage.getItem('access_token')` 读取，手动拼 `Authorization: Bearer {token}`
- **Backend**: FastAPI `HTTPBearer` security，从 `Authorization` header 提取 token
- **CORS**: 已配置 `allow_credentials=True`，cookie 基础设施已就绪
- **部署**: dev 环境 vite proxy `/api` → `localhost:8000`，生产环境待确认（可能同域或 nginx 反向代理）
- **刷新流程**: 当前 401 直接跳登录，**未实现**自动 refresh token 重试

## 方案设计

### A. Cookie 方案（推荐）
**优势**: 最佳安全性，浏览器自动带 cookie，代码最简洁  
**前提**: 前后端同域（或通过 nginx 统一入口）  
**变更**:
1. 后端 `/login` 和 `/refresh` 不再返回 token JSON，改为 `set_cookie` 写入 `access_token` / `refresh_token`（HttpOnly, Secure, SameSite=Lax）
2. 新增 `/auth/logout` 端点，清除 cookie
3. `get_current_user` 依赖改为从 `request.cookies` 读取，移除 `HTTPBearer`
4. 前端移除所有 `localStorage` token 操作，axios 移除 `Authorization` header 拼接（浏览器自动带 cookie）
5. 前端 401 响应时调用 `/auth/refresh`（cookie 自动带 refresh_token），成功后重试原请求

**trade-off**:
- ❌ 跨域部署（前后端不同域）需额外配置 `CORS_ORIGINS` 精确匹配 + 前端 `withCredentials: true`
- ❌ 移动端 WebView / React Native 等非浏览器环境需单独处理 cookie 存储
- ✅ XSS 无法窃取 token（HttpOnly）
- ✅ CSRF 有 SameSite=Lax 基础防护（严格场景可升级 Strict 或加 CSRF token）

### B. 混合方案（备选）
仅 `refresh_token` 用 HttpOnly cookie，`access_token` 仍走 JSON response + localStorage。
**优势**: 短期 access_token 泄露风险可控（15min TTL），长期 refresh_token 受保护  
**劣势**: 复杂度高，XSS 仍可窃取 access_token 并在有效期内冒用

### C. 双模式支持（备选）
同时支持 cookie 和 header 两种认证方式，`get_current_user` 先查 cookie，无则查 header。
**优势**: 向后兼容，移动端可继续用 header  
**劣势**: 维护成本高，安全策略不统一

**选择方案 A（纯 Cookie）**，理由：
- 本项目是 Web 应用，vite proxy 确保 dev 环境同域，生产环境文档未见跨域部署计划
- 简洁性 > 灵活性，后续有移动端需求再加 header 回退

## 实施步骤

### 1. 后端改造 `app/api/auth.py`

#### 1.1 移除 `HTTPBearer`，新增 cookie 依赖
```python
from fastapi import Cookie

async def get_current_user(
    access_token: str = Cookie(None),
    session: AsyncSession = Depends(get_session)
) -> UserInfo:
    if not access_token:
        raise HTTPException(401, "Missing authentication")
    payload = verify_token(access_token, "access")
    # ... 后续逻辑不变
```

#### 1.2 `/login` 端点改写 cookie
```python
from fastapi import Response

@router.post("/login")
async def login(
    request: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session)
):
    # ... 原有验证逻辑
    access_token = create_access_token(...)
    refresh_token = create_refresh_token(...)

    # 写 cookie 而非返回 JSON
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.is_production,  # 生产强制 HTTPS
        samesite="lax",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    # 仍返回 role 供前端路由判断（role 非敏感，无需 HttpOnly）
    return {"role": user_role}
```

#### 1.3 `/refresh` 端点改为从 cookie 读取
```python
@router.post("/refresh")
async def refresh_token(
    refresh_token: str = Cookie(None),
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    if not refresh_token:
        raise HTTPException(401, "Missing refresh token")
    # ... 原有验证逻辑
    # 写新 cookie
    response.set_cookie(...)
    return {"role": user_role}
```

#### 1.4 新增 `/logout`
```python
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}
```

### 2. 前端改造

#### 2.1 `stores/auth.ts` 移除 localStorage，仅持久化 role
```typescript
const role = ref<Role>((localStorage.getItem('role') as Role) || '')

function setAuth(data: { role: string }) {
  role.value = data.role
  localStorage.setItem('role', data.role)
  // 移除 accessToken / refreshToken ref 及其 localStorage 操作
}

function clearAuth() {
  role.value = ''
  localStorage.removeItem('role')
}
```

#### 2.2 `api/client.ts` 改造
- **移除** request interceptor 的 `Authorization` header 拼接
- **axios 配置** 加 `withCredentials: true`（让浏览器自动带 cookie）
- **401 拦截器** 改为调用 `/auth/refresh`，成功后重试原请求

```typescript
const client = axios.create({
  baseURL: '/',
  timeout: 30000,
  withCredentials: true  // 关键：让 cookie 自动携带
})

// 移除 request interceptor（不再手动拼 Authorization）

// Response interceptor - 401 自动刷新
client.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true })
        return client(originalRequest)  // 重试原请求
      } catch (refreshError) {
        // refresh 也失败 → 登出
        useAuthStore().clearAuth()
        router.push('/login')
        return Promise.reject(refreshError)
      }
    }
    ElMessage.error(error.response?.data?.detail || '请求失败')
    return Promise.reject(error)
  }
)
```

#### 2.3 `LoginView.vue` 改造
登录成功后只保存 `role`：
```typescript
const { data } = await axios.post('/api/v1/auth/login', ...)
auth.setAuth({ role: data.role })  // 只传 role
```

#### 2.4 其他直接读 localStorage 的站点清理
- `WorkOrderPopup.vue:124` 移除 `localStorage.getItem('access_token')`（cookie 自动带）
- `OrdersView.vue:251` 移除手动拼 `Authorization` header

### 3. 后端配置微调 `app/core/config.py`

确认有 `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` 和 `JWT_REFRESH_TOKEN_EXPIRE_DAYS`（已存在，无需改）。

### 4. 验证

#### 4.1 手动测试（dev 环境）
1. 启动 backend + vite dev server
2. 登录 `13800000001`，检查浏览器 DevTools → Application → Cookies，应看到 `access_token` / `refresh_token`（HttpOnly ✓）
3. 访问需认证页面（如 `/orders`），Network 面板确认请求自动带 `Cookie` header
4. 等待 access_token 过期或手动删除，触发 401 → 自动 refresh → 重试成功
5. 登出，确认 cookie 被清除

#### 4.2 单测补充
- `tests/test_auth_cookie.py`：测试登录写 cookie、refresh 读写 cookie、logout 清 cookie
- `tests/test_auth_dependency.py`：测试 `get_current_user` 从 cookie 读取

#### 4.3 CORS 验证（若生产跨域）
模拟跨域场景（frontend `localhost:5173`，backend `localhost:8000`），确认：
- `Access-Control-Allow-Credentials: true` 响应头存在
- `Access-Control-Allow-Origin` 精确匹配（不能是 `*`）
- 前端 `withCredentials: true` 生效

## 回退方案

若生产环境发现问题（如跨域配置不符、移动端需求），可快速回退：
1. 后端恢复返回 JSON token，保留 cookie 写入（双模式）
2. 前端恢复 localStorage + header 拼接
3. 下个迭代修正后再切纯 cookie

## 不做 / 留意

- **不改** JWT 签名算法、过期时间（仅改传输方式）
- **不改** role 持久化方式（localStorage 仍存 role 用于路由守卫，role 非敏感）
- **CSRF 防护**: SameSite=Lax 已覆盖多数场景，严格需求可后续加 CSRF token（GET 请求不受 CSRF 影响，POST 有 Lax 保护）
- **移动端**: 本次不覆盖，后续需求再加 header 模式回退

## 验收

- ✅ 浏览器 DevTools 能看到 HttpOnly cookie
- ✅ 登录后访问 `/orders` 等受保护路由成功（自动带 cookie）
- ✅ 手动删除 access_token cookie 后，401 自动 refresh 并重试成功
- ✅ 登出后 cookie 清除，再访问受保护路由跳登录页
- ✅ localStorage 中无 token 残留（仅 role）
- ✅ 单测覆盖 cookie 认证路径
