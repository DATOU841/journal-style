## 2026-06-24 - Task: journal-style Phase 1 downstream-consumable contracts and gates
### What was done
- Added Phase 1 contracts for MinerU/mu complete fulltext core packs, per-article style profiles, aggregation bundles, polish consumption packs, and calibrated fit scoring models.
- Extended the workflow and gate policy so fulltext style claims require an upstream MinerU/mu complete-text pack, per-article profiling before aggregation, provenance before downstream handoff, and replay calibration before scoring use.
- Updated downstream handoff protocols so article polish, writing, reference-footnote, and search-intake receive executable constraints and missing-material requests instead of broad descriptive reports.
- Added offline regression fixtures for the new downstream-consumable gates and refreshed the release manifest so the new config/scripts are integrity-protected.
### Testing
- `python3 -m json.tool` on updated and newly added JSON config/schema files: passed.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 11/11 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 24/24 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed.
### Notes
- `SKILL.md`: documented MinerU/mu complete fulltext pack acceptance, per-article profiling, downstream constraints, and calibrated scoring boundaries.
- `config/mu-fulltext-pack-schema.json`: added the MinerU/mu complete fulltext core pack schema.
- `config/per-article-profile-schema.json`: added the per-article style profile batch schema.
- `config/aggregation-schema.json`: added the aggregation bundle schema for constraints locks and downstream packs.
- `config/journal-polish-consumption-pack-schema.json`: added the real `journal_style_profile_v1` consumption pack schema for future article-polish integration.
- `config/scoring-model-schema.json`: added the calibrated fit scoring model schema.
- `config/stage-gates.json`: added thresholds for MinerU/mu pack acceptance, per-article profile completion, aggregation strength, provenance, and scoring replay calibration.
- `config/workflow-states.json`: inserted MinerU/mu pack acceptance, per-article profiling, aggregation, scoring calibration, and provenance-gated handoff steps.
- `config/release-manifest.json`: refreshed integrity hashes for the protected config/scripts.
- `references/mu-fulltext-pack-protocol.md`: documented MinerU/mu pack purpose, fields, and acceptance rules.
- `references/per-article-profile-protocol.md`: documented per-article style profiling requirements.
- `references/aggregation-and-consumption-protocol.md`: documented aggregation locks and downstream consumption pack rules.
- `references/scoring-model-protocol.md`: documented calibrated scoring model boundaries and replay requirements.
- `references/evidence-rules.md`: added MinerU/mu complete fulltext evidence rules and downgrade policy.
- `references/stage-gates-protocol.md`: documented the new fail-closed gates.
- `references/output-schema.md`: added the new required artifacts and fields.
- `references/handoff-to-wenzhang-runse.md`: upgraded article-polish handoff fields to executable constraints.
- `references/handoff-to-zhengwen-xiezuo.md`: upgraded writing handoff fields to structure and argument constraints.
- `references/handoff-to-cankao-wenxian.md`: upgraded reference-footnote handoff fields to reference ecology lock fields.
- `references/handoff-to-jiansuo-ruku.md`: added MinerU/mu complete fulltext pack request fields.
- `scripts/build_material_intake_manifest.py`: registered the new Phase 1 artifacts in Step0 material intake.
- `scripts/journal_style_runtime.py`: added new schema files to release integrity tracking and mapped the new gates.
- `scripts/run_stage_gates.py`: implemented the new gate logic.
- `tests/run_downstream_consumable_fixtures.py`: added synthetic offline fixtures for the new gates.
- Rollback: revert this task by restoring the modified tracked files from the previous git revision and deleting the newly added Phase 1 schema/protocol/test files listed above; then rebuild `config/release-manifest.json` from the restored state.

