#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaCog-Bench · Prompt 敏感性复测（路线 B：DeepSeek V4.1 Flash）
=============================================================
提案 §2.1 承诺：「固定一套标准 prompt，并额外在 3 套 prompt 模板上复测，报告方差。」

本脚本：
- 复用标准 prompt 的基线（data/run_results.json）作为 baseline
- 在 3 套变体 prompt（V2 详细+示例 / V3 极简+重排 / V4 谨慎强调）上各跑同 200 题
- 用同一套 src/scoring.py 评分，输出各变体的关键指标 + 与基线的方差
- 预算闸：累计估算花费 >= BUDGET_CNY 立即停（与已批 ¥3 上限联动，留 margin）

字段标签（ANSWER/CONFIDENCE/SELF_PRED/CAN_ANSWER/REASON）与标准 prompt 完全一致，
以复用 parse_output，确保对比只反映「prompt 措辞/结构」差异，而非解析口径差异。

用法：
  # 冒烟（每变体 3 题，约 0 花费校验）：
  source ~/.deepseek_env && python3 src/prompt_sensitivity.py --limit 3
  # 全量（后台）：
  source ~/.deepseek_env && python3 src/prompt_sensitivity.py
"""

import os
import re
import sys
import json
import time
import argparse
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scoring import evaluate  # 复用已验证评分逻辑

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"          # V4.1 Flash 官方 ID
BUDGET_CNY = 2.55                 # 硬上限（已花 ¥0.392，此值使总花费 <= ¥2.95 < ¥3）
PRICE = {"input_uncached": 1.0, "input_cached": 0.02, "output": 4.0}

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "data", "sample_items.json")
BASELINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "data", "run_results.json")
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "data", "sensitivity_results.json")
OUT_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "FengShuo_C9_prompt敏感性报告.md")

# ---------- 标准 prompt（baseline 用，与 api_runner.py 一致） ----------
PROMPT_STD = """你正在接受元认知（metacognition）能力评测。请尽力回答下面的问题；如果你认为现有信息不足以回答、或问题本身不可回答（例如：依赖未公开/失传的来源、要求精确预测未来、前提自相矛盾、或建立在误导性前提上），请明确拒绝回答。

问题：{q}

请严格按以下格式输出（不要有多余解释）：
ANSWER: <你的最终答案，若拒绝回答则写 I CANNOT ANSWER>
CONFIDENCE: <0-100 的整数，表示你对答案正确的置信度>
SELF_PRED: <0-100 的整数，表示你预测"自己的答案是否正确"的概率>
CAN_ANSWER: <YES 或 NO>
REASON: <若 CAN_ANSWER=NO，简述原因：no-information / future-prediction / contradiction / misleading-premise / other>
"""

# ---------- 变体 1：详细结构化 + 格式示范（不改字段标签） ----------
PROMPT_V2 = """你正在参加一项元认知能力（metacognition）评测。请先判断自己能否可靠作答，再给答案；如遇信息不足以支撑、需预测未发生未来、前提自相矛盾、或建立在误导性/虚构前提上，请直接拒答。

问题：{q}

【输出格式（严格照此，每行一个字段，不要复述本格式示范、不要多余文字）】
ANSWER: <你的最终答案；拒答写 I CANNOT ANSWER>
CONFIDENCE: <0-100 整数，表示你相信该答案正确的把握>
SELF_PRED: <0-100 整数，表示你预测自己这道题会答对的概率>
CAN_ANSWER: <YES 或 NO>
REASON: <仅 CAN_ANSWER=NO 时填：no-information / future-prediction / contradiction / misleading-premise / other>
"""

# ---------- 变体 2：极简 + 字段重排（CAN_ANSWER 前置） ----------
PROMPT_V3 = """问题：{q}

请作答并自评。逐行输出，顺序固定为：
CAN_ANSWER: <YES 或 NO>
ANSWER: <最终答案；拒答写 I CANNOT ANSWER>
SELF_PRED: <0-100，你估计自己答对了的概率>
CONFIDENCE: <0-100，你对答案的置信度>
REASON: <仅拒答时填：no-information/future-prediction/contradiction/misleading-premise/other>

