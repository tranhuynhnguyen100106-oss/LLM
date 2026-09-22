# CreditLens Streamlit phiên bản công khai

CreditLens là AI Credit Underwriting Copilot hỗ trợ đọc hồ sơ PDF, chuẩn hóa dữ kiện, tính chỉ số bằng Python, phát hiện mâu thuẫn, liên kết bằng chứng và tạo báo cáo Word, Excel hoặc PDF.

Ứng dụng không phê duyệt hoặc từ chối khoản vay. Các ngưỡng chỉ dùng để minh họa học thuật. Quyết định cuối cùng bắt buộc do con người xem xét.

## Tính năng của bản này

- Giao diện tiếng Việt, nền sáng, màu gradient và hiệu ứng neon nhẹ.
- Upload đơn đề nghị vay, chứng từ thu nhập, sao kê và tài liệu nghĩa vụ nợ.
- Trích xuất có cấu trúc và confidence score.
- Python tính DTI, DSR, thu nhập khả dụng, hệ số đệm số dư và biến động thu nhập.
- Phát hiện chênh lệch thu nhập, doanh nghiệp, chức danh, thời gian làm việc và nghĩa vụ nợ.
- Evidence traceability đến tài liệu, trang, trường và giá trị.
- Nhập OpenAI API Key riêng cho từng phiên. Key không được ghi vào source hoặc báo cáo.
- Chuyên viên chọn xuất báo cáo `.docx`, `.xlsx` hoặc `.pdf`.
- Có `render.yaml` để triển khai trên dịch vụ web hỗ trợ Blueprint và `packages.txt` để cài font PDF tiếng Việt.

## Chạy thử trong một ô Colab hoặc Jupyter

Tệp `CreditLens_Public_OneCell.py` ở ngoài gói project là ô bootstrap. Dán toàn bộ nội dung của tệp đó vào một ô Python và chạy. Ô này sẽ:

1. Tạo thư mục `creditlens_public`.
2. Giải nén source code.
3. Cài dependencies.
4. Chạy Streamlit để kiểm thử trong phiên notebook.
5. Tạo sẵn `creditlens_public_deploy.zip` để tải lên GitHub.

URL xem trong Colab chỉ tồn tại khi runtime còn hoạt động. Không sử dụng URL Colab làm URL public chính thức.

## Triển khai công khai miễn phí bằng Streamlit Community Cloud

1. Chạy ô bootstrap và tải `creditlens_public_deploy.zip` xuống máy.
2. Giải nén ZIP. Bên trong phải có `app.py`, `credit_underwriting_colab.py`, `requirements.txt`, `packages.txt` và thư mục `.streamlit`.
3. Tạo một repository GitHub mới, ví dụ `creditlens-underwriting`.
4. Đặt repository ở chế độ Public nếu muốn source code mở.
5. Upload toàn bộ nội dung bên trong thư mục project lên nhánh `main`. Không upload `.env`, `secrets.toml` hoặc API Key.
6. Đăng nhập Streamlit Community Cloud bằng GitHub.
7. Chọn Create app, sau đó chọn repository, branch `main` và main file `app.py`.
8. Chọn URL mong muốn và bấm Deploy.
9. Sau khi app chạy, đặt quyền chia sẻ Public. Bất kỳ ai có URL đều có thể truy cập.

Streamlit Community Cloud chạy trên máy chủ từ xa nên app không tắt khi máy cá nhân tắt. Tuy nhiên, gói miễn phí cho app ngủ sau thời gian không có truy cập; người dùng có quyền truy cập có thể đánh thức app. Nếu yêu cầu không có trạng thái ngủ, hãy dùng một gói hosting trả phí hoặc VPS luôn hoạt động.

## Triển khai luôn hoạt động

Project có `render.yaml` và mặc định chọn `plan: free` để tránh phát sinh chi phí ngoài ý muốn. Gói Render Free ngủ sau thời gian không có truy cập; nếu cần không sleep, hãy nâng chính web service đó lên một compute plan trả phí. Lệnh chạy là:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
```

Không có nền tảng miễn phí nào nên được xem là cam kết uptime 24/7. Để đáp ứng đúng nghĩa “không ngưng hoạt động”, cần gói trả phí không spin-down hoặc VPS.

## API Key trên web công khai

Mỗi người dùng nhập key của họ tại mục Cài đặt AI. Key chỉ nằm trong `st.session_state` của phiên và có nút xóa. Không đặt một OpenAI API Key chung vào source public vì người lạ có thể gây phát sinh chi phí.

Nếu chỉ demo riêng cho giảng viên, có thể dùng secret của nền tảng nhưng phải thêm giới hạn truy cập và hạn mức chi phí. Không commit `.streamlit/secrets.toml`.

## Xuất báo cáo

Mở Tóm tắt thẩm định, chọn một định dạng rồi tải:

- Word: báo cáo trình bày theo mục, có bảng chỉ số, cảnh báo, bằng chứng và dữ kiện trích xuất.
- Excel: nhiều sheet, giữ kiểu số và phần trăm để tiếp tục phân tích.
- PDF: báo cáo Unicode tiếng Việt có header, footer và số trang.

Báo cáo được tạo trong RAM. Ứng dụng không lưu tệp báo cáo vào thư mục máy chủ.

## Kiểm thử

```bash
CREDITLENS_SELF_TEST=1 python credit_underwriting_colab.py
```

## Quyền riêng tư

- Chỉ dùng dữ liệu tổng hợp hoặc đã ẩn danh.
- Giới hạn mỗi PDF là 10 MB.
- Tệp tạm bị xóa sau khi đọc.
- Không log API Key hoặc nội dung PDF.
- Có nút xóa hồ sơ khỏi phiên.
- Public demo không phù hợp với dữ liệu khách hàng thật.
