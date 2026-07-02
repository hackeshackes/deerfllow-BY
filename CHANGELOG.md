# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.5.10] - 2026-XX-XX

> **范围:** 把 v1.5.8/v1.5.9 留下的 P0 缺口"收口"。v1.6.0 大版本留作 5-7 周的画布 + 协作完整化。
> 详细实施计划:`docs/superpowers/plans/2026-07-02-micx-v1.5.10-multitenancy-closure.md`

### Added

#### 多租户收口(基于 v1.5.8 数据层 → 真实可用)
- `multitenancy/routers/api.py` — `/api/admin/cost/summary`、`/api/admin/quota/{tenant_id}`、`/api/admin/usage/{tenant_id}` 路由
- `app.py` 注册 `multitenancy_router` + 注入 singleton(`InMemoryUsageTracker` + `QuotaService`)
- 严格基于 v1.5.8 现有类(`InMemoryUsageTracker` / `aggregate_costs` / `ResourceQuota` / `QuotaService.check_and_record`),不引入新数据模型

#### 配额 enforce modes
- `ResourceQuota.enforce_mode` 字段(frozen dataclass,默认 `"advisory"`,在 `__post_init__` 校验)
- `QuotaService.check_only(tenant_id, tokens)` 新增方法 — 不写入 tracker,只判断
- 三模式:`advisory`(默认,只警告)/ `soft`(只警告)/ `hard`(超额阻断,`allowed=False`)
- 原 `check_and_record` 签名保留,v1.5.8 所有 caller 不破坏

#### 可观测性
- `observability/routers/metrics.py` — Prometheus `/metrics` 端点
- `observability/metrics.py` 暴露 `render_prometheus()` — 走现有 in-process `_counters` / `_gauges` 字典,无 prometheus-client 依赖
- LangfuseExporter 配置 surface 沿用 v1.5.8(`MICX_LANGFUSE_ENABLED=true` + `export_span`),**真实 SDK 推迟 v1.6.0**

#### 前端成本看板
- `/workspace/admin/governance/cost` — 月度 usage summary、模型分布、配额编辑器
- `core/multitenancy/api.ts` + `hooks/use-cost-summary.ts`

### Test
- 多租户 admin API:~6 个集成测试
- 配额 soft-enforce:5 个(advisory / soft / hard / disabled / check_only 不写入)
- Prometheus metrics:3 个(counter / gauge / endpoint)
- 成本看板前端:3 个
- **合计:** ~17 个新测试

### Out of scope (deferred to v1.6.0)
- Langfuse 真实 export SDK
- Workspace 级别 breakdown(UsageRecord 暂无 `workspace_id` 字段)
- Per-tenant 用户/模型维度的精确隔离(`aggregate_costs(group_by="user_id")` 当前返回全租户)
- 模型路由 admin API(`router_service.py` 已有,UI 一起做)

---

## [1.6.0] - 2026-XX-XX

> **范围:** 战略 spec §4.3 完整版 — 画布(后端 + 前端编辑)+ 跨部门发布 + Slack 连接器 + ABAC 简化版 + 资源隔离(workspace 实际接入 LangGraph runtime)。**v1.5.x 系列里唯一大版本**,带架构变化。
> 详细大纲计划:`docs/superpowers/plans/2026-07-02-micx-v1.6.0-canvas-completion.md`

### Added(规划)

#### 画布后端
- `canvas/models.py` — Workflow / WorkflowNode / WorkflowEdge(5 节点:AGENT/TOOL/PROMPT/BRANCH/LOOP)
- `canvas/store.py` — InMemoryWorkflowStore + SQLite 持久化(可选)
- `canvas/versions.py` — VersionManager(commit / list / rollback)
- `canvas/executor.py` — WorkflowExecutor(顺序拓扑 + branch/loop 路由)
- `canvas/nodes/{agent,tool,prompt,branch,loop}.py` — 5 类节点执行器
- `canvas/routers/workflows.py` — CRUD + execute + versions + rollback API

#### 画布前端
- `/workspace/workflows` — 列表 / 新建 / 详情 / 编辑 4 个页面
- `NodeInspector` + `NodePalette` + `EdgeConnector` + `WorkflowToolbar`
- React Flow 完整化(已在 v1.5.9 引入,本版本加属性面板 / 保存 / 运行 / 撤销重做)

#### 协作收尾
- `collaboration/publish.py` — PublishService(链式保留 original_thread_id)
- `core/collaboration/PublishButton.tsx` — Thread 详情页发布入口

#### 连接器
- `connectors/slack/` — Slack 连接器(chat.postMessage + Webhook)

#### ABAC 简化版(战略 spec P2)
- `abac/evaluator.py` + `policies.py` — Subject / Resource / Action / AttributePolicy
- 示例策略:部门匹配 + admin override
- 接入点:thread 访问 + workflow 执行前(补充 RBAC,不替换)

#### 资源隔离
- LangGraph agent 启动时检查 workspace_id
- workflow execution 强制要求 user 在 workspace 内
- 配额 soft-enforce 与 workflow 关联

