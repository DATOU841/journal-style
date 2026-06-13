# journal-style 到检索入库的请求协议

## 1. 适用场景

- 全量题录库采集
- 选题专项库采集
- 相邻 / 竞品期刊参照库采集
- 用户参考文献核验库补充

## 2. 请求 JSON

```json
{
  "request_type": "journal_corpus",
  "journal_name": "",
  "year_range": "2020-2025",
  "target_count": 500,
  "include_pdf": true,
  "include_rag": true,
  "fields": ["title", "author", "institution", "abstract", "keywords", "references"],
  "exclude_rules": ["会议综述", "书评"],
  "zotero_collection_name": "",
  "kb_name": "",
  "acceptance": {
    "min_item_rate": 0.8,
    "min_pdf_rate": 0.5,
    "min_rag_success_rate": 0.8,
    "require_recall_test": true,
    "require_item_level_receipt": true
  },
  "secret_policy": "env_only_no_process_arg_key",
  "notes": ""
}
```

## 3. `request_type`

- `journal_corpus`：目标期刊全量题录库。
- `topic_library`：围绕用户方向的选题专项库。
- `peer_journals`：相邻或竞品期刊参照库。
- `user_refs`：用户稿件参考文献核验库。

## 4. 请求示例

### 4.1 全量题录库

```json
{
  "request_type": "journal_corpus",
  "journal_name": "目标期刊",
  "year_range": "2020-2025",
  "target_count": 300,
  "include_pdf": true,
  "include_rag": true,
  "fields": ["title", "author", "institution", "abstract", "keywords", "column", "references"],
  "exclude_rules": ["会议综述", "书评", "征稿启事"],
  "zotero_collection_name": "journal-style-目标期刊-全量题录",
  "kb_name": "kb-journal-style-目标期刊",
  "acceptance": {
    "min_item_rate": 0.8,
    "min_pdf_rate": 0.5,
    "min_rag_success_rate": 0.8,
    "require_recall_test": true,
    "require_item_level_receipt": true
  },
  "secret_policy": "env_only_no_process_arg_key"
}
```

### 4.2 选题专项库

```json
{
  "request_type": "topic_library",
  "journal_name": "目标期刊",
  "year_range": "2018-2025",
  "target_count": 120,
  "include_pdf": true,
  "include_rag": true,
  "fields": ["title", "author", "institution", "abstract", "keywords", "references"],
  "exclude_rules": ["偏题材料", "无 PDF 条目"],
  "zotero_collection_name": "journal-style-目标期刊-选题专项库",
  "kb_name": "kb-journal-style-目标期刊-topic"
}
```

## 5. 发起门禁

- 期刊身份已确认或已标明仍存在身份风险。
- 时间范围明确。
- 排除规则明确。
- 目标数量明确。
- 需要 PDF / RAG 时必须写明验收标准。
- 需要 Zotero/PDF/RAG 时必须要求 item-level receipt；runner report 不得作为正式完成依据。
- 密钥必须通过环境变量或服务器受控 secret 文件加载，不得通过进程参数传递。
