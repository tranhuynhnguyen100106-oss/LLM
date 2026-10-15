"""Ten required failure-case records for the evaluation report."""

from __future__ import annotations

from typing import Any


def build_failure_cases(predictions: list[dict[str, Any]], cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prediction_by_scenario = {case["scenario"]: prediction for case, prediction in zip(cases, predictions, strict=True)}

    def observed(scenario: str) -> dict[str, Any]:
        prediction = prediction_by_scenario.get(scenario, {})
        return {"status": prediction.get("status", "N/A"), "risk_flags": prediction.get("risk_flags", [])}

    return [
        {
            "case_id": "FAIL-01",
            "input": "PDF quét chỉ có ảnh, không có lớp văn bản",
            "ground_truth": "Các trường phải được OCR hoặc chuyển cho con người",
            "actual_output": "N/A – chưa có OCR fixture trong bộ dữ liệu này",
            "failure_type": "Scanned PDF / no text",
            "probable_cause": "Bộ đọc PDF hiện chỉ khai thác lớp văn bản",
            "mitigation": "Thêm OCR có confidence và bắt buộc đối chiếu bằng chứng trang",
            "status": "KNOWN LIMITATION",
        },
        {
            "case_id": "FAIL-02",
            "input": "Bảng PDF nhiều cột và ô gộp",
            "ground_truth": "Giữ đúng quan hệ hàng-cột",
            "actual_output": "N/A – cần bộ PDF bảng được gán nhãn riêng",
            "failure_type": "Multi-column table",
            "probable_cause": "Thứ tự text extraction có thể khác thứ tự trực quan",
            "mitigation": "Bổ sung table parser và benchmark theo cell",
            "status": "NOT RUN",
        },
        {
            "case_id": "FAIL-03",
            "input": "Nhãn trường hiếm hoặc viết tắt chưa có trong alias",
            "ground_truth": "Nhận diện đúng trường",
            "actual_output": "N/A – cần mở rộng fixture theo mẫu tổ chức",
            "failure_type": "Uncommon labels",
            "probable_cause": "Từ điển alias chưa bao phủ mẫu mới",
            "mitigation": "Quản trị alias theo phiên bản và bổ sung regression case",
            "status": "NOT RUN",
        },
        {
            "case_id": "FAIL-04",
            "input": "Ngày không theo YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY hoặc YYYY/MM/DD",
            "ground_truth": "Chuẩn hóa được hoặc báo không đủ dữ liệu",
            "actual_output": "N/A – bộ hiện tại chỉ đo các định dạng được công bố",
            "failure_type": "Non-standard date",
            "probable_cause": "Date parser cố ý giới hạn để tránh đoán mơ hồ",
            "mitigation": "Thêm parser có locale và cờ xác nhận thủ công",
            "status": "KNOWN LIMITATION",
        },
        {
            "case_id": "FAIL-05",
            "input": "Nghĩa vụ nợ kê khai bằng 0 nhưng quan sát lớn hơn 0",
            "ground_truth": "Không chia cho 0; phát cảnh báo nợ chưa kê khai",
            "actual_output": "Đã được self-test hiện tại bao phủ",
            "failure_type": "Zero declared debt",
            "probable_cause": "Rủi ro chia cho 0 nếu dùng tỷ lệ chênh lệch thông thường",
            "mitigation": "Giữ nhánh xử lý tuyệt đối và regression test",
            "status": "MITIGATED",
        },
        {
            "case_id": "FAIL-06",
            "input": "Thiếu sao kê ngân hàng",
            "ground_truth": "INSUFFICIENT INFORMATION",
            "actual_output": observed("Thiếu sao kê ngân hàng"),
            "failure_type": "Missing statement",
            "probable_cause": "Không đủ nguồn kiểm chứng và chỉ số dòng tiền",
            "mitigation": "Yêu cầu bổ sung sao kê; không tự điền dữ liệu",
            "status": "EVALUATED",
        },
        {
            "case_id": "FAIL-07",
            "input": "Thiếu chứng từ thu nhập",
            "ground_truth": "INSUFFICIENT INFORMATION",
            "actual_output": observed("Thiếu chứng từ thu nhập"),
            "failure_type": "Missing income document",
            "probable_cause": "Thiếu nguồn xác minh độc lập",
            "mitigation": "Yêu cầu bổ sung chứng từ; giữ human-in-the-loop",
            "status": "EVALUATED",
        },
        {
            "case_id": "FAIL-08",
            "input": "Provider trả HTTP 429 credit_balance_exhausted",
            "ground_truth": "Báo lỗi quota rõ ràng, không làm hỏng kết quả Python",
            "actual_output": "Đã quan sát: OpenAI RateLimitError 429 insufficient_quota",
            "failure_type": "LLM quota",
            "probable_cause": "Tài khoản API không còn credit",
            "mitigation": "Bổ sung credit hoặc chọn provider hợp lệ; không tự retry",
            "status": "OBSERVED",
        },
        {
            "case_id": "FAIL-09",
            "input": "Provider không phản hồi trong thời gian cho phép",
            "ground_truth": "Timeout an toàn, báo lỗi và giữ phân tích xác định",
            "actual_output": "N/A – requires controlled provider test",
            "failure_type": "LLM timeout",
            "probable_cause": "Mạng hoặc provider chậm",
            "mitigation": "Timeout hữu hạn, log an toàn và không retry ngoài kiểm soát",
            "status": "NOT RUN",
        },
        {
            "case_id": "FAIL-10",
            "input": "Generic prompt không cung cấp evidence contract",
            "ground_truth": "Mọi claim quan trọng có evidence và nhất quán dữ kiện",
            "actual_output": "Được đo bằng fixture generic_prompt đã lưu",
            "failure_type": "Ungrounded output",
            "probable_cause": "Prompt không có structured facts/evidence constraints",
            "mitigation": "Dùng structured output + evidence references + human review",
            "status": "EVALUATED",
        },
    ]
