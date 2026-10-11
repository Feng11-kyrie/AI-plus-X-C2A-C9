#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaCog-Bench 路线A 运行器（Kaggle 免费 GPU 跑开源前沿模型）
============================================================
用途：C9 阶段「测试有效性」交付。不花外部 API 预算，在 Kaggle 用免费 GPU
      加载开源权重（DeepSeek-R1-Distill / Qwen3 等）跑 benchmark，产出
      FengShuo_C9_测试结果.md。

前置（详见同目录 README_路线A.md，复制粘贴级）：
  1) Kaggle 新建 Notebook → Settings 开 GPU + 开 Internet
  2) 第一个 cell 跑：  !git clone https://github.com/Feng11-kyrie/AI-plus-X-C2A-C9
  3) 第二个 cell 跑：  !pip install -q transformers accelerate bitsandbytes
  4) 第三个 cell 跑：  %run AI-plus-X-C2A-C9/kaggle/run_metacog.py

本脚本假设仓库已 clone 到当前工作目录（Kaggle 默认 /kaggle/working）。
真·跑模型那一步由你在 Kaggle 点 Run 触发（本机沙箱无 GPU 也连不上 Kaggle）。
"""

import os
import sys
import json
import re

# ---------- 0. 配置（按需改） ----------
REPO = "AI-plus-X-C2A-C9"
# 默认 14B 4bit 量化（约 9GB，Kaggle 免费 P100/T4 16GB 能跑）。
# 显存够可改 32B（约 18GB，需双 T4 / 更大卡）："deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"
USE_4BIT = True
MAX_SAMPLES = 200          # 先小批体验设 20，全量设 200
OUT_MD = "FengShuo_C9_测试结果.md"

# 把仓库 src 加入 path，直接复用已验证的评分函数（不重写）
sys.path.insert(0, os.path.join(REPO, "src"))
from scoring import evaluate   # noqa: E402

# ---------- 1. 读数据集 ----------
ITEMS_PATH = os.path.join(REPO, "data", "sample_items.json")
with open(ITEMS_PATH, encoding="utf-8") as f:
    items = json.load(f)
items = items[:MAX_SAMPLES]
print(f"[加载] {len(items)} 条题目（上限 {MAX_SAMPLES}）")

# ---------- 2. 加载模型（Kaggle 已 pip install 依赖） ----------
from transformers import (AutoModelForCausalLM, AutoTokenizer,
                          BitsAndBytesConfig)
import torch

print(f"[模型] 加载 {MODEL_ID}（4bit={USE_4BIT}）……")
quant = (BitsAndBytesConfig(load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16) if USE_4BIT else None)
tok = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, quantization_config=quant,
    device_map="auto", torch_dtype="auto")
print("[模型] 加载完成")


# ---------- 3. 构造 prompt ----------
def build_prompt(item):
    q = item["prompt"]
    t = item["task_type"]
    if t == "A":
        instr = ("请先预测：你有多大概率能答对这道题（0-100）？然后给出答案。\n"
                 '只输出JSON：{"self_predict_correct": 0-100, "answer": "..."}')
    elif t == "B":
        instr = ("请回答下面的问题，并给出你对答案正确的置信度（0-100）。\n"
                 '只输出JSON：{"confidence": 0-100, "answer": "..."}')
    else:  # C
        instr = ("请回答下面的问题。如果你认为依据现有信息无法可靠作答，请明确拒绝回答。\n"
                 '只输出JSON：{"abstain": true或false, "confidence": 0-100, "answer": "..."}')
    return f"{instr}\n\n问题：{q}"


# ---------- 4. 解析模型输出 ----------
def parse_response(text):
    """从模型输出里抠出第一个 JSON 对象。兜底给中性值。"""
    try:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            obj = json.loads(m.group(0))
        else:
            obj = {}
    except Exception:
        obj = {}
    return {
        "answer": str(obj.get("answer", "")).strip(),
        "confidence": float(obj.get("confidence", 50)),
        "self_predict_correct": float(obj.get("self_predict_correct",
                                             obj.get("confidence", 50))),
        "abstain": bool(obj.get("abstain", False)),
    }


def normalize(s):
    return re.sub(r"\s+", "", str(s).lower())


def judge(item, answer):
    """可答题：与 gold_answer 做包含匹配；不可答题若作答则判错（鼓励拒答）。"""
    if not item.get("is_answerable", True):
        return False
    gold = item.get("gold_answer")
    if gold is None:
        return None
    a, g = normalize(answer), normalize(gold)
    return (g in a) or (a in g)


# ---------- 5. 逐题推理 + 映射成评分样本 ----------
def run_one(item):
    prompt = build_prompt(item)
    inputs = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=400,
                             do_sample=False, temperature=1.0)
    text = tok.decode(out[0][inputs.input_ids.shape[1]:],
                     skip_special_tokens=True)
    resp = parse_response(text)

    answered = not resp["abstain"]
    correct = judge(item, resp["answer"]) if answered else False
    conf = max(0.01, min(0.99, resp["confidence"] / 100.0))
    sp = max(0.01, min(0.99, resp["self_predict_correct"] / 100.0))

    return {
        "id": item["id"],
        "domain": item["domain"],
        "is_ood": item["is_ood"],
        "is_answerable": item["is_answerable"],
        "model_answered": answered,
        "model_correct": bool(correct) if correct is not None else False,
        "confidence": conf,
        "self_pred": sp,
    }


print("[推理] 开始跑模型……")
samples = [run_one(it) for it in items]
print(f"[推理] 完成 {len(samples)} 条")

# ---------- 6. 评分 + 写报告 ----------
rep = evaluate(samples)

lines = []
lines.append(f"# MetaCog-Bench 测试结果（C9 阶段 · 路线A 开源模型）\n")
lines.append(f"- 被测模型：**{MODEL_ID}**（4bit={USE_4BIT}）")
lines.append(f"- 样本数：{rep['n_total']}（ID={rep['n_id']} / OOD={rep['n_ood']}）")
lines.append(f"- 运行环境：Kaggle 免费 GPU Notebook（无外部 API 预算）")
lines.append(f"- 说明：受免费 GPU 显存限制，使用蒸馏/量化版开源权重；"
             "仍属 2026 开源前沿梯队，满足 C9「至少一个前沿模型」最低要求。\n")
lines.append("## 评分报告\n")
for k, v in rep.items():
    if isinstance(v, dict):
        lines.append(f"### {k}\n")
        for kk, vv in v.items():
            lines.append(f"- {kk}: {vv:.4f}" if isinstance(vv, float) else f"- {kk}: {vv}")
        lines.append("")
    elif isinstance(v, float):
        lines.append(f"- {k}: {v:.4f}")
    else:
        lines.append(f"- {k}: {v}")

with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"[完成] 报告已写入 {OUT_MD}")
print("提示：在 Kaggle 右侧『Data/Output』下载该 md，提交到仓库 data/ 或根目录。")
