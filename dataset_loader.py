"""
dataset_loader.py
=================
Load dataset benchmark salmane11/SQLShield từ HuggingFace.

Dataset columns:
  - question : NLQ (natural language query)
  - query    : SQL query tương ứng (ground truth)
  - context  : Database schema (CREATE TABLE statements)
  - malicious: 1 = MALICIOUS, 0 = SAFE (ground truth label)

Splits: train (8000), validation (1800), test (1800)
"""
from datasets import load_dataset
from typing import Literal


def load_sqlshield(
    split: Literal["train", "validation", "test"] = "test",
    max_samples: int | None = None,
) -> list[dict]:
    """
    Load SQLShield benchmark dataset.

    Args:
        split      : "train" | "validation" | "test"
        max_samples: Giới hạn số mẫu (None = lấy toàn bộ split)

    Returns:
        List of dicts với keys: question, query, context, malicious, label_str
    """
    print(f"[dataset_loader] Loading salmane11/SQLShield ({split} split)...")
    ds = load_dataset("salmane11/SQLShield", split=split)

    if max_samples is not None:
        ds = ds.select(range(min(max_samples, len(ds))))

    samples = []
    for row in ds:
        malicious = int(row["malicious"])
        samples.append({
            "question" : row["question"],
            "query"    : row["query"],
            "context"  : row["context"],
            "malicious": malicious,
            "label_str": "MALICIOUS" if malicious == 1 else "SAFE",
        })

    n_mal  = sum(s["malicious"] for s in samples)
    n_safe = len(samples) - n_mal
    print(
        f"[dataset_loader] Loaded {len(samples)} samples — "
        f"MALICIOUS: {n_mal}, SAFE: {n_safe}"
    )
    return samples
