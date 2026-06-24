# journal-style 下游可消费化根源治理规划

> 文档类型：规划 / 交接（Claude 规划稿，交 Codex 后续施工）
> 输出路径：`/Users/a13497/.codex/skills/journal-style/.handoff/claude/2026-06-24-journal-style-downstream-consumable-plan.md`
> 版本基线：journal-style@0.1.9；文章润色@0.2.8.4.3
> 日期：2026-06-24

## 0. 文档定位与边界

本文只做思考与规划，不施工、不改源码、不跑正式任务、不连服务器、不触发 CNKI/WoS/Zotero/PDF/RAG、不写 C03、不进入真实文衡 B02。所有结论基于只读阅读现有 skill 文件得出。

### 0.1 本次治理要解决的一句话问题

journal-style 现在产出的是「期刊画像报告」，而下游（文章润色 / 正文写作 / 参考文献补注）需要的是「可直接执行的期刊适配约束 + 已刊样本校准的定位坐标」。画像层与执行层之间存在**信息粒度断层**和**契约产销断层**，导致下游拿到的可执行信息不足。

### 0.2 阅读范围（已只读核对）

journal-style：`SKILL.md`、`references/evidence-rules.md`、`references/fulltext-article-pattern-mining-protocol.md`、`references/scoring-rubric.md`、`references/downstream-handoff.md`、`references/handoff-to-{wenzhang-runse,zhengwen-xiezuo,cankao-wenxian}.md`、`references/handoff-{to,from}-jiansuo-ruku.md`、`references/output-schema.md`、`references/core-library-selection-protocol.md`、`references/secret-boundary-protocol.md`、`references/task-adapter-protocol.md`、`config/{stage-gates,workflow-states,source-profiles-schema,release-manifest}.json`、`scripts/{analyze_fulltext_article_patterns,score_fit}.py`、`templates/wenheng-handoff-schema.json`。

文章润色：`SKILL.md`、`scripts/{consume-journal-style-profile,assert-journal-style-consumed,polish-scan-journal-format}.py`、`config/{stage-gates,journal-style-consumption-policy,journal-profile-dimensions}.json`、`references/shared-protocol.md`。

### 0.3 关键事实指纹（施工前请复核这些是否仍成立）

- journal-style 全仓 `grep journal_style_profile_v1` **无生产者**；文章润色 `consume-journal-style-profile.py` 消费的是 synthetic fixture。**产销断层确认。**
- 现有全文分析 `analyze_fulltext_article_patterns.py` 是**聚合统计**（Counter 汇总），`article_summaries` 仅截前 12 篇、字段浅，**无逐篇完整体例画像**。
- `score_fit.py` 是 8 维 100 分制，但分值由外部主观喂入（`data.get(key, 0)`），**无已刊样本回放校准**，无分数区间/中位数/四分位。
- 文章润色 `polish-scan-journal-format.py` 的阈值（正文 3–6 节、关键词 3–8、引言≤2 段）是**通用写死默认**（`config/final-submission-quality.zh.json`），**未按目标期刊样本校准**。

## 1. 当前根因诊断

### 1.1 为什么现有画像无法有效帮助下游

第一，**粒度断层**。现有 fulltext 分析把核心库所有文章揉成全刊聚合（高频章节、材料/方法标记计数、摘要均长、关键词均量）。聚合量适合「给用户看的期刊概览」，但润色需要的是「本刊单篇文章长什么样」的分布与区间：字数区间、段落数、章节层级深度、是否分小节、脚注还是尾注、注释内容类型、参考文献中外比例。这些必须**先逐篇抽取再统计分布**，聚合均值会抹掉分布信息（例如均长 13000 字掩盖了 9000–18000 的真实区间）。

第二，**契约断层**。下游 `consume-journal-style-profile.py` 期望 `journal_style_profile_v1`，但 journal-style 从不生产它，只产出 markdown 报告 + 薄 handoff JSON 片段（`title_style`/`abstract_keywords`/`format_constraints` 数组）。下游只能拿 synthetic fixture 跑通流程，真实链路是断的。

第三，**可执行性断层**。现有交接字段多为「描述性」（如 `argument_style: []` 自由文本数组），无法直接变成润色检查项。润色侧需要「带阈值、带区间、带缺口判定」的结构化约束，才能落成 scan 的 PASS/FAIL。