## 2026-06-24 - Task: journal-style Phase 1 review fixes for run modes and scoring order
### What was done
- Added `light` / `standard` / `full` run-mode handling so metadata-only tasks can reach a metadata terminal without being blocked by the MinerU/mu fulltext gate.
- Kept MinerU/mu fulltext pack, per-article profiling, aggregation, and calibrated scoring as hard gates for `full` mode only.
- Reordered scoring so the calibrated scoring model precedes `submission-fit-score.md`.
- Added regression coverage for metadata-mode reachability, full-mode MinerU/mu blocking, direct正文 leakage in downstream constraints, and metadata/fulltext provenance conflict.
### Testing
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 13/13 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 26/26 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 -m json.tool config/workflow-states.json` and `config/stage-gates.json`: passed.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed.
### Notes
- `config/workflow-states.json`: added run-mode path tags, metadata terminal path, fulltext-only MinerU/mu chain, and scoring-after-calibration order.
- `scripts/journal_style_runner.py`: added mode resolution and path-filtered state progression.
- `scripts/build_task_skeleton.py`: added `--run-mode` and persisted mode into task state/status.
- `references/run-modes-protocol.md`: added the run-mode protocol and anti-escape rules.
- `references/output-schema.md`: documented `run_mode` values and terminal semantics.
- `references/stage-gates-protocol.md`: documented path gating and scoring order rules.
- `SKILL.md`: documented run modes and clarified MinerU/mu is full-mode-only.
- `tests/run_state_machine_fixtures.py`: added metadata/full path integration fixtures.
- `tests/run_downstream_consumable_fixtures.py`: added direct正文 leakage and provenance conflict must-fail fixtures.
- `config/release-manifest.json`: refreshed integrity hashes for protected config/scripts.
- Rollback: revert the files listed in this entry to the prior git revision and rebuild `config/release-manifest.json`.

## 2026-06-24 - Task: journal-style Phase 2 batch 0 wiring closure
### What was done
- Closed the scoring execution gap by placing replay calibration before submission-fit scoring in the physical workflow order and adding a `submission-fit-ready` gate over the calibrated scoring model.
- Made the runner consume `entry` dependencies and `requires_inputs`, so workflow declarations are execution constraints instead of decorative metadata.
- Made MinerU/mu ready counts authoritative for per-article profile completeness and upgraded `section_tree`, `paragraph_sequence`, and `reference_list` to full-mode hard required fields while keeping `notes` advisory.
- Added offline regression fixtures for full-mode end-to-end reachability, uncalibrated scoring blockage, and mu-pack-ready-count enforcement.
### Testing
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 14/14 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 28/28 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 -m json.tool config/workflow-states.json config/stage-gates.json config/mu-fulltext-pack-schema.json`: passed.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed.
### Notes
- `config/workflow-states.json`: moved calibration before fit scoring and attached `submission-fit-ready` to the scoring step.
- `config/stage-gates.json`: added `submission-fit-ready`, split hard required and advisory MinerU/mu structure fields.
- `config/mu-fulltext-pack-schema.json`: made `section_tree`, `paragraph_sequence`, and `reference_list` required per article.
- `scripts/journal_style_runner.py`: now verifies `entry` ordering and required inputs before satisfying steps.
- `scripts/journal_style_runtime.py`: mapped `submission-fit-ready` to the gate runner.
- `scripts/run_stage_gates.py`: added calibrated-model fit gating and mu-pack authoritative ready-count checks for per-article profiles.
- `tests/run_downstream_consumable_fixtures.py`: added the mu ready-count authority regression.
- `tests/run_state_machine_fixtures.py`: added full-chain terminal and uncalibrated-model blockage regressions.
- `references/mu-fulltext-pack-protocol.md`: documented full-mode hard required structure fields.
- `references/handoff-to-jiansuo-ruku.md`: documented upstream MinerU/mu pack field obligations.
- `references/stage-gates-protocol.md`: documented the new scoring and MinerU/mu gate rules.
- `config/release-manifest.json`: refreshed integrity hashes for protected config/scripts.
- Rollback: revert the files listed in this entry to the previous revision and rebuild `config/release-manifest.json`.

