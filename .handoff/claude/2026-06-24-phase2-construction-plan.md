# journal-style Phase 2 施工前规划报告

- 规划对象：journal-style（下游可消费期刊约束生产器）Phase 2 施工
- 类型：只读审查 + 施工前规划（未施工、未改源码、未触发真实检索链、未写 C03、未进真实文衡 B02/C03/H08）
- 规划人：Claude
- 日期：2026-06-24
- 复核基础：独立通读 SKILL/progress/五份协议/workflow-states/stage-gates/runner/run_stage_gates/两套测试/五份 schema/evidence-rules/三份 handoff/Phase 1 审查报告；并交叉读了下游「文章润色」skill 的 consumption-policy、journal-profile-dimensions、quality-thresholds 和 consume-journal-style-profile.py。

---

## 0. 结论先行

**可以进入 Phase 2，但必须先做一个「接线闭环批次（批次 0）」，否则后续四个生成器全部建在不稳的地基上。**

三句话判断：

1. Phase 1 的契约 / schema / gate / fixture 地基质量是好的，边界（不写正文、不跑 MinerU、不让 RAG 冒充全文、不模仿主编）守得住；过度阻断的 P0 已真修——metadata 任务现在能经 `paths` 过滤到达 `step08c` 终态。
2. 但 Phase 1 报告里标「必须先修」的**评分时序 P1 在执行层并未真正闭环**：只改了装饰性的 `next` 字段，runner 仍按数组物理序推进，而数组里 `step09_fit`（打分，263 行）物理排在 `step09b_scoring_calibration`（校准，281 行）之前，且 `step09_fit` 无 gate、runner 不校验 `requires_inputs`。结果是 runner 仍会把执行者引向「先打分、后校准」，违反「未校准不得定位」。
3. 更根本的是：**Phase 1 只立了「验收闸门」，没有任何「生产逻辑」**。逐篇画像、聚合锁、消费包、校准评分这四类产物目前都只有 gate 能「验收」，没有脚本能「产出」。Phase 2 的主体工作量是写这四个 fail-closed 生成器。

**最高优先的新发现（直接对应痛点「文章润色拿不到有用信息」）：跨 skill 消费契约字段错位。**

- journal-style 产出的消费包 `journal_style_profile_v1` 顶层是 `constraints`（length_band / section_hierarchy / abstract_keywords / reference_constraints…）、`gap_checklist`、`sample_count`、`evidence_index`。
- 但文章润色的消费脚本 `consume-journal-style-profile.py` **只读** `target_journal_exists`、`journal_style_artifact_exists/path`、`mode`、`reference_ecology{gap_exists, missing_reference_items, missing_citation_items}`——**完全不读 `constraints`**；并在 `word_count_policy` 里写死 `recommended_word_count_range:{13000,18000}`，且显式声明 `journal_profile_word_count_ignored:true`。
- 即：journal-style 即使把体例约束算得再准，下游目前也不消费；字数等仍走文章润色自己写死的值。**这是痛点的另一半根因，必须在 Phase 2 当作一等公民处理，而非 journal-style 内部优化即可解决。**

---

## 1. 现状核验：Phase 1 问题项 → 当前真实状态

区分四类：已真修 / 声称修但未闭环 / 预期延后 / 新发现。

| 来源 | 问题 | 声称 | 我的复核 | 真实状态 |
|---|---|---|---|---|
| P0 | metadata 任务被 mu 包阻断、无终态 | 已修 | `paths` 过滤 + `step08c` metadata terminal（next:null）；fixture 断言 completed 且 step07b 被 skip | ✅ 已真修 |
| P1 | 评分先于校准 | 已 Reorder | 只改了 `next` 链；数组物理序仍 step09_fit(263) 早于 step09b(281)；runner 纯数组序、不读 entry/next/requires_inputs；step09_fit 无 gate | ❌ 执行层未闭环 |
| P1 | 正文泄漏守卫无 fixture | 已补 | `fx_per_article_direct_text_no_go` 注入 `{"正文":…}` 断言 NO_GO | ✅ 已补 |
| P1 | 逐篇 gate expected_count 自证 | 延后 | gate 仍取画像批次自报 `ready_article_count`，未回查 mu 包 | ⚠️ 未修（Phase 2 必清） |
| P2 | 聚合「5 具名产物」未强制 | 延后 | `gate_aggregation_threshold` 只遍历现有 artifacts；fixture 仅 1 个 artifact 即 PASS | ⚠️ 未修 |
| P2 | 消费包缺顶层 confidence/conclusion_strength | 延后 | schema 顶层 required 无此二字段 | ⚠️ 未修 |
| P2 | handoff-to-wenzhang-runse 与 schema 不一致 | 延后 | 文档仍扁平结构，真实 schema 收进 `constraints` | ⚠️ 未修 |
| 新 | full 链无端到端集成测试 | — | 仅 `fx_full_mode_requires_mu_pack`（缺包停 step07b）；无 fixture 跑通 step07b→…→step10 | ❌ 缺失 |
| 新 | 跨 skill 字段错位 | — | consume 脚本不读 constraints、字数走写死值 | ❌ 断点 |

