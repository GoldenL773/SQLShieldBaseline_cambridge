# SQLShield Baseline

Tái hiện pipeline bảo mật Text-to-SQL từ bài báo **SQLShield** dưới dạng Python baseline độc lập, phục vụ mục đích đánh giá định lượng (benchmark & ablation study).

## Kiến trúc Pipeline

```
NLQ (User Input)
    │
    ▼
[Layer 1] NLQShield (salmane11/SQLPromptShield — BERT)
    │  MALICIOUS → BLOCKED
    │  SAFE ↓
    ▼
[Layer 2] SQL Generator (Gemini 2.5 Flash)
    │
    ▼
[Layer 3] SQLShield (salmane11/SQLQueryShield — CodeBERT)
    │  MALICIOUS → BLOCKED
    │  SAFE ↓
    ▼
[Layer 4] Mock Executor → "Mock: OK"
```

## Cấu trúc Project

```
SQLShieldBaseline/
├── shields.py          # HuggingFace model wrappers (NLQShield + SQLShield)
├── sql_generator.py    # Gemini 2.5 Flash Text-to-SQL + Mock Executor
├── pipeline.py         # Core pipeline 4-bước (có hỗ trợ ablation)
├── dataset_loader.py   # Load salmane11/SQLShield từ HuggingFace
├── evaluator.py        # Multi-metric: Security Accuracy, ABR, FPR, Latency
├── run_eval.py         # CLI runner
├── requirements.txt
└── .env.example
```

## Cài đặt

```bash
pip install -r requirements.txt
```

Tạo file `.env` từ template:
```bash
copy .env.example .env
# Sau đó điền GEMINI_API_KEY vào file .env
```

## Chạy Evaluation

### Full pipeline (cả 2 shield)
```bash
python run_eval.py --mode full --split test
```

### Ablation Study
```bash
# Tắt NLQShield (Layer 1) — đánh giá đóng góp của PromptShield
python run_eval.py --mode no-prompt-shield

# Tắt SQLShield (Layer 2) — đánh giá đóng góp của QueryShield
python run_eval.py --mode no-query-shield

# Không có shield nào — baseline thuần
python run_eval.py --mode no-shield
```

### Chỉ benchmark shield (không gọi LLM, dùng SQL gốc từ dataset)
```bash
python run_eval.py --mode full --skip-sql-gen --max 200
```

### Giới hạn số mẫu (tránh API rate limit)
```bash
python run_eval.py --mode full --max 50
```

## Metrics

| Metric | Ý nghĩa |
|---|---|
| Security Accuracy | (TP+TN) / Total |
| Attack Block Rate | TP / (TP+FN) — Recall trên MALICIOUS |
| False Positive Rate | FP / (FP+TN) — Chặn nhầm SAFE |
| Avg NLQ Latency (ms) | Thời gian trung bình của NLQShield |
| Avg SQL Latency (ms) | Thời gian trung bình của SQLShield |

## Dataset

- **salmane11/SQLShield** (HuggingFace): 11,600 samples (train/val/test)
- Labels: `malicious=1` (MALICIOUS), `malicious=0` (SAFE)
- Bao gồm: SR, SQ, MPV, BRP attack types + benign samples

## Paper Reference

> *SQLShield: Securing Text-to-SQL Integrated Applications against Prompt Injections*
> Models: `salmane11/SQLPromptShield`, `salmane11/SQLQueryShield`
> Dataset: `salmane11/SQLShield`
