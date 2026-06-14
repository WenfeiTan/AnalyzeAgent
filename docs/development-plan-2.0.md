# Analyze Agent Development Plan 2.0

## 0. 文档用途

本文档是 Analyze Agent 可视化开发及产品演示原型的顺序执行计划，也是
Codex 在多轮对话和上下文压缩后恢复开发状态的主要依据。

本计划继承 `docs/development-branch-plan.md` 中的以下规则：

- 直接在当前 workspace 开发，不创建额外 workspace 或 worktree。
- 使用 `main` 作为稳定分支，开发分支统一使用 `codex/` 前缀。
- 严格顺序开发；每个分支从最新 `main` 创建。
- 每个分支必须完成实现、测试、日志、状态更新和提交，再 squash merge 回
  `main`。
- 每次恢复开发时，先读取 `docs/development-status.md`、本文档和当前分支日志，
  然后核对 Git 状态。
- 遇到需要产品决策或缺少外部契约的真实阻塞时才询问用户。

## 1. 产品定位

本阶段交付一个本地运行的开发及产品演示原型，不作为生产系统部署。

目标用户可以：

1. 在浏览器中提交符合稳定 schema 的英文 Initial Requirement。
2. 查看 Analyze Agent 的真实工作阶段和最终分析结果。
3. 从本地历史记录选择 requirement，提交补充信息或搜索反馈，执行 Update
   workflow。
4. 选择明确标注的 Fake Knowledge Base 场景，演示空结果、完整复用、部分复用和
   故障降级。
5. 展开查看完整 request、response 和 trace payload，用于调试。

本阶段不包含：

- 登录、用户体系和权限管理。
- 公网部署、生产级扩缩容或高可用。
- 在页面中输入、保存或显示 Gemini API key。
- 真实 vector-mcp 接入。
- Elastic Search Agent 或完整 Asset Discovery 编排界面。
- 人工制造不真实的模型进度动画。

## 2. 技术方案

### 2.1 技术栈

Agent：

- Python 3.11+。
- Google ADK、Gemini adapters 和现有 application/domain layers。
- SQLite：继续使用当前 requirement/revision repository。
- 作为可独立测试和复用的 Python package/runtime，不启动额外网络服务。

Backend：

- Python 3.11+。
- FastAPI：独立 JSON API 和 Server-Sent Events server。
- Uvicorn：本地启动。
- 只负责 transport、job orchestration、API errors 和 Agent composition。

Frontend：

- React。
- Vite。
- TypeScript strict mode。
- 原生 `EventSource` 消费 SSE working-status events。
- Vitest 和 Testing Library。
- Playwright 验证浏览器关键路径。

选择该方案的原因：

- React 和 TypeScript 适合结构化 Initial/Update 表单、动态 feedback editor 和复杂结果
  展示。
- Vite 提供独立且轻量的前端开发、构建和测试环境。
- pnpm 提供可重复的 Frontend dependency lock 和 workspace-local installation。
- SSE 足以表达单向阶段状态，不需要 WebSocket。
- `frontend -> backend -> agent` 是唯一允许的依赖方向。
- Agent 不知道 Backend 或 Frontend；Backend 不知道 Frontend implementation。
- Frontend 只依赖版本化 HTTP/SSE contract，不直接依赖 Python package、Gemini、
  SQLite 或 Retriever implementation。

### 2.2 仓库结构和解耦边界

采用 monorepo 管理三个独立 workspace。Agent 是可复用 Python package，Backend 和
Frontend 是两个独立应用：

```text
AnalyzeAgent/
  agent/
    pyproject.toml
    uv.lock
    src/
      analyze_agent/
    tests/
    data/
  backend/
    pyproject.toml
    uv.lock
    src/
      analyze_api/
    tests/
  frontend/
    package.json
    pnpm-lock.yaml
    tsconfig.json
    vite.config.ts
    src/
    tests/
  docs/
  Makefile
  README.md
  .env.example
```

边界规则：

- Agent 拥有 domain models、confidence rules、application workflows、ADK entrypoint、
  Gemini adapters、Retriever ports/adapters、SQLite revisions、logging 和 resilience。
- Agent 不导入 FastAPI，不定义 HTTP route、CORS、SSE 或 Web job state。
- Backend 将 Agent 作为明确版本的 Python dependency，只通过 Agent public facade
  调用，不直接导入 `application/`、`domain/`、`ports/` 或 adapter implementation。