> 本轮只读不执行，未重跑 13/13、26/26；但通读两套 fixture 的断言逻辑，覆盖项与代码一致、可信，同时定位到它们**未覆盖**的三处缺口（上表「新」「未闭环」行）。

---

## 2. 最小施工批次（给 Codex 的可执行清单）

原则：每批可独立验证、独立回滚；生成器一律 fail-closed；先把接线与回归锚钉死，再写生产逻辑。

### 批次 0【前置·必做，先于所有生成器】接线闭环 + 回归锚

- **目标**：让状态机执行层与协议时序一致，为 full 链建立端到端回归锚，堵住「未校准先打分」，并清掉逐篇 expected_count 回查残留。
- **改的文件类型**：`config/workflow-states.json`（把 step09b 物理调到 step09_fit 之前）、`scripts/journal_style_runner.py`（消费 `entry` 或断言数组序==拓扑序）、`config/stage-gates.json` + `scripts/run_stage_gates.py`（给 step09_fit 加「已校准模型存在且通过」前置；逐篇 gate 回查 mu 包 ready 篇数）、`tests/run_state_machine_fixtures.py`（补集成 fixture）、`config/release-manifest.json`（重签）。
- **输入/输出契约**：step09_fit 必须依赖 step09b 产物 `journal-fit-scoring-model.json` 且其过 `scoring-replay-calibrated`，否则阻断；逐篇 gate 的 `expected_count = mu 包 ready 篇数`（权威），画像数须 ≥ mu ready，自报值只能更严不能更松。
- **验证**：① 齐全 full 链 task → 断言推进到 step10；② 只有打分、无校准模型 → 断言阻断在打分前；③ mu 包 30 篇、画像只交 12 篇自报 ready=12 → 断言 per-article gate NO_GO；④ 复跑 13/13 + 26/26 + smoke + `--check`。
- **fail-closed**：校准模型缺失/未校准 → 打分不可达；画像数 < mu ready → NO_GO；数组序与 next 拓扑序不一致 → 测试红。

### 批次 1：逐篇画像生成器

- **目标**：把「只有 per-article-profile-complete gate」补成「有产出 + 验收」，对每篇合格 mu 全文产出 `per_article_style_profile_v1`。
- **改的文件**：新增 `scripts/analyze_per_article_style.py`；gate 已存在不改。
- **输入**：经 `mu-fulltext-pack` gate 的 mu 包（≥10 篇 ready）。
- **输出**：`per-article-style-profiles.json`（13 维 + evidence_index + downstream_constraints，过 gate）。
- **维度分工（关键）**：确定性维度从 mu 包结构字段直接统计（length_band / paragraph_stats / section_hierarchy / keywords_profile / reference_profile / notes_profile）；语义维度（intro_pattern / argument_rhythm / material_types / method_types / title_structure / conclusion_pattern）由受控判断产出，每条挂 `evidence_path` 回指 mu_fulltext 具体位置。
- **fail-closed**：mu 包未过 gate / <10 篇 → 只产 `pending-materials.json` 待补清单，不产画像；任何维度无证据锚点 → 该维度标 gap，不编；downstream_constraints 出现可抄写正文键 → NO_GO。

### 批次 2：聚合锁生成器 + 5 具名产物强制

