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
- 参考文献生态分析
- 作者机构网络分析
- 作者公共身份与署名基金结构分析
- 多期刊作者身份对比
- 参考文献网络分析
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
- `journal-submission-operations-report.md`
- `journal-submission-operations-statistics.json`
- `journal-quantitative-analysis-report.md`
- `journal-funding-topic-association-report.md`
- `journal-funding-topic-association-statistics.json`
- `journal-rag-fulltext-pattern-report.md`
- `journal-rag-fulltext-pattern-statistics.json`
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
- `references/scoring-rubric.md`
- `references/quantitative-analysis-protocol.md`
- `references/journal-submission-operations-protocol.md`
- `references/fulltext-article-pattern-mining-protocol.md`
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

- `scripts/build_task_skeleton.py`：建立任务目录和初始状态文件。
- `scripts/validate_wenheng_status.py`：校验文衡状态 JSON。
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