第四，**定位缺失**。`score_fit.py` 只给用户稿件一个孤立分数，没有「已刊样本分数区间」作参照系，用户无法知道自己的稿件在该刊已发表文献中处于什么水平。

### 1.2 metadata-only / 普通 RAG 包 / 完整 mu 全文材料包 三者差别

- **metadata-only（题录+摘要）**：来源是数据库元数据/官网目录。能支撑题名风格、选题趋势、栏目结构、作者机构网络等。**禁止**用于全文风格、论证风格、体例细节证据（`journal-style-consumption-policy.json` 已把 `full_text_style_evidence` 等列入 `metadata_only_forbidden_uses`）。

- **普通 RAG 包（召回片段）**：来源是 RAG 向量库导出的命中片段。强项是「证据定位/召回」——回答「某主张在样本里有没有依据」。弱项是它是**碎片化、按 query 召回**的，不保证单篇文章结构完整，**无法做需要通读全篇的体例分析**（段落序列、章节树、脚注/尾注全集、参考文献表全量）。

- **完整 mu 全文材料包**：来源是 `检索入库` 经 mu 处理后的**整篇规范化全文**。这是体例分析的唯一充分输入：有完整正文、章节树、段落序列、注释全集、参考文献表、图表线索、页码字数、provenance 与 sha。**只有它能支撑逐篇深度体例画像。**

结论：RAG 包用于召回与证据定位（保留），mu 全文包用于体例分析（新增），二者**不可互相替代**，更不能用 metadata 冒充任何一种全文证据。

### 1.3 现有输出：可保留 vs 必须升级

可保留（继续作为画像层与防线，不动）：

- 状态机编排（`journal_style_runner.py` + `workflow-states.json` + `gate_runner.py` 现场重跑信任模型）。
- 发布态完整性闸门（`release-manifest.json` + `assert_release_integrity()`，fail-closed 退出码 3）。
- task-local adapter（只改 `gate_input`、白名单 step、sha 绑定）。
- `source-profiles-schema.json`（`检索入库`→journal-style 契约，provenance 反查 Step0）。
- 证据矩阵与降级策略（`evidence-rules.md`）、secret boundary、文衡 native + C03 source lock、公开介绍纪律。
- metadata-layer 全部分析（题名/趋势/栏目/作者机构/基金等）。

必须升级或新增：

- 新增 **mu 全文材料包契约**（当前 `source-profiles-schema.json` 只到题录行级 + pdf_ready/rag_ready 标志，无整篇 mu 正文/章节树/参考文献表字段）。
- 新增 **逐篇体例画像层**（替换「聚合即一切」，改为「逐篇→分组→聚合」）。
- 新增 **下游可消费契约 `journal_style_profile_v1` 的真实生产者**（消解产销断层）。
- 升级 **评分**：从孤立主观分升级为「已刊样本回放校准 + 区间定位」。
- 升级 **证据门槛**：把用户要求的 10 / 10–19 / 20+ / 20–30 分级门槛写进 gate。

## 2. 新增材料包契约：`mu_fulltext_core_pack`

### 2.1 定位与职责边界

`mu_fulltext_core_pack`（建议 schema id：`journal_style_mu_fulltext_core_pack_v1`）是核心库文章的**完整 mu 处理全文材料包**，是逐篇体例分析的唯一充分输入。

职责锁定（与现有协议一致）：

- 由 `检索入库` 或上游材料链**生产**（真实 PDF 获取、OCR、mu 文本规范化、章节/参考文献解析、RAG 导库全部在上游）。
- journal-style **只验收和分析，不自行检索下载**。这条与 `fulltext-article-pattern-mining-protocol.md`「本 skill 只分析交接出的文本，不新增下载职责」一致，必须延续。
- 它是对现有 `source-profiles-schema.json` 的**扩展层**，不是替代：题录行级契约继续存在；`core_library_selected=true` 的行**额外**要求挂一个 mu 全文包条目。
- 普通 RAG 包**可继续用于召回与证据定位**，但 gate 层必须区分「RAG 召回可用」与「mu 全文体例就绪」两种就绪状态，前者不能点亮后者。

### 2.2 来源与 provenance 约束

