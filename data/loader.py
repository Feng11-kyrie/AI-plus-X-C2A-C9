#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaCog-Bench 数据加载器（单干底座）
读取 data/sample_items.json，映射到 src/scoring.py 的评分格式并打印报告。

运行：python3 data/loader.py
用户只需编辑 sample_items.json，无需改本文件。
"""
import json
import os
import sys

# 把仓库根目录加入路径，便于 import src/scoring.py
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.scoring import evaluate  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS_PATH = os.path.join(HERE, "sample_items.json")


def load_samples(path=ITEMS_PATH):
    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)
    samples = []
    for it in items:
        mr = it.get("model_response", {})
        samples.append({
            "id": it["id"],
            "domain": it["domain"],
            "is_ood": it["is_ood"],
            "is_answerable": it["is_answerable"],
            "model_answered": bool(mr.get("answered", False)),
            "model_correct": bool(mr.get("is_correct", False)),
            "confidence": float(mr.get("confidence", 0.0)),
            "self_pred": float(mr.get("self_predict_correct", 0.0)),
        })
    return samples


def main():
    if not os.path.exists(ITEMS_PATH):
        print(f"未找到 {ITEMS_PATH}，请先创建 sample_items.json")
        return
    samples = load_samples()
    rep = evaluate(samples)
    print("=" * 52)
    print("MetaCog-Bench 评分报告（来自 sample_items.json）")
    print("=" * 52)
    for k, v in rep.items():
        if isinstance(v, dict):
            print(f"\n[{k}]")
            for kk, vv in v.items():
                if isinstance(vv, float):
                    print(f"  {kk:22s}: {vv:.4f}")
                else:
                    print(f"  {kk:22s}: {vv}")
        elif isinstance(v, float):
            print(f"{k:28s}: {v:.4f}")
        else:
            print(f"{k:28s}: {v}")
    print("\n注意：model_response 当前为占位示例值，需替换为真实模型输出后重跑。")


if __name__ == "__main__":
    main()
