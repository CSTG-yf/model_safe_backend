# 后端比赛 MVP 重构计划书

依据文件：`project_goal_markdown/大模型安全创新比赛实施建议.md`

## 1. 新目标定位

后端重构目标从“通用大模型测评平台”调整为：

> 面向单个目标模型的安全评测、风险归因与个性化防护策略生成平台。

核心闭环：

```text
目标模型 -> 普通评测/越狱评测/RAG 污染评测/Agent 工具评测
-> JudgeService 裁判 -> Trace 风险归因 -> 风险画像
-> 个性化防护策略包 -> 回归验证 -> 风险诊断报告
```

比赛 MVP 不再优先扩散到大规模知识图谱、多模态伪造、联邦学习、差分隐私训练等远期方向，而是集中跑通：

```text
目标模型风险画像 + Trace 风险归因 + 个性化防护策略包 + 回归验证
```

时间允许时再补齐：

```text
RAG 污染沙箱 + Agent 工具越权沙箱
```

### 1.1 核心产物：ModelProtectionStrategy

平台最终产物不是单次评分，也不是单个 Markdown 提示词，而是面向目标模型的个性化防护策略包：

```text
ModelProtectionStrategy
├─ risk_profile.json              # 模型风险画像
├─ guard_prompt.md                # 可读防护提示词片段
├─ guard_policy.json              # 后端可执行防护策略
├─ rag_guard_rules.json           # RAG 污染、敏感文档、引用约束规则
├─ agent_tool_policy.json         # Agent 工具白名单、参数 schema、高危确认规则
├─ output_guard_rules.json        # 输出审查、拒答、改写规则
├─ regression_cases.json          # 该模型专属回归样例
└─ policy_report.md               # 报告和答辩展示版本
```

Markdown 只作为人工可读展示层；运行时以 JSON/YAML 结构化策略为准。每次用户输入前，后端通过策略编译器把基础安全策略、目标模型风险画像、当前场景规则和个性化 prompt patch 合成为最终调用上下文。

## 2. 已完成基础

前期阶段已经完成以下后端底座，可直接复用：

- 配置环境化、`.env.example`、密钥治理。
- 项目级权限、统一响应、全局异常、请求 ID、日志基础设施。
- `QuestionBank`、`Question`、`QuestionRiskTag`、`QuestionQualityCheck` 等结构化题库模型。
- `EvaluationRun`、`EvaluationCase`、`EvaluationCaseResult`、`EvaluationArtifact` 等统一评测模型。
- `TaskService` 异步任务基础。
- `ModelGateway` 模型调用入口。
- `JudgeService` 裁判评分服务，已覆盖 `capability`、`safety`、`jailbreak`、`rag`、`agent` rubric。
- `MetricDefinition`、`MetricValue` 与默认指标注册表。

这些能力不推倒重来，下一轮重构以新增业务 app 和兼容式接入为主。

## 3. 后端技术选型

| 方向 | 技术选型 | 说明 |
| --- | --- | --- |
| Web API | Django + Django REST framework | 保留现有栈，减少迁移成本 |
| 异步任务 | Celery + Redis | 承载红队、RAG、Agent、回归和报告任务 |
| 实时反馈 | Django Channels + Redis | 推送任务进度、红队轮次、Trace 过程 |
| 模型接入 | `core.model_gateway.ModelGateway` | 统一目标模型、裁判模型、建议生成模型 |
| 结构化输出 | Pydantic + JSON Schema | 用于攻击结果、裁判结果、防护建议结构校验 |
| 关系数据库 | 现阶段继续使用 MySQL | 保持当前部署稳定；后续可评估 PostgreSQL |
| RAG 检索 | Chroma/Ollama 向量检索 + 数据库关键词兜底 | 已接入 Chroma 容器与 Ollama embedding 服务；断路时回退关键词检索 |
| Agent 沙箱 | Django 服务内模拟工具 | 不执行真实危险操作，只记录和拦截 mock tool call |
| 防护策略 | 结构化 Policy Pack + Markdown 展示 | 后端执行 JSON/YAML，报告导出 Markdown |
| API 文档 | drf-spectacular | 后续补充 OpenAPI，便于前端接入 |
| 测试 | Django TestCase + mock ModelGateway | 核心规则和服务优先单测 |

