# YuKit 构建与运行指南

YuKit 是一个公网多人使用的工具箱平台。当前版本包含 FastAPI 后端、Vue 3 前端、PostgreSQL 数据模型、Redis 限流与队列骨架、ARQ Worker、GitHub OAuth 接口、邮箱登录预留接口，以及第一个可用工具 `JSON Format`。

## 1. 准备环境

建议版本：

- Python 3.13+
- Node.js 22+
- pnpm 11+
- Docker Desktop，可选；运行完整 Compose 栈时需要

检查命令：

```powershell
python --version
node --version
pnpm --version
docker compose version
```

## 2. 安装依赖

在项目根目录执行：

```powershell
python -m pip install -e "backend[dev]"
cd frontend
pnpm install
cd ..
```

如果 `pnpm install` 提示 `esbuild` 构建脚本未批准，执行：

```powershell
cd frontend
pnpm approve-builds --all
pnpm install
cd ..
```

## 3. 快速本地开发模式

这个模式使用 SQLite，本地不用先启动 PostgreSQL 和 Redis。适合前后端开发、页面预览和功能调试。

### 3.1 初始化本地数据库

```powershell
New-Item -ItemType Directory -Force .logs | Out-Null
$env:YUKIT_DATABASE_URL="sqlite+aiosqlite:///D:/DevProjects/YuKit/.logs/dev.db"
cd backend
python -m alembic upgrade head
cd ..
```

如果你的项目路径不是 `D:/DevProjects/YuKit`，把上面的路径改成你的实际绝对路径。

### 3.2 启动后端 API

```powershell
$env:YUKIT_DATABASE_URL="sqlite+aiosqlite:///D:/DevProjects/YuKit/.logs/dev.db"
$env:YUKIT_DEV_AUTH_ENABLED="true"
$env:YUKIT_REDIS_URL=""
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端地址：

- 健康检查：http://127.0.0.1:8000/api/health
- 工具元数据：http://127.0.0.1:8000/api/tools

### 3.3 启动前端

另开一个 PowerShell 窗口：

```powershell
cd frontend
pnpm dev -- --host 127.0.0.1 --port 5173
```

打开：

```text
http://127.0.0.1:5173
```

本地开发模式下点击 `Sign in` 会优先使用 dev login。如果 dev login 不可用，前端会跳转到 GitHub OAuth。

## 4. 完整 Docker Compose 模式

这个模式会启动：

- `caddy`：静态资源与反向代理
- `api`：FastAPI
- `worker`：ARQ Worker
- `postgres`：PostgreSQL
- `redis`：Redis

### 4.1 构建前端静态资源

```powershell
cd frontend
pnpm install
pnpm build
cd ..
```

### 4.2 创建环境文件

```powershell
Copy-Item .env.example .env
```

本地 Compose 默认会覆盖 API/数据库/Redis 的容器内连接地址。需要 GitHub OAuth 时，再编辑 `.env`：

```text
YUKIT_GITHUB_CLIENT_ID=你的 GitHub OAuth Client ID
YUKIT_GITHUB_CLIENT_SECRET=你的 GitHub OAuth Client Secret
YUKIT_PUBLIC_BASE_URL=http://localhost:8080
YUKIT_API_BASE_URL=http://localhost:8080/api
```

### 4.3 启动完整服务

```powershell
docker compose up --build
```

打开：

```text
http://localhost:8080
```

查看服务状态：

```powershell
docker compose ps
docker compose logs api
docker compose logs worker
```

停止服务：

```powershell
docker compose down
```

如果需要同时删除数据库和 Redis 卷：

```powershell
docker compose down -v
```

## 5. 验证命令

后端测试：

```powershell
python -m pytest backend/tests -q -p no:cacheprovider
```

后端代码检查：

```powershell
python -m ruff check backend/app backend/tests --no-cache
```

前端测试：

```powershell
cd frontend
pnpm test
cd ..
```

前端生产构建：

```powershell
cd frontend
pnpm build
cd ..
```

Compose 配置检查：

```powershell
docker compose config
```

## 6. 常见问题

### Docker build 连接失败

如果看到类似：

```text
failed to connect to the docker API
```

通常是 Docker Desktop 没有启动，或者当前终端连不上 Docker daemon。先启动 Docker Desktop，再重跑：

```powershell
docker compose config
docker compose up --build
```

### 前端请求 API 失败

开发模式下前端通过 Vite 代理访问后端。确认后端正在监听：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

确认前端是从 `frontend/` 目录启动：

```powershell
cd frontend
pnpm dev -- --host 127.0.0.1 --port 5173
```

### 登录后没有历史或收藏

收藏、偏好和历史需要数据库。快速开发模式下确认 `YUKIT_DATABASE_URL` 已设置，并且已经执行：

```powershell
cd backend
python -m alembic upgrade head
```

### Redis 未启动

快速开发模式可以把 `YUKIT_REDIS_URL` 设为空，后端会跳过 Redis 限流。完整 Compose 模式会自动启动 Redis。

## 7. 当前功能范围

已实现：

- JSON Format 工具
- 匿名运行公开工具
- dev login
- GitHub OAuth 接口
- 邮箱登录预留接口
- 用户收藏
- 用户偏好
- 执行历史
- PostgreSQL/SQLite 数据模型与迁移
- Redis 限流
- ARQ Worker 队列骨架
- Caddy + Docker Compose 部署骨架
- GitHub Actions CI

后续可继续扩展：

- 更多工具插件，例如 Timestamp、Base64、Regex Test
- 真实生产域名 HTTPS 配置
- 管理后台
- 更完整的异步工具 UI 状态轮询