- Backend 拥有 FastAPI routes、API request/response DTO mapping、job registry、SSE
  transport、CORS 和 Web-specific error mapping。
- Backend 不渲染 HTML，不托管 frontend build output，不引用 TypeScript source。
- Frontend 不导入 Python 文件，不直接访问 SQLite，也不包含 Gemini 或 Retriever
  逻辑。
- Backend 默认运行于 `http://localhost:8000`。
- Frontend dev server 默认运行于 `http://localhost:5173`。
- Frontend 通过 `VITE_ANALYZE_API_BASE_URL` 配置 Backend 地址。
- Backend 仅对显式配置的本地 frontend origin 开启 CORS。
- API 使用 `/api/v1` 前缀；SSE 也属于同一版本化 contract。
- Backend OpenAPI document 是跨应用 contract 的 source of truth。
- Frontend 使用 OpenAPI 生成或校验 TypeScript API types，生成文件放在
  `frontend/src/api/generated/`，业务组件不得手写复制 Backend schema。
- Root `Makefile` 只负责编排安装、测试和同时启动两个独立进程，不承载业务代码。
- Agent、Backend 和 Frontend 可以分别安装和测试；Backend 和 Frontend 可以分别启动；
  Frontend 可以独立构建。
- 不创建 Agent HTTP service。未来 Asset Discovery orchestrator 可以直接使用 Agent
  package，或在其自身部署边界内包装 Agent。

现有 Python 工程将在独立分支中整体迁入 `agent/`。Backend 和 Frontend 从空骨架开始，
该迁移只改变工程布局和命令，不修改 Analyze Agent 行为。

### 2.3 运行结构

```text
Browser
  -> React + TypeScript Frontend
  -> versioned HTTP/SSE API
  -> FastAPI Backend
  -> Analysis Job Service
  -> Analyze Agent public API
  -> InitialAnalysisService / UpdatedAnalysisService
  -> Gemini adapters
  -> KnowledgeBaseRetriever
  -> FakeKnowledgeBaseRetriever (default)
  -> SQLiteRequirementRepository

Analysis Job Service
  -> StageEventSink
  -> in-process event stream
  -> SSE endpoint
  -> Browser working-status timeline
```

只有 Frontend 和 Backend 分别运行；Agent 在 Backend 进程内作为 dependency 执行，不是
第三个网络 hop。生产构建产物也不由 FastAPI 提供；若未来需要部署，由外部 reverse
proxy 或 Asset Discovery host 分别路由 Frontend 和 Backend。

### 2.4 API key

`GOOGLE_API_KEY` 只从运行进程环境变量读取。

- 页面不提供 API key 输入框。
- API response、debug payload、日志和 stage event 不包含 API key。
- 缺少 key 时，Backend 可以启动并通过 configuration endpoint 告知 Frontend，但不允许
  提交分析任务。

### 2.5 Working status

Working status 必须来自 application workflow 发出的真实事件，不允许由前端按照固定
时间播放。

第一版阶段：

| Stage | Initial | Update | 含义 |
| --- | --- | --- | --- |
| `validating_input` | Yes | Yes | 校验 request schema 和英文输入 |
| `loading_revision` | No | Yes | 从 SQLite 读取 latest revision |
| `updating_requirement` | No | Yes | Gemini 生成完整 updated requirement |
| `analyzing_requirement` | Yes | Yes | Gemini 分析 requirement |
| `searching_knowledge_base` | Yes | Yes | 调用当前 Retriever |
| `reconstructing_mappings` | Yes | Yes | 根据 chunks 重建并校验证据 |
| `calculating_confidence` | Yes | Yes | 代码计算 confidence 和 priority |
| `persisting_revision` | Yes | Yes | 写入 immutable revision 和 output snapshot |
| `completed` | Yes | Yes | 返回最终 typed response |
| `failed` | Yes | Yes | 返回安全的错误类型和失败阶段 |

每个事件至少包含：

- `job_id`
- `request_id`
- `stage`
- `status`
- `sequence`
- `timestamp`
- `duration_ms`（阶段完成时）
- 不含敏感原文的可选 metadata

### 2.6 Job model

