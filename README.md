# MicX 智能服务工作台 | MicX Intelligent Workspace

[English](#english-section) | [中文](#中文-section)

---

<!-- 中文部分 -->
# 中文-section

## MicX 是什么？

MicX 是基于 [DeerFlow](https://github.com/HACKESHACKES/deerflow) 的增强版本，专注于多用户协作、定时任务、企业级安全和中文本地化。

> **注意**: 本项目已与原版 DeerFlow 有显著差异，请勿直接使用原版文档参考本项目。

---

## 版本对比：MicX vs DeerFlow 原版

| 类别 | DeerFlow 原版 | MicX 版本 |
|------|--------------|-----------|
| **Agent 编排** | ✅ | ✅ |
| **沙箱执行** | ✅ | ✅ |
| **工具系统** | ✅ | ✅ |
| **MCP 集成** | ✅ | ✅ |
| **定时任务** | ❌ | ✅ **新增** |
| **知识库 RAG** | ❌ | ✅ **新增** |
| **IM 渠道集成** | ❌ | ✅ **新增** |
| **钉钉支持** | ❌ | ✅ **新增** |
| **Admin 管理控制台** | ❌ | ✅ **新增** |
| **监控中心** | ❌ | ✅ **新增** |
| **配置中心** | ❌ | ✅ **新增** |
| **用户/工作区管理** | ❌ | ✅ **新增** |
| **技能远程安装** | ❌ | ✅ **新增** |
| **线程可见性** | ❌ | ✅ **新增** |
| **中文本地化** | 部分 | ✅ **完整** |
| **品牌定制** | DeerFlow | ✅ **MicX** |
| **安全加固** | 基础 | ✅ **生产级** |
| **Checkpoint 持久化** | Memory | ✅ **SQLite/PostgreSQL** |

---

## MicX 核心差异说明

### 1. 定时任务系统

DeerFlow 原版没有定时任务功能。MicX 实现了一套完整的定时任务系统：

- **支持 Cron 表达式和 Interval 间隔触发**
- **APScheduler 调度引擎**，服务重启后自动恢复任务
- **任务执行后自动生成对话标题**（根据 prompt 模板前 50 字符）
- **完整的执行历史记录**，可查看每次 AI 响应内容
- **暂停/恢复控制**，随时开关任务

**API 端点:**
```bash
GET    /api/tasks                    # 列出所有任务
POST   /api/tasks                   # 创建任务
GET    /api/tasks/{id}              # 获取任务详情
PUT    /api/tasks/{id}              # 更新任务
DELETE /api/tasks/{id}              # 删除任务
POST   /api/tasks/{id}/run          # 立即运行
POST   /api/tasks/{id}/pause       # 暂停任务
POST   /api/tasks/{id}/resume       # 恢复任务
GET    /api/tasks/{id}/executions   # 获取执行历史
```

**Cron 表达式示例:**
```
0 9 * * *       # 每天上午 9:00 执行
0 9 * * 1       # 每周一上午 9:00 执行
30 14 * * *     # 每天下午 2:30 执行
*/15 * * * *    # 每 15 分钟执行
```

### 2. 多用户协作体系

DeerFlow 原版是单用户设计。MicX 实现了完整的多用户体系：

| 功能 | 说明 |
|------|------|
| **用户邀请制** | 管理员邀请新用户，账号激活后才能使用 |
| **工作区隔离** | 个人空间 + 共享工作区，数据完全隔离 |
| **线程可见性** | Private (仅创建者可见) / Workspace (工作区成员可见) |
| **权限控制** | artifact 访问规则、thread ownership |
| **角色管理** | admin / member 两种角色 |

### 3. Admin 管理控制台

MicX 提供了完整的 Admin 控制台：

| 功能 | 路径 | 说明 |
|------|------|------|
| **监控中心** | `/workspace/admin/monitoring` | 健康状态、指标概览、追踪配置、最近问题 |
| **配置中心** | `/workspace/admin/config` | 系统配置、Tracing 配置、品牌定制 |
| **模型管理** | `/workspace/admin/models` | 模型配置 CRUD、API Key 管理 |
| **用户管理** | `/workspace/admin/users` | 用户 CRUD、邀请、禁用、角色 |
| **工作区管理** | `/workspace/admin/workspaces` | 创建/重命名/删除、成员管理 |
| **技能管理** | `/workspace/admin/models/skills` | 远程安装、冲突处理、中文元数据 |
| **MCP 配置** | `/workspace/admin/models/mcp` | MCP 服务器管理 |
| **IM 渠道** | `/workspace/admin/models/mcp/channels` | 飞书/Slack/Telegram/钉钉/企微配置 |
| **审计日志** | `/workspace/admin/audit` | 配置变更、敏感操作历史 |

### 4. 安全加固

| 功能 | 说明 |
|------|------|
| **密码强制** | BY_ADMIN_PASSWORD 必须设置，禁用弱密码 |
| **上传限制** | 10MB 文件大小限制 |
| **Rate Limiting** | Nginx 层 API 限流 (100r/s API, 10r/s auth) |
| **Request ID** | 请求追踪中间件 |
| **会话安全** | HTTP-only Cookie，14 天过期 |

### 5. IM 渠道集成

支持多种即时通讯渠道：

| 渠道 | 配置字段 | 说明 |
|------|----------|------|
| **飞书** | app_id, app_secret | 字节跳动飞书平台 |
| **Slack** | bot_token, app_token | Socket Mode 支持 |
| **Telegram** | bot_token | Bot API 集成 |
| **企业微信** | bot_id, bot_secret | 腾讯企业微信 |
| **钉钉** | client_id, client_secret | 阿里巴巴钉钉平台 |

### 6. Checkpoint 持久化

DeerFlow 原版使用内存存储，重启后对话历史丢失。MicX 支持持久化：

- `memory` - 默认，进程重启后丢失
- `sqlite` - 文件持久化 (开发推荐)
- `postgres` - PostgreSQL 持久化 (生产推荐)

### 7. 文件上传修复

MicX 修复了 DeerFlow 原版文件上传的多个问题：

| 问题 | 原因 | 修复 |
|------|------|------|
| 新对话无法上传文件 | 线程未创建 | 自动创建缺失线程 |
| 上传后 AI 找不到文件 | 路径解析不一致 | 扩展路径搜索范围 |
| 文件保存在错误位置 | 上下文丢失 | 搜索所有 workspaces/users 目录 |

**路径解析逻辑:**
1. 当前 workspace 路径
2. 所有 workspaces 目录
3. 所有 users 目录
4. 用户特定 legacy 路径
5. 全局 legacy 路径

---

## 快速开始

### 环境要求

- Docker & Docker Compose v2
- Python 3.12+ (容器内已包含)
- Node.js 22+ (前端开发时需要)

### 1. 克隆仓库

```bash
git clone https://github.com/hackeshackes/deerfllow-BY.git
cd deerfllow-BY
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp config.example.yaml config.yaml

# 必须设置管理员密码 (至少8字符)
export BY_ADMIN_PASSWORD="YourSecurePassword123!"
```

### 3. 启动服务

```bash
# 开发模式 (推荐) - 代码修改后自动重载
docker-compose -f docker/docker-compose-dev.yaml up --build

# 生产模式
docker-compose -f docker/docker-compose.yaml up --build
```

### 4. 访问服务

| 服务 | 地址 |
|------|------|
| **前端** | http://localhost:2026 |
| **API 文档** | http://localhost:2026/docs |
| **Admin 控制台** | 登录后访问 /workspace/admin |

### 5. 创建管理员账号

首次启动后，访问 http://localhost:2026/sign-up 使用邀请码注册第一个账号。

---

## 部署配置

### 环境变量

| 变量 | 必需 | 说明 | 默认值 |
|------|------|------|--------|
| `BY_ADMIN_PASSWORD` | **是** | 管理员密码 (至少8字符) | - |
| `BY_ADMIN_EMAIL` | 否 | 管理员邮箱 | sabar.bao@me.com |
| `BY_ADMIN_NAME` | 否 | 管理员名称 | MicX Admin |
| `DEER_FLOW_MAX_UPLOAD_SIZE_MB` | 否 | 上传文件大小限制 | 10 |
| `DEER_FLOW_CHECKPOINT_STORE` | 否 | Checkpoint 存储类型 | sqlite |
| `BY_ADMIN_PASSWORD_STRICT_MODE` | 否 | 禁用密码强度检查 | true |

### Nginx Rate Limiting

默认配置：
- API 端点: 100 requests/second
- Auth 端点: 10 requests/second
- Upload 端点: 20 requests/minute

### Checkpoint 持久化配置

```yaml
# config.yaml
checkpointer:
  type: sqlite
  connection_string: checkpoints.db
```

---

## 架构

```
┌─────────────────────────────────────────────────────┐
│                   Nginx (Port 2026)                  │
│            统一反向代理，统一入口                      │
└──────────────┬──────────────────────┬───────────────┘
               │                      │
   /api/langgraph/*       /api/* (其他)
               ▼                      ▼
┌──────────────────────┐  ┌───────────────────────────┐
│   LangGraph Server   │  │      Gateway API (8001)    │
│      (Port 2024)      │  │        FastAPI REST        │
│                      │  │                           │
│  ┌────────────────┐  │  │  模型/MCP/Skills/Memory   │
│  │   Lead Agent   │  │  │  上传/工件/监控/审计      │
│  │ ┌────────────┐ │  │  │                           │
│  │ │Middleware 9链│ │  │  Admin 控制台 API          │
│  │ ├────────────┤ │  │  定时任务调度器             │
│  │ │  Tools    │ │  │  IM 渠道管理器              │
│  │ ├────────────┤ │  │                           │
│  │ │ Subagents │ │  │  ┌───────────────────────────┐
│  │ └────────────┘ │  │  │     Frontend (Next.js)    │
│  └────────────────┘  │  │  /chats /admin /settings │
└──────────────────────┘  └───────────────────────────┘
```

---

## 技能系统

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

## 开发

```bash
# 前端开发
cd frontend
pnpm install
pnpm dev          # 开发服务器 (热重载)
pnpm build        # 生产构建
pnpm lint         # 代码检查
pnpm typecheck    # 类型检查

# 后端开发
cd backend
uv sync           # 安装依赖
make lint         # 代码检查
make test         # 运行测试

# 同时开发前后端
cd ..
make dev          # 启动所有服务 (开发模式)
```

---

## 文档

- [PRD 文档](./docs/plans/2026-04-13-micx-vnext-prd.md)
- [执行计划](./docs/plans/2026-04-13-micx-vnext-execution.md)
- [修复计划](./docs/plans/2026-04-15-micx-fix-plan.md)
- [CHANGELOG](./CHANGELOG.md) - 版本历史

---

## License

基于 DeerFlow 项目，遵循原项目许可证。

---

<a name="english-section"></a>

# English Section

## What is MicX?

MicX is an enhanced version of [DeerFlow](https://github.com/HACKESHACKES/deerflow), focused on multi-user collaboration, scheduled tasks, enterprise security, and Chinese localization.

---

## MicX vs DeerFlow Comparison

| Category | DeerFlow Original | MicX Version |
|----------|------------------|--------------|
| **Agent Orchestration** | ✅ | ✅ |
| **Sandbox Execution** | ✅ | ✅ |
| **Tool System** | ✅ | ✅ |
| **MCP Integration** | ✅ | ✅ |
| **Scheduled Tasks** | ❌ | ✅ **New** |
| **Knowledge Base RAG** | ❌ | ✅ **New** |
| **IM Channels** | ❌ | ✅ **New** |
| **DingTalk Support** | ❌ | ✅ **New** |
| **Admin Console** | ❌ | ✅ **New** |
| **Monitoring Center** | ❌ | ✅ **New** |
| **Configuration Center** | ❌ | ✅ **New** |
| **User/Workspace Management** | ❌ | ✅ **New** |
| **Remote Skill Installation** | ❌ | ✅ **New** |
| **Thread Visibility** | ❌ | ✅ **New** |
| **Chinese Localization** | Partial | ✅ **Complete** |
| **Brand Customization** | DeerFlow | ✅ **MicX** |
| **Security Hardening** | Basic | ✅ **Production** |
| **Checkpoint Persistence** | Memory | ✅ **SQLite/PostgreSQL** |

---

## Key Differences from DeerFlow

### 1. Scheduled Tasks System

DeerFlow has no scheduled tasks. MicX implements a complete scheduled task system:

- **Cron expressions and Interval triggers**
- **APScheduler engine** - tasks survive service restarts
- **Auto-generated conversation titles** (first 50 chars of prompt template)
- **Complete execution history** - view full AI responses
- **Pause/Resume control**

### 2. Multi-user Collaboration

DeerFlow is single-user. MicX implements a complete multi-user system:

| Feature | Description |
|---------|-------------|
| **Invitation System** | Admin invites new users, account activation required |
| **Workspace Isolation** | Personal space + shared workspaces |
| **Thread Visibility** | Private (creator only) / Workspace (members可见) |
| **Role Management** | admin / member |

### 3. Admin Management Console

| Feature | Path | Description |
|---------|------|-------------|
| **Monitoring Center** | `/workspace/admin/monitoring` | Health, metrics, tracing config |
| **Configuration Center** | `/workspace/admin/config` | System, tracing, brand config |
| **Model Management** | `/workspace/admin/models` | Model CRUD, API Key management |
| **User Management** | `/workspace/admin/users` | User CRUD, invitation, roles |
| **Workspace Management** | `/workspace/admin/workspaces` | Create/rename/delete, members |
| **Skill Management** | `/workspace/admin/models/skills` | Remote install, Chinese metadata |
| **MCP Configuration** | `/workspace/admin/models/mcp` | MCP server management |
| **IM Channels** | `/workspace/admin/models/mcp/channels` | Feishu/Slack/Telegram/DingTalk/WeCom |
| **Audit Logs** | `/workspace/admin/audit` | Config changes, sensitive actions |

### 4. IM Channels

| Channel | Config Fields | Description |
|---------|---------------|-------------|
| **Feishu** | app_id, app_secret | ByteDance Feishu |
| **Slack** | bot_token, app_token | Socket Mode supported |
| **Telegram** | bot_token | Bot API integration |
| **WeCom** | bot_id, bot_secret | Tencent WeCom |
| **DingTalk** | client_id, client_secret | Alibaba DingTalk |

### 5. File Upload Fixes

MicX fixes several file upload issues from DeerFlow:

| Issue | Cause | Fix |
|-------|-------|-----|
| Cannot upload in new conversations | Thread not created | Auto-create missing threads |
| AI cannot find uploaded files | Path resolution mismatch | Extended path search |
| Files saved to wrong location | Context lost | Search all workspaces/users dirs |

**Path Resolution Order:**
1. Current workspace path
2. All workspaces directories
3. All users directories
4. User-specific legacy path
5. Global legacy path

---

## Quick Start

### Requirements

- Docker & Docker Compose v2
- Python 3.12+ (included in container)
- Node.js 22+ (for frontend development)

### 1. Clone Repository

```bash
git clone https://github.com/hackeshackes/deerfllow-BY.git
cd deerfllow-BY
```

### 2. Configure Environment

```bash
# Copy config template
cp config.example.yaml config.yaml

# Set admin password (at least 8 characters)
export BY_ADMIN_PASSWORD="YourSecurePassword123!"
```

### 3. Start Services

```bash
# Development mode (recommended) - hot reload enabled
docker-compose -f docker/docker-compose-dev.yaml up --build

# Production mode
docker-compose -f docker/docker-compose.yaml up --build
```

### 4. Access Services

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:2026 |
| **API Docs** | http://localhost:2026/docs |
| **Admin Console** | After login, visit /workspace/admin |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Nginx (Port 2026)                  │
│              Unified reverse proxy, single entry      │
└──────────────┬──────────────────────┬───────────────┘
               │                      │
   /api/langgraph/*       /api/* (others)
               ▼                      ▼
┌──────────────────────┐  ┌───────────────────────────┐
│   LangGraph Server   │  │      Gateway API (8001)    │
│      (Port 2024)      │  │        FastAPI REST        │
│                      │  │                           │
│  ┌────────────────┐  │  │  Models/MCP/Skills/Memory│
│  │   Lead Agent   │  │  │  Uploads/Artifacts/Monitor│
│  │ ┌────────────┐ │  │  │  Scheduled Tasks          │
│  │ │Middleware 9链│ │  │  │  IM Channel Manager      │
│  │ ├────────────┤ │  │  │                           │
│  │ │  Tools    │ │  │  │  ┌───────────────────────────┐
│  │ ├────────────┤ │  │  │  │     Frontend (Next.js)    │
│  │ │ Subagents │ │  │  │  │  /chats /admin /settings │
│  │ └────────────┘ │  │  │  └───────────────────────────┘
│  └────────────────┘  │  └───────────────────────────┘
└──────────────────────┘
```

---

## Development

```bash
# Frontend
cd frontend
pnpm install
pnpm dev          # Dev server (hot reload)
pnpm build        # Production build
pnpm lint         # Lint
pnpm typecheck    # Type check

# Backend
cd backend
uv sync           # Install dependencies
make lint         # Lint
make test         # Run tests

# Full stack dev
cd ..
make dev          # Start all services (dev mode)
```

---

## Documentation

- [PRD Document](./docs/plans/2026-04-13-micx-vnext-prd.md)
- [Execution Plan](./docs/plans/2026-04-13-micx-vnext-execution.md)
- [Fix Plan](./docs/plans/2026-04-15-micx-fix-plan.md)
- [CHANGELOG](./CHANGELOG.md) - Version history

---

## License

Based on DeerFlow project, following original license.
