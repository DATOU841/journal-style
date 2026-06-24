# 期刊适配校准评分模型协议

## 定位

`journal_fit_scoring_model_v1` 是基于已刊核心样本回放校准的适配评分器。它不是主编模拟器，不预测录用概率，不替代编辑部判断。

内部可用 `editorial_preference_proxy_v1` 作别名，但对外必须说明这是期刊适配近似模型。

## 必须声明

- `not_editor_simulation=true`
- `no_acceptance_prediction=true`
- `calibration.status=calibrated`
- `dimensions[].rationale` 必须说明该维度权重来自哪类已刊样本证据或约束锁

## 校准要求

正式用于用户稿件定位前，必须先对已刊核心样本回放评分，并形成：

- `replay_scores[]`
- `published_score_distribution.min`
- `published_score_distribution.q1`
- `published_score_distribution.median`
- `published_score_distribution.q3`
- `published_score_distribution.max`

`published_score_distribution` 必须由 `replay_scores[]` 计算得出，不得用常量表、经验表或占位分布冒充回放。`calibration.source` 必须标为 `per_article_profile_replay`。

模型必须携带 `scoring_constraints`，来源为 `journal_style_aggregation_bundle`，至少包含：

- `section_hierarchy.section_min/section_max`
- `abstract_keywords.keyword_min/keyword_max`
- `reference_constraints.reference_min/reference_max`

未完成回放校准时，不得给用户稿件做分位定位。

## 输出落点

- `journal-fit-scoring-model.json` 只保存模型本体、维度权重、维度依据和已刊样本分布。
- `submission-fit-score.md` 保存用户稿相对位置、维度扣分原因和补强建议。
- 用户稿结果不得写回模型本体；模型不得包含录用概率或具体编辑个人模拟。
- 用户稿评分必须消费模型中的目标期刊 `scoring_constraints`；通用区间只能作为缺字段时的 fallback，并必须标明 `source=fallback`。

## 测试轮次

- 第 1 轮：已刊核心样本回放。
- 第 2 轮：边界样本抽查。
- 第 3 轮：用户稿 fixture 差距定位。

最少完成第 1 轮才能作为初版校准评分器；推荐完成 3 轮后锁定评分标准。