- mu 全文包文件本身必须在 Step0 `material-intake-manifest.json` 注册，sha256 与 manifest 一致（沿用 `provenance_back_reference` 机制）。
- 每篇条目 `article_id` 必须能 join 回 `core-library-ledger.json`（沿用 `join_key=item_key`、`core_join_completeness_min=0.9`）。
- 每篇必须带 `provenance`（来源 ledger、抽取方式、mu 版本）与 `sha`（全文文本 sha256），否则该篇判 `NO_GO`，不得进入逐篇画像。
- secret boundary 延续：包内不得含 key/token/cookie/vector dump；journal-style 不解析 Zotero DB。

### 2.3 条目字段契约（每篇文章一条）

必填（缺一即该篇 `NO_GO`）：`article_id`、`title`、`authors[]`、`year`、`column`、`mu_fulltext`（mu 规范化整篇正文）、`provenance{source_ledger, extraction_method, mu_version}`、`fulltext_sha256`。

体例结构字段（缺失记降级标签，不静默置空）：

- `abstract`、`keywords[]`；
- `section_tree[]`：章节树，每节 `{level, title, order, has_subsections, subsection_count}`，支持多级层级；
- `paragraph_sequence[]`：段落序列，每段 `{section_ref, order, char_count}`，用于段落数与平均段长；
- `notes{type: footnote|endnote|inline|none, count, content_types[]}`：脚注/尾注判别 + 注释内容类型（释义、出处、补充论证、致谢等）；
- `reference_list[]`：参考文献表，每条 `{raw, year, lang(zh|foreign), is_self_journal}`，支撑中外比例 / 近年比例 / 期刊内互引；
- `figures_tables{figure_count, table_count, plate_clues[]}`：图表线索；
- `page_range`、`char_count_total`：页码与字数。

### 2.4 与普通 RAG 包的硬区别（写进契约说明，供 gate 判别）

| 维度 | 普通 RAG 包 | mu 全文核心包 |
|---|---|---|
| 形态 | 按 query 召回的碎片 | 整篇规范化全文 |
| 完整性 | 不保证单篇完整 | 单篇完整、可通读 |
| 适用 | 召回 / 证据定位 | 逐篇体例深度分析 |
| 就绪标志 | `rag_ready/recall_ok` | `mu_fulltext_ready`（新增） |

### 2.5 包级验收门槛

- 包内每篇必填字段覆盖率必须 100%，否则该篇不计入「就绪篇数」。
- 「就绪篇数」= 同时满足必填齐全 + sha 校验通过 + join 回核心库的篇数。
- 体例结构字段（section_tree / reference_list 等）按篇统计覆盖率，低覆盖率字段在下游聚合时强制降级标签。
- 包级 gate 产出 `mu_fulltext_ready_count` 与各结构字段覆盖率，作为后续逐篇/聚合门槛的输入。

## 3. 逐篇分析层：`per_article_style_profile_v1`

### 3.1 定位

对 mu 全文包里每一篇**就绪**文章单独产出一份 `per_article_style_profile_v1`（建议落点 `03-analysis/fulltext-layer/per-article/<article_id>.json`）。这是「逐篇→分组→聚合」三段式的第一段，**先逐篇、再分组、再汇总**，不允许跳过逐篇直接聚合。

### 3.2 每篇必须单独抽取的维度

- `title_structure`：主副标题、字数、问题-对象结构、常见动词。
- `abstract_profile`：结构（背景/问题/方法/结论是否齐全）、字数。
- `keywords_profile`：数量、类型（主题词/方法词/对象词）、排序。
- `length_band`：全文字数区间归档（落入哪个区间桶）。
- `paragraph_stats`：段落总数、平均段长、最长/最短段。
- `section_hierarchy`：章节层级深度、是否分小节、各级节数。
- `intro_pattern`：引言模式（开门见山/综述切入/材料切入/问题切入）。
- `material_types[]`：材料类型（档案/碑帖/图像/田野/数据库/文献汇编）。
- `method_types[]`：方法类型（考辨/比较/个案/阐释/计量/图像分析/文本分析）。
- `argument_rhythm`：论证节奏（小节推进方式、单节材料密度、是否报告体堆叠）。
- `notes_profile`：脚注/尾注/夹注判别 + 注释内容类型分布。
- `reference_profile`：参考文献数量、格式体例、中外比例、近年（近 5 年）比例、期刊内互引数。
- `conclusion_pattern`：结论方式（回应问题/展望/收束判断）。
- `downstream_constraints`：从本篇可派生、供下游使用的约束（**只给约束，不输出可抄写正文**）。

