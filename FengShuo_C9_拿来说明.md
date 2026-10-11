# 拿来说明 · C9 测试阶段 / Provenance — C9 Test Stage

**作者 / Author:** Feng Shuo（冯硕）
**日期 / Date:** 2026-10-11
**承接:** `FengShuo_C2A_拿来说明.md`（提案阶段）

> 说明本阶段（模型测试 + 评分 + 复盘）中真实借鉴的来源、拿来的部分、去掉的部分，以及自主改进。

---

## 1. 真实来源 / Real Sources

| 来源 | 拿来什么 | 类型 |
|---|---|---|
| **DeepSeek 官方 API**（`api.deepseek.com`，模型 `deepseek-flash` = V4.1 Flash） | 云端推理算力与模型权重 | 商业服务（用户付费授权，¥3 上限，实测 ¥0.392） |
| **Kadavath 2022**（arXiv:2207.05221） | Task A 的 P(True)/P(IK) 自我预测提问范式 | 方法范式 |
| **Lin 2022 CalibratedMath**（arXiv:2205.14334） | verbalized confidence + 分布偏移校准思路 → Task B | 方法 |
| **Guo 2017**（arXiv:1706.04599） | ECE（期望校准误差）定义与分桶实现 | 标准指标 |
| **Brier 1950** | Brier Score 概率校准误差 | 标准指标 |
| **Artificial Analysis 2025 — Omniscience Index** | Task C 的 +1/−1/0 计分与「知不知道」聚合 | 计分设计 |
| **HalluLens（ACL 2025）** | 错误拒答率（false-refusal）双向指标 | 双向指标 |
| **Geifman & El-Yaniv** | 选择性预测 risk-coverage AUC | 附加指标 |
| **DeepMind 2026** | 三层框架 + OOD 转移约束（全局骨架，同提案） | 理论骨架 |
| **SelfAware / AbstentionBench** | 不可答题题型与拒答场景（同提案，用于题库生成） | 题型 |

---

## 2. 拿来 / 去掉 / 改进 / Borrowed / Dropped / Improved

### 拿来（直接复用）
- 评分指标的**数学定义**：ECE、Brier、Omniscience Index、AUROC、false-refusal 均按文献标准实现，未自创。
- **API 调用范式**：OpenAI-compatible 的 `/chat/completions` + Bearer key，标准用法。
- **题型与 OOD 划分**：沿用提案阶段基于 SelfAware/AbstentionBench 生成的题库（200 题）。

### 去掉（刻意不沿用）
- **Kaggle 路线**：原计划 Kaggle 免费 GPU 跑开源权重，用户授权后改 API 路线 B，省去 Kaggle Notebook 搭建。
- **子串判分的过度宽松**：未沿用「任意子串命中即判对」，已在 AAR 标注为局限，计划下一步升级语义判分。

### 改进（自主做的）
- **`meta_auroc` 算法重写**：初版二分查找在浮点边界失灵（0.99 比较），改为定义式暴力配对计数，经手算交叉验证（0.505）。
- **预算闸 + dry-run**：在调用脚本内置 ¥2.7 硬上限与 0 花费校验模式，保证「不超用户授权额度」。
- **OOD 转移护栏落地为实测**：把提案的 `calibration_gap = ECE_OOD − ECE_ID` 从设计变成实测（0.317），并验证其区分力（OOD 准确率 2.6% vs ID 65.8%）。

---

## 3. 学术诚信声明 / Integrity Note

- 所有引用 benchmark / 指标均来自可核实出处（arXiv / 会议 / 官方文档），无虚构文献。
- 测试数据由程序生成并标注 `is_ood` / `is_answerable`，未使用任何受版权保护的现成测试集原文。
- 评分脚本 bug 及修复已在 `FengShuo_C9_AAR.md` 与 `src/scoring.py` 注释中**公开披露**，数字可复算。
- API key 仅存于用户本机 600 权限文件，未进仓库、未进聊天、未上传任何第三方。
