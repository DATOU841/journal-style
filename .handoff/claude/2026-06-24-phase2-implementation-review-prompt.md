# Claude 复审提示词：journal-style Phase 2 implementation review

你是 Claude，本轮任务是对 `journal-style` Phase 2 施工结果做独立复审，不是继续规划、不是继续施工、不是运行真实期刊任务。

你有写入权限，请将结果写入 `/Users/a13497/.codex/skills/journal-style/.handoff/claude/2026-06-24-phase2-implementation-review.md`。

## 任务边界

- 只读审查源码、协议、schema、fixture、progress 和本地离线测试结果。
- 可以运行本地离线测试、JSON 校验、py_compile、manifest check。
- 不得修改 `journal-style` 或 `文章润色` 源码、配置、schema、测试、progress。
- 不得触发 CNKI、WoS、Zotero、PDF 获取、MinerU/mu 实际处理、RAG 导库、服务器、文衡 B02/C03/H08、模型池。
- 不得把 `journal-style` 变成正文写作或文章润色工具；它只生产期刊画像、约束锁、下游可消费包和评分校准依据。
- `mu` 指 MinerU，是上游 `检索入库` 将 PDF 文献处理成完整文本版本的方式；本 skill 只验收和分析上游交付的 mu 包。

## 背景

用户指出根因：`journal-style` 过去几乎不能给 `文章润色` 等下游 skill 提供可执行信息。普通 RAG 包不足以支撑文章体例分析；需要额外的 MinerU/mu 完整全文核心样本包，对 10 篇以上核心文献做逐篇体例分析，再分组聚合，形成下游可消费的期刊格式、题名、摘要关键词、章节层级、注释/参考文献、论证节奏、参考文献生态和适配评分模型。

Phase 1 已建立 schema/gate/fixture 地基。你此前规划的 Phase 2 施工顺序是：批次 0 接线闭环，批次 1 逐篇画像生成器，批次 2 聚合锁，批次 3 文章润色消费包，批次 4 校准评分脚本，批次 5 打通 `文章润色` 消费桥。本轮 Codex 已按此顺序施工。

## 需要重点复审的施工结果

### 批次 0：状态机接线闭环

复审点：
- `step09b_scoring_calibration` 是否在物理 workflow 顺序和执行约束上均先于 `step09_fit`。
- runner 是否真正消费 `entry` / `requires_inputs`，而不是只把它们当装饰字段。
- `submission-fit-ready` 是否阻断未校准模型进入用户稿评分。
- `mu-fulltext-pack` 中 `section_tree`、`paragraph_sequence`、`reference_list` 是否为 full 模式 hard required，`notes` 是否仍为 advisory。
- `per-article-profile-complete` 是否以 mu 包 ready 篇数为权威计数，不信任画像自报 ready count。
- `light` / `standard` metadata-only 路径是否不被 MinerU/mu fulltext gate 误阻断，且不得输出全文体例稳定结论。

### 批次 1：逐篇体例画像生成器

复审点：
- 新增 `scripts/analyze_per_article_style.py` 是否只消费上游 mu 包，并先过 `mu-fulltext-pack` gate。
- mu 包不达标时是否只写 `pending-materials.json`，不生成正式画像。
- 画像是否遵守“逐篇 -> 分组 -> 聚合”的第一步；语义维度是否强制 evidence_path 锚定，无证据时标 gap。
- 是否有正文泄漏守卫，不能把 `正文`、`paragraph`、`full_text` 等可直接抄写文本作为下游约束输出。

### 批次 2：聚合锁和五个具名产物

复审点：
- 新增 `scripts/aggregate_journal_style.py` 是否吃 gate-passing 的逐篇画像。
- `journal-style-aggregation-bundle.json` 是否强制包含五个具名产物：
  - `journal-style-constraints-lock`
  - `journal-format-convention-profile`
  - `journal-argument-preference-profile`
  - `journal-reference-ecology-lock`
  - `journal-polish-consumption-pack`
- `aggregation-threshold` gate 是否缺任一具名产物即 NO_GO。
- 样本门槛是否 fail-closed：少于 10 篇只能待补，10-19 篇只能初步偏好，20 篇以上才允许稳定体例，30 篇以上才建议论证风格/参考生态高置信。

### 批次 3：文章润色消费包

复审点：
- 新增 `scripts/export_polish_consumption_pack.py` 是否从聚合 bundle 导出 `05-handoff/journal-polish-consumption-pack.json`，而不是重新臆造。
- `journal_style_profile_v1` 是否带顶层 `confidence` / `conclusion_strength`。
- `constraints.length_band` 是否 `advisory_only`，只展示，不作为 gate，不覆盖 `文章润色` 13000-18000 策略。
- `references/handoff-to-wenzhang-runse.md` 是否已与真实嵌套 `constraints` 结构对齐。

### 批次 4：校准评分模型和用户稿评分结果分离

复审点：
- 新增 `scripts/calibrate_fit_scoring.py` 是否产出 `journal-fit-scoring-model.json`，包含已刊样本回放分布、维度、权重和 `dimensions[].rationale`。
- 新增 `scripts/score_user_manuscript.py` 是否只把用户稿应用结果写到 `submission-fit-score.md`，不污染模型本体。
- 未校准、回放不足或缺 rationale 时是否不能做用户稿分位定位。
- 文案是否避免“模仿主编”“录用概率”等越界表达。

### 批次 5：跨 skill 文章润色消费桥

