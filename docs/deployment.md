# YuKit 部署说明

本文档说明 YuKit 当前版本的本地启动、镜像构建、阿里云 ACR 推送、ECS 自动部署，以及在已有 1Panel OpenResty 和 PostgreSQL 容器时的推荐配置。

YuKit 后端使用 PostgreSQL 保存用户、会话、收藏、偏好设置和工具执行历史；使用 Redis 做限流和 ARQ 异步任务队列。当前已实现的工具包括 JSON 格式化、时间戳转换、Base64、正则测试，以及登录后可用的异步文本哈希。

## 本地启动

```powershell
cd frontend
pnpm install
pnpm build
cd ..
Copy-Item .env.example .env
docker compose up --build
```

本地访问地址：

```text
http://localhost:8080
```

本地 `docker-compose.yml` 会启动 Caddy、API、worker、PostgreSQL、Redis 等完整开发环境。它会把 HTTP 发布到 `${YUKIT_HTTP_PORT:-8080}`，HTTPS 发布到 `${YUKIT_HTTPS_PORT:-8443}`。

GitHub OAuth 本地调试需要在 `.env` 中配置：

```text
YUKIT_GITHUB_CLIENT_ID=<github-oauth-client-id>
YUKIT_GITHUB_CLIENT_SECRET=<github-oauth-client-secret>
YUKIT_PUBLIC_BASE_URL=http://localhost:8080
YUKIT_API_BASE_URL=http://localhost:8080/api
```

本地可以开启开发登录：

```text
YUKIT_DEV_AUTH_ENABLED=true
```

生产环境必须关闭：

```text
YUKIT_DEV_AUTH_ENABLED=false
```

## Caddy 和 Nginx/OpenResty 怎么选

如果是一个全新的单应用服务器，Caddy 更省心：配置简单，自动申请和续期 HTTPS 证书，适合小团队快速上线。

如果服务器已经通过 1Panel 管理 OpenResty，或者已经有多个站点共用一个入口代理，继续用 OpenResty/Nginx 更合适。它和现有 1Panel 体系一致，反代规则、站点配置、日志和证书都可以统一管理。

YuKit 当前服务器属于第二种情况：服务器已经有 OpenResty 容器，也已经有 PostgreSQL 容器，所以生产部署推荐：

- 不再启动仓库里的 Caddy。
- 不再启动仓库里的 PostgreSQL。
- 使用现有 OpenResty 作为公网入口。
- 使用现有 PostgreSQL 作为数据库。
- YuKit 自己只启动 `web`、`api`、`worker`、`redis`、`migrate`。

这里的 `web` 镜像内部会用 Nginx 提供静态前端文件，但它不是公网入口。公网入口仍然是你服务器上已经运行的 OpenResty。

## ACR 镜像部署方案

生产环境使用 [docker-compose.prod.yml](../docker-compose.prod.yml)，并把应用拆成两个镜像：

- `:api-latest` 和 `:api-<git-sha>`：FastAPI API、Alembic 数据库迁移、ARQ worker 共用的后端运行镜像。
- `:web-latest` 和 `:web-<git-sha>`：Vue 前端构建产物，由容器内 Nginx 提供静态服务。

`docker-compose.prod.yml` 只启动：

- `yukit-web`
- `yukit-api`
- `yukit-worker`
- `yukit-redis`
- `yukit-migrate`

它不会启动 Caddy，也不会启动 PostgreSQL。因为你的 OpenResty 容器使用的是 Docker `host` 网络，生产 Compose 会把 YuKit 的 `web` 和 `api` 只绑定到宿主机回环地址 `127.0.0.1`，再由 OpenResty 反代进去。这样不会对公网直接暴露 YuKit 容器端口，也可以和 1Panel 里的 OpenResty、PostgreSQL 容器共存。

## GitHub Actions Secrets

在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 中配置：