### 验收
- 3 个部门试点,资源完全隔离
- 配额超限自动降级或阻断
- Langfuse trace 覆盖率 ≥ 95%
- 非工程师能独立配置 5 节点工作流
- 5+ 个连接器全部可用
- P95 响应延迟 < 2s(50+ 并发用户)

### Changed
- v1.5.8 中标注的"v1.6.0 拆解为三段"完成 — v1.5.8 收口 60% / v1.5.10 收口 P0 / v1.6.0 完成剩余 P1/P2

---

## [1.5.5] - 2026-07-01

### Reverted

- **前端 New Chat 体验还原** — 移除 `SceneSelector` 选择页,点击 "New Chat" 直接进入 Welcome + Composer。删除 `frontend/src/app/workspace/chats/components/SceneSelector.tsx`、`chats/new/page.tsx` 与对应 tests (199 行删除, 0 行新增)。`/workspace/chats/new` 现在被 `[thread_id]/page.tsx` 接管,`isNewThread=true` 立即渲染。

### Fixed

- **v1.5.5+ nginx 路由补齐** (`docker/nginx/nginx.conf`) — 新增 `/api/connectors`、`/api/spaces`、`/api/subscriptions` 三个 location 块,这些路由已在 `app.py` 注册但 nginx 中漏配,导致请求 fall through 到前端 404 HTML。
- **voice_config.py 模块丢失修复** (`backend/app/gateway/data/voice_config.py`) — 该模块被 `routers/voice.py` import,但在 `git filter-repo` 历史重写 + 后续 cherry-pick 中丢失。无法启动 gateway (ModuleNotFoundError)。强制追踪例外 bypass `.gitignore` 中的 `backend/app/gateway/data/` (该路径下通常是数据库文件)。

### Infrastructure

- **dev 镜像 + bind-mount override** (`docker-compose.dev.yaml`) — 新增 dev override,使用 `backend/Dockerfile` 的 `dev` target (保留 build-essential + uv toolchain) + bind mount `backend/` 到容器。后续代码改动 `docker compose restart gateway` 即生效 (uv sync 秒级)。无需每次 5 分钟级镜像 rebuild。
- **`docker-gateway:dev` 镜像构建** (5.11 GB) — 基于 dev target,生产用 `docker-gateway:latest`。

## [1.5.8] - 2026-XX-XX

### Added

#### 多租户 + 资源治理(原 v1.6.0 范围下放)
- `multitenancy/models.py` — Tenant / Workspace / Project / ResourceQuota 域模型(frozen dataclass)
- `multitenancy/quota.py` + `usage_tracker.py` — Token 配额 + RPM 限流(advisory 模式,默认 0 = 禁用)
- `multitenancy/router_service.py` + `cost_calculator.py` — 多模型路由(cost/quality/speed 三策略)
- `multitenancy/cost_dashboard.py` — 按 tenant/user/model 聚合

#### 可观测性补完
- `observability/tracing.py` — OTel 抽象,disabled-by-default no-op
- `observability/langfuse_exporter.py` — Langfuse export config surface
- `observability/metrics.py` — Counter / Gauge 线程安全原语

#### 新连接器
- `connectors/jira/` — Jira Cloud REST v3(create_issue / transition / comment,Basic auth)
- `connectors/linear/` — Linear GraphQL API(issueCreate / commentCreate mutations)

#### 共享对话评论(协作闭环最后一块)
- `comments/` — Thread comments + @mention 提取(lookbehind 排除邮箱)

#### 画布骨架
- `/workspace/canvas` — 5 节点画布(agent / tool / prompt / branch / loop)
- 节点 + 边渲染、调色板、增删;完整编辑 + LangGraph 执行留给 v1.5.9

### Changed
- v1.6.0(原 6-7 周大版本)拆解为 v1.5.8 + v1.5.9 + v1.6+ 三段
- 文档:`docs/superpowers/plans/2026-06-22-micx-v1.6.0-multitenant-canvas.md` 标记为 deferred

### Test
- 多租户模型:9 个
- Token 配额:6 个
- 模型路由:8 个
- 成本看板:6 个
- 可观测性:9 个
- Jira 连接器:9 个
- Linear 连接器:8 个
- 评论服务:13 个
- **后端合计**:68 个新测试通过
- 画布前端:8 个
- MentionInput async:6 个(usersApi 5 个)
- **前端合计**:+13 新测试

## [1.5.7] - 2026-XX-XX

### Fixed (from v1.5.5 gray)
- 飞书 / 钉钉 / 企微 4 个连接器 token 之前无限缓存(生产 2h 后会 401);现改用 `CachedToken` + 2h TTL,15min 提前刷新,401 后自动 invalidate 强制下次重取
- `CachedToken` 单飞(single-flight)保证:多个并发请求看到过期 token 时只触发 1 次网络取数,避免雪崩