Web 请求不会长时间阻塞等待完整 workflow。提交后返回 `job_id`，后台执行 workflow：

```text
POST /api/v1/jobs/initial
POST /api/v1/jobs/update
GET  /api/v1/jobs/{job_id}
GET  /api/v1/jobs/{job_id}/events
```

- `events` 使用 SSE 推送阶段变化。
- `GET job` 返回当前状态、最终结果或安全错误。
- 第一版 active job 和 event buffer 保存在进程内。
- 服务重启后未完成 job 不恢复；已经成功持久化的 requirement/revision 仍可从 SQLite
  查询。
- 每个 job 使用独立的 workflow context 和 Retriever 选择，禁止修改全局 runtime
  来切换 Fake KB 场景。

## 3. 交互设计

### 3.1 Initial Analysis

表单字段：

- `requirement`：必填英文文本。
- `business_domain`：可选。
- `target_gda`：可选。
- `knowledge_base_scenario`：默认 `empty`。

展示内容：

- 当前阶段、已完成阶段和阶段耗时。
- analyzed requirement summary、business goal、domain context 和 constraints。
- clear fields、keywords、reused mappings 的 confidence、priority、strategy 和
  evidence。
- warnings 和 trace。
- 默认折叠的完整 request/response JSON。

### 3.2 Updated Analysis

表单字段：

- 从 SQLite 历史列表选择 `requirement_id`。
- 展示 latest revision number 和最近分析摘要。
- `supplemental_information`：可选英文文本。
- `search_feedback`：可添加多个结构化 feedback item。
- `knowledge_base_scenario`：默认 `empty`。

第一版 feedback editor 支持：

- target type：asset、attribute、field mapping。
- decision：accept、reject。
- candidate ID、reason、field name。
- asset ID/name/source system。
- attribute ID/name。

前端根据 target type 显示必填字段，最终提交现有
`UpdatedAnalysisRequest.search_feedback` schema。

### 3.3 History

- 列出 SQLite 中已有 requirement。
- 展示 requirement ID、latest revision number、创建/更新时间和安全摘要。
- 选择后可查看 revision history 和 output snapshot。
- 不在普通日志中输出完整 requirement；debug 页面显示本地数据库中的业务内容时要明确
  标注仅适合本地演示。

### 3.4 Error behavior

UI 必须区分：

- 配置错误，例如缺少 API key。
- 输入 schema 或英文校验错误。
- Gemini timeout、schema failure 或调用错误。
- Fake Retriever timeout/invalid payload 降级 warning。
- revision conflict。
- 未知内部错误。

页面只显示可操作且脱敏的错误信息；完整 Python traceback 不发送给浏览器。

## 4. Fake Knowledge Base 模式

### 4.1 默认行为

可视化原型默认使用 `FakeKnowledgeBaseRetriever`，默认场景为 `empty`。页面必须显示
`Fake Knowledge Base` 标识，避免被误认为真实检索结果。

内置场景：

- `empty`
- `complete_mapping`
- `partial_mapping`
- `no_evidence`
- `timeout`
- `invalid`

场景 payload 继续基于 `tests/fixtures/vector_mcp/` 的 normalized chunk schema，但运行
时 fixture 应移入或复制到 package-owned demo resources，不能依赖 tests 目录才能启动。

### 4.2 替换真实 vector-mcp 的依赖

后续切换真实 Knowledge Base 前必须获得：

1. vector-mcp 调用方式：MCP transport、tool name 和认证方式。
2. request 样例及 text 参数约束。
3. success response 样例。
4. empty result 样例。
5. timeout、服务异常和非法 payload 样例。
6. chunk ID、text、similarity、metadata 和 source identity 的字段定义。
7. timeout、retry、rate limit 和最大 chunk 数约束。
8. 本地、测试和部署环境的 endpoint/configuration 方式。

获得契约后执行原计划中的 `codex/vector-mcp-adapter`：

- 实现新的 `KnowledgeBaseRetriever` adapter。
- 在配置中增加 `fake` / `vector_mcp` provider 选择。
- UI 默认 provider 根据环境配置决定，而不是由用户随意切换生产 provider。
- 保留 Fake KB 作为本地 demo 和 contract regression fixture。
- 不修改 application workflow、stage event、domain response 或 Web API contract。

## 5. 顺序开发分支