## 2026-06-24 - Task: journal-style Phase 2 batch 1 per-article profile generator
### What was done
- Added an offline per-article profile generator that consumes only an upstream MinerU/mu fulltext core pack, validates it with the existing `mu-fulltext-pack` gate, and emits `per-article-style-profiles.json`.
- The generator computes deterministic structure dimensions from MinerU/mu fields and attaches evidence paths for controlled semantic dimensions; it writes `pending-materials.json` instead of profiles when the mu pack is not gate-ready.
- Added regression coverage proving valid packs generate gate-passing profiles and insufficient packs do not create formal profiles.
### Testing
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 16/16 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 28/28 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed.
### Notes
- `scripts/analyze_per_article_style.py`: new offline generator for `per_article_style_profile_v1` batches with fail-closed pending output.
- `scripts/journal_style_runtime.py`: added the generator to release integrity tracking.
- `tests/run_downstream_consumable_fixtures.py`: added generator success and pending-material regression fixtures.
- `config/release-manifest.json`: refreshed integrity hashes for protected config/scripts.
- Rollback: delete `scripts/analyze_per_article_style.py`, remove it from `MANIFEST_TRACKED_SCRIPTS`, revert the fixture additions, and rebuild `config/release-manifest.json`.

## 2026-06-24 - Task: journal-style Phase 2 batch 2 aggregation locks
### What was done
- Added an offline aggregation generator that consumes gate-passing per-article profiles and emits five required downstream artifacts in `journal-style-aggregation-bundle.json`.
- Made the aggregation gate require all five named artifacts: constraints lock, format convention profile, argument preference profile, reference ecology lock, and polish consumption pack.
- Added regression coverage for missing named artifacts and successful generation of the full named bundle.
### Testing
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 18/18 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 28/28 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- `python3 -m json.tool config/stage-gates.json`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed.
### Notes
- `scripts/aggregate_journal_style.py`: new offline generator for five named aggregation artifacts and an embedded polish consumption payload.
- `scripts/run_stage_gates.py`: aggregation gate now fails closed when any required named artifact is absent.
- `scripts/journal_style_runtime.py`: added the aggregation generator to release integrity tracking.
- `config/stage-gates.json`: declared `required_named_artifacts` for the aggregation gate.
- `tests/run_downstream_consumable_fixtures.py`: added missing-artifact and aggregation-generator fixtures.
- `tests/run_state_machine_fixtures.py`: updated full-chain synthetic aggregation fixtures to include all required artifacts.
- `config/release-manifest.json`: refreshed integrity hashes for protected config/scripts.
- Rollback: delete `scripts/aggregate_journal_style.py`, remove it from `MANIFEST_TRACKED_SCRIPTS`, revert aggregation gate/config/test changes, and rebuild `config/release-manifest.json`.

## 2026-06-24 - Task: journal-style Phase 2 batch 3 polish consumption pack export
### What was done
- Added a thin export step that writes the `journal-polish-consumption-pack` payload from the aggregation bundle into `05-handoff/journal-polish-consumption-pack.json`.
- Added top-level `confidence` and `conclusion_strength` to the `journal_style_profile_v1` consumption pack contract.
- Aligned the article-polish handoff documentation with the nested `constraints` structure and documented `length_band.advisory_only` as display-only.
### Testing
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 19/19 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 28/28 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- `python3 -m json.tool config/journal-polish-consumption-pack-schema.json`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed.
### Notes
- `scripts/export_polish_consumption_pack.py`: new exporter that verifies aggregation and provenance gates around the consumption pack.
- `scripts/journal_style_runtime.py`: added the exporter to release integrity tracking.
- `config/journal-polish-consumption-pack-schema.json`: added required top-level confidence fields.
- `references/handoff-to-wenzhang-runse.md`: replaced the old flat example with the real nested `journal_style_profile_v1` structure.
- `references/output-schema.md`: documented downstream confidence fields and advisory-only length semantics.
- `tests/run_downstream_consumable_fixtures.py`: added the consumption-pack export fixture.
- `config/release-manifest.json`: refreshed integrity hashes for protected config/scripts.
- Rollback: delete `scripts/export_polish_consumption_pack.py`, remove it from `MANIFEST_TRACKED_SCRIPTS`, revert schema/doc/test changes, and rebuild `config/release-manifest.json`.

