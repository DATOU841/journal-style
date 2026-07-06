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

### run-mode path gate

- 正式任务只推进 common + metadata + fulltext + scoring 路径。
- 历史 `light` / `standard` / 空模式必须解析为 `full`，不得进入 metadata terminal。
- MinerU/mu 完整全文包是正式任务 hard gate。
- metadata-only 只能作为阻塞态，不得作为正式完成态。

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

### mu-fulltext-pack

- 只验收 `检索入库` 上游交回的 MinerU/mu 完整全文核心包。
- `mu` 指 MinerU：入库环节把初始 PDF 文献处理成文字版本的方式。
- 普通 RAG 召回包不能替代 MinerU/mu 完整全文包。
- full 模式 ready 篇必须包含 `section_tree`、`paragraph_sequence`、`reference_list`；缺任一项不计入 ready 篇数。
- `notes` 是建议结构字段，低覆盖率只降级注释体例分析，不单独阻断 ready。
- 就绪篇数低于 10 篇判 `NO_GO`；10-19 篇只允许 `DEGRADED` 初步偏好。

### zotero-pdf-rag-handoff

- 原始交接输入固定为 `025-rag-import/zotero-pdf-rag-handoff-input.json`。
- `06-gates/zotero-pdf-rag-handoff.json` 只保存 `gate_runner.py` 对原始输入现场生成的 sha-chained receipt。
- 禁止把原始 handoff 输入写在 `06-gates/` 下；否则 runner 重跑 gate 时会覆盖输入，造成下一轮无法反查 item-level receipts。

### per-article-profile-complete

- 每篇就绪 MinerU/mu 全文必须有一份逐篇画像。
- 逐篇画像必须包含题名、摘要、关键词、字数、段落、章节、引言、材料、方法、论证、注释、参考文献和结论方式维度。
- 每篇必须有 `evidence_index`，不得输出可直接粘贴的正文。

### aggregation-threshold

- 聚合必须消费逐篇画像。
- 少于 10 篇只能样本观察；20 篇以上才允许稳定体例结论。
- 论证风格和参考文献生态高置信结论要求 30 篇以上。

### provenance-required

- 下游消费包和约束锁必须有 `evidence_index`。
- 证据必须能反查到 article_id、source path 和 provenance。

### scoring-replay-calibrated

- `journal_fit_scoring_model_v1` 必须声明不模拟具体主编、不预测录用。
- 必须先完成已刊样本回放，并形成已刊样本分数分布。
- 未校准不得用于用户稿件分位定位。
- `submission-fit-score.md` 必须在评分模型校准之后生成；不得先出用户稿适配分再事后校准。
- `submission-fit-ready` gate 必须复核 `journal-fit-scoring-model.json` 已通过 `scoring-replay-calibrated`，否则即使 `submission-fit-score.md` 已存在也不能推进。
