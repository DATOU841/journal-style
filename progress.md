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

## 2026-06-24 - Task: Wenheng native execution hard gate for 0.1.11
### What was done
- Prepared `0.1.11` to close the execution bypass between the Wenheng startup gate and the local task runner.
- Made `journal-style-startup.py` write a task-local `00-intake/wenheng-native-binding.json` receipt after B02/F06/H08 validation, and write `00-intake/wenheng-intake-request.json` when no B02 task is available.
- Made `build_task_skeleton.py` and `journal_style_runner.py` fail closed by default unless the task has a validated Wenheng native binding receipt; legacy/debug execution now requires an explicit flag or environment variable and cannot become production evidence.
- Added `task_folder`, `target_skill`, `source_run_id`, and `h08_evidence_stub` to the required native binding payload so later B02 timeline, H08 evidence, archive, and C03 source-lock integration have stable task identity.
- Added the Wenheng startup/binding scripts to release-manifest integrity tracking.
### Testing
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 23/23 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 35/35 fixtures after adding Wenheng native hard-gate fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 scripts/validate_readme.py`: passed.
- `python3 scripts/validate_public_introduction.py --mode final`: passed.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- JSON validation for `config/*.json` and `templates/*.json`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed, manifest current.
- `git diff --check`: passed.
### Notes
- `/Users/a13497/.codex/skills/journal-style/scripts/wenheng_native.py`: added binding receipt, intake request, production/native validation, and required task packet fields.
- `/Users/a13497/.codex/skills/journal-style/scripts/journal-style-startup.py`: writes binding receipts on validated startup and intake requests on missing B02 binding.
- `/Users/a13497/.codex/skills/journal-style/scripts/build_task_skeleton.py`: requires validated native binding by default, with explicit offline legacy/debug escape.
- `/Users/a13497/.codex/skills/journal-style/scripts/journal_style_runner.py`: requires validated native binding by default before release integrity and workflow evaluation.
- `/Users/a13497/.codex/skills/journal-style/scripts/journal_style_runtime.py`: adds the Wenheng native entry scripts to release integrity tracking.
- `/Users/a13497/.codex/skills/journal-style/tests/run_state_machine_fixtures.py`: adds must-fail and success coverage for native binding, skeleton, runner, and intake request behavior.
- `/Users/a13497/.codex/skills/journal-style/docs/wenheng-native-protocol.md`: documents the binding receipt and hard-gate execution rule.
- `/Users/a13497/.codex/skills/journal-style/SKILL.md`: surfaces the production/native binding receipt rule in the skill entrypoint.
- `/Users/a13497/.codex/skills/journal-style/VERSION`: bumps the release target to `0.1.11`.
- `/Users/a13497/.codex/skills/journal-style/README.md`: updates version metadata to `0.1.11`.
- `/Users/a13497/.codex/skills/journal-style/docs/public-introduction.zh.md`: updates version metadata to `0.1.11`.
- `/Users/a13497/.codex/skills/journal-style/config/release-manifest.json`: refreshed integrity hashes after adding protected scripts.
- Rollback: revert the listed files and rebuild `config/release-manifest.json`; publish rollback as a new corrective version rather than moving existing release tags.

## 2026-06-24 - Task: journal-style 0.1.11 release publication
### What was done
- Published the Wenheng native execution hard gate as `0.1.11`.
- Committed the hard-gate code, docs, tests, progress, and version metadata at `b72cac0eb542f9387c7a367498b65cca95b37726`.
- Re-signed `config/release-manifest.json` from a clean reviewed HEAD and committed it at `8fed3a6d757913068d19215e4f7126a01eb2f7da`.
- Created and pushed annotated tag `v0.1.11`, pointing to `8fed3a6d757913068d19215e4f7126a01eb2f7da`.
- Pushed `main` and `v0.1.11` to `origin`; no runtime sync, server connection, CNKI/WoS/Zotero/PDF/MinerU/RAG, C03 writeback, or real Wenheng task was run.
### Testing
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 23/23 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 35/35 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 scripts/validate_readme.py`: passed.
- `python3 scripts/validate_public_introduction.py --mode final`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed, manifest current.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- JSON validation for `config/*.json` and `templates/*.json`: passed.
- `git diff --check`: passed.
- Checked `/Users/a13497/.codex/skills/journal-style` for `__pycache__` / `.pyc` residue after validation cleanup: none found.
### Notes
- `/Users/a13497/.codex/skills/journal-style/progress.md`: appended this post-tag release publication record only; the `v0.1.11` tag remains on the release manifest commit and is not moved.
- Rollback: revert the post-tag progress-record commit if only this audit note should be withdrawn. To roll back the published release itself, do not move `v0.1.11`; publish a corrective commit and follow-up version/tag or explicitly delete the remote tag under release-owner approval.

## 2026-06-25 - Task: journal-style 0.1.12 sidecar adaptation planning
### What was done
- Completed development-prep planning for adapting journal-style to `检索入库 0.2.11` post-2.5 sidecar artifacts.
- Wrote a minimal implementation plan covering optional sidecar discovery, safe metadata-only consumption, fallback to legacy handoff files, verification fixtures, rollback, and explicit non-goals.
- Kept the plan within planning scope: no source code changes, no formal journal-style task, no CNKI/WoS/Zotero/PDF/MinerU/RAG/server operation, no commit, no tag, no push, and no release.
### Testing
- Confirmed the plan file first line is `STATUS: PLAN_READY`.
- Confirmed the plan file has the required sections for files to change, validation method, rollback method, and non-goals.
- No runtime tests were run because this was a development-prep planning task only.
### Notes
- `/Users/a13497/.codex/skills/journal-style/.handoff/claude/0.1.12-journal-style-sidecar-adaptation-plan.md`: added the sidecar adaptation development plan.
- `/Users/a13497/.codex/skills/journal-style/progress.md`: appended this planning record.
- Rollback: delete `/Users/a13497/.codex/skills/journal-style/.handoff/claude/0.1.12-journal-style-sidecar-adaptation-plan.md` and remove this progress entry; no source code, config, schema, runtime, server bundle, tag, or release state needs rollback.

## 2026-06-25 - Task: journal-style 0.1.12 sidecar adaptation implementation
### What was done
- Implemented best-effort journal-style consumption of `检索入库 0.2.11` sidecar artifacts with metadata-only safety, optional discovery, and legacy fallback behavior.
- Added safe sidecar manifest generation and a planning-only RAG seed pack so journal-style can read source roles, bibliography scope, fulltext pointers, and gaps without opening `full.md` bodies.
- Wired sidecar context into core library selection as a small metadata boost only, kept the 25%-40% gate intact, and preserved the no-fulltext/no-RAG boundary.
- Tightened gate handling so missing sidecar inputs pass cleanly, forbidden payloads still fail closed, and count-style summary keys are not misclassified as content leaks.
- Updated the skill docs, release metadata, and validation fixtures so the sidecar path is explicit and locally testable.
### Testing
- `python3 tests/run_sidecar_adaptation_fixtures.py`: passed, 6/6 fixtures.
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 23/23 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 35/35 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 scripts/validate_readme.py`: passed.
- `python3 scripts/validate_public_introduction.py --mode final`: passed.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- JSON validation for `config/*.json` and `templates/*.json`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed, manifest current.
- `git diff --check`: passed.
- Checked `/Users/a13497/.codex/skills/journal-style` for `__pycache__` / `.pyc` residue after validation cleanup: none found.
### Notes
- `/Users/a13497/.codex/skills/journal-style/README.md`: bumped public version metadata to `0.1.12`.
- `/Users/a13497/.codex/skills/journal-style/SKILL.md`: documented sidecar best-effort capability and clarified current capability scope.
- `/Users/a13497/.codex/skills/journal-style/VERSION`: set the skill version to `0.1.12`.
- `/Users/a13497/.codex/skills/journal-style/config/field-policy.json`: added sidecar leak-guard keys for fulltext, body, vector, and credential-like payloads.
- `/Users/a13497/.codex/skills/journal-style/config/release-manifest.json`: re-signed integrity hashes after the implementation changes.
- `/Users/a13497/.codex/skills/journal-style/config/stage-gates.json`: added the `jiansuo-sidecar-safety` gate configuration.
- `/Users/a13497/.codex/skills/journal-style/docs/public-introduction.zh.md`: aligned the public intro version metadata with `0.1.12`.
- `/Users/a13497/.codex/skills/journal-style/docs/wenheng-native-protocol.md`: recorded the sidecar-aware Wenheng boundary wording.
- `/Users/a13497/.codex/skills/journal-style/references/core-library-selection-protocol.md`: described how sidecar context may boost metadata-only selection without changing the hard gate.
- `/Users/a13497/.codex/skills/journal-style/references/evidence-rules.md`: added evidence-layer guidance for optional sidecar inputs.
- `/Users/a13497/.codex/skills/journal-style/references/fulltext-article-pattern-mining-protocol.md`: clarified that sidecar pointers are not fulltext body consumption.
- `/Users/a13497/.codex/skills/journal-style/references/handoff-from-jiansuo-ruku.md`: added the sidecar-adaptation handoff expectations for incoming assets.
- `/Users/a13497/.codex/skills/journal-style/references/handoff-to-jiansuo-ruku.md`: updated the return path so gaps and role evidence stay declarative.
- `/Users/a13497/.codex/skills/journal-style/references/output-schema.md`: moved sidecar-derived outputs into an optional enhancement subsection.
- `/Users/a13497/.codex/skills/journal-style/references/secret-boundary-protocol.md`: aligned the boundary language with the sidecar-safe intake rule.
- `/Users/a13497/.codex/skills/journal-style/references/jiansuo-sidecar-consumption-protocol.md`: added the new sidecar consumption protocol.
- `/Users/a13497/.codex/skills/journal-style/scripts/build_material_intake_manifest.py`: marked sidecar assets as optional intake inputs and kept them out of hard gaps.
- `/Users/a13497/.codex/skills/journal-style/scripts/build_jiansuo_sidecar_manifest.py`: generated the safe metadata-only sidecar manifest and derived summary files.
- `/Users/a13497/.codex/skills/journal-style/scripts/build_journal_style_rag_seed_plan.py`: generated a planning-only RAG seed pack with `executed=false`.
- `/Users/a13497/.codex/skills/journal-style/scripts/gate_runner.py`: allowed the optional sidecar gate to pass cleanly when the manifest is absent.
- `/Users/a13497/.codex/skills/journal-style/scripts/journal_style_runtime.py`: registered the new sidecar scripts and gate ID for release tracking.
- `/Users/a13497/.codex/skills/journal-style/scripts/run_stage_gates.py`: added the `jiansuo-sidecar-safety` gate and exempted count namespaces from false-positive leak matches.
- `/Users/a13497/.codex/skills/journal-style/scripts/select_core_library.py`: accepted optional sidecar context, added safe role evidence, and created the output directory before writing.
- `/Users/a13497/.codex/skills/journal-style/tests/run_sidecar_adaptation_fixtures.py`: added synthetic fixtures for missing sidecar, safe manifest, leak rejection, seed planning, core-library boosting, and bibliography scope coverage.
- `/Users/a13497/.codex/skills/journal-style/.handoff/claude/0.1.12-journal-style-sidecar-adaptation-plan.md`: retained the development plan file for downstream review.
- Rollback: revert the files above, delete the sidecar plan file if needed, and rebuild `config/release-manifest.json` afterward; do not move tags or publish anything from this working tree.

## 2026-06-28 - Task: journal-style 0.1.13 review memory overlay release prep
### What was done
- Upgraded the journal-style version line and public-facing docs to `0.1.13` because `0.1.12` is already published and cannot be reused for new overlay capability.
- Added a dedicated review-memory fixture suite so the Obsidian workbench overlay path is verified independently from the general smoke path.
- Extended the smoke path and manifest tracking to cover the new `journal_review_memory_v1` compiler, protocol, and export script.
### Testing
- `python3 tests/run_review_memory_fixtures.py`: passed, 5/5 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 23/23 fixtures.
- `python3 tests/run_state_machine_fixtures.py`: passed, 35/35 fixtures.
- `python3 -m py_compile scripts/*.py tests/*.py`: passed.
- `python3 scripts/validate_readme.py`: passed.
- `python3 scripts/validate_public_introduction.py --mode final`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed, manifest current.
- `git diff --check`: passed.
### Notes
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/VERSION`: bumped to `0.1.13`.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/README.md`: aligned public version metadata with `0.1.13`.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/docs/public-introduction.zh.md`: aligned public version metadata with `0.1.13` and added the review-memory overlay mention.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/tests/run_review_memory_fixtures.py`: new isolated fixture suite for review-memory export boundaries.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/scripts/run_smoke_tests.py`: now exercises the review-memory fixture suite during smoke.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/scripts/journal_style_runtime.py`: now tracks the review-memory schema/script in release integrity.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/config/release-manifest.json`: will be re-signed after validation.
- Rollback: restore the files listed above to the previous release state and remove this progress entry; if the release is already tagged, publish a corrective version rather than moving the tag.

## 2026-07-04 - Task: Wenheng native read/write auth and retrieval handoff consumption fix
### What was done
- Updated journal-style native startup to read B02 task packets with `WENHENG_BACKEND_READ_API_KEY` and keep H08 LearningEvent writes on `WENHENG_BACKEND_API_KEY`.
- Aligned task packet parsing with the current Wenheng backend shape by accepting direct task payloads, `routing.target_skill`, and `evidence_path` as the H08 evidence stub source while still fail-closing when those resolved fields are absent.
- Re-signed `config/release-manifest.json` after the native adapter change so runner integrity protection remains load-bearing on top of the existing `0.1.13` release metadata.
- Verified a real journal-style staging task could bind through B02/F06 and consume the 检索入库 Stage2 handoff through the runner's live step06 gate.
### Testing
- `python3 scripts/build_release_manifest.py`
- `python3 -m py_compile scripts/wenheng_native.py`
- `python3 scripts/run_smoke_tests.py`
- `python3 scripts/journal-style-startup.py --task-dir [LOCAL_TASK_COPY]/journal-style-copy --target-journal 江汉论坛 --wenheng-task-id TASK-1783178581909 --compact`
- `python3 scripts/build_task_skeleton.py --task-dir [LOCAL_TASK_COPY]/journal-style-copy --journal-name 江汉论坛 --task-id TASK-1783178581909 --topic-keywords 艺术,美术,美学,市场,经济 --target-year-range 近三年 --run-mode standard --force`
- `python3 scripts/journal_style_runner.py --task-dir [LOCAL_TASK_COPY]/journal-style-copy --mode standard` (completed through `step06_zotero_pdf_rag`, then stopped at expected `step07_core_library` missing core-library artifact)
### Notes
- Modified files:
  - `scripts/wenheng_native.py`: accepts current backend task packet shape and preserves read/write key split.
  - `docs/wenheng-native-protocol.md`: documents `evidence_path` as the current H08 evidence stub source.
  - `config/release-manifest.json`: re-signed integrity hashes after the native adapter change.
  - `progress.md`: appends this native handoff consumption record.
- Rollback: revert the three modified files and rebuild `config/release-manifest.json` from the restored script bytes. Do not publish a journal-style release from this working tree without a separate review.

## 2026-07-06 - Task: journal-style 0.1.14 single full-depth mode remediation
### What was done
- Documented the C03 non-display root cause and wrote a Claude planning prompt for the single-mode remediation handoff.
- Converted the formal journal-style contract to a single `full` full-depth mode: metadata-only output is now a blocker/intermediate state only, not a delivery standard.
- Removed the formal metadata-terminal state-machine branch, forced legacy `light` / `standard` task mirrors to resolve as `full`, and made new skeletons default to `full`.
- Added regression coverage proving old `standard` state now blocks at the MinerU/mu fulltext pack gate, while a complete full-depth fixture still reaches handoff completion.
- Bumped the skill version to `0.1.14` and re-signed the release manifest after the tracked workflow and script changes.
### Testing
- `python3 -m py_compile scripts/*.py`: passed.
- `python3 tests/run_state_machine_fixtures.py`: passed, 35/35 fixtures.
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 23/23 fixtures.
- `python3 tests/run_sidecar_adaptation_fixtures.py`: passed, 6/6 fixtures.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 scripts/validate_readme.py`: passed.
- `python3 scripts/validate_public_introduction.py --mode final`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed, manifest current.
- `git diff --check`: passed.
### Notes
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/.handoff/claude/0.1.14-single-full-depth-mode-materials.md`: added the C03 symptom, production profile facts, root cause, and acceptance criteria.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/.handoff/claude/0.1.14-single-full-depth-mode-planning-prompt.md`: added the Claude/Fable planning prompt for single full-depth mode.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/README.md`: aligned public version metadata with `0.1.14`.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/SKILL.md`: replaced the three-mode section with the single full-depth formal task contract.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/VERSION`: bumped to `0.1.14`.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/config/release-manifest.json`: re-signed integrity hashes after workflow and script changes.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/config/workflow-states.json`: removed formal `light` / `standard` run modes and deleted the metadata-only terminal step.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/docs/public-introduction.zh.md`: aligned public version metadata with `0.1.14`.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/docs/wenheng-native-protocol.md`: documented single full-depth mode and the fulltext-pack blocker rule.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/references/output-schema.md`: clarified that `METADATA_ONLY_NOT_FULLTEXT_READY` is a blocker label, not delivery success.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/references/run-modes-protocol.md`: rewrote the run-mode protocol as the single full-depth protocol.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/references/stage-gates-protocol.md`: updated the run-mode gate rules to force formal tasks through full-depth.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/scripts/build_task_skeleton.py`: restricted `--run-mode` to `full` and defaulted new tasks to `full`.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/scripts/journal_style_runner.py`: forced all formal and legacy task mode resolution to `full`.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/tests/run_state_machine_fixtures.py`: replaced the metadata-terminal fixture with a legacy-standard-to-fulltext-gate blocker fixture.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/progress.md`: appended this implementation and verification record.
- Rollback: revert this commit or restore the files listed above from `HEAD~1`, delete the two `.handoff/claude/0.1.14-*` files if needed, and rebuild `config/release-manifest.json`; no production C03 data, task data, tag, push, or deployment was changed in this local remediation.

## 2026-07-06 - Task: journal-style 0.1.14 full-depth closure and C03 production profile
### What was done
- Closed the remaining single-mode escape in `wenheng-center-status` validation by rejecting `overall_journal_style=metadata_only` as a formal overall status.
- Added a direct sidecar-to-MinerU fulltext core-pack builder so existing nonempty `检索入库` sidecars can be converted into the required journal-style full-depth input without rerunning CNKI/Zotero/PDF/RAG.
- Extended sidecar manifesting to support recovered external sidecar directories and to report full-mode structure coverage while preserving the no-full-md-body-read safety boundary.
- Split Step6 raw handoff input from the generated gate receipt so reruns no longer overwrite the original `检索入库` handoff evidence.
- Ran the 江汉论坛 real task through the full-depth chain from existing 54 nonempty sidecar fulltexts, generated per-article profiles, aggregation, scoring, handoff, and validated Wenheng status.
- Created the formal Wenheng task `TASK-1783183335633-FULLDEPTH`, copied the completed task evidence into the controlled task folder, completed it through the backend, and wrote the C03 journal profile through `/api/c03/journal-profiles/from-task/TASK-1783183335633-FULLDEPTH`.
- Verified the C03 profile `JP-TASK-1783183335633-FULLDEPTH` is a production profile for 江汉论坛 with `source_run_id=RUN-jianghan-full-depth-20260706`, `FULLTEXT_READY`/`full-depth` tags, and no `metadata-only` or `standard-mode` tag.
- Added the Claude final-review prompt for the full remediation and C03 closure.
### Testing
- `python3 -m py_compile scripts/*.py`: passed.
- `python3 -m py_compile tests/run_state_machine_fixtures.py`: passed.
- Inline `overall_journal_style=metadata_only` validation check: passed with expected exit 1 and `A节修复验收: PASS`.
- `python3 tests/run_state_machine_fixtures.py`: passed, 35/35 fixtures including `standard_task_forced_to_full_blocks_at_step07b` and `full_depth_with_valid_sidecar_completes`.
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 23/23 fixtures.
- `python3 tests/run_sidecar_adaptation_fixtures.py`: passed, 8/8 fixtures including `build_mu_pack_from_sidecar_pass`.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 scripts/validate_readme.py`: passed.
- `python3 scripts/validate_public_introduction.py --mode final`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed, manifest current.
- `git diff --check`: passed.
- Server-side 江汉论坛 full-depth run: 54 sidecar articles converted to a valid mu fulltext core pack, runner reached `completed`, `validate_wenheng_status.py` passed, and C03 GET confirmed the production profile.
### Notes
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/.handoff/claude/0.1.14-single-full-depth-mode-final-review-prompt.md`: added the release-blocking Claude final-review prompt and exact C03 verification requirements.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/.handoff/droid/0.1.14-single-full-depth-mode-plan.md`: retained the Droid execution plan used for this run.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/config/workflow-states.json`: separated Step6 handoff input from the generated gate receipt and kept the state machine on the full-depth path.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/config/release-manifest.json`: kept the tracked script/config hashes current after source changes.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/references/jiansuo-sidecar-consumption-protocol.md`: corrected the old fallback wording so missing sidecars now block full-depth completion instead of allowing metadata-only delivery.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/references/output-schema.md`: clarified full-depth handoff and blocker labels.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/references/stage-gates-protocol.md`: documented the full-depth gate input/receipt behavior and blocker semantics.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/scripts/aggregate_journal_style.py`: exported `FULLTEXT_READY` and fulltext-layer status into the downstream consumption pack.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/scripts/build_jiansuo_sidecar_manifest.py`: added external sidecar directory support and full-mode structure coverage reporting without opening `full.md` bodies.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/scripts/build_material_intake_manifest.py`: registered the new Step6 raw handoff input path.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/scripts/build_mu_fulltext_core_pack_from_sidecar.py`: added the converter from existing `检索入库` fulltext sidecars to `mu-fulltext-core-pack.json`.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/scripts/journal_style_runtime.py`: added the new converter script to release integrity tracking.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/scripts/validate_wenheng_status.py`: rejected `overall_journal_style=metadata_only` as a formal overall status.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/tests/run_sidecar_adaptation_fixtures.py`: added sidecar structure counting and sidecar-to-mu-pack regression coverage.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/tests/run_state_machine_fixtures.py`: added the full-depth completion and legacy-standard blocker fixtures.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/progress.md`: appended this closure, verification, and C03 writeback record.
- Server task evidence path: `/opt/wenheng-control/repo/data/tasks/TASK-1783183335633-FULLDEPTH`.
- Server runtime task path: `/home/ubuntu/wenheng-runtime/jianghan-forum-journal-style-20260704`.
- Rollback: revert or reset the local source changes before commit, rebuild `config/release-manifest.json`, and remove this progress entry if this local candidate is abandoned. The C03 writeback is production data; rollback must be done through the Wenheng backend by retiring or superseding `JP-TASK-1783183335633-FULLDEPTH`, not by editing task artifacts or database rows by hand.

## 2026-07-06 - Task: journal-style 0.1.14 BLOCK-01 sidecar manifest reference coverage fix
### What was done
- Resolved the final-review blocker where the 江汉论坛 sidecar manifest showed `reference_list` coverage as 1/54 while the later mu fulltext pack had 54/54.
- Added a structure-only summary output from the sidecar-to-mu-pack builder so reference coverage derived during fulltext pack construction can be reviewed without embedding fulltext bodies in the sidecar manifest.
- Updated the sidecar manifest builder to consume that structure summary as a count-only overlay, preserving `full_md_files_opened=0` while reconciling `section_tree` / `paragraph_sequence` / `reference_list` coverage.
- Added a regression fixture proving a sidecar with missing manifest-level `reference_list` can be reconciled through the structure summary without opening `full.md` in manifest generation.
- Rebuilt the 江汉论坛 runtime manifest and formal task evidence so both now show 54/54 full-mode structure readiness and `full_md_files_opened=0`.
### Testing
- `python3 -m py_compile scripts/*.py`: passed.
- `python3 tests/run_state_machine_fixtures.py`: passed, 35/35 fixtures.
- `python3 tests/run_downstream_consumable_fixtures.py`: passed, 23/23 fixtures.
- `python3 tests/run_sidecar_adaptation_fixtures.py`: passed, 9/9 fixtures including `structure_summary_reconciles_manifest_without_fullmd_read`.
- `python3 scripts/run_smoke_tests.py`: passed.
- `python3 scripts/validate_readme.py`: passed.
- `python3 scripts/validate_public_introduction.py --mode final`: passed.
- `python3 scripts/build_release_manifest.py --check`: passed, manifest current.
- `git diff --check`: passed.
- Server F-section verification: 江汉论坛 manifest `item_count=54`, `ready_structure_count=54`, `reference_list.count=54`, `full_md_files_opened=0`; `mu-fulltext-pack` PASS with 54 ready articles; runner `current_step=completed`; provenance gate PASS; `validate_wenheng_status.py` returned `ok=true`.
### Notes
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/scripts/build_mu_fulltext_core_pack_from_sidecar.py`: now writes `mu-fulltext-structure-summary.json`, a structure-count-only companion file with no fulltext body.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/scripts/build_jiansuo_sidecar_manifest.py`: now reads the structure summary overlay to reconcile full-mode structure coverage without opening `full.md`.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/tests/run_sidecar_adaptation_fixtures.py`: added the 9th fixture for reference-list coverage reconciliation through a structure summary.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/config/release-manifest.json`: re-signed tracked script hashes after the blocker fix.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/progress.md`: appended this blocker-resolution record.
- Server runtime updated files: `/home/ubuntu/wenheng-runtime/journal-style-skill-0.1.14-runtime/scripts/build_mu_fulltext_core_pack_from_sidecar.py`, `/home/ubuntu/wenheng-runtime/journal-style-skill-0.1.14-runtime/scripts/build_jiansuo_sidecar_manifest.py`, and `/home/ubuntu/wenheng-runtime/journal-style-skill-0.1.14-runtime/config/release-manifest.json`.
- Server evidence updated files: `/home/ubuntu/wenheng-runtime/jianghan-forum-journal-style-20260704/00-intake/jiansuo-sidecar-manifest.json`, `/home/ubuntu/wenheng-runtime/jianghan-forum-journal-style-20260704/03-analysis/fulltext-layer/mu-fulltext-core-pack.json`, `/home/ubuntu/wenheng-runtime/jianghan-forum-journal-style-20260704/03-analysis/fulltext-layer/mu-fulltext-structure-summary.json`, plus the same evidence copies under `/opt/wenheng-control/repo/data/tasks/TASK-1783183335633-FULLDEPTH`.
- Rollback: restore the two script files and `config/release-manifest.json` from the previous candidate, rerun `python3 scripts/build_release_manifest.py`, and restore the pre-fix server manifest/core-pack evidence from backup or by rerunning the previous builder. If the production C03 profile must be rolled back, retire or supersede `JP-TASK-1783183335633-FULLDEPTH` through Wenheng backend controls rather than editing database rows manually.

## 2026-07-06 - Task: journal-style 0.1.14 formal Fable review prompt
### What was done
- Created a separate formal Fable/Claude review prompt for `journal-style 0.1.14` so the next reviewer does not mistake Codex internal precheck files for an official release review.
- Explicitly marked the existing `final-review.md` and `rereview.md` files as background-only internal prechecks and required the formal reviewer to rerun code, local gates, server evidence checks, and C03 verification independently.
- Included the current release boundary: no commit, tag, push, formal skill sync, server runtime final sync, or deployment may happen until the formal review returns `STATUS: PASS` and the user separately authorizes the release chain.
### Testing
- `sed -n '1,80p' .handoff/claude/0.1.14-single-full-depth-mode-formal-fable-review-prompt.md`: confirmed the formal prompt first section states the internal reports are not PASS evidence and names the required output report path.
- `git status --short .handoff/claude/0.1.14-single-full-depth-mode-formal-fable-review-prompt.md progress.md`: confirmed the new prompt and this progress entry are tracked as current working-tree changes.
### Notes
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/.handoff/claude/0.1.14-single-full-depth-mode-formal-fable-review-prompt.md`: added the standalone formal review prompt for Fable/Claude with A-J review requirements and strict PASS/BLOCKED rules.
- `/Users/a13497/Desktop/skill工作区/journal-style-skill/progress.md`: appended this formal-review-prep record.
- Rollback: delete the formal review prompt file and remove this progress entry; no code, runtime, C03 profile, Git tag, push, formal sync, or deployment state is changed by this prompt-only step.
