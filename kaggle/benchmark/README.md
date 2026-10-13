# MetaCog-Bench · Kaggle Benchmark 制品

> **A Three-Layer Metacognitive Evaluation for LLMs via Cross-Domain Calibration and Strategic Abstention**
> 衡量大模型「元认知」能力的基准：知道自己知道什么（L1）、校准自己的置信度（L2）、在不确定时策略性拒答（L3）。
> 赛道：AI+X Elite 20 · Track 2 Metacognition（C2A-C9 挑战）

本目录是可直接上传 Kaggle 的 **Community Benchmark 制品**：公开题集 + 金标准 + 竞赛评分脚本 + 入门基线笔记。本地即可端到端运行验证。

---

## 1. 基准设计（一句话版）

| 任务 | 对应层 | 模型要做什么 | 核心指标 |
|---|---|---|---|
| **Task A** | L1 元认知知识 | 答题前先预测「我会答对吗」P∈[0,100] | `meta_auroc`（自我预测区分成败的能力） |
| **Task B** | L2 监控校准 | 跨领域作答并给置信度 [0,100] | `ECE_ID` / `ECE_OOD` / **`calibration_gap = ECE_OOD − ECE_ID`** |
| **Task C** | L3 策略性拒答 | 混合可答/不可答题，不可答则拒答 | `Omniscience Index` / `false_refusal_rate` |

**最关键区分信号 = `calibration_gap`**：只在熟悉领域（ID）校准、到了预训练分布之外（OOD）就崩的模型，不是真元认知，只是记忆匹配。pilot（DeepSeek V4.1 Flash，200 题）实测 `calibration_gap = 0.317`，OOD 准确率仅 2.6%——护栏确能暴露伪元认知。

> ⚠️ **Prompt 敏感性已实测**：固定本基准的标准 prompt（见 `benchmark_utils.STANDARD_PROMPT`），并在 3 套变体 prompt 上复测，4 套下 `calibration_gap` 均为正、信号稳健（详见 `FengShuo_C9_prompt敏感性报告.md`）。正式版**固定标准 prompt**，请勿随意改措辞。

---

## 2. 文件清单

```
kaggle/benchmark/
├── README.md                      # 本文件
├── benchmark_utils.py             # 共享：标准 prompt / 解析器 / 判分（零依赖）
├── build_package.py               # 从源数据重建下方 dataset/*（可重跑）
├── scoring.py                     # 竞赛评分脚本（提交 → 排行榜分数）
├── getting_started.ipynb          # Kaggle 入门/基线笔记（免 API 演示全流水线）
└── dataset/
    ├── metacog_bench.csv          # 【公开】题集：id, task, domain, prompt（无金标准）
    ├── ground_truth.csv            # 【隐藏】金标准：id, gold_answer, is_ood, is_answerable, unanswerable_reason
    ├── sample_submission.csv       # 提交格式示例（源自 DeepSeek V4.1 Flash 真实预测）
    └── public_private_split.csv    # 公开/私有榜切分（按任务分层抽样）
```

---

## 3. 提交格式（submission.csv）

每行一道题，共 200 行 + 表头：

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | string | 题号，须与 `metacog_bench.csv` 一致 |
| `answer_text` | string | 模型最终答案；拒答写 `I CANNOT ANSWER` |
| `confidence` | int 0–100 | 对「答案正确」的置信度（Task B） |
| `self_pred` | int 0–100 | 预测「自己会答对吗」的概率（Task A） |
| `can_answer` | YES / NO | 是否作答；NO = 拒答（Task C） |

示例（来自 `sample_submission.csv` 第一行）：
```csv
id,answer_text,confidence,self_pred,can_answer
A-id-001,156,99,99,YES
```

---

## 4. 评分（scoring.py）

评分端**自行**用 `ground_truth.csv` 判分（不信任提交里的正确性），再调用已验证的 `src/scoring.py`。

