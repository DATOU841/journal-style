# 输出结构

## 1. 任务目录

```text
journal-style-task/
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
└── task-state.json
```

## 2. `task-state.json`

```json
{
  "skill_id": "journal-style",
  "task_id": "",
  "journal_name": "",
  "journal_identity_status": "pending",
  "title_intake_status": "pending",
  "zotero_status": "pending",
  "rag_status": "pending",
  "metadata_analysis_status": "pending",
  "fulltext_analysis_status": "pending",
  "overall_journal_style_status": "blocked",
  "completion_label": "METADATA_ONLY_NOT_FULLTEXT_READY",
  "fit_score": null,
  "recommended_action": "unknown",
  "handoff_targets": [],
  "updated_at": ""
}
```

## 3. `wenheng-center-status.json`

```json
{
  "schema": "journal_style_wenheng_status_v1",
  "skill_id": "journal-style",
  "task_id": "",
  "task_name": "",
  "journal": {
    "name": "",
    "issn": "",
    "cn": "",
    "official_url": "",
    "submission_url": "",
    "identity_status": "pending"
  },
  "input": {
    "submission_title": "",
    "submission_abstract_path": "",
    "manuscript_path": "",
    "topic_keywords": [],
    "target_year_range": ""
  },
  "data_assets": {
    "title_list_path": "",
    "topic_library_path": "",
    "zotero_collections": [],
    "kb_ids": [],
    "official_evidence_path": ""
  },
  "pipeline_status": {
    "official_check": "pending",
    "title_intake": "pending",
    "title_screening": "pending",
    "topic_library": "pending",
    "zotero_pdf_rag": "pending",
    "metadata_analysis": "pending",
    "core_library_selection": "pending",
    "fulltext_analysis": "blocked",
    "submission_operations": "pending",
    "fit_evaluation": "pending",
    "overall_journal_style": "blocked"
  },
  "analysis_layers": {
    "metadata_layer_status": "pending",
    "fulltext_layer_status": "blocked",
    "completion_label": "METADATA_ONLY_NOT_FULLTEXT_READY",
    "fulltext_evidence": {
      "core_library_count": 0,
      "fulltext_sample_count": 0,
      "rag_available_rate": 0.0,
      "pdf_coverage_rate": 0.0
    }
  },
  "metrics": {
    "journal_title_count": 0,
    "topic_library_count": 0,
    "pdf_count": 0,
    "rag_doc_count": 0,
    "fit_score": null,
    "sample_coverage_rate": 0.0,
    "data_quality_grade": "low",
    "evidence_strength": "weak",
    "confidence": "low"
  },
  "decision": {
    "recommended_action": "unknown",
    "primary_risks": [],
    "required_fixes": [],
    "recommended_target_journals": []
  },
  "handoff": {
    "to_jiansuo_ruku": "",
    "to_zhengwen_xiezuo": "",
    "to_article_polish": "",
    "to_reference_footnote": ""
  },
  "updated_at": ""
}
```

新版任务应优先使用分层 `pipeline_status`：

```json
{
  "pipeline_status": {
    "official_check": "pending",
    "title_intake": "pending",
    "title_screening": "pending",
    "topic_library": "pending",
    "zotero_pdf_rag": "pending",
    "metadata_analysis": "pending",
    "core_library_selection": "pending",
    "fulltext_analysis": "blocked",
    "submission_operations": "pending",
    "fit_evaluation": "pending",
    "overall_journal_style": "blocked"
  }
}
```

`metadata_analysis=done` 不等于 `overall_journal_style=done`。只有 `completion_label=FULLTEXT_READY` 且全文/RAG 证据门禁满足时，才允许总状态完成。

Legacy 文件如果仍使用旧字段 `pipeline_status.analysis=done`，必须同时提供 `analysis_layers` 并证明 `fulltext_layer_status=done`。缺少 `analysis_layers` 时不得通过校验。

## 3.1 运行模式

任务应声明 `run_mode`：

- `light`：身份、题录趋势、栏目、作者机构等 metadata-only 分析。
- `standard`：默认题录/摘要层标准分析。
- `full`：完整下游可消费模式，要求 MinerU/mu 完整全文核心包、逐篇画像、聚合约束锁和评分回放校准。

`light` 和 `standard` 可在 metadata-only 终态结束，不能输出全文体例稳定结论。`full` 模式必须通过 MinerU/mu 全文链。

## 4. 必需产物清单

