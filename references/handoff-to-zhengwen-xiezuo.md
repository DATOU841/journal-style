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
