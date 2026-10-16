# CREDIT REVIEW SUMMARY — HOSO-MAU-EVAL-004 (bản mẫu)

> Bản MẪU minh họa: dựng tất định từ facts Python (ban_tom_tat_tu_ket_qua), không gọi LLM; đúng schema CreditReviewSummary và đã vượt hậu kiểm (a)–(e). Dữ liệu tổng hợp, đã giả danh hóa.

### 1. Tổng quan khách hàng
Khách hàng KH_01, đơn vị công tác kê khai DN_A, chức danh Chuyên viên phân tích.

### 2. Đề nghị vay vốn
Số tiền đề nghị vay 600.000.000 VND; mục đích: Sửa chữa nhà ở.

### 3. Thông tin tài chính đã xác minh
Thu nhập dùng để tính: Ghi có bình quân sao kê (giá trị thận trọng hơn). Thu nhập kê khai 30.000.000 VND, lương thực nhận 20.000.000 VND, ghi có bình quân sao kê 18.000.000 VND.

### 4. Chỉ số tín dụng
- DTI hiện hữu: 11,1% (Trong ngưỡng minh họa)
- DSR dự kiến: 52,8% (Cần chú ý)
- Thu nhập còn lại trước khoản vay mới: 7.000.000 VND (Trong ngưỡng minh họa)
- Hệ số đệm số dư: 2,40× (Trong ngưỡng minh họa)
- Chênh lệch thu nhập: 40,0% (Cần chú ý)
- Biến động thu nhập: 6,0% (Trong ngưỡng minh họa)

### 5. Kiểm tra nhất quán
Rule Python phát hiện: INCOME_MISMATCH, HIGH_DSR_DEMO.

### 6. Cảnh báo rủi ro
- **INCOME_MISMATCH** (R-001): Các nguồn thu nhập chênh 40,0%, vượt ngưỡng minh họa 15,0%. Cần xác minh nguồn thu và kỳ ghi nhận.
- **HIGH_DSR_DEMO** (R-002): DSR dự kiến 52,8% vượt ngưỡng cảnh báo minh họa 45,0%.

### 7. Thông tin còn thiếu
- Không phát hiện hạng mục bắt buộc còn thiếu.

### 8. Câu hỏi cần xác minh
- Nguồn thu nhập nào là thường xuyên, có thể xác minh và thuộc đúng kỳ sao kê?

### 9. Bằng chứng
- R-001: 01_don_de_nghi_vay.pdf, trang 1, Thu nhập hàng tháng kê khai = 30.000.000 VND
- R-001: 02_chung_tu_thu_nhap.pdf, trang 1, Lương thực nhận = 20.000.000 VND
- R-001: 03_sao_ke_ngan_hang.pdf, trang 1, Ghi có bình quân hàng tháng = 18.000.000 VND
- R-002: 04_nghia_vu_no.pdf, trang 1, Khoản trả nợ quan sát hàng tháng = 2.000.000 VND
- R-002: 01_don_de_nghi_vay.pdf, trang 1, Khoản trả nợ dự kiến hàng tháng = 7.500.000 VND
- R-002: 03_sao_ke_ngan_hang.pdf, trang 1, Ghi có bình quân hàng tháng = 18.000.000 VND

### 10. Trạng thái xem xét của con người
**CẦN CON NGƯỜI XEM XÉT** (HUMAN REVIEW REQUIRED)

---
**Bắt buộc con người xem xét. Nội dung này không phải quyết định tín dụng.**
