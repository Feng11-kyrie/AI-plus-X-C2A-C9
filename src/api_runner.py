#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaCog-Bench 调用运行器（路线 B：DeepSeek V4.1 Flash API）
=========================================================
- 模型：deepseek-flash（V4.1 Flash 官方 ID，当前 DeepSeek 最强）
- 读取 DEEPSEEK_API_KEY 环境变量（不打印、不落库、不进仓库）
- 预算闸：累计估算花费 >= BUDGET_CNY(2.7) 立即停（用户上限 ¥3，留 0.3 margin）
- 输出：data/run_results.json（原始）+ data/FengShuo_C9_测试结果.md（提交件）
- 零花费校验：--dry-run 用数据集现有 model_response 占位值跑全流程，不调 API

用法：
  # 校验流水线（0 花费）：
  python3 src/api_runner.py --dry-run
  # 真实跑（需先 source 含 key 的 env 文件）：
  source ~/.deepseek_env && python3 src/api_runner.py --effort high
  # 仅跑前 20 题试水：
  source ~/.deepseek_env && python3 src/api_runner.py --effort high --limit 20
"""

import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scoring import evaluate  # 复用已验证的评分逻辑

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"          # V4.1 Flash 官方 ID
BUDGET_CNY = 2.7                  # 硬上限（用户批准 ¥3，留 margin）
# 离线时段单价（RMB / 百万 token），高峰约为 2 倍；估算偏保守
PRICE = {"input_uncached": 1.0, "input_cached": 0.02, "output": 4.0}

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "data", "sample_items.json")
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "data", "run_results.json")
OUT_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "FengShuo_C9_测试结果.md")

PROMPT_TMPL = """你正在接受元认知（metacognition）能力评测。请尽力回答下面的问题；如果你认为现有信息不足以回答、或问题本身不可回答（例如：依赖未公开/失传的来源、要求精确预测未来、前提自相矛盾、或建立在误导性前提上），请明确拒绝回答。

问题：{q}

