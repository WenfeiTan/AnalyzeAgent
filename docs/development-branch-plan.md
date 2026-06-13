# Analyze Agent Development Execution Plan

## 0. 文档用途

本文档是 Codex 在多轮对话和上下文压缩后继续开发的执行手册，不是多人团队协作方案。

使用规则：

1. 开始任何开发前，先阅读：
   - `docs/development-status.md`
   - 本文档
   - 当前分支对应的 `docs/development-logs/<branch-name>.md`
2. 以 Git 状态、测试结果和日志中的 evidence 为准，不依赖对话记忆判断进度。
3. 只按本文定义的顺序推进；除非用户明确修改计划，不自行并行创建多个开发分支。
4. 每次开始、关键决策、遇到阻塞、完成测试和合并时，立即更新开发日志。
5. 回答用户“当前进度”时，先读取 `development-status.md` 和当前分支日志，再检查 Git，不凭记忆回答。
6. 分支完成后必须更新总状态，才能进入下一个分支。

## 1. 开发方式

- 所有开发直接在当前 workspace 进行：
  `/Users/wenfeitan/Desktop/vibecoding/AnalyzeAgent`
- 不创建额外 workspace 或 Git worktree。
- 使用 `main` 作为稳定主分支。
- 不创建长期 `develop` 分支。
- 分支统一使用 `codex/` 前缀。
- 由 Codex 单一开发流推进，采用严格顺序开发。
- 每个分支从最新 `main` 创建，完成测试后 squash merge 回 `main`。

采用严格顺序开发的原因：

- 当前仓库基本为空，基础工程和数据契约尚未建立。
- 前几个分支会定义后续模块共同依赖的 models、ports 和配置。
- vector-mcp 的真实 payload 及 ES Agent 最终契约尚未确定。
- 单代理在同一 workspace 中并行分支没有实际收益，还会增加状态恢复和合并成本。

## 2. 分支顺序

### 2.1 `codex/bootstrap-adk-python`

目标：建立可运行的 Python、ADK 和 Gemini 工程骨架。

交付物：

- Python 3.11+ 项目结构。
- 依赖和开发命令。
- Google ADK agent 基础入口。
- Gemini API key 和 model ID 环境配置。
- 配置校验及 `.env.example`。
- pytest、lint 和基础 CI 命令。
- 最小 smoke test。

完成门槛：

- 项目可安装和启动。
- 无 API key 时给出清晰配置错误。
- 基础测试通过。

### 2.2 `codex/domain-contracts`

目标：冻结第一版核心数据模型和业务边界。

交付物：

- Initial/Updated request models。
- `clear_fields`、`keywords`、`reused_mappings` response models。
- asset、attribute、field mapping feedback models。
- `accept` / `reject` feedback decision。
- normalized chunk model。
- error models。
- confidence engine 和初始评分配置。

完成门槛：

- 所有模型均可进行严格 schema validation。
- confidence score 由代码计算，Gemini 不能直接决定最终分数。
- schema 单元测试通过。

### 2.3 `codex/sqlite-revisions`

目标：由代码可靠管理 requirement history 和 revisions。

交付物：

- SQLite schema 和 repository。
- requirement、revision、feedback 和 output snapshot 持久化。
- latest revision 查询。
- immutable revision 写入。
- transaction 和 revision number 唯一约束。
- repository 单元测试和并发冲突测试。

完成门槛：

- revision ID、number 和顺序完全由代码管理。
- Gemini 不生成或选择 revision。
- 可通过 `requirement_id` 恢复完整历史。

### 2.4 `codex/knowledge-retriever-contract`

目标：定义 Analyze Agent 与外部 Knowledge Base 检索能力之间的稳定边界。

交付物：

```text
KnowledgeBaseRetriever.search(text)
  -> list[KnowledgeChunk]
```

- Retriever port。
- `KnowledgeChunk` typed model。
- timeout 和 retriever error 定义。
- 外部响应归一化边界。

完成门槛：

- Domain/application 层不依赖 MCP SDK。
- 调用方只依赖 `text in -> chunks out`。

### 2.5 `codex/fake-knowledge-retriever`

目标：在真实 vector-mcp payload 未知时支持完整开发和测试。

交付物：

