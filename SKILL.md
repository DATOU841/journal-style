---
name: journal-style
description: 面向中文期刊语境，分析期刊身份、近年题录、选题趋势、材料与方法偏好、论证风格、参考文献生态、投稿匹配度和文衡交接；用于期刊分析、选题评估、改投判断与下游交接，不写正文，不润色正文，不模仿正文语气。
---

# journal-style

这个 skill 只做期刊分析层，默认服务中文语境期刊，也可处理外文期刊的结构化分析。

## 文衡原生协议

正式期刊画像、投稿匹配或 C03 交接任务启动前必须先进入文衡 B02，由主仓 `/api/tasks` 创建或绑定 `journal_style` 任务，取得 `wenheng_task_id`、标准 task folder、F06 routing decision 和 H08 evidence stub。缺少 `wenheng_task_id`、task folder 或 routing decision 时，本 skill 只能生成 `wenheng-intake-request`，列明目标期刊、脱敏稿件方向、需要的证据层级和建议 routing；不得正式分析、评分或生成 C03 profile。

本 skill 不写正文、不润色正文、不模仿期刊语气，因此通常不适用正文写作类 G07 风格规则；但每个 `wenheng-center-status.json`、H08 evidence 和 C03 handoff 必须写入 `style_memory_not_applicable_reason`。如果输出面向用户的分析摘要、交接说明或反馈复盘需要中文表达约束，可读取 G07 active rules 并记录：

- `style_memory_source`
- `style_memory_rules_applied`
- `style_memory_rules_ignored`
- `style_memory_conflicts`
- `style_memory_not_applicable_reason`
- `style_memory_feedback_candidate_id`

完成后必须产出 `05-handoff/wenheng-center-status.json` 和 C03 handoff，并由文衡后端受控调用 `/api/c03/journal-profiles/from-task/:taskId` 写入 C03。`task_id`、`source_run_id`、`evidence_path`、`source_skill` 等 source fields 实行来源锁定（source lock），只能由文衡 task、运行事件和 H08 evidence 派生，不得由人工手填或在 handoff 中伪造。只允许建议 C03 微调字段：`priority`、`submission_stage`、`tags`、`next_action`、`match_status`。失败必须进入 H08 error review；完成必须进入文衡 archive package。期刊画像经验和用户反馈只进入 G07 feedback candidate，不得自动晋升 active rule。

文衡协议细节见 `docs/wenheng-native-protocol.md`；handoff 字段见 `templates/wenheng-handoff-schema.json`。运行入口见 `scripts/journal-style-startup.py`，该入口只生成文衡受控 handoff，不直接写 C03 source fields。正式任务必须先由该入口写入 `00-intake/wenheng-native-binding.json`；`scripts/build_task_skeleton.py` 和 `scripts/journal_style_runner.py` 在 production/native 模式下会校验该绑定收据，缺失或非 B02/F06/H08 验证通过时 fail-closed。显式 legacy/debug 模式只供离线回归，不得成为 production evidence。

## 边界

- 不写论文正文。
- 不润色论文正文。
- 不把期刊分析混成正文生成工具。
- 不用题名直接臆测全文风格。
- 证据不足时只写“推测”“待补证据”“部分支持”，不写成确定结论。
- 在身份、题录、专题库、PDF/RAG 和参考文献生态未核验前，不给高置信投稿结论。

## 首版能力范围

当前稳定能力覆盖这些范围：

- 期刊身份确认
- 全量题录采集框架
- 选题专项库框架
- `检索入库` 接口约束
- 数据性量化分析报告
- 投稿运营与公开声誉证据分析
- 基金与选题关联分析
- 题名风格分析
- 选题趋势分析
- 材料、方法、论证风格分析
- RAG/全文样本模式挖掘
- MinerU/mu 完整全文核心包验收
- 逐篇全文体例画像
- 下游可消费期刊约束锁
- 已刊样本回放校准评分器
- 参考文献生态分析
- 作者机构网络分析
- 作者公共身份与署名基金结构分析
- 多期刊作者身份对比
- 参考文献网络分析
- 投稿匹配度评分
- 选题建议
- 文衡状态输出
- 下游技能交接
- 可 best-effort 消费检索入库 0.2.11 sidecar 的来源角色、全文可用性指针、RAG 查询种子和缺口账本
- 可从 Obsidian 期刊评审工作台 front matter 导出 `journal_review_memory_v1` 人工评审记忆 overlay；该 overlay 只作建议性控制面，永不进入证据链。

