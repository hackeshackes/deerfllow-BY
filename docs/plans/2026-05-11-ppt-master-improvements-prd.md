# PPT Master 服务改进 PRD

## 1. 背景与目标

### 1.1 问题描述

当前 PPT Master 服务存在以下问题：

| 问题 | 当前行为 | 影响 |
|------|---------|------|
| LLM 超时无控制 | `model.invoke()` 无限阻塞 | ReadTimeout 持续等待，用户体验差 |
| 无重试机制 | 一次失败即 fallback | 临时故障无法恢复 |
| 静默失败 | `except Exception: pass` | 错误被吞掉，无法排查 |
| Fallback 质量差 | 固定模板内容 | 生成 PPT 无 AI 价值 |
| 无进度跟踪 | 长时间无反馈 | 用户以为卡死 |
| 无任务持久化 | 中断即失败 | 无法续跑 |

### 1.2 目标

在不对系统其他部分造成影响的前提下，提升 PPT Master 的：
- **可靠性**：超时控制 + 重试机制
- **可观测性**：任务状态 + 进度跟踪
- **质量保证**：降级警告 + 内容验证

---

## 2. 方案设计

### 2.1 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                      PPTMasterService                           │
├─────────────────────────────────────────────────────────────────┤
│  1. LLM 调用层 (_generate_outline)                              │
│     ├── 超时控制 (默认 120s)                                    │
│     ├── 重试机制 (指数退避, 最多3次)                            │
│     ├── 错误分类 (可重试 vs 不可重试)                            │
│     └── 降级策略 (fallback with warning)                        │
│                                                                  │
│  2. 任务状态层 (PPTTaskState)                                  │
│     ├── 持久化 (JSON 文件, TTL 24h)                            │
│     ├── 进度跟踪 (phase + percent)                              │
│     ├── 中断恢复 (断点续跑)                                     │
│     └── 超时取消 (deadline)                                     │
│                                                                  │
│  3. 质量保证层                                                 │
│     ├── 输出验证 (JSON schema)                                   │
│     ├── 最小内容量 (slides ≥ 3)                                 │
│     ├── 内容完整性 (title + bullets)                            │
│     └── 降级标记 (is_fallback flag)                             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 配置项

**config.yaml 新增配置**：
```yaml
ppt_master:
  timeout: 120           # LLM 单次调用超时(秒)
  max_retries: 3         # 最大重试次数
  base_delay: 2.0        # 初始重试延迟(秒)
  retry_multiplier: 2.0   # 退避系数
  max_delay: 60.0       # 最大延迟(秒)
  enable_fallback: true   # 是否启用 fallback
  task_ttl: 86400       # 任务状态保留时间(秒, 默认24h)
  task_dir: /tmp/ppt-master-tasks  # 任务状态目录
```

### 2.3 错误分类

| 错误类型 | 示例 | 处理策略 |
|---------|------|---------|
| **可重试** | ReadTimeout, RateLimit, 5xx | 指数退避重试 |
| **不可重试** | AuthError, InvalidRequest, 400 | 立即 fallback |

### 2.4 任务状态

```python
@dataclass
class PPTTaskState:
    task_id: str
    topic: str
    phase: str  # "outline" | "building" | "finalize" | "complete" | "failed"
    progress: float  # 0.0 - 1.0
    attempts: int
    max_attempts: int
    error: str | None
    is_fallback: bool
    started_at: float
    updated_at: float
    output_path: str | None
```

### 2.5 API 变更

**新增 Endpoint**：
```bash
GET /api/ppt/task/{task_id}/status
# 返回: PPTTaskState

POST /api/ppt/task/{task_id}/cancel
# 返回: {"success": true, "message": "Task cancelled"}

GET /api/ppt/task/{task_id}/status/stream
# SSE 流式进度
```

**原有 API 变更**：
```bash
POST /api/ppt/generate
# 新增响应字段: task_id, warning(可选)

# 成功响应:
{
    "success": true,
    "task_id": "abc123",
    "status": "completed",
    "message": "PPT generated successfully",
    "is_fallback": false,  # 新增
    "warning": null         # 新增
}

# 降级响应:
{
    "success": true,
    "task_id": "abc123",
    "status": "completed_with_fallback",
    "message": "PPT generated with basic template",
    "is_fallback": true,   # 新增
    "warning": "LLM timeout after 3 attempts. Used basic template."  # 新增
}
```