### 3.3 逐篇画像的硬纪律

- 每篇 profile 的**每条结论**必须带 `evidence_path`（指向 mu 全文包内 section/paragraph 锚点）、`article_id`、`provenance`。无锚点的结论判 `NO_GO`，不得写入。
- 规则识别（章节/材料/方法标记）必须标 `rule_based=true` 并允许人工复核，沿用现有 `fulltext-article-pattern-mining-protocol.md` 的「允许人工复核」原则。
- `downstream_constraints` 只能是「区间/数量/比例/层级/有无」类约束，**严禁**出现可直接粘贴的句子、段落或题名。

## 4. 聚合归纳层

逐篇 profile 全部完成后才能进入聚合。聚合层从逐篇 profile 计算**分布（区间/中位数/四分位/众数）**，不是简单求均值。

### 4.1 五个聚合产物

- `journal-style-constraints-lock`（`journal_style_constraints_lock_v1`）：体例硬约束总锁（字数区间、段落区间、章节层级、摘要关键词、注释体例），下游润色直接消费。
- `journal-format-convention-profile`：格式体例画像（脚注 vs 尾注、参考文献格式、英文项、图表惯例）。
- `journal-argument-preference-profile`：论证风格偏好（引言模式分布、论证节奏、材料-论证配比）。
- `journal-reference-ecology-lock`：参考文献生态锁（篇均量区间、中外比例、近年比例、期刊内互引率、高频作者/文献候选）。
- `journal-polish-consumption-pack`：面向文章润色的总消费包（即真实 `journal_style_profile_v1`，见第 5 节），聚合上述四项为可执行检查项。

### 4.2 每个产物的强制元数据

每项聚合产物必须带：`sample_count`（就绪篇数）、`coverage`（该维度逐篇覆盖率）、`confidence`（high/medium/low）、`degrade_label`（降级标签）、`evidence_index`（可反查的逐篇 article_id 列表）。

### 4.3 样本门槛矩阵（按用户要求分级，写进 gate）

| 样本就绪篇数 | 允许输出的结论强度 |
|---|---|
| < 10 篇 | 仅「样本观察」，禁止任何稳定结论；下游只能拿观察提示 |
| 10–19 篇 | 「初步偏好」：可给体例/格式初步约束，标 `preliminary` |
| ≥ 20 篇 | 允许「稳定体例/风格结论」 |
| 论证风格 / 参考文献生态 | 建议门槛上调至 20–30 篇方可写稳定结论；20–29 篇标 `medium`，≥30 篇方可 `high` |

该矩阵必须与 `evidence-rules.md` 现有门槛**对齐并取严**（现有 format_convention 仅 10 篇全文、rag_fulltext_pattern 10/20 篇；新矩阵不得低于现有，论证/参考文献按用户要求提高）。任何低于门槛的产物，gate 强制写降级标签，不允许 prose 自行「软化」。

## 5. 下游消费协议

总原则：journal-style 只交「约束 + 缺口 + 定位」，绝不交「正文 / 润色文本 / 可抄写句段」。下游契约统一升级到能直接落成检查项。

### 5.1 给 `文章润色`（消解产销断层的核心）

升级 `journal_style_profile_v1`，使其成为 `journal-polish-consumption-pack` 的真实落盘，至少包含可直接变成 scan 检查项与差距定位的字段：

- `length_band`：字数区间 → 比对用户稿字数，输出超/欠区间差距。
- `paragraph_band`、`section_hierarchy`：段落数 / 章节层级 → 比对结构。
- `abstract_keywords`：摘要长度区间、关键词数量区间与排序习惯。
- `notes_convention`：脚注/尾注、注释内容类型 → 比对用户稿注释体例。
- `reference_constraints`：篇均量区间、中外比例、近年比例、期刊内互引下限。
- `title_style`：题名模式（只给模式，不生成题名）。
- `argument_rhythm`：论证节奏约束。
- `citation_density`：正文引用密度区间。
- `gap_checklist[]`：基于上述区间的「缺口清单」模板。
- `source_evidence_scope` 与 `metadata_only`：延续现有策略，metadata_only 时禁止点亮全文风格约束（与 `journal-style-consumption-policy.json` 对齐）。