### Added
- `connectors/persistence/sqlite_dlq.py` — DLQ 持久化(SQLite,跨重启);`flush_to_sqlite()` 把 in-memory 积压一次性写盘
- `connectors/token_refresh.py` — 可复用的 token 缓存原语,带 TTL + invalidate + 单飞
- lifespan 启动时从 `MICX_CONNECTORS` 环境变量(YAML body)自动注册内置连接器;空 env → 空注册表(dev 默认)

### Test
- `test_connectors_token_refresh.py` — 6 个:TTL 行为、并发序列化、单飞
- `test_connectors_persistence.py` — 7 个:DLQ push/list/delete/clear、跨实例持久化、flush round-trip
- `test_app_lifespan.py` — 3 个:env→registry 路径、空 env 行为、API regression guard

### Out of scope (deferred to v1.6+)
- Subscription store 持久化(InMemory 仍可用,等真实用户流量再加 Postgres)
- 401 触发自动 retry(v1.5.7 改 invalidate,下次调用会拿到新 token,等同隐式 retry 1 次)
- Async SQLite(aiosqlite);当前用 stdlib sqlite3 同步路径,生产前切换

## [1.5.5] - 2026-XX-XX

### Added

#### 业务系统连接器 (4 个内置)
- 抽出 `connectors/` 子系统,统一 `Connector` 协议(YAML 声明式配置)
- 连接器统一运行时:重试(默认 2 次) + 死信队列
- Webhook 双向桥(常量时间比较 secret)
- 飞书连接器:群消息发送 + URL 验证 + 文本事件解析(respx mock 测试)
- 钉钉连接器:群消息 + 机器人(accessToken 缓存)
- 企微连接器:群消息 + 应用消息(gettoken 缓存)
- 邮件连接器:SMTP 发件(aiosmtplib),IMAP 收件接口留 poller
- 内置连接器 YAML 注册(`integrations/builtin.py`)
- 连接器 admin API:`GET /api/connectors`、`/api/connectors/dlq`、`/api/connectors/{name}/webhook`

#### 空间化协作 (兑现 v1.4.4 路线图核心)
- 一级空间切换器 `WorkspaceSwitcher`(cookie 持久化 + `router.refresh()`)
- `useCurrentSpace` / `useSpaces` hooks 配合后端 `X-MicX-Space` header
- 对话按来源分区 `PartitionedChatList`(All / Manual / Automation / Channel)
- 新建对话场景化 `SceneSelector`(Free / Q&A / Document / Analyze / Automate)
- @提及自动补全 `MentionInput`
- Thread 数据模型扩展:`space_type` / `source` / `published_from_thread_id` 字段
- 订阅模型 + `@mention` 触发服务 + 通知 fan-out
- 订阅 API:`POST /api/subscriptions`、`DELETE /api/subscriptions/{kind}/{id}`、count 查询
- 空间 API:`GET /api/spaces`、`/api/spaces/current`、`/api/spaces/{id}`

#### SAML 2.0 支持 (补全 v1.5.4 推后的工作)
- `python3-saml` wrapper(SAMLConfig + SAMLProvider + SP metadata)
- 支持 ADFS / Shibboleth / 其他 SAML 2.0 IdP

### Changed
- 前端 workspace layout 注入 WorkspaceSwitcher
- 后端新增 `connectors/` / `spaces/` / `subscriptions/` / `threads/` 子系统
- 后端新增 `identity/auth/saml/` 模块

## [1.5.3] - 2026-06-10

### Security

#### 凭据泄露修复与历史清理
- `docker/e2e-test-micx.js` 及其他 6 个 e2e 测试脚本中硬编码的 `BY_ADMIN_PASSWORD` / `BETTER_AUTH_SECRET` 改为从 `E2E_EMAIL` / `E2E_PASSWORD` 环境变量读取
- `.env` 中真实 `BETTER_AUTH_SECRET` 和 `BY_ADMIN_PASSWORD` 已轮换为新随机值,同步更新 3 个 `.env` 文件(根、`docker/`、`frontend/`)
- `git filter-repo` 重写 v1.5.0 起的所有 commit,彻底从 git 历史中清除泄露的凭据
- 推送到远端新分支 `force-v1.5.3-clean`(独立分支,`main` 保留原历史不动)
- `.gitignore` 扩展,覆盖 `docker/node_modules/`、`docker/test-results/`、`docker/e2e-tests/`,共 untrack 423 个误追踪文件(~44M)
- `secrets.enc` vault 用新 `BETTER_AUTH_SECRET` 重新加密,所有 LLM API key 保留,owner 用户用 PBKDF2-HMAC-SHA256 120000 轮重新 hash

### Changed

#### 后端异步化 (Async refactor)
- `memory/updater.py` `model.invoke` → `await model.ainvoke`,相关函数改 `async def`;caller `queue.py` 用 `asyncio.run` 适配 threading.Timer
- `sandbox/local/local_sandbox.py` 同步 `subprocess.run` → `asyncio.create_subprocess_shell` / `create_subprocess_exec`,abstract `Sandbox.execute_command` 与 `bash_tool` 同步改 async,超 10 处相关调用点和测试同步更新
- `community/infoquest` / `community/aio_sandbox` 3 个文件:同步 `requests` → `httpx.AsyncClient`
- 整体上消除后端 event loop 阻塞,支持并发 LLM 调用与并发的沙箱命令

