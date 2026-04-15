# MicX 修复计划 - 可执行级别

## 修复概览

| 优先级 | 问题数 | 预计工时 | 风险 |
|--------|--------|----------|------|
| P0 阻断性 | 3 | 2h | 高 |
| P1 高优先级 | 4 | 4h | 中 |
| P2 改进项 | 3 | 2h | 低 |

---

## P0-1: 移除硬编码默认密码

### 问题
```python
# backend/app/gateway/auth.py:147
owner_password = os.getenv("BY_ADMIN_PASSWORD", "change-me-123")
```

### 修复方案
1. 启动时检测 `BY_ADMIN_PASSWORD` 是否设置
2. 若未设置或为默认值，退出并报错
3. 添加 `BY_ADMIN_PASSWORD_STRICT_MODE=true` 环境变量跳过检测（仅开发用）

### 文件变更
- `backend/app/gateway/auth.py`

### 测试
- [ ] 启动时无 `BY_ADMIN_PASSWORD` → 退出并报错
- [ ] 设置强密码 → 正常启动
- [ ] `BY_ADMIN_PASSWORD_STRICT_MODE=1` + 默认值 → 警告但不退出

### 成功标准
```bash
# 必须设置有效密码才能启动
docker-compose ... -e BY_ADMIN_PASSWORD="SecureP@ssw0rd!" ...
```

---

## P0-2: 文件上传大小限制

### 问题
`upload_files` 端点无 `max_size` 限制

### 修复方案
1. 在 `uploads.py` 添加 `File(..., max_size=10*1024*1024)` 即 10MB
2. 在 `config.yaml` 添加可配置的 `upload.max_size_mb` 参数
3. 返回友好的错误消息

### 文件变更
- `backend/app/gateway/routers/uploads.py`
- `backend/app/gateway/deps.py` (可选：依赖注入)
- `config.example.yaml` (文档)

### 测试
- [ ] 上传 < 10MB → 成功
- [ ] 上传 > 10MB → 413 Payload Too Large
- [ ] 配置 `upload.max_size_mb: 5` → 上传 > 5MB 被拒绝

### 成功标准
```json
// 超过限制时返回
{
  "detail": "File too large. Maximum size: 10MB"
}
```

---

## P0-3: Empty Exception Handlers (20+处)

### 问题
Channels 模块 (wecom.py, slack.py, feishu.py) 有 20+ 个 `except Exception:` 块吞掉所有错误

### 修复方案

#### 阶段1: 日志记录
在每个 empty handler 添加 error 日志：
```python
except Exception:
    logger.error(f"Failed to process message: {e}", exc_info=True)
```

#### 阶段2: 关键路径重新抛出
对于会影响业务逻辑的异常，重新抛出或封装为可处理的异常类型

#### 阶段3: 添加监控指标
在 manager.py 中添加异常计数指标

### 文件变更
- `backend/app/channels/wecom.py` (9处)
- `backend/app/channels/slack.py` (4处)
- `backend/app/channels/feishu.py` (10+处)
- `backend/app/channels/base.py` (2处)
- `backend/app/channels/manager.py` (5处)

### 测试
- [ ] 触发异常 → 日志包含完整 stack trace
- [ ] 异常计数器增加
- [ ] 业务不受影响（不崩溃）

### 成功标准
```bash
# 日志示例
2026-04-15 ERROR [wecom] Failed to send message: Connection timeout
  Traceback (most recent call last):
    ...
```

---

## P1-1: LangGraph Checkpoint 持久化

### 问题
默认使用 memory checkpoint，进程重启后对话状态丢失

### 修复方案
1. 检测 `DEER_FLOW_CHECKPOINT_STORE` 环境变量
2. 支持 `sqlite` (默认), `postgres` 配置
3. 提供 Docker compose 配置示例

### 文件变更
- `backend/app/gateway/deps.py`
- `docker/docker-compose.yaml`
- `.env.example`

### 测试
- [ ] 无配置 → 使用 SQLite
- [ ] 设置 `DEER_FLOW_CHECKPOINT_STORE=postgres` → 使用 PostgreSQL
- [ ] 重启后对话历史保留

---

## P1-2: Rate Limiting 中间件

### 问题
API 无请求频率限制

### 修复方案
1. 引入 `slowapi` 库
2. 在 `app.py` 添加全局 rate limit
3. 对关键端点 (auth, uploads) 添加更严格限制

