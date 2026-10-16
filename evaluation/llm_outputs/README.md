# Output LLM thật (đánh giá #2)

Thư mục này chứa output **thật** của LLM do `scripts/run_llm_eval.py` sinh ra, mỗi tệp một hồ sơ:
`<model>/<case_id>.json` (schema `creditlens-llm-eval-v1`). Nội dung đã giả danh hóa (KH_01, DN_A; ngày chỉ giữ tháng/năm)
và không bao giờ chứa API key. `evaluation/llm_live.py` chấm offline các tệp này (không gọi API); trang Evaluation
hiển thị kết quả ở mục "Đánh giá output LLM thật", tách khỏi số liệu mô phỏng.

```bash
export GEMINI_API_KEY=...        # khóa của người chạy, không ghi vào repo
python scripts/run_llm_eval.py --model gemini-3.8-flash --cases 12 --sleep 6
```
