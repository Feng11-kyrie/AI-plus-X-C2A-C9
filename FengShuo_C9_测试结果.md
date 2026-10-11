# MetaCog-Bench · C9 模型测试结果

- **模型**：`deepseek-flash`（DeepSeek V4.1 Flash，当前 DeepSeek 最强）
- **推理档位**：`high`
- **测试题数**：200 / 200
- **估算花费**：¥0.392（用户上限 ¥3.0）
- **日期**：2026-10-11

## 评分报告（src/scoring.py，已修复 meta_auroc 算法）

- n_total: 200
- n_id: 161
- n_ood: 39
- TaskA_meta_accuracy: 0.6584
- TaskA_meta_auroc: 0.5050
- TaskB_ECE_ID: 0.3103
- TaskB_ECE_OOD: 0.6272
- TaskB_calibration_gap: 0.3169
- TaskB_brier_ID: 0.3130
### TaskC
- coverage: 0.6950
- acc_answered: 0.7698
- good_abstain_rate: 0.6721
- false_refusal_rate: 0.3279
- omniscience_index: 0.3711
- selective_auroc: 0.4943
