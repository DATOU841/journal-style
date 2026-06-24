# journal-style Phase 2 施工结果独立复审

- 复审对象：journal-style（下游可消费期刊约束生产器）Phase 2 批次 0–5 施工结果
- 复审类型：只读审查 + 本地离线测试复跑（未改任何 journal-style / 文章润色 源码、配置、schema、测试、progress；未触发 CNKI / WoS / Zotero / PDF / MinerU·mu / RAG 导库 / 服务器 / 文衡 B02·C03·H08 / 模型池）
- 复审人：Claude
- 日期：2026-06-24
- 复核基础：通读 SKILL/progress/Phase 2 施工规划；逐行读 workflow-states、stage-gates、journal_style_runner、run_stage_gates、五个新生成器（analyze_per_article_style / aggregate_journal_style / export_polish_consumption_pack / calibrate_fit_scoring / score_user_manuscript）、三份新 schema、handoff-to-wenzhang-runse；交叉读 文章润色 的 consume-journal-style-profile / assert-journal-style-consumed / consumption-policy / run-fixtures 相关 fixture；本地复跑两套 fixtures + smoke + manifest --check + py_compile + 文章润色 全套。

---

## 1. STATUS

**CHANGES_REQUESTED**

范围限定：批次 0、1、2、3、5 验收通过，质量良好；**唯独批次 4（校准评分）存在一处 P1 级伪数据/越位问题，必须最小返修后才能进入发布前收束。** 其余为可延后的 P2 加固项。

## 2. 业务结论

- **痛点根因（journal-style 给不出可执行信息 / 产销断层）已被真正解决**：逐篇画像→聚合锁→消费包→文章润色消费，这条主链是用真实 mu 包结构字段算出的分布，并且 `文章润色` 端确实读到了 `constraints` 并落进约束锁与最终质量门桥。这部分可以收束。
- **但不能整体放行进入打包/同步**：批次 4 产出的 `journal-fit-scoring-model.json` 把两张硬编码常量分布表标成「已刊样本回放校准结果」（`calibration.status=calibrated` / `source=published_sample_replay`），`score_user_manuscript.py` 又用通用写死区间而非目标期刊聚合 band 给用户稿打分。这正好命中用户划定的「不得有伪数据」「必须真实 per-journal」红线，属于必须返修项。
- 修法很小、可独立完成，不动主链：只需让校准器真正回放逐篇特征算分布、让评分器消费 bundle 的真实 band，并去掉/修正误导性的 provenance 标签。返修后可升为 APPROVED_WITH_NOTES 并进入发布前收束。

## 3. 高优先级问题（按 P0/P1/P2 排序）

### P0

无。状态机时序、gate fail-closed、release 完整性守卫、五具名产物强制、mu 权威计数、metadata 不冒充全文这些硬骨头均已正确闭环（详见第 4、5 节）。

### P1-1：校准评分模型用硬编码常量冒充「已刊样本回放分布」

- 文件：`scripts/calibrate_fit_scoring.py:93-96`
- 问题：`published_score_distribution` 不是回放已刊样本算出来的，而是按 `sample_count>=20` 二选一的两张写死表——`{min70,q1 78,median84,q3 90,max96}` 或 `{65,72,78,84,90}`。同一个产物却写 `calibration.status="calibrated"`（`:104`）、`calibration.source="published_sample_replay"`（`:107`）。即产物对自己的来源做了**与事实不符的声明**。
- 影响：这是本轮唯一命中「伪数据」红线的点。`scoring-replay-calibrated` gate 只校验分布有五分位且 `replay_sample_count>=10`，校验不到「分布是否真由回放得出」，所以伪分布能过闸。下游 `score_user_manuscript.py` 的分位定位（`percentile()`）正是拿这套伪 q1/median/q3 给用户稿定相对位置。
- 建议最小修法：在 `calibrate_fit_scoring.py` 内，遍历 bundle 背后的逐篇画像特征（章节数/关键词数/参考数/有无注释摘要——这些 `per_article_style_profile_v1.dimensions` 里都有），用与 `score_features` 同一套规则对每篇已刊样本打分，得到真实分数序列后再算 min/q1/median/q3/max；若暂不实现真实回放，则必须把 `status` 降为 `in_progress`、去掉 `source=published_sample_replay`、并显式标 `distribution_is_placeholder=true`，不得以 `calibrated` 出厂。

### P1-2：用户稿评分用通用写死区间，而非目标期刊聚合 band（per-journal 名不副实）