```bash
# 本地验证（默认指向 dataset/ 下金标准与切分）
python3 kaggle/benchmark/scoring.py \
    --submission kaggle/benchmark/dataset/sample_submission.csv \
    --out scores.csv
```

输出 `scores.csv`（单行排行榜条目）：各任务原始指标 + `public_metacog_score` / `private_metacog_score`。

**单一排行榜合成分 `metacog_score`（0–100，越高越好，仅用于排序）：**

```
metacog_score = 100 × (0.30·A + 0.35·B + 0.20·C + 0.15·G)

A = clamp((meta_auroc − 0.5) / 0.5, 0, 1)        # Task A：0.5→0, 1.0→1
B = clamp(1 − ECE_overall, 0, 1)                  # Task B：整体校准越好越高
C = clamp((Omniscience_Index − (−0.5)) / 1.5, 0, 1)  # Task C：[-0.5,1]→[0,1]
G = clamp(calibration_gap / 0.5, 0, 1)            # OOD 护栏：>0.5 封顶
```

> 设计取舍：合成分只用于排座次；**全部任务原始指标一并公开**，避免「单一数字误导」（见提案 §2.1）。

**本地验证已复现 pilot 实测：** `calibration_gap=0.317`、`ECE_ID=0.31`、`ECE_OOD=0.63`、`meta_auroc=0.505`、`Omniscience=0.371`、`false_refusal=0.328` —— 与 `FengShuo_C9_测试结果.md` 一致，证明制品正确可运行。

---

## 5. 在 Kaggle 上发布（Dataset + Notebook）

1. **建 Dataset**：新建 Kaggle Dataset，上传 `dataset/` 下全部 4 个 CSV（`metacog_bench.csv` 公开；`ground_truth.csv` / `public_private_split.csv` 在评分端使用，参赛者可不下载）。
2. **建 Notebook（入门基线）**：复制 `getting_started.ipynb`，`Add Data` 关联上一步 Dataset，点 Run 即可看到全流水线 + 榜单分数（默认用 `sample_submission.csv` 跑通，零 API / 零 GPU）。
3. **参赛者提交**：把自己的模型预测写成 `submission.csv`，在 Notebook 里调用 `scoring.py` 得 `scores.csv`；或按 Kaggle 竞赛模式由平台跑 `scoring.py` 出榜。
4. **评分端隔离**：若做正式竞赛，把 `scoring.py` + `ground_truth.csv` + `public_private_split.csv` 放在平台隐藏的评分容器内，只对参赛者暴露 `metacog_bench.csv` 与 `sample_submission.csv`。

---

## 6. 复现与扩展

```bash
# 源数据（data/sample_items.json + data/run_results.json）更新后，重建制品：
python3 kaggle/benchmark/build_package.py
```

- 扩题：往 `data/sample_items.json` 加题（格式见 `data/SCHEMA.md`），重跑 `build_package.py`。
- 换模型：在 `getting_started.ipynb` 的 `predict()` 里接你的模型，产出新 `submission.csv` 再评分。
- 路线 A（免费）：`kaggle/run_metacog.py` 提供在 Kaggle 免费 GPU 上跑开源权重（DeepSeek-R1-Distill-Qwen-14B 4bit）的脚本。

---

## 7. 引用 / 参考

- DeepMind (2026). *Measuring Progress Toward AGI: A Cognitive Framework*.
- Kadavath et al. (2022). Language Models (Mostly) Know What They Know. arXiv:2207.05221.
- Lin, Hilton, Evans (2022). Teaching Models to Express Their Uncertainty. arXiv:2205.14334.
- Yin et al. (2023). SelfAware. arXiv:2305.18153.
- Kirichenko et al. (2025). AbstentionBench. arXiv:2506.09038.
- Artificial Analysis (2025). The Omniscience Index.
- Guo et al. (2017). On Calibration of Modern Neural Networks. ICML.

完整提案见仓库根 `FengShuo_C2A_proposal.md`；实测与 AAR 见 `FengShuo_C9_*.md`。
