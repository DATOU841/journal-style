# 期刊评审工作台记忆包协议

## 定位

`journal_review_memory_v1` 是从 Obsidian「期刊评审工作台」人工笔记编译出的风格记忆 overlay。它与 `journal_style_profile_v1` 平行，但证据等级更低。

它只能作为建议性控制面使用：

- `provenance` 必须是 `human_review_memory`
- `source_evidence_scope` 必须是 `human_review_memory`
- `not_evidence` 必须是 `true`
- 不得包含 `source_excerpt`
- 不得生成或绑定正文事实证据

## 输入来源

编译器只读取 Obsidian note 的 YAML front matter，不读取正文 body 作为机器输入。推荐来源：

- `03-期刊适配/<刊>-投稿要求.md`
- `02-高危病灶库/*.md`

`00-总控`、`10-个案评审`、`20-经验回写` 的过程性笔记不进入消费包。

## 输出位置

正式任务中，消费包应作为 handoff 附件复制到任务目录：

```text
00-intake/journal-review-memory-pack.json
```

共享缓存可以使用：

```text
/Users/a13497/.codex/shared/journal-review-memory/<刊slug>.json
```

共享缓存不是开发源，也不是证据源。

## 下游消费边界

正文写作只读取前塑型字段：

- `style_hints`
- `avoid_patterns` 中已人工晋升或候选 lint 项
- `abstract_conclusion_rules`

文章润色可读取修复型字段：

- `format_specs`
- `verified_fix_strategies`
- `ai_tone_replacements`
- `avoid_patterns`

`verified_fix_strategies.fix_kind=evidence_action` 只能路由到检索入库或 RAG 补证，不得让正文写作或文章润色直接编造引用。

## 冲突处理

当记忆包与以下对象冲突时，记忆包让位：

1. G07 active rules
2. `journal_style_profile_v1` 证据型期刊画像
3. 正式 RAG grounding
4. guard ledger / source trace

冲突必须记录到下游 receipt 或 handoff 的 `review_memory_conflicts`。
