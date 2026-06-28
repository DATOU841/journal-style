# 给正文写作的交接协议

## 1. 交接定位

只交接期刊画像和写作约束，不写正文，不给可直接粘贴的正文段落。交接内容应来自逐篇画像聚合后的约束锁。

## 2. 必填字段

```json
{
  "target_journal": "",
  "fit_score": null,
  "confidence": "low",
  "problem_consciousness": [],
  "structure_constraints": {
    "section_count_band": {"min": null, "max": null},
    "hierarchy_depth": null,
    "subsection_habit": ""
  },
  "section_rhythm": [],
  "argument_style": {
    "intro_patterns": [],
    "argument_rhythm": [],
    "conclusion_patterns": []
  },
  "material_method_requirements": [],
  "avoid_patterns": [],
  "pending_evidence": [],
  "evidence_index": []
}
```

## 3. 必须说明

- 期刊接受的问题意识类型。
- 结构偏好。
- 论证风格偏好。
- 材料和方法要求。
- 不宜触碰的写法。
- 低置信点和待补证据。
- 不交接可直接粘贴的段落、题名或句子。
- 全文结构约束必须来自 MinerU/mu 完整全文逐篇画像。

## 4. 可选人工评审记忆 overlay

正文写作可 best-effort 读取 `review_memory_overlay`，但它永远不是证据：

```json
{
  "review_memory_overlay": {
    "present": true,
    "provenance": "human_review_memory",
    "source_evidence_scope": "human_review_memory",
    "not_evidence": true,
    "pack_ref": "00-intake/journal-review-memory-pack.json",
    "applies_to": "zhengwen-xiezuo",
    "advisory_only": true
  }
}
```

消费边界：

- 只读取 `style_hints`、`avoid_patterns` 和 `abstract_conclusion_rules` 作为前塑型提示。
- 不读取 `source_excerpt`，也不得把人工记忆转写成事实证据。
- 与 G07 active rules、`journal_style_profile_v1` 或正式 RAG grounding 冲突时，人工记忆让位并记录 `review_memory_conflicts`。
