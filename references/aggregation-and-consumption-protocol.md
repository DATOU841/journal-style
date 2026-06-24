# 聚合锁与下游消费包协议

## 定位

聚合层消费逐篇画像，产出下游可执行的期刊约束。聚合不是简单均值，而是基于逐篇分布生成区间、中位数、四分位、众数和降级标签。

## 必要聚合产物

- `journal-style-constraints-lock`
- `journal-format-convention-profile`
- `journal-argument-preference-profile`
- `journal-reference-ecology-lock`
- `journal-polish-consumption-pack`

`journal-polish-consumption-pack` 使用真实 `journal_style_profile_v1` schema，供 `文章润色` 后续消费。

## 强制元数据

每个聚合产物必须包含：

- `sample_count`
- `coverage`
- `confidence`
- `conclusion_strength`
- `degrade_label`
- `evidence_index`

## 样本门槛

- 少于 10 篇：只允许样本观察。
- 10-19 篇：只允许初步偏好。
- 20 篇以上：允许稳定体例结论。
- 论证风格、参考文献生态高置信结论要求 30 篇以上。

## 下游边界

给 `文章润色`、`正文写作`、`参考文献补注` 的内容只能是约束、差距、证据和补采需求，不写正文，不润色正文，不生成可抄写段落。
