#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaCog-Bench · 竞赛评分脚本（scoring）
=======================================
读取「提交 + 金标准 + 切分」，自行判分并产出排行榜分数。

输入（参赛者提交）：
  submission.csv  : id, answer_text, confidence(0-100), self_pred(0-100), can_answer(YES/NO)
隐藏（评分端）：
  ground_truth.csv: id, gold_answer, is_ood, is_answerable, unanswerable_reason
  public_private_split.csv: id, split(public/private)

输出：
  scores.csv      : 单行排行榜条目（各任务指标 + public/private metacog_score）
  并打印人类可读报告。

设计要点（呼应提案 §2.1「单一数字会误导」）：
  - 同时输出全部任务原始指标（Task A/B/C 分层），不只用合成分。
  - 单一排行榜合成分 metacog_score 仅用于排序，权重与归一化方式在 README 公开。

用法：
  # 本地验证（默认相对路径）
  python3 kaggle/benchmark/scoring.py --submission kaggle/benchmark/dataset/sample_submission.csv
  # 指定输出
  python3 kaggle/benchmark/scoring.py --submission <sub.csv> --out scores.csv
  # Kaggle 端（路径由平台注入）
  python3 scoring.py --submission /kaggle/input/.../submission.csv \
                     --ground-truth /kaggle/input/.../ground_truth.csv \
                     --split /kaggle/input/.../public_private_split.csv \
                     --out /kaggle/working/scores.csv
