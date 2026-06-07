# 文衡接入契约

## 1. 状态字段原则

- 只写脱敏元数据。
- 不写正文全文，不写检索细节，不写 PDF 正文。
- 任何低置信结论都要显式标记。

## 2. 关键字段

- `journal.identity_status`
- `pipeline_status`
- `metrics.fit_score`
- `decision.recommended_action`
- `handoff`

## 3. 门禁

- `identity_status != confirmed` 时，不要写成“高适配”。
- `rag_doc_count == 0` 时，不要写成“论证风格已完成分析”。
- `fit_score == null` 时，不要交给正文写作当作已完成画像。

