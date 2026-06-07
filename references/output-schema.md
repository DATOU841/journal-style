# 输出结构

## 1. 任务目录

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
  "analysis_status": "pending",
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
    "topic_library": "pending",
    "pdf_check": "pending",
    "rag_import": "pending",
    "analysis": "pending",
    "fit_evaluation": "pending"
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

## 4. 必需产物清单

- `00-official/journal-identity-confirmation.md`
- `00-official/journal-official-and-web-evidence.md`
- `01-title-intake/journal-full-title-list.xlsx`
- `01-title-intake/journal-title-ingestion-log.md`
- `02-topic-library/topic-special-library-plan.md`
- `02-topic-library/topic-related-title-list.xlsx`
- `02-topic-library/zotero-and-pdf-check-report.md`
- `025-rag-import/rag-import-handoff.md`
- `03-analysis/journal-rag-fulltext-pattern-report.md`
- `03-analysis/journal-rag-fulltext-pattern-statistics.json`
- `03-analysis/journal-quantitative-analysis-report.md`
- `03-analysis/journal-title-style-report.md`
- `03-analysis/journal-topic-trend-report.md`
- `03-analysis/journal-method-material-report.md`
- `03-analysis/journal-argument-style-report.md`
- `03-analysis/journal-reference-ecology-report.md`
- `03-analysis/journal-author-institution-network-report.md`
- `03-analysis/journal-author-institution-network-statistics.json`
- `03-analysis/journal-author-profile-and-byline-report.md`
- `03-analysis/journal-author-profile-and-byline-statistics.json`
- `03-analysis/journal-reference-network-report.md`
- `03-analysis/journal-reference-network-statistics.json`
- `04-fit-evaluation/submission-fit-score.md`
- `04-fit-evaluation/journal-submission-operations-report.md`
- `04-fit-evaluation/journal-submission-operations-statistics.json`
- `04-fit-evaluation/topic-suggestion-report.md`
- `04-fit-evaluation/target-journal-decision.md`
- `05-handoff/handoff-to-downstream-skills.md`
- `05-handoff/wenheng-center-status.json`

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
