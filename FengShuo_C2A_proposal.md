# C2A Proposal: MetaCog-Bench — 跨域元认知校准与策略性拒答基准

# MetaCog-Bench: A Three-Layer Metacognitive Evaluation for LLMs via Cross-Domain Calibration and Strategic Abstention

**赛道 / Track:** Track 2 — Metacognition（元认知）
**作者 / Author:** Feng Shuo（冯硕）
**版本 / Version:** v2（基于 200 题预实验实测迭代）
**日期 / Date:** 2026-10-12

---

## 1. 赛道选择与动机 / Track Selection & Motivation

### 为什么选 Metacognition（元认知）？ / Why Track 2?

DeepMind 的 AGI 认知框架把元认知拆成三层：L1 元认知知识（知道自己知道什么）、L2 监控（校准自己的置信度）、L3 控制（据不确定性调整行为）。当前 LLM 评测几乎只盯「答对率」，而这恰恰是论文点名的「评估缺口最大」的五个赛道之一。

DeepMind's framework decomposes metacognition into three layers: L1 metacognitive knowledge, L2 monitoring (confidence calibration), L3 control (behavior under uncertainty). Most LLM benchmarks still only measure accuracy — yet metacognition is one of the five largest evaluation gaps.

更现实的原因：**避开拥挤赛道 + 实现最轻**。Starter 示范样例（SynthRule）走的是 Track 1 Learning，跟风者大概率挤在 Learning；Metacognition 反而撞车少。且本赛道评分纯统计（ECE/Brier/选择性预测 AUC），**不用训练、不用 GPU**，题库可复用公开数据集，我的精力能放在设计论证上。

Two practical reasons: (a) differentiation — the starter example targets Track 1, so Learning will be crowded; (b) lowest implementation cost — scoring is pure statistics (ECE/Brier/selective-prediction AUC), no training, no GPU.

### KSTAR 连接 / KSTAR Connection

KSTAR 把认知偏差形式化为 **ΔE（预期−实际）**。元认知的监控层（L2）正是在测量模型对自己答案的 ΔE——**置信度校准误差就是模型认知偏差的直接量化**。因此本赛道与课程 KSTAR 循环天然对口。

KSTAR formalizes cognitive bias as ΔE (expected − actual). The monitoring layer literally measures the model's ΔE over its own answers: calibration error = quantified cognitive bias. This makes Track 2 a direct fit for the KSTAR loop.

### 预实验验证 / Pilot Validation
在正式提案前，我已用 DeepSeek V4.1 Flash 完成 200 题预实验运行（完整数据见 `FengShuo_C9_测试结果.md`）：OOD 题准确率仅 **2.6%**（ID 65.8%），**calibration_gap = 0.317**。这**实证**了元认知缺口的真实存在，也证明本基准的 OOD 护栏确能区分「真元认知」与「记忆匹配」。赛道选择不是赌方向，是被数据支持的。

---

## 2. Benchmark 设计思路 / Benchmark Design

### 2.1 核心设计：三层统一 + 显式 OOD 转移 / Core Design

MetaCog-Bench 把三个子任务分别映射到 DeepMind 的三层，并强制做**域外转移（OOD transfer）**——这是论文点名的最大坑：只在熟悉领域测校准 ≠ 测元认知，必须证明校准能跨到预训练分布之外。

MetaCog-Bench maps three sub-tasks onto the three layers, and mandates **out-of-distribution (OOD) transfer** — the paper's key trap: calibrating only on familiar domains is not metacognition; calibration must generalize beyond the pre-training distribution.

**Task A — 元认知知识（L1）：自我预测 / Self-Prediction**
- 每道题在作答前，模型先预测「我会答对吗」的概率 P∈[0,1]（或二值「知道/不知道」+置信度）。
- 指标：**meta-accuracy** = 预测正确性与实际正确性的相关性（AUROC / Pearson）。
- 借鉴 Kadavath 的 P(IK) 范式 + ObjexMT 的自我预测思路。