- 文件：`scripts/score_user_manuscript.py:64-72`
- 问题：扣分判断写死成 `3<=section<=6`、`3<=keyword<=6`、`15<=reference<=60` 这套通用值；而目标期刊真实区间（`section_min/max`、`keyword_min/max`、`reference_min/max`）在聚合 bundle / 消费包的 `constraints` 里，模型本体 `journal-fit-scoring-model.json` 又根本没带这些 band（`calibrate_fit_scoring.py` 的 model 只有 dimensions 权重 + 分布，不含 band）。
- 影响：所谓「按目标期刊约束锁核对」在评分路径上没有兑现——任何期刊都用同一套通用阈值，与本 skill「per-journal 适配」的立身之本矛盾。
- 建议最小修法：让 `calibrate_fit_scoring.py` 把 bundle 的 `constraints`（section/keyword/reference 等真实 band）写进 model；`score_user_manuscript.score_features` 改为从 model 读该期刊 band 做偏离判断，写死值仅作 band 缺失时的护栏 fallback 并标 `source=fallback`。

### P2-1：正文泄漏守卫的关键词集比声明窄

- 文件：`scripts/run_stage_gates.py:543-561`（`_direct_text_keys`）
- 问题：bad_keys 只含 `paragraph / sentence / draft_text / rewritten_text / copyable_text / 正文`，**不含** `full_text / fulltext / mu_fulltext / sentence_text`。而复审要求与施工口径都点名了 `full_text`。`config/field-policy.json` 另有一套 `fulltext/全文` 禁词，但那套只作用于 metadata-ledger，没有复用到逐篇 `downstream_constraints` 这道守卫上。
- 影响：当前生成器不会产出这些键（`analyze_per_article_style.py` 的 `downstream_constraints` 只写数值 observation），所以是潜在缺口而非现实泄漏。但守卫窄于声明，一旦未来生成器或人工产物塞入 `full_text`，不会被拦。
- 建议最小修法：把 `_direct_text_keys` 的 bad_keys 与 `field-policy.json` 的 forbidden_keys 合流（至少补 `full_text/fulltext/mu_fulltext`），单一事实源。

### P2-2：消费桥的 `profile_driven_constraints` 未受 metadata_only 约束

- 文件：`/Users/a13497/.codex/skills/文章润色/scripts/consume-journal-style-profile.py:135-152`、`:223`
- 问题：`profile_driven_constraints` 在计算时只排除了 `length_band`，**没有**按 `metadata_only` 收口；只有 `full_text_style_constraints_locked`（`:140`）做了 metadata 守卫。于是一个 metadata_only 却（非法地）带着 section_hierarchy/argument_rhythm 的 profile，仍会把这些全文维度写进 lock 和 final-quality-gate 的 `profile_driven_constraints`。`assert-journal-style-consumed.py` 只校验 `style_evidence_usable_for_full_text`/`full_text_style_evidence_locked` 两个 flag，查不到这一层。
- 影响：理论缺口。真实 `aggregate_journal_style.py` 只产 `metadata_only=False` 的包，fixture 里 metadata 场景 `constraints` 也是空的，所以现网不触发。但与「metadata-only 不得驱动全文体例阈值」的口径有一道未上锁的门。
- 建议最小修法：metadata_only 时把 `profile_driven_constraints` 过滤到元数据安全键（或直接置空），并在 assert 里补一条「metadata_only 时 profile_driven_constraints 不得含全文维度」。

### P2-3：逐篇 gate 的 mu 权威重算在 `source_pack` 缺失时被跳过

- 文件：`scripts/run_stage_gates.py:616-621`
- 问题：`gate_per_article_profile_complete` 只有在 batch 声明了 `source_pack/source_mu_pack` 时才回查 mu 包重算 ready；缺该字段时 `expected_count` 回落到自报值（`:619`）。`per_article_profile_batch` schema 未把 `source_pack` 列为硬 required。
- 影响：真实 `analyze_per_article_style.py` 总会写 `source_pack`（`:355`），所以正常链路有权威计数兜底；风险只在「手搓 batch 不带 source_pack」时绕过权威重算。
- 建议最小修法：把 `source_pack` 升为 batch schema / gate 的硬 required，缺失即 NO_GO，堵死自报路径。

### P2-4：handoff 文档示例字段超前于聚合器实际产出

- 文件：`references/handoff-to-wenzhang-runse.md:20-50`
- 问题：示例里的 `title_style.high_frequency_verbs`、`abstract_keywords.abstract_length_range/keyword_order_habits`、`reference_constraints.recent_ratio_target/foreign_ratio_target/self_journal_citation_target`、`section_hierarchy.subsection_habit` 等子字段，`aggregate_journal_style.py` 并不产出。结构（嵌套进 `constraints`）已对齐，但这些叶子字段是「画饼」。
- 影响：下游若按文档期待这些字段会拿到缺失值。非阻断（schema additionalProperties:true，消费脚本对缺字段是容忍的）。
- 建议最小修法：要么实现，要么在文档标注为「预留/未来字段」，避免暗示已交付。

