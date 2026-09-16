# v1.8 收尾计划 — 模型管理加强 + 即时通讯频道更新 + 既有遗留收口

> **Planned:** 2026-09-15
> **性质:** 当前版本 (main `2b45f4ac`) 的收尾计划。把新需求（模型管理加强、IM 频道更新）与既有遗留项整合到一个可排期的清单。
> **约定:** 每个里程碑 TDD → 实现 → 后端+前端门禁 → commit。后端 `CI=1 uv run pytest tests/ -q`（仅剩 2 个已知 `client_e2e`）、前端 `pnpm test` + `pnpm build`、ruff 洁净。

---

## Context

当前版本功能已基本可用（ABAC 管理覆盖、canvas、quota、多区域密钥、Slack socket mode 已交付），登录旁路问题已修复。收尾阶段聚焦三块：**① 模型管理菜单加强**（把主流供应商全纳入 + 通过 API 地址自动拉取模型快捷配置）、**② 即时通讯频道更新**、**③ 清理既有遗留**。

## 现状（已核实，勿重推）

- 模型管理后端：`routers/models.py` 有 `/api/admin/models` CRUD + `/test` + `/reload`；`ModelConfig` 字段支持 `model / base_url / api_key / use(类路径) / request_timeout / max_retries / max_tokens / temperature / use_responses_api / output_version / supports_thinking / supports_reasoning_effort / when_thinking_enabled / supports_vision / thinking / capabilities`。前端 `models-preset.ts` 的 `providers` + `modelPresets` 目前以 **OpenAI 系为主**（GPT-4.1/4o/4o-mini）。
- 模型持久化：写 `models.override.yaml`（`_read_override_data/_normalize_model_record/_persist_and_reload`）→ `reload_app_config()`，已有 `model.created` 审计。
- IM 频道：`backend/app/channels/` 已有 `feishu / slack(socket mode) / telegram / wecom / dingtalk` 五个 `Channel` 实现；由 `config.yaml[channels]` 驱动，`/api/channels/` 状态端点；前端已有 `admin/channels` 页。Slack Socket Mode 的 **admin 开关 + 429 指标** 仍是 v1.7 defer。
- 模型自动发现：**无**。当前新增模型靠手动填 `base_url + model + api_key`。

---

## 规划里程碑

### M1 — 模型管理：主流供应商全域纳入（用户需求①）

**目标：** 新增模型时能选入所有主流大模型供应商，且预置每个供应商的推荐模型 + 默认参数。

- **任务 M1.1（供应商预置）** 扩展前端 `core/config/model-presets.ts` 的 `providers` + `modelPresets`，覆盖：
  - 国际/主流：OpenAI、Anthropic (Claude)、Google Gemini、Mistral、Cohere、Groq、Azure OpenAI、xAI (Grok)、Amazon Bedrock。
  - 中国/本地：DeepSeek、阿里云百炼 (Qwen)、智谱 GLM、Moonshot Kimi、字节豆包、`01.AI`、MiniMax、Kimi。
  - 本地/自托管：Ollama、vLLM、LM Studio、OpenAI 兼容网关。
- [ ] 每个 preset 预置：`provider, api_base, model(示例), supports_vision/thinking/reasoning, output_version, api_key 占位`，供一键填充表单。
- [ ] **后端供应商目录** `deerflow/models/catalog.py`（或扩展已有 `vendor_catalog`）：出 `{provider_id, display_name, api_base, doc, auth_type(api_key/oauth), discovery`，供前端下拉 + 后端校验 `use` 解析路径。
- [ ] 测试：preset/catalog 单测（供应商覆盖清单、字段完整性、`use` 类路径可导入）。

### M2 — 模型管理：从 API 地址自动读取模型 + 快捷配置（需求②）

**目标：** 输入供应商 API 地址 + 密钥 → 后台拉取可用模型列表与参数 → 一键生成配置草案。

- [ ] **M2.1 后端探查端点** `POST /api/admin/models/inspect`，body `{provider_id?, base_url?, api_key?, auth_type?}`，owner-only（`require_abac`，沿用 `admin-config` 资源或新增）。
  - OpenAI 兼容：`GET {base_url}/models`；解析 `id`，合并常见能力指标（由 id 前缀/命名规则推断 `supports_vision/thinking`）。
  - 非 OpenAI 兼容：对 Anthropic 用官方 `models` 端点（或回退预置清单）；对 Google 用 `generativelanguage...listModels`；对非兼容 provider 回退到 M1 预置。
  - 失败降级：返回 `{providers_fallback: true}`，不因网络密钥缺失 500。