#### 构建基础设施
- `backend/Dockerfile` 新增 `HF_ENDPOINT` ARG,支持受限网络(中国/受限地区)从 `hf-mirror.com` 镜像下载 faster-whisper 模型
- `docker/docker-compose.yaml` gateway / langgraph 服务传递 `HF_ENDPOINT` 到 build args

### Added

#### 后端 rate limit 中间件
- 新增 `app/gateway/rate_limit.py`,基于 `BaseHTTPMiddleware` 的 per-IP 滑动窗口限流,默认 120 req/min
- 在 `app.py` 注册,超出限制返回 429 + `Retry-After` 头
- 使用 PEP 585 内置泛型(`dict[str, deque[float]]`),通过 ruff 静态检查

#### 前端测试基础设施
- 添加 Vitest 2.1.9 + happy-dom 测试框架
- `package.json` 新增 `test` / `test:watch` 脚本,`check` 脚本现在包含 `vitest run`
- 首批 6 个 `core/` 纯函数文件添加测试,共 47 个 vitest 测试全部通过(markdown / json / threads / messages / tools / i18n / knowledge)
- 修复 Vitest 配置与 vite 版本冲突(移除 `@vitejs/plugin-react`,项目 vite 7 与 vitest 2 内部 vite 5 类型冲突)

#### 前端代码组织
- `memory-settings-page.tsx` 从 1006 行拆分为 11 个子组件 / hook(225 行父文件),消除超大文件违规
  - 子组件:`FactsList`、`FactEditorDialog`、`FactDeleteDialog`、`MemoryImportDialog`、`MemoryClearDialog`、`MemoryToolbar`、`MemorySummaryView`、`MemoryFactsBlock`
  - Hook:`useMemoryActions`(state + handlers)
  - 共享:`memory/types.ts`、`memory/utils.ts`

### Fixed

#### 用户改密码入口可达性
- 抽取 `change-password-form.tsx` 独立组件,POST `/api/account/change-password` 表单(带 `type=submit` 按钮)
- `settings-dialog.tsx` 添加 `account` section(中英 i18n key `t.settings.sections.account`),用户可在 SettingsDialog 内改密码
- `nginx.conf` 新增 `location /api/account { proxy_pass http://$gateway_backend; }`,修复之前 404 导致改密 API 不可用
- `account-page.tsx` 重构复用 ChangePasswordForm,独立页面 `/workspace/account` 仍可用

#### 登录体验
- 登录按钮添加 `type="submit"`,鼠标点击可触发(之前只能按 Enter 提交)

#### 应用稳定性
- 修复 `n.filter is not a function` 崩溃:`/api/users/me` / `loadKnowledgeBases` 401 时不再把 `undefined` 塞进 state
- 加 3 个缺失路由:`/workspace/admin/dashboard`、`/workspace/admin/channels`、`/workspace/settings/memory`

### Deployment

- v1.5.3 完整部署到本地 docker(4 个核心服务:v1.5.3 baked-in 镜像)
- 16/16 页面 ✅,核心 Chat E2E ✅(真实 AI 回复),0 console 错误
- 凭据已通过 SettingsDialog UI 可改

## [1.5.2] - 2026-05-28

### Added

#### Admin 页面全量 i18n 本地化
- 所有 Admin 管理页面完全支持中英文切换
- 修复页面包括:
  - memory-admin-page.tsx (记忆管理)
  - models-admin-page.tsx (模型管理)
  - monitoring-admin-page.tsx (监控中心)
  - token-usage-admin-page.tsx (Token 统计)
  - users-admin-page.tsx (用户管理)
  - workspaces-admin-page.tsx (工作区管理)

#### 中英文切换完整支持
- Settings → Appearance → Language 可切换中文/英文
- 所有管理后台界面现已支持完整国际化

## [1.5.1] - 2026-05-26

### Added

#### 知识库搜索增强 (RAG)
- 知识库搜索功能持续开发中
- 为后续 RAG 增强打下基础

#### Artifacts .skill 档案支持
- 新增从 .skill 压缩包中提取内部文件的功能
- 支持路径格式: `xxx.skill/SKILL.md`
- 增强 Content-Disposition 头部处理
- 5 分钟缓存头避免重复 ZIP 解压

### Changed

#### Docker 配置优化
- CLI auth 目录绑定 (`~/.claude`, `~/.codex`)
- 环境变量整理和路径规范化
- 新增 healthcheck 注释

### Fixed

#### 模型加载稳定性修复
- 修复 LangGraph 多 worker 场景下模型配置缓存初始化时序问题
- 症状: 首个请求报错 "No chat model could be resolved"
- 解决: 重启 LangGraph 服务后配置正确加载

