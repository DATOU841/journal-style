# journal-style Phase 1 下游可消费化施工审查报告

- 审查对象：journal-style Phase 1（下游可消费期刊约束生产器地基）
- 审查类型：只读审查 + 规划判断（不施工、不改源码、不触发真实检索链、不写 C03、不进真实文衡 B02）
- 审查人：Claude
- 日期：2026-06-24
- 审查范围：契约 / schema / gate / 状态机 / fixture / 协议文档

---

## 1. 结论

**APPROVED_WITH_NOTES（有保留通过）**

一句话理由：契约、schema、gate、fixture 这套“地基”目标已经达到，边界守得住，fail-closed 设计自洽，全部离线验证我已独立复跑通过；但**状态机把 MinerU/mu 完整全文包做成了所有路径的硬前置，导致 metadata-only 任务在当前 runner 下没有可达终态**——这是一个必须在 Phase 2 之前解决的结构性接线问题，并非契约本身的缺陷。

### 1.1 独立复核结果（我本机离线复跑，未触发任何外链）

| 验证项 | Codex 报告 | 我的复跑 | 一致 |
|---|---|---|---|
| `tests/run_downstream_consumable_fixtures.py` | 11/11 | `ok:true, 11/11` | ✅ |
| `tests/run_state_machine_fixtures.py` | 24/24 | `ok:true, 24/24` | ✅ |
| `scripts/build_release_manifest.py --check` | passed | `release-manifest.json is current` (rc=0) | ✅ |
| `scripts/run_smoke_tests.py` | passed | `smoke tests passed` (rc=0) | ✅ |

`python3 -m json.tool` / `py_compile` 我以通读方式静态确认（所读 JSON 均合法、脚本无语法异常），未单独再跑。结论：Codex 报告的验证状态属实，未发现伪造或夸大。

> 说明：我把“过度阻断”定为本轮最关键的判断点（用户点名的重点），它落在 `config/workflow-states.json` + `scripts/journal_style_runner.py` 的接线层，而不是新增的五个 schema 或 gate 逻辑本身。新增的契约/schema/gate 质量是好的，所以总评是“有保留通过”而非“打回”。但请注意：**一旦 runner 被用于 metadata-only 真实任务，该问题立即升级为阻断级。**
---

## 2. 关键发现（按严重程度）

### 【P0 · 结构性】工作流把 MinerU/mu 全文包变成全路径硬前置，metadata-only 任务无可达终态

- **文件**：`config/workflow-states.json`、`scripts/journal_style_runner.py`（`compute_position` / `step_satisfied`）
- **问题说明**：
  - `journal_style_runner.compute_position()` 是**纯数组顺序**扫描 `steps`，在第一个未满足的 step 处 `break`，**完全不读 `entry` 字段**。
  - 在 `steps` 数组里，`step07b_mu_fulltext_pack`（gate `mu-fulltext-pack`，要求 `mu-fulltext-core-pack.json` 存在且就绪篇数 ≥10，否则 NO_GO）排在 `step08a_metadata_layer` **之前**。
  - 因此任何**没有 MinerU/mu 全文包**的任务，会在 `step07b` 处 fail-closed 停住，永远到不了 `step08a` 元数据层分析。
  - 唯一的终态节点是 `step10_handoff`（`next:null`），而它被 `step07b → step08b1 → step08b → step09b` 这条全文链整体挡在后面。状态机里**没有任何 metadata-only 的退出/终态**。
- **影响**：
  - 这与 skill 自身能力声明直接冲突。`SKILL.md` 首版能力范围列出的“题名风格、选题趋势、作者机构网络、作者公共身份”等都只需题录/摘要层证据；`references/evidence-rules.md` 证据矩阵也明确这些维度“只需题录”或“题录+摘要”。
  - gate 词表里 `METADATA_ONLY_NOT_FULLTEXT_READY` 是一个合法 completion_label，但状态机**没有任何 step 能把任务带到这个标签对应的完成态**——“有合法标签，无合法路径”。
  - 结果：一个纯粹的“期刊身份 + 题录趋势 + 作者网络”分析，在 runner 下会被一个它根本不需要的 ≥10 篇 MinerU 全文包阻断。这是过度阻断，且是本轮新引入的。