## 4. 边界核验

逐项给结论（✅=未发现问题；⚠️=发现问题）：

- **伪数据**：⚠️ 命中一处。`calibrate_fit_scoring.py:93-96` 的回放分布是写死常量却标 `calibrated`/`published_sample_replay`；`score_user_manuscript.py:64-72` 用通用写死区间冒充 per-journal band。已记为 P1-1 / P1-2。其余生成器（逐篇、聚合、导出）均从真实上游结构字段计算，未见编造。
- **metadata 冒充全文**：✅ 守得住。`gate_completion_label`（`run_stage_gates.py:163-166`）禁止 metadata 提升为 overall 完成；`gate_provenance_required`（`:728-732`）禁止 `metadata_only=true` 同时 `source_evidence_scope=mu_fulltext_core_pack`；workflow 用 path 过滤让 light/standard 走不到 fulltext/scoring 步（`workflow-states.json` + `journal_style_runner.workflow_steps_for_mode`）。消费桥侧另有 metadata 守卫（见 P2-2 的局部缺口，非现实触发）。
- **RAG 冒充 mu**：✅ 守得住。`gate_mu_fulltext_pack`（`:455-463`）强制 `schema=...mu_fulltext_core_pack_v1`、`mu_processing_required=true`、`mu_processor∈{mineru,mu}`、`ordinary_rag_is_not_substitute`；并对每篇校验 `fulltext_sha256` 自洽（`:499-501`）。
- **正文泄漏**：✅（现实）/ ⚠️（守卫窄）。逐篇 `downstream_constraints` 只写数值 observation，无任何可抄写文本键；`per-article-profile-complete` gate 用 `_direct_text_keys` 拦截。守卫关键词集偏窄已记为 P2-1。
- **模拟主编 / 录用概率**：✅ 守得住。`scoring-replay-calibrated` gate 强制 `not_editor_simulation=true`、`no_acceptance_prediction=true`（`:748-751`）；`calibrate_fit_scoring` 与 `score_user_manuscript` 均显式声明且报告正文写明「不是主编模拟，不预测录用概率」（`score_user_manuscript.py:96`）。措辞合规。
- **真实外链触发**：✅ 未发现。五个新脚本无 `requests/urllib/socket/httpx/aiohttp` 等网络库；全部 `subprocess` 仅本地调用 `run_stage_gates.py` / `gate_runner.py`。复跑测试只写临时目录，未触达 CNKI/WoS/Zotero/MinerU/RAG/服务器/文衡/模型池。
- **是否被改造成正文写作工具**：✅ 否。产物全是画像/约束锁/消费包/评分依据，消费桥明确「不改正文」「缺失维度回 journal-style 或检索入库补材料，不在此处补写正文」（`consume`/`score_user_manuscript` 文案）。

> 补充（非缺陷，记录其保守行为）：`aggregate_journal_style.conclusion_strength` 最高只返回 `medium`，`artifact()` 里 high→medium 的降级实际永不触发，即「30+ 才建议高置信」被保守地永不自动产出。这是 fail-safe 取向，安全但偏保守，可在真实样本充足后再放开。

## 5. 下游可消费性判断

**结论：核心产销断层（journal-style → 文章润色）这一轮真正打通了；唯一残留断点在「评分校准依据」这条支链，不在主消费链上。**

主链（已闭合）：
1. `analyze_per_article_style.py` 先过 `mu-fulltext-pack` gate，不达标只写 `pending-materials.json`，达标才逐篇产 `per_article_style_profile_v1`；确定性维度从 mu 结构字段算，语义维度无锚点即标 `gap:`（`infer_material_types/method_types:200/213`），每维挂 `evidence_path`。
2. `aggregate_journal_style.py` 先过 `per-article-profile-complete` gate，再用分布（min/median/q1/q3 + 众数，非裸均值）聚成五具名产物；`aggregation-threshold` gate 缺任一具名产物即 NO_GO（`run_stage_gates.py:682-684`，配置见 `stage-gates.json:129-135`）。
3. `export_polish_consumption_pack.py` 只从 bundle 抽 `journal-polish-consumption-pack` 的 payload（`find_consumption_pack`），两侧过 `aggregation-threshold` + `provenance-required`，不另起炉灶臆造。消费包带顶层 `confidence`/`conclusion_strength`（schema required 已加，`journal-polish-consumption-pack-schema.json:11-12`）。
4. `文章润色/consume-journal-style-profile.py` **确实读** `journal_style_profile_v1.constraints`（`:29/44`），非字数维度进 `profile_driven_constraints` 并落进约束锁与 final-quality-gate 桥（`:152/223`）；`length_band` 只进 `word_count_policy` 展示、`word_count_target_is_gate=False`、保留 13000–18000 不被覆盖（`:126/154/224-225`）。fixture `fixture_gsy_16` 用真实值断言了 `section_min==4`/`keyword_max==5`/`reference_min==22` 的流通，且字数仍非 gate；`fixture_gsy_17` 断言 metadata 冒充全文会被 assert 拦下。

