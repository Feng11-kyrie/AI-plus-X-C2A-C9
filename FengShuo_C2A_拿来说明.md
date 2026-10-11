# 拿来说明 / Attribution

**作者 / Author:** Feng Shuo（冯硕）
**挑战 / Challenge:** C2A — Track 2 Metacognition
**日期 / Date:** 2026-10-11

---

## 借鉴来源 / References

| 来源 / Source | 链接 / Link | 核心思想 / Key Idea |
|---|---|---|
| DeepMind AGI 框架 (2026) | [PDF](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/measuring-progress-toward-agi/measuring-progress-toward-agi-a-cognitive-framework.pdf) | 10 个认知能力 + 五缺口赛道；§7.7 元认知三层（knowledge/monitoring/control）+ OOD 转移约束 |
| Kadavath et al. 2022 | [arXiv:2207.05221](https://arxiv.org/abs/2207.05221) | P(True)/P(IK) 自我评估范式；模型能预测自己能否答对 |
| Lin, Hilton, Evans 2022 (CalibratedMath) | [arXiv:2205.14334](https://arxiv.org/abs/2205.14334) | verbalized confidence + 分布偏移下测校准 |
| Yin et al. 2023 (SelfAware) | [arXiv:2305.18153](https://arxiv.org/abs/2305.18153) | 不可答题五分类（无共识/主观/推测/变量多/哲学）+ 可答对照 |
| Kirichenko et al. 2025 (AbstentionBench) | [arXiv:2506.09038](https://arxiv.org/abs/2506.09038) | 拒答六场景；推理微调使拒答降 24% |
| OpenAI 2024 (SimpleQA) | [openai.com](https://openai.com/index/introducing-simpleqa/) | 把拒答作为一等公民结果（correct/incorrect/not attempted） |
| Bang et al. 2025 (HalluLens) | ACL 2025 | 幻觉率 + 错误拒答率 双向指标 |
| Artificial Analysis 2025 (Omniscience Index) | [artificialanalysis.ai](https://artificialanalysis.ai) | +1 正确 / −1 错误 / 0 拒答 的合成分 |
| Guo et al. 2017 (ECE) | [arXiv:1706.04599](https://arxiv.org/abs/1706.04599) | Expected Calibration Error 定义 |
| Geifman & El-Yaniv (Selective Prediction) | NeurIPS'17 / JMLR'19 | risk-coverage 曲线、选择性预测 AUC |
| Metacognition in LLMs (综述) | [arXiv:2607.11881](https://arxiv.org/abs/2607.11881) | 指出现有元认知基准零散、受通用能力混淆、缺稳定现象 |

---

## 拿来的部分 / Adopted

### 从 DeepMind 框架拿了什么
- **拿了：** 元认知三层结构（L1 知识 / L2 监控 / L3 控制）作为 benchmark 的唯一骨架；以及「必须做 OOD 转移，否则退化成知识测试」的设计约束
- **为什么好用：** 这是挑战的官方理论依据，用它的框架 = 直击评分「基准设计 25 分」与「研究严谨性 20 分」

### 从 Kadavath 2022 拿了什么
- **拿了：** 「先答后评」「让模型预测自己能否答对（P(IK)）」的范式
- **为什么好用：** 直接落成 Task A（L1 元认知知识）的自我预测题型，且有现成指标（meta-accuracy）

### 从 CalibratedMath (Lin 2022) 拿了什么
- **拿了：** 「作答 + 给 verbalized 置信度」的任务形式，以及用分布偏移测校准的方法论
- **为什么好用：** 零样本即可 elicitate 置信度，不需微调，实现最轻

### 从 SelfAware + AbstentionBench 拿了什么
- **拿了：** 不可答题的分类体系（SelfAware 五类 / AbstentionBench 六场景）作为 Task C 题型池
- **为什么好用：** 题型经过验证、可直接复用，省去从零造题

### 从 Omniscience Index + HalluLens 拿了什么
- **拿了：** 「+1/−1/0 拒答计分」公式（Omniscience）与「同时报错误拒答率」的双向指标（HalluLens）
- **为什么好用：** 用单一合成分 + 一个安全护栏，简洁且可解释

---

## 去掉的部分 / Removed

| 来源 | 他们做了什么 | 我不要 | 原因 |
|---|---|---|---|
| CalibratedMath | 仅数学单域、需监督微调 | 去掉单域限制与微调依赖 | 单域无法证明跨域元认知；微调增加实现成本与泄漏风险 |
| SelfAware | 仅文本相似度 F1、无置信度/校准/OOD | 去掉纯文本相似度判据 | F1 无法量化校准质量，也不区分「真知道」与「套话拒答」 |
| AbstentionBench | 仅测拒答（L3），无 L1/L2 | 去掉「只测拒答」的窄口径 | 与 DeepMind 三层框架不符，无法完整刻画元认知 |
| SimpleQA | 仅 4k 短事实、已饱和 | 去掉其作为主测试集 | 已接近天花板（GPT-5+搜索 >95%），无区分度 |
| 各单点基准 | 只在熟悉分布上测 | 去掉「无 OOD 转移」的做法 | 论文点名的最大坑：熟悉域校准 ≠ 元认知 |

---

## 我的改进 / My Improvements

### 改进 1：三层统一框架（核心创新）
- **现有方法的问题：** 现有工作单点打洞——要么只校准（L2），要么只拒答（L3），没有把 L1/L2/L3 放进一个 benchmark 同测
- **我的改进：** 以 DeepMind 三层为唯一骨架，Task A/B/C 分别映射 L1/L2/L3，首次给出**统一**的元认知评测
- **效果：** 一个分数体系同时覆盖「知不知道自己知道」「置信度准不准」「不确定时处不处理」，信息量是单点基准的 3 倍

### 改进 2：显式 OOD 转移护栏（差异化关键）
- **现有方法的问题：** 几乎都在模型熟悉分布上测校准，无法区分「元认知」与「记忆匹配」
- **我的改进：** 强制把领域分为 ID（预训练高频）与 OOD（小众/罕见），报告 **calibration gap = ECE_OOD − ECE_ID** 作为「元认知 vs 知识测试」的判别器
- **效果：** 只在 ID 校准、OOD 崩溃的模型被直接暴露，真正测到元认知能力

### 改进 3：Prompt 敏感性控制
- **现有方法的问题：** 幻觉研究表明 prompt 架构可大幅改变结果，单一数值会误导
- **我的改进：** 固定标准 prompt + 额外 3 套模板复测，报告方差
- **效果：** 结果更可信，直接提升「研究严谨性 20 分」

### 改进 4：双向指标 + 选择性预测统一
- **现有方法的问题：** 多数只报单向（要么幻觉率，要么拒答率）
- **我的改进：** Task C 同时报 Omniscience Index 与 false-refusal rate；跨 Task B/C 用选择性预测 AUC 统一区分度
- **效果：** 捕捉「拒答一切」与「瞎答一切」两种失败模式，避免单一指标误导