## 2026-06-24 - Task: journal-style Phase 2 batch 4 calibrated scoring scripts
### What was done
- Added a calibrated fit scoring model generator that consumes the aggregation bundle and writes `journal-fit-scoring-model.json` with replay distribution, dimensions, and dimension rationales.
- Added a user manuscript scoring report generator that keeps user results in `submission-fit-score.md`, separate from the model body.
- Tightened the scoring gate so every scoring dimension must include a rationale and added regressions for missing rationales and manuscript-score report generation.
### Testing
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 21/21 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 28/28 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- `python3 -m json.tool config/scoring-model-schema.json`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed.
### Notes
- `scripts/calibrate_fit_scoring.py`: new calibrated scoring model generator.
- `scripts/score_user_manuscript.py`: new user manuscript fit-score report generator.
- `scripts/run_stage_gates.py`: scoring calibration gate now requires `dimensions[].rationale`.
- `scripts/journal_style_runtime.py`: added both scoring scripts to release integrity tracking.
- `config/scoring-model-schema.json`: documented dimension rationale in the model schema.
- `references/scoring-model-protocol.md`: documented model/result separation and rationale requirements.
- `tests/run_downstream_consumable_fixtures.py`: added missing-rationale and calibrated-score workflow fixtures.
- `config/release-manifest.json`: refreshed integrity hashes for protected config/scripts.
- Rollback: delete `scripts/calibrate_fit_scoring.py` and `scripts/score_user_manuscript.py`, remove them from `MANIFEST_TRACKED_SCRIPTS`, revert scoring gate/schema/doc/test changes, and rebuild `config/release-manifest.json`.

## 2026-06-24 - Task: journal-style Phase 2 batch 5 article-polish consumption bridge
### What was done
- Connected the downstream bridge by updating `文章润色` to consume nested `journal_style_profile_v1.constraints` from the journal-style consumption pack.
- Preserved the user-approved word-count policy: `length_band` remains advisory-only and does not override ScholarPolish's existing 13000-18000 display recommendation or become a gate.
- Passed non-word-count journal constraints such as section hierarchy, keyword range, notes convention, argument rhythm, title style, and reference constraints into ScholarPolish's constraints lock and final quality bridge.
### Testing
- In `/Users/a13497/.codex/skills/文章润色`, `python3 tests/run-fixtures.py --all`: passed.
- In `/Users/a13497/.codex/skills/文章润色`, `python3 scripts/run-local-gate.py --pre-review`: passed.
- In `/Users/a13497/.codex/skills/文章润色`, `python3 scripts/verify-skill-structure.py --target article-polish`: passed.
- In `/Users/a13497/.codex/skills/文章润色`, `python3 -m py_compile scripts/consume-journal-style-profile.py scripts/assert-journal-style-consumed.py tests/run-fixtures.py`: passed.
### Notes
- `/Users/a13497/.codex/skills/文章润色/scripts/consume-journal-style-profile.py`: reads nested journal-style constraints and writes profile-driven constraints into ScholarPolish outputs.
- `/Users/a13497/.codex/skills/文章润色/scripts/assert-journal-style-consumed.py`: verifies full-text journal profiles produce non-word-count constraints and do not turn length into a gate.
- `/Users/a13497/.codex/skills/文章润色/config/journal-style-consumption-policy.json`: recognizes `mu_fulltext_core_pack` as full-text evidence scope.
- `/Users/a13497/.codex/skills/文章润色/templates/journal-style-constraints-lock-template.json`: documents profile constraints and advisory-only length band.
- `/Users/a13497/.codex/skills/文章润色/tests/run-fixtures.py`: adds fixture coverage for real constraints consumption.
- `/Users/a13497/.codex/skills/文章润色/progress.md`: records the cross-skill consumption bridge change.
- Rollback: revert the listed `文章润色` files to their previous version and rerun its fixture suite; no journal-style source files need rollback for this bridge entry.

