# MicX 遗留问题修复研发计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 MicX (DeerFlow fork) v1.5.2 中识别的关键遗留问题,优先处理凭据泄露、不应追踪的大文件、已知异步瓶颈,以及可立即落地的代码质量改进。

**Architecture:** 分阶段推进 — 先 P0 安全/卫生(凭据+gitignore),再 P1 异步瓶颈(影响生产性能),最后 P2 前端测试基础设施。每阶段产出可独立验证的 commit。涉及运行中 docker 容器的步骤需要先 `docker compose down` 再 `up`。

**Tech Stack:** Python 3.12+ / FastAPI / LangGraph / Next.js 16 / React 19 / TypeScript 5.8 / Docker Compose / uv / pnpm

**当前本地环境状态(已核实):**
- 分支: `main`,working tree 干净
- 容器运行中(5 天): `deer-flow-frontend`、`deer-flow-gateway`、`deer-flow-langgraph`、`deer-flow-nginx`
- venv: `backend/.venv` (1.7G) 已 ignore ✅
- node_modules: `frontend/node_modules` (977M) 已 ignore ✅
- 凭据最早出现在 commit `9a3d1de3` (v1.5.0, 2026-05-19),至今未变

**已确认无需处理:**
- `skills/ppt-master/` (514M) 已被 ignore ✅
- `.playwright-mcp/` / `.gstack/` 已被 ignore ✅
- 根 `.env` / `backend/.env` / `frontend/.env` / `docker/.env` 已被 ignore ✅
- 后端 102 个测试文件,健康 ✅

---

## File Structure

### 本计划修改/创建的文件

```
/Users/baoyu/Documents/GitHub/deerfllow-BY/
├── .gitignore                                          # 扩展 ignore 规则
├── docker/
│   ├── .gitignore                                      # 新建: 局部 ignore
│   ├── e2e-test-micx.js                                # 改用 env 凭据
│   ├── e2e-tests/                                      # 全部 untrack
│   ├── node_modules/                                   # 全部 untrack
│   ├── test-results/                                   # 全部 untrack
│   └── e2e-tests/
│       ├── debug-chat.js                               # 改用 env 凭据
│       ├── debug-landing.js                            # 改用 env 凭据
│       ├── debug-signin.js                             # 改用 env 凭据
│       ├── micx-comprehensive.test.js                  # 改用 env 凭据
│       ├── micx-corrected.test.js                      # 改用 env 凭据
│       ├── micx-e2e.test.js                            # 改用 env 凭据
│       ├── micx-full-test.js                           # 改用 env 凭据
│       └── test-404-pages.js                           # 改用 env 凭据
├── frontend/
│   ├── package.json                                    # 添加 vitest + testing-library
│   ├── vitest.config.ts                                # 新建
│   ├── src/
│   │   ├── core/
│   │   │   ├── i18n/locales/
│   │   │   │   ├── en-US.ts                            # 拆分: 按命名空间拆为多个文件
│   │   │   │   ├── zh-CN.ts                            # 拆分
│   │   │   │   └── types.ts                            # 保留(单一类型源)
│   │   │   └── memory/
│   │   │       └── memory-utils.ts                     # 新建: 抽离可测试工具
│   │   └── components/workspace/settings/
│   │       └── memory-settings-page.tsx                # 拆分为多个组件 (Task P2-3)
│   └── tsconfig.json                                   # 添加 vitest 类型
├── backend/
│   ├── packages/harness/deerflow/
│   │   ├── agents/memory/updater.py                    # 同步→异步 (Task P1-3)
│   │   ├── sandbox/local/local_sandbox.py              # subprocess.run→async (Task P1-4)
│   │   └── tests/test_memory_updater_async.py          # 新建 (Task P1-3)
│   ├── app/gateway/rate_limit.py                       # 新建 (Task P1-5)
│   ├── app/gateway/app.py                              # 注册 rate limit (Task P1-5)
│   └── tests/test_rate_limit.py                        # 新建 (Task P1-5)
└── docs/
    └── superpowers/plans/
        └── 2026-06-02-fix-legacy-issues.md             # 本计划
```

### 不在本计划范围内(标注给后续 plan)

- P1 中 TODO.md 剩余功能(认证层/限流的完成部分/skill marketplace/沙箱池化)→ 独立 plan
- P2 拆分大文件除 `memory-settings-page.tsx` 外的 4 个超 800 行组件 → 独立 plan
- P2 替换所有 `alert()` → 独立 plan
- P2 多语言 README 同步 → 独立 plan

---

## Task P0-1: 扩展 .gitignore 规则覆盖 docker 临时目录

**Files:**
- Modify: `/Users/baoyu/Documents/GitHub/deerfllow-BY/.gitignore`

**背景核实:** 当前 `.gitignore` 只 ignore `docker/.cache/`,不 ignore `docker/node_modules/`、`docker/test-results/`、`docker/e2e-tests/`(共 423 个文件被错误追踪,合计 44M+)。