- [ ] **校验端点**：`POST /api/admin/models/{name}/test`（已有）继续作为「连接测试」，`inspect` 专注「枚举可用模型」。
- [ ] **前端 `models` 页**：新增「自动发现」面板 — 输入 provider/base_url/api_key → 调 `inspect` → 列出可用模型（id、可推断能力）→ 一键「以此新增」，用返回参数 + 能力预填 `ModelConfig` 表单（含 `use`/thinking/vision 推断）。
- [ ] 安全：`base_url` 做 SSRF 校验（仅允许 https/provider 白名单/内网校验），`api_key` 走现有 `$ENV`/`secret://` 引用占位，不明文落库。
- [ ] 测试：`inspect` 端点单测（OpenAI 兼容 mock、非兼容 fallback、SSRF 拒绝、参数推断）、前端交互单测。

### M3 — IM 频道更新 + 收尾（既有遗留 + 新）

- [ ] **频道审计/更新**：`channels/service.py` 生命周期、五平台 `Channel` 迁移到异步流式发送（对齐 Feishu 卡片 patcch 模式）；补 `channels` 状态健康字段（已连接/ws 状态）。
- [ ] **单一管理入口**：`admin/channels` 前端集成为每平台「启用 + 凭据填表 + 心跳/最近消息」卡片（align `secrets-admin-page` 四 Tab 模板）。
- [ ] **沿用 v1.7 defer**：给 Slack Socket Mode 加 admin 开关（在 `admin/channels` 支持 bot/app token + socket/webhook 切换）。
- [ ] 可选扩展：Discord 频道（`channels/discord.py`，用现有 `Channel` ABC），按需纳入。

### M4 — 模型/频道既有遗留收口（上版 defer 项）

- [ ] **M4.1 model-admin 兼容**：`models.py` 的 `POST /admin/models` 增 `provider`/`discovered_from` 标注；删除 base-model 逻辑保留。
- [ ] **M4.2 多区域密钥（v1.7 M4 遗留）**：GCS/Aliyun replicator adapters + 实时 DR drill（需真实 obj-store 凭据）。
- [ ] **M4.3 策略编辑器（v1.7 M2.6 遗留）**：`/api/admin/policies` 增加专属审计 tab + `POST publish`。
- [ ] **M4.4 测试红线归零**：修最后 2 个 `client_e2e`（stale `.skill` regex + Docker `/app` 路径），使全量后端 `0` known-failure。

---

## 验收标准（全部通过才算收尾）

1. 主流供应商（国际 + 中国 + 本地/自托管）均可在「新增模型」中选入，且能保存为新 `ModelConfig`。
2. 输入任一主流 OpenAI 兼容 base_url + key，`inspect` 能列出该供应商可用模型，并能一键生成配置草案；`/admin/models/{name}/test` 可连测。
3. `inspect` 对非 OpenAI 兼容 provider 走预置回退，SSRF 与密钥安全守死，无明文落库。
4. IM 频道都能在 `admin/channels` 里「启用 + 配” + 心跳」；Slack socket 有 admin 开关。
5. 全量回归：`CI=1 uv run pytest tests/ -q` 通过（第 zero known `client_e2e` removed IN M4.4，否则 ≤2 known）；`pnpm test` + `pnpm build` 绿；ruff 洁净。
6. 每条 M 落 commit，文档（CHANGELOG / CLAUDE 模型/频道节）同步。

---

## 风险

- **M2 发现粒度**：OpenAI 兼容 `/models` 无「能力」元数据，能力推断靠命名启发式，可能误判 — 允许前端手动覆写，不 tod硬。
- **SS 过滤**：`base_url` 用户输入是 SSRF 风险，必须白名单/内网拒绝。
- **频道更新**：DingTalk/WeCom 官方 SDK 迭代快，授权模式可能有变化 → 用已有 `Channel` ABC 隔离，不引入新基础库。
- **M4 的 DR drill** 需真实凭据，代码可交付，实操演练需环境。

## 排期建议

可以先生成 M1→M2（用户需求核心「模型管理加强」），M3（频道）接续，M4 收尾项穿插。M4 各子项彼此独立。