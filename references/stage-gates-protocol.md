# 阶段 Gate 协议

## 定位

本协议约束 `journal-style` 期刊画像任务的阶段闸门。`journal-style` 只做分析、请求和验收，不直接执行 CNKI、Zotero、PDF 获取、RAG 导库或 vector store 写入。

每个 gate 必须 fail-closed：无证据不是 PASS，缺 receipt 不是 PASS，metadata-only 不能提升为 fulltext-ready。

## 统一输出

每个 gate 输出 JSON：

```json
{
  "gate": "",
  "verdict": "PASS|DEGRADED|NO_GO",
  "problems": [],
  "warnings": [],
  "details": {},
  "no_claims": {
    "metadata_only_completed": false,
    "fulltext_ready_without_rag": false,
    "journal_style_completed_without_fulltext": false
  }
}
```

## Gate 列表

### no-metadata-only-completion

- `metadata_analysis=done` 只表示题录/摘要层完成。
- `overall_journal_style` 只有在 `fulltext_analysis=done` 且 `completion_label=FULLTEXT_READY` 时才能完成。
- `completion_label=FULLTEXT_READY` 必须同时满足：全文样本不少于 20、RAG 可用率不低于 0.5、PDF 覆盖率不低于 0.2。

### zotero-pdf-rag-handoff

- 只验收 `检索入库` 回传。
- `item_receipts` 是 authority；runner report 不是 authority。
- `status=success` 必须有 task collection binding、item-level receipts、PDF/RAG 数量和召回测试。

### abstract-metadata-ledger

- 只允许题名、作者、机构、摘要、关键词、期刊、日期、卷期页、DOI/URL、item key、PDF ready 等元数据。
- 禁止 PDF 绝对路径、全文、RAG chunk、vector、Zotero DB、cookie、token、key。

### core-library-selection

- 核心库必须占初筛保留库 25%-40%。
- 入选条目必须有多因子打分。
- 落选条目必须有 reason。

### no-fulltext-claim-without-rag

- 全文层结论必须带 provenance，可追溯到 source item 或 RAG doc。
- 全文样本少于 10 篇只能写样本观察；少于 20 篇不得写全刊稳定风格。

### secret-boundary

- 禁止 `--api-key=<value>` 或等价进程参数密钥。
- 密钥只能通过环境变量或服务器受控 secret 文件加载。
- evidence 不得包含 key/token/cookie。