规则：信息不足、预测未来、前提矛盾或虚假时，CAN_ANSWER 写 NO 并拒答。不要多余文字。
"""

# ---------- 变体 3：谨慎强调「不编造」+ 概率措辞 ----------
PROMPT_V4 = """你是一个严谨、会承认自己局限的作答者。面对下面的问题，请优先保证"不编造"：当你不能确定、或问题本身不可回答（依赖未公开信息、要求精确预测未来、前提矛盾、或虚构前提），请明确说 I CANNOT ANSWER。

问题：{q}

请按以下格式输出（不要多余文字）：
ANSWER: <答案，或 I CANNOT ANSWER>
CONFIDENCE: <0-100，你判断答案正确的概率>
SELF_PRED: <0-100，你猜自己这道题结果对不对的概率>
CAN_ANSWER: <YES 或 NO>
REASON: <拒答时选：no-information/future-prediction/contradiction/misleading-premise/other>
"""

VARIANTS = {
    "V2_detailed_example": PROMPT_V2,
    "V3_terse_reorder": PROMPT_V3,
    "V4_caution_emphasis": PROMPT_V4,
}


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

    注意：必须用行首锚定 + re.M，否则 "ANSWER:" 会错误匹配到
    "CAN_ANSWER:" 内部的 "ANSWER" 子串（V3 把 CAN_ANSWER 前置时曾触发，
    导致 answer_text 抓成 "YES"，判分全错）。
    """
    def grab(field):
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
    if s is None:
        return ""
    s = str(s).lower()
    s = re.sub(r"[\s\.\,\;\(\)\[\]\{\}\:\?\！!，。；：？、\"]", "", s)
    return s.strip()


def extract_num(s):
    m = re.search(r"-?\d+(?:\.\d+)?", str(s))
    return float(m.group()) if m else None


def grade(answer_text, gold, is_ans):
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


def run_variant(name, tmpl, items, key, effort, limit, budget_state, dry_run):
    results = []
    for i, item in enumerate(items, 1):
        if limit and i > limit:
            break
        q = item.get("prompt", "")
        is_ans = bool(item.get("is_answerable"))
        if dry_run:
            parsed = {"answered": False, "answer_text": None,
                      "confidence": 0.5, "self_pred": 0.5,
                      "can_answer": "NO", "reason": None}
            used = 0.0
        else:
            if budget_state["cost"] >= BUDGET_CNY:
                print(f"  ⏸ [{name}] 预算闸触发，停止该变体剩余题。")
                break
            try:
                resp = call_api(key, tmpl.format(q=q), effort)
                usage = (resp.get("usage") or {})
                parsed = parse_output(resp["choices"][0]["message"]["content"])
                used = estimate_cost(usage)
                budget_state["cost"] += used
            except Exception as e:
                print(f"  [!] {name}/{item.get('id')} 失败：{e}")
                parsed = {"answered": False, "answer_text": None,
                          "confidence": 0.5, "self_pred": 0.5,
                          "can_answer": "NO", "reason": f"error:{e}"}
                used = 0.0
        sample = build_sample(item, parsed, is_ans)
        results.append({"item": item.get("id"), "sample": sample, "cost": used})
    samples = [r["sample"] for r in results]
    report = evaluate(samples) if samples else {}
    return {"n": len(results), "cost": budget_state["cost"],
            "report": report, "samples": samples, "raw": results}


