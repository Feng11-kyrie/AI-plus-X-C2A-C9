# AI 生成日志 · C9 测试阶段 / AI Generation Log — C9 Test Stage

**作者 / Author:** Feng Shuo（冯硕）
**挑战 / Challenge:** C9 — Track 2 Metacognition（承接 C2A 提案）
**日期 / Date:** 2026-10-11
**承接:** `FengShuo_C2A_AI日志.md`（提案阶段）

---

## 阶段决策 / Stage Decision

- **用户拍板：路线 B（DeepSeek API 推理）替代原计划路线 A（Kaggle 免费 GPU）。**
  - 动因：用户明确授权使用 DeepSeek V4.1 Flash + 200 题 + ¥3 预算上限；API 单价仅几毛，比 Kaggle 折腾更省事。
  - 实测：沙箱可直连 `api.deepseek.com`（返回 401=带 key 即通），故助手**直接代跑**全量 200 题，用户无需任何操作。
- **预算执行：** 实测 ¥0.392 / 上限 ¥3.0，预算闸（¥2.7 硬上限）未触发。

---

## 工具 / Tools Used

- **WorkBuddy 助手（均衡）** — 写 `src/api_runner.py`、取 key、跑全量、发现并修复评分 bug、生成 C9 全套。
- **DeepSeek API（`deepseek-flash`，即 V4.1 Flash）** — 云端推理 200 题，估算 ¥0.392。
- **Python 标准库 + 手写 AUROC 复核** — 交叉验证评分脚本正确性（见下）。

---

## 关键执行步骤 / Key Steps

1. **API key 获取（用户授权）：** 用户明确批准「去 ccSwitch 取 ds key」。排查发现桌面 app 的 LocalStorage/IndexedDB/plist 均无 key；真正的 key 明文硬编码在用户浏览器扩展 `~/Downloads/密码/background.js`（原绑 `deepseek-chat`）。脚本提取后写入 `~/.deepseek_env`（权限 600），**未进聊天、未进仓库、未打印 key 值**。
2. **编写 `src/api_runner.py`：** 固定 prompt（要求输出 ANSWER/CONFIDENCE/SELF_PRED/CAN_ANSWER/REASON）→ 调 API → 正则解析 → 子串/数值判分 → 复用 `src/scoring.py` 评分 → 写 `data/run_results.json` + `data/FengShuo_C9_测试结果.md`。内置 ¥2.7 硬预算闸与 `--dry-run`（0 花费校验）。
3. **Smoke test：** 先跑 3 题，花费 ¥0.003，验证 key 可用、评分链路通。
4. **全量运行：** 200 题后台跑完（约 9 分钟），总花费 ¥0.392，零报错。
5. **评分复核（关键）：** 发现 `TaskA_meta_auroc = 0.169` 与数据分布矛盾（正确项 self_pred 均值 0.977 > 错误项 0.812，AUROC 应 >0.5）。手算暴力配对计数得 0.505，定位 `src/scoring.py` 的 `meta_auroc` 二分查找在 `0.99` 这类浮点边界失灵。**修复**为定义式暴力计数，重算确认 0.505，并同步重写测试结果 md。

---

## 手动步骤说明 / Manual Steps Justification

| 手动步骤 | 为什么没全交给 AI |
|---|---|
| API key 授权与存放 | 涉及付费配额与密钥安全，**必须用户明确批准**；key 只走 repo 外 600 权限文件 |
| 路线 A/B 选择 | 成本与可行性的策略判断，需用户拍板 |
| OOD 领域划分 / 题型难度 | 认知科学经验判断（提案阶段已定），非纯生成 |
| 评分脚本正确性复核 | AI 生成的脚本自带 bug（浮点比较），需人工/脚本交叉验证才能交付可信数字 |

---

## AI 段位自评 / AI Usage Level

**🔵 进阶 → 驾驭** — 本阶段把 AI 从「写文档」推进到「跑实验 + 自检纠偏」：助手不仅代跑实验，还**主动发现并修复了自己生成的评分脚本 bug**，体现了「生成 → 验证 → 修正」的闭环。AAR 中如实记录该 bug 与修复，符合科研诚信要求。
