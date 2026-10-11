# AI-plus-X-C2A-C9 — 衡量 AGI 的认知能力（Track 2 Metacognition）

挑战 ID：ch-20260717031352-tlg70p ｜ 截止：2026-12-31 23:59

## 赛道
**Track 2 — Metacognition（元认知）**

## 提案基准：MetaCog-Bench
跨域元认知校准与策略性拒答基准。按 DeepMind《Measuring Progress Toward AGI》§7.7 的三层框架（L1 元认知知识 / L2 监控校准 / L3 控制拒答）统一设计，并强制 **OOD 域外转移** 以区分「元认知」与「记忆匹配」。

## 文件结构
**C2A 提案阶段（已交付）**
- `FengShuo_C2A_proposal.md` — C2A 提案 v1（四部分：选赛道 / 基准设计 / 人类基线 / 创新与可行性）
- `FengShuo_C2A_AI日志.md` — AI 使用日志（多轮调研 + 提案迭代佐证）
- `FengShuo_C2A_拿来说明.md` — 借鉴来源与改进说明（拿来主义底座）

**C9 测试阶段（已交付，2026-10-11）**
- `FengShuo_C9_测试结果.md` — DeepSeek V4.1 Flash 200 题测试结果 + `src/scoring.py` 评分
- `FengShuo_C9_AI日志.md` — 测试阶段过程（取 key / 跑全量 / 发现并修评分 bug）
- `FengShuo_C9_拿来说明.md` — 测试阶段来源/借鉴说明
- `FengShuo_C9_AAR.md` — 复盘报告（占 20 分）

**底座 / 代码**
- `src/scoring.py` — 评分脚手架（ECE / Brier / meta-accuracy / Omniscience；meta_auroc 已修复）
- `src/api_runner.py` — 路线 B 调用运行器（DeepSeek API，含 ¥2.7 预算闸与 dry-run）
- `data/generate_items.py` — 200 题生成器（真实事实题库 + OOD + 不可答四类）
- `data/sample_items.json` — 数据集（A61/B59/C80，OOD39）
- `data/loader.py` `data/SCHEMA.md` — JSON 加载与格式说明
- `kaggle/run_metacog.py` `kaggle/README_路线A.md` — 路线 A 备选（Kaggle 免费 GPU）
- `research/论文精读笔记.md` `research/metacognition_benchmark_survey.md` — 调研底座
- `PLAN.md` `C9_提交框架.md` — 计划与 C9 交付框架

## 进度
- ✅ P0 立项：论文精读 + ≥11 个 benchmark 调研
- ✅ P1 C2A 三件套 v1 完成（待提交评审，抢「首个合格提交者直接录取 Elite 20」）
- ✅ P4 模型测试：路线 B 实测 DeepSeek V4.1 Flash 200 题（¥0.392 / 上限 ¥3）
  - 关键结果：calibration_gap = 0.317（OOD 准确率 2.6% vs ID 65.8%）；Task A meta_auroc = 0.505（近随机）；不可答召回 100%
  - 修复 `meta_auroc` 浮点 bug，已交叉验证
- ✅ C9 四件套（测试结果 / AI日志 / 拿来说明 / AAR）全部完成并推送

> 路线 B 实测已完成；若后续要展示基准「区分度」（强/弱模型对比），可再加 1 个模型（仍在免费/几毛级），见 `FengShuo_C9_AAR.md` §5。
