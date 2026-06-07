# 多期刊作者身份对比协议

## 定位

多期刊作者身份对比用于比较目标期刊与相邻期刊在作者职称、学位/身份、署名结构、学生作者参与、通讯作者和基金支撑方面的差异。它服务改投判断和目标期刊选择，不推断具体期刊的私人关系、内部录用倾向或投稿捷径。

## 输入

输入为多个期刊的 `journal-author-profile-and-byline-statistics.json`，也可由同等字段的 JSON 汇总表替代。

每个期刊至少应包含：

- `journal_name`
- `record_count`
- `author_title_coverage_rate`
- `author_stage_or_degree_coverage_rate`
- `fund_field_coverage_rate`
- `author_count_distribution`
- `first_author_title_distribution`
- `second_author_stage_distribution`
- `student_author_record_ratio`
- `senior_first_student_second_ratio`
- `senior_first_master_second_ratio`
- `senior_first_phd_second_ratio`
- `funded_record_ratio`
- `fund_level_distribution`
- `evidence_strength`

## 指标

- 各期刊样本数和字段覆盖率。
- 第一作者职称结构对比。
- 第二作者身份结构对比。
- 学生作者参与比例对比。
- 高年资一作 + 硕士/博士二作线索对比。
- 基金论文比例对比。
- 基金层级分布对比。
- 作者画像相对适配提示。

## 判断规则

- 少于 2 个期刊：不得生成对比结论。
- 任一期刊样本低于 50 条：该期刊对比只能标“样本不足”。
- 职称或身份字段覆盖率低于 50%：不得比较作者身份结构强差异。
- 基金字段覆盖率低于 50%：不得比较基金支撑强差异。
- 不得从作者身份对比推断录用倾向、私人关系或投稿捷径。

## 输出

- `04-fit-evaluation/multi-journal-author-profile-comparison-report.md`
- `04-fit-evaluation/multi-journal-author-profile-comparison-statistics.json`

报告必须包含：

- 对比期刊清单、样本数和字段覆盖率。
- 作者身份结构核心指标对比。
- 基金支撑结构对比。
- 适合进一步补证据的期刊和字段。
- 改投判断提示，但不得替代投稿匹配评分。
- 降级提示和不得推断项。