## 标准任务目录

每个任务按这个结构落地：

```text
journal-style-task/
├── 00-intake/
├── 00-official/
├── 01-title-intake/
├── 015-title-screening/
├── 02-topic-library/
├── 02b-core-library/
├── 025-rag-import/
├── 03-analysis/
│   ├── metadata-layer/
│   └── fulltext-layer/
│       ├── mu-fulltext-core-pack.json
│       ├── per-article-style-profiles.json
│       └── journal-style-aggregation-bundle.json
├── 04-fit-evaluation/
├── 05-handoff/
├── 06-gates/
├── scripts/
├── current-run-state.json   # 唯一权威状态（状态机写入）
└── task-state.json          # 只读镜像，不用于判断阶段位置
```

## 工作流

### 运行模式

任务必须声明或默认进入一种运行模式：

- `light`：只做身份、题录趋势、栏目、作者机构等 metadata-only 分析，不要求 MinerU/mu 完整全文包。
- `standard`：默认模式，做题录/摘要层标准期刊分析与非全文投稿辅助判断，不要求 MinerU/mu 完整全文包。
- `full`：完整下游可消费模式，要求 `检索入库` 上游交付 MinerU/mu 完整全文核心包，并完成逐篇画像、聚合约束锁和已刊样本回放校准评分。

MinerU/mu 完整全文包是 `full` 模式的 hard gate，不是所有任务的 hard gate。`light`/`standard` 不得输出全文体例、论证风格或参考文献生态的稳定结论。

### 状态机运行入口（防漂移）

所有任务必须经状态机编排，不允许把多个步骤压成一次动作，也不允许把 gate 当产物手写。

- `current-run-state.json` 是唯一权威状态源；`task-state.json` 与 `05-handoff/wenheng-center-status.json` 只是只读镜像，不得用于判断阶段位置。
- 阈值、字段策略、步骤定义全部来自 `config/`（`stage-gates.json`、`field-policy.json`、`workflow-states.json`、`source-profiles-schema.json`），脚本不得再硬编码。
- 运行顺序：先 `scripts/build_material_intake_manifest.py` 建 Step0 物料清单，再 `scripts/journal_style_runner.py --task-dir <task>` 推进。runner 在消费任何 gate 前会用 `scripts/gate_runner.py` 现场重跑 gate 逻辑，存储的 `06-gates/<gate>.json` 只是带 sha 链的回执，手写或过期的 verdict 不被信任。
- 重跑/续跑用 `scripts/journal_style_resume.py --task-dir <task> --resume-manifest <manifest>`：声明 `satisfied_by_prior_run` 的步骤只有在「有 gate 且现场重跑通过」时才跳过；无 gate 步骤永不跳过，必须逐步执行。
- 交接前用 `scripts/validate_source_profiles.py`（P4 provenance 反查 Step0 清单）和 `scripts/validate_field_policy.py`（P5 双向字段策略：仅凭证阻断，公开元数据不拦截）做契约校验。
- 回归用 `tests/run_state_machine_fixtures.py`，复现本轮漂移事故并断言被拦截。
- 发布态完整性闸门（0.1.9 新增）：`config/release-manifest.json` 记录全部 `config/` 与状态机脚本的 sha256。`journal_style_runner.py`、`gate_runner.py`、`journal_style_resume.py`、`run_stage_gates.py` 在执行任何业务逻辑前先调用 `assert_release_integrity()`，发现发布后 config 或脚本字节漂移即 fail-closed（退出码 3，不推进、不写 completed），并把失败写入 `06-gates/h08/`。执行窗口不得把任务级适配写进 skill repo；如需适配路径，必须走 task-local adapter。该闸门是树内字节漂移检测；彻底防重签需要发布流程配合 `--require-clean` 和外部发布保护。
- 任务级路径适配只能走受控通道：把 gate 输入放在非默认路径时，用 `00-intake/task-adapter-manifest.json` 声明 override。override 只能改 `gate_input` 指向的 task-local 路径，且必须在 Step0 清单注册、sha 绑定、step 在白名单内（仅 `step06_zotero_pdf_rag`、`step08a_metadata_layer`）；任何试图改 `gate`/`next`/`threshold`/`resume_skippable` 的 override 一律拒绝。详见 `references/task-adapter-protocol.md`。
- 发布期由 `scripts/build_release_manifest.py --require-clean` 生成 manifest：该选项要求 manifest 追踪的 config/scripts 相对 HEAD 干净，避免未提交改动被直接重签；`--check` 用于发布前校验 manifest 是否与当前字节一致。

