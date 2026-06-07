# 检索入库到 journal-style 的回传协议

## 1. 响应 JSON

```json
{
  "status": "success",
  "request_type": "journal_corpus",
  "zotero_collection": "",
  "item_count": 0,
  "pdf_count": 0,
  "kb_id": "",
  "rag_doc_count": 0,
  "failed_items": [],
  "quality_report": "",
  "handoff_path": ""
}
```

## 2. 状态取值

- `success`：条目、PDF、RAG 均达到验收要求。
- `partial`：至少一项未达标，但仍可降级分析。
- `failed`：不能进入期刊画像分析。

## 3. 验收标准

- 条目数达到目标数的 80% 以上。
- 若要求 PDF：PDF 率不低于 50%。
- 若要求 RAG：RAG 导库成功率不低于 80%。
- 无 PDF 条目、重复条目、失败条目必须列清。
- 必须有样本召回测试或等价可用性说明。

## 4. 失败处理

- `status = failed`：阻断流程，文衡标 `pipeline_status.rag_import = failed` 或对应失败阶段。
- `status = partial`：降级分析，量化报告标注样本不完整。
- PDF 率低于 30%：材料、方法、论证风格分析标低置信。
- RAG 可用率低于 50%：论证风格和参考文献生态不得给高置信结论。

## 5. 质量核验清单

- 条目数
- PDF 数
- RAG 文档数
- 重复条目
- 无 PDF 条目
- 样本召回
- 数据来源
- 失败原因