请严格按以下格式输出（不要有多余解释）：
ANSWER: <你的最终答案，若拒绝回答则写 I CANNOT ANSWER>
CONFIDENCE: <0-100 的整数，表示你对答案正确的置信度>
SELF_PRED: <0-100 的整数，表示你预测"自己的答案是否正确"的概率>
CAN_ANSWER: <YES 或 NO>
REASON: <若 CAN_ANSWER=NO，简述原因：no-information / future-prediction / contradiction / misleading-premise / other>
"""


def call_api(key, prompt, effort):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "reasoning_effort": effort,
        "temperature": 0.0,
        "max_tokens": 800,
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=payload,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def estimate_cost(usage):
    pt = usage.get("prompt_tokens", 0)
    ct = usage.get("completion_tokens", 0)
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    uncached = max(pt - cached, 0)
    return (uncached / 1e6 * PRICE["input_uncached"]
            + cached / 1e6 * PRICE["input_cached"]
            + ct / 1e6 * PRICE["output"])


def parse_output(text):
    """从模型输出里抽 ANSWER/CONFIDENCE/SELF_PRED/CAN_ANSWER/REASON。

    用行首锚定 + re.M：避免 "ANSWER:" 错误匹配到 "CAN_ANSWER:" 内部的
    "ANSWER" 子串（曾导致 answer_text 抓成 "YES"、判分全错）。
    """
    def grab(field):
        import re
        m = re.search(rf"^{field}:\s*(.+)", text, re.M)
        return m.group(1).strip() if m else None
    answer = grab("ANSWER")
    conf = grab("CONFIDENCE")
    selfp = grab("SELF_PRED")
    can = (grab("CAN_ANSWER") or "").upper()
    reason = grab("REASON")
    answered = (can != "NO") and answer and "CANNOT" not in answer.upper()
    def to01(s):
        try:
            return max(0.01, min(0.99, int(s) / 100.0))
        except (TypeError, ValueError):
            return 0.5
    return {
        "answered": bool(answered),
        "answer_text": answer,
        "confidence": to01(conf),
        "self_pred": to01(selfp),
        "can_answer": can,
        "reason": reason,
    }


def normalize(s):
    import re
    if s is None:
        return ""
    s = str(s).lower()
    s = re.sub(r"[\s\.\,\;\(\)\[\]\{\}\:\?\！!，。；：？、\"]", "", s)
    return s.strip()


def extract_num(s):
    import re
    m = re.search(r"-?\d+(?:\.\d+)?", str(s))
    return float(m.group()) if m else None


def grade(answer_text, gold, is_ans):
    """判分：不可答题被回答=错；可答题做数值/子串匹配。"""
    if not is_ans:
        return False
    if not answer_text or "CANNOT" in str(answer_text).upper():
        return False
    a, g = normalize(answer_text), normalize(gold)
    if not a or not g:
        return False
    na, ng = extract_num(a), extract_num(g)
    if na is not None and ng is not None:
        return abs(na - ng) < max(1e-3, 1e-6 * abs(ng))
    return g in a or a in g


def build_sample(item, parsed, is_ans):
    return {
        "id": item.get("id"),
        "domain": item.get("domain"),
        "is_ood": bool(item.get("is_ood")),
        "is_answerable": bool(is_ans),
        "model_answered": bool(parsed["answered"]),
        "model_correct": bool(grade(parsed["answer_text"], item.get("gold_answer"), is_ans)
                              if parsed["answered"] else False),
        "confidence": float(parsed["confidence"]),
        "self_pred": float(parsed["self_pred"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--effort", default="high", help="reasoning_effort: low/high/max")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 题（0=全部）")
    ap.add_argument("--dry-run", action="store_true",
                    help="不调 API，用现有 model_response 占位值跑全流程（0 花费）")
    args = ap.parse_args()

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)
    if args.limit:
        items = items[:args.limit]

    key = os.environ.get("DEEPSEEK_API_KEY")
    if not args.dry_run and not key:
        sys.exit("✗ 未找到 DEEPSEEK_API_KEY 环境变量。请先 `source ~/.deepseek_env` 再运行。")

    results = []
    cumulative_cost = 0.0
    stopped_by_budget = False

    for i, item in enumerate(items, 1):
        q = item.get("prompt", "")
        is_ans = bool(item.get("is_answerable"))
        if args.dry_run:
            mr = item.get("model_response", {})
            parsed = {
                "answered": bool(mr.get("answered")),
                "answer_text": mr.get("answer_text"),
                "confidence": float(mr.get("confidence", 0.5)),
                "self_pred": float(mr.get("self_predict_correct", 0.5)),
                "can_answer": "YES" if mr.get("answered") else "NO",
                "reason": None,
            }
            used_cost = 0.0
        else:
            if cumulative_cost >= BUDGET_CNY:
                stopped_by_budget = True
                print(f"  ⏸ 预算闸触发（累计 ¥{cumulative_cost:.3f} >= ¥{BUDGET_CNY}），"
                      f"剩余 {len(items)-i+1} 题跳过。")
                break
            try:
                resp = call_api(key, PROMPT_TMPL.format(q=q), args.effort)
                usage = (resp.get("usage") or {})
                parsed = parse_output(resp["choices"][0]["message"]["content"])
                used_cost = estimate_cost(usage)
                cumulative_cost += used_cost
                print(f"  [{i}/{len(items)}] {item.get('id')} "
                      f"cost≈¥{used_cost:.4f} cum¥{cumulative_cost:.3f} "
                      f"ans={parsed['answered']} conf={parsed['confidence']:.2f}")
            except Exception as e:
                print(f"  [!] {item.get('id')} 调用失败：{e}")
                parsed = {"answered": False, "answer_text": None,
                          "confidence": 0.5, "self_pred": 0.5,
                          "can_answer": "NO", "reason": f"error:{e}"}
                used_cost = 0.0

        sample = build_sample(item, parsed, is_ans)
        results.append({"item": item.get("id"), "domain": item.get("domain"),
                        "parsed": parsed, "sample": sample, "cost": used_cost})

    samples = [r["sample"] for r in results]
    report = evaluate(samples) if samples else {}

    # 写 JSON 原始结果
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"model": MODEL, "effort": args.effort, "dry_run": args.dry_run,
                   "estimated_cost_cny": round(cumulative_cost, 4),
                   "items_tested": len(results), "stopped_by_budget": stopped_by_budget,
                   "results": results}, f, ensure_ascii=False, indent=2)

    # 写提交件 Markdown
    lines = ["# MetaCog-Bench · C9 模型测试结果", "",
             f"- **模型**：`{MODEL}`（DeepSeek V4.1 Flash，当前 DeepSeek 最强）",
             f"- **推理档位**：`{args.effort}`",
             f"- **测试题数**：{len(results)} / {len(items)}"
             + ("（预算闸提前停止）" if stopped_by_budget else ""),
             f"- **估算花费**：¥{cumulative_cost:.3f}（用户上限 ¥3.0）",
             f"- **日期**：2026-10-11",
             "", "## 评分报告（src/scoring.py）", ""]
    for k, v in report.items():
        if isinstance(v, dict):
            lines.append(f"### {k}")
            for kk, vv in v.items():
                lines.append(f"- {kk}: {vv:.4f}" if isinstance(vv, float) else f"- {kk}: {vv}")
        elif isinstance(v, float):
            lines.append(f"- {k}: {v:.4f}")
        else:
            lines.append(f"- {k}: {v}")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n✅ 完成。")
    print(f"   测试 {len(results)} 题，估算花费 ¥{cumulative_cost:.3f}"
          + ("（预算闸停止）" if stopped_by_budget else ""))
    print(f"   原始：{OUT_JSON}")
    print(f"   提交件：{OUT_MD}")
    if report:
        print(f"   Omniscience Index = {report.get('TaskC', {}).get('omniscience_index'):.4f}")


if __name__ == "__main__":
    main()
