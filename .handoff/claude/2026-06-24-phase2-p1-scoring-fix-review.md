# journal-style Phase 2 · 批次 4 评分校准 P1 返修定向复审

- 复审对象：Codex 对上一轮 CHANGES_REQUESTED 中「批次 4（评分校准）」两个 P1 的最小返修
- 复审类型：只读审查 + 本地离线测试复跑 + 真实链探针（合成数据）。未改任何源码 / 配置 / schema / 测试 / progress；未触发 CNKI / WoS / Zotero / PDF / MinerU·mu / RAG 导库 / 服务器 / 文衡 B02·C03·H08 / 模型池
- 复审人：Claude
- 日期：2026-06-24
- 复核基础：逐行读 `calibrate_fit_scoring.py` / `score_user_manuscript.py` / `run_stage_gates.py`（scoring 段）/ `scoring-model-schema.json` / `scoring-model-protocol.md` / 两套 fixtures / `release-manifest.json` / `progress.md`；复跑两套 fixtures + smoke + py_compile + manifest --check + JSON 校验；另用测试模块的合成数据跑真实 `analyze→aggregate→calibrate→score` 链，直接 dump 模型核对。

---

## 1. STATUS

**APPROVED_WITH_NOTES**

## 2. 业务结论

- 两个 P1 均**已真实闭合**，不是表面改标签：批次 4 现在用逐篇画像回放算分布、用目标期刊聚合 band 给用户稿评分，伪数据红线已拆除。
- 主链（逐篇→聚合→消费包→文章润色消费）**未被返修牵动**，仍是上一轮已通过的状态。
- **可以进入发布前收束 / 打包 / 同步**。残留仅为上一轮已记录的 P2 加固项（与本次返修无关、非阻断），列为后续小步即可。

## 3. P1 闭合判断

### P1-1 校准分布真实来自逐篇画像回放 —— 已闭合

逐条对照复审点：

- **读 per-article-style-profiles + 先过 gate**：✅ `calibrate_fit_scoring.py:23` 新增 `DEFAULT_PROFILES`，`:208-210` 缺文件即退出，`:220-228` 在 `aggregation-threshold` 之后再跑 `per-article-profile-complete` gate，非 PASS/DEGRADED 即 `return 1`。
- **source 改为真实值**：✅ `:249` `calibration.source="per_article_profile_replay"`（旧的误导性 `published_sample_replay` 已删）；并新增 `:250-251` `source_profiles` / `source_aggregation_bundle` 两个 provenance 路径，可回溯。
- **replay_scores 逐篇生成**：✅ `:237` 对每个 profile 调 `replay_score()`；`:159-181` 每条返回 `article_id` / `score` / `feature_values` / `deductions`，扣分逐项带 band 与来源。
- **分布由 replay_scores 算出**：✅ `:238` `distribution=score_distribution([item["score"]...])`；`:69-82` 无回放分数直接 `raise`，杜绝空表占位；`:81` `source="replay_scores"`。旧的两张写死常量表（原 `:93-96`）已不存在。
- **gate 反算并拒绝不一致**：✅ `run_stage_gates.py:803-827` —— gate 自己从 `replay_scores[]` 取分、重算 `scoring_distribution()`、逐分位 `same_number` 比对，不一致即 NO_GO；`:817-818` 强制 `distribution.source=replay_scores`；`:779-780` 强制 `calibration.source=per_article_profile_replay`；`:815-816` 分布 `sample_count` 必须等于 `replay_scores` 条数。校验器 `scoring_distribution`(`:128-139`) 与生成器 `score_distribution` 用同一套分位公式（`len//4` / `median` / `(len*3)//4`，均 round 2），探针实测重算一致。
- **常量伪分布 must-fail fixture**：✅ `tests/run_downstream_consumable_fixtures.py:473-482` `fx_scoring_constant_distribution_no_go` —— 把分布改回旧常量 `{70,78,84,90,96}`，断言 NO_GO 且 problems 含 `does not match replay_scores`。实跑命中（detail：`published_score_distribution min does not match replay_scores`）。

