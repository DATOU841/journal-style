# MinerU/mu 完整全文核心包协议

## 定位

`mu_fulltext_core_pack` 是 `检索入库` 在 PDF 获取、OCR/解析和 MinerU/mu 处理后交给 `journal-style` 的完整全文材料包。这里的 `mu` 指 MinerU：在入库环节把初始 PDF 文献处理成可分析文字版本的处理方式。

`journal-style` 只验收和分析该包，不执行 CNKI/WoS/Zotero/PDF 获取，不运行 MinerU，不导入 RAG。

## 与普通 RAG 包的区别

- 普通 RAG 包用于片段召回和证据定位，不保证单篇文章完整。
- MinerU/mu 完整全文包必须提供整篇规范化文本、章节树、段落序列、注释和参考文献表。
- RAG 可用不等于 MinerU/mu 完整全文可用；不得用 RAG 片段点亮全文体例分析。

## 必填字段

包级 schema 为 `journal_style_mu_fulltext_core_pack_v1`。每篇文章至少包含：

- `article_id`
- `title`
- `authors`
- `year`
- `column`
- `mu_fulltext`
- `fulltext_sha256`
- `core_library_joined`
- `provenance.source_ledger`
- `provenance.extraction_method`
- `provenance.mu_version`
- `section_tree`
- `paragraph_sequence`
- `reference_list`

建议字段：

- `abstract`
- `keywords`
- `notes`
- `figures_tables`
- `page_range`
- `char_count_total`

## 验收规则

- 包文件必须在 Step0 material-intake manifest 注册并 sha 绑定。
- 每篇文章必须能 join 回核心库。
- `fulltext_sha256` 必须匹配 `mu_fulltext` 当前文本。
- full 模式下，`section_tree`、`paragraph_sequence`、`reference_list` 是硬 required；缺任一项的文章不计入 ready 篇数。
- `notes` 是建议字段；缺失会降低注释体例分析能力，但不单独使该篇文章失去 ready 资格。
- 就绪篇数低于 10 篇时，不得进入全文体例画像。
- 10-19 篇只能输出初步偏好。
- 20 篇以上才允许稳定体例结论。
- 论证风格、参考文献生态高置信结论建议 30 篇以上。

## 输出纪律

证据不足时输出待补材料请求。不得用题录、摘要或 RAG 片段补写缺失全文字段。
