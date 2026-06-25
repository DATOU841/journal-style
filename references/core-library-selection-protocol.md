# 核心库筛选协议

## 定位

核心库用于全文格式、论证风格、参考文献生态和下游交接分析。核心库筛选发生在标题层初筛与 Zotero/PDF/RAG 回传之后。

核心库不是“所有下载成功的文章”，也不是“题名看起来相近的文章”。它必须由多因子打分和覆盖约束共同决定。

## 比例

核心库占初筛保留库的 25%-40%。比例越界时不得 PASS。

## 建议权重

| 因子 | 权重 |
| --- | --- |
| 与用户题目相近度 | 0.25 |
| 栏目相近度 | 0.15 |
| 材料/方法相近度 | 0.15 |
| 理论/艺术史相关度 | 0.15 |
| 全文可用性 | 0.15 |
| 年度/栏目代表性 | 0.15 |

## 输出

`core-library-ledger.json`：

```json
{
  "screened_count": 0,
  "selected": [
    {
      "title": "",
      "item_key": "",
      "selected": true,
      "scores": {},
      "total": 0.0,
      "coverage_tags": []
    }
  ],
  "rejected": [
    {
      "title": "",
      "item_key": "",
      "reason": ""
    }
  ]
}
```

落选原因必须明确。高相关但缺全文的文章不能被静默丢弃，应进入 `pending_fulltext_only_candidate`。

## Sidecar 增强

当存在 `source-role-register.json` 或 sidecar manifest 时，可额外写入 `source_role_tags`、`sidecar_role_evidence` 和 `sidecar_context`，但只允许：

- 对 `same_journal` / `same_column` / `same_topic` / `target_journal_ecosystem` 做小幅 metadata 增益
- 对 `theory_anchor` / `comparison_material` / `primary_source` 仅打标签，不改变 25%-40% gate
- 缺失 sidecar 时完全回退旧逻辑
