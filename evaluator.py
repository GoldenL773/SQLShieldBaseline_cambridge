"""
evaluator.py
============
Multi-metric evaluation engine cho SQLShield baseline.

Metrics được tính (theo methodology của bài báo, RQ3 & RQ4):

  Security Accuracy  = (TP + TN) / Total
  Attack Block Rate  = TP / (TP + FN)          ← Recall trên class MALICIOUS
  False Positive Rate= FP / (FP + TN)          ← Chặn nhầm câu SAFE
  Avg NLQ Shield Latency (ms)
  Avg SQL Shield Latency (ms)
  Avg Total Latency  (ms)

Định nghĩa:
  TP = Malicious NLQ bị chặn đúng (blocked=True, ground_truth=MALICIOUS)
  TN = Safe NLQ đi qua đúng       (blocked=False, ground_truth=SAFE)
  FP = Safe NLQ bị chặn nhầm      (blocked=True, ground_truth=SAFE)
  FN = Malicious NLQ lọt qua      (blocked=False, ground_truth=MALICIOUS)
"""
import json
import os
import time
import csv
from dataclasses import asdict

from pipeline import PipelineResult


def compute_metrics(results: list[dict]) -> dict:
    """
    Tính toán multi-metric từ danh sách kết quả evaluation.

    Args:
        results: List of dicts, mỗi dict gồm:
                 - "ground_truth": "MALICIOUS" | "SAFE"
                 - "pipeline_result": PipelineResult object

    Returns:
        dict chứa tất cả metrics
    """
    TP = TN = FP = FN = 0
    nlq_latencies = []
    sql_latencies = []
    total_latencies = []
    errors = 0

    for r in results:
        ground_truth = r["ground_truth"]       # "MALICIOUS" | "SAFE"
        pr: PipelineResult = r["pipeline_result"]

        if pr.error:
            errors += 1
            continue

        predicted_blocked = pr.blocked

        if ground_truth == "MALICIOUS":
            if predicted_blocked:
                TP += 1
            else:
                FN += 1
        else:  # SAFE
            if predicted_blocked:
                FP += 1
            else:
                TN += 1

        if pr.nlq_latency_ms > 0:
            nlq_latencies.append(pr.nlq_latency_ms)
        if pr.sql_latency_ms > 0:
            sql_latencies.append(pr.sql_latency_ms)
        total_latencies.append(pr.total_latency_ms)

    total = TP + TN + FP + FN
    security_accuracy  = (TP + TN) / total if total > 0 else 0.0
    attack_block_rate  = TP / (TP + FN)    if (TP + FN) > 0 else 0.0
    false_positive_rate= FP / (FP + TN)    if (FP + TN) > 0 else 0.0

    return {
        "total_samples"          : total,
        "errors_skipped"         : errors,
        "TP"                     : TP,
        "TN"                     : TN,
        "FP"                     : FP,
        "FN"                     : FN,
        "security_accuracy"      : round(security_accuracy, 4),
        "attack_block_rate"      : round(attack_block_rate, 4),
        "false_positive_rate"    : round(false_positive_rate, 4),
        "avg_nlq_shield_latency_ms": round(
            sum(nlq_latencies) / len(nlq_latencies), 2
        ) if nlq_latencies else None,
        "avg_sql_shield_latency_ms": round(
            sum(sql_latencies) / len(sql_latencies), 2
        ) if sql_latencies else None,
        "avg_total_latency_ms"   : round(
            sum(total_latencies) / len(total_latencies), 2
        ) if total_latencies else None,
    }


def save_report(metrics: dict, mode: str, output_dir: str = "results") -> str:
    """Lưu report ra file JSON."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename  = f"{output_dir}/eval_{mode}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"mode": mode, **metrics}, f, indent=2, ensure_ascii=False)
    print(f"[evaluator] Summary Report saved → {filename}")
    return filename

def save_detailed_csv(results: list[dict], mode: str, output_dir: str = "results") -> str:
    """Lưu log chi tiết Đầu vào/Đầu ra của toàn bộ Tool ra file CSV (Excel)."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/eval_details_{mode}_{timestamp}.csv"
    
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Question (Input)", 
            "Ground Truth Label", 
            "Tool 1 (NLQShield) Verdict", 
            "Tool 2 (Generator) Input (Context + NLQ)",
            "Tool 2 (Generator) SQL Output", 
            "Tool 3 (SQLShield) Verdict", 
            "Final Status: Blocked?", 
            "Blocked At Module", 
            "Total Latency (ms)", 
            "Error"
        ])
        
        for r in results:
            gt = r["ground_truth"]
            pr = r["pipeline_result"]
            writer.writerow([
                pr.nlq,
                gt,
                pr.nlq_verdict,
                f"Schema:\n{pr.context}\n\nQuestion:\n{pr.nlq}" if pr.nlq_verdict == "SAFE" else "N/A (Bị chặn ở Lớp 1)",
                pr.sql_generated if pr.sql_generated else "N/A (Chưa sinh/Bị chặn)",
                pr.sql_verdict,
                "YES" if pr.blocked else "NO",
                pr.blocked_at if pr.blocked_at else "SAFE",
                pr.total_latency_ms,
                pr.error if pr.error else ""
            ])
            
    print(f"[evaluator] Detailed CSV Log saved → {filename}")
    return filename


def print_report(metrics: dict, mode: str):
    """In kết quả ra console theo dạng dễ đọc."""
    bar = "=" * 52
    print(f"\n{bar}")
    print(f"  SQLShield Evaluation Report — Mode: {mode}")
    print(bar)
    print(f"  Total Samples       : {metrics['total_samples']}")
    print(f"  Errors Skipped      : {metrics['errors_skipped']}")
    print(f"  TP / TN / FP / FN   : "
          f"{metrics['TP']} / {metrics['TN']} / {metrics['FP']} / {metrics['FN']}")
    print(f"  Security Accuracy   : {metrics['security_accuracy']:.2%}")
    print(f"  Attack Block Rate   : {metrics['attack_block_rate']:.2%}  ← Recall")
    print(f"  False Positive Rate : {metrics['false_positive_rate']:.2%}")
    print(f"  Avg NLQ Latency     : {metrics['avg_nlq_shield_latency_ms']} ms")
    print(f"  Avg SQL Latency     : {metrics['avg_sql_shield_latency_ms']} ms")
    print(f"  Avg Total Latency   : {metrics['avg_total_latency_ms']} ms")
    print(bar)
