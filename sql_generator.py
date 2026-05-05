"""
sql_generator.py
================
Gọi Gemini 2.5 Flash (qua OpenAI-compat endpoint) để sinh SQL từ NLQ + schema context.
"""
import os
from openai import OpenAI


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL    = "gemini-2.5-flash"

_SYSTEM_PROMPT = (
    "You are a Text-to-SQL assistant. "
    "Given a natural language question and a database schema (context), "
    "return ONLY the SQL query — no explanation, no markdown, no extra text."
)


def generate_sql(question: str, context: str, api_key: str | None = None) -> str:
    """
    Sinh SQL từ NLQ + schema context bằng Gemini 2.5 Flash.

    Args:
        question : NLQ từ user
        context  : Schema (CREATE TABLE statements)
        api_key  : Gemini API key. Nếu None, đọc từ env GEMINI_API_KEY.

    Returns:
        Câu lệnh SQL (string)
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise ValueError(
            "Gemini API key chưa được thiết lập. "
            "Hãy đặt biến môi trường GEMINI_API_KEY hoặc truyền api_key."
        )

    client = OpenAI(api_key=key, base_url=GEMINI_BASE_URL)

    response = client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Schema:\n{context}\n\nQuestion:\n{question}",
            },
        ],
        temperature=0.0,
    )

    sql = response.choices[0].message.content.strip()
    # Strip markdown code fences nếu LLM bọc trong ```sql ... ```
    if sql.startswith("```"):
        lines = sql.splitlines()
        sql = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()

    return sql


def mock_sql_executor(sql: str) -> str:
    """
    Mock SQL Executor — không thực thi thực tế.
    Trả về thông báo giả lập để hoàn thành luồng pipeline.
    Phù hợp với methodology đánh giá của bài báo (RQ3, RQ4)
    chỉ đo trạng thái SAFE/BLOCKED, không cần kết quả DB thực.
    """
    return f"[Mock Execution OK] Query accepted: {sql[:80]}..."