- **建议修复方式**（详见第 4 节，此处给方向）：
  1. 引入 `path`/`mode` 概念：把 `step07b_mu_fulltext_pack`、`step08b1_per_article_profile`、`step08b_fulltext_layer`、`step09b_scoring_calibration` 标记为 **fulltext-style path 专属**步骤；
  2. 为 metadata-only / 轻量路径补一个**独立终态**（例如 `step10_handoff` 接受 `completion_label=METADATA_ONLY_NOT_FULLTEXT_READY`，且在该标签下不要求全文链 step 完成）；
  3. 让 runner 真正按 `entry`（DAG）而非数组顺序判定可达性，或显式按 `mode` 过滤要执行的 step 子集。
- **附带问题（同根因）**：`entry` 字段当前是**装饰性**的——runner 不消费它。这与本仓“dimension_thresholds 不得装饰”的一贯纪律不一致；`entry` 给人一种 DAG 假象，但实际依赖顺序是数组下标。建议要么让 runner 校验 `entry`，要么删除 `entry` 以免误导。
### 【P1 · 中】评分产出排在校准之前：step09_fit 先出分，step09b 才校准模型

- **文件**：`config/workflow-states.json`（`step09_fit` → `step09b_scoring_calibration`）
- **问题说明**：`step09_fit`（产出 `submission-fit-score.md`，即用户稿件适配打分）`gate:null`、无门禁，且**排在** `step09b_scoring_calibration`（产出校准过的 `journal_fit_scoring_model_v1`）**之前**。也就是“先给用户稿打分，再校准评分模型”。
- **影响**：`references/scoring-model-protocol.md` 明文“未完成回放校准时，不得给用户稿件做分位定位”。当前接线下，`step09b` 的 gate 能挡住**最终 handoff**（step10），但挡不住 `step09` 已经先产出了一份未受校准约束的适配分。这违反了协议的时序意图，存在“分数已生成、校准是事后补”的口子。
- **建议修复方式**：把校准模型作为打分的**前置输入**——让 `step09_fit` 依赖 `step09b` 的产物（或合并：先 `step09b` 校准、再 `step09_fit` 在已校准模型上打分），并给 `step09_fit` 加一个“消费已校准模型”的校验，而不是让它无门禁地早于校准。

### 【P1 · 中】逐篇 gate 的 `expected_count` 自证，未与 mu 包就绪篇数交叉核对

- **文件**：`scripts/run_stage_gates.py`（`gate_per_article_profile_complete`）
- **问题说明**：该 gate 的 `expected_count` 取自**画像批次文件自身**的 `ready_article_count`（`data.get("ready_article_count") ... or len(profiles)`），而不是回查 `mu-fulltext-core-pack.json` 实际就绪篇数。若批次把 `ready_article_count` 写成 `len(profiles)`，则“逐篇齐全”检查恒真。
- **影响**：可被绕过——mu 包有 30 篇，但画像只交 12 篇且自报 `ready_article_count=12`，gate 仍 PASS，聚合据此“看起来逐篇齐全”。逐篇→聚合的完整性保证被削弱。
- **建议修复方式**：让该 gate（或 runner 接线）把 mu 包的 ready 篇数作为 `expected_count` 的权威来源，逐篇画像数必须 ≥ mu 包就绪篇数；批次自报值只能更严不能更松。

### 【P1 · 中】正文泄漏守卫（`forbid_direct_reusable_text`）无 fixture 覆盖

- **文件**：`scripts/run_stage_gates.py`（`_direct_text_keys` / `gate_per_article_profile_complete`）、`tests/run_downstream_consumable_fixtures.py`
- **问题说明**：`_direct_text_keys` 会拦截 `downstream_constraints` 里出现 `paragraph/sentence/draft_text/rewritten_text/copyable_text/正文` 等可直接抄写键——这是**守住“不写正文”边界的核心闸**。但 11 个 fixture **没有一个**故意塞一个 `正文` 键来断言它被 NO_GO。
- **影响**：这是边界最敏感的一道防线，却处于“写了但没被测”的状态；未来一旦该逻辑被改坏，回归测试不会报警。
- **建议修复方式**：补一个 must-fail fixture：在 `downstream_constraints` 注入 `{"正文": "..."}` 或 `{"paragraph": "..."}`，断言 `per-article-profile-complete` 判 NO_GO。
### 【P2 · 低-中】聚合“必要产物清单”未被 gate 强制