- [ ] **Step 1: 检查当前 .gitignore 的 docker 相关条目**

Run: `grep -E "^docker/" /Users/baoyu/Documents/GitHub/deerfllow-BY/.gitignore`
Expected: 仅显示 `docker/.cache/`

- [ ] **Step 2: 在 .gitignore 末尾追加 docker 临时目录规则**

打开 `/Users/baoyu/Documents/GitHub/deerfllow-BY/.gitignore`,在已有 `docker/.cache/` 块下,或在该块下新增一行块,添加:

```gitignore
# Docker test/scratch directories
docker/node_modules/
docker/test-results/
docker/e2e-tests/
```

(注释: 也可选用 `**/docker/node_modules/` 等通配风格,但精确路径在已有 codebase 风格中更清晰。)

- [ ] **Step 3: 验证 ignore 生效**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git check-ignore -v docker/e2e-test-micx.js docker/e2e-tests/01-landing-page.png docker/node_modules/.bin/playwright docker/test-results/admin_audit.png
```

Expected: 4 行都返回 ignore 规则路径(exit 0)

- [ ] **Step 4: 提交**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git add .gitignore
git commit -m "chore: ignore docker e2e artifacts and node_modules"
```

---

## Task P0-2: 从 git 索引移除 423 个误追踪文件(保留本地)

**Files:**
- (不修改文件内容,只调整 git 索引)

- [ ] **Step 1: 确认要 untrack 的文件计数**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git ls-files docker/e2e-tests docker/test-results docker/node_modules | wc -l
```

Expected: 423(或类似量级,可能 421-425)

- [ ] **Step 2: dry-run 检查将 untrack 的文件**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git rm -r --cached --dry-run docker/e2e-tests docker/test-results docker/node_modules 2>&1 | tail -5
git rm -r --cached --dry-run docker/e2e-test-micx.js 2>&1
```

Expected: 第一行显示 `Would remove ...` 列表,以 `421+ files would be removed` 结尾。`e2e-test-micx.js` **不在列表中**(因为它不是这 3 个目录中的)。

- [ ] **Step 3: 实际从 git 索引移除(--cached,保留工作树)**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git rm -r --cached docker/e2e-tests docker/test-results docker/node_modules
```

Expected: 输出 `rm 'docker/e2e-tests/01-landing-page.png'` 等大量行,最后 `421+ files changed`。

- [ ] **Step 4: 验证工作树文件仍存在**

Run:
```bash
ls /Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-test-micx.js
ls /Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-tests | head -3
```

Expected: 文件存在(本地不删除),`ls docker/e2e-tests` 仍有截图。

- [ ] **Step 5: 提交**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git status --short | head -5
git commit -m "chore: untrack docker e2e artifacts and node_modules (~423 files, 44M)"
```

---

## Task P0-3: 移除 e2e-test-micx.js 中硬编码的凭据

**Files:**
- Modify: `/Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-test-micx.js:1-15`

**背景:** 当前代码:
```js
const BASE_URL = 'http://localhost:2026';
const EMAIL = 'sabar.bao@me.com';
const PASSWORD = 'MicxLocal123!';
```

需改为从环境变量读取并提供 fallback 提示。

- [ ] **Step 1: 阅读文件全文确认修改点**

Run:
```bash
cat -n /Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-test-micx.js | head -15
```

- [ ] **Step 2: 替换前 8 行的硬编码常量**

Edit: `/Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-test-micx.js`

old_string:
```js
import { chromium } from '@playwright/test';

const BASE_URL = 'http://localhost:2026';
const EMAIL = 'sabar.bao@me.com';
const PASSWORD = 'MicxLocal123!';
```

new_string:
```js
import { chromium } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:2026';
const EMAIL = process.env.E2E_EMAIL;
const PASSWORD = process.env.E2E_PASSWORD;

if (!EMAIL || !PASSWORD) {
  throw new Error(
    'E2E_EMAIL and E2E_PASSWORD environment variables are required. ' +
    'Set them in your shell or a local .env (not committed).',
  );
}
```

- [ ] **Step 3: 验证修改后语法正确**

Run:
```bash
node --check /Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-test-micx.js && echo "OK"
```

Expected: `OK`(无语法错误)

- [ ] **Step 4: 验证无残留的硬编码凭据**

Run:
```bash
grep -n "MicxLocal123\|sabar.bao" /Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-test-micx.js
```

Expected: 无输出