**真实链探针（合成 12 篇）直接证据**：`calibration.source=per_article_profile_replay`、带 `source_profiles`/`source_aggregation_bundle`；`replay_scores` 12 条逐篇含四字段；`published_score_distribution.source=replay_scores`；独立重算 min/q1/median/q3/max 与模型**完全一致**（matches=True）。

### P1-2 用户稿评分消费目标期刊 band —— 已闭合

- **calibrate 把 bundle constraints 写进 model**：✅ `calibrate_fit_scoring.py:92-100` `extract_constraints` 从 `journal-polish-consumption-pack`（缺则 `constraints-lock`）的 `payload.constraints` 取真实 band；`:103-111` compact 出 `section_hierarchy/abstract_keywords/reference_constraints/notes_convention`，标 `source=journal_style_aggregation_bundle`、`fallback_used=false`；`:257` 写进 `model.scoring_constraints`。
- **score 从 model 读 band**：✅ `score_user_manuscript.py:65-72` `constraints_from_model` 读 `model.scoring_constraints`；`:56-62` `band_value` 取 `section_min/max` 等真实 band；`:90-118` `score_features` 用该 band 判偏离，不再用通用写死区间。
- **通用区间仅作 fallback 且标来源**：✅ `band_value` 缺字段时返回 `(3,6)`/`(3,6)`/`(15,60)` 并标 `source="fallback"`（`:62`）；扣分项带 `constraint_source`，报告逐行输出「约束来源：{source}」（`:181-183`）；表头另输出「评分约束来源」（`:148`）。协议 `scoring-model-protocol.md:42` 明文要求。
- **目标期刊 band 应用 fixture**：✅ `:529-559` `fx_score_user_uses_journal_band` —— band 设 section 4-4、reference 22-22，喂 `section_count=3`/`reference_count=20`，断言报告含「目标期刊章节区间：4-4」「目标期刊参考文献区间：22-22」「章节数量偏离目标期刊区间 4-4」「参考文献数量偏离目标期刊区间 22-22」「约束来源：journal_style_aggregation_bundle」。实跑通过。
- **gate 强制 band 在场**：✅ `run_stage_gates.py:785-797` 要求 `scoring_constraints.source=journal_style_aggregation_bundle` 且 section/keyword/reference 三组 min/max 非空，缺即 NO_GO；score 又先过 `submission-fit-ready`（包 `scoring-replay-calibrated`，`:847-860`）才打分。故真实路径下 model 必带真实 band，fallback 实为护栏冗余。

**探针实测**：`scoring_constraints.source=journal_style_aggregation_bundle`、`fallback_used=false`、三组 band 均为数值。

**schema 同步收紧**（`config/scoring-model-schema.json`）：required 增 `scoring_constraints`/`replay_scores`/`published_score_distribution`（`:5-14`）；`distribution.source` const=`replay_scores`（`:56`）；`scoring_constraints.source` const=`journal_style_aggregation_bundle` 且三组 band required（`:59-68`）；`replay_scores` items required `article_id`/`score`（`:70-81`）。协议文档 `:27`/`:42` 与实现一致。

## 4. 仍需返修项

- **P0**：无。
- **P1**：无。两个 P1 均闭合。
- **P2（carry-over，非阻断，发布后小步即可，勿因此扩范围）**：
  - P2-1 `_direct_text_keys`（`run_stage_gates.py:565-573`）仍只含 `paragraph/sentence/draft_text/rewritten_text/copyable_text/正文`，未并入 field-policy 的 `full_text/fulltext/mu_fulltext`。本次返修未触此处，状态同上一轮。
  - P2-2 文章润色消费桥 `profile_driven_constraints` 未按 `metadata_only` 收口（上一轮记录，理论缺口，现网不触发）。
  - P2-3 `source_pack` 未升为 batch schema/gate 硬 required（上一轮记录）。
  - P2-4 handoff 文档若干叶子字段超前于聚合器实际产出（上一轮记录）。
  - 新增微项（cosmetic，可并入 P2）：`score_features` 走 fallback 分支时，扣分 reason 文案仍写「偏离目标期刊区间」，与同行 `constraint_source=fallback` 略有字面矛盾；因 gate 已强制 band 在场，该分支实际不可达，仅为措辞洁癖。

