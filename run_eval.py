"""
run_eval.py
===========
CLI runner cho SQLShield Baseline Evaluation.

Cách chạy:
  python run_eval.py --mode full                # Full pipeline (cả 2 shield)
  python run_eval.py --mode no-prompt-shield    # Ablation: tắt NLQShield
  python run_eval.py --mode no-query-shield     # Ablation: tắt SQLShield
  python run_eval.py --mode no-shield           # Baseline không bảo vệ

Options:
  --split     : train | validation | test  (default: test)
  --max        : Giới hạn số mẫu          (default: None = toàn bộ)
  --output-dir : Thư mục lưu report       (default: results/)
  --skip-sql-gen : Bỏ qua bước gọi LLM (chỉ đánh giá Shield trên NLQ/SQL gốc)
"""
import argparse
import os
import sys
import io
import time

# Fix encoding trên Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from dataset_loader import load_sqlshield
from pipeline import SQLShieldPipeline
from evaluator import compute_metrics, print_report, save_report, save_detailed_csv


MODES = {
    "full"            : {"use_nlq_shield": True,  "use_sql_shield": True},
    "no-prompt-shield": {"use_nlq_shield": False, "use_sql_shield": True},
    "no-query-shield" : {"use_nlq_shield": True,  "use_sql_shield": False},
    "no-shield"       : {"use_nlq_shield": False, "use_sql_shield": False},
}


def run_evaluation(
    mode: str,
    split: str,
    max_samples: int | None,
    output_dir: str,
    skip_sql_gen: bool,
):
    print(f"\n[run_eval] Mode: {mode} | Split: {split} | Max: {max_samples or 'all'}")
    print(f"[run_eval] Skip SQL Generation: {skip_sql_gen}")

    # ── Load dataset ──────────────────────────────────────────────────────
    samples = load_sqlshield(split=split, max_samples=max_samples)

    # ── Khởi tạo pipeline ─────────────────────────────────────────────────
    cfg = MODES[mode]

    if skip_sql_gen:
        # Khi skip_sql_gen=True: dùng SQL từ dataset (ground truth query)
        # thay vì gọi LLM. Giúp evaluate shield thuần tuý, không phụ thuộc API.
        def _mock_gen(question, context=""):
            # Tìm SQL gốc từ dataset — lấy qua closure của vòng for bên dưới
            return _current_sql[0]
        generate_fn = _mock_gen
    else:
        generate_fn = None  # Dùng Gemini mặc định

    pipeline = SQLShieldPipeline(
        use_nlq_shield=cfg["use_nlq_shield"],
        use_sql_shield=cfg["use_sql_shield"],
        generate_sql_fn=generate_fn,
    )

    # ── Chạy evaluation ───────────────────────────────────────────────────
    eval_results = []
    _current_sql = [""]   # Mutable closure cho mock generator

    print(f"\n[run_eval] Running {len(samples)} samples...\n")
    t_start = time.perf_counter()

    for i, sample in enumerate(samples):
        _current_sql[0] = sample["query"]  # Cập nhật SQL gốc cho mock

        pr = pipeline.run(
            question=sample["question"],
            context=sample["context"],
        )

        eval_results.append({
            "ground_truth"   : sample["label_str"],
            "pipeline_result": pr,
        })

        # Progress bar mỗi 50 mẫu
        if (i + 1) % 50 == 0 or (i + 1) == len(samples):
            elapsed = round(time.perf_counter() - t_start, 1)
            print(f"  [{i+1}/{len(samples)}] elapsed: {elapsed}s")

    # ── Tính metrics & lưu report ─────────────────────────────────────────
    metrics = compute_metrics(eval_results)
    print_report(metrics, mode)
    save_report(metrics, mode, output_dir)
    save_detailed_csv(eval_results, mode, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="SQLShield Baseline Evaluation CLI"
    )
    parser.add_argument(
        "--mode",
        choices=list(MODES.keys()),
        default="full",
        help="Chế độ chạy: full | no-prompt-shield | no-query-shield | no-shield",
    )
    parser.add_argument(
        "--split",
        choices=["train", "validation", "test"],
        default="test",
        help="Dataset split (default: test)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        metavar="N",
        help="Giới hạn số mẫu (mặc định: toàn bộ split)",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Thư mục lưu report JSON (default: results/)",
    )
    parser.add_argument(
        "--skip-sql-gen",
        action="store_true",
        help=(
            "Bỏ qua bước gọi Gemini — dùng SQL gốc từ dataset. "
            "Nên dùng khi chỉ muốn benchmark tốc độ/độ chính xác của Shield."
        ),
    )

    args = parser.parse_args()

    run_evaluation(
        mode        = args.mode,
        split       = args.split,
        max_samples = args.max,
        output_dir  = args.output_dir,
        skip_sql_gen= args.skip_sql_gen,
    )


if __name__ == "__main__":
    main()