本轮重构已将自适应红队编排升级为 LangGraph `StateGraph` agent；Neo4j、Milvus 仍放到第二轮增强，避免比赛 MVP 被基础设施拖慢。

### 3.1 模型职责边界

项目内必须区分两类模型：

- 被评测模型：项目或任务的目标模型，是安全评测、红队攻击、RAG/Agent 沙箱要测试的对象。来源为 `Project.ai_model_name` 或接口中的 `target_model_name`。
- 平台内置模型：后端系统自身使用的模型，用于攻击生成、裁判评分、防护建议润色等内部能力。来源为环境变量 `INTERNAL_ATTACK_MODEL_NAME`、`INTERNAL_JUDGE_MODEL_NAME`、`INTERNAL_RECOMMENDATION_MODEL_NAME`。

禁止把平台内置默认模型当作被评测模型兜底。若真实执行评测且项目没有配置目标模型，接口应要求显式传入 `target_model_name`。

## 4. 新增模块设计

### 4.1 `trace_analysis`

职责：记录应用链路、风险证据和归因结果。

核心模型：

- `AppTrace`：一次应用调用或一次评测链路。
- `TraceStep`：链路步骤，如 `user_input`、`retrieval`、`context_build`、`model_output`、`tool_call`、`post_check`。
- `TraceRisk`：风险类型、风险等级、证据、原因、防护提示。

核心服务：

- `TraceRecorder`：创建 trace、追加 step、追加 risk、汇总风险等级。
- `TraceAttributionService`：根据 step 内容和裁判结果生成风险归因。

API：

```text
GET /api/traces/?project_id=1
GET /api/traces/{trace_id}/
GET /api/traces/{trace_id}/risks/
```

### 4.2 `redteam_engine`

职责：把现有越狱固定模板升级为轻量自适应红队策略调度。

核心模型：

- `AttackStrategy`：攻击策略模板。
- `RedTeamAttempt`：每一轮攻击尝试。
- `StrategyStat`：策略在风险类别上的效果统计。

核心服务：

- `StrategySelector`：按历史成功率、平均风险分、新颖度、成本选择下一轮策略。
- `RedTeamGraphAgent`：基于 LangGraph `StateGraph` 编排红队状态。
- `RedTeamOrchestrator`：创建 `EvaluationRun`，并把每个目标交给 LangGraph agent 执行攻击生成、目标模型调用、裁判评分、Trace 写入、统计更新。
- `StrategySeedService`：把现有越狱策略初始化为可配置模板。

模型使用边界：

- `target_model_name`：被评测模型，用于接收攻击 prompt。
- `attack_model_name`：平台内置攻击生成模型，后续用于生成动态攻击 prompt。
- `judge_model_name`：平台内置裁判模型，用于 `JudgeService` 评分。

策略得分：

```text
score = 历史成功率 * 0.45 + 平均风险分 * 0.35 + 新颖度 * 0.10 - 平均成本 * 0.10
```

API：

```text
POST /api/redteam/runs/
GET  /api/redteam/runs/{run_id}/
GET  /api/redteam/runs/{run_id}/attempts/
GET  /api/redteam/strategies/
GET  /api/redteam/strategy-stats/
```

### 4.3 `mitigation`

职责：根据风险归因生成防护建议，并把失败样例沉淀为回归集。

核心模型：

- `MitigationTemplate`：风险到建议的确定性模板。
- `MitigationRecommendation`：针对项目、Trace、Run 的具体建议。
- `RegressionSet`：回归样例集。
- `RegressionCase`：单条回归样例。

核心服务：

- `RecommendationService`：用 `risk_code + scenario_type + step_type` 匹配模板，生成建议。
- `RegressionService`：从失败攻击、RAG 污染、Agent 越权样例生成回归集。
- `DefenseCompareService`：对比修复前后风险分、攻击成功率、误拒率、正常任务通过率。

API：

```text
GET  /api/mitigation/recommendations/?project_id=1
POST /api/mitigation/recommendations/{id}/accept/
POST /api/regression/sets/
POST /api/regression/runs/
GET  /api/regression/runs/{run_id}/compare/
```

### 4.4 `rag_security`

