# 文衡接入契约

## 1. 状态字段原则

- 只写脱敏元数据。
- 不写正文全文，不写检索细节，不写 PDF 正文。
- 任何低置信结论都要显式标记。
- 字段扩展必须兼容 `journal_style_wenheng_status_v1`。

## 2. 关键字段

- `journal.identity_status`
- `pipeline_status`
- `metrics.fit_score`
- `metrics.sample_coverage_rate`
- `metrics.data_quality_grade`
- `metrics.evidence_strength`
- `decision.recommended_action`
- `handoff`

## 3. 扩展 metrics

```json
{
  "sample_coverage_rate": 0.0,
  "data_quality_grade": "low",
  "evidence_strength": "weak"
}
```

## 4. 取值规则

- `data_quality_grade`：`high|medium|low`
- `evidence_strength`：`strong|medium|weak`
- `sample_coverage_rate`：`title_coverage_rate * 0.4 + pdf_coverage_rate * 0.3 + rag_availability_rate * 0.3`

## 5. 门禁

- `identity_status != confirmed` 时，不要写成“高适配”。
- `rag_doc_count == 0` 时，不要写成“论证风格已完成分析”。
- `fit_score == null` 时，不要交给正文写作当作已完成画像。
- `data_quality_grade == low` 时，推荐动作不得直接写 `submit`。
- `evidence_strength == weak` 时，文衡前台必须显示“待补证据”。

