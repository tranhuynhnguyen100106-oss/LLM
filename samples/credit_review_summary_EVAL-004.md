# CREDIT REVIEW SUMMARY — HOSO-MAU-EVAL-004 (bản mẫu từ LLM thật)

> Bản MẪU từ output LLM thật (model `gemini-3.6-flash`, lưu tại `evaluation/llm_outputs/gemini-3.6-flash/EVAL-004.json`): đúng schema `CreditReviewSummary` và đã vượt toàn bộ hậu kiểm Python (a)–(e). Dữ liệu tổng hợp, đã giả danh hóa.

### 1. Tổng quan khách hàng
DỮ KIỆN: Mã hồ sơ EVAL-004, khách hàng `KH_01`, đơn vị công tác `DN_A`, chức danh Chuyên viên phân tích, thâm niên 48.0 tháng. DIỄN GIẢI: Hồ sơ đề nghị vay vốn phục vụ mục đích sửa chữa nhà ở.

### 2. Đề nghị vay vốn
DỮ KIỆN: Số tiền đề nghị vay 600.000.000 VND, thời hạn vay 120.0 tháng, khoản trả nợ dự kiến hàng tháng 7.500.000 VND, mục đích vay Sửa chữa nhà ở.

### 3. Thông tin tài chính đã xác minh
DỮ KIỆN: Thu nhập kê khai 30.000.000 VND, lương thực nhận 20.000.000 VND, thu nhập qua sao kê (ghi có bình quân) 18.000.000 VND. Thu nhập dùng để tính là 18.000.000 VND (Ghi có bình quân sao kê). Nghĩa vụ nợ hiện hữu 2.000.000 VND, chi phí sinh hoạt 9.000.000 VND, số dư tài khoản bình quân 18.000.000 VND.

### 4. Chỉ số tín dụng
- DTI hiện hữu: 11,1% (Trong ngưỡng minh họa)
- DSR dự kiến: 52,8% (Cần chú ý)
- Thu nhập còn lại trước khoản vay mới: 7.000.000 VND (Trong ngưỡng minh họa)
- Hệ số đệm số dư: 2,40× (Trong ngưỡng minh họa)
- Chênh lệch thu nhập: 40,0% (Cần chú ý)
- Biến động thu nhập: 6,0% (Trong ngưỡng minh họa)

### 5. Kiểm tra nhất quán
DỮ KIỆN: Thông tin về đơn vị công tác (`DN_A`), chức danh (Chuyên viên phân tích), ngày bắt đầu làm việc (06/2022) và nghĩa vụ nợ (2.000.000 VND) khớp đúng giữa các tài liệu. Có chênh lệch 40,0% giữa các con số thu nhập kê khai (30.000.000 VND), lương thực nhận (20.000.000 VND) và ghi có bình quân sao kê (18.000.000 VND).

### 6. Cảnh báo rủi ro
- **INCOME_MISMATCH** (R-001): DỮ KIỆN: Các nguồn thu nhập chênh 40,0%, vượt ngưỡng minh họa 15,0%. DIỄN GIẢI: Cần xác minh nguồn thu và kỳ ghi nhận.
- **HIGH_DSR_DEMO** (R-002): DỮ KIỆN: DSR dự kiến 52,8% vượt ngưỡng cảnh báo minh họa 45,0%.

### 7. Thông tin còn thiếu
- Không phát hiện hạng mục bắt buộc còn thiếu.

### 8. Câu hỏi cần xác minh
- Nguồn thu nhập nào là thường xuyên, có thể xác minh và thuộc đúng kỳ sao kê?

### 9. Bằng chứng
- `01_don_de_nghi_vay.pdf` (trang 1): Họ và tên: `KH_01`; Thu nhập kê khai: 30.000.000; Số tiền đề nghị vay: 600.000.000; Thời hạn vay: 120; Khoản trả nợ dự kiến: 7.500.000; Nghĩa vụ nợ kê khai: 2.000.000; Chi phí sinh hoạt: 9.000.000
- `02_chung_tu_thu_nhap.pdf` (trang 1): Lương thực nhận: 20.000.000; Đơn vị công tác: `DN_A`; Chức danh: Chuyên viên phân tích; Ngày bắt đầu: 06/2022
- `03_sao_ke_ngan_hang.pdf` (trang 1): Ghi có bình quân hàng tháng: 18.000.000; Số dư bình quân: 18.000.000; Biến động thu nhập: 6,00%
- `04_nghia_vu_no.pdf` (trang 1): Khoản trả nợ quan sát hàng tháng: 2.000.000

### 10. Trạng thái xem xét của con người
**CẦN CON NGƯỜI XEM XÉT** (HUMAN REVIEW REQUIRED)

---
**Bắt buộc con người xem xét. Nội dung này không phải quyết định tín dụng.**
