#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaCog-Bench 评分脚手架（最小可用版本 v0.1）
===========================================
赛道：Track 2 元认知（Metacognition）
定位：单干实现底座 —— 把 proposal 里的指标落成可跑代码

覆盖指标（对应 DeepMind §7.7 三层）：
- Task A (L1 元认知知识)：meta_accuracy、meta_auroc
- Task B (L2 监控校准)：ECE_ID、ECE_OOD、calibration_gap、brier
- Task C (L3 策略性拒答)：Omniscience Index、false_refusal_rate
- 附加：selective_auroc（risk-coverage 辅助）

纯标准库，无第三方依赖，python3 直接跑：
    python3 src/scoring.py
"""

from collections import defaultdict
import random


# ---------- 数据格式约定 ----------
# 每条样本是一个 dict，字段含义：
#   id              : 样本编号（字符串）
#   domain          : 领域，如 "math" / "law" / "biology"
#   is_ood          : 是否属于 OOD 转移集（Task B 区分 ID/OOD）
#   is_answerable   : 题目本身是否可答（不可答题用于 Task C）
#   model_answered  : 模型是否给出答案（False = 拒答/abstain）
#   model_correct   : 模型答案是否正确（拒答项填 False 即可）
#   confidence      : 模型对"答案正确"的置信度，0~1（Task B 用）
#   self_pred       : 模型预测"我会答对吗"的概率，0~1（Task A 用）
SAMPLE_FIELDS = ["id", "domain", "is_ood", "is_answerable",
                 "model_answered", "model_correct", "confidence", "self_pred"]


# ---------- Task B：校准（L2 监控） ----------
def expected_calibration_error(confidences, corrects, n_bins=10):
    """ECE：把置信度分桶，算 |准确率 - 平均置信| 的加权差。越小越校准。"""
    bins = defaultdict(list)
    for c, ok in zip(confidences, corrects):
        b = min(int(c * n_bins), n_bins - 1)
        bins[b].append((c, ok))
    n = len(confidences)
    ece = 0.0
    for items in bins.values():
        m = len(items)
        if m == 0:
            continue
        avg_conf = sum(x[0] for x in items) / m
        avg_acc = sum(1 for x in items if x[1]) / m
        ece += (m / n) * abs(avg_acc - avg_conf)
    return ece


def brier_score(confidences, corrects):
    """Brier：预测概率与 0/1 真值的均方误差。越小越准。"""
    n = len(confidences)
    return sum((c - (1.0 if ok else 0.0)) ** 2 for c, ok in zip(confidences, corrects)) / n


# ---------- Task A：元认知知识（L1） ----------
def meta_accuracy(self_preds, corrects):
    """把 self_pred(0~1) 二值化为"预测会答对/不会"，再与实际答对比准确率。"""
    pred = [1 if p >= 0.5 else 0 for p in self_preds]
    actual = [1 if ok else 0 for ok in corrects]
    n = len(self_preds)
    return sum(1 for p, a in zip(pred, actual) if p == a) / n


def meta_auroc(self_preds, corrects):
    """self_pred 区分"会答对/不会答对"的 AUROC。越高越能预判自己成败。

    实现：按定义直接枚举所有 (正样本, 负样本) 对计数
          AUROC = (#(pos > neg) + 0.5 * #(pos == neg)) / (|pos| * |neg|)
    规模（数百样本）下暴力计数完全够用，且对浮点边界稳健，
    避免早期二分查找在 0.99 这类 int/100 值上因浮点比较失灵的问题。
    """
    pos = [p for p, ok in zip(self_preds, corrects) if ok]
    neg = [p for p, ok in zip(self_preds, corrects) if not ok]
    if not pos or not neg:
        return None
    n_pos, n_neg = len(pos), len(neg)
    wins = 0.0
    for pv in pos:
        for nv in neg:
            if pv > nv:
                wins += 1.0
            elif pv == nv:
                wins += 0.5
    return wins / (n_pos * n_neg)


# ---------- Task C：策略性拒答（L3 控制） ----------
def omniscience_index(samples):
    """衡量"知道什么不知道"（Omniscience）。
    - coverage            : 作答覆盖率
    - acc_answered        : 作答里的准确率
    - good_abstain_rate   : 拒答里真正不可答的比例
    - false_refusal_rate  : 把可答题拒了的比例（越低越好）
    - omniscience_index   : coverage*acc - 0.5*false_refusal（代理指标）
    """
    answered = [s for s in samples if s["model_answered"]]
    abstained = [s for s in samples if not s["model_answered"]]
    n = len(samples)
    coverage = len(answered) / n if n else 0.0
    acc_answered = (sum(1 for s in answered if s["model_correct"]) / len(answered)
                    if answered else 0.0)
    good_abstain = (sum(1 for s in abstained if not s["is_answerable"]) / len(abstained)
                    if abstained else 0.0)
    false_refusal = (sum(1 for s in abstained if s["is_answerable"]) / len(abstained)
                     if abstained else 0.0)
    omni = coverage * acc_answered - 0.5 * false_refusal
    return {
        "coverage": coverage,
        "acc_answered": acc_answered,
        "good_abstain_rate": good_abstain,
        "false_refusal_rate": false_refusal,
        "omniscience_index": omni,
    }


# ---------- 附加：selective prediction AUROC ----------
def selective_auroc(confidences, corrects):
    """置信度越高越该答对：AUROC(confidence, correct)。
    越高说明模型越能靠置信度筛掉错误。"""
    return meta_auroc(confidences, corrects)


# ---------- 汇总报告 ----------
def evaluate(samples):
    id_samples = [s for s in samples if not s["is_ood"]]
    ood_samples = [s for s in samples if s["is_ood"]]

    def split(lst):
        return ([s["confidence"] for s in lst],
                [s["model_correct"] for s in lst],
                [s["self_pred"] for s in lst])

    id_c, id_ok, id_sp = split(id_samples)
    ood_c, ood_ok, ood_sp = split(ood_samples)

    ece_id = expected_calibration_error(id_c, id_ok)
    ece_ood = expected_calibration_error(ood_c, ood_ok)

    report = {
        "n_total": len(samples),
        "n_id": len(id_samples),
        "n_ood": len(ood_samples),
        "TaskA_meta_accuracy": meta_accuracy(id_sp, id_ok),
        "TaskA_meta_auroc": meta_auroc(id_sp, id_ok),
        "TaskB_ECE_ID": ece_id,
        "TaskB_ECE_OOD": ece_ood,
        "TaskB_calibration_gap": ece_ood - ece_id,   # 关键判别器
        "TaskB_brier_ID": brier_score(id_c, id_ok),
        "TaskC": omniscience_index(samples),
        "selective_auroc": selective_auroc(id_c, id_ok),
    }
    return report


# ---------- 演示用假数据（真实提交时换成模型输出） ----------
def demo_samples(n_per_domain=40, seed=2026):
    random.seed(seed)
    samples = []
    domains = {"math": 0.25, "law": 0.5, "biology": 0.4}  # 不同领域基线正确率
    for dom, base_acc in domains.items():
        for i in range(n_per_domain):
            is_ood = (i % 2 == 0)  # 一半当 OOD 转移
            acc = base_acc * (0.6 if is_ood else 1.0)  # OOD 上准确率下降
            correct = random.random() < acc
            conf = min(0.99, max(0.05, acc + random.uniform(-0.15, 0.15)))
            self_pred = min(0.99, max(0.01, (1 if correct else 0) * 0.7 + acc * 0.3))
            is_ans = random.random() > 0.15               # 部分题目不可答
            answered = is_ans and (random.random() < 0.9 or conf > 0.5)
            samples.append({
                "id": f"{dom}-{i}", "domain": dom, "is_ood": is_ood,
                "is_answerable": is_ans, "model_answered": answered,
                "model_correct": correct and answered,
                "confidence": conf, "self_pred": self_pred,
            })
    return samples


def main():
    samples = demo_samples()
    rep = evaluate(samples)
    print("=" * 52)
    print("MetaCog-Bench 评分报告（演示数据，非真实模型）")
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
    print("\n提示：把 demo_samples() 换成你模型的真实输出（dict 列表）即可复用全部指标。")


if __name__ == "__main__":
    main()