```text
ACR_REGISTRY=crpi-a848fntml5lhz63u.cn-shenzhen.personal.cr.aliyuncs.com
ACR_IMAGE_REPOSITORY=crpi-a848fntml5lhz63u.cn-shenzhen.personal.cr.aliyuncs.com/aliyun_neeko/yukit
ACR_USERNAME=dbp1906
ACR_PASSWORD=<acr-password>
SERVER_HOST=120.25.195.126
SERVER_USER=<ssh-user>
SERVER_PORT=22
SERVER_SSH_KEY=<private-key>
DEPLOY_PATH=/opt/yukit
```

这些 ACR 地址必须和阿里云控制台显示的实例域名完全一致。比如你能 `docker login` 成功的域名是 `crpi-a848fntml5lhz63u...`，那么 `ACR_REGISTRY`、`ACR_IMAGE_REPOSITORY` 和服务器 `.env` 里的 `YUKIT_IMAGE_REPOSITORY` 都要使用同一个 `crpi-a848fntml5lhz63u` 前缀，不能混用相近的拼写。

GitHub Actions 会通过公网 ACR 地址推送镜像，ECS 服务器默认也通过公网 ACR 地址拉取镜像。不要默认使用 `-vpc` 域名；如果服务器无法解析 VPC ACR 域名，会在 `docker compose pull` 时报 `lookup ...-vpc... no such host`。

推送到 `main` 分支时，CI/CD 会自动执行：

1. 后端检查、类型检查、测试。
2. 前端测试、构建、E2E smoke。
3. 校验本地 Compose 和生产 Compose。
4. 构建并推送 `api-latest`、`api-<git-sha>`、`web-latest`、`web-<git-sha>`。
5. SSH 登录 ECS，拉取镜像，执行数据库迁移，重启 YuKit 服务。

生产前端镜像会按子路径构建：

```text
VITE_BASE_PATH=/yukit/
VITE_API_BASE_URL=/yukit/api
```

如果以后不再使用 `/yukit` 子路径，而是改成独立域名根路径，需要同步修改 GitHub Actions 里的 `Build web image` 构建参数、OpenResty 反代规则、`YUKIT_PUBLIC_BASE_URL` 和 `YUKIT_API_BASE_URL`。

## 首次服务器配置

在 ECS 上创建部署目录：

```bash
mkdir -p /opt/yukit
cd /opt/yukit
```

首次手动部署前，需要先把当前仓库里的生产 Compose 文件同步到服务器。下面这条命令在本地仓库目录执行：

```bash
scp docker-compose.prod.yml root@120.25.195.126:/opt/yukit/docker-compose.prod.yml
```

如果你依赖 GitHub Actions 自动同步，注意 `deploy` job 只会在推送到 `main` 分支时执行；只推送功能分支不会更新 `/opt/yukit/docker-compose.prod.yml`。

你当前服务器的网络情况是：

```bash
docker inspect 1Panel-openresty-awUd --format '{{range $name, $_ := .NetworkSettings.Networks}}{{println $name}}{{end}}'
docker inspect 1Panel-postgresql-Dhce --format '{{range $name, $_ := .NetworkSettings.Networks}}{{println $name}}{{end}}'
```

结果分别是：

```text
OpenResty: host
PostgreSQL: 1panel-network
```

`host` 是 Docker 内置网络，不是 user-defined network，因此不能执行下面这种命令：

```bash
docker network connect --alias yukit-postgres host 1Panel-postgresql-Dhce
```

它会报错：

```text
network-scoped aliases are only supported for user-defined networks
```

推荐的最少改动方案是：

- OpenResty 保持 `host` 网络。
- YuKit 的 `web` 绑定到 `127.0.0.1:18080`。
- YuKit 的 `api` 绑定到 `127.0.0.1:18000`。
- YuKit 的 `api`、`worker`、`migrate` 加入 PostgreSQL 所在的 `1panel-network`。
- 数据库地址使用 `1Panel-postgresql-Dhce:5432`。
- 外部访问路径使用 `http://120.25.195.126/yukit/`，不接管服务器根路径 `/`。