复审点：
- `/Users/a13497/.codex/skills/文章润色/scripts/consume-journal-style-profile.py` 是否真实读取 `journal_style_profile_v1.constraints`。
- 非字数约束是否进入 `profile_driven_constraints` 或等价内部约束锁，供后续 skeleton、格式检查和最终质量门消费。
- `length_band` 是否只展示、不 gate、不覆盖 13000-18000。
- `/Users/a13497/.codex/skills/文章润色/scripts/assert-journal-style-consumed.py` 和 fixtures 是否覆盖“fulltext profile 产生非字数约束”“字数仍非 gate”。
- metadata-only journal profile 是否不得驱动全文体例阈值。

## 重点文件

`journal-style`：

- `/Users/a13497/.codex/skills/journal-style/SKILL.md`
- `/Users/a13497/.codex/skills/journal-style/config/workflow-states.json`
- `/Users/a13497/.codex/skills/journal-style/config/stage-gates.json`
- `/Users/a13497/.codex/skills/journal-style/config/mu-fulltext-pack-schema.json`
- `/Users/a13497/.codex/skills/journal-style/config/per-article-profile-schema.json`
- `/Users/a13497/.codex/skills/journal-style/config/aggregation-schema.json`
- `/Users/a13497/.codex/skills/journal-style/config/journal-polish-consumption-pack-schema.json`
- `/Users/a13497/.codex/skills/journal-style/config/scoring-model-schema.json`
- `/Users/a13497/.codex/skills/journal-style/scripts/journal_style_runner.py`
- `/Users/a13497/.codex/skills/journal-style/scripts/run_stage_gates.py`
- `/Users/a13497/.codex/skills/journal-style/scripts/analyze_per_article_style.py`
- `/Users/a13497/.codex/skills/journal-style/scripts/aggregate_journal_style.py`
- `/Users/a13497/.codex/skills/journal-style/scripts/export_polish_consumption_pack.py`
- `/Users/a13497/.codex/skills/journal-style/scripts/calibrate_fit_scoring.py`
- `/Users/a13497/.codex/skills/journal-style/scripts/score_user_manuscript.py`
- `/Users/a13497/.codex/skills/journal-style/tests/run_downstream_consumable_fixtures.py`
- `/Users/a13497/.codex/skills/journal-style/tests/run_state_machine_fixtures.py`
- `/Users/a13497/.codex/skills/journal-style/progress.md`

`文章润色`：

- `/Users/a13497/.codex/skills/文章润色/SKILL.md`
- `/Users/a13497/.codex/skills/文章润色/state/dev-error-memory.md`
- `/Users/a13497/.codex/skills/文章润色/scripts/consume-journal-style-profile.py`
- `/Users/a13497/.codex/skills/文章润色/scripts/assert-journal-style-consumed.py`
- `/Users/a13497/.codex/skills/文章润色/config/journal-style-consumption-policy.json`
- `/Users/a13497/.codex/skills/文章润色/templates/journal-style-constraints-lock-template.json`
- `/Users/a13497/.codex/skills/文章润色/tests/run-fixtures.py`
- `/Users/a13497/.codex/skills/文章润色/progress.md`

## Codex 已复跑的本地验证

你应独立复跑关键项，至少核验这些结果是否可信：

`journal-style`：

```bash
cd /Users/a13497/.codex/skills/journal-style
python3 tests/run_downstream_consumable_fixtures.py
python3 tests/run_state_machine_fixtures.py
python3 scripts/run_smoke_tests.py
python3 -m json.tool config/workflow-states.json >/dev/null
python3 -m json.tool config/stage-gates.json >/dev/null
python3 -m json.tool config/mu-fulltext-pack-schema.json >/dev/null
python3 -m json.tool config/per-article-profile-schema.json >/dev/null
python3 -m json.tool config/aggregation-schema.json >/dev/null
python3 -m json.tool config/journal-polish-consumption-pack-schema.json >/dev/null
python3 -m json.tool config/scoring-model-schema.json >/dev/null
python3 -m json.tool config/release-manifest.json >/dev/null
python3 -m py_compile scripts/*.py tests/*.py
python3 scripts/build_release_manifest.py --check
```

Codex 当前观察到：下游可消费 fixture 21/21 passed，状态机 fixture 28/28 passed，smoke passed，JSON/py_compile passed，release manifest current。

`文章润色`：

```bash
cd /Users/a13497/.codex/skills/文章润色
python3 tests/run-fixtures.py --all
python3 scripts/run-local-gate.py --pre-review
python3 scripts/verify-skill-structure.py --target article-polish
```

Codex 当前观察到：fixtures 全部 passed，pre-review status=passed，structure check ok=true。`文章润色` 目录当前不是 git repo，不能用 git status 判断改动。

## 你需要给出的结论格式

报告必须包含：

1. `STATUS`：只能是 `APPROVED`、`APPROVED_WITH_NOTES`、`CHANGES_REQUESTED`、`BLOCKED` 之一。
2. `业务结论`：是否可以进入发布前收束，还是必须返修。
3. `高优先级问题`：按 P0/P1/P2 排序；每条给文件路径、问题、影响、建议修法。
4. `边界核验`：明确说明是否发现伪数据、metadata 冒充全文、RAG 冒充 mu、正文泄漏、模拟主编/录用概率、真实外链触发等问题。
5. `下游可消费性判断`：说明这次是否真正解决 `journal-style` 到 `文章润色` 的产销断层；若仍有断点，指出断点在哪里。
6. `测试复核`：列出你实际运行的命令和结果；若未运行，说明原因。
7. `发布建议`：是否允许进入下一步发布/打包/同步；若不允许，列最小返修清单。

请以审查为主，不要写新规划大纲，不要扩展 Phase 3。若发现问题，只给最小可执行修复建议。
