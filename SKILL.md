---
name: journal-style
description: 面向中文期刊语境，分析期刊身份、近年题录、选题趋势、材料与方法偏好、论证风格、参考文献生态、投稿匹配度和文衡交接；用于期刊分析、选题评估、改投判断与下游交接，不写正文，不润色正文，不模仿正文语气。
---

# journal-style

这个 skill 只做期刊分析层，默认服务中文语境期刊，也可处理外文期刊的结构化分析。

## 边界

- 不写论文正文。
- 不润色论文正文。
- 不把期刊分析混成正文生成工具。
- 不用题名直接臆测全文风格。
- 证据不足时只写“推测”“待补证据”“部分支持”，不写成确定结论。
- 在身份、题录、专题库、PDF/RAG 和参考文献生态未核验前，不给高置信投稿结论。

## 首版能力范围

首版只覆盖这些能力：

- 期刊身份确认
- 全量题录采集框架
- 选题专项库框架
- `检索入库` 接口约束
- 数据性量化分析报告
- 题名风格分析
- 选题趋势分析
- 材料、方法、论证风格分析
- 参考文献生态分析
- 投稿匹配度评分
- 选题建议
- 文衡状态输出
- 下游技能交接

## 标准任务目录

每个任务按这个结构落地：

```text
journal-style-task/
├── 00-official/
├── 01-title-intake/
├── 02-topic-library/
├── 025-rag-import/
├── 03-analysis/
├── 04-fit-evaluation/
├── 05-handoff/
├── scripts/
└── task-state.json
```

## 工作流

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

### 4. 选题专项库

- 围绕用户拟投方向，收集目标期刊同类文章、相邻期刊文章、关键作者和高频参考文献。
- 只做专题分析，不把它改写成正文素材库。
- 实际 CNKI / Zotero / PDF / RAG 操作交给 `检索入库`。

### 5. Zotero / PDF / RAG 核验

- 核对集合结构、条目数、PDF 数、重复条目、无 PDF 条目和 RAG 导库状态。
- 先确认样本能召回，再引用 RAG 结论。

### 6. 期刊画像分析

- 题名风格：字数、主副标题比例、结构、常见动词、问题-对象结构。
- 选题趋势：年度聚类、栏目变化、热点/稳定/退潮/拥挤方向。
- 材料与方法：一手材料类型、方法分布、证据标准。
- 论证风格：问题提出、文献综述、段落节奏、结论方式。
- 参考文献生态：数量分布、中外比例、近年文献、期刊内互引、高频作者。
- 格式体例：摘要、关键词、标题层级、注释与参考文献、作者信息、英文项。

### 7. 投稿匹配评分

- 采用 100 分制。
- 评分要给证据，不要只给主观印象。
- 风险项单独扣分，不要掩盖成“总体不错”。

### 8. 选题建议与交接

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
- `journal-quantitative-analysis-report.md`
- `journal-title-style-report.md`
- `journal-topic-trend-report.md`
- `journal-method-material-report.md`
- `journal-argument-style-report.md`
- `journal-reference-ecology-report.md`
- `submission-fit-score.md`
- `topic-suggestion-report.md`
- `target-journal-decision.md`
- `handoff-to-downstream-skills.md`
- `wenheng-center-status.json`

## 需要阅读的 references

- `references/output-schema.md`
- `references/evidence-rules.md`
- `references/scoring-rubric.md`
- `references/quantitative-analysis-protocol.md`
- `references/handoff-to-jiansuo-ruku.md`
- `references/handoff-from-jiansuo-ruku.md`
- `references/topic-suggestion-protocol.md`
- `references/column-analysis-protocol.md`
- `references/multi-journal-comparison.md`
- `references/wenheng-contract.md`
- `references/downstream-handoff.md`
- `references/handoff-to-zhengwen-xiezuo.md`
- `references/handoff-to-wenzhang-runse.md`
- `references/handoff-to-cankao-wenxian.md`

## scripts

- `scripts/build_task_skeleton.py`：建立任务目录和初始状态文件。
- `scripts/validate_wenheng_status.py`：校验文衡状态 JSON。
- `scripts/score_fit.py`：汇总投稿匹配度分项。
- `scripts/analyze_title_corpus.py`：分析题名结构和基础趋势。
- `scripts/analyze_reference_ecology.py`：分析参考文献生态。
- `scripts/generate_quantitative_report.py`：生成数据性量化分析报告。
- `scripts/generate_topic_suggestions.py`：生成选题建议，不生成正式正文题名。
- `scripts/update_wenheng_status.py`：增量更新文衡状态并记录历史。
- `scripts/analyze_column_structure.py`：分析栏目生命周期和稳定性。

## 输出纪律

- 证据尽量落到数据库、官网、PDF 和 RAG。
- 不能确认的内容就写“待核验”。
- 不把分析写成正文，不把正文写成分析。
- 下游交接要明确：给谁、补什么、为什么补。