落地要点：文章润色 `polish-scan-journal-format.py` 当前用写死阈值；治理后应允许它**读入本 pack 的区间覆盖默认阈值**（区间缺失时回退默认，并标注 `calibrated=false`）。

### 5.2 给 `正文写作`

升级 `handoff-to-zhengwen-xiezuo` 字段为可执行结构约束，但**不写正文**：

- `structure_constraints`：章节数区间、层级深度、是否分小节。
- `section_rhythm`：各节材料密度、论证推进方式。
- `material_method_preference`：偏好材料/方法类型分布。
- `argument_scale`：论证尺度（问题意识类型、结论尺度）。
- `avoid_patterns[]`：避免项（报告体堆叠、综述式引言等）。
- 全部带 `evidence_paths` 与 `confidence`；低置信点单列 `pending_evidence`。

### 5.3 给 `参考文献补注`

升级 `handoff-to-cankao-wenxian` 的 `reference_ecology`，全部来自 `journal-reference-ecology-lock`：

- `reference_count_band`：篇均参考文献数量区间。
- `recent_ratio_target`：近年文献比例目标区间。
- `foreign_ratio_target`：中外比例目标区间。
- `self_journal_citation_target`：期刊内互引率目标。
- `high_frequency_authors[]` / `high_frequency_references[]`：高频作者/文献**候选**，每条必须带可追溯样本 `evidence_paths`，外文文献真实性单独标 `foreign_verified`。
- `user_reference_gaps[]`：用户稿件相对生态的缺口。
- 纪律延续：互引建议不得变成机械堆引用；候选不得伪造。

### 5.4 给 `检索入库`（补采请求）

当 mu 全文包就绪篇数 / 字段覆盖率不足门槛时，journal-style **不硬生成结果**，而是产出结构化补采请求（沿用 `handoff-to-jiansuo-ruku.md` 的 `journal_corpus`/`topic_library` 请求形态，新增 mu 维度）：

- `missing_fulltext[]`：缺哪些完整 mu 全文（按 article_id / 核心库条目）。
- `missing_core_libraries[]`：缺哪些核心库（栏目/年份覆盖缺口）。
- `missing_reference_parse_fields[]`：缺哪些参考文献解析字段（如 year/lang/self_journal 未解析）。
- `mu_processing_required=true`：明确要求 mu 处理后的完整文本，而非碎片召回。
- 验收沿用现有 `acceptance`（item-level receipt、recall_test），新增 `require_mu_fulltext=true` 与 mu 字段覆盖率要求。

补采请求必须保持 `no_topic_change`，且 journal-style 不自行执行检索下载。

## 6. 多维度期刊适配评分模型

### 6.1 命名与定性

建议命名 `journal_fit_scoring_model_v1`（对外）/ `editorial_preference_proxy_v1`（内部别名）。**治理「模仿主编」**：

- 不叫、不声称模拟任何具体主编个人；只做「基于已刊样本校准的期刊适配近似」。
- 不承诺录用；输出是「与已刊文献库的相似度定位」，不是「录用概率」。
- 不把主观猜测写成事实；每个维度分必须可验证、可反查证据。
- 文档与输出措辞必须是「初版校准评分器（calibrated scorer, 初版）」，**不得**表述为「统计意义上稳定的机器学习模型」。

### 6.2 评分维度（可验证）

在现有 `score_fit.py` 8 维基础上重构为可校准维度，每维必须绑定证据来源：

1. 题名/摘要/关键词适配（对照 `journal-polish-consumption-pack` 区间）。
2. 体例格式适配（字数/段落/章节层级/注释体例）。
3. 章节结构适配。
4. 材料方法适配。
5. 论证风格适配。
6. 参考文献生态适配（对照 ecology-lock 区间）。
7. 注释脚注规范适配。
8. 投稿运营/风险项（沿用 submission-operations 证据，风险单独扣分）。

### 6.3 已刊样本回放校准（核心，区别于现状）

现状 `score_fit.py` 只给孤立分；治理后必须：

