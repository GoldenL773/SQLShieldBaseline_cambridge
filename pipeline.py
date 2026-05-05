"""
pipeline.py
===========
Core pipeline 4-bước theo kiến trúc Agent-based của bài báo SQLShield.

Flow:
  NLQ → [NLQShield] → (nếu SAFE) → [SQL Generator] → [SQLShield] → [Mock Executor]
                   ↓ MALICIOUS                      ↓ MALICIOUS
                 BLOCKED                          BLOCKED

Mỗi lần chạy trả về PipelineResult với đầy đủ thông tin để tính metrics.
"""
import time
from dataclasses import dataclass, field
from typing import Optional

from shields import NLQShield, SQLShield
from sql_generator import generate_sql, mock_sql_executor


@dataclass
class PipelineResult:
    nlq: str
    context: str = ""
    # --- Shield 1 ---
    nlq_verdict: str = ""          # "SAFE" | "MALICIOUS"
    nlq_score: float = 0.0
    nlq_latency_ms: float = 0.0
    # --- SQL Generator ---
    sql_generated: Optional[str] = None
    # --- Shield 2 ---
    sql_verdict: str = ""          # "SAFE" | "MALICIOUS"
    sql_score: float = 0.0
    sql_latency_ms: float = 0.0
    # --- Executor ---
    mock_result: Optional[str] = None
    # --- Tổng hợp ---
    blocked: bool = False
    blocked_at: Optional[str] = None   # "nlq_shield" | "sql_shield" | None
    total_latency_ms: float = 0.0
    error: Optional[str] = None


class SQLShieldPipeline:
    """
    Pipeline tái hiện hệ thống Agent-based của bài báo SQLShield.
    
    Chế độ ablation (dùng để Ablation Study):
      - use_nlq_shield : bật/tắt Layer 1 (NLQShield)
      - use_sql_shield : bật/tắt Layer 2 (SQLShield)
    """

    def __init__(
        self,
        use_nlq_shield: bool = True,
        use_sql_shield: bool = True,
        generate_sql_fn=None,
        device: int = -1,
    ):
        self.use_nlq_shield = use_nlq_shield
        self.use_sql_shield = use_sql_shield

        # Lazy-load chỉ những shield được bật
        self._nlq_shield: Optional[NLQShield] = (
            NLQShield(device=device) if use_nlq_shield else None
        )
        self._sql_shield: Optional[SQLShield] = (
            SQLShield(device=device) if use_sql_shield else None
        )

        # Cho phép inject custom sql generator (dùng trong test)
        self._generate_sql = generate_sql_fn or generate_sql

    def run(self, question: str, context: str = "") -> PipelineResult:
        """
        Chạy toàn bộ pipeline cho 1 câu hỏi.
        
        Args:
            question : NLQ từ user
            context  : Database schema (CREATE TABLE statements)
        
        Returns:
            PipelineResult với đầy đủ thông tin các bước
        """
        result = PipelineResult(nlq=question, context=context)
        t_total = time.perf_counter()

        try:
            # ── Bước 1: NLQShield (Layer 1) ──────────────────────────────
            if self.use_nlq_shield:
                verdict, score, lat = self._nlq_shield.predict(question)
                result.nlq_verdict    = verdict
                result.nlq_score      = score
                result.nlq_latency_ms = lat

                if verdict == "MALICIOUS":
                    result.blocked    = True
                    result.blocked_at = "nlq_shield"
                    result.total_latency_ms = round(
                        (time.perf_counter() - t_total) * 1000, 2
                    )
                    return result
            else:
                result.nlq_verdict = "SKIPPED"

            # ── Bước 2: Text-to-SQL Generator ────────────────────────────
            try:
                sql = self._generate_sql(question=question, context=context)
            except Exception as e:
                result.error = f"SQL Generator error: {e}"
                result.total_latency_ms = round(
                    (time.perf_counter() - t_total) * 1000, 2
                )
                return result

            result.sql_generated = sql

            # ── Bước 3: SQLShield (Layer 2) ──────────────────────────────
            if self.use_sql_shield:
                verdict, score, lat = self._sql_shield.predict(sql)
                result.sql_verdict    = verdict
                result.sql_score      = score
                result.sql_latency_ms = lat

                if verdict == "MALICIOUS":
                    result.blocked    = True
                    result.blocked_at = "sql_shield"
                    result.total_latency_ms = round(
                        (time.perf_counter() - t_total) * 1000, 2
                    )
                    return result
            else:
                result.sql_verdict = "SKIPPED"

            # ── Bước 4: Mock SQL Executor ─────────────────────────────────
            result.mock_result = mock_sql_executor(sql)

        except Exception as e:
            result.error = str(e)

        result.total_latency_ms = round(
            (time.perf_counter() - t_total) * 1000, 2
        )
        return result