- **文件**：`references/aggregation-and-consumption-protocol.md`、`scripts/run_stage_gates.py`（`gate_aggregation_threshold`）
- **问题说明**：协议要求聚合 bundle 必含 5 个具名产物（`journal-style-constraints-lock`、`journal-format-convention-profile`、`journal-argument-preference-profile`、`journal-reference-ecology-lock`、`journal-polish-consumption-pack`）；但 `gate_aggregation_threshold` 只遍历“现有 artifacts”逐项校验元数据/阈值，**不检查这 5 个具名产物是否齐全**。fixture 里 bundle 仅含 1 个 artifact 即 PASS。
- **影响**：bundle 可“缺斤少两”仍过门——下游消费方可能拿到不完整的约束集。属契约与执行的轻度脱节。
- **建议修复方式**：在聚合 gate 增加“必备具名产物存在性”检查（Phase 2 处理即可，Phase 1 不阻断）。

### 【P2 · 低-中】给文章润色的 handoff 文档字段布局与 `journal_style_profile_v1` schema 不一致

- **文件**：`references/handoff-to-wenzhang-runse.md` vs `config/journal-polish-consumption-pack-schema.json`
- **问题说明**：handoff 文档声称“正式交接应优先使用 `journal-polish-consumption-pack.json`，schema 为 `journal_style_profile_v1`”，但其 JSON 示例是**扁平结构**（`title_style`、`abstract_keywords`、`length_band`… 平铺在顶层），而真实 schema 把这些**收进 `constraints` 对象**，且字段名也不完全对应（如 schema 的 `reference_constraints` vs 文档的 `reference_constraints.reference_count_band`）。
- **影响**：文章润色对接方若照文档示例实现，会与真实消费包 schema 对不上，增加对接摩擦。
- **建议修复方式**：把 handoff 文档示例改为直接引用/对齐 `journal_style_profile_v1` 的 `constraints` 嵌套结构，单一事实源化。

### 【P2 · 低】消费包缺顶层 `confidence`/`conclusion_strength`

- **文件**：`config/journal-polish-consumption-pack-schema.json`
- **问题说明**：聚合 bundle 的每个 artifact 都带 `confidence`/`conclusion_strength`，但下游真正消费的 `journal_style_profile_v1` 顶层只有 `source_evidence_scope` + `metadata_only` + `sample_count`，没有显式总体置信度。
- **影响**：文章润色要决定“约束应用强度”时，只能从 `sample_count`+`scope` 反推，不如直接读一个 `confidence`/`conclusion_strength` 字段稳。
- **建议修复方式**：Phase 2 给消费包补顶层 `confidence` 与 `conclusion_strength`（可由聚合层下传），让消费方零推断地分档应用。

### 【P2 · 低】五个 schema 文件被完整性保护，但运行时无 JSON-Schema 校验消费它们

- **文件**：`config/*-schema.json`、`scripts/run_stage_gates.py`
- **问题说明**：新增 schema 已纳入 `release-manifest.json` 字节保护，但 gate 实际是用 Python **重新实现**了字段存在性/常量校验（按 `schema` 字符串相等 + 手写字段检查），并未用 jsonschema 对文件做真正校验。schema 文件目前更像“契约文档”，与 Python 校验存在长期漂移风险。
- **影响**：schema 与 gate 两份事实源可能各自演化、悄悄分叉。
- **建议修复方式**：Phase 2 评估引入轻量 jsonschema 校验，或在 CI 加一致性测试（schema 改了、gate 没跟上时报警）。

### 【P3 · 提示】两处“应为硬约束却只 warning”

- **文件**：`scripts/run_stage_gates.py`（`gate_mu_fulltext_pack`）
- **问题说明**：`ordinary_rag_is_not_substitute` 非 `true` 只产生 warning；`mu_processor` 取值非 `mineru/mu` 时虽 NO_GO，但空值放行。考虑到“普通 RAG 不得替代全文包”是红线，前者建议升为硬性 NO_GO（或在 schema 设为 required+const）。
- **影响**：弱——schema 已要求 MinerU 全文，绕过空间有限；属收紧建议，非缺陷。

### 【P3 · 提示】`build_material_intake_manifest.py` 未纳入完整性保护

- **文件**：`scripts/journal_style_runtime.py`（`MANIFEST_TRACKED_SCRIPTS`）
- **问题说明**：该脚本登记了 Phase 1 新产物（Step0 清单），但自身不在受保护脚本列表内。它不直接判 gate，风险较低，但它决定“哪些资产被登记/可被后续消费”。可评估是否纳入保护。
---