- **先对已刊核心样本回放评分**：用同一评分器给 mu 全文包中每篇已刊文章打分。
- 计算 `published_score_distribution`：分数区间、中位数、四分位（Q1/Q3）、低分异常样本及其解释。
- 用户稿件评分必须**与该分布比较**，输出 `percentile_position`（处于已刊样本的哪个分位）与 `gap_to_median`，而非孤立分数或主观印象。
- 评分器在未完成样本回放前，**禁止**用于用户稿件定位（见第 7 节 gate）。

### 6.4 1–3 轮测试与锁定流程

每轮都用 fixture/已刊样本，不用真实任务做试验台：

- **第 1 轮：回放核心样本**。给全部已刊样本打分，检查分布是否合理（已刊样本不应大面积低分；若大面积低分→说明维度/权重失真）。修复机制：调权重、调维度判据，记录到 `scoring-calibration-log`。
- **第 2 轮：抽查边界样本**。选取已知「该刊典型高契合」与「明显改投/被拒」样本（可用降级/反例 fixture），检查评分器能否区分。修复机制：补充判据、修正误判维度。
- **第 3 轮：对一个用户稿件做差距定位**（fixture 稿）。检查 `percentile_position`、`gap_checklist` 是否可解释、可执行。修复机制：对齐下游 `gap_checklist` 字段。
- 每轮列出：输入样本、期望、实测、偏差、修复项、是否进入下一轮。三轮后**锁定评分标准**（权重 + 判据 sha 写入 release-manifest 追踪范围）。

### 6.5 输出契约

评分输出 `journal_fit_score_v1` 必须含：`total`、各维度分 + 证据、`published_score_distribution{min,q1,median,q3,max,low_outliers[]}`、`user_position{percentile, gap_to_median, gap_checklist[]}`、`confidence`、`degrade_label`、`calibration_round`（已完成校准轮次）。措辞固定为「初版校准评分器，非统计稳定模型」。

## 7. 状态机与 gate 规划

### 7.1 新增/改造的 workflow step

在现有 `workflow-states.json`（step00–step10）基础上插入，保持「严格顺序、不跳步、不压步」：

- 改造 `step06_zotero_pdf_rag`：验收新增 `mu_fulltext_ready_count` 与 mu 字段覆盖率（仍走 zotero-pdf-rag-handoff gate，扩展阈值）。
- 新增 `step07b_mu_fulltext_pack_acceptance`：验收 mu 全文包契约（gate：`mu-fulltext-pack`）。
- 新增 `step08b1_per_article_profile`：逐篇画像（gate：`per-article-profile-complete`）。置于现 `step08b_fulltext_layer` 之前或并入其前段。
- 改造 `step08b_fulltext_layer`：改为「聚合层」，消费逐篇 profile 产出五个聚合产物（gate：`aggregation-threshold`）。
- 新增 `step09b_scoring_calibration`：评分器样本回放校准（gate：`scoring-replay-calibrated`）。
- 改造 `step10_handoff`：产出真实 `journal_style_profile_v1` / polish-consumption-pack（gate：扩展 `no-metadata-only-completion`）。

### 7.2 必须 fail-closed 的 gate

- `mu-fulltext-pack`：完整 mu 全文包缺失或就绪篇数为 0 → 不得声称 `fulltext-style-ready`。
- `per-article-profile-complete`：未完成逐篇 profile → 不得进入聚合（沿用「无 gate 步骤永不跳过」+ 本 gate 强制逐篇齐全）。
- `aggregation-threshold`：样本低于 4.3 节门槛 → 不得输出稳定风格结论，强制降级标签。
- `provenance-required`：任一聚合/约束 lock 缺 provenance/evidence_index → 不得进入下游 constraints lock。
- `scoring-replay-calibrated`：评分器未完成样本回放 → 不得用于用户稿件定位。

所有 gate 沿用现有信任模型：`gate_runner.py` 现场重跑、verdict 内嵌 sha、手写/过期 verdict 不被信任。

### 7.3 防线保持

- 新增 config（如 `mu-fulltext-pack.schema.json`、扩展 `stage-gates.json`、新 workflow step）与新脚本必须纳入 `release-manifest.json` 的 sha256 追踪，发布用 `build_release_manifest.py --require-clean` 重签。
- 任务级路径差异只能走 task-local adapter；新增 step 若需 adapter，必须扩展白名单并保持「只改 gate_input」铁律。
- 阈值集中在 `config/`，脚本不得硬编码第二份（延续现有原则）。

