"""Điểm khởi chạy Streamlit cho CreditLens.

Thứ tự giao diện: UI v3 ("Đánh giá tín dụng vay", bản AI Studio) → UI v2 → legacy.
- UI_V3_ENABLED (mặc định bật; đặt "false" để tắt).
- Nếu v3 lỗi (thiếu bundle, lỗi render…) thì tự quay về v2; nếu v2 lỗi thì quay về legacy.
"""

from credit_underwriting_colab import chay_ung_dung_streamlit
from creditlens_ui_v2 import chay_ung_dung_streamlit_v2, show_v2_fallback_notice, ui_v2_enabled
from creditlens_ui_v3 import chay_ung_dung_streamlit_v3, ui_v3_enabled


def _run_v2_then_legacy() -> None:
    try:
        chay_ung_dung_streamlit_v2()
        return
    except Exception:
        # Không để lỗi build/render chặn legacy fallback,
        # và không đưa exception (có thể chứa dữ liệu nhạy cảm) ra giao diện.
        show_v2_fallback_notice()
    chay_ung_dung_streamlit()


def main() -> None:
    if ui_v3_enabled():
        try:
            chay_ung_dung_streamlit_v3()
            return
        except Exception:
            # v3 lỗi → tự quay về v2 (rồi legacy); không đưa chi tiết lỗi ra giao diện.
            _run_v2_then_legacy()
            return
    if ui_v2_enabled():
        _run_v2_then_legacy()
        return
    chay_ung_dung_streamlit()


if __name__ == "__main__":
    main()