## 5. 边界核验

逐项结论（✅=未发现问题）：

- **伪数据**：✅ 已拆。旧的两张写死分布表 + 通用 band 冒充，已被「真实回放分布 + bundle band」取代；gate 反算分布、强制双 source 常量，常量伪分布 must-fail fixture 实测拦下。
- **metadata / RAG 冒充 mu**：✅ 不受本次影响。calibrate/score 不碰 mu 包；mu 权威计数与 metadata 守卫在既有 gate（`mu-fulltext-pack` / `provenance-required` / `completion-label`）未改动。
- **模拟主编 / 录用概率**：✅ gate 强制 `not_editor_simulation`/`no_acceptance_prediction`（`:770-773`），model 两字段为 true，report 正文「不是主编模拟，不预测录用概率」，`risk_control` 维度 rationale 明示「不预测录用概率」。措辞合规。
- **真实外链触发**：✅ calibrate / score / run_stage_gates 三脚本零网络库（`requests/urllib/socket/httpx/aiohttp` 全无命中）；全部 `subprocess` 仅本地调 `run_stage_gates.py`。复审仅读 + 跑本地合成测试 + 临时目录探针，未触达任何外部链路 / 服务 / 模型池。
- **是否被改成正文工具**：✅ 否。产物仍是分布 / 约束 / 扣分依据；report 文案「缺失维度必须回 journal-style 消费包或检索入库补材料，不在此处补写正文」。

## 6. 测试复核（实际运行命令与结果，macOS / python3）

- `python3 tests/run_downstream_consumable_fixtures.py` → ok=True，**23/23**（含 `fx_scoring_constant_distribution_no_go`、`fx_score_user_uses_journal_band`、`fx_calibrate_and_score_user_manuscript` 三条 P1 回归全绿）。
- `python3 tests/run_state_machine_fixtures.py` → ok=True，**28/28**（full-mode 全链终态、uncalibrated 阻断等均在新严格模型契约下仍通过，无回归）。
- `python3 scripts/run_smoke_tests.py` → **smoke tests passed**。
- `python3 -m py_compile scripts/*.py tests/*.py` → **OK**。
- `python3 scripts/build_release_manifest.py --check` → **release-manifest.json is current**（calibrate/score 两脚本 sha 在 `manifest:28-29`，校准返修后已刷新）。
- `python3 -m json.tool config/scoring-model-schema.json` / `config/release-manifest.json` → **JSON OK**。
- 真实链探针（`/tmp` 临时，合成 12 篇，import 测试模块 helper 不触发其 main）：analyze / aggregate / calibrate rc 全 0，`scoring_gate_verdict=PASS`，模型字段如第 3 节实证。
- 网络库扫描：三脚本零命中。

**未运行 / 主动未触发**：CNKI / WoS / Zotero / PDF / MinerU·mu / RAG / 服务器 / 文衡 B02·C03·H08 / 模型池；真实期刊端到端任务未跑（本轮为复审）。

**关于文章润色侧 `run-local-gate.py --pre-review` 失败**：按流程语义判断为「当前已存在 Claude review，pre-review 期望其缺席 / 未发布」导致，属工作流状态结果，非本次 journal-style 评分返修引入的功能回归。本轮未改文章润色任何文件，不计为阻断。

## 7. 发布建议

**允许进入发布前收束 / 打包 / 同步。**

两个 P1 已用「代码消费真实数据 + gate 反算硬拦 + schema/协议收紧 + 双向 fixture」四重闭合，并经独立真实链探针证实。残留 P2 为上一轮既有加固项，非阻断，建议作为发布后的小步逐项消化（优先 P2-1：把 `_direct_text_keys` 与 field-policy 禁词合流为单一事实源）。

> 复审范围声明：本轮只审批次 4 P1 返修是否闭合，未重规划 Phase 3、未继续施工、未运行真实期刊任务。所有判断基于只读审查 + 本地离线测试 + 合成数据探针。
