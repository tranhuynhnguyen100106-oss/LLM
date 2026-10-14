# CreditLens - Hệ thống Thẩm định Tín dụng Xác định (React SPA)

CreditLens là hệ thống AI Credit Underwriting Copilot hỗ trợ đọc hồ sơ tài liệu PDF, chuẩn hóa dữ kiện có cấu trúc, tính toán các chỉ số tài chính xác định (DTI, DSR, thu nhập khả dụng, đệm số dư), phát hiện mâu thuẫn đa tài liệu, liên kết bằng chứng minh bạch và tạo báo cáo quyết định cấp tín dụng.

> **Nguyên tắc an toàn:** Ứng dụng hỗ trợ thẩm định và phân tích xác định; không tự phê duyệt hoặc từ chối khoản vay. Mọi quyết định cuối cùng bắt buộc do chuyên viên và Hội đồng Tín dụng xem xét.

---

## Kiến trúc và Công nghệ

Dự án được xây dựng hoàn toàn dưới dạng **React SPA (Vite + TypeScript)** theo tiêu chuẩn hiện đại:

- **Framework:** React 19 + TypeScript 5
- **Build Tool:** Vite
- **Hệ thống Design Tokens:** CSS Variables theo thiết kế đồng thương hiệu HUB × CreditLens (`#203469` Navy và `#A71B28` Accent Red)
- **Hỗ trợ giao diện:** 3 chế độ Theme (Theo hệ thống, Sáng, Tối)
- **Khả năng tiếp cận:** Hỗ trợ phím tắt, Skip Link, đầy đủ nhãn ARIA và tự động giảm chuyển động khi bật `prefers-reduced-motion`

---

## 8 Phân hệ Chức năng Chính

1. **Tổng quan và Hồ sơ (`1_overview`):**
   - Vùng tiếp nhận tài liệu (Intake Area) hỗ trợ kéo thả hoặc chọn nhiều tệp PDF (Đơn vay, Chứng từ thu nhập, Sao kê ngân hàng, Nghĩa vụ nợ).
   - Bộ chọn 10 tình huống thử nghiệm (Demo Cases) tổng hợp xác định.
   - Stepper quy trình 4 chặng: Tiếp nhận → Tính toán xác định → Đối chiếu đa chứng từ → Con người xem xét.

2. **Trích xuất tài liệu (`2_extraction`):**
   - Danh mục tài liệu với trạng thái, số trang, loại nhận diện và điểm tin cậy (Confidence score).
   - 20 trường dữ kiện chuẩn hóa theo vai trò nguồn (Kê khai / Quan sát từ chứng từ / Tính toán).
   - Chi tiết bằng chứng nguồn (Evidence Disclosure) trích xuất từ tài liệu và số trang cụ thể.

3. **Phân tích tín dụng (`3_analysis`):**
   - Thẻ nguồn thu nhập cơ sở dùng để tính toán và trạng thái xác minh độc lập.
   - Lưới 6 chỉ số tài chính trọng yếu: DTI hiện hữu, DSR dự kiến, Thu nhập còn lại, Hệ số đệm số dư, Chênh lệch thu nhập, Biến động thu nhập.
   - Bảng đối chiếu chéo dữ liệu đa chứng từ (Thu nhập 3 nguồn, Đơn vị công tác, Nghĩa vụ nợ).

4. **Cảnh báo rủi ro (`4_risk`):**
   - Động cơ quy tắc xác định phát hiện mâu thuẫn: `INCOME_MISMATCH`, `EMPLOYER_MISMATCH`, `POSSIBLE_UNDECLARED_DEBT`, `HIGH_DTI_DEMO`, `HIGH_DSR_DEMO`, `LOW_BALANCE_BUFFER`, `HIGH_INCOME_VOLATILITY`, `LOW_EXTRACTION_CONFIDENCE`.
   - Phân loại mức độ nghiêm trọng: CAO (HIGH), TRUNG BÌNH (MEDIUM), THẤP (LOW), THÔNG TIN (INFO).
   - Trích dẫn bằng chứng đính kèm từng cảnh báo.

5. **Tóm tắt thẩm định (`5_summary`):**
   - Bảng tổng hợp quyết định cấp tín dụng (Decision-Support Hero) với thông tin khách hàng, khoản vay đề nghị.
   - Phân tách rõ ràng giữa *Deterministic findings* (kết quả tính toán xác định) và *Human review checklist* (câu hỏi và thông tin cần bổ sung).
   - Tùy chọn tạo diễn giải ngôn ngữ tự nhiên bằng AI hỗ trợ.
   - Nút xuất báo cáo: Tải Markdown (`.md`), Tải JSON có cấu trúc (`.json`), In / Lưu PDF.

6. **Phương pháp và Giới hạn (`6_methodology`):**
   - Kiến trúc 3 tầng: Dữ kiện → Phân tích xác định → Diễn giải AI.
   - 6 thẻ công thức tài chính kèm ý nghĩa và giới hạn đo lường.
   - Bảng ma trận năng lực xử lý các loại định dạng PDF.
   - Nhóm các giới hạn hệ thống và trách nhiệm con người.

7. **Evaluation Benchmark (`7_evaluation`):**
   - Bộ kiểm thử chất lượng chạy trên 12 kịch bản synthetic gold dataset độc lập.
   - Scorecards độ chính xác trích xuất và phân loại.
   - Ma trận nhầm lẫn (Confusion Matrix) 3x3 cho trạng thái thẩm định.
   - Bảng Grounding consistency và so sánh với baseline con người / LLM zero-shot.
   - Danh mục 6 trường hợp ngoại lệ (Failure Cases) kèm nguyên nhân và giải pháp khắc phục.
   - Xuất kết quả đánh giá ra định dạng CSV và JSON.

8. **Cài đặt & Trợ lý AI (`8_settings`):**
   - Quản lý trạng thái kết nối các nhà cung cấp mô hình (Gemini, OpenAI, Claude, DeepSeek).
   - Thanh trượt tinh chỉnh 8 ngưỡng rủi ro minh họa trong phiên với tính năng **tính toán lại tức thì** trên toàn bộ ứng dụng.
   - Khung chat tương tác với trợ lý CreditLens trả lời câu hỏi nghiệp vụ dựa trên dữ kiện hồ sơ.

---

## Hướng dẫn Khởi chạy

```bash
# Cài đặt dependencies
npm install

# Khởi chạy máy chủ phát triển (Port 3000)
npm run dev

# Kiểm tra build sản phẩm
npm run build
```