## 3. 对 Phase 1 的总体评价

**目标“契约 / schema / gate / fixture 地基”——基本达成，质量良好。** 下面是逐条核对结论。

### 3.1 边界守住情况（Q1）——✅ 守住

- **仍只做期刊分析层**：`SKILL.md`、各 handoff 协议反复重申“不写正文、不润色、不模仿语气”；`per-article-profile-complete` gate 用 `_direct_text_keys` 主动拦截可抄写正文键（机制存在，惟缺测试，见 P1）。
- **未把 MinerU/mu 职责塞进 journal-style**：`mu-fulltext-pack-protocol.md` 明确“只验收和分析、不运行 MinerU、不下载 PDF、不导 RAG”；`gate_mu_fulltext_pack` 只校验来包、对既有文本算 sha，不做任何获取。
- **未让 RAG 片段替代全文包**：`ordinary_rag_is_not_substitute` 字段 + 协议 + 证据矩阵新增行三处一致；`provenance-required` 对 `source_evidence_scope != mu_fulltext_core_pack` 给降级警告。
- **评分器边界**：`journal_fit_scoring_model_v1` 强制 `not_editor_simulation=true`、`no_acceptance_prediction=true`，协议明确“不是主编模拟器、不预测录用”。未见“模仿主编”字样。

### 3.2 schema 是否足以支撑 Phase 2（Q2）——✅ 足够（含少量补强项）

- `mu_fulltext_core_pack`：完整全文、章节树、段落序列、注释、参考文献表、provenance（source_ledger/extraction_method/mu_version）、`fulltext_sha256` 齐备。注：`section_tree` 等结构字段在 schema 里是“建议”、由 gate 以 ≥0.8 覆盖率 warning 把关，Phase 1 可接受。
- `per_article_style_profile_v1`：能承载逐篇 13 维 + `evidence_index` + `downstream_constraints`，gate 强制 13 维齐全。
- aggregation bundle：`sample_count/coverage/confidence/conclusion_strength/degrade_label/evidence_index` 足以表达样本数、覆盖率、置信度、降级与证据索引。
- `journal_style_profile_v1`（消费包）：8 类约束 + `source_evidence_scope` + `metadata_only` + `gap_checklist` + `evidence_index`，可作为文章润色真实消费包（建议补顶层 confidence，见 P2）。
- scoring model：校准状态/轮次/回放样本/已刊分布/维度权重齐备，规避了主编模拟与录用预测。

### 3.3 gate 是否足够 fail-closed（Q3）——✅ 基本到位

| 要求 | 实现 | fixture |
|---|---|---|
| MinerU 包 <10 篇阻断 | `gate_mu_fulltext_pack` ready<10 → NO_GO | `mu_pack_below_10_no_go` ✅ |
| 10-19 篇仅 degraded/初步偏好 | ready<20 → warning → DEGRADED | `mu_pack_10_preliminary_degraded` ✅ |
| 未完成逐篇阻断聚合 | step08b1 gate 先于 step08b（线性序+step_satisfied） | `per_article_missing_profile_no_go` ✅ |
| 聚合缺 evidence_index 阻断 handoff | 聚合 gate + `provenance-required` 双重要求 | `provenance_missing_no_go` ✅ |
| 评分未回放校准阻断定位 | `scoring-replay-calibrated` NO_GO | `scoring_uncalibrated_no_go` ✅（但时序见 P1） |
| release manifest 纳入新 schema/gate | 5 schema + 关键脚本均入 `config_sha256`/`script_sha256`，`--check` current | 完整性 must-fail fixtures ✅ |

完整性闸门（drift→fail-closed、缺 manifest→fail-closed、侧门 `run_stage_gates` 同样 rc=3）有 must-fail 守卫覆盖，质量高。

### 3.4 与文章润色接口（Q5）——✅ 合理

- 本轮不改文章润色源码是**对的**：Phase 1 只立契约，消费包尚未由真实运行产出，此时改下游属过早。
- `journal-polish-consumption-pack` 提供的 8 类约束正是润色工具原本写死的那批阈值，足以作为“替换写死阈值”的载体。
- 最小改造点见第 6 节。
---

## 4. 对过度阻断风险的判断（Q4，用户点名的重点）