#### 对话可见性修复
- 修复 `normalize_thread_visibility()` 默认值为 PRIVATE
- 解决新创建对话在列表中不可见的问题
- 测试用例已更新并全部通过

## [1.5.0] - 2026-05-19

### Added

#### 语音转文字 (STT) 功能
- 内置 faster-whisper 语音识别引擎，完全离线处理
- 支持中文、英文等多语言识别
- 管理员可配置模型大小（小/中/大）
- 隐私安全，录音数据不上传第三方

#### Admin 模型配置
- STT 模型大小配置开关（小/中/大）
- 根据服务器资源选择合适的模型规格

### Fixed

#### 对话可见性修复
- 修复 `normalize_thread_visibility()` 默认值为 PRIVATE
- 解决新创建对话在列表中不可见的问题
- 测试用例已更新并全部通过

## [1.4.9.3] - 2026-05-17

### Added

#### GLM (智谱AI) Model Expansion (GLM 模型扩展)
- Expanded from 6 to 13 GLM models:
  - **Text Models**: GLM-5.1, GLM-5, GLM-5-Turbo, GLM-4.7, GLM-4.6, GLM-4.7-FlashX, GLM-4.5-Air, GLM-4.5-AirX, GLM-4.7-Flash (free)
  - **Vision Models**: GLM-5V-Turbo, GLM-4.6V, GLM-4.6V-FlashX, GLM-4.6V-Flash (free)
- Updated model descriptions with context window sizes (200K/128K)
- Added GLM-5-Turbo (OpenClaw optimized for agentic workflows)

#### Minimax (小米) Model Expansion (Minimax 模型扩展)
- Expanded from 4 to 8 Minimax models:
  - **Flagship**: M2.7, M2.7-Highspeed, M2.5, M2.5-Highspeed
  - **Special**: M2-her (role-play/multi-turn conversations)
  - **Legacy**: M2.1, M2.1-Highspeed, M2
- Fixed model naming: `M2.5-Lightning` → `M2.5-Highspeed` (official naming)
- Fixed API endpoint: `https://api.minimax.io/v1` → `https://api.minimax.io/anthropic` (Anthropic-compatible mode)
- Corrected context window size in descriptions: 1M → 200K

### Changed

#### Model Presets Cleanup (模型预设修正)
- All GLM/Minimax models now have accurate context window sizes in descriptions
- Minimax API endpoint updated to Anthropic-compatible mode for better compatibility

## [1.4.9.2] - 2026-05-16

### Added

#### MCP Preset Servers (MCP 预设服务器)
- Added 10 MCP server presets: filesystem, github, postgres, sqlite, brave-search, slack, memory, google-maps, sentry, aws-kb
- MCP server configuration UI with expandable OAuth settings panel
- Client ID/Secret, Auth URL, Token URL, and Scopes configuration support

#### IM Channel Test Integration (IM 渠道测试集成)
- Added test functionality for all 5 IM channels: Feishu, Slack, Telegram, WeCom, DingTalk
- Channel test API endpoints in backend
- UI in channels-admin-page.tsx with test button and result display

#### Model Presets Enhancement (模型预设增强)
- Added 10 model providers with 40+ model presets:
  - **OpenAI**: GPT-4.1, GPT-4.1 Mini, o3, o3-mini, o4-mini, o1-mini
  - **Anthropic**: Claude Opus 4.7, Claude Sonnet 4.6, Claude 3.5 Sonnet, Claude 3.5 Haiku
  - **Google**: Gemini 2.5 Pro, Gemini 2.5 Flash, Gemini 2.0 Flash
  - **DeepSeek**: V4 Pro, V4 Flash, R1, R1-0528
  - **Groq**: Llama 4 Scout, Llama 4 Maverick, Llama 3.3 70B, Qwen3 32B
  - **xAI**: Grok 4.3, Grok 3
  - **Cohere**: Command A, Command R+, Command R7B
  - **GLM**: GLM-5.1, GLM-5, GLM-4.7, GLM-4.7-FlashX, GLM-5V-Turbo, GLM-4.6V
  - **Minimax**: M2.7, M2.7-Highspeed, M2.5, M2.5-Lightning
  - **Qwen**: Qwen3-Max, Qwen3.5-Plus, Qwen3.5-Flash, Qwen-VL-Max, QVQ-Max
- Model import UI in Admin panel with provider filtering
- Updated config.example.yaml with comprehensive model configuration examples

### Changed

#### Config.example.yaml Update (配置文件更新)
- Added MODEL PRESETS REFERENCE section at top of models configuration
- Added example configurations for all 10 providers
- Improved documentation with provider-specific settings

## [1.4.9.1] - 2026-05-16

### Fixed