创建 `/opt/yukit/.env`：

```bash
cat > /opt/yukit/.env <<'EOF'
YUKIT_IMAGE_REPOSITORY=crpi-a848fntml5lhz63u.cn-shenzhen.personal.cr.aliyuncs.com/aliyun_neeko/yukit
YUKIT_DB_NETWORK=1panel-network
YUKIT_WEB_HTTP_BIND=127.0.0.1:18080
YUKIT_API_HTTP_BIND=127.0.0.1:18000
YUKIT_ENVIRONMENT=production
YUKIT_DEV_AUTH_ENABLED=false
YUKIT_PUBLIC_BASE_URL=http://120.25.195.126/yukit
YUKIT_API_BASE_URL=http://120.25.195.126/yukit/api
YUKIT_DATABASE_URL=postgresql+asyncpg://<db-user>:<db-password>@1Panel-postgresql-Dhce:5432/yukit
YUKIT_REDIS_URL=redis://redis:6379/0
YUKIT_SESSION_SECRET=<long-random-secret>
YUKIT_LOG_LEVEL=INFO
YUKIT_LOG_FORMAT=json
YUKIT_LOG_MAX_SIZE=10m
YUKIT_LOG_MAX_FILE=5
YUKIT_GITHUB_CLIENT_ID=<github-oauth-client-id>
YUKIT_GITHUB_CLIENT_SECRET=<github-oauth-client-secret>
EOF
```

`YUKIT_COOKIE_SECURE` 默认不需要设置：后端会根据 `YUKIT_API_BASE_URL` 是否使用 `https://` 自动决定是否给 OAuth 和 session cookie 加 `Secure`。当前用 HTTP IP 访问时应保持自动或设为 `false`；绑定 HTTPS 域名后应保持自动或设为 `true`。

创建 `.env` 并同步 compose 后，先做一次配置校验：

```bash
cd /opt/yukit
grep -q 'YUKIT_IMAGE_REPOSITORY' docker-compose.prod.yml || { echo 'docker-compose.prod.yml 不是当前版本，请重新同步'; exit 1; }
docker compose -f docker-compose.prod.yml config >/dev/null
docker compose -f docker-compose.prod.yml config | grep 'image:'
```

正常情况下，最后一条命令应该能看到 `aliyun_neeko/yukit:web-latest`、`aliyun_neeko/yukit:api-latest` 和 `redis:7-alpine`。如果看到 `ACR_REGISTRY`、`ACR_NAMESPACE` 相关 warning，或者看到 `//yukit:latest`，说明 `/opt/yukit/docker-compose.prod.yml` 还是旧版，或者服务器没有加载当前文档里的 `.env` 配置；先重新同步 compose，再继续拉镜像。

如果看到 `lookup crpi-...-vpc... no such host`，说明服务器当前不能解析阿里云 ACR 的 VPC 域名。把 `/opt/yukit/.env` 中的 `YUKIT_IMAGE_REPOSITORY` 改回公网域名：

```text
YUKIT_IMAGE_REPOSITORY=crpi-a848fntml5lhz63u.cn-shenzhen.personal.cr.aliyuncs.com/aliyun_neeko/yukit
```

如果使用已有 PostgreSQL，需要在里面创建 `yukit` 数据库和对应用户。可以通过 1Panel 数据库管理界面创建，也可以进入 PostgreSQL 容器使用 `psql` 创建。

如果你不想依赖 `1Panel-postgresql-Dhce` 这个容器名，也可以额外创建一个专用网络并给 PostgreSQL 加稳定别名：

```bash
docker network create yukit-shared
docker network connect --alias yukit-postgres yukit-shared 1Panel-postgresql-Dhce
```

对应 `.env` 改为：

