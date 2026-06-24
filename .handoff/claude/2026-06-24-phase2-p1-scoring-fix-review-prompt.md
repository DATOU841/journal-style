# Claude 定向复审提示词：journal-style Phase 2 P1 scoring fix review

你是 Claude。本轮任务是对 Codex 针对 Phase 2 implementation review 中 P1 批次 4 评分问题的返修做定向复审，不是重新规划 Phase 3，不是继续施工，不是运行真实期刊任务。

你有写入权限，请将结果写入 `/Users/a13497/.codex/skills/journal-style/.handoff/claude/2026-06-24-phase2-p1-scoring-fix-review.md`。

## 背景

你上一轮报告 `/Users/a13497/.codex/skills/journal-style/.handoff/claude/2026-06-24-phase2-implementation-review.md` 给出：

- `STATUS: CHANGES_REQUESTED`
- 批次 0/1/2/3/5 通过
- 唯一必须返修是批次 4 评分校准 P1

你指出的两个 P1 问题是：

1. `scripts/calibrate_fit_scoring.py` 用硬编码常量表冒充 `published_sample_replay`，却标 `calibration.status=calibrated`。
2. `scripts/score_user_manuscript.py` 用通用写死区间（如 3-6 节）给用户稿评分，没有消费目标期刊聚合 band。

Codex 已做最小返修，不动逐篇画像、聚合锁、消费包、文章润色消费桥主链。

## 本轮只审这些文件

- `/Users/a13497/.codex/skills/journal-style/scripts/calibrate_fit_scoring.py`
- `/Users/a13497/.codex/skills/journal-style/scripts/score_user_manuscript.py`
- `/Users/a13497/.codex/skills/journal-style/scripts/run_stage_gates.py`
- `/Users/a13497/.codex/skills/journal-style/config/scoring-model-schema.json`
- `/Users/a13497/.codex/skills/journal-style/references/scoring-model-protocol.md`
- `/Users/a13497/.codex/skills/journal-style/tests/run_downstream_consumable_fixtures.py`
- `/Users/a13497/.codex/skills/journal-style/tests/run_state_machine_fixtures.py`
- `/Users/a13497/.codex/skills/journal-style/config/release-manifest.json`
- `/Users/a13497/.codex/skills/journal-style/progress.md`

可按需核对上一轮 review 报告和 Phase 2 规划，但不要扩大为全量重审，除非发现返修牵动了主链。

## 需要确认的闭合点

### P1-1：校准分布是否真实来自逐篇画像回放

请核对：

- `calibrate_fit_scoring.py` 是否读取 `per-article-style-profiles.json`，并先通过 `per-article-profile-complete` gate。
- `calibration.source` 是否从误导性的 `published_sample_replay` 改为真实的 `per_article_profile_replay`。
- `replay_scores[]` 是否逐篇生成，含 article_id、score、feature_values、deductions。
- `published_score_distribution` 是否由 `replay_scores[]` 计算得出，而不是常量表。
- `run_stage_gates.py` 的 `scoring-replay-calibrated` 是否会反算 `replay_scores[]` 并拒绝分布不一致的模型。
- `tests/run_downstream_consumable_fixtures.py` 是否有常量伪分布 must-fail fixture。

### P1-2：用户稿评分是否消费目标期刊 band

请核对：

- `calibrate_fit_scoring.py` 是否把 aggregation bundle 中的目标期刊 constraints 写入 `scoring_constraints`。
- `score_user_manuscript.py` 是否从 model 的 `scoring_constraints` 读取 section/keyword/reference band，而不是直接使用通用写死区间。
- 通用区间是否只作为缺字段 fallback，并在报告/扣分项里标注来源。
- `tests/run_downstream_consumable_fixtures.py` 是否有目标期刊 band 应用 fixture，例如 section 4-4、reference 22-22 能触发对应扣分和报告文本。

## 边界

- 不得修改源码、配置、schema、测试、progress。
- 不得触发 CNKI、WoS、Zotero、PDF 获取、MinerU/mu 实际处理、RAG 导库、服务器、文衡 B02/C03/H08、模型池。
- 只可运行本地离线测试、JSON 校验、py_compile、manifest check。
- 只评价这次 P1 是否闭合；P2 加固项仍可作为 notes，不得因此扩大返修范围，除非它们直接阻断 P1。

## Codex 已复跑的本地验证

`journal-style`：

```bash
cd /Users/a13497/.codex/skills/journal-style
python3 tests/run_downstream_consumable_fixtures.py   # passed, 23/23
python3 tests/run_state_machine_fixtures.py           # passed, 28/28
python3 scripts/run_smoke_tests.py                    # passed
python3 -m py_compile scripts/*.py tests/*.py          # passed
python3 scripts/build_release_manifest.py --check      # current
git diff --check                                      # passed
```

`文章润色`：

```bash
cd /Users/a13497/.codex/skills/文章润色
python3 tests/run-fixtures.py --all                    # passed
python3 scripts/verify-skill-structure.py --target article-polish  # passed
```

说明：`python3 scripts/run-local-gate.py --pre-review` 在 `文章润色` 侧失败，报 `pre-review mode expected Claude review to be absent or unpublished`。这是因为当前已存在 Claude review，不是本次 journal-style 评分返修造成的 fixture 或结构失败；请按流程语义判断，不要误判为功能回归。

## 输出格式

报告必须包含：

1. `STATUS`：只能是 `APPROVED`、`APPROVED_WITH_NOTES`、`CHANGES_REQUESTED`、`BLOCKED`。
2. `业务结论`：P1 是否闭合，是否可以进入发布前收束。
3. `P1 闭合判断`：逐条说明 P1-1/P1-2 是否已闭合。
4. `仍需返修项`：若有，按 P0/P1/P2 排序；只列阻断发布的最小项。
5. `边界核验`：是否仍有伪数据、metadata/RAG 冒充 mu、模拟主编/录用概率、真实外链触发。
6. `测试复核`：列出你实际运行的命令和结果。
7. `发布建议`：允许或不允许进入发布/打包/同步。

若 P1 已闭合，请给出 `APPROVED_WITH_NOTES` 或 `APPROVED`；P2 notes 可保留为后续小步，不要阻断发布前收束。