### 5.1 `codex/split-agent-backend-frontend`

目标：把仓库整理为可复用 Python Agent package、Python Backend 和 TypeScript Frontend
三个职责独立的 workspace。

交付物：

- 将现有 Python package、tests、`pyproject.toml` 和 `uv.lock` 迁入 `agent/`。
- 定义 Agent public facade 和 import surface，封装 runtime composition、Initial、
  Update、history query 和 stage event injection。
- 新建独立 `backend/` Python/FastAPI 工程骨架，并声明对本地 Agent package 的依赖。
- 新建独立 `frontend/` React、Vite、TypeScript strict 工程骨架。
- Agent、Backend 和 Frontend 各自的 lint/test 基线。
- 分离的 Agent/Backend/Frontend 安装与测试命令。
- Root `Makefile` 仅提供统一编排命令。
- 更新 `.gitignore`、`.env.example`、README 和开发日志路径说明。

完成门槛：

- Python 迁移前后的 66 个现有测试全部通过。
- Agent 可独立安装和测试，且不依赖 FastAPI 或 Frontend。
- Backend 可独立导入 Agent public API，不反向修改 Agent global runtime。
- Frontend 可独立启动并显示不依赖 Backend implementation 的 shell 页面。
- Frontend build、typecheck、lint 和基础测试通过。
- 代码依赖检查确认只有 `backend -> agent`，不存在反向或跨层 source import。

### 5.2 `codex/workflow-stage-events`

目标：为 Initial 和 Update workflow 建立真实、可测试且与 UI 无关的阶段事件机制。

交付物：

- typed `WorkflowStage`、`StageStatus` 和 `StageEvent`。
- application-level `StageEventSink` port 和 no-op implementation。
- Initial、Update、analysis pipeline 和 persistence 的阶段 instrumentation。
- 阶段顺序、失败阶段、duration 和 correlation ID 测试。
- 现有 ADK tool 行为和 response schema 保持兼容。

完成门槛：

- Initial 和 Update 每个声明阶段都由真实代码路径触发。
- 异常产生一次 `failed` terminal event，不产生伪 `completed`。
- event 不包含 requirement、chunk text、feedback reason 或 secret。
- 现有测试和新增单元测试通过。

### 5.3 `codex/web-api-job-runtime`

目标：建立可驱动 Analyze Agent 的本地 Web API、后台 job 和 SSE 状态流。

交付物：

- FastAPI application factory。
- `/api/v1` versioned API contract 和 OpenAPI document。
- Agent public API 到 HTTP DTO 的显式 mapping layer。
- Initial/Update job submission endpoints。
- job state/result endpoint。
- SSE stage event endpoint，支持断线后的 sequence replay。
- requirement list、latest revision 和 revision history read API。
- per-job Fake Retriever 场景注入。
- local development CORS allowlist。
- 有界 job/event retention，避免开发服务器无限增长内存。
- API schema、错误映射、并发隔离和 SSE tests。

完成门槛：

- API 不依赖 ADK 对话层即可调用 application services。
- Agent package 不依赖 FastAPI，也不感知 job ID、SSE 或 CORS。
- 两个并发 job 使用不同 Fake KB 场景时不会串数据。
- 已完成 job 可取得与 `AnalyzeResponse` 一致的 payload。
- 缺少 API key、非法输入和 workflow error 返回稳定错误结构。

### 5.4 `codex/interactive-demo-ui`

目标：实现 Initial、Update、History 和结果调试的浏览器界面。

交付物：

- React + TypeScript application。
- 基于 OpenAPI contract 的 generated/validated API types。
- 可配置 API base URL 和 Backend configuration status。
- Initial Analysis form。
- Updated Analysis form 和结构化 feedback editor。
- requirement/revision history selector。
- 真实 working-status timeline 和阶段耗时。
- analyzed result cards/tables。
- confidence、priority、origin、strategy、evidence 和 warnings 展示。
- 可折叠 request、response、trace JSON。
- loading、empty、completed、warning 和 failed states。
- 响应式但以桌面演示为主的样式。
- 页面可访问性基础：label、keyboard focus、status live region。
- Vitest/Testing Library component tests。

完成门槛：