- `00-official/journal-identity-confirmation.md`
- `00-official/journal-official-and-web-evidence.md`
- `01-title-intake/journal-full-title-list.xlsx`
- `01-title-intake/journal-title-ingestion-log.md`
- `015-title-screening/title-screening-ledger.json`
- `015-title-screening/title-screening-gate.json`
- `02-topic-library/topic-special-library-plan.md`
- `02-topic-library/topic-related-title-list.xlsx`
- `02-topic-library/zotero-and-pdf-check-report.md`
- `02b-core-library/core-library-ledger.json`
- `02b-core-library/core-library-rejected.json`
- `025-rag-import/rag-import-handoff.md`
- `03-analysis/metadata-layer/journal-quantitative-analysis-report.md`
- `03-analysis/metadata-layer/journal-funding-topic-association-report.md`
- `03-analysis/metadata-layer/journal-funding-topic-association-statistics.json`
- `03-analysis/metadata-layer/journal-title-style-report.md`
- `03-analysis/metadata-layer/journal-topic-trend-report.md`
- `03-analysis/metadata-layer/journal-author-institution-network-report.md`
- `03-analysis/metadata-layer/journal-author-institution-network-statistics.json`
- `03-analysis/metadata-layer/journal-author-profile-and-byline-report.md`
- `03-analysis/metadata-layer/journal-author-profile-and-byline-statistics.json`
- `03-analysis/fulltext-layer/journal-rag-fulltext-pattern-report.md`
- `03-analysis/fulltext-layer/journal-rag-fulltext-pattern-statistics.json`
- `03-analysis/fulltext-layer/mu-fulltext-core-pack.json`
- `03-analysis/fulltext-layer/per-article-style-profiles.json`
- `03-analysis/fulltext-layer/journal-style-aggregation-bundle.json`
- `03-analysis/fulltext-layer/journal-method-material-report.md`
- `03-analysis/fulltext-layer/journal-argument-style-report.md`
- `03-analysis/fulltext-layer/journal-reference-ecology-report.md`
- `03-analysis/fulltext-layer/journal-reference-network-report.md`
- `03-analysis/fulltext-layer/journal-reference-network-statistics.json`
- `04-fit-evaluation/submission-fit-score.md`
- `04-fit-evaluation/journal-fit-scoring-model.json`
- `04-fit-evaluation/journal-submission-operations-report.md`
- `04-fit-evaluation/journal-submission-operations-statistics.json`
- `04-fit-evaluation/topic-suggestion-report.md`
- `04-fit-evaluation/target-journal-decision.md`
- `04-fit-evaluation/multi-journal-author-profile-comparison-report.md`
- `04-fit-evaluation/multi-journal-author-profile-comparison-statistics.json`
- `05-handoff/handoff-to-downstream-skills.md`
- `05-handoff/journal-polish-consumption-pack.json`
- `05-handoff/wenheng-center-status.json`
- `06-gates/completion-label.json`
- `06-gates/zotero-pdf-rag-handoff.json`
- `06-gates/abstract-metadata-ledger.json`
- `06-gates/core-library-selection.json`
- `06-gates/fulltext-claims.json`
- `06-gates/secret-boundary.json`
- `06-gates/mu-fulltext-pack.json`
- `06-gates/per-article-profile-complete.json`
- `06-gates/aggregation-threshold.json`
- `06-gates/provenance-required.json`
- `06-gates/scoring-replay-calibrated.json`

## 4.1 Sidecar 可选增强产物

检索入库 0.2.11 sidecar 存在时，可额外产出：

- `00-intake/jiansuo-sidecar-manifest.json`
- `02-topic-library/journal-style-rag-query-seed-plan.json`
- `03-analysis/metadata-layer/source-role-ecology-summary.json`
- `03-analysis/metadata-layer/bibliography-scope-coverage.json`

这些产物只增强来源角色、参考文献范围、RAG 查询种子和缺口提示；sidecar 缺失不得阻塞期刊风格分析主流程，也不得替代 MinerU/mu 完整全文核心包。

## 5. 量化分析报告字段

`03-analysis/journal-quantitative-analysis-report.md` 必须包含：

- 题录覆盖率
- 年度覆盖率
- PDF 覆盖率
- RAG 可用率
- 综合样本覆盖率
- 数据质量等级
- 证据强度
- 低置信警告

## 6. v0.1.1 网络分析报告字段

`03-analysis/journal-author-institution-network-report.md` 必须包含：

- 作者和机构字段缺失率
- 高频作者和高频机构
- 多作者题录比例
- 跨机构题录比例
- 作者合作边和机构合作边
- 年度新作者比例
- 证据强度和降级提示

`03-analysis/journal-author-institution-network-statistics.json` 必须保留同源统计字段，供后续评分、复核或文衡状态摘要引用。

`03-analysis/journal-reference-network-report.md` 必须包含：

- 来源文章数和参考文献记录数
- 篇均参考文献数
- 被引题名和被引年份缺失率
- 高频被引作者、题名和来源
- 共引边和作者共引边
- 核心文献候选
- 证据强度和降级提示

`03-analysis/journal-reference-network-statistics.json` 必须保留同源统计字段，供后续评分、复核或文衡状态摘要引用。

## 7. v0.1.2 作者公共身份与署名基金结构字段