- `FakeKnowledgeBaseRetriever`。
- 固定 fake payload fixtures。
- 空 chunks 场景。
- 完整 mapping chunks。
- 部分 mapping chunks。
- 无有效证据 chunks。
- timeout 和非法响应模拟。

明确不包含：

- 不实现假 MCP server。
- 不复制 vector search 或 cosine similarity。
- 不开发真实 vector-mcp adapter。

完成门槛：

- Fake Retriever 可通过依赖注入替换。
- 所有预设场景均有测试。

### 2.6 `codex/initial-analysis`

目标：完成新 requirement 的分析工作流。

交付物：

- `analyze_initial` application operation。
- 英文 requirement 校验。
- Gemini structured analysis。
- `analyzed_requirement`。
- clear field 提取。
- keyword 提取和规范化。
- confidence 和 priority 计算。
- 首个 requirement revision 写入。

完成门槛：

- Knowledge Base 为空时仍可正常输出。
- 输出符合正式 response schema。
- 不生成无证据的 asset 或 attribute。

### 2.7 `codex/knowledge-reuse`

目标：根据 Fake Retriever 返回的 chunks 复用历史成功信息。

交付物：

- chunk evidence extraction。
- success case reconstruction。
- field -> attribute -> asset mapping 验证。
- full、partial 和 rejected reuse。
- `reused_mappings` 输出。
- supporting chunk evidence。

完成门槛：

- 只有可回溯到 chunk 的 mapping 才能复用。
- 相似 chunk 不能仅凭 similarity 获得 high confidence。
- 无证据内容不会被 Gemini 补全成事实。

### 2.8 `codex/update-analysis`

目标：完成用户补充信息和搜索反馈驱动的更新工作流。

交付物：

- `analyze_update` application operation。
- 根据 `requirement_id` 读取 latest revision。
- 解析英文 supplemental information。
- 处理 asset、attribute 和 field mapping feedback。
- `accept` / `reject` 行为。
- negative constraints。
- 完整新英文 requirement 生成。
- structured change set 和 `change_summary`。
- 新 revision 持久化。

完成门槛：

- 不通过字符串简单拼接生成新 requirement。
- rejected 结果不会被无理由重复推荐。
- 原始 supplemental information、feedback 和 change set 均可追踪。

### 2.9 `codex/adk-integration`

目标：将两个 application operations 接入 Google ADK。

交付物：

- ADK Analyze Agent。
- Gemini instruction 和 structured output registration。
- `analyze_initial` 和 `analyze_update` 两个明确入口。
- 稳定的 `search_knowledge_base(text)` tool。
- 通过依赖注入将该 tool 绑定到 Fake Retriever。
- Agent/application integration tests。

当前架构：

```text
ADK Analyze Agent
  -> analyze_initial / analyze_update
  -> search_knowledge_base tool
  -> KnowledgeBaseRetriever
  -> FakeKnowledgeBaseRetriever
```

完成门槛：

- Agent 不直接依赖 Fake Retriever implementation。
- 后续替换真实 adapter 时不修改 prompt、domain 或 application workflow。

### 2.10 `codex/observability-hardening`

目标：补齐可运行性、降级和安全能力。

交付物：

- Structured logging。
- request、requirement 和 revision correlation IDs。
- stage latency 和调用指标。
- Gemini 和 Retriever timeout/retry。
- schema repair 限制。
- 敏感信息脱敏。
- prompt injection 防护。
- 回归测试和运行说明。

完成门槛：

- Gemini 或 Retriever 故障不会生成伪高置信度结果。
- API key 不进入日志或代码库。
- Initial/Updated 两条路径均有端到端回归测试。

### 2.11 `codex/vector-mcp-adapter`

状态：延后，等待真实 vector-mcp 请求和响应样例。

目标：用真实外部 service adapter 替换 Fake Retriever。

交付物：

- vector-mcp client/ADK tool binding。
- 真实 payload 到 `KnowledgeChunk` 的归一化。
- timeout、retry 和错误映射。
- contract tests。
- Fake/real adapter 配置切换。

完成门槛：

- 不修改 domain、application workflow 或 Agent instruction。
- Fake Retriever 测试继续保留。
- 真实 service 的空结果和异常路径通过联调。

## 3. 状态恢复协议

每次恢复开发时按以下顺序执行：

