# 文衡原生接入协议

## 适用范围

本协议适用于期刊身份分析、题录/样本分析、投稿匹配评分、C03 profile handoff 和下游技能交接。

## 启动前置

正式分析或评分前必须已有文衡 B02 task packet，至少包含：

- `wenheng_task_id`
- `task_folder`
- `task_type = journal_style`
- `target_skill`
- `f06_routing_decision`
- `h08_evidence_stub`

缺少任一关键字段时，只能生成 `wenheng-intake-request`，不得正式分析、评分或产出 C03 profile。

## 启动收据与执行闸门

正式任务必须先运行 `scripts/journal-style-startup.py`。该入口验证 B02/F06/H08 后，在 task folder 写入 `00-intake/wenheng-native-binding.json`，作为后续本地执行入口的唯一 task-local 文衡绑定收据。

- `scripts/build_task_skeleton.py` 默认要求该绑定收据存在且为 `validated_by_b02_task_api`，否则 fail-closed。
- `scripts/journal_style_runner.py` 默认要求该绑定收据存在且为 `validated_by_b02_task_api`，否则 fail-closed。
- 只有显式离线调试可以使用 `--allow-legacy-debug` 或 `WENHENG_ALLOW_LEGACY_FLOW=1`；legacy/debug 输出不得作为 production evidence、C03 profile 或 H08 完成证据。
- `00-intake/wenheng-intake-request.json` 只是请求文衡创建或绑定 B02 task 的待办，不是正式任务开始凭证。

## G07 适用性

本 skill 不写正文、不润色正文、不模仿期刊语气，正文风格类 G07 rules 默认不适用；必须在 `wenheng-center-status.json`、H08 evidence 和 C03 handoff 中写 `style_memory_not_applicable_reason`。若面向用户的分析摘要或交接说明需要中文表达约束，可读取 G07 active rules 并记录 applied/ignored/conflicts。

## C03 handoff

完成后必须产出 `05-handoff/wenheng-center-status.json` 和 C03 handoff，并由文衡后端受控调用 `/api/c03/journal-profiles/from-task/:taskId` 写入 C03。`task_id`、`source_run_id`、`evidence_path`、`source_skill` 实行来源锁定（source lock），只能由文衡 task、运行事件和 H08 evidence 派生，不得手工伪造。只允许建议 C03 微调字段：`priority`、`submission_stage`、`tags`、`next_action`、`match_status`。

## B02/H08 回写

identity confirmed、title corpus ready、RAG/sample status、fit score ready、handoff ready 必须回写 B02 timeline 和 H08 evidence。失败进入 H08 error review；完成进入文衡 archive package；期刊画像经验和用户反馈进入 G07 feedback candidate。

## 数据边界

不得把真实全文、PDF 内容、RAG chunk、Zotero 底层数据、绝对路径、cookie、token、key 或完整 prompt 写入文衡。只写脱敏摘要、计数、证据强度、风险、相对 task folder 引用和 next action。

## Sidecar 接口

检索入库 0.2.11 的 sidecar 只作为可选增强输入使用。文衡侧与 journal-style 只接收安全摘要、角色登记、查询种子计划、全文可用性指针和缺口账本，不接收 `full.md` 正文、RAG chunk、向量、Zotero DB 或带签名的下载 URL。
