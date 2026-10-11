# MetaCog-Bench 数据集格式说明（v0.1）

> 单干实现底座的一部分。本文件定义 benchmark 题目（输入 + 金标准标签）的格式，
> 并说明它如何对接 `src/scoring.py` 的评分。
> 你（用户）只需要**编辑 `sample_items.json`**，不写代码：填题目、填金标准、跑完模型后填 `model_response`。

---

## 1. 一条题目的完整结构

```json
{
  "id": "A-math-001",
  "task": "A",
  "domain": "math",
  "is_ood": false,
  "is_answerable": true,
  "prompt": "计算：17 × 23 = ?",
  "gold_answer": "391",
  "unanswerable_reason": null,
  "model_response": {
    "answered": true,
    "answer_text": "391",
    "is_correct": true,
    "confidence": 0.92,
    "self_predict_correct": 0.88
  }
}
```

## 2. 字段含义

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 题目唯一编号，建议 `任务-领域-序号` |
| `task` | "A" / "B" / "C" | 对应 DeepMind §7.7 三层：A=元认知知识 / B=监控校准 / C=策略性拒答 |
| `domain` | string | 领域，如 math / law / biology / physics / general |
| `is_ood` | bool | 是否属于 OOD 转移集（Task B 用，区分 ID/OOD 校准） |
| `is_answerable` | bool | 题目本身是否可答（Task C 用，不可答 = 应拒答） |
| `prompt` | string | 喂给模型的题目原文 |
| `gold_answer` | string / null | 可答题的金标准答案；不可答题填 `null` |
| `unanswerable_reason` | string / null | 不可答的原因（无依据/未知未来/前提矛盾等） |

### `model_response`（跑完模型后由你填写）

| 字段 | 类型 | 说明 |
|---|---|---|
| `answered` | bool | 模型是否给出答案（`false` = 拒答 / abstain） |
| `answer_text` | string / null | 模型给出的答案文本 |
| `is_correct` | bool | 答案是否等于 `gold_answer`（拒答填 `false`） |
| `confidence` | float 0~1 | 模型对"答案正确"的置信度（Task B 用） |
| `self_predict_correct` | float 0~1 | 模型预测"我会答对吗"的概率（Task A 用） |

> ⚠️ `model_response` 目前是**占位示例值**，需在你用真实模型跑完 `prompt` 后替换。
> 替换前_loader 也能跑（演示流水线），但分数不代表真实模型。

---

## 3. 三任务出题要点

- **Task A（L1 元认知知识）**：让模型先预测"我会答对吗"，再答题。
  重点看 `self_predict_correct` 能否区分"会/不会答对" → `meta_accuracy` / `meta_auroc`。
- **Task B（L2 监控校准）**：跨领域出题，一半设为 OOD（如用拓扑学解释经济）。
  重点看 `confidence` 与实际正确率是否匹配 → `ECE_ID` / `ECE_OOD` / **`calibration_gap`**。
- **Task C（L3 策略性拒答）**：混合"可答"与"不可答"（无依据/未知未来/前提矛盾/对抗诱导）。
  重点看模型能否在不可答题上拒答、在可答题上作答 → `Omniscience Index` / `false_refusal_rate`。

---

## 4. 对接评分脚本

`data/loader.py` 读取本目录的 `sample_items.json`，把每条题目的
`model_response` + `is_ood` + `is_answerable` + `domain` 映射成
`src/scoring.py` 的 `evaluate()` 所需 dict，并打印报告：

```bash
python3 data/loader.py
```

你日后要做的只有三步：
1. 往 `sample_items.json` 加题目（照现有格式复制粘贴）；
2. 用模型跑 `prompt`，把结果填进对应 `model_response`；
3. 运行 `python3 data/loader.py` 看分数。
