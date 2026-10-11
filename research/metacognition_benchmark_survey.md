# 元认知已有 Benchmark 调研对照表（拿来主义底座）

> 用途：为 C2A 提案「拿来说明」与「基准设计」提供真实可查的文献底座
> 调研方式：WebSearch × 6 轮（2026-10-11），逐条核对 arXiv / 论文出处
> 结论：现有工作**零散、单点、缺三层统一框架、普遍不做 OOD 转移** → 这是我们的切入空白

图例：L1=元认知知识 / L2=监控校准 / L3=控制(拒答) ｜ ✅=测了前沿模型 ｜ ⚠️=局限

---

## 一、逐条对照表（≥10 项）

| # | 名称 / 出处 | 测什么(层) | 任务格式 | 评分指标 | 局限(⚠️) | 测前沿模型? | 我的借鉴点 |
|---|---|---|---|---|---|---|---|
| 1 | **Kadavath et al. 2022**「Language Models (Mostly) Know What They Know」arXiv:2207.05221 | L1+L2 | MC/TF 题 + 开放式；问 P(True)/P(IK) | 校准曲线、ECE、Brier | ⚠️ 主要大模型家族；P(IK) 在新任务上校准差 | ✅ GPT-3 族 | 「先答后评」「预测自己能否答对」范式 → Task A 原型 |
| 2 | **Lin, Hilton, Evans 2022**「Teaching Models to Express Their Uncertainty in Words」(CalibratedMath) arXiv:2205.14334 | L2 | 21 类程序生成算术题，答+给置信度 | MSE/MAD、verbalized vs logit 校准 | ⚠️ 仅数学单域；需微调；**不做 OOD 转移** | ✅ GPT-3 | 「verbalized confidence + 分布偏移测校准」方法 → Task B 方法 |
| 3 | **Yin et al. 2023** SelfAware arXiv:2305.18153（复旦/新国立） | L1+L3(自知) | 1032 不可答 + 2337 可答，5 类；文本相似度判是否表达不确定 | F1（不确定表达） | ⚠️ 仅文本相似度、无置信度、无校准、无 OOD、无分层 | ✅ 20 个 LLM（GPT-4 F1 75.47% vs 人 84.93%） | 「不可答题五分类 + 可答对照」题型 → Task C 题型池 |
| 4 | **Kirichenko et al. 2025** AbstentionBench（FAIR@Meta）arXiv:2506.09038 | L3 | 20 数据集：未知答案/欠定/假前提/主观/过期信息 | 拒答召回(recall~0.6) | ⚠️ 只测拒答、无置信度校准、无 L1、OOD 非重点 | ✅ 20 个前沿 LLM | 「推理微调反而使拒答降 24%」关键发现 → Task C 设计动机 |
| 5 | **OpenAI 2024** SimpleQA | L3 | 4326 短事实问答，单正确答案 | correct/incorrect/not attempted 三类 | ⚠️ 仅 4k 短事实、已饱和（GPT-4o+搜索~90%，GPT-5>95%） | ✅ GPT-4o/5 | 「把拒答作为一等公民结果」的计分哲学 → Task C 计分 |
| 6 | **Bang et al. 2025** HalluLens（ACL 2025） | L2+L3 | 短 QA + 长文生成 + 不存在实体检测 | 幻觉率 + **错误拒答率(false refusal)** | ⚠️ 聚焦幻觉/事实性，非三层元认知 | ✅ GPT-4o(误拒4.13%) / Llama-3.1-8B(>83%) | 「同时报幻觉率与误拒率」双向指标 → Task C 双向指标 |
| 7 | **Artificial Analysis 2025** Omniscience Index（2025-11） | L3 综合 | 多域问答 | +1 正确 / −1 错误 / 0 拒答 的合成分 | ⚠️ 单一合成分、无分层、无校准曲线、无 OOD | ✅ 36 个前沿模型（仅 3 个 >0） | 「拒答不扣分、猜错重罚」的计分公式 → Task C 核心计分 |
| 8 | **Guo et al. 2017**「On Calibration of Modern Neural Networks」ICML（arXiv:1706.04599） | L2 方法论 | — | **ECE** 定义 | 方法论，非 benchmark | — | ECE 作为 Task B 主指标 |
| 9 | **Brier 1950**「Verification of Forecasts…」 | L2 方法论 | — | **Brier Score** | 方法论 | — | Brier 作为 Task B 次指标（对极端置信敏感） |
| 10 | **Geifman & El-Yaniv** Selective Classification/Prediction（NeurIPS'17 / JMLR'19） | L2+L3 方法论 | — | **risk-coverage 曲线、AUC** | 方法论 | — | 选择性预测 AUC → 跨 Task B/C 的统一区分度指标 |
| 11 | **Metacognition in LLMs: Foundations, Progress…** arXiv:2607.11881（2026 综述） | 全景 | 综述 CogEdit/MetaMedQA/ObjexMT/AwareXtend 等 | — | ⚠️ 指出现有基准「零散、受通用能力混淆、缺稳定现象」 | — | 佐证「缺口大、需统一框架」的论点；Ackerman2025/Prasad2025 范式可后续扩展 |

---

## 二、共性缺口（= 我们的设计空白）

1. **无统一三层框架**：现有工作单点打洞（要么只校准 L2，要么只拒答 L3），没有把 L1/L2/L3 放进一个 benchmark 同时测。
2. **普遍不做 OOD 转移**：这是论文点名的最大坑。SelfAware/CalibratedMath/AbstentionBench 都在「模型熟悉分布」上测，无法区分「元认知」与「记忆匹配」。
3. **缺 prompt 敏感性控制**：幻觉研究表明 prompt 架构可大幅改变结果（single number 误导）。现有基准基本只报固定模板单值。
4. **L1 最弱**：「模型能否预测自己会不会答对」除 Kadavath 外极少系统测量。

→ 我们的 MetaCog-Bench 正好补这四点：三层统一 + 显式 OOD 转移 + prompt 敏感性报告 + L1 自我预测。

---

## 三、可直接复用的题型/数据池

- 不可答题五分类（SelfAware）：无科学共识 / 想象推测 / 完全主观 / 变量过多 / 哲学类
- 拒答六场景（AbstentionBench）：欠定意图 / 主观 / 假前提 / 过期数据 / 欠定上下文 / 答案未知
- 不存在实体检测（HalluLens NonExistentEntities）：识别并拒答关于虚构实体的问题
- 程序生成题（CalibratedMath）：可无限生成、难度可调、无泄漏风险

---

*整理人：冯硕 ｜ 日期：2026-10-11 ｜ 用途：C2A 提案「拿来说明」+「基准设计」论据*
