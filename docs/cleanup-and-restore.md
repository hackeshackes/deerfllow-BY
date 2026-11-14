# DeerFlow 本地清理与恢复指南

> **记录日期:** 2026-11-14
> **适用:** 本地开发环境（macOS + Docker Desktop）。项目暂不开发时清理资源；需要时按本文恢复。

---

## 一、清掉哪些、释放了多少（2026-11-14 实际执行）

依赖源码与仓库外的开发/运行/缓存产物，按来源分组：

| 级别 | 内容 | 释放 | 备注（删后需重建） |
|---|---|---|---|
| 1 | `backend/.venv`（Python 环境） | ~1.8G | `uv sync` 重建 |
| 1 | `frontend/node_modules` | ~1.3G | `pnpm install` 重建 |
| 1 | `frontend/.next`（Next 构建缓存） | ~2.5G | `next build` 重建 |
| 1 | `.pytest_cache` / `.ruff_cache` / `.playwright-mcp` / `logs` / `test-results` | ~5M | 测试/运行再生成 |
| 1 | `docker/.env.bak`（旧密码备份） | 小 | 删去 |
| 2 | `backend/.deer-flow`（运行 DB：checkpoints/canvas/comments/memory/users/workspaces + `models.override.yaml`） | ~1.0G | 再次开发需重新初始化（见下） |
| 3 | `.claude/worktrees/*`（6 个历史工作树，含各自 venv/node_modules） | ~14G | `git worktree remove -f` + `prune` |
| 4 | Docker：deer-flow 容器全停删、镜像 ×3（gateway/langgraph/frontend ~13G）、deer-flow 网络 ×3 | ~13G | `docker compose build / up` 重建镜像 |

**合计**：仓库目录由 ~21G 降到 **~665M**（仅源码+`.git`+docs）；本机磁盘可用从 ~23Gi 增到 **~36Gi**。其它项目（`by-tradingagents`/`litellm` 等）的容器/镜像/卷**未动**。

---

## 二、恢复开发（再次需要时可执行）

### 1) 恢复依赖
```bash
cd backend && uv sync
cd frontend && pnpm install
```

### 2) 重建运行时初始数据
`backend/.deer-flow` 被删后，首次启动会重建默认状态：
- **owner 用户 / 密码**：`scripts/` 或正常初始化创建首个 owner；密码以当前部署的 `BY_ADMIN_PASSWORD` 为准（必要时用 `reset_owner_password.py` 重设）。
- **模型配置**：`models.override.yaml` 已删，需重新通过模型管理 UI 添加/配置模型（含 API key）。

### 3) 重建 Docker 镜像并启动
> 说明：构建较长且依赖网络能拉到 HF whisper 小模型 + npm；网络不稳时可能需重试。
```bash
# 构建（backend 镜像含 whisper）
HF_ENDPOINT=https://huggingface.co docker compose -p deer-flow -f docker/docker-compose.yaml build gateway langgraph frontend
docker compose -p deer-flow -f docker/docker-compose.yaml up -d
```

### 4) 一致性校验
```bash
cd backend && CI=1 uv run pytest tests/ -q     # 期望全绿（0 known）
cd frontend && pnpm test && pnpm build
curl -s localhost:2026/health
```

---

## 三、注意 / Trade-offs
- **`.deer-flow` 数据删除不可逆**：若里面有需要保留的对话/用户/工作流数据，先备份 `backend/.deer-flow` 再清。
- **删除镜像后重建慢**：Docker build 会重新下载 whisper + 依赖。
- **Docker 清理范围**：示例清的是 `deer-flow-*`；如需一并清其它项目镜像，请自行评估（本机其它容器/卷未被动过）。

## 四、位置
- 本文件：`docs/`（建议保留受版本管）。
- 发行说明：`docs/releases/*.md`。
- 后续清理/恢复变更在此更新本页即可。