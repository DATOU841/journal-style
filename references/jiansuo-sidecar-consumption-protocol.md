# 检索入库 0.2.11 sidecar 消费协议

## 定位

journal-style 对 `检索入库 0.2.11` 的 2.5 后 sidecar 产物采用 best-effort 消费：
- 缺失 sidecar 不阻断主流程
- 只消费 metadata / pointer / gap / plan
- 不读取 `full.md` 正文、不读 PDF 正文、不读 Zotero DB、不读 RAG chunk、不连向量库

## 可消费产物

- `02-kb-builder/zotero-reference-full-bibliography.md`
- `025-rag-import/fulltext/fulltext-index.json`
- `025-rag-import/fulltext/<stable-id>/manifest.json`
- `025-rag-import/mineru-job-ledger.jsonl`
- `026-knowledge-workbench/downstream-consumption-manifest.json`
- `026-knowledge-workbench/source-role-register.json`
- `026-knowledge-workbench/rag-query-seed-pack.json`
- `026-knowledge-workbench/gap-ledger.json`
- `026-knowledge-workbench/sources/*.md`

## 读取规则

- `source-role-register.json`：只用于来源角色、期刊生态、理论锚点、比较材料、一手材料的 metadata 识别。
- `rag-query-seed-pack.json`：只转换成查询种子计划，不执行 RAG。
- `zotero-reference-full-bibliography.md`：用于任务全量文献范围和正式入库范围的覆盖差异，不读 Zotero DB。
- `fulltext-index.json` / `manifest.json`：只读全文可用性、标题、sha256、向量化状态、`full_md_path` 指针；`full.md` 不打开。
- `gap-ledger.json`：用于降级、补采和过度确定抑制。

## 输出

- `00-intake/jiansuo-sidecar-manifest.json`
- `03-analysis/metadata-layer/source-role-ecology-summary.json`
- `03-analysis/metadata-layer/bibliography-scope-coverage.json`
- `02-topic-library/journal-style-rag-query-seed-plan.json`

## 安全边界

- 发现 `token` / `cookie` / `api_key` / `full_zip_url` / `chunk_text` / `vector` / `embedding` / `full_md` 内容时必须 fail-closed。
- `full_md_path` 只允许作为指针字段。
- sidecar 存在不等于全文体例分析完成。

## 回退

sidecar 缺失时，回退到 journal-style 既有交接面和 metadata-only 流程，不阻断期刊画像主流程。