断点（支链，待 P1 返修后才闭合）：
- 「适配评分模型 / 评分校准依据」名义上交付了 `journal-fit-scoring-model.json` + `submission-fit-score.md`，但模型的回放分布是伪造、用户稿评分用通用 band。也就是说，下游若要消费「这篇稿子相对该刊已刊样本处于什么分位、各维度该补什么」，目前拿到的是占位结果，不是真实 per-journal 校准。这条支链在 P1-1/P1-2 修好前不算可消费。

模型/结果分离本身是对的：`score_user_manuscript.py` 只写 `submission-fit-score.md`（`DEFAULT_OUTPUT`），不回写模型本体；缺稿件特征时写「待补、暂不定位」而非编分（`:103-117`）；先过 `submission-fit-ready` gate 才打分（`:165`）。问题只在「分布与 band 的真实性」，不在分离与时序。

## 6. 复审点逐项核对（对应施工 prompt 的检查清单）

### 批次 0（状态机接线闭环）— 全部通过
- step09b 物理序先于 step09_fit：✅ `workflow-states.json:263`(step09b) 早于 `:280`(step09_fit)；且执行层双锁——step09_fit.entry=[step09b.satisfied]，自身 gate `submission-fit-ready` 再校验模型。
- runner 真正消费 entry/requires_inputs：✅ `journal_style_runner.validate_step_order`(`:140`) 断言数组序==拓扑序，`_entry_satisfied`(`:129`) 运行时校验依赖完成，`step_satisfied`(`:88`) 校验 requires_inputs/produces 落盘并现场重跑 gate。（`next` 字段未被消费、改由数组序+entry 权威，等价且更稳，可接受。）
- submission-fit-ready 阻断未校准：✅ `gate_submission_fit_ready`(`:786`) 包裹 `scoring-replay-calibrated` 并继承全部 problems。
- mu 结构字段硬 required / notes advisory：✅ `stage-gates.json:97-104` + `gate_mu_fulltext_pack:481-490`（required_structure 缺即弃篇）/`:515-518`（notes 仅覆盖率 warning）。
- per-article 以 mu ready 为权威：✅ `gate_per_article_profile_complete:616-640` 独立重算 mu ready，`expected_count=mu_ready_count or ...`，自报低于重算即 NO_GO。
- light/standard 不被 mu gate 误阻断、不出全文结论：✅ path 过滤 + `gate_completion_label` 禁止 metadata 提升 overall。

### 批次 1（逐篇画像）— 全部通过
- 只消费 mu 包且先过 gate：✅ `analyze_per_article_style.py:343-347`。
- 不达标只写 pending：✅ `:338-347`、`write_pending:304`。
- 逐篇优先 + 语义维度强制 evidence_path、无证据标 gap：✅ `evidence_index:252-266`，`infer_*` 无锚点回 `gap:`。
- 正文泄漏守卫：✅（现实）downstream_constraints 仅数值；守卫窄见 P2-1。

### 批次 2（聚合锁 + 五具名产物）— 全部通过
- 吃 gate-passing 画像：✅ `aggregate_journal_style.py:243-247`。
- 五具名产物强制、缺一 NO_GO：✅ `build_bundle:178-195` + `gate_aggregation_threshold:682-684`。
- 样本门槛 fail-closed：✅ `conclusion_strength:97-102`（<10 仅 observation、<20 不得 stable）+ gate `:697-702`（<10 only observation、<20 禁 stable、arg/ref/network<30 禁 high）。

### 批次 3（消费包）— 通过（含 P2-4 文档项）
- 从 bundle 导出不臆造：✅ `find_consumption_pack:46-52`。
- 顶层 confidence/conclusion_strength：✅ pack 与 schema 均含。
- length_band advisory_only、不 gate、不覆盖 13000-18000：✅。
- handoff 文档对齐嵌套 constraints：✅ 结构已对齐；叶子字段超前见 P2-4。

