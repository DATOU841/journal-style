# 检索入库到 journal-style 的回传协议

## 1. 响应 JSON

```json
{
  "status": "success",
  "request_type": "journal_corpus",
  "zotero_collection": "",
  "task_collection_binding": "live",
  "item_count": 0,
  "pdf_count": 0,
  "kb_id": "",
  "rag_doc_count": 0,
  "item_receipts": [
    {
      "item_key": "",
      "title": "",
      "in_collection": true,
      "pdf_ready": false,
      "rag_indexed": false,
      "recall_ok": false,
      "reason": ""
    }
  ],
  "failed_items": [],
  "duplicate_items": [],
  "no_pdf_items": [],
  "recall_test": {
    "sampled": 0,
    "passed": 0
  },
  "quality_report": "",
  "handoff_path": "",
  "redaction": "no key/token/cookie/fulltext/RAG chunk/Zotero DB"
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
- 必须有逐条 item-level receipt；只给总数不得判定 `success`。
- `task_collection_binding=missing` 直接失败，不允许继续到 RAG/全文分析。
- runner report 只作诊断，不作正式完成依据。

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

## 6. 0.2.11 sidecar 说明

`02-kb-builder/zotero-reference-full-bibliography.md`、`025-rag-import/fulltext/fulltext-index.json`、`025-rag-import/fulltext/<stable-id>/manifest.json`、`025-rag-import/mineru-job-ledger.jsonl`、`026-knowledge-workbench/downstream-consumption-manifest.json`、`026-knowledge-workbench/source-role-register.json`、`026-knowledge-workbench/rag-query-seed-pack.json`、`026-knowledge-workbench/gap-ledger.json` 与 `026-knowledge-workbench/sources/*.md` 都属于可选增强输入。

缺失时不得阻断 journal-style 主流程。`full_md_path` 只作指针，`full.md` 正文不得被 journal-style 默认打开。