1. 读取 `docs/development-status.md`，确认当前阶段、当前分支和下一动作。
2. 读取当前分支的详细日志，确认已完成内容、未完成内容、决策和已执行测试。
3. 运行 `git status --short --branch`，核对实际分支和工作区状态。
4. 查看当前分支相对 `main` 的 diff 和最近提交。
5. 运行日志中标记为最后通过的最小测试，确认环境和代码状态仍一致。
6. 从日志的 `Next action` 继续，不重新猜测任务范围。

如果日志与 Git/代码不一致：

- Git 和代码事实优先。
- 在继续开发前修正日志。
- 不删除无法解释的改动；先判断是否为用户或之前会话留下的工作。

## 4. 开发日志管理

### 4.1 文件结构

```text
docs/
  development-branch-plan.md
  development-status.md
  development-logs/
    README.md
    codex-bootstrap-adk-python.md
    codex-domain-contracts.md
    ...
```

`development-status.md` 是总索引，供用户快速查看整体进度。

每个 `development-logs/<branch-name>.md` 是对应分支的 append-oriented 详细日志。分支日志在分支开始时创建，不预先生成空日志。

### 4.2 总状态字段

总状态必须记录：

- 最后更新时间。
- 当前 Git 分支。
- 当前分支状态：`pending`、`in_progress`、`blocked`、`completed`、`merged`、`deferred`。
- 总体完成度，以完成分支数表示，不使用主观百分比。
- 当前目标。
- 最近完成事项。
- 下一动作。
- 当前阻塞。
- 最近验证命令及结果。
- 各分支状态表。

### 4.3 分支日志字段

每个分支日志必须包含：

- Branch。
- Status。
- Started/Completed/Merged 时间。
- Base commit 和最终 commit。
- Objective。
- Scope。
- Decisions。
- Work log。
- Files changed。
- Tests/checks。
- Known limitations。
- Blockers。
- Next action。
- Completion checklist。

Work log 使用带时间的追加记录：

```markdown
## Work Log

### YYYY-MM-DD HH:mm Asia/Shanghai

- Action:
- Result:
- Evidence:
- Decision:
- Next:
```

日志只记录可验证事实，不粘贴大量终端输出，不记录 API key、完整敏感 requirement 或其他 secret。

### 4.4 强制更新时间点

必须更新日志的节点：

1. 创建或切换到分支后。
2. 完成初次代码勘察后。
3. 修改实现方案或公共契约后。
4. 每完成一个交付物后。
5. 测试失败并确认原因后。
6. 发现阻塞或外部依赖后。
7. 测试全部通过后。
8. commit、merge 或结束当前开发回合前。

每次日志更新同时维护 `development-status.md`，保证用户无需阅读所有分支日志即可了解进度。

## 5. 分支与合并规则

每个分支：

- 只处理该分支定义的目标。
- 包含对应测试。
- 不夹带无关重构。
- 修改 schema 时同步更新文档和 contract tests。
- 持续更新当前分支日志和总状态。
- 合并前从最新 `main` 同步并通过完整测试。

合并策略：

- 使用 squash merge。
- 一个分支对应一个清晰 commit/PR 主题。
- `main` 始终保持可安装、可测试。
- 后续分支从合并后的最新 `main` 创建。
- 不建立长依赖链，不同时长期维护多个未合并分支。
- 合并完成后将分支状态标记为 `merged`，记录 merge/squash commit，并创建下一个分支。

## 6. 完成与进度判定

分支只有满足以下条件才可标记为 `completed`：

- 分支目标和交付物全部完成。
- 完成门槛中的测试通过。
- `git diff --check` 通过。
- 没有未记录的已知限制或阻塞。
- 分支日志 completion checklist 全部勾选。

只有代码已合入 `main` 后才标记为 `merged`。

总体进度按分支状态统计：

```text
merged branches / currently applicable branches
```

`codex/vector-mcp-adapter` 在真实接口不可用期间状态为 `deferred`，不计入当前可完成分支的分母。

## 7. 近期执行顺序

当前建议立即按以下顺序推进：

1. `codex/bootstrap-adk-python`
2. `codex/domain-contracts`
3. `codex/sqlite-revisions`
4. `codex/knowledge-retriever-contract`
5. `codex/fake-knowledge-retriever`

完成这五个基础分支后继续按第 2 节顺序开发，不启动并行路线。