### 批次 4（校准评分）— 部分通过，命中 P1-1 / P1-2
- 产物结构（分布五分位 + dimensions 权重 + rationale）：✅ 结构在、gate 校验在。
- 模型/结果分离、缺特征不编分、措辞不越界：✅。
- 「已刊样本回放分布」真实性 / per-journal band：⚠️ 伪造 + 通用写死（P1-1/P1-2，必须返修）。

### 批次 5（跨 skill 消费桥）— 全部通过
- 真实读 constraints、非字数进 profile_driven、length_band 不 gate 不覆盖：✅。
- assert + fixtures 覆盖「全文 profile 产非字数约束」「字数仍非 gate」：✅ `fixture_gsy_16`。
- metadata 不驱动全文阈值：✅（flag 层 + 空 constraints 场景）；深层守卫缺口见 P2-2。

## 7. 测试复核（我实际运行的命令与结果）

均在 macOS / `python3` 3.9.6 本地离线执行，未触发任何外部链路：

journal-style（`/Users/a13497/.codex/skills/journal-style`）：
- `python3 tests/run_downstream_consumable_fixtures.py` → **21/21 passed, 0 failed**（与 progress 声称一致）。
- `python3 tests/run_state_machine_fixtures.py` → **28/28 passed, 0 failed**（含 full-chain 终态、未校准模型阻断、mu ready 权威计数三条新回归）。
- `python3 scripts/run_smoke_tests.py` → **smoke tests passed**。
- `python3 scripts/build_release_manifest.py --check` → **release-manifest.json is current**（五个新脚本 sha256 均在 manifest，`release-manifest.json:25-29`）。
- `python3 -m py_compile scripts/*.py tests/*.py` → **passed**。
- 网络库扫描（requests/urllib/socket/httpx/aiohttp）→ 五个新脚本 **零命中**。
- `git status --porcelain` → 工作树有未提交改动（M：SKILL/config/references/scripts/tests 等；??：.handoff、三新 schema、五新脚本）。这些是 Codex 的 Phase 2 施工产物，**非本次复审所改**；我只读 + 跑测试 + py_compile，未触碰任何受控源/配置/schema/测试/progress。

文章润色（`/Users/a13497/.codex/skills/文章润色`，注意该目录非 git repo，无法用 git status 判改动）：
- `python3 tests/run-fixtures.py --all` → **212/212 passed**，顶层 status=passed（首次粗解析误报「77/1」，复核为流串扰假象，已用按 status 清点定论）。
- `python3 scripts/run-local-gate.py --pre-review` → **passed**（errors=[]）。
- `python3 scripts/verify-skill-structure.py --target article-polish` → **ok=true**。

未运行项：CNKI/WoS/Zotero/PDF/MinerU·mu/RAG/服务器/文衡/模型池全部按边界**主动未触发**；真实期刊端到端任务**未跑**（本轮是复审，不是真实运行）。

## 8. 发布建议

**暂不允许进入发布/打包/同步**；先做下方最小返修，返修并复跑后即可放行（届时 STATUS 可升 APPROVED_WITH_NOTES）。

最小返修清单（P1，必做）：
1. `calibrate_fit_scoring.py`：用 bundle 背后逐篇画像特征做真实回放算 `published_score_distribution`；若本阶段不实现真实回放，则把 `calibration.status` 降为 `in_progress`、删去 `source=published_sample_replay`、加 `distribution_is_placeholder=true`，禁止以 `calibrated` 出厂。
2. `calibrate_fit_scoring.py` + `score_user_manuscript.py`：把目标期刊真实 band（section/keyword/reference 等）写进 model 并在 `score_features` 中消费；通用写死值仅作 fallback 且标 `source=fallback`。
3. 复跑两套 fixtures + smoke + `--check`；若上述改动触及 model 形态，补一条「分布须由回放得出 / band 须来自 bundle」的回归断言，避免再次以伪数据过闸。

建议但可延后（P2，不阻断发布，列入下一个小步）：
- P2-1 合并 `_direct_text_keys` 与 field-policy 禁词（补 full_text/fulltext/mu_fulltext）。
- P2-2 消费桥按 metadata_only 收口 `profile_driven_constraints` 并补 assert。
- P2-3 把 `source_pack` 升为 batch schema/gate 硬 required。
- P2-4 handoff 文档把未实现叶子字段标「预留/未来」。

> 复审范围声明：本轮以审查为主，未写新规划大纲、未扩展 Phase 3；所有修法均为最小可执行项。批次 0/1/2/3/5 的实现质量与边界守持均达标，主产销断层已解决；唯批次 4 的评分校准真实性需返修后方可整体收束。
