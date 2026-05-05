import json
import os
from dotenv import load_dotenv
load_dotenv()

from dataset_loader import load_sqlshield
from pipeline import SQLShieldPipeline

def main():
    print("=== TẢI 2 MẪU TỪ DATASET (1 ĐỘC HẠI, 1 AN TOÀN) ===")
    # Lấy 20 mẫu đầu tiên, sau đó chọn ra 1 mẫu SAFE và 1 mẫu MALICIOUS để minh họa
    samples = load_sqlshield(split="test", max_samples=50)
    
    malicious_sample = next(s for s in samples if s["malicious"] == 1)
    safe_sample = next(s for s in samples if s["malicious"] == 0)

    # Khởi tạo Pipeline (Central Agent)
    pipeline = SQLShieldPipeline(use_nlq_shield=True, use_sql_shield=True)
    
    def trace(sample, label):
        print("\n" + "="*70)
        print(f"BẮT ĐẦU TRACE MỘT CÂU HỎI ({label})")
        print("="*70)
        
        question = sample["question"]
        context = sample["context"]
        
        print(f"\n🎯 [User Input]: \n  '{question}'")
        print(f"📖 [Database Schema Context]: \n  '{context}'")
        
        print("\n▶ LỚP 1: SQLPromptShield (Tool 1)")
        print(f"  - Đầu vào : {question}")
        verdict1, _, _ = pipeline._nlq_shield.predict(question)
        print(f"  - Đầu ra  : {verdict1}")
        
        if verdict1 == "MALICIOUS":
            print("\n❌ Central Agent: Phát hiện độc hại ở Lớp 1. NGẮT QUÁ TRÌNH. Báo ALERT cho user.")
            return

        print("\n▶ LỚP 2: Text-to-SQL Generator (Tool 2 - Gemini)")
        print(f"  - Đầu vào : (NLQ an toàn) + (Schema Context)")
        try:
            sql = pipeline._generate_sql(question, context)
            print(f"  - Đầu ra  : {sql}")
        except Exception as e:
            print(f"  - Đầu ra  : LỖI GỌI API GEMINI ({e})")
            return
            
        print("\n▶ LỚP 3: SQLQueryShield (Tool 3)")
        print(f"  - Đầu vào : {sql}")
        verdict2, _, _ = pipeline._sql_shield.predict(sql)
        print(f"  - Đầu ra  : {verdict2}")

        if verdict2 == "MALICIOUS":
            print("\n❌ Central Agent: Phát hiện mã độc ẩn trong SQL ở Lớp 3. NGẮT QUÁ TRÌNH. Báo ALERT cho user.")
            return

        print("\n▶ LỚP 4: SQL-Executor (Tool 4 - Tương tác DB)")
        print(f"  - Đầu vào : {sql}")
        print(f"  - Đầu ra  : [Dữ liệu trích xuất từ DB trả về cho Central Agent]")
        print("\n✅ Central Agent: Trả dữ liệu an toàn về cho người dùng.")

    trace(malicious_sample, "MẪU CÓ MÃ ĐỘC - PROMPT INJECTION")
    trace(safe_sample, "MẪU AN TOÀN - NGƯỜI DÙNG BÌNH THƯỜNG")

if __name__ == "__main__":
    main()
