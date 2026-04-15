# MicX 智能服务工作台 | MicX Intelligent Workspace

[English](#english-section) | [中文](#中文-section)

---

<!-- 中文部分 -->
# 中文-section

## MicX 版本说明

### 版本对比：MicX vs DeerFlow 原版

| 类别 | DeerFlow 原版 | MicX 版本 |
|------|--------------|-----------|
| **Agent 编排** | ✅ | ✅ |
| **沙箱执行** | ✅ | ✅ |
| **工具系统** | ✅ | ✅ |
| **MCP 集成** | ✅ | ✅ |
| **Admin 控制台** | ❌ | ✅ **新增** |
| **监控中心** | ❌ | ✅ **新增** |
| **配置中心** | ❌ | ✅ **新增** |
| **用户/工作区管理** | ❌ | ✅ **新增** |
| **技能远程安装** | ❌ | ✅ **新增** |
| **线程可见性** | ❌ | ✅ **新增** |
| **中文本地化** | 部分 | ✅ **完整** |
| **品牌定制** | DeerFlow | ✅ **MicX** |
| **安全加固** | 基础 | ✅ **生产级** |
| **Checkpoint 持久化** | Memory | ✅ **SQLite** |

---

### MicX 新增功能详情

#### 1. Admin 管理控制台

| 功能 | 说明 |
|------|------|
| **监控中心** | 健康状态、指标概览、追踪配置、最近问题面板 |
| **配置中心** | 系统配置、Tracing 配置 (LangSmith/Langfuse)、品牌配置 |
| **模型管理** | 模型配置 CRUD、API Key 管理、覆盖配置 |
| **用户管理** | 用户 CRUD、邀请、禁用、角色管理 |
| **工作区管理** | 创建/重命名/删除工作区、成员管理 |
| **技能管理** | 远程安装、冲突处理、中文元数据编辑 |
| **审计日志** | 配置变更记录、敏感操作历史 |

#### 2. 多用户/协作功能

| 功能 | 说明 |
|------|------|
| **线程可见性模型** | Private by default, explicit workspace sharing |
| **个人空间隔离** | 用户只能看到自己的私人线程 |
| **共享空间协作** | 同一工作区成员可共享线程 |
| **权限控制** | artifact 访问规则、thread ownership |

#### 3. 技能系统增强

| 功能 | 说明 |
|------|------|
| **远程安装** | 从 URL 下载 .skill 归档 |
| **冲突处理** | cancel / replace / rename 策略 |
| **中文本地化** | display_name_zh, description_zh |
| **安全扫描** | Skill 内容安全验证 |

#### 4. 安全修复

| 功能 | 说明 |
|------|------|
| **密码强制** | BY_ADMIN_PASSWORD 必须设置，禁用弱密码 |
| **上传限制** | 10MB 文件大小限制 |
| **Rate Limiting** | Nginx 层 API 限流 (100r/s API, 10r/s auth) |
| **Request ID** | 请求追踪中间件 |

---

### 快速开始

#### 环境要求

- Docker & Docker Compose
- Python 3.12+ (容器内已包含)
- Node.js 22+ (前端开发时需要)

#### 1. 克隆仓库

```bash
git clone https://github.com/hackeshackes/deerfllow-BY.git
cd deerfllow-BY
```

#### 2. 配置环境变量

```bash
# 复制配置模板
cp config.example.yaml config.yaml

# 必须设置管理员密码 (至少8字符)
export BY_ADMIN_PASSWORD="YourSecurePassword123!"
```

#### 3. 启动服务

```bash
# 开发模式 (推荐)
docker-compose -f docker/docker-compose-dev.yaml up --build

# 生产模式
docker-compose -f docker/docker-compose.yaml up --build
```

#### 4. 访问服务

| 服务 | 地址 |
|------|------|
| **前端** | http://localhost:2026 |
| **API 文档** | http://localhost:2026/docs |
| **Admin 控制台** | 登录后访问 /workspace/admin |

---

### 部署配置

#### 环境变量

| 变量 | 必需 | 说明 | 默认值 |
|------|------|------|--------|
| `BY_ADMIN_PASSWORD` | **是** | 管理员密码 (至少8字符) | - |
| `BY_ADMIN_EMAIL` | 否 | 管理员邮箱 | sabar.bao@me.com |
| `BY_ADMIN_NAME` | 否 | 管理员名称 | BY Owner |
| `DEER_FLOW_MAX_UPLOAD_SIZE_MB` | 否 | 上传文件大小限制 | 10 |
| `DEER_FLOW_CHECKPOINT_STORE` | 否 | Checkpoint 存储类型 | sqlite |
| `BY_ADMIN_PASSWORD_STRICT_MODE` | 否 | 禁用密码强度检查 | true |

#### Nginx Rate Limiting

默认配置：
- API 端点: 100 requests/second
- Auth 端点: 10 requests/second
- Upload 端点: 20 requests/minute

#### Checkpoint 持久化

支持三种模式：
- `memory` - 默认，进程重启后丢失
- `sqlite` - 文件持久化 (推荐开发)
- `postgres` - PostgreSQL 持久化 (生产推荐)

```yaml
# config.yaml
checkpointer:
  type: sqlite
  connection_string: checkpoints.db
```

---

### 架构

```
┌─────────────────────────────────────────────────────┐
│                   Nginx (Port 2026)                  │
│            统一反向代理，统一入口                      │
└──────────────┬──────────────────────┬───────────────┘
               │                      │
  /api/langgraph/*        /api/* (其他)
               ▼                      ▼
┌──────────────────────┐  ┌───────────────────────────┐
│   LangGraph Server   │  │      Gateway API (8001)    │
│      (Port 2024)      │  │        FastAPI REST        │
│                      │  │                           │
│  ┌────────────────┐  │  │  模型/MCP/Skills/Memory   │
│  │   Lead Agent   │  │  │  上传/工件/监控/审计      │
│  │ ┌────────────┐ │  │  │                           │
│  │ │Middleware 9链│ │  │  Admin 控制台 API          │
│  │ ├────────────┤ │  │  │                           │
│  │ │  Tools    │ │  │  └───────────────────────────┘
│  │ ├────────────┤ │  │
│  │ │ Subagents │ │  │  ┌───────────────────────────┐
│  │ └────────────┘ │  │  │     Frontend (Next.js)    │
│  └────────────────┘  │  │  /chats /admin /settings │
└──────────────────────┘  └───────────────────────────┘
```

---

### 技能系统

MicX 支持扩展技能系统：

```bash
# 内置技能 (21个)
- academic-paper-review  (学术论文评审)
- bootstrap              (伙伴初始化)
- chart-visualization    (图表可视化)
- data-analysis          (数据分析)
- deep-research          (深度研究)
- github-deep-research   (GitHub 深度研究)
- image-generation       (图像生成)
- ... 更多

# 安装远程技能
POST /api/skills/remote-install
{
  "url": "https://example.com/my-skill.skill",
  "conflict_strategy": "replace"
}

# 技能管理
GET /api/skills                    # 列出所有技能
POST /api/skills/{name}/enable    # 启用技能
POST /api/skills/{name}/disable   # 禁用技能
PUT /api/skills/{name}/metadata   # 更新中文元数据
```

---

### 开发

```bash
# 前端开发
cd frontend
pnpm install
pnpm dev          # 开发服务器
pnpm build        # 生产构建
pnpm lint         # 代码检查

# 后端开发
cd backend
uv sync           # 安装依赖
make lint         # 代码检查
make test         # 运行测试
```

---

### 文档

- [PRD 文档](./docs/plans/2026-04-13-micx-vnext-prd.md)
- [执行计划](./docs/plans/2026-04-13-micx-vnext-execution.md)
- [修复计划](./docs/plans/2026-04-15-micx-fix-plan.md)

---

## English Section

## MicX Version Overview

### MicX vs DeerFlow Comparison

| Category | DeerFlow Original | MicX Version |
|----------|------------------|--------------|
| **Agent Orchestration** | ✅ | ✅ |
| **Sandbox Execution** | ✅ | ✅ |
| **Tool System** | ✅ | ✅ |
| **MCP Integration** | ✅ | ✅ |
| **Admin Console** | ❌ | ✅ **New** |
| **Monitoring Center** | ❌ | ✅ **New** |
| **Configuration Center** | ❌ | ✅ **New** |
| **User/Workspace Management** | ❌ | ✅ **New** |
| **Remote Skill Installation** | ❌ | ✅ **New** |
| **Thread Visibility** | ❌ | ✅ **New** |
| **Chinese Localization** | Partial | ✅ **Complete** |
| **Brand Customization** | DeerFlow | ✅ **MicX** |
| **Security Hardening** | Basic | ✅ **Production** |
| **Checkpoint Persistence** | Memory | ✅ **SQLite** |

---

### MicX New Features

#### 1. Admin Management Console

| Feature | Description |
|---------|-------------|
| **Monitoring Center** | Health status, metrics overview, tracing config, recent issues |
| **Configuration Center** | System config, Tracing config (LangSmith/Langfuse), Brand config |
| **Model Management** | Model CRUD, API Key management, override config |
| **User Management** | User CRUD, invitation, disable, role management |
| **Workspace Management** | Create/rename/delete workspaces, member management |
| **Skill Management** | Remote install, conflict handling, Chinese metadata editing |
| **Audit Logs** | Config change records, sensitive action history |

#### 2. Multi-user/Collaboration

| Feature | Description |
|---------|-------------|
| **Thread Visibility Model** | Private by default, explicit workspace sharing |
| **Personal Space Isolation** | Users only see their own private threads |
| **Shared Space Collaboration** | Workspace members can share threads |
| **Access Control** | Artifact access rules, thread ownership |

#### 3. Enhanced Skills System

| Feature | Description |
|---------|-------------|
| **Remote Installation** | Download .skill archives from URL |
| **Conflict Handling** | cancel / replace / rename strategies |
| **Chinese Localization** | display_name_zh, description_zh |
| **Security Scanning** | Skill content security validation |

#### 4. Security Fixes

| Feature | Description |
|---------|-------------|
| **Password Enforcement** | BY_ADMIN_PASSWORD required, weak passwords forbidden |
| **Upload Limit** | 10MB file size limit |
| **Rate Limiting** | Nginx layer API rate limit (100r/s API, 10r/s auth) |
| **Request ID** | Request tracing middleware |

---

### Quick Start

#### Requirements

- Docker & Docker Compose
- Python 3.12+ (included in container)
- Node.js 22+ (for frontend development)

#### 1. Clone Repository

```bash
git clone https://github.com/hackeshackes/deerfllow-BY.git
cd deerfllow-BY
```

#### 2. Configure Environment

```bash
# Copy config template
cp config.example.yaml config.yaml

# Set admin password (at least 8 characters)
export BY_ADMIN_PASSWORD="YourSecurePassword123!"
```

#### 3. Start Services

```bash
# Development mode (recommended)
docker-compose -f docker/docker-compose-dev.yaml up --build

# Production mode
docker-compose -f docker/docker-compose.yaml up --build
```

#### 4. Access Services

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:2026 |
| **API Docs** | http://localhost:2026/docs |
| **Admin Console** | After login, visit /workspace/admin |

---

### Deployment Configuration

#### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `BY_ADMIN_PASSWORD` | **Yes** | Admin password (min 8 chars) | - |
| `BY_ADMIN_EMAIL` | No | Admin email | sabar.bao@me.com |
| `BY_ADMIN_NAME` | No | Admin name | BY Owner |
| `DEER_FLOW_MAX_UPLOAD_SIZE_MB` | No | Upload size limit | 10 |
| `DEER_FLOW_CHECKPOINT_STORE` | No | Checkpoint store type | sqlite |
| `BY_ADMIN_PASSWORD_STRICT_MODE` | No | Disable password check | true |

#### Nginx Rate Limiting

Default config:
- API endpoints: 100 requests/second
- Auth endpoints: 10 requests/second
- Upload endpoints: 20 requests/minute

#### Checkpoint Persistence

Three modes supported:
- `memory` - Default, lost on restart
- `sqlite` - File persistence (dev recommended)
- `postgres` - PostgreSQL persistence (prod recommended)

```yaml
# config.yaml
checkpointer:
  type: sqlite
  connection_string: checkpoints.db
```

---

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Nginx (Port 2026)                  │
│              Unified reverse proxy, single entry      │
└──────────────┬──────────────────────┬───────────────┘
               │                      │
  /api/langgraph/*        /api/* (others)
               ▼                      ▼
┌──────────────────────┐  ┌───────────────────────────┐
│   LangGraph Server   │  │      Gateway API (8001)    │
│      (Port 2024)      │  │        FastAPI REST        │
│                      │  │                           │
│  ┌────────────────┐  │  │  Models/MCP/Skills/Memory│
│  │   Lead Agent   │  │  │  Uploads/Artifacts/Monitor│
│  │ ┌────────────┐ │  │  │                           │
│  │ │Middleware 9链│ │  │  Admin Console APIs        │
│  │ ├────────────┤ │  │  │                           │
│  │ │  Tools    │ │  │  └───────────────────────────┘
│  │ ├────────────┤ │  │
│  │ │ Subagents │ │  │  ┌───────────────────────────┐
│  │ └────────────┘ │  │  │     Frontend (Next.js)    │
│  └────────────────┘  │  │  /chats /admin /settings │
└──────────────────────┘  └───────────────────────────┘
```

---

### Skills System

MicX supports extensible skills:

```bash
# Built-in skills (21)
- academic-paper-review
- bootstrap
- chart-visualization
- data-analysis
- deep-research
- github-deep-research
- image-generation
- ... more

# Install remote skill
POST /api/skills/remote-install
{
  "url": "https://example.com/my-skill.skill",
  "conflict_strategy": "replace"
}

# Skill management
GET /api/skills                    # List all skills
POST /api/skills/{name}/enable    # Enable skill
POST /api/skills/{name}/disable   # Disable skill
PUT /api/skills/{name}/metadata   # Update metadata
```

---

### Development

```bash
# Frontend
cd frontend
pnpm install
pnpm dev          # Dev server
pnpm build        # Production build
pnpm lint         # Lint

# Backend
cd backend
uv sync           # Install dependencies
make lint         # Lint
make test         # Run tests
```

---

### Documentation

- [PRD Document](./docs/plans/2026-04-13-micx-vnext-prd.md)
- [Execution Plan](./docs/plans/2026-04-13-micx-vnext-execution.md)
- [Fix Plan](./docs/plans/2026-04-15-micx-fix-plan.md)

---

## License

Based on DeerFlow project, following original license.
