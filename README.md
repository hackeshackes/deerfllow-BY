# MicX 版本说明

## 版本对比：MicX vs DeerFlow 原版

### 功能对比表

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

## MicX 新增功能详情

### 1. Admin 管理控制台

| 功能 | 说明 |
|------|------|
| **监控中心** | 健康状态、指标概览、追踪配置、最近问题面板 |
| **配置中心** | 系统配置、Tracing 配置 (LangSmith/Langfuse)、品牌配置 |
| **模型管理** | 模型配置 CRUD、API Key 管理、覆盖配置 |
| **用户管理** | 用户 CRUD、邀请、禁用、角色管理 |
| **工作区管理** | 创建/重命名/删除工作区、成员管理 |
| **技能管理** | 远程安装、冲突处理、中文元数据编辑 |
| **审计日志** | 配置变更记录、敏感操作历史 |

### 2. 多用户/协作功能

| 功能 | 说明 |
|------|------|
| **线程可见性模型** | Private by default, explicit workspace sharing |
| **个人空间隔离** | 用户只能看到自己的私人线程 |
| **共享空间协作** | 同一工作区成员可共享线程 |
| **权限控制** | artifact 访问规则、thread ownership |

### 3. 技能系统增强

| 功能 | 说明 |
|------|------|
| **远程安装** | 从 URL 下载 .skill 归档 |
| **冲突处理** | cancel / replace / rename 策略 |
| **中文本地化** | display_name_zh, description_zh |
| **技能元数据存储** | 持久化技能配置 |
| **安全扫描** | Skill 内容安全验证 |

### 4. 安全修复

| 功能 | 说明 |
|------|------|
| **密码强制** | BY_ADMIN_PASSWORD 必须设置，禁用弱密码 |
| **上传限制** | 10MB 文件大小限制 |
| **Rate Limiting** | Nginx 层 API 限流 (100r/s API, 10r/s auth) |
| **Request ID** | 请求追踪中间件 |

---

## 快速开始

### 环境要求

- Docker & Docker Compose
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

# 编辑 config.yaml 设置你的 API keys
# 必须设置管理员密码
export BY_ADMIN_PASSWORD="YourSecurePassword123!"
```

### 3. 启动服务

```bash
# 开发模式 (推荐)
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

---

## 部署配置

### 环境变量

| 变量 | 必需 | 说明 | 默认值 |
|------|------|------|--------|
| `BY_ADMIN_PASSWORD` | **是** | 管理员密码 (至少8字符) | - |
| `BY_ADMIN_EMAIL` | 否 | 管理员邮箱 | sabar.bao@me.com |
| `BY_ADMIN_NAME` | 否 | 管理员名称 | BY Owner |
| `DEER_FLOW_MAX_UPLOAD_SIZE_MB` | 否 | 上传文件大小限制 | 10 |
| `DEER_FLOW_CHECKPOINT_STORE` | 否 | Checkpoint 存储类型 | sqlite |
| `BY_ADMIN_PASSWORD_STRICT_MODE` | 否 | 禁用密码强度检查 | true |

### Nginx Rate Limiting

默认配置：
- API 端点: 100 requests/second
- Auth 端点: 10 requests/second
- Upload 端点: 20 requests/minute

### Checkpoint 持久化

支持三种模式：
- `memory` - 默认，进程重启后丢失
- `sqlite` - 文件持久化 (推荐开发)
- `postgres` -  PostgreSQL 持久化 (生产推荐)

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
│  └────────────────┘  │  │  /chats /admin /settings  │
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

### 前端开发

```bash
cd frontend
pnpm install
pnpm dev          # 开发服务器
pnpm build        # 生产构建
pnpm lint         # 代码检查
```

### 后端开发

```bash
cd backend
uv sync           # 安装依赖
make lint         # 代码检查
make test         # 运行测试
```

### 测试

```bash
# 完整测试
cd backend && uv run pytest tests/ -q

# 带覆盖率
cd backend && uv run pytest tests/ --cov=. --cov-report=term-missing
```

---

## 文档

- [PRD 文档](./docs/plans/2026-04-13-micx-vnext-prd.md)
- [执行计划](./docs/plans/2026-04-13-micx-vnext-execution.md)
- [修复计划](./docs/plans/2026-04-15-micx-fix-plan.md)

---

## License

基于 DeerFlow 项目，遵循原有 License。