### 1. 初始化任务

- 记录目标期刊、学科方向、用户稿件/拟题、时间范围、需要的判断。
- 创建任务目录和状态文件。
- 默认把“全量题录库”和“选题专项库”分开，不混成一个库。

### 2. 期刊身份确认

- 核实正式刊名、曾用名、ISSN/CN、主办/主管单位、官网、投稿系统、收录状态、栏目和刊期。
- 排除同名刊、假官网、过期投稿页。
- 输出身份确认和官网/网页证据。

### 3. 全量题录采集

- 采集近年目录、题名、作者、单位、摘要、关键词、基金、页码、来源和 PDF 状态。
- 数据优先来自数据库元数据和官网目录。
- 题录框架要能持续扩充，不要只做临时样本。

### 4. 标题层初筛

- 基于题名和题录元数据剔除明显不相关条目。
- 默认保留艺术学、艺术史、艺术理论、艺术教育；可剔除明显无关的建筑、设计、工艺、景观、纯作品图版等。
- 剔除必须写入 ledger，不得删除已有 Zotero/PDF/RAG receipt。

### 5. 选题专项库

- 围绕用户拟投方向，收集目标期刊同类文章、相邻期刊文章、关键作者和高频参考文献。
- 只做专题分析，不把它改写成正文素材库。
- 实际 CNKI / Zotero / PDF / RAG 操作交给 `检索入库`。

### 6. Zotero / PDF / RAG 核验

- 核对集合结构、条目数、PDF 数、重复条目、无 PDF 条目和 RAG 导库状态。
- 先确认样本能召回，再引用 RAG 结论。
- 只认 `检索入库` 的 item-level receipt，不把 runner report 当完成依据。
- 若任务需要全文体例分析，必须额外验收 `检索入库` 交回的 MinerU/mu 完整全文核心包。这里的 `mu` 指 MinerU：入库环节把初始 PDF 文献处理成文字版本的方式。
- 普通 RAG 召回包不能替代 MinerU/mu 完整全文包；RAG 可用只说明可召回证据，不说明单篇体例完整可分析。

### 7. 核心库筛选

- 从初筛保留库中按 25%-40% 筛选核心库。
- 核心库筛选必须结合题目相近度、栏目、材料方法、理论/艺术史相关度、全文可用性和年度/栏目代表性。
- 核心库不是“所有下载成功的文章”，也不是主观题名挑选。

### 8. 期刊画像分析

- 题名风格：字数、主副标题比例、结构、常见动词、问题-对象结构。
- 选题趋势：年度聚类、栏目变化、热点/稳定/退潮/拥挤方向。
- 材料与方法：一手材料类型、方法分布、证据标准。
- 论证风格：问题提出、文献综述、段落节奏、结论方式。
- 参考文献生态：数量分布、中外比例、近年文献、期刊内互引、高频作者。
- 格式体例：摘要、关键词、标题层级、注释与参考文献、作者信息、英文项。
- 题录/摘要层结论必须标 `metadata_only`。
- 全文格式、论证风格和参考文献生态必须来自核心库全文/PDF/RAG；无 provenance 不得给高置信结论。
- 全文体例结论必须遵守“逐篇 -> 分组 -> 聚合”：先对每篇 MinerU/mu 完整全文生成 `per_article_style_profile_v1`，再聚合为期刊约束锁。
- 少于 10 篇 MinerU/mu 完整全文只能写待补材料；10-19 篇只能写初步偏好；20 篇以上才允许稳定体例结论；论证风格和参考文献生态高置信结论建议 30 篇以上。

### 9. 投稿匹配评分

- 采用 100 分制。
- 评分要给证据，不要只给主观印象。
- 风险项单独扣分，不要掩盖成“总体不错”。
- 评分器不得称为“模仿主编”，不得模拟具体编辑个人，不预测录用概率。正式定位为 `journal_fit_scoring_model_v1`：基于已刊核心样本回放校准的期刊适配评分器。
- 评分模型未完成已刊样本回放校准前，不得给用户稿件做分位定位。

