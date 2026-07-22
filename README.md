# MicX 智能服务工作台 | MicX Intelligent Workspace

[English](#english-section) | [中文](#中文-section)

---

<!-- 中文部分 -->
# 中文-section

## MicX 是什么？

MicX 是基于 [DeerFlow](https://github.com/HACKESHACKES/deerflow) 的增强版本，专注于多用户协作、定时任务、企业级安全和中文本地化。

> **注意**: 本项目已与原版 DeerFlow 有显著差异，请勿直接使用原版文档参考本项目。

## 🎉 v1.6.3 已发布 (2026-07-22)

### 本版本核心变更

v1.6.3 是一次 **patch 累计迭代**：自 v1.6.1-canvas-released 以来,drift recovery operator script + admin-secrets 闭环两次增量 + security pentest V01–V11 防御加固 + 周围基础设施。

- **🔐 Owner-only admin secrets vault (M1 + M2)** — `POST /api/admin/secrets/{upsert,rotate,status,audit-events}` 四个 owner-only 端点。Helper 层 (`upsert_secret` / `delete_secret` / `rotate_env_secret` / `rotate_vault_cipher` / `is_placeholder_value` / `mask_secret_value` / `KNOWN_SECRET_KEYS` / `KNOWN_VAULT_KEYS`) 通过 `tempfile.mkstemp + Path.replace` 原子写入。M2 增量加 POSIX `fcntl.flock` 跨进程 rotate 锁 + `SECRETS_VAULT_ROUTABLE` 白名单 + `audit.jsonl` 过滤表面 + 前端 `secrets-admin-page` 四 Tab UI + `admin-page-shell` KeyRoundIcon 入口。总计 81 用例 (M1 53 + M2 13 + 助手 + 审计)。

- **🛠️ Drift recovery helper** — `scripts/reset_owner_password.py` 修复 owner 密码哈希与 `BY_ADMIN_PASSWORD` 漂移场景(忘记密码、手工编辑、`users.json` 字段重命名失误)。从 `.env` 读 `BY_ADMIN_PASSWORD`,重写 salt + PBKDF2-SHA256 (120k 轮) 哈希匹配 `auth.py:_hash_password`,**只动 owner,其他 6 个用户原样不动**,原子写入。端到端已验证:重置 → `/api/session/login` → `/api/admin/secrets/*` 全 200。

- **🛡️ Security pentest (V01–V11)** — 7 个 path 一次性回归:fail-fast auth secret、owner-only admin 守卫、HTML/script payload 拒绝、upload 危险扩展 (含双重扩展名)、SCIM owner-only、email mask、opt-in invite token、secure cookies。95 用例跨 7 个测试文件 + 综合端到端回归。

- **🧠 Vendor-aware model catalog (2026 providers)** — Anthropic beta header / Google thought signature / DeepSeek `reasoning_content` / Qwen `thinking_budget`。与 admin secrets 协同:`models.override.yaml` 中 `secret://` 引用 rotate 后热生效。

- **🛡️ CI: secret scanning** — `.github/workflows/gitleaks.yaml` 在 PR + push 触发,pin `gitleaks/gitleaks-action@v3`,自定义 `config.toml` 防 v1.5.0 泄露密码 `MicxLocal123!` 类问题回归。

- **📦 Env template hardening** — `.env` / `docker/.env` template 加 `BETTER_AUTH_SECRET` + `MICX_ADMIN_SECRET_KEY` 占位,README 引导新部署者一次性补齐 secret,命中 V01 fail-fast 路径而非启动 dev default。

- **🐳 Provisioner profile** — `docker/docker-compose.yaml` 的 `provisioner` 标 `profiles: ["provisioner"]` (与 `compose-dev.yaml:27` 对齐),K8s 命令:`docker compose -f docker/docker-compose.yaml --profile provisioner up -d --build`。本地沙箱 (默认) 不构建也不启动。

### 如何升级

```bash
cd deerfllow-BY
git fetch origin
git checkout v1.6.3
docker compose -f docker/docker-compose.yaml down
docker compose -f docker/docker-compose.yaml up -d --build
```

或者用 dev override (秒级 bind-mount + uv sync 生效):

```bash
git checkout v1.6.3
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.dev.yaml up -d --build
```

> **注意:** v1.6.3 要求 `.env` 中**必须**设置 `MICX_ADMIN_SECRET_KEY` 或 `BETTER_AUTH_SECRET`(否则 gateway fail-fast 退出),新部署请先在模板里补齐。

详细变更见 [CHANGELOG.md](./CHANGELOG.md),本次发布说明见 [docs/releases/v1.6.3.md](./docs/releases/v1.6.3.md)。

---

## 🎉 v1.5.5 已发布 (2026-07-01)

### 本版本核心变更

v1.5.5 是一次**真实部署验证 + 用户体验还原 + 基础设施加固**的迭代:

- **🚀 全栈真实部署验证完成** — 端到端 7/7 smoke 通过 (`/health`、`/api/connectors`、`/api/connectors/dlq`、`/api/spaces`、`/api/spaces/current`、`DELETE /api/subscriptions/...`、`/api/connectors` 全部 200/204),Rate Limit 124 req/min 命中返回 429 + `Retry-After` header 经验证可恢复,前端 5 个核心 UI 路径(landing、sign-in、workspace 路由、Next.js 静态资源)全部正常。
- **🚪 New Chat 交互还原** — 移除 `SceneSelector` 选择页,点击 "New Chat" 直接进入 **Welcome + Composer**(与 v1.5.x 原始体验一致),删除 199 行 SceneSelector 组件 + tests + scene selector 页面。
- **🔌 v1.5.5+ nginx 路由补齐** — 新增 `/api/connectors`、`/api/spaces`、`/api/subscriptions` nginx location 块(原配置漏配),`/api/users/*` 改为带 trailing slash 覆盖 `users/search` 子路径。
- **🐳 Backend dev 镜像构建** — 新增 `docker-gateway:dev` 镜像 (基于 `backend/Dockerfile` 的 `dev` target) + `docker-compose.dev.yaml` override,bind-mount 主机 `backend/` 到容器,后续代码改动 `uv sync` 即可生效 (秒级),无需每次 5 分钟级镜像 rebuild。
- **🔧 缺失模块修复** — `backend/app/gateway/data/voice_config.py` 模块在 filter-repo 历史重写 + cherry-pick 中丢失,已恢复并强制追踪 (该模块被 `voice.py` 路由 import,gateway 不修复无法启动)。
- **🔐 PR-#6 收尾** — 14/14 fix-legacy-issues 任务全部完成并推送至 [PR #6](https://github.com/hackeshackes/deerfllow-BY/pull/6),包含 v1.5.0 泄露密码 `MicxLocal123!` 从 git history 的 `filter-repo` 清除。

完整 7/7 后端 smoke 测试 ✅、前端 `pnpm check` (eslint + tsc + vitest) 通过 ✅、Rate Limit 实测命中恢复 ✅。

### 如何升级

```bash
cd deerfllow-BY
git fetch origin
git checkout v1.5.5
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.dev.yaml up -d
```

或者用传统 runtime stage:

```bash
docker compose -f docker/docker-compose.yaml down gateway
docker compose -f docker/docker-compose.yaml up -d --build gateway
```

> **Kubernetes / provisioner 模式用户注意**：`docker/docker-compose.yaml` 中 `provisioner` 服务声明了 `profiles: ["provisioner"]`，本地沙箱用户（默认）不会构建或启动 provisioner 容器。脚本层的 service 白名单（`scripts/deploy.sh` / `scripts/docker.sh`）会在 `sandbox.provisioner_url` 配置存在时自动加入 `provisioner`；也可直接通过 `--profile provisioner` 启用（注意 `--profile` 须置于 subcommand 之前）：
>
> ```bash
> docker compose -f docker/docker-compose.yaml --profile provisioner up -d --build
> ```

详细变更见 [CHANGELOG.md](./CHANGELOG.md)。

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
| **空间化工作台** | ❌ | ✅ **v1.4.4 新增** |
| **自动化入口** | ❌ | ✅ **v1.4.4 新增** |
| **工作流卡片** | ❌ | ✅ **v1.4.4 新增** |
| **AI消息引用来源** | ❌ | ✅ **v1.4.6 新增** |
| **Admin记忆查看** | ❌ | ✅ **v1.4.6 新增** |
| **记忆增强管理** | ❌ | ✅ **v1.4.6 新增** |
| **PPT Master 服务** | ❌ | ✅ **v1.4.7 新增** |
| **深度研究技能增强** | ❌ | ✅ **v1.4.7 新增** |
| **Bug 修复版本** | ❌ | ✅ **v1.4.8 新增** |
| **登录 Session 修复** | ❌ | ✅ **v1.4.9.1 新增** |
| **MCP 预设 + OAuth + IM 测试** | ❌ | ✅ **v1.4.9.2 新增** |
| **模型预设增强 (10家 40+模型)** | ❌ | ✅ **v1.4.9.2 新增** |
| **GLM/Minimax 模型扩展 (21家 60+模型)** | ❌ | ✅ **v1.4.9.3 新增** |
| **语音转文字 (STT) + Admin 模型配置** | ❌ | ✅ **v1.5.0 新增** |
| **知识库搜索增强 (RAG)** | ❌ | ✅ **v1.5.1 新增** |
| **Artifacts .skill 档案支持** | ❌ | ✅ **v1.5.1 新增** |
| **Docker 配置优化** | ❌ | ✅ **v1.5.1 优化** |
| **模型加载稳定性修复** | ❌ | ✅ **v1.5.1 修复** |
| **Admin 页面全量 i18n 本地化** | ❌ | ✅ **v1.5.2 新增** |
| **中英文切换完整支持** | ❌ | ✅ **v1.5.2 新增** |
| **凭据泄露修复 + Git 历史清理** | ❌ | ✅ **v1.5.3 安全** |
| **后端异步化(memory/sandbox/community)** | ❌ | ✅ **v1.5.3 性能** |
| **Per-IP Rate Limit 中间件** | ❌ | ✅ **v1.5.3 新增** |
| **前端 Vitest 测试框架** | ❌ | ✅ **v1.5.3 新增** |
| **`memory-settings-page` 拆分重构** | ❌ | ✅ **v1.5.3 重构** |
| **改密码 UI 在 SettingsDialog 内** | ❌ | ✅ **v1.5.3 修复** |
| **New Chat 直接进入 Welcome + Composer (撤销 SceneSelector)** | ❌ | ✅ **v1.5.5 还原** |
| **v1.5.5+ nginx 路由补齐 (connectors/spaces/subscriptions)** | ❌ | ✅ **v1.5.5 修复** |
| **Backend dev 镜像 + bind-mount (uv sync 秒级生效)** | ❌ | ✅ **v1.5.5 基础设施** |
| **voice_config.py 模块丢失修复** | ❌ | ✅ **v1.5.5 修复** |
| **真实部署端到端 smoke 测试 7/7 通过** | ❌ | ✅ **v1.5.5 验证** |
| **Owner-only admin secrets vault (Fernet 加密 vault + 4 端点)** | ❌ | ✅ **v1.6.3 新增** |
| **Cross-process rotate 锁 + audit.jsonl 表面 + 密钥白名单** | ❌ | ✅ **v1.6.3 新增** |
| **Vendor-aware model catalog (Anthropic/Google/DeepSeek/Qwen 专属字段)** | ❌ | ✅ **v1.6.3 新增** |
| **Drift recovery helper (`scripts/reset_owner_password.py`)** | ❌ | ✅ **v1.6.3 工具** |
| **Security pentest V01–V11 (fail-fast secret + owner 守卫 + XSS/扩展名/cookie)** | ❌ | ✅ **v1.6.3 加固** |
| **CI secret scanning (gitleaks-action v3, pin)** | ❌ | ✅ **v1.6.3 CI** |
| **Env template (`BETTER_AUTH_SECRET` + `MICX_ADMIN_SECRET_KEY` placeholders)** | ❌ | ✅ **v1.6.3 部署** |
| **改密码 UI 在 SettingsDialog 内** | ❌ | ✅ **v1.5.3 修复** |
| **凭据泄露修复 + Git 历史清理** | ❌ | ✅ **v1.5.3 安全** |
| **后端异步化 (memory/sandbox/community)** | ❌ | ✅ **v1.5.3 性能** |
| **Per-IP Rate Limit 中间件** | ❌ | ✅ **v1.5.3 新增** |
| **前端 Vitest 测试框架** | ❌ | ✅ **v1.5.3 新增** |
| **`memory-settings-page` 拆分重构** | ❌ | ✅ **v1.5.3 重构** |
| **改密码 UI 在 SettingsDialog 内** | ❌ | ✅ **v1.5.3 修复** |
| **New Chat 直接进入 Welcome + Composer (撤销 SceneSelector)** | ❌ | ✅ **v1.5.5 还原** |
| **v1.5.5+ nginx 路由补齐 (connectors/spaces/subscriptions)** | ❌ | ✅ **v1.5.5 修复** |
| **Backend dev 镜像 + bind-mount (uv sync 秒级生效)** | ❌ | ✅ **v1.5.5 基础设施** |
| **voice_config.py 模块丢失修复** | ❌ | ✅ **v1.5.5 修复** |
| **真实部署端到端 smoke 测试 7/7 通过** | ❌ | ✅ **v1.5.5 验证** |

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
| **配置中心** | `/workspace/admin/config` | 系统配置、Tracing 配置、**登录页/首页品牌文字定制** |
| **模型管理** | `/workspace/admin/models` | 模型配置 CRUD、API Key 管理 |
| **用户管理** | `/workspace/admin/users` | 用户 CRUD、邀请、禁用、角色 |
| **工作区管理** | `/workspace/admin/workspaces` | 创建/重命名/删除、成员管理 |
| **技能管理** | `/workspace/admin/models/skills` | 远程安装、冲突处理、中文元数据 |
| **MCP 配置** | `/workspace/admin/models/mcp` | MCP 服务器管理 |
| **IM 渠道** | `/workspace/admin/models/mcp/channels` | 飞书/Slack/Telegram/钉钉/企微配置 |
| **审计日志** | `/workspace/admin/audit` | 配置变更、敏感操作历史 |

**品牌配置** - 管理员可在配置中心自定义所有品牌文字：

| 页面 | 可配置内容 |
|------|-----------|
| **登录页** | Badge 文字、标题、副标题、2个功能卡片标题/描述 |
| **首页** | 3个能力卡片、4个使用场景、"为什么选择"区块、团队版区块 |

支持 `{name}` 和 `{support_email}` 占位符。

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

### 6. 飞书平台工具 (Feishu Tools)

MicX 实现了完整的飞书平台 API 工具集，共 **57 个工具**，覆盖云文档、多维表格、日历、任务、邮件等模块：

#### 云文档 (Docx) - 5 个
| 工具 | 说明 |
|------|------|
| `feishu_doc_read` | 读取文档内容 |
| `feishu_doc_search` | 搜索文档 |
| `feishu_doc_meta` | 获取文档元数据 |
| `feishu_doc_create` | 创建新文档 |
| `feishu_doc_write` | 写入文档内容（追加块） |

#### 多维表格 (Bitable) - 7 个
| 工具 | 说明 |
|------|------|
| `feishu_bitable_read` | 读取多维表格数据 |
| `feishu_bitable_write` | 批量写入多维表格 |
| `feishu_bitable_record_create` | 创建单条记录 |
| `feishu_bitable_record_update` | 更新单条记录 |
| `feishu_bitable_record_delete` | 删除单条记录 |
| `feishu_bitable_table_list` | 列出所有表格 |
| `feishu_bitable_field_list` | 列出所有字段 |

#### 日历 (Calendar) - 7 个
| 工具 | 说明 |
|------|------|
| `feishu_calendar_list` | 列出日历 |
| `feishu_calendar_event_list` | 列出日历事件 |
| `feishu_calendar_event_create` | 创建日历事件 |
| `feishu_calendar_event_get` | 获取事件详情 |
| `feishu_calendar_event_update` | 更新日历事件 |
| `feishu_calendar_event_delete` | 删除日历事件 |
| `feishu_calendar_freebusy` | 查询忙闲状态 |

#### 任务 (Task) - 6 个
| 工具 | 说明 |
|------|------|
| `feishu_task_list` | 列出任务 |
| `feishu_task_add` | 添加新任务 |
| `feishu_task_get` | 获取任务详情 |
| `feishu_task_update` | 更新任务 |
| `feishu_task_complete` | 完成任务 |
| `feishu_task_delete` | 删除任务 |

#### 邮件 (Mail) - 4 个
| 工具 | 说明 |
|------|------|
| `feishu_mail_list` | 列出邮件 |
| `feishu_mail_get` | 获取邮件内容 |
| `feishu_mail_send` | 发送邮件 |
| `feishu_mail_create_draft` | 创建邮件草稿 |

#### 电子表格 (Sheets) - 4 个
| 工具 | 说明 |
|------|------|
| `feishu_sheet_read` | 读取表格数据 |
| `feishu_sheet_write` | 写入表格数据 |
| `feishu_sheet_range` | 读取指定范围 |
| `feishu_sheet_create` | 在文件夹中创建表格 |

#### 云盘 (Drive) - 8 个
| 工具 | 说明 |
|------|------|
| `feishu_drive_file_list` | 列出文件 |
| `feishu_drive_file_meta` | 获取文件元数据 |
| `feishu_drive_file_download` | 下载文件 |
| `feishu_drive_file_delete` | 删除文件 |
| `feishu_drive_file_move` | 移动文件 |
| `feishu_drive_file_copy` | 复制文件 |
| `feishu_drive_create_folder` | 创建文件夹 |
| `feishu_drive_file_upload` | 上传文件 |

#### 消息增强 (IM) - 3 个
| 工具 | 说明 |
|------|------|
| `feishu_send_message` | 发送消息 |
| `feishu_download_file` | 下载消息附件 |
| `feishu_message_get` | 获取消息内容 |

#### 通讯录 (Contact) - 2 个
| 工具 | 说明 |
|------|------|
| `feishu_contact_user` | 查询用户信息 |
| `feishu_contact_dept` | 查询部门信息 |

#### 审批 (Approval) - 3 个
| 工具 | 说明 |
|------|------|
| `feishu_approval_list` | 列出审批实例 |
| `feishu_approval_get` | 获取审批详情 |
| `feishu_approval_action` | 操作审批（通过/拒绝） |

#### 妙记 (Minutes) - 2 个
| 工具 | 说明 |
|------|------|
| `feishu_minutes_get` | 获取妙记摘要 |
| `feishu_minutes_content` | 获取妙记全文内容 |

#### OKR - 3 个
| 工具 | 说明 |
|------|------|
| `feishu_okr_period_list` | 列出 OKR 周期 |
| `feishu_okr_get` | 获取 OKR 详情 |
| `feishu_okr_progress` | 获取 OKR 进度 |

#### 考勤 (Attendance) - 2 个
| 工具 | 说明 |
|------|------|
| `feishu_attendance_record` | 查询考勤记录 |
| `feishu_attendance_group` | 查询考勤组 |

#### 消息 (Messages) - 1 个
| 工具 | 说明 |
|------|------|
| `feishu_get_messages` | 获取会话消息列表 |

### 7. Checkpoint 持久化

DeerFlow 原版使用内存存储，重启后对话历史丢失。MicX 支持持久化：

- `memory` - 默认，进程重启后丢失
- `sqlite` - 文件持久化 (开发推荐)
- `postgres` - PostgreSQL 持久化 (生产推荐)

### 8. 文件上传修复

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

### 9. 知识库 (Knowledge Base)

MicX 实现了完整的 RAG 知识库系统：

| 功能 | 说明 |
|------|------|
| **文档上传** | 支持多种文档格式，自动转换为可检索内容 |
| **向量存储** | 基于嵌入模型的语义检索 |
| **知识检索** | Agent 上下文自动注入相关知识 |
| **网页抓取** | Jina AI 驱动的网页内容提取 |
| **CRUD 管理** | 完整的知识库管理 API |

**API 端点:**
```bash
GET    /api/knowledge                    # 列出所有知识库
POST   /api/knowledge                   # 创建知识库（支持 visibility 字段）
GET    /api/knowledge/{id}              # 获取知识库详情
PUT    /api/knowledge/{id}              # 更新知识库
DELETE /api/knowledge/{id}              # 删除知识库
POST   /api/knowledge/{id}/documents   # 上传文档
GET    /api/knowledge/{id}/search       # 搜索知识
```

**可见性选项:**
- `private` - 私有，仅创建者可见
- `workspace` - 工作区共享，工作区成员可见
- `global` - 全局（仅管理员可创建）

**Admin 管理:** `/workspace/admin/knowledge`
- 查看所有用户的知识库
- 编辑知识库（名称、描述、可见性）
- 支持修改为私有/工作区共享/全局

### 10. 监控中心

MicX 提供了完整的系统监控能力：

| 功能 | 说明 |
|------|------|
| **健康状态** | 各服务组件运行状态一目了然 |
| **指标概览** | 请求量、响应时间、错误率等核心指标 |
| **追踪配置** | LangSmith / Langfuse 集成配置 |
| **最近问题** | 自动记录和展示系统异常 |

**Admin 管理:** `/workspace/admin/monitoring`

### 11. 审计日志

记录所有敏感操作，支持合规和问题排查：

| 功能 | 说明 |
|------|------|
| **配置变更** | 所有配置修改的完整历史 |
| **敏感操作** | 用户管理、权限变更等敏感操作记录 |
| **时间线视图** | 按时间排序的操作记录 |

**Admin 管理:** `/workspace/admin/audit`

### 12. 空间化用户工作台 (v1.4.4)

MicX 在 v1.4.4 重新设计了用户工作台，实现以"空间"为核心的导航体系：

| 功能 | 说明 |
|------|------|
| **空间切换器** | 顶部一级空间切换，支持个人空间与共享工作区快速切换 |
| **侧边栏导航重组** | 新建对话 / 对话 / 资料库 / 自动化 / 工作流 / Agents 六大入口 |
| **Recent Chat 分区** | 对话列表按来源分区显示：最近继续 / 自动化结果 / 外部渠道 |
| **状态 Badge 横向排列** | 已共享 / 私有 / 自动化 / 团队状态与标题同行显示，不堆叠 |
| **自动化入口** | 新增 `/workspace/automations` 列表页和 `/workspace/automations/new` 创建页 |
| **工作流卡片页** | 新增 `/workspace/workflows` 页面展示可用工作流技能 |
| **资料库三范围 Tab** | 当前空间资料 / 我的私人资料 / 全局资料，分层管理 |
| **对话 URL 预填** | `?prompt=` 参数可预填新建对话输入框 |
| **nginx upstream 动态解析** | 修复开发环境 gateway 重建后 502 问题 |
| **provisioner 可选** | 沙箱提供器改为 Docker profile，kubeconfig 不再阻塞普通开发 |

### 13. 工作流系统 (Workflows)

用户可通过工作流技能执行特定任务流程：

| 功能 | 说明 |
|------|------|
| **工作流列表页** | `/workspace/workflows` 展示所有可用的工作流技能 |
| **快速启动** | 点击工作流卡片自动跳转新建对话并预填对应 prompt |
| **工作流分类** | 自动聚合常用工作流，支持快速访问 |
| **远程安装** | 管理员可从远程 URL 安装新工作流技能 |

**工作流技能 API:**
```bash
GET    /api/user/skills              # 获取用户可用技能列表
POST   /api/skills/{name}/enable     # 启用技能
POST   /api/skills/{name}/disable    # 禁用技能
GET    /api/skills                   # 列出所有内置技能
```

### 14. 自动化系统 (Automations)

自动化功能帮助用户将重复性工作变为周期性 AI 自动执行：

| 功能 | 说明 |
|------|------|
| **自动化列表** | `/workspace/automations` 查看所有自动化任务及状态 |
| **创建自动化** | `/workspace/automations/new` 配置触发频率、输出位置等 |
| **状态显示** | Badge 横向排列，运行中/已完成/已暂停一目了然 |
| **自动化结果** | 自动生成对话记录，标记来源为"自动化" |
| **定时触发** | 支持 Cron 表达式和 Interval 间隔两种触发方式 |

**自动化 API:**
```bash
GET    /api/tasks                    # 列出所有自动化任务
POST   /api/tasks                     # 创建自动化任务
GET    /api/tasks/{id}                # 获取任务详情
PUT    /api/tasks/{id}                # 更新任务配置
DELETE /api/tasks/{id}                # 删除任务
POST   /api/tasks/{id}/run            # 立即执行一次
POST   /api/tasks/{id}/pause          # 暂停任务
POST   /api/tasks/{id}/resume         # 恢复任务
GET    /api/tasks/{id}/executions     # 获取执行历史
```

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

- [v1.4.9 PRD](./docs/plans/2026-05-12-micx-v1.4.9-prd.md) - v1.4.9 知识库搜索增强
- [v1.4.9 执行计划](./docs/plans/2026-05-12-micx-v1.4.9-execution-plan.md) - v1.4.9 执行计划
- [v1.4.9.1 PRD](./docs/plans/2026-05-16-micx-v1.5-prd.md) - 登录 Session 修复
- [v1.4.9.1 执行计划](./docs/plans/2026-05-16-micx-v1.5-execution-plan.md) - v1.4.9.1 执行计划
- [v1.4.8 PRD](./docs/plans/2026-05-12-micx-v1.4.8-prd.md) - Bug 修复版本
- [v1.4.8 执行计划](./docs/plans/2026-05-12-micx-v1.4.8-execution-plan.md) - Bug 修复执行计划
- [v1.4.7 PRD](./docs/plans/2026-05-07-micx-v1.4.7-prd.md) - PPT Master 服务
- [v1.4.7 执行计划](./docs/plans/2026-05-07-micx-v1.4.7-execution-plan.md) - PPT Master 执行计划
- [v1.4.6 PRD](./docs/plans/2026-05-06-micx-v1.4.6-prd.md) - 可信知识与记忆
- [v1.4.6 执行计划](./docs/plans/2026-05-06-micx-v1.4.6-execution-plan.md)
- [v1.4.4 PRD](./docs/plans/2026-04-26-micx-v1.4.4-prd-final.md)
- [v1.4.4 执行计划](./docs/plans/2026-04-26-micx-v1.4.4-execution-plan.md)
- [v1.4 PRD](./docs/plans/2026-04-19-micx-v1.4-prd.md)
- [v1.4 执行计划](./docs/plans/2026-04-19-micx-v1.4-execution.md)
- [v1.4 Bugfix 计划](./docs/plans/2026-04-19-micx-v1.4-bugfix-plan.md)
- [v1.3 PRD](./docs/plans/2026-04-17-micx-v1.3-prd.md)
- [v1.3 执行计划](./docs/plans/2026-04-17-micx-v1.3-execution.md)
- [v1.2 计划](./docs/plans/2026-04-16-micx-v1.2-plan.md)
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

> **Note**: This project has diverged significantly from upstream DeerFlow. Do not reference upstream DeerFlow documentation when using MicX.

## 🎉 v1.5.3 Released (2026-06-10)

### Core Changes in This Release

v1.5.3 is a **security + performance + quality** triplet:

- **🔐 Security fix** — Hardcoded `BY_ADMIN_PASSWORD` / `BETTER_AUTH_SECRET` leaked in v1.5.0 e2e scripts are now environment-driven; real secrets are rotated; git history rewritten with `filter-repo` and pushed to a separate branch `force-v1.5.3-clean` (main's original history preserved).
- **⚡ Backend async refactor** — `memory/updater.py` `model.invoke` → `await model.ainvoke`, `local_sandbox.py` `subprocess.run` → `asyncio.create_subprocess_shell`, 3 community tools migrated from `requests` to `httpx.AsyncClient`. No more event-loop blocking.
- **🛡️ Per-IP rate limit** — New `RateLimitMiddleware` (sliding window, 120 req/min default), returns 429 + `Retry-After` on overflow.
- **🧪 Frontend test infrastructure** — Vitest 2 + happy-dom, 47 new unit tests, `pnpm check` now runs `vitest run`.
- **🧹 Code cleanup** — `memory-settings-page.tsx` decomposed from 1006 lines into 11 sub-components / hooks (225-line parent file).

Full 16/16 pages ✅, core Chat E2E ✅, zero console errors.

### How to Upgrade

```bash
cd deerfllow-BY
git fetch origin
git checkout force-v1.5.3-clean   # NOTE: not main! History-rewritten branch
# or: git checkout v1.5.3
docker compose -f docker/docker-compose.yaml down
docker compose -f docker/docker-compose.yaml build
docker compose -f docker/docker-compose.yaml up -d
```

See [CHANGELOG.md](./CHANGELOG.md) for full changes.

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
| **Workspace-Centric UI** | ❌ | ✅ **v1.4.4 New** |
| **Automation Portal** | ❌ | ✅ **v1.4.4 New** |
| **Workflow Cards** | ❌ | ✅ **v1.4.4 New** |
| **AI Message Citations** | ❌ | ✅ **v1.4.6 New** |
| **Admin Memory View** | ❌ | ✅ **v1.4.6 New** |
| **Enhanced Memory Management** | ❌ | ✅ **v1.4.6 New** |
| **PPT Master Service** | ❌ | ✅ **v1.4.7 New** |
| **Deep-Research Skill Enhancement** | ❌ | ✅ **v1.4.7 New** |
| **Bug Fix Release** | ❌ | ✅ **v1.4.8 New** |
| **Admin Pages Full i18n Localization** | ❌ | ✅ **v1.5.2 New** |
| **Complete Chinese/English Language Switch** | ❌ | ✅ **v1.5.2 New** |
| **Credential Leak Fix + Git History Rewrite** | ❌ | ✅ **v1.5.3 Security** |
| **Backend Async Refactor (memory/sandbox/community)** | ❌ | ✅ **v1.5.3 Performance** |
| **Per-IP Rate Limit Middleware** | ❌ | ✅ **v1.5.3 New** |
| **Frontend Vitest Test Framework** | ❌ | ✅ **v1.5.3 New** |
| **`memory-settings-page` Decomposition Refactor** | ❌ | ✅ **v1.5.3 Refactor** |
| **Change-Password UI Inside SettingsDialog** | ❌ | ✅ **v1.5.3 Fix** |

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
| **Configuration Center** | `/workspace/admin/config` | System, tracing, **login page & homepage brand text** |
| **Model Management** | `/workspace/admin/models` | Model CRUD, API Key management |
| **User Management** | `/workspace/admin/users` | User CRUD, invitation, roles |
| **Workspace Management** | `/workspace/admin/workspaces` | Create/rename/delete, members |
| **Skill Management** | `/workspace/admin/models/skills` | Remote install, Chinese metadata |
| **MCP Configuration** | `/workspace/admin/models/mcp` | MCP server management |
| **IM Channels** | `/workspace/admin/models/mcp/channels` | Feishu/Slack/Telegram/DingTalk/WeCom |
| **Audit Logs** | `/workspace/admin/audit` | Config changes, sensitive actions |

**Brand Customization** - Admin can configure all brand text from the Configuration Center:

| Page | Configurable Content |
|------|---------------------|
| **Login Page** | Badge text, title, subtitle, 2 feature card titles/descriptions |
| **Homepage** | 3 capability cards, 4 use-case items, "Why choose" block, team edition block |

Supports `{name}` and `{support_email}` placeholders.

### 4. IM Channels

| Channel | Config Fields | Description |
|---------|---------------|-------------|
| **Feishu** | app_id, app_secret | ByteDance Feishu |
| **Slack** | bot_token, app_token | Socket Mode supported |
| **Telegram** | bot_token | Bot API integration |
| **WeCom** | bot_id, bot_secret | Tencent WeCom |
| **DingTalk** | client_id, client_secret | Alibaba DingTalk |

### 5. Feishu Platform Tools

MicX implements a comprehensive Feishu platform API toolset with **57 tools** covering Docs, Bitable, Calendar, Tasks, Mail, and more:

#### Docx - 5 tools
| Tool | Description |
|------|-------------|
| `feishu_doc_read` | Read document content |
| `feishu_doc_search` | Search documents |
| `feishu_doc_meta` | Get document metadata |
| `feishu_doc_create` | Create new document |
| `feishu_doc_write` | Write content to document (append blocks) |

#### Bitable - 7 tools
| Tool | Description |
|------|-------------|
| `feishu_bitable_read` | Read bitable data |
| `feishu_bitable_write` | Batch write to bitable |
| `feishu_bitable_record_create` | Create single record |
| `feishu_bitable_record_update` | Update single record |
| `feishu_bitable_record_delete` | Delete single record |
| `feishu_bitable_table_list` | List all tables |
| `feishu_bitable_field_list` | List all fields |

#### Calendar - 7 tools
| Tool | Description |
|------|-------------|
| `feishu_calendar_list` | List calendars |
| `feishu_calendar_event_list` | List calendar events |
| `feishu_calendar_event_create` | Create calendar event |
| `feishu_calendar_event_get` | Get event details |
| `feishu_calendar_event_update` | Update calendar event |
| `feishu_calendar_event_delete` | Delete calendar event |
| `feishu_calendar_freebusy` | Query free/busy status |

#### Task - 6 tools
| Tool | Description |
|------|-------------|
| `feishu_task_list` | List tasks |
| `feishu_task_add` | Add new task |
| `feishu_task_get` | Get task details |
| `feishu_task_update` | Update task |
| `feishu_task_complete` | Complete task |
| `feishu_task_delete` | Delete task |

#### Mail - 4 tools
| Tool | Description |
|------|-------------|
| `feishu_mail_list` | List emails |
| `feishu_mail_get` | Get email content |
| `feishu_mail_send` | Send email |
| `feishu_mail_create_draft` | Create email draft |

#### Sheets - 4 tools
| Tool | Description |
|------|-------------|
| `feishu_sheet_read` | Read sheet data |
| `feishu_sheet_write` | Write sheet data |
| `feishu_sheet_range` | Read specific range |
| `feishu_sheet_create` | Create spreadsheet in folder |

#### Drive - 8 tools
| Tool | Description |
|------|-------------|
| `feishu_drive_file_list` | List files |
| `feishu_drive_file_meta` | Get file metadata |
| `feishu_drive_file_download` | Download file |
| `feishu_drive_file_delete` | Delete file |
| `feishu_drive_file_move` | Move file |
| `feishu_drive_file_copy` | Copy file |
| `feishu_drive_create_folder` | Create folder |
| `feishu_drive_file_upload` | Upload file |

#### IM - 3 tools
| Tool | Description |
|------|-------------|
| `feishu_send_message` | Send message |
| `feishu_download_file` | Download message attachment |
| `feishu_message_get` | Get message content |

#### Contact - 2 tools
| Tool | Description |
|------|-------------|
| `feishu_contact_user` | Query user info |
| `feishu_contact_dept` | Query department info |

#### Approval - 3 tools
| Tool | Description |
|------|-------------|
| `feishu_approval_list` | List approval instances |
| `feishu_approval_get` | Get approval details |
| `feishu_approval_action` | Approve/reject approval |

#### Minutes - 2 tools
| Tool | Description |
|------|-------------|
| `feishu_minutes_get` | Get minutes summary |
| `feishu_minutes_content` | Get minutes full content |

#### OKR - 3 tools
| Tool | Description |
|------|-------------|
| `feishu_okr_period_list` | List OKR periods |
| `feishu_okr_get` | Get OKR details |
| `feishu_okr_progress` | Get OKR progress |

#### Attendance - 2 tools
| Tool | Description |
|------|-------------|
| `feishu_attendance_record` | Query attendance records |
| `feishu_attendance_group` | Query attendance groups |

#### Messages - 1 tool
| Tool | Description |
|------|-------------|
| `feishu_get_messages` | Get conversation message list |

### 6. File Upload Fixes

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

### 7. Knowledge Base (RAG)

MicX implements a complete RAG-based knowledge management system:

| Feature | Description |
|---------|-------------|
| **Document Upload** | Multiple formats, auto-converted to searchable content |
| **Vector Storage** | Embedding-based semantic retrieval |
| **Knowledge Retrieval** | Auto-injected relevant knowledge in agent context |
| **Web Scraping** | Jina AI-powered web content extraction |
| **CRUD API** | Complete knowledge base management |

**API Endpoints:**
```bash
GET    /api/knowledge                    # List all knowledge bases
POST   /api/knowledge                   # Create knowledge base (supports visibility field)
GET    /api/knowledge/{id}              # Get knowledge base details
PUT    /api/knowledge/{id}              # Update knowledge base
DELETE /api/knowledge/{id}              # Delete knowledge base
POST   /api/knowledge/{id}/documents   # Upload documents
GET    /api/knowledge/{id}/search       # Search knowledge
```

**Visibility Options:**
- `private` - Private, only creator can access
- `workspace` - Workspace shared, visible to workspace members
- `global` - Global (admin only)

**Admin:** `/workspace/admin/knowledge`
- View all users' knowledge bases
- Edit knowledge bases (name, description, visibility)
- Can change visibility to private/workspace/global

### 8. Monitoring Center

MicX provides comprehensive system monitoring:

| Feature | Description |
|---------|-------------|
| **Health Status** | Clear view of all service component statuses |
| **Metrics Overview** | Request volume, response time, error rate KPIs |
| **Tracing Config** | LangSmith / Langfuse integration |
| **Recent Issues** | Auto-logged system anomalies |

**Admin:** `/workspace/admin/monitoring`

### 9. Audit Logs

Complete audit trail for compliance and troubleshooting:

| Feature | Description |
|---------|-------------|
| **Config Changes** | Full history of all configuration modifications |
| **Sensitive Operations** | User management, permission changes |
| **Timeline View** | Chronologically sorted operation records |

**Admin:** `/workspace/admin/audit`

### 10. Workspace-Centric UI (v1.4.4)

MicX v1.4.4 redesigns the user workspace around "spaces" for better navigation:

| Feature | Description |
|---------|-------------|
| **Workspace Switcher** | Top-level space switcher, fast toggle between personal and shared workspaces |
| **Sidebar Navigation** | Reorganized: New Chat / Chats / Sources / Automations / Workflows / Agents |
| **Recent Chat Sections** | Chat list grouped by source: Recent / Automation Results / External Channels |
| **Horizontal Status Badges** | Shared/Private/Automation/Team status inline with title, no vertical stacking |
| **Automation Portal** | New `/workspace/automations` list and `/workspace/automations/new` create page |
| **Workflow Cards** | New `/workspace/workflows` page showcasing available workflow skills |
| **Knowledge Triple Tabs** | Current Space / My Private / Global knowledge bases, layered access |
| **URL Prompt Prefill** | `?prompt=` parameter pre-fills the new chat input box |
| **nginx Dynamic Upstream** | Fixes 502 after gateway rebuild in dev environments |
| **Provisioner Optional** | Sandbox provisioner moved to Docker profile, kubeconfig no longer blocks dev |

### 11. Workflows

Users execute specific task flows through workflow skills:

| Feature | Description |
|---------|-------------|
| **Workflow List** | `/workspace/workflows` displays all available workflow skills |
| **Quick Launch** | Click a workflow card → new chat with pre-filled prompt |
| **Remote Install** | Admins install new workflow skills from remote URLs |

### 12. Automations

Automations convert repetitive work into scheduled AI executions:

| Feature | Description |
|---------|-------------|
| **Automation List** | `/workspace/automations` view all automation tasks and status |
| **Create Automation** | `/workspace/automations/new` configure trigger frequency, output location |
| **Horizontal Status** | Badges displayed inline, running/completed/paused at a glance |
| **Automation Results** | Auto-generated chat records tagged with "automation" source |
| **Scheduled Triggers** | Supports both Cron expressions and Interval triggers |

**Automation API:**
```bash
GET    /api/tasks                    # List all automation tasks
POST   /api/tasks                     # Create automation task
GET    /api/tasks/{id}                # Get task details
PUT    /api/tasks/{id}                # Update task config
DELETE /api/tasks/{id}                # Delete task
POST   /api/tasks/{id}/run            # Run once immediately
POST   /api/tasks/{id}/pause          # Pause task
POST   /api/tasks/{id}/resume         # Resume task
GET    /api/tasks/{id}/executions     # Get execution history
```

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

- [v1.4.9 PRD](./docs/plans/2026-05-12-micx-v1.4.9-prd.md) - Knowledge Base Search Enhancement
- [v1.4.9 Execution Plan](./docs/plans/2026-05-12-micx-v1.4.9-execution-plan.md) - v1.4.9 Execution Plan
- [v1.4.8 PRD](./docs/plans/2026-05-12-micx-v1.4.8-prd.md) - Bug Fix Release
- [v1.4.8 Execution Plan](./docs/plans/2026-05-12-micx-v1.4.8-execution-plan.md) - Bug Fix Execution
- [v1.4.7 PRD](./docs/plans/2026-05-07-micx-v1.4.7-prd.md) - PPT Master Service
- [v1.4.7 Execution Plan](./docs/plans/2026-05-07-micx-v1.4.7-execution-plan.md) - PPT Master Execution
- [v1.4.6 PRD](./docs/plans/2026-05-06-micx-v1.4.6-prd.md) - Trusted Knowledge & Memory
- [v1.4.6 Execution](./docs/plans/2026-05-06-micx-v1.4.6-execution-plan.md)
- [v1.4.4 PRD](./docs/plans/2026-04-26-micx-v1.4.4-prd-final.md)
- [v1.4.4 Execution](./docs/plans/2026-04-26-micx-v1.4.4-execution-plan.md)
- [v1.4 Execution](./docs/plans/2026-04-19-micx-v1.4-execution.md)
- [v1.4 Bugfix Plan](./docs/plans/2026-04-19-micx-v1.4-bugfix-plan.md)
- [v1.3 PRD](./docs/plans/2026-04-17-micx-v1.3-prd.md)
- [v1.3 Execution](./docs/plans/2026-04-17-micx-v1.3-execution.md)
- [v1.2 Plan](./docs/plans/2026-04-16-micx-v1.2-plan.md)
- [PRD Document](./docs/plans/2026-04-13-micx-vnext-prd.md)
- [Execution Plan](./docs/plans/2026-04-13-micx-vnext-execution.md)
- [Fix Plan](./docs/plans/2026-04-15-micx-fix-plan.md)
- [CHANGELOG](./CHANGELOG.md) - Version history

---

## License

Based on DeerFlow project, following original license.