- 不打开终端也能完成 Initial 和 Update 演示。
- 页面不会把 Fake KB 结果标成真实数据。
- refresh 后仍可从 SQLite history 找回已完成 requirement。
- UI 不显示 API key、traceback 或未脱敏内部错误。
- Frontend build、typecheck、lint、component tests 和 API integration tests 通过。

### 5.5 `codex/demo-hardening-runbook`

目标：完成 demo resources、端到端回归、启动命令和演示说明。

交付物：

- package-owned Fake KB demo scenario registry。
- 分别启动 Backend、Frontend 的命令，以及统一开发命令，例如 `make dev`。
- health/configuration endpoint 和页面配置状态。
- Initial empty KB、Initial mapping reuse、Update supplement、Update feedback、
  timeout degradation 的端到端测试。
- Playwright 浏览器关键路径。
- README、runbook 和 `.env.example` 更新。
- 本地数据清理与数据库路径说明。
- 日志和 metrics 对 Web job/stage 的覆盖。

完成门槛：

- 全新 checkout 在安装依赖和配置 API key 后可按文档启动。
- 所有 Fake KB 场景有明确标签并可重复演示。
- 全量 pytest、Ruff、`git diff --check` 和 UI smoke test 通过。
- 文档明确真实 vector-mcp 的缺失和替换步骤。

## 6. 分支执行顺序

严格按以下顺序开发：

1. `codex/split-agent-backend-frontend`
2. `codex/workflow-stage-events`
3. `codex/web-api-job-runtime`
4. `codex/interactive-demo-ui`
5. `codex/demo-hardening-runbook`

不建议并行，原因是：

- Stage event 开发需要先完成 Agent 目录迁移和 public API 边界。
- Web API 依赖稳定的 stage event contract。
- UI 依赖稳定的 job、SSE 和 history API。
- hardening 需要在完整用户路径存在后才能做有效端到端验证。
- 单一 workspace 中并行会增加 dependency drift 和日志恢复成本。

## 7. 测试策略

Agent 分支至少执行：

```bash
make agent-test
make agent-lint
git diff --check
```

Backend 分支至少执行：

```bash
make backend-test
make backend-lint
git diff --check
```

Frontend 分支至少执行：

```bash
make frontend-test
make frontend-lint
make frontend-typecheck
make frontend-build
git diff --check
```

按分支增加：

- Workspace split：Agent 全量 regression、Backend import boundary test 和 Frontend
  scaffold smoke test。
- Stage events：application unit tests 和失败路径测试。
- Web API：FastAPI TestClient/HTTPX、SSE、并发隔离和错误 contract tests。
- UI：Vitest/Testing Library、API contract 和 component behavior tests。
- Hardening：Playwright、完整 Initial/Update demo regression 和双进程启动 smoke test。

需要 Gemini 的自动测试继续使用 injected fakes，不消耗真实 API；只在明确的手工 smoke
test 中使用用户环境中的 `GOOGLE_API_KEY`。

## 8. 状态和日志管理

- 总状态继续维护在 `docs/development-status.md`。
- 分支开始时创建：
  `docs/development-logs/<branch-name-with-slash-replaced-by-hyphen>.md`。
- 日志字段、更新时间点和 completion checklist 继续遵守
  `docs/development-logs/README.md`。
- 2.0 总进度按 `merged branches / 5 applicable branches` 统计。
- `codex/vector-mcp-adapter` 继续标记为 `deferred`，不计入 2.0 分母。

## 9. Definition of Done

2.0 只有在以下条件全部满足时才算完成：

- 用户可在浏览器完成 Initial 和 Update workflow。
- Working status 来自真实 workflow events。
- 分析结果有清晰摘要，完整 payload 可折叠查看。
- SQLite history 可用于选择和恢复 requirement。
- Fake KB 场景清晰标注且可重复演示。
- API key 仅来自环境变量。
- Agent、Backend 和 Frontend 可独立安装和测试。
- Agent 是无 FastAPI 依赖的可复用 package，不是第三个网络服务。
- Frontend 只通过版本化 HTTP/SSE API 访问 Backend。
- Backend 只通过 Agent public API 使用核心能力，不导入 Agent private modules。
- Backend 不托管或引用 Frontend source/build output，Agent 不引用 Backend。
- UI、API 和 application 层职责分离。
- 5 个分支全部测试、记录、提交并 squash merge 回 `main`。
- `development-status.md` 和 runbook 与代码事实一致。