"""

import argparse
import csv
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 复用已验证的 src/scoring.py（meta_auroc 定义式实现等）。
# 用 importlib 显式按路径加载，避免与本文件同名 "scoring" 模块自引用冲突。
_src_path = os.path.join(ROOT, "src", "scoring.py")
_spec = importlib.util.spec_from_file_location("src_scoring", _src_path)
_src_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_src_mod)
evaluate = _src_mod.evaluate

# benchmark_utils（grade / 解析等）与本文件同目录
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from benchmark_utils import grade  # noqa: E402

DS = os.path.join(ROOT, "kaggle", "benchmark", "dataset")


# ---------- 工具 ----------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def metacog_score(rep):
    """单一排行榜合成分（0-100，越高越好）。仅用于排序，权重公开透明。

    - Task A meta_auroc：0.5→0, 1.0→1（随机以下记为 0）
    - Task B 整体 ECE：1-ECE（ECE 上限取 1.0）
    - Task C Omniscience Index：区间 [-0.5,1.0] 线性映射到 [0,1]
    - OOD 护栏 calibration_gap：0→0, 0.5→1（>0.5 封顶；为负则该项 0）
    权重 0.30 / 0.35 / 0.20 / 0.15。
    """
    a_raw = rep.get("TaskA_meta_auroc")
    a = clamp((a_raw - 0.5) / 0.5, 0, 1) if a_raw is not None else 0.0
    n = rep.get("n_total", 0) or 1
    ece_overall = (rep.get("TaskB_ECE_ID", 0) * rep.get("n_id", 0)
                   + rep.get("TaskB_ECE_OOD", 0) * rep.get("n_ood", 0)) / n
    b = clamp(1 - ece_overall / 1.0, 0, 1)
    omni = rep.get("TaskC", {}).get("omniscience_index", 0.0)
    c = clamp((omni - (-0.5)) / 1.5, 0, 1)
    gap = clamp(rep.get("TaskB_calibration_gap", 0.0) / 0.5, 0, 1)
    return 100 * (0.30 * a + 0.35 * b + 0.20 * c + 0.15 * gap)


# ---------- IO ----------
def read_csv_map(path, key_col, val_cols):
    """读 CSV，返回 {key: [vals...]}。"""
    out = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = row[key_col]
            out[key] = [row[c] for c in val_cols]
    return out


def load_submission(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


# ---------- 主流程 ----------
def score(sub_path, gt_path, split_path, out_path):
    sub_rows = load_submission(sub_path)
    gt = read_csv_map(gt_path, "id",
                      ["gold_answer", "is_ood", "is_answerable",
                       "unanswerable_reason"])
    split = read_csv_map(split_path, "id", ["split"])

    samples = []
    skipped = 0
    for r in sub_rows:
        pid = r["id"]
        if pid not in gt:
            skipped += 1
            continue
        gold_answer, is_ood_s, is_ans_s, _ = gt[pid]
        is_ans = (is_ans_s.strip().lower() == "true")
        # 自行判分（不信任提交里的正确性）
        answer_text = r.get("answer_text", "") or ""
        can = (r.get("can_answer", "") or "YES").upper()
        answered = (can != "NO") and answer_text and "CANNOT" not in answer_text.upper()
        correct = (grade(answer_text, gold_answer, is_ans)
                   if answered else False)
        try:
            conf = max(0.01, min(0.99, float(r.get("confidence", 50)) / 100.0))
            sp = max(0.01, min(0.99, float(r.get("self_pred", 50)) / 100.0))
        except ValueError:
            conf, sp = 0.5, 0.5
        samples.append({
            "id": pid,
            "domain": pid.split("-")[1] if "-" in pid else "general",
            "is_ood": (is_ood_s.strip().lower() == "true"),
            "is_answerable": is_ans,
            "model_answered": bool(answered),
            "model_correct": bool(correct),
            "confidence": float(conf),
            "self_pred": float(sp),
        })

    if not samples:
        print("✗ 提交为空或无匹配题目，无法评分。")
        return None

    rep_full = evaluate(samples)

    # 按切分评估
    pub_ids = {pid for pid, v in split.items() if v[0] == "public"}
    priv_ids = {pid for pid, v in split.items() if v[0] == "private"}
    rep_pub = evaluate([s for s in samples if s["id"] in pub_ids])
    rep_priv = evaluate([s for s in samples if s["id"] in priv_ids])

    score_full = metacog_score(rep_full)
    score_pub = metacog_score(rep_pub)
    score_priv = metacog_score(rep_priv)

    # 写 scores.csv（单行）
    header = ["model", "meta_auroc", "ece_id", "ece_ood", "calibration_gap",
              "omniscience_index", "false_refusal_rate",
              "public_metacog_score", "private_metacog_score"]
    model_name = os.path.splitext(os.path.basename(sub_path))[0]
    row = [model_name,
           rep_full.get("TaskA_meta_auroc"),
           round(rep_full.get("TaskB_ECE_ID", 0), 4),
           round(rep_full.get("TaskB_ECE_OOD", 0), 4),
           round(rep_full.get("TaskB_calibration_gap", 0), 4),
           round(rep_full.get("TaskC", {}).get("omniscience_index", 0), 4),
           round(rep_full.get("TaskC", {}).get("false_refusal_rate", 0), 4),
           round(score_pub, 2), round(score_priv, 2)]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerow(row)

    # 人类可读报告
    print("=" * 60)
    print("MetaCog-Bench 评分报告")
    print("=" * 60)
    print(f"提交文件      ：{sub_path}")
    print(f"评分题数      ：{len(samples)}（跳过 {skipped} 条无金标准）")
    print(f"公开/私有     ：{len(pub_ids)} / {len(priv_ids)}")
    print("-" * 60)
    print(f"{'指标':28s} {'全量':>10s} {'公开':>10s} {'私有':>10s}")
    print("-" * 60)
    def g(rep, k):
        v = rep.get(k)
        return f"{v:.4f}" if isinstance(v, float) else str(v)
    print(f"{'TaskA meta_auroc':28s} {g(rep_full,'TaskA_meta_auroc'):>10s} "
          f"{g(rep_pub,'TaskA_meta_auroc'):>10s} {g(rep_priv,'TaskA_meta_auroc'):>10s}")
    print(f"{'TaskB ECE_ID':28s} {g(rep_full,'TaskB_ECE_ID'):>10s} "
          f"{g(rep_pub,'TaskB_ECE_ID'):>10s} {g(rep_priv,'TaskB_ECE_ID'):>10s}")
    print(f"{'TaskB ECE_OOD':28s} {g(rep_full,'TaskB_ECE_OOD'):>10s} "
          f"{g(rep_pub,'TaskB_ECE_OOD'):>10s} {g(rep_priv,'TaskB_ECE_OOD'):>10s}")
    print(f"{'TaskB calibration_gap':28s} {g(rep_full,'TaskB_calibration_gap'):>10s} "
          f"{g(rep_pub,'TaskB_calibration_gap'):>10s} {g(rep_priv,'TaskB_calibration_gap'):>10s}")
    omf = rep_full.get("TaskC", {})
    print(f"{'TaskC Omniscience':28s} {omf.get('omniscience_index'):>10.4f} "
          f"{rep_pub.get('TaskC',{}).get('omniscience_index'):>10.4f} "
          f"{rep_priv.get('TaskC',{}).get('omniscience_index'):>10.4f}")
    print(f"{'TaskC false_refusal':28s} {omf.get('false_refusal_rate'):>10.4f} "
          f"{rep_pub.get('TaskC',{}).get('false_refusal_rate'):>10.4f} "
          f"{rep_priv.get('TaskC',{}).get('false_refusal_rate'):>10.4f}")
    print("-" * 60)
    print(f"{'★ metacog_score（排行）':28s} {score_full:>10.2f} "
          f"{score_pub:>10.2f} {score_priv:>10.2f}")
    print("=" * 60)
    print(f"已写出排行榜条目：{out_path}")
    return rep_full


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", required=True)
    ap.add_argument("--ground-truth", default=os.path.join(DS, "ground_truth.csv"))
    ap.add_argument("--split", default=os.path.join(DS, "public_private_split.csv"))
    ap.add_argument("--out", default="scores.csv")
    args = ap.parse_args()
    score(args.submission, args.ground_truth, args.split, args.out)


if __name__ == "__main__":
    main()