### 10. 选题建议与交接

- 至少给出三类建议：高适配、可补强、不建议。
- 明确下一步是补检索、补文献、补 PDF/RAG，还是转到写作、润色、补注。
- 文衡状态要和实际证据同步，不要先写满分再找证据。

## 必要输出

每个任务至少产出或更新这些文件：

- `journal-identity-confirmation.md`
- `journal-official-and-web-evidence.md`
- `journal-full-title-list.xlsx`
- `journal-title-ingestion-log.md`
- `topic-special-library-plan.md`
- `topic-related-title-list.xlsx`
- `zotero-and-pdf-check-report.md`
- `rag-import-handoff.md`
- `journal-submission-operations-report.md`
- `journal-submission-operations-statistics.json`
- `journal-quantitative-analysis-report.md`
- `journal-funding-topic-association-report.md`
- `journal-funding-topic-association-statistics.json`
- `journal-rag-fulltext-pattern-report.md`
- `journal-rag-fulltext-pattern-statistics.json`
- `mu-fulltext-core-pack.json`
- `per-article-style-profiles.json`
- `journal-style-aggregation-bundle.json`
- `journal-polish-consumption-pack.json`
- `journal-review-memory-pack.json`（可选，人工评审记忆 overlay，`not_evidence=true`）
- `journal-fit-scoring-model.json`
- `journal-title-style-report.md`
- `journal-topic-trend-report.md`
- `journal-method-material-report.md`
- `journal-argument-style-report.md`
- `journal-reference-ecology-report.md`
- `journal-author-institution-network-report.md`
- `journal-author-institution-network-statistics.json`
- `journal-author-profile-and-byline-report.md`
- `journal-author-profile-and-byline-statistics.json`
- `journal-reference-network-report.md`
- `journal-reference-network-statistics.json`
- `submission-fit-score.md`
- `topic-suggestion-report.md`
- `target-journal-decision.md`
- `multi-journal-author-profile-comparison-report.md`
- `multi-journal-author-profile-comparison-statistics.json`
- `handoff-to-downstream-skills.md`
- `wenheng-center-status.json`

## 需要阅读的 references

- `references/output-schema.md`
- `references/evidence-rules.md`
- `references/stage-gates-protocol.md`
- `references/title-screening-protocol.md`
- `references/core-library-selection-protocol.md`
- `references/secret-boundary-protocol.md`
- `references/scoring-rubric.md`
- `references/quantitative-analysis-protocol.md`
- `references/journal-submission-operations-protocol.md`
- `references/fulltext-article-pattern-mining-protocol.md`
- `references/run-modes-protocol.md`
- `references/mu-fulltext-pack-protocol.md`
- `references/per-article-profile-protocol.md`
- `references/aggregation-and-consumption-protocol.md`
- `references/review-memory-pack-protocol.md`
- `references/scoring-model-protocol.md`
- `references/funding-topic-association-protocol.md`
- `references/handoff-to-jiansuo-ruku.md`
- `references/handoff-from-jiansuo-ruku.md`
- `references/topic-suggestion-protocol.md`
- `references/column-analysis-protocol.md`
- `references/author-institution-network-protocol.md`
- `references/author-profile-and-byline-protocol.md`
- `references/reference-network-protocol.md`
- `references/multi-journal-comparison.md`
- `references/multi-journal-author-profile-comparison-protocol.md`
- `references/wenheng-contract.md`
- `references/downstream-handoff.md`
- `references/handoff-to-zhengwen-xiezuo.md`
- `references/handoff-to-wenzhang-runse.md`
- `references/handoff-to-cankao-wenxian.md`

## scripts

状态机入口（防漂移核心，新增）：