#### 登录 Session Cookie 签名不一致问题 (Login Session Cookie Signature Mismatch)
- 根因: `docker-compose-dev.yaml` 中 frontend 服务的 `BETTER_AUTH_SECRET` 硬编码为 `local-dev-secret-for-micx`，与 backend 的 `micx-local-dev-secret-2026-04-13-please-change` 不一致
- 影响: backend 创建的 session cookie 被 frontend 拒绝验证，导致登录看似成功但立即跳转回登录页
- 修复: 移除 docker-compose-dev.yaml 中 frontend 服务的硬编码 BETTER_AUTH_SECRET 环境变量，改为从 `frontend/.env` 文件读取

## [1.4.8] - 2026-05-12

### Fixed

#### PPT Master 误触发问题 (PPT Master False Trigger)
- 修复 Lead Agent 在普通对话中误触发 PPT Master 技能的问题
- 根因: prompt.py 中技能加载指令过于激进
- 修复: 修改技能加载规则, 仅在用户明确要求或任务直接匹配技能核心用例时加载技能

#### UI Bug 修复 (Frontend Bug Fixes)
- Bug 4: 修复模式切换下拉菜单不显示已选模式的问题
- Bug 6: 修复引用消息时 AI 回复异常的问题
- Bug 8: 修复特定 UI 状态下输入框宽度异常的问题

## [1.4.7] - 2026-05-11

### Added

#### PPT Master Service (PPT Master 服务)
- 超时控制 (默认 120s)
- 重试机制 (指数退避, 最多3次)
- 错误分类 (可重试 vs 不可重试错误)
- 任务状态持久化 (JSON 文件, TTL 24h)
- 进度跟踪 API (`GET /api/ppt/task/{id}/status`)
- 降级警告 (`is_fallback`, `warning` 字段)
- 中文字体支持 (matplotlib + WenQuanYi 字体)
- API 端点:
  - `POST /api/ppt/generate` - 生成 PPT
  - `GET /api/ppt/task/{task_id}/status` - 获取任务状态
  - `POST /api/ppt/task/{task_id}/cancel` - 取消任务
  - `GET /api/ppt/download/{task_id}` - 下载 PPT
  - `GET /api/ppt/templates` - 获取模板列表

#### Deep-Research Skill Enhancement (深度研究技能增强)
- 添加中文触发词 (深度研究、深度搜索、深入研究)
- Agent prompt 添加复合任务优先级规则
- 修复 Skill 路由问题

### Removed

#### UI Cleanup (界面清理)
- 移除"设置和更多"菜单中的"演示生成"入口

## [1.4.6] - 2026-05-06

### Added

#### AI Message Citation Badges (AI消息引用来源badge)
- Frontend `MarkdownContent` component now automatically detects `[citation:xxx](url)` format
- Renders citation badges via `CitationLink` component with hover preview
- Supports web search citations and knowledge base citations in AI messages

#### Memory Settings Enhancement (记忆设置增强)
- Added undo toast for fact deletion in memory settings page
- Shows fact content before deletion, allows undo within 5 seconds
- Improved delete confirmation dialog
- Displays source thread link for non-manual facts

#### Admin Memory View (Admin记忆查看)
- New admin page at `/workspace/admin/memory`
- Admin can query any user's memory data by user ID
- Displays: context, facts with confidence levels, system prompt context, last updated time
- Backend API: `GET /api/admin/memory/users/{user_id}`

#### Knowledge Base Document Retry (知识库文档重试)
- Knowledge base detail page at `/workspace/knowledge/{kb_id}` already includes reindex/retry functionality
- Failed documents can be re-indexed via the retry button

## [1.4.4] - 2026-04-29

### Fixed

#### Per-User Memory Path (记忆功能用户私有路径)

- Fixed memory saving to global `memory.json` instead of per-user file
- Root cause: `MemoryMiddleware` queues updates in a background `threading.Timer` callback where FastAPI's `ContextVar` is not propagated
- Fix: Capture `user_id` at middleware time and pass explicitly through queue → updater → storage
- Memory now correctly saves to `.deer-flow/users/{user_id}/memory.json`

### Added

#### Brand Text Customization (品牌文字定制)

- Admin can now configure all login page and homepage text from `/workspace/admin/config`
- **Login page**: Badge text, title, subtitle, 2 feature card titles/descriptions
- **Homepage**: 3 capability cards, 4 use-case items, "Why choose" block, team edition block
- Supports `{name}` and `{support_email}` placeholders in text
- Changes take effect immediately (hot-reload via `micx-brand-updated` event)

## [1.4.3] - 2026-04-26

### Added

#### Capture/Summarize Bug Fix (沉淀功能修复)

##### Frontend: HTTP 422 & Toast Loop
- Fixed `POST /api/threads/{id}/summarize` request missing `Content-Type: application/json` header and request body
- Added `body: JSON.stringify({ max_messages: 50 })` to match FastAPI Pydantic validation
- Improved error handling: non-Error objects now serialized via `JSON.stringify()` instead of showing hardcoded text
- Prevented toast error infinite loop caused by effect re-triggering on failed state

##### Backend: Empty Message Text in Summarization
- Fixed `summarize_thread` reading raw msgpack checkpoint data without deserializing LangChain objects
- Added `serialize_channel_values()` call to convert msgpack `ExtType` objects to JSON-safe dicts
- Messages are now properly extracted for LLM summarization