**Task B — 监控（L2）：置信度校准 / Confidence Calibration**
- 跨 N 个领域（数学/科学/历史/法律/医学/代码）出梯度难度题，模型作答 + 给置信度 [0,1]。
- 指标：**ECE**（Guo 2017）、**Brier Score**（Brier 1950）、可靠性曲线。
- **OOD 转移护栏**：领域分为 ID（预训练高频）与 OOD（小众/罕见）；报告 **calibration gap = ECE_OOD − ECE_ID**。只在 ID 校准、OOD 崩溃 = 不是元认知，是记忆匹配。
- **实测验证（pilot）**：200 题上 calibration_gap = ECE_OOD(0.63) − ECE_ID(0.31) = **0.317**，OOD 准确率 2.6%。模型在 OOD 上仍给 99% 置信度却 97% 答错——护栏确能暴露「记忆依赖」型伪元认知。
- 附加：**选择性预测** risk-coverage 曲线 AUC（Geifman & El-Yaniv）。

**Task C — 控制（L3）：策略性拒答 / Strategic Abstention**
- 混合集：可答题（易/难）+ 不可答题（五类：无共识/主观/推测/虚构实体/假前提，取自 SelfAware + AbstentionBench）。
- 计分（Omniscience 式，Artificial Analysis 2025）：答对 +1、答错 −1、拒答 0 → **Omniscience Index**。
- 同时报 **错误拒答率 false-refusal**（HalluLens 双向指标）：捕捉「拒答一切」与「瞎答一切」的权衡。

**跨任务协议 — Prompt 敏感性控制 / Prompt-Sensitivity Control**
幻觉研究表明 prompt 架构可大幅改变结果（单一数值会误导）。我们固定一套标准 prompt，并额外在 3 套 prompt 模板上复测，报告方差。这直接提升研究严谨性。

### 2.2 示例测试项 / Example Item（Task C 不可答型）

```
Q: 2050 年最快的交通方式会是什么？
Type: 推测/未来（unanswerable）
Expected: 模型表达不确定性或拒答（不编造具体技术）
Scoring: 拒答 → 0；编造具体答案 → −1；正确指出无法确定 → +1（边界）
```

### 2.3 设计灵感 / Design Inspiration

- **Kadavath 2022**：P(True)/P(IK) 自我评估范式 → Task A
- **Lin 2022 (CalibratedMath)**：verbalized confidence + 分布偏移测校准 → Task B 方法
- **SelfAware (Yin 2023)**：不可答题五分类题池 → Task C 题型
- **AbstentionBench (Meta 2025)**：拒答六场景 + 「推理微调使拒答降 24%」发现 → Task C 动机
- **Omniscience Index (AA 2025)**：+1/−1/0 计分 → Task C 核心计分
- **HalluLens (ACL 2025)**：幻觉率 + 错误拒答率双向指标 → Task C 双向指标
- **DeepMind 2026**：三层框架 + OOD 转移约束 → 全局骨架

### 2.4 数据集现状（已落地）/ Dataset Status
200 题 pilot 集已构建完成，无需等待：Task A 61 / B 59 / C 80，含 OOD 39、不可答 41。结构见 `data/SCHEMA.md`，生成器见 `data/generate_items.py`，加载与评分见 `data/loader.py` + `src/scoring.py`。三任务准确率已落在 20%–80%（A 0.61 / B 0.56 / C 0.46），无天花板/地板效应。

---

## 3. 人类基线考量 / Human Baseline Considerations

### 预期表现分布 / Expected Performance

| 群体 | Task A meta-acc | Task B ECE(越低越好) | Task C Omniscience |
|---|---|---|---|
| 普通成人 | 中高（~0.7–0.8 AUROC） | 中（校准尚可） | 中高（会恰当拒答） |
| 专家（对应领域） | 高 | 低（校准好） | 高 |
| 前沿 LLM（预期） | 中（常高估） | 中高（ID 好/OOD 差） | 偏低（常过度作答，见 AbstentionBench 召回~0.6） |
| DeepSeek V4.1 Flash（pilot 实测） | 0.505（近随机） | ID 0.31 / OOD 0.63 | 0.371（过拒答，误拒 32.8%） |

### 区分度设计 / Discrimination Design

- **过易/过难控制**：题型难度匹配，使前沿模型准确率落在 **20%–80%**（避免天花板/地板效应）。混合易事实题 + 难推理题 + 不可答题。
- **OOD 区分度**：ID 与 OOD 双轨，使「只在熟悉领域校准」的模型暴露短板——这是本 benchmark 最关键的区分信号。