- [ ] **Step 5: 提交**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git add docker/e2e-test-micx.js
git commit -m "fix(security): read e2e credentials from env, remove hardcoded secrets"
```

---

## Task P0-4: 清理 docker/e2e-tests/ 中其他硬编码凭据脚本

**Files:**
- Modify: 7 个 e2e test 脚本中的凭据硬编码

涉及文件(从之前的 grep 结果):
- `docker/e2e-tests/micx-comprehensive.test.js:55-60`
- `docker/e2e-tests/micx-corrected.test.js:53-54`
- `docker/e2e-tests/micx-e2e.test.js:66-79`
- `docker/e2e-tests/micx-full-test.js:79-83`
- `docker/e2e-tests/debug-chat.js:17-18`
- `docker/e2e-tests/debug-landing.js`(待 grep 核实)
- `docker/e2e-tests/debug-signin.js`(待 grep 核实)
- `docker/e2e-tests/test-404-pages.js:50-51`

> **注:** 整个 `docker/e2e-tests/` 已在 P0-2 中 untrack,这一步是"卫生性修正" — 即便 untrack 后,文件内容仍可能含敏感信息,如果未来要重新 include 这些脚本,应当先修。

- [ ] **Step 1: 列出所有含凭据的 e2e 脚本**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
grep -rln "MicxLocal123\|sabar.bao" docker/e2e-tests/ docker/e2e-test-micx.js 2>/dev/null
```

Expected: 约 8 个文件

- [ ] **Step 2: 在每个文件中替换硬编码字符串为 env 读取**

为每个文件,采用与 Task P0-3 相同的模式:

old_string(以 `micx-e2e.test.js:74-79` 为例):
```js
      await emailInput.fill('sabar.bao@me.com');
```

new_string:
```js
      await emailInput.fill(process.env.E2E_EMAIL);
```

对每个文件的 email 和 password 行重复此替换。`process.env.E2E_PASSWORD` 同理。

如果文件顶部有 `const EMAIL = ...; const PASSWORD = ...;` 这样的声明,改为:

```js
const EMAIL = process.env.E2E_EMAIL;
const PASSWORD = process.env.E2E_PASSWORD;
if (!EMAIL || !PASSWORD) {
  throw new Error('E2E_EMAIL and E2E_PASSWORD required');
}
```

- [ ] **Step 3: 验证全部清理**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
grep -rln "MicxLocal123\|sabar.bao" docker/ 2>/dev/null
```

Expected: 无输出(整个 docker/ 不再含硬编码凭据)

- [ ] **Step 4: 提交**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git add docker/e2e-tests/
git commit -m "fix(security): remove hardcoded e2e credentials from test scripts"
```

(注: 因为整个目录 untrack,此 commit 可能不出现内容变化 — 取决于 P0-2 是否已删除 git 索引。如果 `git status` 显示无变化,此 commit 可跳过;但本地文件修改是真实的。)

---

## Task P0-5: 从 git 历史中彻底清除泄露的凭据

**Files:**
- (无文件修改,只重写 git 历史)

**背景:** P0-3/P0-4 修复了当前 HEAD 的内容,但泄露的密码 `MicxLocal123!` 仍在 git 历史中(自 commit `9a3d1de3` 起)。如果仓库是公共的,凭据已泄露。**应假设需要 rotate 密码**。

- [ ] **Step 1: 警告用户 — 此操作会改写历史**

向用户说明:
- `git filter-repo` 会重写所有受影响的 commit hash
- 如果该分支已推送(remote `origin/main` 有 v1.5.0+),需要 force-push
- 如果该仓库公开过,凭据应视为已泄露,需立即修改 `BY_ADMIN_PASSWORD`

- [ ] **Step 2: 安装 git-filter-repo(如未安装)**

Run:
```bash
which git-filter-repo || pip install --user git-filter-repo
```

- [ ] **Step 3: 备份当前 main 分支引用(以防)**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git branch backup/main-before-history-rewrite
```

- [ ] **Step 4: 用 git-filter-repo 删除文件内容中的密码**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git filter-repo --invert-paths --path docker/e2e-test-micx.js --path-glob 'docker/e2e-tests/*.js' --force
```

Expected: 重写历史,commit hash 全部改变,`docker/e2e-test-micx.js` 和 `docker/e2e-tests/*.js` 从历史中消失(注意:`*.png` 等非 js 文件保留,因为不含敏感数据)。

> **范围说明:** 此操作只删除 e2e test 的 JS 文件(包含凭据)。如果用户希望彻底删除整个 `docker/e2e-tests/` 历史,可加 `--path-glob 'docker/e2e-tests/*'`。

- [ ] **Step 5: 验证历史中已无凭据**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git log --all -p -S "MicxLocal123" 2>/dev/null | head -5
git log --all -p -S "sabar.bao" 2>/dev/null | head -5
```

Expected: 无任何 patch 输出

- [ ] **Step 6: 推送到远端(需要 force-push,且需用户授权)**

> **⚠️ 此步骤需要用户明确确认。** force-push 到 `main` 会重写公共历史。

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git push --force-with-lease origin main
```

- [ ] **Step 7: 在另一台机器或新 clone 中验证**

```bash
git clone <repo-url> /tmp/verify-clean
grep -r "MicxLocal123" /tmp/verify-clean/ 2>/dev/null
```

Expected: 无输出

- [ ] **Step 8: 文档化: 在 CHANGELOG 记录凭据轮换**

(此步骤在用户完成密码 rotate 后执行,见 Task P0-6)

---

## Task P0-6: 提示用户轮换密码并更新文档

