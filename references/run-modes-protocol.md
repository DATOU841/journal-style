# 运行模式协议

## 定位

`journal-style` 支持 `light`、`standard`、`full` 三种运行模式。模式只决定本次任务要推进到哪一类证据终态，不降低对应终态的证据门槛。

## light

用于期刊身份、题录趋势、栏目结构、作者机构网络等 metadata-only 分析。

- 路径：`common` + `metadata` + `metadata_terminal`
- 不要求 MinerU/mu 完整全文包。
- 只能输出 `METADATA_ONLY_NOT_FULLTEXT_READY` 或同等级的非全文完成标签。
- 不得输出全文体例、论证风格、参考文献生态的稳定结论。

## standard

用于题录/摘要层的标准期刊分析与投稿辅助判断。

- 路径：`common` + `metadata` + `metadata_terminal`
- 不要求 MinerU/mu 完整全文包。
- 可输出题名、摘要、选题趋势、作者机构、基金等元数据层结论。
- 全文风格和下游可执行全文约束仍必须标待补材料。

## full

用于下游可消费的完整期刊约束生产。

- 路径：`common` + `metadata` + `fulltext` + `scoring`
- 要求 `检索入库` 上游交付 MinerU/mu 完整全文核心包。
- 必须先逐篇画像，再聚合约束锁，再完成已刊样本回放校准评分。
- 只有 full 模式可以输出稳定全文体例约束和 `journal-polish-consumption-pack`。

## 防逃逸规则

- 低模式不能绕过全文证据门槛输出 full 模式结论。
- full 模式不能因为存在 metadata 终态而跳过 MinerU/mu 全文链。
- runner 必须按模式过滤状态机 step；`paths` 字段是执行约束，不是装饰字段。