## 8. 测试与验收

### 8.1 需要的 fixture（全部假数据，不碰真实任务）

- `fixtures/mu-pack/`：合规 mu 全文包样例（含 12–30 篇合成文章，字段齐全）+ 残缺包（缺 section_tree / 缺 provenance / sha 不匹配）用于触发 NO_GO。
- `fixtures/per-article/`：逐篇 profile 期望输出（golden）。
- `fixtures/aggregation/`：分别覆盖 <10 / 10–19 / 20+ / 30+ 篇四档，验证降级标签随门槛变化。
- `fixtures/scoring/`：含已刊样本回放集 + 边界样本（高契合 / 改投）+ 一份用户稿 fixture。
- `fixtures/downstream/`：润色/正文/补注三个下游消费契约的 golden 输出。

### 8.2 用假数据验证 schema/gate（不用真实任务）

- 复用现有 `tests/run_state_machine_fixtures.py` 模式：复现「逐篇未完成就聚合」「样本不足却出稳定结论」「mu 包缺失却宣称 fulltext-ready」「评分器未回放就定位用户稿」四类事故，断言被 gate 拦截。
- schema 校验脚本（仿 `validate_source_profiles.py`）对 mu 包 / 逐篇 / 聚合 / 评分四层做契约校验。
- smoke test 仿 `run_smoke_tests.py`，用临时样本跑通新脚本，不读真实任务数据。

### 8.3 如何证明「不是伪数据」

每一项下游输出必须可回溯，validator 强制检查：

- `source`（来自哪个 mu 包 / 哪批 article_id）、`sample_count`、`coverage`、`fulltext_sha256`/`provenance`、`degrade_label` 五件套缺一不可。
- 聚合 lock 的 `evidence_index` 必须能 join 回逐篇 profile，逐篇能 join 回 mu 包，mu 包能 join 回 Step0 manifest——形成**端到端 provenance 链**。
- 任一环断裂即判 NO_GO，不允许「无源好看结论」。

### 8.4 必须输出「待补材料」而非硬生成的情形

- mu 全文包就绪篇数 < 门槛；
- 关键体例字段覆盖率过低（如 reference_list 解析覆盖率不足）；
- 评分样本回放集不足以形成分布；
- provenance 链断裂。
以上一律产出第 5.4 节的补采请求 + 降级说明，绝不用占位/想象数据补齐。

## 9. 分阶段实施建议

每阶段只列「预计要改/新增的文件」，本规划不实际修改任何文件。

### Phase 1：契约 / schema / gate / fixture（不做真实检索）

目标：把断层在契约层补齐，全部用 fixture 验证。

预计新增：
- `config/mu-fulltext-pack-schema.json`（mu 包契约）。
- `config/per-article-profile-schema.json`、`config/aggregation-schema.json`、`config/scoring-model-schema.json`。
- `config/stage-gates.json`（扩展：新增 5 个 gate 阈值块）。
- `config/workflow-states.json`（插入新 step）。
- `tests/fixtures/...`（第 8.1 节全部）、`tests/run_downstream_consumable_fixtures.py`。
- `references/mu-fulltext-pack-protocol.md`、`references/per-article-profile-protocol.md`、`references/scoring-model-protocol.md`。

预计改造：`SKILL.md`（首版能力范围 + 工作流补段）、`references/evidence-rules.md`（门槛对齐取严）、`release-manifest.json`（新文件纳入 sha 追踪）。

### Phase 2：接入 mu 全文包验收与逐篇 profile

预计新增脚本：
- `scripts/accept_mu_fulltext_pack.py`（验收 mu 包，产 `mu-fulltext-pack` gate 输入）。
- `scripts/build_per_article_profile.py`（逐篇画像，替代「聚合即一切」的前段）。
- `scripts/validate_mu_fulltext_pack.py`、`scripts/validate_per_article_profile.py`。

预计改造：`scripts/analyze_fulltext_article_patterns.py`（从「聚合一切」降为「读逐篇 profile 做分布聚合」）、`workflow-states.json`（step07b/step08b1）、`gate_runner.py` / `run_stage_gates.py`（新增 gate 逻辑，阈值仍读 config）。

### Phase 3：聚合 constraints lock 与下游 handoff