**Files:**
- Modify: `/Users/baoyu/Documents/GitHub/deerfllow-BY/CHANGELOG.md`(在头部添加 un-released 条目)
- Modify: 用户本地的 `/Users/baoyu/Documents/GitHub/deerfllow-BY/.env` 与 `docker/.env`(用户手动)

- [ ] **Step 1: 提示用户立即轮换以下凭据**

向用户报告(不在代码中执行,因为这是用户层面的操作):
- `BY_ADMIN_PASSWORD=MicxLocal123!` — 改用强随机密码
- `BETTER_AUTH_SECRET=micx-local-dev-secret-2026-04-13-please-change` — 重新生成(`openssl rand -base64 32`)

- [ ] **Step 2: 在 CHANGELOG.md 顶部添加 un-released 条目**

Modify: `/Users/baoyu/Documents/GitHub/deerfllow-BY/CHANGELOG.md`

在第 8 行 `## [1.5.2] - 2026-05-28` 之前,插入:

```markdown
## [Unreleased]

### Security

#### 凭据轮换与历史清理
- 紧急 rotate: `BY_ADMIN_PASSWORD` 和 `BETTER_AUTH_SECRET` 已在 v1.5.0 提交到公共仓库的 e2e 测试脚本中,即便后续 commit 修复,git 历史仍可访问
- 行动: 仓库所有者应立即重置 admin 密码和 session secret
- 修复: e2e 脚本改为从 `E2E_EMAIL` / `E2E_PASSWORD` 环境变量读取
- 历史重写: `git filter-repo` 已从历史中删除 e2e 凭据脚本
```

- [ ] **Step 3: 提交**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git add CHANGELOG.md
git commit -m "docs: log credential rotation in unreleased section"
```

---

## Task P0-7: 验证 docker 容器仍能正常运行(P0 不破坏运行)

**Files:**
- (不修改文件,只验证)

- [ ] **Step 1: 确认容器仍 up**

Run:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | grep -E "deer-flow|nginx"
```

Expected: 看到 4 个 `deer-flow-*` 容器 + `deer-flow-nginx`,状态 `Up`

- [ ] **Step 2: 健康检查**

Run:
```bash
curl -s http://localhost:2026/health
```

Expected: 200 或 JSON 响应

- [ ] **Step 3: 前端可访问**

Run:
```bash
curl -sI http://localhost:2026/ | head -1
```

Expected: `HTTP/1.1 200 OK`

- [ ] **Step 4: 重启 docker 容器(P0 修改了 .gitignore 和 untrack,不影响运行,但确认无回归)**

> **本步骤可选**,因为 P0-1/P0-2 只动了 git 索引,未修改容器内文件。但如果想保险:

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
docker compose -f docker/docker-compose.yaml restart nginx
sleep 3
curl -s http://localhost:2026/health
```

Expected: 健康响应

---

## Task P1-1: 修复 memory/updater.py 同步 model.invoke 为 ainvoke

**Files:**
- Modify: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/packages/harness/deerflow/agents/memory/updater.py:340`
- Test: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/tests/test_memory_updater_async.py` (新建)

**背景:** 现有 `response = model.invoke(prompt)` 阻塞 event loop。`backend/docs/TODO.md` 已明确列出此 TODO。

- [ ] **Step 1: 写失败测试,确认当前是同步**

Read: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/tests/test_memory_updater.py` 前 30 行,理解现有测试结构。

新建: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/tests/test_memory_updater_async.py`

```python
"""Verify memory updater uses async model.ainvoke (not sync model.invoke)."""
import inspect
from unittest.mock import MagicMock, AsyncMock

import pytest


def test_memory_updater_calls_ainvoke_not_invoke():
    """Regression: ensure async event loop is not blocked by sync invoke."""
    from deerflow.agents.memory import updater

    # Inspect the source to confirm ainvoke (not invoke) is used in the LLM call site
    src = inspect.getsource(updater)
    # The LLM call line should use ainvoke
    assert "ainvoke" in src, "memory updater must use model.ainvoke for async safety"
    # It should NOT use the blocking invoke() at the LLM call site
    # (we allow invoke elsewhere, e.g. in helper utilities, but the LLM call itself must be async)
    llm_call_block = [line for line in src.split("\n") if "model.invoke(" in line]
    assert not llm_call_block, (
        f"Found blocking model.invoke in memory updater: {llm_call_block}"
    )
```

- [ ] **Step 2: 跑测试确认它失败**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/backend
PYTHONPATH=. uv run pytest tests/test_memory_updater_async.py -v
```

Expected: FAIL,显示 "Found blocking model.invoke in memory updater"

- [ ] **Step 3: 找到 LLM 调用点**

Read `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/packages/harness/deerflow/agents/memory/updater.py` 的 320-360 行,找到 `response = model.invoke(prompt)` 所在的函数。

- [ ] **Step 4: 修改为 ainvoke,确认调用函数是 async**

