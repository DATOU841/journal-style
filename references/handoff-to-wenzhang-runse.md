# 给文章润色的交接协议

## 1. 交接定位

只给题名、摘要、关键词、体例、注释参考文献和论证节奏约束，不改正文。正式交接应优先使用 `journal-polish-consumption-pack.json`，其 schema 为 `journal_style_profile_v1`。

## 2. 必填字段

```json
{
  "schema": "journal_style_profile_v1",
  "target_journal": "",
  "source_evidence_scope": "mu_fulltext_core_pack",
  "metadata_only": false,
  "sample_count": 0,
  "confidence": "low",
  "conclusion_strength": "sample_observation",
  "degrade_label": "待补材料",
  "constraints": {
    "title_style": {
      "avg_length": null,
      "subtitle_ratio": null,
      "patterns": [],
      "high_frequency_verbs": []
    },
    "abstract_keywords": {
      "abstract_length_range": "",
      "keyword_min": null,
      "keyword_max": null,
      "keyword_order_habits": []
    },
    "length_band": {
      "min": null,
      "max": null,
      "advisory_only": true,
      "source": "reference_only"
    },
    "paragraph_band": {"min": null, "max": null},
    "section_hierarchy": {"section_min": null, "section_max": null, "subsection_habit": ""},
    "notes_convention": {"type": "", "content_types": []},
    "reference_constraints": {
      "reference_min": null,
      "reference_max": null,
      "recent_ratio_target": null,
      "foreign_ratio_target": null,
      "self_journal_citation_target": null
    },
    "argument_rhythm": {
      "preferred": []
    }
  },
  "gap_checklist": [],
  "evidence_index": []
}
```

## 3. 必须说明

- 题名结构建议只给模式，不生成正文式题名。
- 摘要和关键词只给长度、数量、顺序习惯。
- `constraints.length_band` 只作参考展示，必须带 `advisory_only=true`，不得覆盖文章润色当前字数门禁。
- 结论尺度和术语倾向必须有证据来源。
- `metadata_only=true` 时不得交接全文体例、论证风格、注释和参考文献生态约束。
- 普通 RAG 片段不得替代 MinerU/mu 完整全文包。

## 4. 可选人工评审记忆 overlay

文章润色可 best-effort 读取 `review_memory_overlay`，并把它作为独立建议 ledger，不得混入证据 ledger：

```json
{
  "review_memory_overlay": {
    "present": true,
    "provenance": "human_review_memory",
    "source_evidence_scope": "human_review_memory",
    "not_evidence": true,
    "pack_ref": "00-intake/journal-review-memory-pack.json",
    "applies_to": "wenzhang-runse",
    "advisory_only": true
  }
}
```

消费边界：

- 可读取 `format_specs`、`verified_fix_strategies`、`ai_tone_replacements` 和 `avoid_patterns`。
- `format_specs.length_band.advisory_only` 必须保持 `true`，不得覆盖文章润色现有字数门禁。
- `verified_fix_strategies.fix_kind=evidence_action` 只能路由检索入库或 RAG 补证，不得由润色链直接编造引用。
- 任何情况下都不得把人工记忆写成 `source_excerpt`。