### 4.1 明确判断：**需要模式分层。是。**

当前工作流确实把 MinerU/mu 完整全文包变成了**所有 journal-style 任务的硬前置**，这会不必要地阻断“纯 metadata-only 期刊身份/题录趋势/作者网络”这一类本应轻量完成的分析。理由已在 P0 给出：`compute_position` 按数组序在 `step07b` 处 fail-closed，而 metadata 层 `step08a` 排在其后、且全程没有 metadata-only 终态。

> 一句话：**MinerU/mu 全文包应是“fulltext-style path 的 hard gate”，而不是“所有 path 的 hard gate”。**

### 4.2 建议的最小修改（不必大改，Phase 2 起步即可落地）

推荐**三模式分层 + 路径化 gate**，按改动量从小到大：

**方案 A（最小、推荐先做）——给 step 打 `path` 标签，runner 按模式过滤**
1. 在 `config/workflow-states.json` 每个 step 增加 `paths` 标签，例如：
   - `metadata`：step00–step08a + 一个 metadata 终态
   - `fulltext`：在 `metadata` 基础上追加 step07b/step08b1/step08b/step09b
2. 任务在 `00-intake` 用一个 `requested_mode`（`light|standard|full`）声明目标：
   - `light`：身份 + 题录趋势 + 作者网络（metadata path，**不要求** mu 包）
   - `standard`：light + 投稿匹配（仍可不含全文链，或含 degraded 全文）
   - `full`：standard + MinerU/mu 全文体例锁 + 校准评分（fulltext path）
3. `compute_position` 只在“当前模式所含 step 子集”内推进，并按 `entry` 判定可达性（不再纯数组序）。
4. 为 metadata path 增加**独立终态**：允许 `step10_handoff` 在 `completion_label=METADATA_ONLY_NOT_FULLTEXT_READY` 时，不要求 step07b/step08b1/step08b/step09b，但仍要求 metadata 层证据门禁与 `provenance-required`（针对 metadata 证据）。

**方案 B（更彻底）——拆成两条显式链**
- `workflow-states.json` 拆出 `metadata_path` 与 `fulltext_path` 两组 steps，各自有终态；`full` 模式 = 跑完 metadata_path 后再进 fulltext_path。语义更清晰，但改动更大。

### 4.3 配套必须同时做的两件事（否则分层是假的）

1. **让 runner 真正消费 `entry` 或 `mode`**：当前 `entry` 不被读取，分层标签若仍被数组序碾压，等于没分。这是方案能否成立的前提。
2. **mu-pack gate 路径化**：`mu-fulltext-pack`、`per-article-profile-complete`、`aggregation-threshold`、`scoring-replay-calibrated` 仅在 `fulltext`/`full` 模式下作为 hard gate；`light` 模式不触发这些 step，自然不被它们阻断。

### 4.4 风险提示

- 分层要小心**不要给“降级逃逸”开口子**：light 模式只能产出 metadata-only 结论与标签，**绝不能**让 light 模式输出“全刊稳定体例 / 论证风格 / 参考文献生态高置信”结论——这些必须仍然锁死在 fulltext path 后。建议在 metadata 终态的 gate 里显式断言“completion_label 必须是 METADATA_ONLY_NOT_FULLTEXT_READY，且不得携带 fulltext 维度的 stable/high 结论”。
---

## 4.5 测试覆盖判断（Q6）——主干已覆盖，存在 3 处可补缺口

**已覆盖的关键事故**：sha 不匹配（`mu_pack_sha_no_go`）、样本不足（`mu_pack_below_10`、`aggregation_under_10`）、逐篇缺失（`per_article_missing`）、聚合越级稳定结论（`aggregation_under_10_stable_no_go`）、无 provenance（`provenance_missing`）、评分未校准（`scoring_uncalibrated`）。完整性/越权/凭证泄漏在 state-machine 套件里有 must-fail 守卫。