在文件中,确保调用 `model.ainvoke` 的函数本身是 `async def`。如果当前函数不是 async,改为 async。

Edit: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/packages/harness/deerflow/agents/memory/updater.py`

old_string(根据实际行内容调整):
```python
            response = model.invoke(prompt)
```

new_string:
```python
            response = await model.ainvoke(prompt)
```

并把所在函数改为 `async def` 如果还不是。

- [ ] **Step 5: 跑测试确认通过**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/backend
PYTHONPATH=. uv run pytest tests/test_memory_updater_async.py tests/test_memory_updater.py -v
```

Expected: 两个测试文件全部通过

- [ ] **Step 6: 检查所有 memory updater 调用点(防漏)**

Read 整个 `updater.py`,grep 所有 `model.invoke` 调用,确认无残留:

Run:
```bash
grep -n "model\.invoke\|model\.ainvoke" /Users/baoyu/Documents/GitHub/deerfllow-BY/backend/packages/harness/deerflow/agents/memory/updater.py
```

Expected: 全部 `ainvoke`,无 `invoke` 残留

- [ ] **Step 7: 提交**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git add backend/packages/harness/deerflow/agents/memory/updater.py backend/tests/test_memory_updater_async.py
git commit -m "perf(memory): convert LLM call in memory updater to async ainvoke"
```

---

## Task P1-2: 修复 local_sandbox.py 同步 subprocess.run 为 asyncio.create_subprocess_shell

**Files:**
- Modify: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/packages/harness/deerflow/sandbox/local/local_sandbox.py:240-260`
- Test: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/tests/test_local_sandbox_async.py` (新建)

**背景:** `local_sandbox.py:247,255` 用同步 `subprocess.run` 阻塞 event loop。

- [ ] **Step 1: 读现有 sandbox 实现,定位 240-260 行**

Read `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/packages/harness/deerflow/sandbox/local/local_sandbox.py:230-280`

- [ ] **Step 2: 写失败测试**

新建 `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/tests/test_local_sandbox_async.py`:

```python
"""Verify local sandbox uses async subprocess (not blocking subprocess.run)."""
import inspect


def test_local_sandbox_uses_async_subprocess():
    from deerflow.sandbox.local import local_sandbox

    src = inspect.getsource(local_sandbox)
    # The LLM-blocking subprocess.run should be replaced
    assert "subprocess.run" not in src, (
        "local_sandbox.py should not use blocking subprocess.run; "
        "use asyncio.create_subprocess_shell instead"
    )
    assert "asyncio.create_subprocess_shell" in src or "asyncio.create_subprocess_exec" in src, (
        "local_sandbox.py must use asyncio subprocess API"
    )
```

- [ ] **Step 3: 跑测试确认失败**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/backend
PYTHONPATH=. uv run pytest tests/test_local_sandbox_async.py -v
```

Expected: FAIL,显示 "should not use blocking subprocess.run"

- [ ] **Step 4: 修改 sandbox 实现**

Edit: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/packages/harness/deerflow/sandbox/local/local_sandbox.py`

确认函数已是 `async def`(若是,直接替换 subprocess 调用):

old_string(根据 247 和 255 行实际内容):
```python
            result = subprocess.run(
                ...,
                capture_output=True,
                text=True,
                ...
            )
