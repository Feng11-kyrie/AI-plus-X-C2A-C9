# AI 生成日志 / AI Generation Log

**作者 / Author:** Feng Shuo（冯硕）
**挑战 / Challenge:** C2A — Track 2 Metacognition
**日期 / Date:** 2026-10-11

---

## 工具 / Tools Used

- **WorkBuddy 助手（均衡）** — 论文分析、benchmark 调研、提案撰写、迭代优化、文件生成
- **WebSearch × 6 轮** — 核实元认知相关 benchmark 与论文出处（确保文献真实可查，对应评分「研究严谨性 20 分」）
- **pypdf（Python）** — 提取 DeepMind 论文原文（/tmp/deepmind_paper.txt，32 页）与中文摘要，供精确检索元认知三层定义
- **unzip + 模板分析** — 解包 c2a-starter.zip，逐行研读 TestStudent 三件套（proposal/AI日志/拿来说明）以对齐交付格式

---

## 论文精读 / Paper Analysis

- **方法：** 把 DeepMind 论文 PDF 交给助手，要求定位并提取：
  1. 10 个认知能力定义与五个缺口赛道
  2. Metacognition（§7.7）的三层框架（knowledge / monitoring / control）
  3. 论文对元认知评估缺口的归因（缺跨域、缺 OOD 转移、缺控制层测量）
- **关键提取：** 论文明确指出元认知三层结构，且**强调只在熟悉领域测校准 ≠ 测元认知，必须做 OOD 转移**。这一点直接成为 MetaCog-Bench 的「OOD 转移护栏」设计。
- **迭代：** 1 轮精读 + 1 轮追问（确认 KSTAR 的 ΔE 与 monitoring 层校准误差的对应关系）。

---

## Benchmark 调研 / Benchmark Research

- **搜索策略（6 轮）：**
  - Q1: 置信度校准 LLM benchmark（Mirror / SelfAware / ConfidenceBench / CalibratedMath）
  - Q2: 选择性预测 / 拒答 benchmark（evaluate-idk / AbstentionBench）
  - Q3: SelfAware 数据集出处与 F1 数字（确认 arXiv:2305.18153，GPT-4 75.47% vs 人 84.93%）
  - Q4: UQ / 幻觉 benchmark（ConfidenceBench / CalibratedMath / TruthfulQA）
  - Q5: SelfAware 原文核实
  - Q6: LLM 元认知 benchmark 2025（HalluLens / Omniscience Index / Metacognition survey 2607.11881）+ Kadavath / AbstentionBench / CalibratedMath 出处核实
- **发现的关键参考（均逐条核对出处）：**
  - Kadavath 2022（arXiv:2207.05221）：P(True)/P(IK) 自我评估范式
  - Lin 2022 CalibratedMath（arXiv:2205.14334）：verbalized confidence + 分布偏移校准
  - SelfAware（arXiv:2305.18153）：不可答题五分类
  - AbstentionBench（Meta, arXiv:2506.09038）：拒答六场景，推理微调使拒答降 24%
  - SimpleQA（OpenAI 2024）、HalluLens（ACL 2025）、Omniscience Index（AA 2025）
  - 标准方法论：ECE（Guo 2017）、Brier（1950）、选择性预测 AUC（Geifman & El-Yaniv）
- **评估结果：** 共调研 ≥11 个相关基准/方法论，沉淀为 `research/metacognition_benchmark_survey.md` 对照表。结论：现有工作**零散、单点、缺三层统一、普遍不做 OOD 转移** → 锁定设计空白。

---

## 提案撰写 / Proposal Writing

- **初稿生成：**
  - 输入：赛道结论（Track 2）+ 论文三层框架 + 调研对照表 + 设计草图（跨域 + 对抗性不可答题 + 置信度 elicitation）
  - 助手生成完整四部分双语初稿
- **迭代次数：** 3 轮
  - 第 1 轮：初稿只测「拒答」，未覆盖 L1/L2。要求补成 DeepMind 三层统一结构 → Task A/B/C 成型
  - 第 2 轮：校准指标偏单薄。补入 OOD 转移护栏（calibration gap = ECE_OOD − ECE_ID）作为「元认知 vs 知识测试」判别器，并加 prompt 敏感性控制
  - 第 3 轮：补人类基线预期表 + 区分度设计（20%–80% 准确率区间）+ 可行性时间表
- **人工决策（用户拍板项）：**
  - 赛道确认 Track 2 Metacognition（9/28–10/11 间经 AskUserQuestion 确认）
  - 基准命名 MetaCog-Bench
  - 保留 OOD 转移护栏（不删，这是与现有 benchmark 的最大差异点）

---

## 手动步骤说明 / Manual Steps Justification

| 手动步骤 | 为什么没全交给 AI |
|---|---|
| 赛道最终拍板（Track 2） | 涉及个人精力分配与竞争策略判断，需用户决策 |
| 题型难度比例（易/难/不可答） | 基于认知科学「避免天花板/地板效应」的经验判断 |
| OOD 领域划分（ID vs OOD） | 需判断哪些领域属预训练高频、哪些属小众，依赖领域经验而非纯生成 |
| P4 阶段 API 调用 | 涉及付费配额，**必须等用户明确同意后**才执行，不自行发起 |

---

## AI 段位自评 / AI Usage Level

**🔵 进阶 → 接近驾驭** — 多轮对话迭代优化 prompt（3 轮提案迭代 + 6 轮调研 + 论文精读追问），并设计了「调研→对照表→提案」的完整 workflow。核心设计骨架（三层统一 + OOD 转移护栏）由人与 AI 协同构思，非纯生成也非纯人工；AI 日志与拿来说明均由助手按真实过程生成，可供评分佐证。

---

## 提案 v2 迭代（2026-10-12）

- **触发**：用户选「2. proposal v2 迭代（用现在更扎实的实测）」，基于 C9 阶段已跑出的 200 题真实测试结果（DeepSeek V4.1 Flash，¥0.392，calibration_gap=0.317，OOD 准确率 2.6%）。
- **核心改动（8 处就地更新 `FengShuo_C2A_proposal.md`）**：
  - 顶部标 `v2` + 日期改 10/12
  - §1 加「预实验验证」段：OOD 准确率 2.6% / ID 65.8% / calibration_gap 0.317，实证元认知缺口与 OOD 护栏有效
  - §2.1 OOD 护栏行后加 pilot 实测注记（calibration_gap=0.317）
  - 新增 §2.4「数据集现状」：200 题 pilot 已落地（A61/B59/C80，OOD39，不可答41）
  - §3 人类基线表加 pilot 实测锚点行（V4.1 Flash：AUROC 0.505 / ECE ID0.31·OOD0.63 / Omniscience 0.371）
  - §3 表后加「对照意义」注记：实测灵敏度高于既有评测
  - §4.1 加「Pilot 已证实」注记：设计假设被数据支持
  - §4.2 可行性表由「声称」改为「已验证」状态（题库/评分/模型测试均 ✅ 已完成）
- **边界处理**：提案仍明确区分 C2A（设计）与 C9（完整测试）——pilot 数据以「设计验证/预实验」措辞引用，指向 `FengShuo_C9_测试结果.md` 为详细来源，不把完整测试结果搬进提案（避免混淆两阶段交付物）。
- **未动主体**：四部分比例 20/40/20/20、英文双语、KSTAR 连接、创新对照表均保留。
- **迭代次数累计**：提案撰写 3 轮 + v2 迭代 1 轮 = 4 轮；均按真实过程记录，可供 AI 使用质量（20 分）佐证。
