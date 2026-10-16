# Sơ đồ workflow — CreditLens (AI Credit Underwriting Copilot)

Sơ đồ toàn bộ pipeline của bản Streamlit (UI v3). Màu xanh: Python tự làm, kết quả xác định. Màu cam: có gọi LLM. Màu đỏ: con người phải duyệt.

```mermaid
flowchart TD
    U["1. Upload<br/>thư mục / từng PDF hoặc hồ sơ minh họa"]:::human
    P["2. Privacy Gateway — Bước 0<br/>detect_pii → bảng xem trước → giả danh hóa<br/>(KH_01, DN_A, [CCCD_ĐÃ_CHE]…)"]:::py
    PH{{"Chuyên viên tick xác nhận bảo mật<br/>và bấm “Giả danh hóa và tiếp tục”"}}:::human
    C["3. Phân loại tài liệu<br/>tên tệp + từ khóa nội dung (pypdf)"]:::py
    CH{{"Bảng xác nhận phân loại<br/>chuyên viên sửa loại nếu sai"}}:::human
    E["4. Extraction<br/>regex/alias trên lớp văn bản PDF (pypdf)"]:::py
    EL["4b. LLM Structured Extraction (fallback)<br/>chỉ trường SỐ/NGÀY regex bỏ sót<br/>JSON {field, value, unit, source_doc, page, quote}"]:::llm
    EG["Grounding check (Python)<br/>value + quote phải có thật trong trang PDF"]:::py
    EH{{"Chuyên viên bấm “Xác nhận” từng trường AI<br/>(trước đó coi như thiếu dữ liệu)"}}:::human
    V["5. Validation & Rules<br/>thiếu tài liệu / thiếu trường cốt lõi<br/>5 loại mâu thuẫn chéo + độ tin cậy thấp"]:::py
    M["6. Python metrics<br/>DTI, DSR, thu nhập còn lại, hệ số đệm số dư,<br/>chênh lệch & biến động thu nhập"]:::py
    EV["7. Evidence<br/>mỗi cảnh báo → tài liệu, trang, trường, trích đoạn"]:::py
    S["8a. LLM Credit Review Summary<br/>JSON schema 10 mục, chỉ dựa trên JSON Python"]:::llm
    Q["8b. LLM Q&A theo vai trò<br/>Thẩm định viên / Kiểm soát rủi ro / Cố vấn"]:::llm
    PC["Hậu kiểm (Python)<br/>số liệu khớp JSON · risk_code hợp lệ · đủ 10 mục ·<br/>trạng thái trùng Python · không có ngôn ngữ quyết định"]:::py
    H{{"9. Human Review<br/>REVIEW READY / HUMAN REVIEW REQUIRED /<br/>INSUFFICIENT INFORMATION → chuyên viên & Hội đồng quyết định"}}:::human

    U --> P --> PH --> C --> CH --> E
    E -- "trường số/ngày = None" --> EL --> EG --> EH --> V
    E --> V --> M --> EV
    EV --> S --> PC --> H
    EV --> Q --> PC
    M --> H

    classDef py fill:#E8F1FF,stroke:#203469,color:#0F172A;
    classDef llm fill:#FFF4E5,stroke:#B45309,color:#0F172A;
    classDef human fill:#FDECEC,stroke:#A71B28,color:#0F172A;
```

## AI tự làm gì, con người duyệt gì

| Bước | Ai thực hiện | Con người phải duyệt? |
|---|---|---|
| Phát hiện & giả danh hóa PII | Python (`privacy_gateway.py`) | Có — xác nhận bảng xem trước, có thể che thêm |
| Phân loại tài liệu | Python (tên tệp + từ khóa) | Có — bảng xác nhận phân loại |
| Trích xuất trường bằng regex | Python | Xem ở trang Trích xuất (có bằng chứng trang) |
| Trích xuất bổ sung bằng AI | **LLM** (1 request/hồ sơ, khi chuyên viên bấm) | **Có — từng trường phải bấm “Xác nhận”** mới được dùng để tính |
| Rules, chỉ số DTI/DSR, trạng thái | Python | Không đổi được bằng AI |
| Credit Review Summary | **LLM** + hậu kiểm Python | Có — nội dung AI chỉ hỗ trợ; vi phạm hậu kiểm thì không vào báo cáo |
| Hỏi đáp theo vai trò | **LLM** (1 request/lần Gửi) | Có — câu trả lời chứa khuyến nghị phê duyệt/từ chối bị chặn |
| Quyết định cho vay | **Chỉ con người** | Hệ thống không bao giờ APPROVE/REJECT |

## Giới hạn đã biết

- Chưa có OCR: PDF scan chỉ có ảnh không đọc được nội dung (FAIL-01) và hồ sơ sẽ ở trạng thái cần con người xem xét.
- Chưa kết nối CIC: tài liệu nghĩa vụ nợ do khách cung cấp và sao kê là nguồn đối chiếu thay thế.
- Ngưỡng là minh họa học thuật, không phải chính sách tín dụng của ngân hàng.