职责：构建轻量 RAG 污染评测沙箱。

核心模型：

- `RagKnowledgeBase`
- `RagDocument`
- `RagEvalCase`

核心服务：

- `SimpleRetriever`：第一版使用关键词/文本相似度检索。
- `RagPromptBuilder`：拼接问题、召回文档、引用约束。
- `RagSecurityEvaluator`：调用目标模型和 `JudgeService` 判断污染命中、污染采纳、敏感泄露。
- `RagTraceWriter`：记录 retrieval、context_build、model_output、post_check step。

API：

```text
POST /api/rag-security/knowledge-bases/
POST /api/rag-security/documents/
POST /api/rag-security/eval-runs/
GET  /api/rag-security/eval-runs/{run_id}/
```

### 4.5 `agent_security`

职责：构建 Agent 工具越权评测沙箱。

核心模型：

- `AgentTool`
- `AgentToolCall`

核心服务：

- `ToolRegistry`：注册 mock 工具。
- `ToolPolicyEngine`：执行白名单、角色、参数 schema、高危确认、敏感参数规则。
- `AgentSandbox`：模拟 Agent 工具调用，不执行真实危险操作。
- `AgentTraceWriter`：记录 tool_call 和拦截原因。

API：

```text
POST /api/agent-security/tools/
POST /api/agent-security/eval-runs/
GET  /api/agent-security/tool-calls/{trace_id}/
```

边界：第一版 Agent 工具安全沙箱不做动态红队，只使用固定越权样例、mock 工具和规则化扰动来验证工具权限防护。

### 4.6 `protection_strategy`

职责：汇总各类评测结果，为目标模型生成个性化防护策略包，并在模型调用前提供可执行防护。

核心模型：

- `ModelProtectionStrategy`：项目/目标模型级策略入口。
- `ProtectionPolicyVersion`：策略版本、状态、发布时间。
- `ProtectionPolicySource`：策略来源，关联 `EvaluationRun`、`AppTrace`、`TraceRisk`、`MitigationRecommendation`、`RegressionCase`。

核心服务：

- `RiskProfileBuilder`：汇总普通评测、越狱、RAG、Agent 的风险画像。
- `ProtectionPolicyGenerator`：生成结构化防护策略。
- `ProtectionPromptBuilder`：生成可读的 prompt patch。
- `ProtectionPolicyCompiler`：在用户输入前合成最终 system/developer prompt 与执行规则。
- `InputGuard` / `OutputGuard` / `RagGuard` / `AgentToolGuard`：运行时防护组件。

API：

```text
POST /api/protection-strategies/generate/
GET  /api/protection-strategies/?project_id=1
GET  /api/protection-strategies/{strategy_id}/
POST /api/protection-strategies/{strategy_id}/activate/
POST /api/protection-strategies/compile/
GET  /api/protection-strategies/{strategy_id}/export/
```

## 5. 阶段计划

### 阶段 A：比赛 MVP 闭环

目标：最短路径跑通“攻击 -> 归因 -> 建议 -> 回归 -> 报告”。

任务顺序：

1. 新增 `trace_analysis` app 和 Trace 数据结构。
2. 普通评测、越狱评测接入 `AppTrace` 和 `TraceStep`。
3. 新增 `redteam_engine` app。
4. 把当前越狱策略拆成 `AttackStrategy` 模板。
5. 实现 `StrategySelector`。
6. 实现 `RedTeamOrchestrator` 第一版。
7. 新增 `mitigation` app。
8. 初始化 `MitigationTemplate`。
9. `TraceRisk` 生成后自动生成 `MitigationRecommendation`。
10. 失败样例自动进入 `RegressionSet`。
11. 回归任务创建 `EvaluationRun(run_type="regression")` 并复测失败样例。
12. 报告接口增加 Trace、风险证据、防护建议、回归对比字段。

交付效果：

```text
选择项目 -> 发起自适应红队 -> 展示攻击路径
-> 展示风险归因和证据 -> 自动生成防护建议
-> 一键生成回归集 -> 执行回归验证 -> 输出诊断报告
```

### 阶段 B：RAG 污染沙箱

目标：补齐区别于普通越狱平台的真实应用链路创新点。