---

## 3. 实施计划

### 阶段 1：配置 + 数据结构
- [ ] 1.1 在 `config.yaml` 添加 ppt_master 配置
- [ ] 1.2 创建 `PPTTaskState` dataclass
- [ ] 1.3 创建 `PPTMasterConfig` 配置类

### 阶段 2：超时 + 重试机制
- [ ] 2.1 实现 `_classify_error()` 错误分类
- [ ] 2.2 实现 `_retry_with_backoff()` 重试装饰器
- [ ] 2.3 实现 `_call_llm_with_retry()` 带超时的 LLM 调用
- [ ] 2.4 替换原 `create_chat_model().invoke()`

### 阶段 3：任务状态持久化
- [ ] 3.1 实现 `_save_task_state()` 状态保存
- [ ] 3.2 实现 `_load_task_state()` 状态加载
- [ ] 3.3 实现 `_cleanup_old_tasks()` TTL 清理
- [ ] 3.4 在 `generate()` 中集成状态更新

### 阶段 4：进度跟踪 API
- [ ] 4.1 新增 `GET /api/ppt/task/{task_id}/status`
- [ ] 4.2 新增 `POST /api/ppt/task/{task_id}/cancel`
- [ ] 4.3 修改 `generate` 返回 task_id

### 阶段 5：质量验证 + 降级警告
- [ ] 5.1 实现 `_validate_outline()` 输出验证
- [ ] 5.2 实现 `_fallback_with_warning()` 带警告的降级
- [ ] 5.3 添加详细日志

### 阶段 6：测试
- [ ] 6.1 单元测试 (超时, 重试, 错误分类)
- [ ] 6.2 集成测试 (Docker 环境)
- [ ] 6.3 功能测试 (完整 PPT 生成流程)

---

## 4. 测试计划

### 4.1 单元测试

```python
class TestPPTMasterRetry:
    def test_timeout_classification():
        # ReadTimeout -> 可重试

    def test_auth_error_not_retryable():
        # AuthError -> 不可重试

    def test_exponential_backoff():
        # delay = base * multiplier^attempt

    def test_fallback_triggered_after_max_retries():
        # 3次重试后 fallback

class TestPPTTaskState:
    def test_state_persistence():
        # 保存 -> 加载 -> 验证

    def test_state_cleanup_on_ttl():
        # 24h 前保留, 24h 后清理
```

### 4.2 功能测试

| 测试项 | 验证点 |
|-------|--------|
| 正常生成 | LLM 成功, 返回完整 PPT |
| 超时降级 | LLM 超时, 返回基础 PPT + warning |
| 重试成功 | 第一次超时, 第二次成功 |
| 进度查询 | task_id 查询返回正确状态 |
| 取消任务 | 正在生成的任务可取消 |
| 错误日志 | 失败原因记录完整 |

### 4.3 Docker 部署测试

```bash
# 1. 重新构建
docker-compose -f docker/docker-compose-dev.yaml build

# 2. 启动服务
docker-compose -f docker/docker-compose-dev.yaml up -d

# 3. 验证服务健康
curl http://localhost:2026/api/ppt/status

# 4. 测试 PPT 生成
curl -X POST http://localhost:2026/api/ppt/generate \
  -H "Content-Type: application/json" \
  -d '{"topic":"测试主题","num_slides":5}'

# 5. 验证任务状态 API
curl http://localhost:2026/api/ppt/task/{task_id}/status
```

---

## 5. 回滚计划

如遇问题，回滚方式：
1. **配置回滚**: 删除 `config.yaml` 中 `ppt_master` 配置段，使用默认值
2. **代码回滚**: `git revert` 本次改动
3. **服务重启**: `docker-compose restart`

---

## 6. 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 重试增加 API 调用成本 | 配置 `max_retries: 3` 控制上限 |
| 任务状态文件堆积 | TTL 24h 自动清理 |
| 代码复杂度增加 | 保持 Service 内聚，注释清晰 |
| Docker 构建时间增加 | 复用现有 layer |

---

## 7. 成功标准

- [ ] LLM 超时后自动重试 (最多3次)
- [ ] 重试失败后返回降级 PPT + warning
- [ ] 任务状态可查询
- [ ] 降级响应包含 `is_fallback: true`
- [ ] Docker 环境测试通过
- [ ] 所有原有功能不受影响