#### Admin Knowledge Base Management (管理员知识库管理)
- Admin knowledge base list page at `/workspace/admin/knowledge`
- Edit knowledge bases (name, description, visibility) via admin interface
- Admin API endpoint: `PUT /api/admin/knowledge/{kb_id}`

#### User Knowledge Base Creation (用户知识库创建)
- User knowledge base creation now respects visibility field
- Options: Private (私有) / Workspace (工作区共享)
- Visibility is properly saved during creation

### Fixed

#### Knowledge Base Creation Bug
- Fixed KB creation ignoring "workspace knowledge" selection
- Visibility field is now properly used instead of hardcoded "private"

#### Skill Management Permissions (技能管理权限)
- Fixed: Regular users could not create custom skills
  - Changed `POST /api/skills/custom` from `require_owner_user` to `require_user`
- Fixed: Admins could not edit built-in (public) skills
  - Updated `PUT /api/skills/custom/{skill_name}` to support admin editing of public skills
  - Added proper handling for both custom and public skill files

#### HTTP 413 Upload Error
- Fixed nginx configuration for large file uploads
- Added `client_max_body_size 100M` and `proxy_request_buffering off`
- Fixed uvicorn command to remove invalid `--limit-max-bytes` parameter

## [1.4.2] - 2026-04-25

### Added

#### Feishu Platform Tools (飞书平台工具)

**Cloud Drive (云盘)**
- `feishu_drive_file_delete` - Delete cloud drive files
- `feishu_drive_file_move` - Move files within cloud drive
- `feishu_drive_file_copy` - Copy files in cloud drive

**Bitable (多维表格)**
- `feishu_bitable_record_create` - Create single record in bitable table
- `feishu_bitable_record_update` - Update single record in bitable table
- `feishu_bitable_record_delete` - Delete single record from bitable table
- `feishu_bitable_table_list` - List all tables in a bitable
- `feishu_bitable_field_list` - List all fields in a bitable table

**IM (消息增强)**
- `feishu_message_get` - Get message content by ID

**Calendar (日历)**
- `feishu_calendar_event_get` - Get calendar event by ID

**Task (任务)**
- `feishu_task_get` - Get task details by GUID

**Mail (邮件)**
- `feishu_mail_create_draft` - Create mail draft

**Sheets (电子表格)**
- `feishu_sheet_create` - Create new spreadsheet in folder

### Fixed

- `feishu_doc_write` - Fixed block_id and response parsing bugs
- `feishu_sheet_write` - Fixed request body format and response field names
- `feishu_sheet_read` / `feishu_sheet_range` - Fixed response data access

## [1.4.0] - 2026-04-20

### Added

#### Scheduled Tasks (定时任务)
- Task CRUD operations with SQLite persistence
- Trigger types: Cron expressions and Interval (minutes/hours/days)
- One-time task support
- Task execution with LangGraph integration
- Execution history with result summary (完整 AI 响应)
- Pause/Resume task controls
- Task sharing between users

#### Knowledge Base (知识库)
- RAG-based knowledge management system
- Document upload and processing
- Vector storage with embedding support
- Knowledge retrieval in agent context
- Web content extraction (jina.ai)
- Knowledge base CRUD operations

#### IM Channels Configuration (IM 渠道配置)
- 飞书 (Feishu) integration
- Slack integration with Socket Mode support
- Telegram Bot integration
- 企业微信 (WeCom) integration
- 钉钉 (DingTalk) integration (NEW)
- Channel enable/disable controls
- Channel restart functionality
- Admin UI for channel management at `/workspace/admin/models/mcp/channels`

#### Navigation Restructuring
- MCP Configuration moved to Admin Console
- IM Channels moved to Admin Console
- Consistent admin navigation structure
- User Settings dropdown cleanup

### Fixed

#### Bug Fixes
- nginx routing for `/api/tasks` and `/api/knowledge` endpoints
- nginx routing for `/api/channels` endpoint (trailing slash handling)
- TypeScript type errors in channels-admin-page.tsx
- TypeScript type errors in mcp-admin-page.tsx
- useMyCustomSkills hook missing refetch return value
- Scheduled tasks datetime.UTC alias compatibility
- Skills custom endpoint 403 permission error
- Cron expression user guidance with examples

### Changed

#### Backend
- Added `tasks` and `knowledge` to router exports
- Updated channel models with new field types
- Fixed _get_skill_shares import issues
- Enhanced task execution with result summary

#### Frontend
- Enhanced task detail page with trigger editing
- Added cron guidance i18n strings
- Fixed nullish coalescing operator usage
- Improved channel configuration UI

## [1.3.0] - 2026-04-19

### Added

#### Scheduled Tasks System
- Task creation with prompt templates
- Cron and interval trigger configuration
- Task pause/resume functionality
- Task execution via "Run Now" button
- Task sharing between users

#### Knowledge Base
- RAG knowledge management
- Document embedding and retrieval
- Web content extraction