边界：本阶段不加入 RAG 动态红队。RAG 评测使用固定污染文档、敏感文档、规则化问题集和可控扰动，评测结果用于生成目标模型的 RAG 防护策略。

任务顺序：

1. 新增 `rag_security` app。
2. 新增知识库、文档、RAG 用例模型。
3. 支持正常文档、污染文档、敏感文档标注。
4. 实现轻量检索和上下文拼接。
5. 调用目标模型生成答案。
6. 使用 `JudgeService(rubric="rag")` 判断污染采纳和敏感泄露。
7. 写入 `AppTrace`、`TraceStep`、`TraceRisk`。
8. 复用 `mitigation` 生成 RAG 防护建议。

交付效果：

```text
用户问题 -> 召回正常/污染文档 -> 模型受污染影响
-> Trace 定位污染来源 -> 推荐可信过滤、注入检测、引用约束
```

### 阶段 C：模型个性化防护策略包

目标：把普通评测、越狱评测、RAG 污染评测和后续 Agent 工具评测沉淀为目标模型的可执行防护策略。

当前状态：已完成基础落地。后端已支持策略模型、风险画像、结构化策略生成、策略编译、运行时守卫、策略导出和基础单测。

任务顺序：

1. 新增 `protection_strategy` app。
2. 新增策略、策略版本、策略来源模型。
3. 从 `EvaluationRun`、`AppTrace`、`TraceRisk`、`MitigationRecommendation` 汇总风险画像。
4. 生成 `guard_policy.json`、`rag_guard_rules.json`、`agent_tool_policy.json`、`output_guard_rules.json`。
5. 生成 `guard_prompt.md`，作为每次模型调用前的个性化 prompt patch。
6. 实现 `ProtectionPolicyCompiler`，把基础策略、模型风险画像、场景规则合成为最终调用上下文。
7. 使用回归集验证防护前后风险分、误拒率、正常任务通过率。

交付效果：

```text
选择目标模型 -> 汇总多类评测 Trace -> 生成风险画像
-> 生成结构化防护策略包 -> 每次输入前自动注入/执行策略
-> 回归验证防护效果 -> 导出策略报告
```

### 阶段 D：Agent 工具安全沙箱

目标：覆盖 OWASP Excessive Agency 风险。

边界：本阶段不加入 Agent 动态红队。Agent 工具安全先使用固定越权样例、mock 工具和规则引擎，确保工作量和耗时可控。

当前状态：已完成基础落地。后端已支持 mock 工具注册、工具权限规则引擎、固定越权样例执行、工具调用记录、Trace/Risk 写入、防护建议生成、回归样例沉淀和 Agent 风险进入 `ModelProtectionStrategy`。

任务顺序：

1. 新增 `agent_security` app。
2. 注册 mock 工具：`search_docs`、`query_user_profile`、`send_email_mock`、`delete_file_mock`、`payment_mock`。
3. 实现工具白名单、角色权限、参数 schema、高危确认规则。
4. 设计工具越权攻击样例。
5. 执行 Agent 模拟调用并记录 `AgentToolCall`。
6. 写入 Trace 和风险归因。
7. 复用 `mitigation` 生成工具权限防护建议。

交付效果：

```text
攻击提示诱导 Agent 调用高危工具
-> 策略引擎识别越权参数
-> 拦截工具调用
-> 输出防护建议和证据
```

### 阶段 E：竞赛报告和包装

目标：把工程能力转换为评委能快速理解的成果。

任务顺序：

1. 报告从分数汇总升级为风险诊断报告。
2. 增加攻击路径、Trace 风险来源、证据片段、防护建议。
3. 增加防护前后对比指标。
4. 增加策略包展示内容：
   - 目标模型风险画像。
   - 个性化防护提示词。
   - RAG 防护规则。
   - Agent 工具权限规则。
   - 回归验证结果。
5. 准备 3 个演示数据集：
   - 自适应红队攻击。
   - RAG 污染攻击。
   - Agent 工具越权攻击。
6. 增加实验统计接口：
   - 自适应策略相对固定模板的提升幅度。
   - Trace 覆盖率。
   - 风险归因准确率。
   - 防护后风险下降幅度。
   - 正常任务可用性保持率。