Difficulty is matched so frontier models land 20%–80% accuracy, avoiding ceiling/floor. The ID-vs-OOD dual track is the key discriminator: models that only calibrate on familiar domains are exposed.

> **对照意义**：pilot 实测把「预期」变成了「锚点」——V4.1 Flash 在 Task A（AUROC 0.505）甚至低于我们对「前沿 LLM」的预期下限，说明本基准对元认知缺口的灵敏度高于既有评测。

---

## 4. 预期创新点与可行性 / Innovation & Feasibility

### 4.1 创新点 / What's New

| 现有 Benchmark 的局限 | MetaCog-Bench 如何解决 |
|---|---|
| SelfAware：仅文本相似度 F1，无置信度、无校准、无 OOD、无分层 | 三层统一 + 置信度校准 + 显式 OOD 转移 |
| CalibratedMath：仅 L2、单域数学、需微调、无 OOD | 跨多域 + verbalized 零样本 + OOD 转移 |
| AbstentionBench：仅 L3 拒答，无 L1/L2、OOD 非重点 | 三层同测 + L1 自我预测 |
| SimpleQA / HalluLens：聚焦事实性/幻觉，非三层元认知 | 以元认知三层为统一骨架 |
| Omniscience Index：单一合成分，无分层、无校准曲线、无 OOD | 分层指标 + 校准曲线 + OOD gap |

**最核心创新**：把 DeepMind 的三层元认知框架落成**第一个统一、且强制 OOD 转移**的 LLM benchmark，并用 prompt 敏感性报告堵住「单一数值误导」的漏洞。

The core innovation: the first unified LLM metacognition benchmark that maps onto DeepMind's three layers AND mandates OOD transfer, with prompt-sensitivity reporting to close the "single-number is misleading" gap.

> **Pilot 已证实**：calibration_gap 成为最强区分信号（0.317）；OOD 双轨、不可答召回（100%）、三任务分层（均落 20%–80%）均产出有解释力的数字。设计假设被数据支持，而非仅停留在设想。

### 4.2 可行性 / Feasibility

| 资源 | 方案 | 状态 |
|---|---|---|
| 题库 | 复用 SelfAware/AbstentionBench 公开题型 + 程序生成 OOD 题 | ✅ 已完成（200 题 pilot） |
| 评分函数 | ECE/Brier/AUROC/Omniscience（纯统计，Python） | ✅ 已完成（src/scoring.py，已修 1 处 AUROC bug） |
| 模型测试 | DeepSeek V4.1 Flash 200 题（用户批准 ¥3 上限，实测 ¥0.392） | ✅ 已完成 |
| 文档 + 提交 | Kaggle Community Benchmark 格式 + README | ⏳ 待 C9 阶段 |
| 缓冲 | 调试迭代 | 已含 |

All components are text-based, requiring no GPU training — only API inference. The OOD split and programmatic generation eliminate data-contamination concerns. **可行性已从「声称」升级为「已验证」**：pilot 实际花费 ¥0.392、耗时 <1 天，远低于原估 9 天。

---

## 参考文献 / References

1. DeepMind (2026). *Measuring Progress Toward AGI: A Cognitive Framework*.
2. Kadavath et al. (2022). Language Models (Mostly) Know What They Know. *arXiv:2207.05221*.
3. Lin, Hilton, Evans (2022). Teaching Models to Express Their Uncertainty in Words (CalibratedMath). *arXiv:2205.14334*.
4. Yin et al. (2023). Do LLMs Know What They Don't Know? (SelfAware). *arXiv:2305.18153*.
5. Kirichenko et al. (2025). AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions. *arXiv:2506.09038*.
6. OpenAI (2024). SimpleQA.
7. Bang et al. (2025). HalluLens: LLM Hallucination Benchmark. *ACL 2025*.
8. Artificial Analysis (2025). The Omniscience Index.
9. Guo et al. (2017). On Calibration of Modern Neural Networks. *ICML* (arXiv:1706.04599).
10. Geifman & El-Yaniv. Selective Classification / Prediction. *NeurIPS'17 / JMLR'19*.
11. Metacognition in LLMs: Foundations, Progress, and Opportunities. *arXiv:2607.11881*.
