"""Điểm khởi chạy Streamlit cho CreditLens."""

from credit_underwriting_colab import chay_ung_dung_streamlit
from creditlens_ui_v2 import chay_ung_dung_streamlit_v2, show_v2_fallback_notice, ui_v2_enabled


def main() -> None:
    """Chạy UI v2 production khi bật cờ; giữ legacy làm rollback an toàn."""

    if ui_v2_enabled():
        try:
            chay_ung_dung_streamlit_v2()
            return
        except Exception:
            # Không để lỗi build/render chặn legacy fallback,
            # và không đưa exception (có thể chứa dữ liệu nhạy cảm) ra giao diện.
            show_v2_fallback_notice()
    chay_ung_dung_streamlit()


if __name__ == "__main__":
    main()