- **目标**：逐篇 → 分组 → 聚合，产出五个具名锁，并把「5 产物齐全」升为 gate 硬约束。
- **改的文件**：新增 `scripts/aggregate_journal_style.py`；改 `run_stage_gates.py`（`gate_aggregation_threshold` 增具名产物存在性检查）+ `config/stage-gates.json`（声明 `required_named_artifacts`）。
- **输入/输出**：吃 `per-article-style-profiles.json`，产 `journal-style-aggregation-bundle.json`，含 journal-style-constraints-lock / journal-format-convention-profile / journal-argument-preference-profile / journal-reference-ecology-lock / journal-polish-consumption-pack 五件；聚合用分布（区间/中位/四分位/众数）+ 降级标签，不用裸均值。
- **验证**：fixture bundle 缺任一具名产物 → NO_GO；<20 篇标 stable → NO_GO（已有）。
- **fail-closed**：样本门槛硬执行（<10 仅观察、10-19 初步、20+ 稳定、30+ 论证/参考高置信）；缺具名产物 → NO_GO。

### 批次 3：消费包生成器 + 顶层置信度 + 文档对齐

- **目标**：产出文章润色可零推断消费的 `journal-polish-consumption-pack.json`；补顶层 confidence/conclusion_strength；handoff 文档对齐 constraints 嵌套（单一事实源）。
- **改的文件**：消费包生成可并入批次 2 聚合器末步；改 `config/journal-polish-consumption-pack-schema.json`（顶层加 confidence/conclusion_strength，并预留 `reference_ecology` 块给下游）；改 `references/handoff-to-wenzhang-runse.md`（示例由扁平改为 constraints 嵌套）。
- **输出契约**：constraints 内字段名与 fixture `make_consumption_pack` 对齐（length_band.min/max、section_hierarchy.section_min/max、abstract_keywords.keyword_min/max、reference_constraints.reference_min/max…）；顶层带 confidence/conclusion_strength/sample_count。
- **fail-closed**：metadata_only=true 时 constraints 仅保留元数据可得项，全文体例项置空并标 gap；source_evidence_scope≠mu_fulltext_core_pack → 降级。

### 批次 4：回放校准评分器

- **目标**：`journal_fit_scoring_model_v1` 回放校准 + 用户稿相对定位输出。
- **改的文件**：新增 `scripts/calibrate_fit_scoring.py`、`scripts/score_user_manuscript.py`；改 `config/scoring-model-schema.json`（增 `user_manuscript_position` / `dimension_deductions` / `strengthening_suggestions` 输出契约）。
- **输入/输出**：吃聚合锁 + 已刊核心样本（回放），产已刊分布（min/q1/median/q3/max）+ 用户稿分位 + 维度扣分原因 + 补强建议。
- **轮次**：R1 已刊回放（最低可用）、R2 边界抽查、R3 用户稿差距定位。
- **fail-closed**：`calibration.status≠calibrated` 或回放 <10 → 不得给用户稿定位；产物不得出现「录用概率」「模仿主编」措辞。

### 批次 5【跨 skill·拍板后做】打通文章润色消费

- **目标**：让文章润色真正读 constraints，用 per-journal profile 替换写死阈值，兑现「真实帮助」。
- **改的文件（在文章润色 skill）**：`scripts/consume-journal-style-profile.py`（读 constraints 并下传）、`config/quality-thresholds.json` 与 `config/journal-profile-dimensions.json`（改为「profile 优先、写死值作护栏 fallback」）。
- **输入/输出**：吃批次 3 的 `journal_style_profile_v1`，让 `journal-style-constraints-lock.json` 等真正带上 per-journal 的字数/节/关键词/参考区间。
- **fail-closed**：metadata_only 包不得驱动全文体例阈值；无 profile 时回落护栏值并显式标 `source=fallback`。

---

## 3. 不得产生伪数据（贯穿全批次的红线）

- 无 mu 全文包 → 只能输出 `pending-materials.json` 待补清单；metadata-only / 普通 RAG 片段**不得**冒充全文体例分析。
- 语义维度判断必须挂 `evidence_path` 回指 mu_fulltext；无锚点 → 标 gap，不编。
- 样本门槛硬执行：<10 待补、10-19 初步偏好、20+ 稳定体例、30+ 论证风格/参考生态高置信。
- 每个生成器的输入先过对应 gate，gate 现场重跑（沿用 P2 sha 链信任模型）；生成器不得绕过 gate 直接产「看起来齐全」的产物。
- 评分器只做「基于已刊样本回放校准的适配近似」，不预测录用、不模拟个人主编。

## 4. 施工顺序（线性）

批次 0（接线闭环 + 回归锚）→ 批次 1（逐篇画像）→ 批次 2（聚合 + 5 产物强制）→ 批次 3（消费包 + 置信度 + 文档对齐）→ 批次 4（校准评分）→【拍板】批次 5（打通文章润色）。

