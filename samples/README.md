# Mẫu nộp bài — dữ liệu tổng hợp

Toàn bộ dữ liệu trong thư mục này là **giả lập**. Tên người, CCCD, số điện thoại, email, địa chỉ và số tài khoản đều không có thật.

| Mục | Nội dung |
|---|---|
| `HOSO-MAU-EVAL-004/` | 4 PDF của một hồ sơ (đơn đề nghị vay, chứng từ thu nhập, sao kê ngân hàng, nghĩa vụ nợ), sinh bằng `tests/fixtures/synthetic_pdfs.py` từ kịch bản gold `EVAL-004 — Thu nhập chênh lệch đáng kể`. Dùng để demo “Tải cả thư mục hồ sơ” ở Bước 0. |
| `credit_review_summary_EVAL-004.md` / `.json` | Credit Review Summary mẫu 10 mục cho đúng hồ sơ trên, **đã giả danh hóa** (`KH_01`, `DN_A`), lấy từ **output LLM thật** (`gemini-3.6-flash`, lưu tại `evaluation/llm_outputs/gemini-3.6-flash/EVAL-004.json`). Bản JSON đúng schema `CreditReviewSummary` và đã vượt toàn bộ hậu kiểm Python (a)–(e). |

Kết quả xác định kỳ vọng cho hồ sơ mẫu: trạng thái **HUMAN REVIEW REQUIRED**, cảnh báo `INCOME_MISMATCH` và `HIGH_DSR_DEMO`.

Sinh lại thư mục PDF:

```bash
python -c "from pathlib import Path; from tests.fixtures.synthetic_pdfs import synthetic_cases, case_uploads; c=[x for x in synthetic_cases() if x.case_id=='EVAL-004'][0]; d=Path('samples/HOSO-MAU-EVAL-004'); d.mkdir(parents=True, exist_ok=True); [ (d/u.name).write_bytes(u.getvalue()) for u in case_uploads(c)]"
```
