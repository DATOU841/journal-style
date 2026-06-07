# 期刊投稿运营与公开声誉证据分析协议

## 定位

期刊投稿运营与公开声誉证据分析用于判断目标期刊的投稿通道、审稿周期、录用/见刊周期、费用政策、退改投风险、公开声誉线索和可信性风险。它只做投稿决策辅助，不把匿名风评写成事实，不替代正式投稿系统、期刊官网或数据库核验。

## 输入

优先使用官方来源，其次使用数据库、第三方统计和作者经验平台。推荐字段：

- `source_type`：`official` / `database` / `third_party` / `forum` / `social` / `unknown`
- `source_title`
- `source_url`
- `evidence_date`
- `review_cycle_days`
- `first_decision_days`
- `acceptance_days`
- `publication_lag_days`
- `acceptance_rate`
- `fee_policy`
- `page_charge`
- `apc`
- `submission_system`
- `reputation_polarity`：`positive` / `negative` / `mixed` / `neutral`
- `reputation_note`
- `warning_flag`

## 来源分级

1. 期刊官网、投稿系统、投稿须知、出版机构官方页面。
2. 数据库页、DOI 页面、期刊平台统计页。
3. 第三方聚合平台或作者经验平台。
4. 论坛、公众号、社交媒体、非实名经验帖。

第三方经验和论坛内容只能作为线索，必须写明样本来源、时间和不可验证性。

## 指标

- 官方投稿系统和入口稳定性。
- 官方审稿周期或一审周期。
- 第三方审稿周期线索。
- 录用到见刊周期。
- 费用政策：版面费、APC、审稿费、开放获取费用。
- 退改投风险：超长等待、撤稿困难、假官网、收费不透明、投稿系统混乱。
- 公开声誉线索：正面、负面、混合、中性，并按来源分层。
- 可信性风险：官网缺失、投稿系统与官网不一致、同名刊混淆、异常收费、疑似中介入口。

## 判断规则

- 没有官方或数据库证据时，不得给强结论。
- 审稿周期来自论坛或第三方平台时，只能写“经验线索”，不得写成期刊承诺。
- 负面风评必须写成“待核验线索”，不得写成定性指控。
- 费用政策必须优先以官网、投稿须知或正式通知为准。
- 同名刊、假官网、投稿中介入口必须列入风险项，不能混入普通风评。

## 输出

- `04-fit-evaluation/journal-submission-operations-report.md`
- `04-fit-evaluation/journal-submission-operations-statistics.json`

报告必须包含：

- 来源构成和证据强度。
- 官方投稿入口和投稿系统状态。
- 审稿周期、录用周期、见刊周期的官方证据与第三方线索分列。
- 费用政策和收费风险。
- 公开声誉线索，按来源层级和正负面分类。
- 可信性风险和待核验项。
- 对投稿匹配评分的影响建议，但不得替代学术适配评分。