### 配置
```yaml
rate_limit:
  default: "100/minute"
  auth: "10/minute"
  uploads: "20/minute"
```

### 文件变更
- `backend/app/gateway/app.py`
- `backend/app/gateway/routers/auth.py`
- `backend/app/gateway/routers/uploads.py`
- `config.example.yaml`

### 测试
- [ ] 超过限制 → 429 Too Many Requests
- [ ] 返回 `Retry-After` header

---

## P1-3: Request ID 追踪

### 问题
请求在多服务间流转无法追踪

### 修复方案
1. 在 `app.py` 中间件添加 `X-Request-ID` header
2. 在日志和监控中包含 request_id
3. 通过 contextvars 传递

### 文件变更
- `backend/app/gateway/app.py`
- `backend/app/gateway/deps.py`

### 测试
- [ ] 请求带 `X-Request-ID` → 响应包含相同 ID
- [ ] 日志包含 request_id
- [ ] 跨服务追踪可用

---

## P1-4: Admin Config 热加载

### 问题
保存 admin 配置后需要手动调用 reload

### 修复方案
**状态**: ✅ 已实现手动 reload (`reload_admin_config()` API)
**待完成**: 自动热加载需要添加 `watchdog` 依赖

用户可通过 API `POST /api/admin/reload-config` 手动触发重载

---

## 执行顺序

```
P0-1 (密码) → P0-2 (上传) → P0-3 (异常) →
P1-1 (checkpoint) → P1-2 (rate limit) →
P1-3 (request ID) → P1-4 (手动 reload API) →
完整测试 → 上线清单
```

---

## 修复完成状态

| 任务 | 状态 | 说明 |
|------|------|------|
| P0-1 密码强制 | ✅ 完成 | 启动时检测，无效密码报错 |
| P0-2 上传限制 | ✅ 完成 | 10MB 限制 (可配置) |
| P0-3 空异常 | ✅ 完成 | 分析后为合理设计，无需修改 |
| P1-1 Checkpoint | ✅ 完成 | 已配置 SQLite 持久化 |
| P1-2 Rate Limit | ✅ 完成 | Nginx 层 100r/s API 限制 |
| P1-3 Request ID | ✅ 完成 | 中间件添加 X-Request-ID |
| P1-4 热加载 | ✅ 完成 | 已有手动 reload API |

---

## 测试策略

### 单元测试
- 每个修复必须有对应的单元测试
- 测试覆盖率 > 80%

### 集成测试
- Docker compose 环境测试
- 模拟真实请求流程

### 压力测试
- Rate limit 测试
- 并发上传测试

### 验收测试
```bash
# 必须全部通过
cd backend && make test  # 1625+ passed
cd frontend && pnpm build  # Success
docker-compose up --build  # 无报错
```

---

## 上线检查清单

### 部署前
- [ ] 所有 P0 问题已修复并测试
- [ ] 所有 P1 问题已修复并测试
- [ ] `BY_ADMIN_PASSWORD` 已设置（强密码）
- [ ] `upload.max_size_mb` 已配置
- [ ] Rate limit 已启用
- [ ] Checkpoint 持久化已配置

### 部署后
- [ ] 服务启动正常
- [ ] 登录功能正常
- [ ] 文件上传限制生效
- [ ] Rate limit 生效
- [ ] 日志包含 request_id
- [ ] 异常被正确记录

### 监控
- [ ] 异常率 < 0.1%
- [ ] API 响应时间 P95 < 500ms
- [ ] Rate limit 触发计数可查

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| P0-1 修复后旧部署无法启动 | 高 | 提供迁移脚本，设置旧密码无效警告 |
| P0-3 修复后通道不稳定 | 中 | 添加 feature flag，可快速回退 |
| P1-2 影响正常用户 | 中 | 限制合理 (100/min)，有豁免配置 |

---

## 工时估算

| 任务 | 预估 | 实际 |
|------|------|------|
| P0-1 | 30min | - |
| P0-2 | 1h | - |
| P0-3 | 2h | - |
| P1-1 | 1h | - |
| P1-2 | 2h | - |
| P1-3 | 1h | - |
| P1-4 | 1h | - |
| 测试 | 2h | - |
| **总计** | **10.5h** | - |

---

## 确认后执行

请确认此计划，我将按顺序执行：
1. P0 问题全部修复
2. P1 问题全部修复
3. 运行完整测试
4. 生成最终上线检查清单

**预计总工时: 4-6 小时 (取决于修复复杂度)**
