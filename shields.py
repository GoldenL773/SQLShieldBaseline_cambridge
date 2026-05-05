"""
shields.py
==========
Wrappers cho 2 HuggingFace models từ bài báo SQLShield (khớp với file Notebook):
  - NLQShield  : salmane11/SQLPromptShield4  (BERT-based, lọc câu hỏi NLQ)
  - SQLShield  : salmane11/SQLQueryShield    (CodeBERT-based, lọc câu SQL)

Mỗi shield trả về: "SAFE" hoặc "MALICIOUS"
"""
import time
from transformers import pipeline


class NLQShield:
    """
    Layer 1 — SQLPromptShield (bert-base-uncased fine-tuned).
    Phát hiện câu hỏi ngôn ngữ tự nhiên độc hại TRƯỚC khi sinh SQL.
    """

    def __init__(self, device: int = -1):
        """
        Args:
            device: -1 = CPU, 0 = GPU (nếu có CUDA)
        """
        print("[NLQShield] Loading salmane11/SQLPromptShield4...")
        self._pipe = pipeline(
            "text-classification",
            model="salmane11/SQLPromptShield4",
            device=device,
        )
        print("[NLQShield] Ready.")

    def predict(self, question: str) -> tuple[str, float, float]:
        """
        Returns:
            verdict  : "SAFE" | "MALICIOUS"
            score    : confidence score của verdict
            latency_ms: thời gian inference (ms)
        """
        t0 = time.perf_counter()
        result = self._pipe(question)[0]
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        label = result["label"].upper()
        # Normalize về SAFE / MALICIOUS
        if label not in ("SAFE", "MALICIOUS"):
            label = "MALICIOUS"  # conservative fallback

        return label, result["score"], latency_ms


class SQLShield:
    """
    Layer 2 — SQLQueryShield (codebert-base fine-tuned).
    Kiểm tra câu lệnh SQL do LLM sinh ra TRƯỚC khi thực thi.
    Là chốt chặn quan trọng chống Backdoor attacks.
    """

    def __init__(self, device: int = -1):
        print("[SQLShield] Loading salmane11/SQLQueryShield...")
        self._pipe = pipeline(
            "text-classification",
            model="salmane11/SQLQueryShield",
            device=device,
        )
        print("[SQLShield] Ready.")

    def predict(self, sql: str) -> tuple[str, float, float]:
        """
        Returns:
            verdict   : "SAFE" | "MALICIOUS"
            score     : confidence score
            latency_ms: thời gian inference (ms)
        """
        t0 = time.perf_counter()
        result = self._pipe(sql)[0]
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        label = result["label"].upper()
        if label not in ("SAFE", "MALICIOUS"):
            label = "MALICIOUS"

        return label, result["score"], latency_ms