## 6. 详细实现优先级

| 顺序 | 任务 | 难度 | 优先级 | 依赖 |
| --- | --- | --- | --- | --- |
| 1 | 新增 `trace_analysis` 数据模型和迁移 | 中等 | P0 | 已有 `EvaluationRun` |
| 2 | Trace 写入服务 `TraceRecorder` | 中等 | P0 | 任务 1 |
| 3 | 越狱/普通评测写入 Trace | 中等 | P0 | 任务 2 |
| 4 | 新增 `redteam_engine` 数据模型 | 中等 | P0 | 已有 `EvaluationRun`、`JudgeService` |
| 5 | 迁移现有越狱策略到 `AttackStrategy` | 中等 | P0 | 任务 4 |
| 6 | 实现 `StrategySelector` | 中等 | P0 | 任务 5 |
| 7 | 实现 `RedTeamOrchestrator` | 较难 | P0 | 任务 2、6 |
| 8 | 新增 `mitigation` 数据模型 | 中等 | P0 | 任务 1 |
| 9 | 初始化防护建议模板 | 简单 | P0 | 任务 8 |
| 10 | TraceRisk 到防护建议自动生成 | 中等 | P0 | 任务 8、9 |
| 11 | 回归集与回归任务第一版 | 较难 | P0 | 任务 7、10 |
| 12 | 报告接入 Trace/建议/回归数据 | 中等 | P1 | 任务 10、11 |
| 13 | RAG 知识库与文档模型 | 中等 | P1 | 任务 1 |
| 14 | RAG 检索与污染采纳判断 | 较难 | P1 | 任务 13 |
| 15 | 模型风险画像与策略模型 | 中等 | P0 | 任务 1、10、11、14 |
| 16 | 防护策略生成与策略编译器 | 较难 | P0 | 任务 15 |
| 17 | 策略包回归验证与导出 | 中等 | P0 | 任务 11、16 |
| 18 | Agent 工具注册与规则引擎 | 较难 | P1 | 任务 1、16 |
| 19 | API 文档和核心接口测试 | 简单 | P1 | 主要接口完成 |

## 7. 指标体系调整

比赛 MVP 优先统计以下指标：

### 发现能力

- `jailbreak_success_rate`：越狱成功率。
- `adaptive_improvement_rate`：自适应策略相对固定模板提升幅度。
- `rag_pollution_hit_rate`：RAG 污染文档召回率。
- `rag_pollution_adoption_rate`：RAG 污染采纳率。
- `agent_unauthorized_tool_call_rate`：Agent 工具越权发现率。

### 解释能力

- `trace_coverage_rate`：Trace 覆盖率。
- `risk_attribution_success_rate`：风险归因成功率。
- `evidence_completeness_rate`：证据片段完整率。

### 防护能力

- `risk_score_reduction_rate`：防护后风险分下降幅度。
- `policy_hit_rate`：个性化防护策略命中率。
- `policy_regression_pass_rate`：策略包回归通过率。
- `regression_pass_rate`：回归通过率。
- `normal_task_pass_rate`：正常任务可用性保持率。
- `false_refusal_rate`：误拒率。

### 工程能力

- `json_parse_success_rate`：结构化输出解析成功率。
- `task_failure_recovery_rate`：任务失败恢复率。
- `report_generation_success_rate`：报告生成成功率。
- `average_task_latency_ms`：任务平均耗时。

## 8. 风险与取舍

1. 不优先接 Neo4j。
   - 原因：当前比赛 MVP 更需要可演示闭环。
   - 替代：先用关系表和 JSON 字段表达风险、证据、防护建议关系。

2. 不优先接更重的分布式向量基础设施。
   - 原因：当前已具备 Chroma/Ollama 向量链路和关键词兜底，足够支撑 RAG 污染演示。
   - 替代：暂不扩展到 Milvus、pgvector 集群或复杂混合检索调优。

3. 使用 LangGraph，但不引入复杂强化学习。
   - 原因：工程周期不可控。
   - 替代：用 LangGraph StateGraph 承载状态流转，用历史成功率、风险分、新颖度、成本的轻量策略调度器选择策略。