- `scripts/journal_style_runner.py`：状态机编排器。按 `config/workflow-states.json` 顺序推进，遇到第一个未满足的步骤即 fail-closed 停下，绝不跳步或把多步压成一次动作。唯一权威状态写入 `current-run-state.json`；`task-state.json` 和 `05-handoff/wenheng-center-status.json` 只作只读镜像。
- `scripts/gate_runner.py`：唯一允许产出 gate verdict 的入口，verdict 内嵌被判产物的 sha256 与 generator marker，写入 `06-gates/<gate>.json` 作为收据。
- `scripts/journal_style_runtime.py`：共享运行库（加载 `config/`、sha256、权威状态读写、`GATE_ID_MAP`、gate 输入解析）。
- `scripts/journal_style_resume.py`：重跑兼容模式。`resume-manifest.json` 声明的“上轮已完成”步骤只有在“有 gate 且现在用 live 产物现场重跑 gate 通过”时才可跳过；无 gate 的步骤永不可跳。
- `scripts/build_material_intake_manifest.py`：Step 0 物料清单，登记每个可用输入资产及其 sha256，供后续 provenance 反查。
- `scripts/validate_source_profiles.py`：校验 `检索入库` → journal-style 的 source_profiles 交接契约，provenance 必须能反查 Step 0 清单。
- `scripts/validate_field_policy.py`：双向 field-policy 校验，仅凭证（key/token 等）判 NO_GO，公开元数据不拦截。

gate 信任模型（重要）：runner 在消费任何步骤前，会用 `gate_runner.py` 对 live 产物现场重跑 gate 逻辑，不信任已存在的 verdict 文件的 marker/sha。因此手写或过期的 gate verdict 无法放行坏产物。所有阈值集中在 `config/stage-gates.json`，凭证白/黑名单集中在 `config/field-policy.json`，Python 不再硬编码第二份。

- `scripts/build_task_skeleton.py`：建立任务目录和初始状态文件。
- `scripts/validate_wenheng_status.py`：校验文衡状态 JSON。
- `scripts/run_stage_gates.py`：运行阶段 gate，阻断 metadata-only 完成、无 provenance 全文宣称、secret 边界和 handoff 漂移。
- `scripts/screen_titles.py`：只读题录元数据生成标题层初筛 ledger，不删除 Zotero/PDF/RAG receipt。
- `scripts/select_core_library.py`：按 25%-40% 比例和多因子评分生成核心库 ledger。
- `scripts/score_fit.py`：汇总投稿匹配度分项。
- `scripts/analyze_title_corpus.py`：分析题名结构和基础趋势。
- `scripts/analyze_journal_submission_operations.py`：分析投稿系统、审稿周期、费用政策和公开声誉证据线索。
- `scripts/analyze_fulltext_article_patterns.py`：分析 `检索入库` 交接后的 RAG/全文样本结构、材料方法和日期线索。
- `scripts/analyze_funding_topic_association.py`：分析基金层级与选题、栏目、材料和方法的关联。
- `scripts/compare_multi_journal_author_profiles.py`：对比多个期刊的作者身份、署名结构和基金支撑情况。
- `scripts/analyze_reference_ecology.py`：分析参考文献生态。
- `scripts/analyze_author_institution_network.py`：分析公开题录中的作者、机构、合作边和集中度。
- `scripts/analyze_author_profile_and_byline.py`：分析公开作者身份、职称学位、署名顺序、通讯作者和基金结构。
- `scripts/analyze_reference_network.py`：分析结构化参考文献的共引、作者共引和核心文献候选。
- `scripts/generate_quantitative_report.py`：生成数据性量化分析报告。
- `scripts/generate_topic_suggestions.py`：生成选题建议，不生成正式正文题名。
- `scripts/update_wenheng_status.py`：增量更新文衡状态并记录历史。
- `scripts/analyze_column_structure.py`：分析栏目生命周期和稳定性。
- `scripts/run_smoke_tests.py`：用临时样本跑通核心脚本，不读取真实任务数据。

## 输出纪律

- 证据尽量落到数据库、官网、PDF 和 RAG。
- 不能确认的内容就写“待核验”。
- 不把分析写成正文，不把正文写成分析。
- 下游交接要明确：给谁、补什么、为什么补。

## 公开介绍纪律

- `README.md` 和 `docs/public-introduction.zh.md` 的正式公开介绍正文必须由文衡 Claude 生成。
- Codex 只维护公开介绍的结构、生成提示、来源标记和校验脚本，不直接撰写公开介绍正文。
- 公开介绍不得宣称本 skill 能写正文、润色正文、直接检索 CNKI、直接下载 PDF、直接导入 RAG 或保证录用。