```text
YUKIT_DB_NETWORK=yukit-shared
YUKIT_DATABASE_URL=postgresql+asyncpg://<db-user>:<db-password>@yukit-postgres:5432/yukit
```

这个专用网络必须是 `docker network create` 创建出来的 user-defined network，不能是内置的 `host` 网络。

## GitHub OAuth 回调地址

当前使用 IP 访问时，GitHub OAuth App 的回调地址配置为：

```text
http://120.25.195.126/yukit/api/auth/github/callback
```

如果登录后浏览器跳到了 `http://120.25.195.126/api/auth/github/callback?...`，说明服务器 `/opt/yukit/.env` 里的 `YUKIT_API_BASE_URL` 少了 `/yukit`，需要改成：

```text
YUKIT_API_BASE_URL=http://120.25.195.126/yukit/api
```

改完后重启 API、worker 和 web，再重新从网页登录。旧的 GitHub `code` 只能使用一次，不能拿旧 callback 地址重复刷新。

如果之后绑定域名和 HTTPS，需要同步修改：

```text
YUKIT_PUBLIC_BASE_URL=https://你的域名/yukit
YUKIT_API_BASE_URL=https://你的域名/yukit/api
```

GitHub OAuth App 的 callback 也要改成：

```text
https://你的域名/yukit/api/auth/github/callback
```

## OpenResty 反向代理

因为 OpenResty 容器使用 `host` 网络，所以它可以直接访问宿主机的 `127.0.0.1`。在现有 OpenResty 站点中添加以下规则，让 YuKit 挂到 `/yukit/` 子路径：

