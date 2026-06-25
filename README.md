<!-- content_source: wenheng_claude -->
<!-- skill_name: journal-style -->
<!-- version: 0.1.12 -->

# journal-style

journal-style 是文衡体系中的期刊风格分析与投稿辅助决策工具。基于题录数据、公开信息和已交接的全文样本，提取期刊多维特征并输出可解释的辅助评分，为投稿决策和选题规划提供证据线索和辅助决策参考。

公开介绍见 [docs/public-introduction.zh.md](docs/public-introduction.zh.md)

## 它解决什么问题

在投稿前系统了解期刊选题范围、作者构成、参考文献偏好，评估稿件与目标期刊的匹配度。

## 当前能力

面向人文社科期刊投稿场景。核心能力包括期刊身份确认与数据库收录状态核验、题录接收与缺口标记、数量化分析（发文量、基金占比、机构分布）、选题趋势画像、参考文献生态统计、样本内结构观察、投稿匹配度可解释辅助评分。

## 边界

真实检索、PDF 获取、RAG 入库由检索入库技能承担，journal-style 不执行数据库实检、不主动获取题录、不主动操作 Zotero。投稿匹配度评分为可解释辅助评分，明确权重配置与证据来源，不能替代编辑部真实偏好。题录、Zotero 状态、PDF/RAG 状态必须来自上游已交接材料。上游缺失时进入降级模式，只输出已证实信息并生成缺口清单。

## 开发验证

校验脚本按本仓库 scripts/ 路径运行，默认使用 Python 3。

在提交前执行以下校验：

```bash
python3 scripts/validate_readme.py
python3 scripts/validate_public_introduction.py --mode final
python3 scripts/run_smoke_tests.py
python3 -m py_compile scripts/*.py
```

## 发布纪律

- 版本号遵循语义化版本控制
- 当前版本：0.1.12