4. RAG/Agent 暂不加入动态红队。
   - 原因：RAG 动态文档投毒和 Agent 动态工具诱导会显著增加模型调用次数、Trace 复杂度和评测耗时，容易拖慢比赛 MVP。
   - 替代：当前使用固定污染文档、固定越权样例、规则化扰动和回归集沉淀。动态红队作为远期增强。

5. 不删除旧接口。
   - 原因：前端已有页面依赖旧接口。
   - 替代：新模块并行接入，旧接口逐步适配到新模型。

## 9. 验收标准

阶段 A 完成时，后端应满足：

- 可创建自适应红队任务。
- 每一轮攻击有 `RedTeamAttempt`。
- 每次任务有 `AppTrace`。
- 每个高风险结果有 `TraceRisk` 和证据。
- 可自动生成 `MitigationRecommendation`。
- 可从失败样例生成 `RegressionSet`。
- 可创建回归验证任务并输出对比结果。
- 报告接口能返回风险诊断所需数据。

阶段 B 完成时，后端应满足：

- 可管理 RAG 知识库和文档。
- 可标记污染文档和敏感文档。
- 可执行 RAG 安全评测。
- 可记录检索、上下文、模型输出、污染采纳判断的 Trace。

阶段 C 完成时，后端应满足：

- 可为目标模型生成 `ModelProtectionStrategy`。
- 可汇总多类评测结果形成风险画像。
- 可生成结构化防护策略和可读防护提示词。
- 可在模型调用前编译并应用个性化策略。
- 可用回归集验证防护前后效果。

阶段 D 完成时，后端应满足：

- 可注册 mock Agent 工具。
- 可对工具调用执行权限和参数规则。
- 可记录工具调用 Trace。
- 可区分“模型计划调用危险工具”和“系统实际拦截危险调用”。

## 10. 推荐下一步

下一步应进入阶段 E，优先做比赛包装与质量保障：

```text
补齐核心服务测试
-> 输出比赛展示数据集
-> 报告接口增加策略包与防护前后对比
-> 整理 API 文档
-> 准备演示闭环数据
```

这样普通评测、越狱红队、RAG 污染、Agent 沙箱和个性化防护策略包可以形成完整比赛演示闭环。
## 阶段 E 执行更新：比赛包装与质量保障

更新时间：2026-05-22

当前已完成 E1、E2、E4：

- E1 指标体系：默认指标注册表已覆盖发现能力、解释能力、防护能力和工程能力四类指标，支撑比赛报告中的量化对比。
- E2 API 文档：`project_goal_markdown/新增API接口文档.md` 已整理所有新增 API，包含请求示例、响应要点和模型职责边界。
- E4 攻击材料和数据集：`project_goal_markdown/attack_datasets/` 已生成红队攻击、RAG 污染文档、Agent 工具越权样例和演示 playbook。

阶段 E 后续优先级保持为：

1. E3：补齐核心服务测试，重点覆盖 Trace、红队策略选择、防护建议、回归、RAG 检索规则、Agent 权限规则和策略编译器。
2. E5：完善报告和答辩材料接口，把策略包、防护前后对比、攻击路径和指标汇总输出为前端可直接展示的数据结构。

## 阶段 E 收口更新：质量保障与答辩接口完成

更新时间：2026-05-22

阶段 E 已全部完成：

- E3 核心服务测试：已补齐 Trace、红队、Mitigation、RAG 和报告聚合测试；与已有 Protection Strategy、Agent Security 测试合并后，覆盖比赛 MVP 闭环核心服务。
- E5 报告和答辩材料接口：新增 `GET /api/report-generation/competition-package/`，前端可直接读取比赛演示所需的任务摘要、风险证据、指标、攻击路径、RAG/Agent 发现、策略包、防护对比和演示材料路径。

当前后端主线已形成：

```text
目标模型 -> 红队/RAG/Agent 评测 -> Trace 风险归因 -> 防护建议与回归样例
-> 个性化防护策略包 -> 比赛报告与答辩材料聚合接口
```

后续若继续增强，优先考虑：

1. 把 `competition-package` 输出接入前端报告页和答辩页。
2. 将 E3 测试扩展到接口级权限与 Celery 异步任务。
3. 在真实模型环境下补一轮非模拟评测与成本/耗时统计。
