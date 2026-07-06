# 单一全量深度模式协议

## 定位

`journal-style` 的正式任务只有 `full` 全量深度模式。历史 `light`、`standard` 和 `metadata-only` 只能作为旧数据中的阻塞标签或离线调试概念出现，不再作为正式交付终态。

## 正式路径

- 路径：`common` + `metadata` + `fulltext` + `scoring`。
- `metadata` 只表示题录/摘要层中间证据，不能单独完成任务。
- MinerU/mu 完整全文核心包是 hard gate。
- 必须先逐篇画像，再聚合约束锁，再完成已刊样本回放校准评分。
- 只有 Step10 handoff 全链完成后，才允许输出正式 C03 profile 和 `journal-polish-consumption-pack`。

## 阻塞态

缺少 MinerU/mu 完整全文包、逐篇画像、聚合包、评分校准或 provenance 时，任务必须停在对应步骤。`METADATA_ONLY_NOT_FULLTEXT_READY` 只能表示“材料不足、不能交付”，不能表示期刊画像已完成。

## 防逃逸规则

- runner 必须把未识别、空值、历史 `light` 和历史 `standard` 都解析为 `full`。
- 状态机不得存在正式 `metadata_terminal` 路径。
- 任何正式 C03 profile 必须来自 Step10 handoff，并带有文衡 source lock、`source_run_id` 和 H08 evidence。
- 离线 legacy/debug 输出不得成为 production evidence，不得写入正式 C03。