### Changed

#### Backend
- Task router with SQLite persistence
- Knowledge router with vector storage
- Channel service improvements

## [1.2.0] - 2026-04-17

### Added

#### Skill User Isolation
- Regular users now only see skills they created or that are shared publicly by admin
- Admin (owner) can see ALL skills
- Skills without share records are treated as private
- Visibility rules: own skills, public skills, workspace-shared skills
- SkillShare records auto-created on custom skill creation and remote install

#### Token Statistics
- File-based token usage tracking per user
- Admin token usage dashboard at `/workspace/admin/token-usage`
- TokenUsageMiddleware logs token consumption with WARNING level

#### Model Presets
- 20+ pre-configured model presets for OpenAI, Anthropic, Google, Azure, Groq, DeepSeek, Ollama, etc.
- Quick model selection in configuration center
- Support for custom model endpoints

#### Configuration Center Enhancements
- MCP server configuration: type, url, headers, description fields
- Tool configuration: use, extra_params fields
- Full parameter support for MCP and tools

### Fixed

#### Preview Window Flicker
- Fixed flickering during agent execution by using CSS visibility instead of conditional rendering

#### Markdown Download
- Added download button in preview mode for markdown files
- Download button uses proper blob URL to save content with correct filename

#### Artifact Download Links
- Fixed artifact links in markdown content (Streamdown rendered) to properly trigger downloads
- Added ArtifactLinkContextProvider to pass threadId through React context
- ArtifactLink now converts internal /mnt/... paths to proper download URLs

### Changed

#### Frontend Updates
- File cards in chat messages are now clickable and trigger downloads
- Image files open in new tab for preview
- Non-image files download directly when clicked
- Download icon added to file cards for visual feedback

## [1.1.0] - 2026-04-16

### Added

#### Admin Configuration Center UI
- Complete config.yaml management through web UI at `/workspace/admin/config`
- System configuration: log_level, token_usage, checkpointer settings
- Model configuration: CRUD operations, API key management
- Sandbox configuration: provider type, bash permissions, timeouts
- Tool configuration: enable/disable tools, group management
- Upload configuration: size limits, allowed extensions, markdown conversion
- Skills configuration: paths, auto-update, security scan settings
- MCP server configuration: command, args, env variables
- Tracing configuration: LangSmith and Langfuse integration
- Configuration validation with detailed error messages
- Sensitive fields (API keys) are masked in responses
- Real-time config reload without service restart

#### User Skills Management
- **Skills Settings Page**: Available at `/workspace/settings/skills` (accessible via Settings Dialog)
- **All Skills Tab**: Browse and enable/disable all available skills
- **My Creations Tab**: View and manage custom skills created by the user
- **Shared Records Tab**: Share skills and rate other skills
- **Custom Skill Creation**: Create new skills with SKILL.md template
  - Name validation and uniqueness checking
  - Security scan before creation
  - Frontmatter validation
- **Skill Sharing**: Share skills with visibility options
  - Public: visible to all users
  - Workspace: visible to workspace members only
- **Skill Rating**: Rate skills with 1-5 stars and optional comments
- **Skill Configuration**: Personal skill settings and default skill selection

#### New Backend APIs
- `GET /api/user/skills` - List user skill configurations
- `PUT /api/user/skills/{skill_name}/config` - Update skill configuration
- `POST /api/user/skills/{skill_name}/enable` - Enable a skill
- `POST /api/user/skills/{skill_name}/disable` - Disable a skill
- `GET /api/user/skills/{skill_name}/ratings` - Get skill ratings
- `POST /api/skills/custom` - Create custom skill
- `POST /api/skills/{skill_name}/share` - Share a skill
- `POST /api/skills/{skill_name}/unshare` - Unshare a skill
- `GET /api/skills/shared` - List shared skills
- `POST /api/skills/{skill_name}/rate` - Rate a skill

#### New Frontend Components
- `UserSkillsPage` - Main skills management interface
- `CreateSkillDialog` - Skill creation with markdown editor
- `ShareSkillDialog` - Share settings with visibility options
- `RateSkillDialog` - Star rating with comment

### Fixed
- Fixed NameError in skills.py where response models were used before definition
- Fixed path configuration in admin config (was using non-existent `data_dir`)
- Fixed type errors in AdminTracingResponse (langfuse config)
- Removed unused imports causing lint warnings

### Changed
- Updated Skill type to include all fields from backend response
- Settings Dialog now includes Skills section in navigation

### Security
- Skill creation blocked if security scan detects malicious content
- API key fields are masked in GET responses
- Password strength requirements enforced for BY_ADMIN_PASSWORD

## [1.0.0] - 2026-04-13

### Added
- Initial MicX release based on DeerFlow
- Admin management console with monitoring, config, skills, users, workspaces, models
- Multi-user support with workspace collaboration
- Thread visibility model (private by default)
- Brand customization (MicX branding)
- Chinese localization complete
- Production security hardening
- SQLite checkpoint persistence

---

## Release Types

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
