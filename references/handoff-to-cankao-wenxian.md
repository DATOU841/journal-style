# 给参考文献补注的交接协议

## 1. 交接定位

只交接参考文献生态缺口和补注方向，不直接伪造文献。正式交接应来自 `journal-reference-ecology-lock`。

## 2. 必填字段

```json
{
  "target_journal": "",
  "reference_ecology": {
    "reference_count_band": {"min": null, "max": null},
    "recent_ratio_target": null,
    "foreign_ratio_target": null,
    "self_journal_citation_target": null,
    "high_frequency_authors": [],
    "high_frequency_references": []
  },
  "user_reference_gaps": [],
  "recommended_supplement_searches": [],
  "evidence_index": []
}
```

## 3. 必须说明

- 高频作者和高频文献必须来自可追溯样本。
- 外文文献真实性要单独标注。
- 期刊内互引建议不得变成机械堆引用。
- 参考文献生态高置信结论必须满足样本和解析门槛，不足时只给补采方向。
