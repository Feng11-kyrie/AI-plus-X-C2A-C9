# 路线 A 操作指南：Kaggle 免费 GPU 跑开源前沿模型

> 目标：C9 阶段「测试有效性」交付 —— 不花一分钱外部 API 预算，用 Kaggle 免费算力
> 加载开源权重（DeepSeek-R1-Distill / Qwen3 等）跑 MetaCog-Bench，产出
> `FengShuo_C9_测试结果.md`。

## 重要现实约束（先读）
- Kaggle 免费 GPU 通常是 **P100 / T4（16GB）**，装不下 671B 满血 DeepSeek。
  因此本路线用 **蒸馏 / 4bit 量化版**（如 `DeepSeek-R1-Distill-Qwen-14B`），
  仍属 2026 开源前沿梯队下沿，**满足 C9「至少一个前沿模型」最低要求**。
- 想要更强模型 → 走路线 B（付费 API，需你明确批预算）或更大显存环境。
- **真·跑模型那一步由你在 Kaggle 网页点 Run**，本机沙箱无 GPU 也连不上 Kaggle。

## 步骤（复制粘贴级）

### 1. 新建 Notebook
登录 Kaggle → Code → New Notebook。

### 2. 开 GPU + 互联网
右侧 Settings：
- Accelerator → **GPU**（选 P100 或 T4）
- Internet → **On**（必须，要下模型权重 + git clone）

### 3. Cell 1 — 拉取仓库（含数据集与评分脚本）
```bash
!git clone https://github.com/Feng11-kyrie/AI-plus-X-C2A-C9
```

### 4. Cell 2 — 装依赖
```bash
!pip install -q transformers accelerate bitsandbytes
```

### 5. Cell 3 — 跑运行器
```bash
%run AI-plus-X-C2A-C9/kaggle/run_metacog.py
```
首次会下载模型权重（几百 MB~几 GB），耐心等。跑完会在 output 生成
`FengShuo_C9_测试结果.md`。

### 6. 导出结果
Notebook 右侧 **Output / Data** 里找到 `FengShuo_C9_测试结果.md` → 下载，
放到本地仓库 `data/` 或根目录，再 `git add` + `commit` + `push`（走 SSH 已配好）。

## 想换模型 / 调规模
改 `kaggle/run_metacog.py` 顶部配置：
- `MODEL_ID`：换成 `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`（显存够时更准）
  或 `Qwen/Qwen3-32B`（中文/多语言更强）。
- `MAX_SAMPLES`：先设 `20` 试跑验证流水线，再设 `200` 跑全量。

## 评分口径
运行器直接复用 `src/scoring.py` 的 `evaluate()`，指标与 proposal 一致：
- Task A（L1 元认知知识）：meta_accuracy / meta_auroc
- Task B（L2 监控校准）：ECE_ID / ECE_OOD / **calibration_gap**（关键判别器）/ brier
- Task C（L3 策略性拒答）：Omniscience Index / false_refusal_rate