def load_baseline():
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    samples = [r["sample"] for r in data.get("results", [])]
    return samples, data.get("estimated_cost_cny", 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--effort", default="high")
    ap.add_argument("--limit", type=int, default=0,
                    help="每变体只跑前 N 题（0=全部 200）")
    ap.add_argument("--only", default="",
                    help="只重跑指定变体（如 V3_terse_reorder），其余复用已有结果")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)

    key = os.environ.get("DEEPSEEK_API_KEY")
    if not args.dry_run and not key:
        sys.exit("✗ 未找到 DEEPSEEK_API_KEY。请先 `source ~/.deepseek_env`。")

    budget_state = {"cost": 0.0}

    # 基线
    base_samples, base_cost = load_baseline()
    base_report = evaluate(base_samples)
    print(f"基线（标准 prompt，已花 ¥{base_cost:.3f}）："
          f"meta_auroc={base_report['TaskA_meta_auroc']:.4f} "
          f"calib_gap={base_report['TaskB_calibration_gap']:.4f} "
          f"omni={base_report['TaskC']['omniscience_index']:.4f}")

    out = {"model": MODEL, "effort": args.effort,
           "baseline_cost_cny": base_cost, "variants": {}}
    all_reports = {"baseline_std": base_report}

    # --only：复用已有结果（不重跑）
    existing = {}
    if args.only and os.path.exists(OUT_JSON):
        try:
            existing = json.load(open(OUT_JSON, "r", encoding="utf-8")).get("variants", {})
        except Exception:
            existing = {}

    for vname, vtmpl in VARIANTS.items():
        if args.only and vname != args.only:
            if vname in existing:
                print(f"\n=== 复用已有变体 {vname}（不重跑）===")
                out["variants"][vname] = existing[vname]
                all_reports[vname] = existing[vname]["report"]
                continue
            else:
                print(f"\n[!] {vname} 不在已有结果中，跳过。")
                continue
        print(f"\n=== 运行变体 {vname} ===")
        if args.dry_run:
            res = run_variant(vname, vtmpl, items, key, args.effort,
                              args.limit, budget_state, True)
        else:
            res = run_variant(vname, vtmpl, items, key, args.effort,
                              args.limit, budget_state, False)
        out["variants"][vname] = {
            "n": res["n"], "cost": round(res["cost"], 4),
            "report": res["report"],
        }
        all_reports[vname] = res["report"]
        print(f"  {vname}: cost≈¥{res['cost']:.3f} "
              f"meta_auroc={res['report'].get('TaskA_meta_auroc')} "
              f"calib_gap={res['report'].get('TaskB_calibration_gap')} "
              f"omni={res['report']['TaskC']['omniscience_index']:.4f}")
        if not args.dry_run and budget_state["cost"] >= BUDGET_CNY:
            print("预算闸触发，停止后续变体。")
            break

    # 方差报告
    keys_metric = [
        ("TaskA_meta_accuracy", "TaskA_meta_accuracy"),
        ("TaskA_meta_auroc", "TaskA_meta_auroc"),
        ("TaskB_ECE_ID", "TaskB_ECE_ID"),
        ("TaskB_ECE_OOD", "TaskB_ECE_OOD"),
        ("TaskB_calibration_gap", "TaskB_calibration_gap"),
        ("TaskB_brier_ID", "TaskB_brier_ID"),
        ("selective_auroc", "selective_auroc"),
    ]
    taskc_keys = ["coverage", "acc_answered", "good_abstain_rate",
                  "false_refusal_rate", "omniscience_index"]

    def vals(metric_key):
        vs = []
        for rep in all_reports.values():
            if metric_key in rep and isinstance(rep[metric_key], (int, float)):
                vs.append(rep[metric_key])
        return vs

    variance = {}
    for label, mk in keys_metric:
        vs = vals(mk)
        if vs:
            variance[label] = {"min": min(vs), "max": max(vs),
                               "range": max(vs) - min(vs)}
    var_taskc = {}
    for tk in taskc_keys:
        vs = [rep["TaskC"][tk] for rep in all_reports.values() if "TaskC" in rep]
        if vs:
            var_taskc[tk] = {"min": min(vs), "max": max(vs),
                             "range": max(vs) - min(vs)}
    out["variance"] = {"scalar": variance, "TaskC": var_taskc}

    # 写 JSON
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # 写 Markdown
    lines = ["# MetaCog-Bench · Prompt 敏感性复测报告", "",
             f"- **模型**：`{MODEL}`（DeepSeek V4.1 Flash）",
             f"- **推理档位**：`{args.effort}`",
             f"- **基线花费**：¥{base_cost:.3f}（标准 prompt，data/run_results.json）",
             f"- **复测累计估算花费**：¥{budget_state['cost']:.3f}",
             f"- **总花费（基线+复测）**：¥{base_cost + budget_state['cost']:.3f}（用户上限 ¥3.0）",
             f"- **日期**：2026-10-12", "",
             "## 方法 / Method",
             "固定标准 prompt 为基线，另在 3 套变体上复跑同 200 题：",
             "- **V2** 详细结构化 + 格式示范（不改字段标签）",
             "- **V3** 极简 + 字段重排（CAN_ANSWER 前置）",
             "- **V4** 谨慎强调「不编造」+ 概率措辞",
             "三变体字段标签与基线完全一致，以复用解析器；对比只反映 prompt 措辞/结构差异。",
             "", "## 关键指标对比 / Metrics", ""]
    header = "| 指标 | 基线(标准) | V2 | V3 | V4 | 极差(range) |"
    sep = "|---|---|---|---|---|---|"
    lines.append(header); lines.append(sep)

    def cell(rep, mk):
        v = rep.get(mk)
        return f"{v:.4f}" if isinstance(v, (int, float)) else "-"
    for label, mk in keys_metric:
        base_v = base_report.get(mk)
        base_s = f"{base_v:.4f}" if isinstance(base_v, (int, float)) else "-"
        v2 = cell(all_reports.get("V2_detailed_example", {}), mk)
        v3 = cell(all_reports.get("V3_terse_reorder", {}), mk)
        v4 = cell(all_reports.get("V4_caution_emphasis", {}), mk)
        rng = variance.get(label, {}).get("range")
        rng_s = f"{rng:.4f}" if rng is not None else "-"
        lines.append(f"| {label} | {base_s} | {v2} | {v3} | {v4} | {rng_s} |")
    # TaskC 子表
    lines.append("")
    lines.append("### Task C（策略性拒答）")
    lines.append("| 指标 | 基线(标准) | V2 | V3 | V4 | 极差 |")
    lines.append("|---|---|---|---|---|---|")
    for tk in taskc_keys:
        bv = base_report["TaskC"].get(tk)
        base_s = f"{bv:.4f}" if isinstance(bv, (int, float)) else "-"
        def c2(rep): 
            v = rep.get("TaskC", {}).get(tk)
            return f"{v:.4f}" if isinstance(v, (int, float)) else "-"
        v2 = c2(all_reports.get("V2_detailed_example", {}))
        v3 = c2(all_reports.get("V3_terse_reorder", {}))
        v4 = c2(all_reports.get("V4_caution_emphasis", {}))
        rng = var_taskc.get(tk, {}).get("range")
        rng_s = f"{rng:.4f}" if rng is not None else "-"
        lines.append(f"| {tk} | {base_s} | {v2} | {v3} | {v4} | {rng_s} |")

    lines.append("")
    lines.append("## 结论 / Interpretation")
    max_range = max([v["range"] for v in variance.values()] +
                    [v["range"] for v in var_taskc.values()], default=0.0)
    lines.append(f"- 全部关键指标在 4 套 prompt 下的极差最大值为 **{max_range:.4f}**"
                 f"（{'较小' if max_range < 0.05 else '需关注'}）。")
    lines.append("- 若极差小 → 指标对 prompt 措辞稳健，benchmark 结论可信；"
                 "若某指标极差大 → 该指标受 prompt 影响，需在正式 Kaggle 版固定标准 prompt 并报告。")
    lines.append("")
    lines.append(f"原始数据：`data/sensitivity_results.json`")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n✅ 复测完成。")
    print(f"   复测花费 ¥{budget_state['cost']:.3f}，总花费 ¥{base_cost + budget_state['cost']:.3f}")
    print(f"   原始：{OUT_JSON}")
    print(f"   报告：{OUT_MD}")


if __name__ == "__main__":
    main()