## 2026-06-24 - Task: journal-style Phase 2 implementation review handoff
### What was done
- Re-ran the local Phase 2 verification set after batches 0-5 and confirmed the journal-style downstream-consumable path, state machine path, release manifest, and article-polish consumption bridge are locally green.
- Created a Claude implementation-review prompt for an independent Phase 2 review, scoped to offline source/schema/fixture inspection and local tests only.
- Fixed the review output target at `/Users/a13497/.codex/skills/journal-style/.handoff/claude/2026-06-24-phase2-implementation-review.md`.
### Testing
- In `/Users/a13497/.codex/skills/journal-style`, `python3 tests/run_downstream_consumable_fixtures.py`: passed, 21/21 fixtures.
- In `/Users/a13497/.codex/skills/journal-style`, `python3 tests/run_state_machine_fixtures.py`: passed, 28/28 fixtures.
- In `/Users/a13497/.codex/skills/journal-style`, `python3 scripts/run_smoke_tests.py`: passed.
- In `/Users/a13497/.codex/skills/journal-style`, JSON validation for updated workflow/gate/schema/manifest files: passed.
- In `/Users/a13497/.codex/skills/journal-style`, `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- In `/Users/a13497/.codex/skills/journal-style`, `python3 scripts/build_release_manifest.py --check`: passed, manifest current.
- In `/Users/a13497/.codex/skills/文章润色`, `python3 tests/run-fixtures.py --all`: passed.
- In `/Users/a13497/.codex/skills/文章润色`, `python3 scripts/run-local-gate.py --pre-review`: passed.
- In `/Users/a13497/.codex/skills/文章润色`, `python3 scripts/verify-skill-structure.py --target article-polish`: passed.
- Checked `/Users/a13497/.codex/skills/journal-style` and `/Users/a13497/.codex/skills/文章润色` for `__pycache__` / `.pyc` residue: none found.
### Notes
- `/Users/a13497/.codex/skills/journal-style/.handoff/claude/2026-06-24-phase2-implementation-review-prompt.md`: added the Claude Phase 2 implementation-review prompt with the required review scope, files, tests, and output path.
- `/Users/a13497/.codex/skills/journal-style/progress.md`: records this review-handoff step and the verification evidence.
- Rollback: delete `/Users/a13497/.codex/skills/journal-style/.handoff/claude/2026-06-24-phase2-implementation-review-prompt.md` and remove this progress entry; no production code needs rollback for this handoff-only step.

## 2026-06-24 - Task: journal-style Phase 2 batch 4 P1 scoring calibration fixes
### What was done
- Replaced the placeholder scoring distribution with real replay scoring over `per_article_style_profile_v1` entries, so `published_score_distribution` is now derived from `replay_scores[]`.
- Added `scoring_constraints` from the aggregation bundle to the scoring model and made user manuscript scoring consume the target journal section, keyword, and reference bands instead of generic hard-coded intervals.
- Tightened the scoring gate so calibrated models must declare `calibration.source=per_article_profile_replay`, include target journal scoring constraints, include replay scores, and have distribution values that match replay scores.
- Added regression coverage for the previous failure mode: constant placeholder distributions now fail closed, and user manuscript scoring must show and apply target journal bands.
### Testing
- In `/Users/a13497/.codex/skills/journal-style`, `python3 tests/run_downstream_consumable_fixtures.py`: passed, 23/23 fixtures.
- In `/Users/a13497/.codex/skills/journal-style`, `python3 tests/run_state_machine_fixtures.py`: passed, 28/28 fixtures.
- In `/Users/a13497/.codex/skills/journal-style`, `python3 scripts/run_smoke_tests.py`: passed.
- In `/Users/a13497/.codex/skills/journal-style`, JSON validation for workflow/gate/schema/manifest files: passed.
- In `/Users/a13497/.codex/skills/journal-style`, `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- In `/Users/a13497/.codex/skills/journal-style`, `python3 scripts/build_release_manifest.py --check`: passed, manifest current.
- In `/Users/a13497/.codex/skills/journal-style`, `git diff --check`: passed.
- In `/Users/a13497/.codex/skills/文章润色`, `python3 tests/run-fixtures.py --all`: passed.
- In `/Users/a13497/.codex/skills/文章润色`, `python3 scripts/verify-skill-structure.py --target article-polish`: passed.
- In `/Users/a13497/.codex/skills/文章润色`, `python3 scripts/run-local-gate.py --pre-review`: failed with `pre-review mode expected Claude review to be absent or unpublished`; this is a workflow-state result because a Claude review is now present, not a fixture or structure regression from this journal-style scoring fix.
- Checked `/Users/a13497/.codex/skills/journal-style` and `/Users/a13497/.codex/skills/文章润色` for `__pycache__` / `.pyc` residue: none found.
### Notes
- `/Users/a13497/.codex/skills/journal-style/scripts/calibrate_fit_scoring.py`: now loads the per-article profile batch, computes per-article replay scores, stores `replay_scores[]`, and derives the published score distribution from those replay scores.
- `/Users/a13497/.codex/skills/journal-style/scripts/score_user_manuscript.py`: now reads `scoring_constraints` from the calibrated model and applies target journal bands in manuscript scoring.
- `/Users/a13497/.codex/skills/journal-style/scripts/run_stage_gates.py`: scoring calibration gate now rejects missing replay scores, missing target journal bands, wrong calibration source, and distributions that do not match replay scores.
- `/Users/a13497/.codex/skills/journal-style/config/scoring-model-schema.json`: records `scoring_constraints`, `replay_scores[]`, and `published_score_distribution.source=replay_scores` in the model contract.
- `/Users/a13497/.codex/skills/journal-style/references/scoring-model-protocol.md`: documents that calibrated distributions must come from replay scores and that manuscript scoring must consume target journal constraints.
- `/Users/a13497/.codex/skills/journal-style/tests/run_downstream_consumable_fixtures.py`: adds the constant-distribution must-fail fixture and target-journal-band scoring fixture.
- `/Users/a13497/.codex/skills/journal-style/tests/run_state_machine_fixtures.py`: updates the full-mode scoring fixture to the stricter calibrated model contract.
- `/Users/a13497/.codex/skills/journal-style/config/release-manifest.json`: refreshed integrity hashes after the scoring fix.
- `/Users/a13497/.codex/skills/journal-style/progress.md`: records this P1 repair and verification evidence.
- Rollback: revert the files listed in this entry to the pre-repair state and rebuild `config/release-manifest.json`; rerun downstream and state-machine fixtures to confirm the previous baseline if rollback is needed.