- **必须先做**：批次 0。它清掉 Phase 1 残留的时序/回查问题并建立 full 链回归锚，后续生成器才有可信验收。
- **强依赖链**：批次 1 → 2 → 3 → 4 严格顺序（后者吃前者产物）。
- **可延后/需授权**：批次 5（跨第二个 skill，且涉字数策略冲突）。批次 3 的「文档对齐 + 顶层置信度」若想更早，可在批次 0 后作为独立小步插入，不阻塞主链。

## 5. 需要用户拍板的问题

1. **逐篇语义维度由谁判、如何防编造？** intro_pattern / argument_rhythm / material_types / method_types 无法纯脚本算。建议：确定性维度脚本统计 + 语义维度受控判断且强制 evidence_path 锚点，无锚点即标 gap。是否认可？用哪一档模型？
2. **本阶段是否纳入文章润色端改造（批次 5）？** 不做批次 5，journal-style 即使产出再好的 constraints，下游现在也不读，痛点无法真正解除。
3. **字数策略冲突以谁为准？** 文章润色现在主动忽略 journal-style 字数、用写死的 13000-18000。打通后：完全用 profile 覆盖 / profile 优先但保留护栏 / 仅 full 模式且 ≥20 篇才允许覆盖？
4. **评分器输出落点与 schema 扩展？** 用户稿相对位置 + 维度扣分 + 补强建议，放进 `journal-fit-scoring-model.json` 还是 `submission-fit-score.md`？是否同意扩 scoring schema 增这三类字段？
5. **mu 包结构字段是否升为 full 模式硬 required？** 当前 section_tree / paragraph_sequence / notes / reference_list 是「建议字段 + 覆盖率 <0.8 仅 warning」。全文体例分析强依赖它们。是否升为 full 模式硬 required（缺则该篇不计入 ready）？这会提高对上游检索入库交付质量的要求。

---

## 6. 决策记录（2026-06-24，用户已拍板）

以下 5 项为用户在本规划轮已确认的决策，Codex 施工以此为准；与上文批次描述冲突处，以本节为准。

1. **批次 5 纳入本阶段**：Phase 2 一路做到打通文章润色消费——改 `consume-journal-style-profile.py` 真正读 `constraints`，并用 per-journal profile 替换文章润色对应写死阈值。
2. **字数维持文章润色写死值**：`constraints.length_band` 仅作参考展示，生成时带 `advisory_only:true` / `source=reference_only`，**不参与门禁、不覆盖 13000–18000**；其余维度（节数/小节、关键词数量、参考文献区间、注释体例、论证节奏、题名风格）由目标期刊 profile 驱动并替换写死阈值。批次 5 的 consume 脚本读到 `advisory_only` 即只展示不门禁。此项与文章润色现有 `journal_profile_word_count_ignored:true` / `word_count_target_is_gate:false` 设计一致。
3. **逐篇语义维度判法**：确定性维度（字数/段落/节级/关键词数/参考数/注释统计）走脚本；语义维度（引言方式/论证节奏/材料类型/方法偏好/题名结构/结论方式）由 Codex 受控判断，**每条强制挂 `evidence_path` 回指 mu 全文位置，无锚点即标 gap、不编**；语义判断用 Opus 同档模型，按篇并行。
4. **评分器输出落点**：已刊评分分布 + 维度权重留在 `journal-fit-scoring-model.json`（模型本体）；用户稿分位 + 维度扣分原因 + 补强建议写进 `submission-fit-score.md`（稿件应用结果）。`scoring-model-schema.json` 只补 `dimensions[].rationale`，不塞用户稿定位字段。
5. **mu 结构字段升 required（分级）**：`section_tree` / `paragraph_sequence` / `reference_list` 升为 **full 模式硬 required**，缺任一则该篇不计入 ready 篇数；`notes` 保持建议字段。此项需同步改 `config/stage-gates.json` 的 `mu-fulltext-pack` gate（把这三项从 `structure_fields` 软覆盖率升为硬校验）、`references/mu-fulltext-pack-protocol.md` 与 `handoff-to-jiansuo-ruku.md`。

> 对批次的影响：决策 2 → 批次 3 产 `length_band` 时打 `advisory_only`，批次 5 consume 读标记只展示不门禁；决策 5 → 并入批次 0 一起做（它改的正是 `mu-fulltext-pack` gate 与 release-manifest，落在批次 0 的接线/重签范围内，顺路完成）。

（报告完·决策已固化）