**建议补的 fixture（按价值排序）**：
1. **正文泄漏守卫**（P1）：`downstream_constraints` 注入 `正文`/`paragraph` 键 → 断言 `per-article-profile-complete` NO_GO。这是边界核心闸，必须补。
2. **新工作流端到端接线**：当前 `run_downstream_consumable_fixtures.py` 全是**直接调 gate**，没有任何 fixture 通过 `journal_style_runner` 跑 `step07b→step08b1→step08b→step09b→step10` 这条新链。**过度阻断的 bug 恰恰长在接线层，而接线层没有集成测试。** 建议补一个最小集成 fixture：构造一个齐全的全文链 task，断言能推进到 step10；再构造一个 metadata-only task，断言（修复后）能到 metadata 终态、（修复前）会卡在 step07b——这条同时充当 P0 的回归锚。
3. **provenance 矛盾分支**：`journal_style_profile_v1` 且 `metadata_only=true` + `source_evidence_scope=mu_fulltext_core_pack` → 断言 NO_GO（该分支已写实现，未被测）。

---

## 5. Phase 2 前置条件

### 5.1 必须先修（进入 Phase 2 之前）

- **[P0]** 工作流过度阻断 + metadata-only 无终态 + `entry` 不被消费（第 2、4 节）。这是 Phase 2“广泛对接下游消费”的地基；不修，metadata 类任务在 runner 下不可用，下游也无法区分 light/full 来源强度。
- **[P1]** 评分先于校准的时序倒置（step09 早于 step09b）。Phase 2 一旦真打分，这个口子会直接违反“未校准不得定位”。
- **[P1]** 正文泄漏守卫补 must-fail fixture（边界核心闸不能裸奔）。

### 5.2 可进入 Phase 2 后再处理

- **[P1]** 逐篇 gate `expected_count` 回查 mu 包就绪篇数（可与 Phase 2 真实逐篇产出一起做）。
- **[P2]** 聚合“5 个必备具名产物”存在性校验。
- **[P2]** handoff-to-wenzhang-runse 文档与 `journal_style_profile_v1` 结构对齐。
- **[P2]** 消费包补顶层 `confidence`/`conclusion_strength`。
- **[P2]** schema 与 gate 一致性测试（防漂移）。
- **[P3]** `ordinary_rag_is_not_substitute` 升为硬约束；`build_material_intake_manifest.py` 评估纳入完整性保护。
---

## 6. 建议下一步（给 Codex 的最小可执行清单）

按顺序、每步可独立验证：

1. **决策模式分层口径**（先定义，再施工）：确认 `light / standard / full` 三模式的能力边界与各自终态，写入 `references/`（建议新增 `references/run-modes-protocol.md`）。这一步只写文档，不动代码。
2. **`workflow-states.json` 路径化**：给每个 step 加 `paths` 标签，并为 metadata path 增加独立终态 step（或让 step10_handoff 接受 metadata-only 标签的精简前置）。
3. **runner 消费 `entry`/`mode`**：改 `compute_position`，按当前模式的 step 子集 + `entry` 依赖判定可达，不再纯数组序 break。补一个集成 fixture 锁住“metadata-only 可达终态”“full 模式仍被 mu 包卡住”。
4. **修评分时序**：让 `step09_fit` 依赖已校准模型（调整 `step09_fit`/`step09b` 的先后或依赖），并加“消费已校准模型”校验。
5. **补三个 fixture**：正文泄漏守卫、新工作流端到端、provenance 矛盾分支（第 4.5 节）。
6. **逐篇 gate 回查 mu 包就绪篇数**：`expected_count` 以 mu 包为权威。
7. **跑全套离线验证 + `build_release_manifest.py --require-clean` 重签**：任何 config/脚本字节变更后，完整性 manifest 必须重建并 `--check` 通过；并复跑两套 fixture + smoke。

> 第 1–3 步是本轮过度阻断的正解，建议作为 Phase 2 的第一批工作；第 4–6 步随后；第 7 步收尾。第 5 节“可延后项”不必挤进这批。

---

## 附：本次审查的事实基础

- 通读了任务清单列出的全部文件（SKILL/progress、5 个新增 schema、stage-gates/workflow-states/release-manifest、runtime/build_material_intake/run_stage_gates、4 个新增协议、8 个更新协议、2 个测试），并额外通读了 `scripts/journal_style_runner.py`、`scripts/journal_style_resume.py` 以判定状态机接线（过度阻断判断的依据）。
- 离线复跑：下游 fixture 11/11、状态机 fixture 24/24、`build_release_manifest.py --check` current、smoke passed——均与 Codex 报告一致。
- 全程未施工、未改源码、未运行真实任务、未连服务器、未触发 CNKI/WoS/Zotero/PDF/RAG、未写 C03、未进真实文衡 B02；除本报告外未写任何文件。

（报告完）