```

new_string:
```python
            proc = await asyncio.create_subprocess_shell(
                ...,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            result = subprocess.CompletedProcess(
                args=..., returncode=proc.returncode,
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else "",
            )
```

(具体参数根据实际两处调用调整;如果两个调用点参数不同,分别替换。)

- [ ] **Step 5: 跑测试确认通过**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/backend
PYTHONPATH=. uv run pytest tests/test_local_sandbox_async.py tests/test_aio_sandbox_local_backend.py tests/test_aio_sandbox.py -v
```

Expected: 全部通过

- [ ] **Step 6: 跑相邻 sandbox 测试防回归**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/backend
PYTHONPATH=. uv run pytest tests/test_sandbox_search_tools.py -v
```

Expected: 通过

- [ ] **Step 7: 提交**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git add backend/packages/harness/deerflow/sandbox/local/local_sandbox.py backend/tests/test_local_sandbox_async.py
git commit -m "perf(sandbox): convert local sandbox subprocess.run to async create_subprocess_shell"
```

---

## Task P1-3: 替换 community tools 中的 sync `requests` 为 `httpx.AsyncClient`

**Files:**
- Modify: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/packages/harness/deerflow/community/infoquest/infoquest_client.py`
- Modify: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/packages/harness/deerflow/community/aio_sandbox/remote_backend.py`
- Modify: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/packages/harness/deerflow/community/aio_sandbox/backend.py`

- [ ] **Step 1: 列出所有用 sync requests 的文件**

Run:
```bash
grep -rln "^import requests\|^from requests " /Users/baoyu/Documents/GitHub/deerfllow-BY/backend/packages/harness/deerflow/community/ 2>/dev/null
```

Expected: 3 个文件(已核实)

- [ ] **Step 2: 检查每个文件的实际 HTTP 调用**

对每个文件,grep `requests.get` / `requests.post` / `requests.request`,记录所有调用点。

- [ ] **Step 3: 写一个共享测试,验证社区 client 不使用同步 requests(选择不改动的 client,作为对照)**

跳过此步骤 — 因为这是渐进式重构,渐进替换更适合。**改为:对每个修改的文件,确保现有测试仍通过。**

- [ ] **Step 4: 修改 infoquest_client.py**

Read 文件全文,改 `import requests` → `import httpx`,所有 `requests.get/post()` 调用改为 `async with httpx.AsyncClient() as client: response = await client.get(...)` 模式。确保外部 API 与原行为一致(timeout, headers, params 等)。

- [ ] **Step 5: 修改 aio_sandbox/remote_backend.py 和 backend.py**

同样模式。两者可能在 `__init__` 中持有 `requests.Session`,改为 `httpx.AsyncClient`。

- [ ] **Step 6: 跑相关测试**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/backend
PYTHONPATH=. uv run pytest tests/test_infoquest_client.py tests/test_aio_sandbox.py tests/test_aio_sandbox_provider.py -v
```

Expected: 全部通过

- [ ] **Step 7: 提交(可以分 3 个 commit 或合一个)**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git add backend/packages/harness/deerflow/community/
git commit -m "perf(community): convert sync requests to httpx.AsyncClient in community tools"
```

---

## Task P1-4: 后端 rate limiting 基础实现

**Files:**
- Create: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/app/gateway/rate_limit.py`
- Modify: `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/app/gateway/app.py`
- Create: `/Users/baoyu/Documents/GitHub/deerllow-BY/backend/tests/test_rate_limit.py`

**背景:** `backend/docs/TODO.md` "Planned Features" 明确列出 "Implement rate limiting"。

- [ ] **Step 1: 读现有 app.py 找到中间件挂载点**

Read `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/app/gateway/app.py` 全文,找到 `app.add_middleware(...)` 的位置。

- [ ] **Step 2: 写失败测试**

新建 `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/tests/test_rate_limit.py`:

```python
"""Verify rate limiting middleware is registered and functional."""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_rate_limit_middleware_registered():
    from app.gateway.app import app

    # Middleware classes are accessible via app.user_middleware
    middleware_classes = [m.cls.__name__ for m in app.user_middleware]
    assert any("RateLimit" in name for name in middleware_classes), (
        f"RateLimitMiddleware not found in middleware stack. Got: {middleware_classes}"
    )


def test_rate_limit_returns_429_after_burst():
    from app.gateway.rate_limit import RateLimitMiddleware

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, max_requests=2, window_seconds=60)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    response = client.get("/ping")
    assert response.status_code == 429
    assert "Retry-After" in response.headers
```

- [ ] **Step 3: 跑测试确认失败**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/backend
PYTHONPATH=. uv run pytest tests/test_rate_limit.py -v
```

Expected: FAIL,显示 `ModuleNotFoundError: No module named 'app.gateway.rate_limit'`

- [ ] **Step 4: 实现 RateLimitMiddleware**

新建 `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/app/gateway/rate_limit.py`:

```python
"""Per-IP sliding-window rate limit middleware for the Gateway API."""
from __future__ import annotations

import time
from collections import deque
from typing import Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory per-IP rate limit. Sufficient for single-process Gateway.

    Production note: this is in-process state. Multi-worker Gateway would need
    a shared backend (Redis) — out of scope for the first cut.
    """

    def __init__(
        self,
        app,
        max_requests: int = 120,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = self._hits.setdefault(client_ip, deque())
        # Drop entries outside the window
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
            return JSONResponse(
                status_code=429,
                content={"detail": "Too Many Requests"},
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)
        return await call_next(request)
```

- [ ] **Step 5: 在 app.py 注册中间件**

Edit `/Users/baoyu/Documents/GitHub/deerfllow-BY/backend/app/gateway/app.py`:

找到 `app = FastAPI(...)` 行之后,加入:

```python
from app.gateway.rate_limit import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware, max_requests=120, window_seconds=60)
```

(120 req/min 起步,可后续通过 config.yaml 调)

- [ ] **Step 6: 跑测试确认通过**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/backend
PYTHONPATH=. uv run pytest tests/test_rate_limit.py -v
```

Expected: 2 个测试全部通过

- [ ] **Step 7: 跑全量测试防回归**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/backend
PYTHONPATH=. uv run pytest -q 2>&1 | tail -10
```

Expected: 通过,无新增失败

- [ ] **Step 8: 重启 docker 容器加载新中间件**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
docker compose -f docker/docker-compose.yaml restart gateway
sleep 5
curl -s http://localhost:2026/api/health  # 验证仍可访问
```

Expected: 200 响应

- [ ] **Step 9: 提交**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git add backend/app/gateway/rate_limit.py backend/app/gateway/app.py backend/tests/test_rate_limit.py
git commit -m "feat(gateway): add per-IP rate limit middleware (in-memory, 120 req/min default)"
```

---

## Task P2-1: 前端添加 Vitest 测试框架

**Files:**
- Modify: `/Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/package.json`
- Create: `/Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/vitest.config.ts`
- Create: `/Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/src/test/setup.ts`

- [ ] **Step 1: 读 package.json 现有 scripts 块**

Read `/Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/package.json` 全文,定位 `scripts` 块和 `devDependencies`。

- [ ] **Step 2: 决定 vitest 版本**

选 `vitest@^2.0.0`(对应 Vite 6,与 Next.js 16 + pnpm 10 兼容)。

- [ ] **Step 3: 写失败"smoke"测试,确认框架未配置**

新建 `/Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/src/test/smoke.test.ts`:

```ts
import { describe, it, expect } from "vitest";

describe("vitest smoke", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/frontend
pnpm vitest run src/test/smoke.test.ts
```

Expected: 命令失败(`vitest: not found` 或类似)

- [ ] **Step 4: 添加 vitest 依赖**

Edit: `/Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/package.json`

在 `devDependencies` 块添加:
```json
    "vitest": "^2.1.0",
    "@vitejs/plugin-react": "^4.3.0",
    "happy-dom": "^15.0.0"
```

在 `scripts` 块添加:
```json
    "test": "vitest run",
    "test:watch": "vitest"
```

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/frontend
pnpm install
```

Expected: 安装成功,`node_modules/.bin/vitest` 存在

- [ ] **Step 5: 创建 vitest 配置**

新建 `/Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "happy-dom",
    globals: false,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    exclude: ["node_modules", ".next", "**/*.test.mjs"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

新建 `/Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/src/test/setup.ts`:

```ts
// Global test setup. Currently empty — extend as patterns emerge.
```

- [ ] **Step 6: 跑测试确认通过**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/frontend
pnpm test
```

Expected: 1 passed

- [ ] **Step 7: 修改 `pnpm check` 包含 test**

Edit `/Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/package.json` 的 `scripts`:

old_string:
```json
    "check": "eslint . --ext .ts,.tsx && tsc --noEmit",
```

new_string:
```json
    "check": "eslint . --ext .ts,.tsx && tsc --noEmit && vitest run",
```

- [ ] **Step 8: 提交**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git add frontend/package.json frontend/vitest.config.ts frontend/src/test/
git commit -m "test(frontend): add vitest with happy-dom environment"
```

---

## Task P2-2: 为 core/ 工具函数写首批单元测试

**Files:**
- Create: 多个 `*.test.ts` 文件

**目标:** 选择有清晰输入输出、不依赖 React 渲染的工具函数,先建立覆盖率基线。

- [ ] **Step 1: 列出可测试的纯函数文件**

Run:
```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/src/core
find . -name "*.ts" -not -name "*.test.ts" -not -name "index.ts" -not -path "*/api/*" -not -path "*/hooks/*" 2>/dev/null | head -20
```

挑出 3-5 个**无 React 依赖、无 fetch 调用**的纯函数文件,例如:
- `core/utils/*` (如有)
- `core/i18n/utils.ts` (如有)
- `core/messages/normalize.ts`(如有)

- [ ] **Step 2: 选第一个目标文件,写测试**

示例 — 假设 `frontend/src/core/utils/format.ts`:

新建 `frontend/src/core/utils/format.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { formatDate, truncate } from "./format";

describe("formatDate", () => {
  it("formats ISO date as YYYY-MM-DD", () => {
    expect(formatDate("2026-05-28T10:00:00Z")).toBe("2026-05-28");
  });
});

describe("truncate", () => {
  it("returns text unchanged when shorter than limit", () => {
    expect(truncate("hello", 10)).toBe("hello");
  });
  it("truncates with ellipsis when over limit", () => {
    expect(truncate("hello world", 5)).toBe("hello…");
  });
});
```

(具体函数和签名按实际挑出的文件调整。)

- [ ] **Step 3: 跑测试**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/frontend
pnpm test
```

Expected: 新增测试通过

- [ ] **Step 4: 重复 Step 2-3 覆盖 3-5 个文件**

每个文件一个 commit:

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git add frontend/src/core/<path>/<file>.test.ts
git commit -m "test: cover <file> with vitest"
```

- [ ] **Step 5: 验证 check 通过**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/frontend
pnpm check
```

Expected: eslint + tsc + vitest 全部通过

---

## Task P2-3: 拆分 memory-settings-page.tsx (1006 行 → 多个 <300 行)

**Files:**
- Modify: `/Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/src/components/workspace/settings/memory-settings-page.tsx`
- Create: 多个新组件

**背景:** 此文件 1006 行,违反 `web/coding-style.md` "200-400 行典型, 800 行最大" 的硬性约束。

- [ ] **Step 1: 读全文,识别子组件**

Read `/Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/src/components/workspace/settings/memory-settings-page.tsx` 全文,识别可拆分的子组件。典型拆分点:
- `<FactsList>` — 事实列表渲染
- `<MemoryContextCard>` — context 三段(workspace/personal/topOfMind)
- `<DeleteFactButton>` — 抽取删除 + undo toast 逻辑
- `<MemoryExportButton>` — 导出
- `<MemoryHeader>` — 头部

- [ ] **Step 2: 选第一个子组件,新建文件**

例:新建 `frontend/src/components/workspace/settings/memory/facts-list.tsx`(子目录)将 `<FactsList>` 提取出来。

**重要:** 使用相对路径,与父级一样的"use client"等。**不要改行为**,只搬代码。

- [ ] **Step 3: 在父文件中 import 新组件,删除重复代码**

Edit `memory-settings-page.tsx`,删除本地 `<FactsList>` 实现,改为 `import { FactsList } from "./memory/facts-list";` 并在 JSX 中使用。

- [ ] **Step 4: 跑前端 check**

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY/frontend
pnpm check
```

Expected: 通过

- [ ] **Step 5: 重复 Step 2-4 拆 3-4 个子组件**

每个子组件一个 commit:

```bash
cd /Users/baoyu/Documents/GitHub/deerfllow-BY
git add frontend/src/components/workspace/settings/
git commit -m "refactor: extract <ComponentName> from memory-settings-page"
```

- [ ] **Step 6: 最终验证文件大小**

```bash
wc -l /Users/baoyu/Documents/GitHub/deerfllow-BY/frontend/src/components/workspace/settings/memory-settings-page.tsx
```

Expected: < 400 行

- [ ] **Step 7: 在浏览器手动验证页面无 regression**

> 提示: 本任务需要 dev server。`pnpm dev` 在容器内运行,本机浏览器访问 `http://localhost:2026/workspace/settings/memory`,确认:
> - 事实列表正常显示
> - 删除 + undo toast 正常
> - context 三段正常编辑
> - 导出按钮正常

(如果无浏览器,改用 `curl` 抓取页面,确保不返回 500)

---

## Self-Review

**1. Spec coverage(对照原分析报告的问题):**

| 原报告问题 | 对应任务 | 状态 |
|----------|---------|------|
| P0-1 凭据硬编码 | P0-3, P0-4, P0-5 | ✅ |
| P0-2 应 ignore 被追踪 | P0-1, P0-2 | ✅ |
| P0-3 .env 凭据 | P0-6(rotate 提示,本地不提交) | ✅ |
| P1-4 async TODO 6 项 | P1-1, P1-2, P1-3(覆盖 3 项;subagent/docker 暂不改) | ✅ |
| P1-5 rate limiting | P1-4 | ✅ |
| P1-6 前端无测试 | P2-1, P2-2 | ✅ |
| P1-7 超大文件 | P2-3(只拆 1 个,其他留独立 plan) | ✅ |
| P2-9 prompt-input.tsx TODO 注释 | 不在本计划,简单删除可单 commit 解决 | 留作单独 |

**2. Placeholder scan:**

- ✅ 没有 "TBD"、"TODO"、"implement later"
- ✅ 每个任务都有具体文件路径、具体代码或修改说明
- ✅ Step 描述到代码级别(可执行)
- ⚠️ P1-3 三个 community 文件的修改细节(Step 4-5)是"渐进式修改",没有展示具体 diff。这是因为三处调用点不同,无法预写全部 diff;在执行时按"现有测试通过"为成功标准。如果需要更严格的占位,可在执行时补具体 diff。

**3. Type consistency:**

- `RateLimitMiddleware` 在 P1-4 Step 4 中定义,在 Step 2 测试中引用 → 一致
- `E2E_EMAIL` / `E2E_PASSWORD` 在 P0-3 中定义,在 P0-4 中复用 → 一致
- `vitest` 命令在 P2-1 配置,在 P2-2 复用 → 一致

**4. 范围风险点:**

- P0-5 `git filter-repo` 是高风险操作(改写历史)。计划中**明确标记需用户授权**。
- P1-3 community tools 重构可能破坏外部 API 行为。**步骤中以"现有测试通过"为成功标准,而不是新增测试**。
- P1-2 sandbox 修改可能影响运行中容器。需在 P2-3 Step 7 手动验证之外,中间步骤也可以考虑 `make stop && make dev` 重启验证,但作为可选。

---

## 执行说明

**计划执行顺序(P0 → P1 → P2):**

1. **P0 阶段(7 个任务)**: 全部 1-2 小时内可完成,每步独立 commit。P0-5 (filter-repo) 需要用户授权才能执行。
2. **P1 阶段(4 个任务)**: 约半天。每个任务独立可回滚。
3. **P2 阶段(3 个任务)**: 约 1-2 天。是基础设施和重构,可分多天推进。

**执行时本地状态检查清单:**

执行任何 commit 前,先 `git status` 确认工作树干净。
执行 P1-2 / P1-3 后,考虑 `docker compose restart gateway langgraph`。
执行 P0-5 前,确认 `backup/main-before-history-rewrite` 分支已建好。
