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

