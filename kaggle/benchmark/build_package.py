#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaCog-Bench · 数据集打包脚本（build_package）
================================================
从源数据（data/sample_items.json + data/run_results.json）生成 Kaggle 基准制品：

  dataset/metacog_bench.csv      公开题集（id, task, domain, prompt）——不含金标准
  dataset/ground_truth.csv       金标准（id, gold_answer, is_ood, is_answerable,
                                 unanswerable_reason）——评分端使用，Kaggle 端隐藏
  dataset/sample_submission.csv  提交格式示例（来自 DeepSeek V4.1 Flash 真实预测）
  dataset/public_private_split.csv  公开/私有榜切分（按任务分层抽样，各任务均分）

纯标准库，可重跑。源数据更新后直接再跑本脚本即可重建制品。

用法：
  python3 kaggle/benchmark/build_package.py
"""

import csv
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_ITEMS = os.path.join(ROOT, "data", "sample_items.json")
SRC_RESULTS = os.path.join(ROOT, "data", "run_results.json")
OUT_DIR = os.path.join(ROOT, "kaggle", "benchmark", "dataset")
SEED = 20261012


def load():
    with open(SRC_ITEMS, encoding="utf-8") as f:
        items = json.load(f)
    with open(SRC_RESULTS, encoding="utf-8") as f:
        results = json.load(f)["results"]
    # 以 item id 为键，方便合并
    parsed_by_id = {r["item"]: r["parsed"] for r in results}
    return items, parsed_by_id


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  ✓ {os.path.relpath(path, ROOT)}  ({len(rows)} 行)")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    items, parsed_by_id = load()
    print(f"[打包] 载入 {len(items)} 题、{len(parsed_by_id)} 条真实预测")

    # --- 公开题集（不给金标准） ---
    public_rows = [[it["id"], it["task"], it["domain"], it["prompt"]] for it in items]
    write_csv(os.path.join(OUT_DIR, "metacog_bench.csv"),
              ["id", "task", "domain", "prompt"], public_rows)

    # --- 金标准（隐藏） ---
    gt_rows = [[it["id"], it.get("gold_answer"),
                it["is_ood"], it["is_answerable"],
                it.get("unanswerable_reason") or ""] for it in items]
    write_csv(os.path.join(OUT_DIR, "ground_truth.csv"),
              ["id", "gold_answer", "is_ood", "is_answerable",
               "unanswerable_reason"], gt_rows)

    # --- 提交格式示例（源自真实预测） ---
    sub_rows = []
    for it in items:
        pid = it["id"]
        p = parsed_by_id.get(pid, {})
        conf = int(round(float(p.get("confidence", 0.5)) * 100))
        sp = int(round(float(p.get("self_pred", 0.5)) * 100))
        can = (p.get("can_answer") or "YES").upper()
        ans = p.get("answer_text") or ""
        sub_rows.append([pid, ans, conf, sp, can])
    write_csv(os.path.join(OUT_DIR, "sample_submission.csv"),
              ["id", "answer_text", "confidence", "self_pred", "can_answer"],
              sub_rows)

    # --- 公开/私有切分（按任务分层抽样，各任务均分） ---
    rng = random.Random(SEED)
    split_rows = []
    by_task = {}
    for it in items:
        by_task.setdefault(it["task"], []).append(it["id"])
    for task, ids in by_task.items():
        rng.shuffle(ids)
        cut = len(ids) // 2
        for i, pid in enumerate(ids):
            split_rows.append([pid, "public" if i < cut else "private"])
    # 按 id 排序输出，便于阅读
    split_rows.sort(key=lambda r: r[0])
    write_csv(os.path.join(OUT_DIR, "public_private_split.csv"),
              ["id", "split"], split_rows)

    pub = sum(1 for r in split_rows if r[1] == "public")
    print(f"[切分] 公开 {pub} / 私有 {len(split_rows) - pub}")
    print("[完成] 制品已生成于 kaggle/benchmark/dataset/")


if __name__ == "__main__":
    main()