预计新增脚本：
- `scripts/build_aggregation_locks.py`（产五个聚合产物）。
- `scripts/build_polish_consumption_pack.py`（产真实 `journal_style_profile_v1`，消解产销断层）。
- `scripts/validate_aggregation.py`、`scripts/validate_downstream_handoff.py`（端到端 provenance 链校验）。

预计改造：
- `references/handoff-to-wenzhang-runse.md` / `handoff-to-zhengwen-xiezuo.md` / `handoff-to-cankao-wenxian.md` / `downstream-handoff.md`（升级为可执行结构约束字段）。
- `references/output-schema.md`（新增逐篇/聚合/消费包产物清单）。
- 文章润色侧（跨 skill 协调，非本仓）：`consume-journal-style-profile.py` 改为消费真实 pack；`polish-scan-journal-format.py` 支持读区间覆盖默认阈值；`journal-style-consumption-policy.json` 扩展字段。**此项需在文章润色仓另立施工项，遵循其 Claude 规划→Codex 施工链。**

### Phase 4：评分模型 + 1–3 轮回放测试 + 润色消费闭环

预计新增脚本：
- `scripts/build_scoring_model.py`、`scripts/replay_calibrate_scoring.py`、`scripts/score_user_manuscript.py`（区间定位）。
- `scripts/validate_scoring_calibration.py`。
- `config/scoring-calibration-log.schema.json`、产物 `scoring-calibration-log.json`。

预计改造：`scripts/score_fit.py`（并入或被新评分器取代，保留兼容）、`workflow-states.json`（step09b）、`SKILL.md`（评分模型措辞纪律：初版校准评分器、不模拟主编、不承诺录用）。

闭环验收：用 fixture 用户稿走完「mu 包→逐篇→聚合→消费包→评分定位→文章润色消费」，确认润色侧拿到的是带区间、带缺口、带定位的可执行约束，且全链 provenance 可反查。

### 跨阶段依赖

Phase 1 是其余阶段地基；Phase 2 依赖 Phase 1 契约；Phase 3 依赖 Phase 2 逐篇产物；Phase 4 依赖 Phase 3 聚合区间。建议每阶段单独走「Codex 准备→Claude 规划→Codex 施工→Claude 评审」链，不一次性合并。

## 10. 边界复述（施工红线）

- journal-style **不写正文、不润色正文、不模仿期刊正文语气**；逐篇/聚合产物只给约束，严禁可抄写句段。
- **不绕过 `检索入库`** 执行 CNKI/WoS/Zotero/PDF/RAG；mu 全文包由上游生产，journal-style 只验收分析。
- **metadata-only 不得冒充全文证据**；RAG 召回包不得点亮 `mu_fulltext_ready`。
- **不用 10 篇样本声称统计稳定模型**；统一表述「初版校准评分器」，并明示稳定性门槛（20+ / 论证·参考文献 20–30）。
- **不生成虚构示例数据冒充真实结果**；门槛不足一律输出「待补材料」+ 降级标签。
- 评分器**不模拟具体主编、不承诺录用、不把主观猜测写成事实**。

## 11. 未决问题（交用户/Codex 决策）

1. mu「完整性」判定标准：以字符数下限、章节树完整度，还是上游 mu_version 标志为准？建议三者组合，阈值入 config。
2. 字数区间分桶粒度（如 3 桶 vs 5 桶）需结合目标学科（艺术学）实际分布定，Phase 2 用 fixture 标定。
3. 评分维度权重是否复用现有 `score_fit.py` 的 20/15/15/10/15/10/10/5，还是按校准结果重定？建议第 1 轮回放后定。
4. 文章润色侧改造跨仓，需确认是否本轮一并立项，还是 journal-style 先把真实 pack 产出、润色侧后续对接。
5. 「期刊内互引」判定需要可靠的刊名归一化；若上游未提供，列入补采字段。

## 12. 一句话交接

先在 Phase 1 用契约 + gate + fixture 把「mu 全文包 / 逐篇画像 / 聚合 / 评分 / 下游消费」五层 schema 钉死并 fail-closed，再分阶段接入真实 mu 全文包，最终让文章润色拿到「带区间、带缺口、带已刊样本定位」的可执行约束，而不是一份期刊画像报告。全程保持 release 完整性闸门、provenance 链与降级纪律，不施工本规划之外的任何真实任务。
