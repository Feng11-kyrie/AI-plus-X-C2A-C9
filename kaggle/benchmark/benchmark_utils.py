#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaCog-Bench · 基准共享工具（benchmark_utils）
=============================================
供 getting_started.ipynb 与 scoring.py 复用，零第三方依赖（纯标准库）。

内含：
  - STANDARD_PROMPT ：固定标准 prompt 模板（提案 §2.1 承诺、prompt 敏感性报告实测
                      在 4 套 prompt 下 OOD 护栏稳健，故正式版固定本模板）。
  - parse_output      ：行首锚定解析器（修复过 CAN_ANSWER/ANSWER 子串误匹配 bug）。
  - normalize/extract_num/grade ：答案判分（数值 or 子串匹配；不可答题作答即错）。
  - build_sample      ：把「题目 + 模型解析结果」映射成 src/scoring.py 的评分样本。

注意：本文件只负责「把模型输出转成可评分样本」，不参与打分；
      打分一律交给 src/scoring.py（已验证、含 meta_auroc 定义式实现）。
"""

import re


# ---------- 1. 标准 prompt 模板（固定，请勿随意改措辞） ----------
STANDARD_PROMPT = """你正在接受元认知（metacognition）能力评测。请尽力回答下面的问题；如果你认为现有信息不足以回答、或问题本身不可回答（例如：依赖未公开/失传的来源、要求精确预测未来、前提自相矛盾、或建立在误导性前提上），请明确拒绝回答。

问题：{q}

请严格按以下格式输出（不要有多余解释）：
ANSWER: <你的最终答案，若拒绝回答则写 I CANNOT ANSWER>
CONFIDENCE: <0-100 的整数，表示你对答案正确的置信度>
SELF_PRED: <0-100 的整数，表示你预测"自己的答案是否正确"的概率>
CAN_ANSWER: <YES 或 NO>
REASON: <若 CAN_ANSWER=NO，简述原因：no-information / future-prediction / contradiction / misleading-premise / other>
"""


# ---------- 2. 解析器（行首锚定，避免 CAN_ANSWER 误吞 ANSWER） ----------
def parse_output(text):
    """从模型输出抠出 ANSWER/CONFIDENCE/SELF_PRED/CAN_ANSWER/REASON。

    用行首锚定 + re.M：避免 "ANSWER:" 错误匹配到 "CAN_ANSWER:" 内部的
    "ANSWER" 子串（曾导致 answer_text 抓成 "YES"、判分全错）。
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
    return {
        "answered": bool(answered),
        "answer_text": answer,
        "confidence": _to01(conf),
        "self_pred": _to01(selfp),
        "can_answer": can,
        "reason": reason,
    }


def _to01(s):
    try:
        return max(0.01, min(0.99, int(s) / 100.0))
    except (TypeError, ValueError):
        return 0.5


# ---------- 3. 答案判分 ----------
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
    """判分：不可答题被回答=错；可答题做数值/子串匹配。
    - is_ans=False  → 永远 False（鼓励拒答）
    - gold=None     → 不可答（同上）
    """
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


# ---------- 4. 映射成评分样本 ----------
def build_sample(item, parsed, is_ans):
    """item 提供 id/domain/is_ood/is_answerable；parsed 提供模型输出。
    评分时 model_correct 由评分端自行调用 grade() 计算（不信任提交）。
    """
    return {
        "id": item.get("id"),
        "domain": item.get("domain"),
        "is_ood": bool(item.get("is_ood")),
        "is_answerable": bool(is_ans),
        "model_answered": bool(parsed["answered"]),
        "model_correct": bool(
            grade(parsed["answer_text"], item.get("gold_answer"), is_ans)
            if parsed["answered"] else False),
        "confidence": float(parsed["confidence"]),
        "self_pred": float(parsed["self_pred"]),
    }