## 2026-06-24 - Task: journal-style Phase 2 P1 scoring fix review handoff
### What was done
- Created a targeted Claude review prompt for the Phase 2 P1 scoring repair.
- Scoped the review to the two previously requested changes: replay-derived scoring distribution and target-journal-band manuscript scoring.
- Fixed the review output target at `/Users/a13497/.codex/skills/journal-style/.handoff/claude/2026-06-24-phase2-p1-scoring-fix-review.md`.
### Testing
- This is a handoff-only step after the P1 repair verification recorded above.
- In `/Users/a13497/.codex/skills/journal-style`, `python3 scripts/build_release_manifest.py --check`: passed, manifest current.
- Checked `/Users/a13497/.codex/skills/journal-style` and `/Users/a13497/.codex/skills/文章润色` for `__pycache__` / `.pyc` residue after the repair: none found.
### Notes
- `/Users/a13497/.codex/skills/journal-style/.handoff/claude/2026-06-24-phase2-p1-scoring-fix-review-prompt.md`: added the targeted Claude review prompt and output path.
- `/Users/a13497/.codex/skills/journal-style/progress.md`: records this review-handoff step.
- Rollback: delete `/Users/a13497/.codex/skills/journal-style/.handoff/claude/2026-06-24-phase2-p1-scoring-fix-review-prompt.md` and remove this progress entry; no production code needs rollback for this handoff-only step.