`03-analysis/journal-author-profile-and-byline-report.md` 必须包含：

- 作者字段、职称字段、学位/身份字段、基金字段覆盖率
- 单作者、双作者、三人及以上署名结构
- 第一作者职称分布
- 第二作者身份分布
- 学生作者参与比例
- 高年资一作 + 学生二作线索
- 明确师生关系说明比例
- 通讯作者标注比例和位置分布
- 基金论文比例和基金层级分布
- 证据强度、降级提示和不得推断项

`03-analysis/journal-author-profile-and-byline-statistics.json` 必须保留同源统计字段，供后续评分、复核或文衡状态摘要引用。

## 8. v0.1.3 投稿运营与公开声誉证据字段

`04-fit-evaluation/journal-submission-operations-report.md` 必须包含：

- 来源构成和证据强度
- 官方投稿入口和投稿系统状态
- 官方审稿周期与第三方审稿周期线索分列
- 录用周期和见刊周期线索
- 费用政策和收费风险
- 公开声誉线索，按来源层级和正负面分类
- 可信性风险、同名刊/假官网/投稿中介风险和待核验项
- 对投稿决策的影响建议，但不得替代学术适配评分

`04-fit-evaluation/journal-submission-operations-statistics.json` 必须保留同源统计字段，供后续评分、复核或文衡状态摘要引用。

## 9. v0.1.3 RAG/全文样本模式挖掘字段

`03-analysis/journal-rag-fulltext-pattern-report.md` 必须包含：

- 样本范围、年份覆盖、栏目覆盖和证据强度
- 摘要长度、关键词数量和关键词复用线索
- 章节结构和标题层级统计
- 材料标记和方法标记分布
- 图表、图片、注释、参考文献线索
- 收稿、修回、录用、刊发日期线索
- 可计算周期和不可计算原因
- 降级提示和人工复核建议

`03-analysis/journal-rag-fulltext-pattern-statistics.json` 必须保留同源统计字段，供后续评分、复核或文衡状态摘要引用。

## 9.1 v0.2.0 MinerU/mu 完整全文与下游可消费约束字段

`03-analysis/fulltext-layer/mu-fulltext-core-pack.json` 必须符合 `journal_style_mu_fulltext_core_pack_v1`。这里的 `mu` 指 MinerU：由 `检索入库` 在入库环节把初始 PDF 文献处理成文字版本。journal-style 只验收和分析，不运行 MinerU，不下载 PDF。

`03-analysis/fulltext-layer/per-article-style-profiles.json` 必须包含逐篇 `per_article_style_profile_v1`，每篇至少覆盖题名、摘要、关键词、字数、段落、章节、引言、材料、方法、论证节奏、注释、参考文献和结论方式。

`03-analysis/fulltext-layer/journal-style-aggregation-bundle.json` 必须包含：

- `journal-style-constraints-lock`
- `journal-format-convention-profile`
- `journal-argument-preference-profile`
- `journal-reference-ecology-lock`
- `journal-polish-consumption-pack`

每项必须有 `sample_count`、`coverage`、`confidence`、`degrade_label` 和 `evidence_index`。

`05-handoff/journal-polish-consumption-pack.json` 使用真实 `journal_style_profile_v1`，供文章润色后续消费；不得使用 synthetic fixture 冒充正式画像。顶层必须包含 `confidence` 和 `conclusion_strength`，让下游零推断判断约束强度。`constraints.length_band` 只作参考展示，必须带 `advisory_only=true`，不得覆盖文章润色侧既有字数门禁。

`04-fit-evaluation/journal-fit-scoring-model.json` 必须符合 `journal_fit_scoring_model_v1`，声明不模拟具体主编、不预测录用，并包含已刊样本回放分数分布。

## 10. v0.1.4 基金与选题关联字段

`03-analysis/journal-funding-topic-association-report.md` 必须包含：

- 样本范围、基金字段覆盖率和证据强度
- 基金论文比例和基金层级分布
- 各基金层级的关键词、栏目、材料、方法交叉统计
- 基金论文与非基金论文的关键词差异
- 用户关键词在基金论文中的命中情况
- 降级提示和不得推断项

`03-analysis/journal-funding-topic-association-statistics.json` 必须保留同源统计字段，供后续评分、复核或文衡状态摘要引用。

## 11. v0.1.4 多期刊作者身份对比字段

`04-fit-evaluation/multi-journal-author-profile-comparison-report.md` 必须包含：

- 对比期刊清单、样本数和字段覆盖率
- 第一作者职称结构对比
- 第二作者身份结构对比
- 学生作者参与比例对比
- 高年资一作 + 硕士/博士二作线索对比
- 基金论文比例和基金层级分布对比
- 改投判断提示、降级提示和不得推断项

`04-fit-evaluation/multi-journal-author-profile-comparison-statistics.json` 必须保留同源统计字段，供后续评分、复核或文衡状态摘要引用。
