# task-adapter-protocol

任务级路径适配协议（0.1.9 引入，配合发布态完整性闸门）。

## 为什么需要

发布态完整性闸门对 `config/` 和状态机脚本做发布后字节漂移检测：执行窗口在跑任务时直接修改 `workflow-states.json`（例如临时加 `gate_input`）会被 fail-closed 拦截。发布期必须用 `build_release_manifest.py --require-clean` 重签，避免未提交改动被直接纳入 manifest。但真实任务里，已有产物有时落在与 skill 默认不同的 task-local 路径。task-adapter 就是唯一受控的适配通道：它只改「gate 判定读哪个 task-local 输入文件」，绝不改 contract。

## 文件位置

`<task-dir>/00-intake/task-adapter-manifest.json`，缺省不存在即视为无 override。

## 字段契约

```json
{
  "schema": "journal_style_task_adapter_v1",
  "task_id": "<task-dir-name>",
  "overrides": [
    {
      "step": "step06_zotero_pdf_rag",
      "field": "gate_input",
      "task_local_path": "025-rag-import/zotero-pdf-rag-handoff-input.json",
      "input_sha256": "<live artifact sha256>",
      "registered_in_step0": true,
      "reason": "existing task stores handoff at a non-default path"
    }
  ]
}
```

## 硬约束（校验器强制，违反即 fail-closed）

- `field` 只能是 `gate_input`；override 只改 task-local 输入路径。
- `step` 必须在白名单内：当前仅 `step06_zotero_pdf_rag`、`step08a_metadata_layer`。
- `task_local_path` 必须位于 task_dir 内（拒绝越界路径）。
- 工件必须存在，且实时 sha256 必须等于 `input_sha256`（登记后调包会被拒）。
- 工件必须已在 `00-intake/material-intake-manifest.json`（Step0 清单）按相同 rel_path + sha 注册，且 `registered_in_step0=true`。
- 出现任何 contract 字段（`gate`、`next`、`threshold`、`resume_skippable`、`gate_logic`、`verdict`）即拒绝。

## 记账

runner 命中合法 override 时，把它写入 `current-run-state.json` 的 `applied_overrides`，供审计与 H08 candidate 追溯。override 只影响输入路径解析，后续 gate 仍由 `gate_runner` → `run_stage_gates` 现场重跑判定，sha 链不变，override 无法削弱既有防线。