## 2026-06-24 - Task: journal-style Phase 2 release-prep closure
### What was done
- Confirmed Claude's targeted review for the Phase 2 P1 scoring repair returned `APPROVED_WITH_NOTES`, leaving only nonblocking P2 follow-up notes.
- Ran the final local release-prep verification set for journal-style after the approved repair.
- Confirmed the repository remote and existing tag state: remote `origin` is configured, latest visible version tag is `v0.1.9`, and current `VERSION` remains `0.1.9`; a new release must choose a new version/tag before commit/tag/push.
- Did not commit, tag, push, sync runtime, connect to servers, or run any real CNKI/WoS/Zotero/PDF/MinerU/RAG/Wenheng task.
### Testing
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 23/23 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 28/28 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 scripts/validate_readme.py`: passed.
- `python3 scripts/validate_public_introduction.py --mode final`: passed.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- JSON validation for workflow/gate/schema/manifest files: passed.
- `python3 scripts/build_release_manifest.py --check`: passed, manifest current.
- `git diff --check`: passed.
- Checked `/Users/a13497/.codex/skills/journal-style` for `__pycache__` / `.pyc` residue: none found.
### Notes
- `/Users/a13497/.codex/skills/journal-style/progress.md`: records the final release-prep verification and release boundary.
- Rollback: remove this progress entry if this release-prep record should be withdrawn; no production code was changed by this closure entry.

## 2026-06-24 - Task: journal-style 0.1.10 release publication
### What was done
- Published the reviewed Phase 2 downstream-consumable journal constraints work as `0.1.10`.
- Committed the reviewed code, schema, protocol, fixture, handoff, progress, and version metadata changes at `bf479077c7da770f48bcb856ffef723820aa54ad`.
- Re-signed `config/release-manifest.json` from a clean reviewed HEAD and committed it at `8c8407d7d624c1afbb2ae40df81f6c137be5dbd1`.
- Created and pushed annotated tag `v0.1.10`, pointing to `8c8407d7d624c1afbb2ae40df81f6c137be5dbd1`.
- Pushed `main` and `v0.1.10` to `origin`; no runtime sync, server connection, CNKI/WoS/Zotero/PDF/MinerU/RAG, or real Wenheng task was run.
### Testing
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 23/23 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 28/28 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 scripts/validate_readme.py`: passed.
- `python3 scripts/validate_public_introduction.py --mode final`: passed.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- JSON validation for `config/*.json` and `templates/*.json`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed, manifest current.
- `git diff --check`: passed.
- Checked `/Users/a13497/.codex/skills/journal-style` for `__pycache__` / `.pyc` residue after validation cleanup: none found.
### Notes
- `/Users/a13497/.codex/skills/journal-style/progress.md`: appended this post-tag release publication record only; the `v0.1.10` tag remains on the release manifest commit and is not moved.
- Rollback: revert the post-tag progress-record commit if only this audit note should be withdrawn. To roll back the published release itself, do not move `v0.1.10`; publish a corrective commit and follow-up version/tag or explicitly delete the remote tag under release-owner approval.