```nginx
location = /yukit {
    return 301 /yukit/;
}

location = /yukit/api {
    return 301 /yukit/api/;
}

location /yukit/api/ {
    proxy_pass http://127.0.0.1:18000/api/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;

    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}

location /yukit/ {
    proxy_pass http://127.0.0.1:18080/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;

    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

注意两个 `proxy_pass` 结尾的 `/`：

- `/yukit/api/` 会被转成后端的 `/api/`。
- `/yukit/` 会被转成前端容器的 `/`。

如果站点里已经有 `location / { ... }`，可以继续保留给原网站使用；这套规则只会接管 `/yukit` 路径。

保存后重载 OpenResty。

可以先在 OpenResty 容器内验证能否访问 YuKit：

```bash
docker exec -it 1Panel-openresty-awUd sh -lc 'wget -qO- http://127.0.0.1:18080/health'
docker exec -it 1Panel-openresty-awUd sh -lc 'wget -qO- http://127.0.0.1:18000/api/health'
```

从外部验证：

```bash
curl -i http://120.25.195.126/yukit/
curl -i http://120.25.195.126/yukit/api/health
curl -i http://120.25.195.126/yukit/api/ready
```

## 手动部署

第一次 CI 推送镜像后，可以在服务器上手动部署一次：

```bash
cd /opt/yukit
grep -q 'YUKIT_IMAGE_REPOSITORY' docker-compose.prod.yml || { echo 'docker-compose.prod.yml 不是当前版本，请重新同步'; exit 1; }
docker compose -f docker-compose.prod.yml config >/dev/null
docker login --username dbp1906 crpi-a848fntml5lhz63u.cn-shenzhen.personal.cr.aliyuncs.com
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml --profile ops run --rm migrate
docker compose -f docker-compose.prod.yml up -d --remove-orphans redis api worker web
docker compose -f docker-compose.prod.yml ps
curl -fsS http://120.25.195.126/yukit/api/ready
```

之后推送到 `main` 分支时，GitHub Actions 的 `deploy` job 会自动执行同样的拉镜像、迁移、重启和健康检查流程。

## 升级和回滚

默认部署使用：

```text
api-latest
web-latest
```

如果要锁定某次发布，可以把生产 Compose 或生产 override 中的镜像 tag 改为：

```text
api-<git-sha>
web-<git-sha>
```

回滚时，把镜像 tag 改回上一个可用版本，然后执行：

```bash
cd /opt/yukit
docker compose -f docker-compose.prod.yml up -d api worker web
curl -fsS http://120.25.195.126/yukit/api/ready
```

## 健康检查

Compose 内置健康检查：

- `api`：访问 `GET /api/health`
- `web`：访问 `GET /health`
- `redis`：执行 `redis-cli ping`

整体就绪检查：

```text
GET /yukit/api/ready
```

`/api/ready` 会检查数据库和 Redis 状态，更适合作为部署后的验收接口。

## 日志

生产 Compose 默认使用 Docker `json-file` 日志驱动，并限制单容器日志为 `YUKIT_LOG_MAX_SIZE` x `YUKIT_LOG_MAX_FILE`，默认约 50MB，避免日志无限占满磁盘。

后端会输出以下 logger：

- `yukit.app`：启动配置摘要，包括环境、公网地址、API 地址和 cookie secure 策略。
- `yukit.request`：每个 HTTP 请求的 method、path、status、duration_ms、request_id。
- `yukit.error`：API 错误码、状态码、path、request_id。
- `yukit.auth`：GitHub OAuth 开始、state 校验失败、token 失败、登录成功等认证事件。
- `yukit.tool`：工具请求入队、同步工具成功或失败。
- `yukit.worker`：异步 worker 任务 running、succeeded、timed_out、failed、canceled。

这些日志不会记录请求 query string、OAuth `code/state` 或工具输入正文。排查登录问题时，优先看 API 日志：

```bash
cd /opt/yukit
docker compose -f docker-compose.prod.yml logs -f api
```

按 request id 追踪一次请求：

```bash
docker compose -f docker-compose.prod.yml logs api | grep 'req_'
```

排查 GitHub 登录：

```bash
docker compose -f docker-compose.prod.yml logs api | grep 'yukit.auth'
docker compose -f docker-compose.prod.yml logs api | grep 'oauth_state_mismatch'
docker compose -f docker-compose.prod.yml logs api | grep 'redirect_uri'
```

排查异步工具：

```bash
docker compose -f docker-compose.prod.yml logs -f api worker
docker compose -f docker-compose.prod.yml logs worker | grep 'worker job'
```

## 数据备份

生产环境使用已有 PostgreSQL 容器，因此优先使用 1Panel 的数据库备份能力。

如果要手动备份，可以在 ECS 上执行：

```bash
mkdir -p /opt/yukit/backups
docker exec -e PGPASSWORD='<db-password>' 1Panel-postgresql-Dhce \
  pg_dump -U <db-user> -d yukit \
  > /opt/yukit/backups/yukit-$(date +%F-%H%M%S).sql
```

建议至少保留：

- 最近 7 天的每日备份。
- 最近 4 周的每周备份。

Redis 不是用户数据的最终来源，但生产 Compose 已开启 AOF 持久化，用于提升队列和限流状态的恢复能力。

## 安全配置

- 生产环境保持 `YUKIT_DEV_AUTH_ENABLED=false`。
- 使用足够长且随机的 `YUKIT_SESSION_SECRET`。
- GitHub OAuth callback 必须和 `YUKIT_API_BASE_URL` 对应。
- Docker stdout 会输出结构化后端日志；需要更详细日志时可设置 `YUKIT_LOG_LEVEL=DEBUG` 后重启服务。
- `YUKIT_ENVIRONMENT=production` 时，API 文档默认不会开放。
- OAuth callback 会校验 state，防止伪造回调。
- 如果使用 HTTP IP 访问，GitHub OAuth 可以工作，但正式对外建议绑定域名并启用 HTTPS。

## 开发服务器

单独启动 API：

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

单独启动前端：

```powershell
cd frontend
pnpm dev
```

前端开发地址：

```text
http://localhost:5173
```
