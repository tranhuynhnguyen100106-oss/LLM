"""CreditLens UI v3 — giao diện "Đánh giá tín dụng vay" (bản AI Studio) chạy trên Streamlit.

Kiến trúc:
- Python (module này + credit_underwriting_colab + privacy_gateway + evaluation) là server và
  source of truth: trích xuất PDF (pypdf), Privacy Gateway, công thức, rules, ngưỡng, evaluation,
  gọi LLM, export Word/Excel/PDF và session state.
- React (../src/components, đóng gói ở frontend-v3/dist) là presentation layer trong một
  Streamlit Component v2. Python → view model JSON (allowlist, đã giả danh hóa) → React render;
  React → event có kiểu (event_id duy nhất) → Python validate + idempotency → action.
- Thứ tự fallback trong app.py: v3 → v2 → legacy.

Ràng buộc bất biến: AI không APPROVE/REJECT; không đổi công thức/ngưỡng/rules; mỗi lần Send tối đa
1 inference request; API key chỉ ở Python backend (không có trong view model, log hay báo cáo).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Mapping

UI_V3_FLAG = "UI_V3_ENABLED"
COMPONENT_NAME = "creditlens_v3_app"
SCHEMA_VERSION = "3.0"
APP_NAME = "Đánh giá tín dụng vay"
_DIST_DIR = Path(__file__).resolve().parent / "frontend-v3" / "dist"
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})
_EVENT_ID = re.compile(r"^[A-Za-z0-9_-]{8,96}$")
_THEMES = ("system", "light", "dark")
_MOTION = ("full", "light", "off")
_RENDERER_CACHE: dict[tuple[int, str], Any] = {}

# Khóa trang của bản AI Studio ↔ trang Python (credit_underwriting_colab.PAGES, cùng thứ tự).
PAGE_KEYS = (
    "1_overview",
    "2_extraction",
    "3_analysis",
    "4_risk",
    "5_summary",
    "6_methodology",
    "7_evaluation",
    "8_settings",
)
PAGE_LABELS = {
    "1_overview": "1. Tổng quan và hồ sơ",
    "2_extraction": "2. Trích xuất tài liệu",
    "3_analysis": "3. Phân tích tín dụng",
    "4_risk": "4. Cảnh báo rủi ro",
    "5_summary": "5. Tóm tắt thẩm định",
    "6_methodology": "6. Phương pháp và giới hạn",
    "7_evaluation": "7. Evaluation",
    "8_settings": "8. Cài đặt",
}
CORE_KIND = {"2_extraction": "extraction", "3_analysis": "analysis", "4_risk": "risk"}

GEMINI_DEFAULT_MODEL = "gemini-3.8-flash"
CHAT_HISTORY_LIMIT = 12
PING_SYSTEM_PROMPT = "Kiểm tra kết nối. Trả lời đúng một từ: OK."
PARTIAL_LABEL = "Key hợp lệ — chưa gọi được model"
OVERLOADED_LABEL = "Key hợp lệ — model đang quá tải phía Google"

CHAT_ROLES = ("underwriter", "risk_auditor", "advisor")
# Nội dung chuyển nguyên văn từ src/lib/prompts.ts (bản AI Studio).
SYSTEM_ROLES = {
    "underwriter": f"""Bạn là Chuyên viên Thẩm định Tín dụng Cấp cao (Senior Underwriter) của hệ thống "{APP_NAME}".
Nhiệm vụ:
1. Đánh giá tính khả thi và rủi ro của hồ sơ vay dựa trên nguyên tắc tài chính - ngân hàng.
2. Phân tích định lượng DTI, DSR, chênh lệch thu nhập kê khai so với sao kê ngân hàng.
3. Chỉ rõ bằng chứng từ tài liệu cụ thể (hợp đồng lao động, sao kê, CIC).
4. Lập luận khách quan, thận trọng theo chuẩn mực ngân hàng thương mại Việt Nam.""",
    "risk_auditor": f"""Bạn là Trưởng ban Kiểm soát Rủi ro & Tuân thủ Tín dụng của hệ thống "{APP_NAME}".
Nhiệm vụ:
1. Phát hiện dấu hiệu gian lận, mâu thuẫn số liệu thu nhập, nợ tiềm ẩn không kê khai.
2. Đánh giá mức độ vi phạm các ngưỡng cảnh báo rủi ro.
3. Đề xuất biện pháp xác minh bổ sung (thực địa, đối soát BHXH, CIC).""",
    "advisor": f"""Bạn là Cố vấn Phương án Tài chính của hệ thống "{APP_NAME}".
Nhiệm vụ:
1. Giải thích thuật ngữ, cách tính DTI, DSR và tác động khi điều chỉnh ngưỡng.
2. Gợi ý cơ cấu khoản vay, thời hạn, tài sản bảo đảm phù hợp năng lực trả nợ.
3. Hỗ trợ hoàn thiện tờ trình thẩm định rõ ràng, có cấu trúc.""",
}
_PROHIBITED_DECISION = (
    r"khuyến nghị\s+(phê duyệt|từ chối)",
    r"nên\s+(phê duyệt|từ chối)",
    r"quyết định\s*:\s*(approve|reject|phê duyệt|từ chối)",
    r"\b(approve|reject)\s+(the\s+)?loan\b",
)
WELCOME_MESSAGE = (
    "Xin chào, tôi là Trợ lý **Đánh giá tín dụng vay**. Hãy hỏi tôi về DTI/DSR, đối chiếu thu nhập hoặc "
    "các cảnh báo rủi ro của hồ sơ đang mở. Dữ liệu gửi AI luôn được giả danh hóa; quyết định cuối cùng "
    "thuộc chuyên viên và Hội đồng Tín dụng."
)
NO_AI_MESSAGE = (
    "**Chưa kết nối AI.** Mở **Cài đặt → Kết nối AI** để xác thực API Key trên máy chủ (khóa không bao giờ "
    "được gửi tới trình duyệt). Hệ thống không tạo câu trả lời mô phỏng."
)


# ==========================================================
# Cờ tính năng
# ==========================================================

def ui_v3_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Bật mặc định; đặt UI_V3_ENABLED=false (env hoặc root-level secret) để quay về v2."""

    source = os.environ if environ is None else environ
    value = str(source.get(UI_V3_FLAG, "true")).strip().casefold()
    return value not in _FALSE_VALUES


class V3ContractError(ValueError):
    """Payload hoặc event v3 không đúng hợp đồng an toàn."""


class V3ComponentUnavailable(RuntimeError):
    """Bundle frontend-v3/dist chưa sẵn sàng."""


# ==========================================================
# Tiện ích
# ==========================================================

def _now_ms() -> int:
    return int(time.time() * 1000)


def _vnd(value: Any) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "N/A"
    return f"{float(value):,.0f}".replace(",", ".") + " VND"


def _pct(value: Any) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "N/A"
    return f"{float(value) * 100:.1f}%"


def build_system_instruction(role: str, ctx: Mapping[str, Any] | None) -> str:
    """Bản Python của buildSystemInstruction (src/lib/prompts.ts) + câu về giả danh hóa."""

    from privacy_gateway import PRIVACY_PROMPT_NOTE

    section = ""
    if ctx:
        warnings = ctx.get("canh_bao") or []
        warning_lines = "\n".join(
            f"  {index}. [{item.get('severity')}] {item.get('name')}: {item.get('description')}"
            for index, item in enumerate(warnings, start=1)
        ) or "  (không có)"
        section = f"""

=== HỒ SƠ VAY ĐANG MỞ ===
Mã hồ sơ: {ctx.get('ma_ho_so') or 'N/A'}
Khách hàng: {ctx.get('ho_ten') or 'N/A'}
Trạng thái đề xuất (xác định): {ctx.get('trang_thai') or 'N/A'}
Số tiền đề nghị vay: {_vnd(ctx.get('so_tien_de_nghi_vay'))} · Thời hạn: {ctx.get('thoi_han_vay_thang') or 'N/A'} tháng
Thu nhập kê khai: {_vnd(ctx.get('thu_nhap_ke_khai'))} · Lương thực nhận: {_vnd(ctx.get('luong_thuc_nhan'))}
DTI: {_pct(ctx.get('dti'))} · DSR: {_pct(ctx.get('dsr'))}
Nguồn thu nhập dùng để tính: {ctx.get('nguon_thu_nhap') or 'N/A'}
Cảnh báo rủi ro ({len(warnings)}):
{warning_lines}
========================="""
    return f"""{SYSTEM_ROLES.get(role, SYSTEM_ROLES['underwriter'])}{section}

Quy tắc phản hồi:
- Tiếng Việt nghiệp vụ ngân hàng, súc tích, định lượng; dùng Markdown (tiêu đề ngắn, gạch đầu dòng, **in đậm** số liệu chính).
- Chỉ dựa trên số liệu của hồ sơ ở trên; nếu thiếu dữ liệu, nói rõ là thiếu, không bịa số.
- Không thay đổi các chỉ số đã tính xác định. Không tự phê duyệt/từ chối khoản vay — quyết định cuối thuộc Hội đồng Tín dụng.
- {PRIVACY_PROMPT_NOTE}"""


def chon_model_mac_dinh(provider: str, models: list[str], preferred: str | None = None) -> tuple[str, str | None]:
    """Chọn model theo danh sách thật từ API; không giả định model tồn tại (V6)."""

    if not models:
        raise ValueError("Nhà cung cấp không trả về model khả dụng.")
    wanted = preferred or (GEMINI_DEFAULT_MODEL if provider == "gemini" else None)
    if wanted and wanted in models:
        return wanted, None
    if wanted:
        fallback = next((model for model in models if "flash" in model.lower()), models[0])
        return fallback, f"Model {wanted} không khả dụng với khóa này; đang dùng {fallback}."
    return models[0], None


def nhan_model(model_id: str) -> str:
    """Nhãn hiển thị suy ra từ id model thật (không dùng danh sách viết cứng)."""

    words = []
    for word in str(model_id).replace("models/", "").split("-"):
        words.append(word.upper() if word.lower() in {"ai", "gpt"} else word[:1].upper() + word[1:])
    return " ".join(words) or str(model_id)


def lich_su_hop_le(messages: list[dict[str, Any]], limit: int = CHAT_HISTORY_LIMIT) -> list[dict[str, str]]:
    """Lịch sử gửi provider: bỏ notice và tin gửi lỗi, gộp lượt cùng vai, lượt đầu luôn là user, tối đa `limit` lượt."""

    turns: list[dict[str, str]] = []
    for item in messages:
        if not isinstance(item, dict) or item.get("notice") or item.get("failed"):
            continue
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        if turns and turns[-1]["role"] == role:
            turns[-1] = {"role": role, "content": turns[-1]["content"] + "\n\n" + content}
        else:
            turns.append({"role": str(role), "content": content})
    turns = turns[-max(1, int(limit)):]
    while turns and turns[0]["role"] != "user":
        turns.pop(0)
    return turns


def _toast(state: Any, title: str, description: str = "", kind: str = "info") -> None:
    toasts = list(state.get("v3_toasts") or [])
    toasts.append(
        {
            "id": f"t{_now_ms()}{len(toasts)}",
            "title": title[:120],
            "description": description[:300],
            "type": kind if kind in {"info", "success", "warning"} else "info",
        }
    )
    state["v3_toasts"] = toasts[-4:]


def _notice(content: str) -> dict[str, Any]:
    return {"role": "assistant", "content": content, "modelUsed": "Hệ thống", "timestamp": _now_ms(), "notice": True}


def khoi_tao_phien_v3(state: Any, settings: Mapping[str, Any]) -> None:
    from creditlens_ui_v2 import theme_mode_from_settings

    defaults: dict[str, Any] = {
        "v3_theme": theme_mode_from_settings(settings),
        "v3_motion": "full",
        "v3_active_page": PAGE_KEYS[0],
        "v3_selected_demo": "CASE-03 — Thu nhập không nhất quán",
        "v3_chat_messages": [_notice(WELCOME_MESSAGE)],
        "v3_chat_role": "underwriter",
        "v3_chat_model": "",
        "v3_toasts": [],
        "v3_upload_nonce": 0,
        "v3_upload_signature": "",
        "v3_recent_events": [],
        "v3_revision": 0,
    }
    for key, value in defaults.items():
        if key not in state:
            state[key] = value


# ==========================================================
# Kết nối AI (khóa chỉ ở Python backend)
# ==========================================================

def _secret_value(st: Any, name: str) -> str:
    try:
        secrets = getattr(st, "secrets", None)
        if secrets is None:
            return ""
        value = secrets.get(name, "")
        return str(value or "").strip()
    except Exception:
        return ""


def ket_noi_gemini_tu_secrets(st: Any) -> None:
    """Dùng st.secrets["GEMINI_API_KEY"] (chủ app cấu hình) — chỉ tải danh sách model, không inference."""

    state = st.session_state
    if state.get("v3_secrets_attempted"):
        return
    state["v3_secrets_attempted"] = True
    key = _secret_value(st, "GEMINI_API_KEY")
    connections = dict(state.get("llm_connections") or {})
    if not key or "gemini" in connections:
        return
    from credit_underwriting_colab import lay_danh_sach_model

    try:
        models = lay_danh_sach_model("gemini", key)
        model, notice = chon_model_mac_dinh("gemini", models)
    except (ValueError, RuntimeError) as exc:
        state["llm_connection_error"] = f"Khóa Gemini trong Secrets chưa dùng được: {exc}"
        return
    connections["gemini"] = {
        "provider": "gemini",
        "api_key": key,
        "fingerprint": hashlib.sha256(f"creditlens|gemini|{key}".encode("utf-8")).hexdigest(),
        "models": models,
        "model": model,
        "verified": True,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "source": "secrets",
    }
    state["llm_connections"] = connections
    if not state.get("active_llm_provider"):
        state["active_llm_provider"] = "gemini"
    if notice:
        _toast(state, "Model mặc định không khả dụng", notice, "warning")


def _ai_connection_status(st: Any) -> dict[str, Any]:
    from credit_underwriting_colab import NHA_CUNG_CAP_LLM, ket_noi_llm_dang_dung

    connection = ket_noi_llm_dang_dung(st)
    error = str(st.session_state.get("llm_connection_error") or "")
    if connection and not connection.get("generate_verified"):
        provider = str(connection.get("provider"))
        last_error = str(connection.get("generate_error") or "")
        return {
            "state": "partial",
            "label": OVERLOADED_LABEL if connection.get("generate_overloaded") else PARTIAL_LABEL,
            "message": (
                f"Lần kiểm tra gần nhất: {last_error} "
                if last_error
                else "Khóa đã tải được danh sách model nhưng chưa gọi thử model. "
            )
            + "Bấm “Kiểm tra kết nối” ở Cài đặt → Kết nối AI (1 request) hoặc gửi một câu hỏi.",
            "provider_label": NHA_CUNG_CAP_LLM[provider]["nhan"],
            "model": str(connection.get("model") or ""),
            "source": "secrets" if connection.get("source") == "secrets" else "session",
        }
    if connection:
        provider = str(connection.get("provider"))
        source = "secrets" if connection.get("source") == "secrets" else "session"
        return {
            "state": "connected",
            "label": "Đã kết nối",
            "message": (
                "Đang dùng khóa do chủ ứng dụng cấu hình trong Secrets. "
                if source == "secrets"
                else "Kết nối đã được xác minh trong phiên hiện tại. "
            )
            + "Khóa chỉ nằm ở máy chủ Python; phân tích xác định vẫn hoạt động độc lập.",
            "provider_label": NHA_CUNG_CAP_LLM[provider]["nhan"],
            "model": str(connection.get("model") or ""),
            "source": source,
        }
    if error:
        return {
            "state": "error",
            "label": "CONNECTION ERROR",
            "message": "Không thể xác thực kết nối AI. Kiểm tra API Key ở Cài đặt → Kết nối AI.",
            "provider_label": None,
            "model": None,
            "source": None,
        }
    return {
        "state": "disconnected",
        "label": "Chưa kết nối AI",
        "message": "Chưa có API Key đã xác minh. Phân tích xác định (Python) vẫn hoạt động đầy đủ; chat và diễn giải AI tạm khóa.",
        "provider_label": None,
        "model": None,
        "source": None,
    }


def _providers(st: Any) -> tuple[list[dict[str, Any]], str]:
    from credit_underwriting_colab import NHA_CUNG_CAP_LLM

    connections = st.session_state.get("llm_connections") or {}
    active = str(st.session_state.get("active_llm_provider") or "")
    output = []
    for provider, info in NHA_CUNG_CAP_LLM.items():
        connection = connections.get(provider) if isinstance(connections, dict) else None
        connected = bool(connection and connection.get("verified"))
        is_active = connected and provider == active
        output.append(
            {
                "provider": provider,
                "label": info["nhan"],
                "description": info["mo_ta"],
                "connected": connected,
                "active": is_active,
                "model": str(connection.get("model")) if connected else None,
                "model_count": len(connection.get("models") or []) if connected else 0,
                "status_label": "ĐANG DÙNG" if is_active else ("ĐÃ KẾT NỐI" if connected else "CHƯA KẾT NỐI"),
                "status_tone": "success" if is_active else ("info" if connected else "neutral"),
            }
        )
    return output, active if active in NHA_CUNG_CAP_LLM else ""


def _chat_models(st: Any) -> list[dict[str, str]]:
    from credit_underwriting_colab import ket_noi_llm_dang_dung

    connection = ket_noi_llm_dang_dung(st)
    if not connection:
        return []
    output = []
    for model_id in list(connection.get("models") or [])[:120]:
        badge = "ĐANG DÙNG" if model_id == connection.get("model") else "KHẢ DỤNG"
        output.append({"id": model_id, "label": nhan_model(model_id), "badge": badge})
    return output


def _danh_dau_goi_model(st: Any, model: str, error: str = "", *, overloaded: bool = False) -> None:
    """Ghi kết quả gọi generateContent thật vào kết nối đang dùng (không chứa khóa trong thông điệp)."""

    state = st.session_state
    provider = str(state.get("active_llm_provider") or "")
    connections = dict(state.get("llm_connections") or {})
    if provider not in connections:
        return
    connection = dict(connections[provider])
    connection["generate_verified"] = not error
    connection["generate_model"] = model
    connection["generate_error"] = error[:300]
    connection["generate_overloaded"] = bool(error) and overloaded
    connections[provider] = connection
    state["llm_connections"] = connections


def kiem_tra_ket_noi_model(st: Any) -> tuple[bool, str]:
    """Nút "Kiểm tra kết nối": đúng 1 generateContent ngắn ("ping") với model đang chọn."""

    from credit_underwriting_colab import ket_noi_llm_dang_dung, tao_phan_hoi_chat_ai

    connection = ket_noi_llm_dang_dung(st)
    if connection is None:
        return False, "Chưa có API Key đã xác minh."
    model = str(connection.get("model") or "")
    try:
        tao_phan_hoi_chat_ai(
            [{"role": "user", "content": "ping"}],
            str(connection.get("api_key") or ""),
            str(connection.get("provider") or ""),
            model,
            None,
            system_prompt=PING_SYSTEM_PROMPT,
        )
    except (ValueError, RuntimeError) as exc:
        _danh_dau_goi_model(st, model, str(exc), overloaded=bool(getattr(exc, "loi_phia_google", False)))
        return False, str(exc)
    _danh_dau_goi_model(st, model)
    return True, f"Đã gọi được model {model}."


# ==========================================================
# Giả danh hóa view model
# ==========================================================

def _pseudonymize_payload(value: Any, vault: Any) -> Any:
    from privacy_gateway import _walk_strings, pseudonymize_text

    return _walk_strings(value, lambda text: pseudonymize_text(text, vault))


def _prompt_context(result: Any, vault: Any) -> dict[str, Any] | None:
    if result is None:
        return None
    metrics = {item.ma_chi_so: item.gia_tri for item in result.chi_so}
    from credit_underwriting_colab import NHAN_RUI_RO

    data = result.du_lieu
    ctx = {
        "ma_ho_so": result.ma_ho_so,
        "ho_ten": data.ho_ten_khach_hang,
        "trang_thai": result.trang_thai,
        "thu_nhap_ke_khai": data.thu_nhap_ke_khai,
        "luong_thuc_nhan": data.luong_thuc_nhan,
        "so_tien_de_nghi_vay": data.so_tien_de_nghi_vay,
        "thoi_han_vay_thang": int(data.thoi_han_vay_thang) if data.thoi_han_vay_thang else None,
        "dti": metrics.get("dti"),
        "dsr": metrics.get("dsr"),
        "nguon_thu_nhap": result.nguon_thu_nhap_dung_de_tinh,
        "canh_bao": [
            {"severity": item.muc_do, "name": NHAN_RUI_RO.get(item.loai, item.loai), "description": item.giai_thich}
            for item in result.canh_bao
        ],
    }
    return _pseudonymize_payload(ctx, vault)


def _result_summary(result: Any, docs: Mapping[str, Any], vault: Any) -> dict[str, Any] | None:
    if result is None:
        return None
    from credit_underwriting_colab import NHAN_RUI_RO

    summary = {
        "ma_ho_so": result.ma_ho_so,
        "ten_ho_so": result.ten_ho_so,
        "trang_thai": result.trang_thai,
        "nguon_thu_nhap_dung_de_tinh": result.nguon_thu_nhap_dung_de_tinh,
        "du_lieu": {"ho_ten_khach_hang": result.du_lieu.ho_ten_khach_hang},
        "documents": [{"name": str(getattr(doc, "ten_tep", key))} for key, doc in docs.items()],
        "fields": [{"key": item.ma_truong} for item in result.truong_trich_xuat],
        "canh_bao": [
            {"severity": item.muc_do, "name": NHAN_RUI_RO.get(item.loai, item.loai), "description": item.giai_thich}
            for item in result.canh_bao
        ],
    }
    return _pseudonymize_payload(summary, vault)


# ==========================================================
# Dựng view model v3 (đúng shape của src/domain/contracts.ts)
# ==========================================================

def _case_context(result: Any, source: str | None, vault: Any) -> dict[str, Any]:
    if result is None:
        return {
            "case_id": None,
            "source": None,
            "status_label": "Chưa có hồ sơ đang mở",
            "status_tone": "neutral",
            "summary": "Tải tài liệu hoặc mở hồ sơ minh họa để bắt đầu.",
        }
    tone = {"REVIEW READY": "success", "HUMAN REVIEW REQUIRED": "warning"}.get(result.trang_thai, "neutral")
    return _pseudonymize_payload(
        {
            "case_id": result.ma_ho_so,
            "source": "Tệp người dùng tải lên" if source == "Tài liệu" else "Hồ sơ minh họa xác định",
            "status_label": result.trang_thai,
            "status_tone": tone,
            "summary": f"{result.ten_ho_so} · {len(result.truong_trich_xuat)} trường · {len(result.canh_bao)} cảnh báo rủi ro.",
        },
        vault,
    )


def _workflow(result: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ready = result is not None
    risks = bool(ready and result.canh_bao)
    steps = [
        {"key": "intake", "label": "Tiếp nhận hồ sơ", "description": "Kiểm tra định dạng PDF, lớp văn bản và phân loại loại tài liệu", "state": "complete" if ready else "current", "status_label": "Đã tiếp nhận" if ready else "Hiện tại"},
        {"key": "compute", "label": "Tính toán xác định", "description": "Tính toán DTI, DSR, thu nhập khả dụng và đệm số dư bằng công thức", "state": "complete" if ready else "upcoming", "status_label": "Đã tính toán" if ready else "Chưa thực hiện"},
        {"key": "crosscheck", "label": "Đối chiếu đa chứng từ", "description": "Kiểm tra chéo thu nhập 3 nguồn, đơn vị công tác và nợ quan sát", "state": ("warning" if risks else "complete") if ready else "upcoming", "status_label": ("Có mâu thuẫn" if risks else "Nhất quán") if ready else "Chưa thực hiện"},
        {"key": "human", "label": "Con người xem xét", "description": "Chuyên viên tín dụng kiểm tra bằng chứng và đưa ra quyết định cuối", "state": "current" if ready else "upcoming", "status_label": "Chờ chuyên viên" if ready else "Chưa thực hiện"},
    ]
    cards = [
        {"key": "card-1", "label": "Tiếp nhận và trích xuất văn bản", "description": "Kiểm tra tính toàn vẹn của PDF và trích xuất dữ liệu lớp văn bản.", "state": "complete" if ready else "current"},
        {"key": "card-2", "label": "Chuẩn hóa Schema", "description": "Ép kiểu dữ liệu số, ngày tháng, tên công ty và loại bỏ khoảng trắng.", "state": "complete" if ready else "upcoming"},
        {"key": "card-3", "label": "Động cơ quy tắc tín dụng", "description": "Kiểm tra các ngưỡng DTI, DSR, chênh lệch nợ và độ tin cậy trích xuất.", "state": ("warning" if risks else "complete") if ready else "upcoming"},
        {"key": "card-4", "label": "Tóm tắt & Xuất báo cáo", "description": "Tạo tóm tắt có căn cứ bằng chứng phục vụ con người xem xét cấp tín dụng.", "state": "current" if ready else "upcoming"},
    ]
    return steps, cards


def _navigation(state: Any) -> list[dict[str, Any]]:
    from credit_underwriting_colab import PAGES
    from privacy_gateway import LOCK_REASON, trang_bi_khoa

    items = []
    for index, key in enumerate(PAGE_KEYS):
        locked = trang_bi_khoa(PAGES[index], state)
        items.append(
            {
                "page": key,
                "label": PAGE_LABELS[key],
                "group": "Hồ sơ" if index < 5 else ("Kiểm chứng" if index < 7 else "Hệ thống"),
                "ordinal": index + 1,
                "locked": locked,
                "lock_reason": LOCK_REASON if locked else "",
            }
        )
    return items


def _logo_data_uri() -> str:
    path = _STATIC_DIR / "hub-logo-transparent.png"
    try:
        return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""


def _evaluation_report(st: Any, settings: Mapping[str, Any]) -> Mapping[str, Any] | None:
    report = st.session_state.get("evaluation_report")
    if isinstance(report, Mapping):
        return report
    from evaluation.evaluator import run_evaluation

    try:
        report = run_evaluation(threshold_config=settings.get("nguong"), provider="not-used", model="deterministic-saved-output")
    except Exception:
        return None
    st.session_state["evaluation_report"] = report
    return report


def build_v3_payload(st: Any, settings: Mapping[str, Any]) -> dict[str, Any]:
    """Toàn bộ view model gửi React: allowlist, giả danh hóa, không có API key hay vault."""

    from credit_underwriting_colab import DEMO_CASES, nguong_hieu_luc, ket_noi_llm_dang_dung, tom_tat_ai_hieu_luc
    from creditlens_ui_v2 import (
        build_core_page_view_model,
        build_demo_panel_view_model,
        build_evaluation_page_view_model,
        build_methodology_page_view_model,
        build_privacy_gateway_view_model,
        build_summary_page_view_model,
        serialize_core_page_view_model,
        serialize_demo_panel_view_model,
        serialize_evaluation_page_view_model,
        serialize_methodology_page_view_model,
        serialize_privacy_gateway_view_model,
        serialize_summary_page_view_model,
        V2CaseContext,
    )
    from privacy_gateway import LOCK_REASON, lay_vault, trang_bi_khoa
    from credit_underwriting_colab import PAGES

    state = st.session_state
    theme = state["v3_theme"] if state.get("v3_theme") in _THEMES else "system"
    active = state.get("v3_active_page") if state.get("v3_active_page") in PAGE_KEYS else PAGE_KEYS[0]
    thresholds = nguong_hieu_luc(settings.get("nguong"))
    vault = lay_vault(state)
    result = state.get("result")
    docs = state.get("docs") or {}
    locked = trang_bi_khoa(PAGES[PAGE_KEYS.index(active)], state)

    case_names = tuple(DEMO_CASES)
    selected = state.get("v3_selected_demo") if state.get("v3_selected_demo") in case_names else case_names[2]
    case_context = _case_context(result, state.get("ui_v2_case_source"), vault)
    demo = serialize_demo_panel_view_model(
        build_demo_panel_view_model(
            case_names=case_names,
            selected_case=selected,
            case_context=V2CaseContext(
                case_id=case_context["case_id"],
                source=case_context["source"],
                status_label=case_context["status_label"],
                status_tone=case_context["status_tone"],
                summary=case_context["summary"][:180],
            ),
            theme=theme,
            processing=False,
            error=None,
        )
    )
    connection = ket_noi_llm_dang_dung(st)
    ai_text = (
        tom_tat_ai_hieu_luc(st, connection, result.ma_ho_so, str(settings["system_prompt"])) if result is not None else ""
    )

    pages: dict[str, Any] = {"core": None, "summary": None, "methodology": None, "evaluation": None}
    if not locked:
        if active in CORE_KIND and result is not None:
            pages["core"] = _pseudonymize_payload(
                serialize_core_page_view_model(
                    build_core_page_view_model(
                        page=CORE_KIND[active], result=result, docs=docs, thresholds=thresholds, theme=theme
                    )
                ),
                vault,
            )
        elif active == "5_summary" and result is not None:
            pages["summary"] = _pseudonymize_payload(
                serialize_summary_page_view_model(
                    build_summary_page_view_model(
                        result=result, docs=docs, thresholds=thresholds, ai_explanation=ai_text or None, theme=theme
                    )
                ),
                vault,
            )
        elif active == "6_methodology":
            pages["methodology"] = serialize_methodology_page_view_model(build_methodology_page_view_model(theme=theme))
        elif active == "7_evaluation":
            pages["evaluation"] = serialize_evaluation_page_view_model(
                build_evaluation_page_view_model(report=_evaluation_report(st, settings), theme=theme)
            )

    privacy = serialize_privacy_gateway_view_model(build_privacy_gateway_view_model(session_state=state, theme=theme))
    privacy_state = {
        key: privacy[key]
        for key in ("state", "badge_label", "field_count", "public_warning", "consent_text", "consent_given", "case_id", "rows", "counts", "audit")
    }
    privacy_state["lock_reason"] = LOCK_REASON
    privacy_state["upload_plan"] = upload_plan_view(state)
    steps, cards = _workflow(result)
    providers, active_provider = _providers(st)
    models = _chat_models(st)
    chat_model = str(state.get("v3_chat_model") or "")
    if models and chat_model not in {item["id"] for item in models}:
        chat_model = str(connection.get("model")) if connection else models[0]["id"]
    chat_messages = []
    for message in state.get("v3_chat_messages") or []:
        item = {key: message[key] for key in ("role", "content", "modelUsed", "timestamp") if key in message}
        retry = message.get("retry")
        if isinstance(retry, dict):
            alt = retry.get("alt_model")
            item["retry"] = {
                "id": str(retry.get("id") or ""),
                "label": nhan_model(str(retry.get("model") or "")),
                "alt_label": nhan_model(str(alt)) if alt else None,
            }
        chat_messages.append(item)
    state["v3_revision"] = int(state.get("v3_revision") or 0) + 1
    payload = {
        "schema_version": SCHEMA_VERSION,
        "component": COMPONENT_NAME,
        "revision": state["v3_revision"],
        "theme": theme,
        "motion_level": state.get("v3_motion") if state.get("v3_motion") in _MOTION else "full",
        "active_page": active,
        "navigation": _navigation(state),
        "case_context": case_context,
        "workflow": steps,
        "process_cards": cards,
        "demo_cases": demo["cases"],
        "selected_demo": selected,
        "custom_case_name": "Hồ sơ tự tải lên" if state.get("ui_v2_case_source") == "Tài liệu" and result is not None else None,
        "result": _result_summary(result, docs, vault),
        "thresholds": thresholds,
        "pages": pages,
        "ai": {"explanation": _pseudonymize_payload(ai_text, vault) if ai_text and not locked else None},
        "chat": {
            "messages": _pseudonymize_payload(chat_messages, vault),
            "role": state.get("v3_chat_role") if state.get("v3_chat_role") in CHAT_ROLES else "underwriter",
            "model": chat_model,
            "models": models,
        },
        "providers": providers,
        "active_provider": active_provider,
        "ai_connection": _ai_connection_status(st),
        "privacy": privacy_state,
        "toasts": list(state.get("v3_toasts") or []),
        "assets": {"hub-logo-transparent.png": _logo_data_uri()},
    }
    state["v3_toasts"] = []
    return assert_safe_v3_payload(payload, st)


def assert_safe_v3_payload(payload: dict[str, Any], st: Any) -> dict[str, Any]:
    """Không có khóa bị cấm, không có API key, không có giá trị thật trong vault."""

    from creditlens_ui_v2 import _assert_no_prohibited_keys
    from privacy_gateway import lay_vault

    try:
        _assert_no_prohibited_keys(payload)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise V3ContractError("Payload v3 không thể tuần tự hóa an toàn.") from exc
    connections = st.session_state.get("llm_connections") or {}
    for connection in connections.values() if isinstance(connections, dict) else []:
        key = str(connection.get("api_key") or "")
        if key and key in encoded:
            raise V3ContractError("Payload v3 chứa API key.")
    vault = lay_vault(st.session_state)
    if vault is not None:
        payload_wo_assets = json.dumps({k: v for k, v in payload.items() if k != "assets"}, ensure_ascii=False)
        from privacy_gateway import PrivacyLeakError, assert_no_pii

        try:
            assert_no_pii(payload_wo_assets, vault)
        except PrivacyLeakError as exc:
            raise V3ContractError("Payload v3 còn giá trị định danh thật.") from exc
    return json.loads(encoded)


# ==========================================================
# Event từ React
# ==========================================================

def _claim(state: Any, event_id: str) -> bool:
    recent = list(state.get("v3_recent_events") or [])
    if event_id in recent:
        return False
    recent.append(event_id)
    state["v3_recent_events"] = recent[-50:]
    return True


def _recompute_result(st: Any, settings: Mapping[str, Any]) -> None:
    """Áp ngưỡng mới bằng chính hàm Python hiện có (phan_tich_tu_du_kien); không đổi công thức."""

    from credit_underwriting_colab import nguong_hieu_luc, phan_tich_tu_du_kien

    state = st.session_state
    result = state.get("result")
    if result is None:
        return
    updated = phan_tich_tu_du_kien(
        result.ma_ho_so,
        result.ten_ho_so,
        result.du_lieu,
        list(result.truong_trich_xuat),
        dict(state.get("docs") or {}),
        time.perf_counter(),
        nguong_hieu_luc(settings.get("nguong")),
    )
    state["result"] = updated
    state["ai_summary"] = ""
    state["ai_summary_context"] = {}


def _model_flash_khac(connection: Mapping[str, Any], model: str) -> str | None:
    """Model Flash khả dụng đầu tiên (theo lay_danh_sach_model) khác model vừa lỗi."""

    return next(
        (item for item in connection.get("models") or [] if "flash" in str(item).lower() and item != model),
        None,
    )


def _v3_chat_send(
    st: Any, text: str, role: str, model_requested: str, *, retry_of: dict[str, Any] | None = None
) -> None:
    from credit_underwriting_colab import ket_noi_llm_dang_dung, tao_phan_hoi_chat_ai
    from privacy_gateway import CHAT_LOCK_REASON, PrivacyLeakError, cong_hoan_tat, lay_vault

    state = st.session_state
    messages = list(state.get("v3_chat_messages") or [])
    if retry_of is not None:
        # Gửi lại: dùng lại đúng tin của chuyên viên (không nhân đôi trong lịch sử).
        user_message = retry_of
        user_message.pop("failed", None)
    else:
        user_message = {"role": "user", "content": text, "timestamp": _now_ms()}
        messages.append(user_message)
    state["v3_chat_messages"] = messages

    def _fail(content: str, retry: dict[str, Any] | None = None) -> None:
        # Tin user của lần gửi lỗi được đánh dấu để không thành lượt user mồ côi ở lần gửi sau.
        user_message["failed"] = True
        notice = _notice(content)
        if retry:
            notice["retry"] = retry
        messages.append(notice)

    if not cong_hoan_tat(state):
        _fail(CHAT_LOCK_REASON)
        return
    connection = ket_noi_llm_dang_dung(st)
    if connection is None:
        _fail(NO_AI_MESSAGE)
        return
    models = list(connection.get("models") or [])
    model = model_requested if model_requested in models else str(connection.get("model") or "")
    if model_requested and model_requested not in models:
        _toast(state, "Model không khả dụng", f"Đang dùng {model} theo danh sách model của nhà cung cấp.", "warning")
    vault = lay_vault(state)
    history = lich_su_hop_le(messages)
    system = build_system_instruction(role, _prompt_context(state.get("result"), vault))
    try:
        # Đúng 1 inference request cho mỗi lần Send.
        response = tao_phan_hoi_chat_ai(
            history,
            str(connection.get("api_key") or ""),
            str(connection.get("provider") or ""),
            model,
            vault,
            system_prompt=system,
        )
    except PrivacyLeakError as exc:
        _fail(str(exc))
        return
    except (ValueError, RuntimeError) as exc:
        # Thông điệp cụ thể + mã lỗi (VD: GEM-429); không chứa khóa hay nội dung hồ sơ.
        message = str(exc).replace(str(connection.get("api_key") or "") or "\0", "[REDACTED]")
        retry = None
        if getattr(exc, "loi_phia_google", False):
            # Lỗi 5xx phía Google: chỉ đề nghị thử lại, người dùng bấm mới gửi (không tự retry).
            retry = {"id": f"r{_now_ms()}{len(messages)}", "model": model, "alt_model": _model_flash_khac(connection, model)}
        _fail(f"**Không nhận được phản hồi từ {nhan_model(model)}.** {message}", retry)
        if getattr(exc, "ma", None):
            _danh_dau_goi_model(st, model, message, overloaded=retry is not None)
        return
    _danh_dau_goi_model(st, model)
    if any(re.search(pattern, response, re.IGNORECASE) for pattern in _PROHIBITED_DECISION):
        _fail("Câu trả lời của AI chứa khuyến nghị phê duyệt/từ chối nên đã bị chặn. Quyết định cuối cùng thuộc con người.")
        return
    messages.append({"role": "assistant", "content": response, "modelUsed": model, "timestamp": _now_ms()})


def _v3_chat_retry(st: Any, retry_id: Any, use_alt: bool) -> None:
    """Nút "Thử lại" / "Thử bằng {model khác}" sau lỗi 5xx: đúng 1 request mỗi lần bấm."""

    from credit_underwriting_colab import ket_noi_llm_dang_dung

    state = st.session_state
    messages = list(state.get("v3_chat_messages") or [])
    if len(messages) < 2 or not isinstance(retry_id, str):
        return
    notice, user_message = messages[-1], messages[-2]
    retry = notice.get("retry") if isinstance(notice, dict) else None
    # Chỉ thông báo lỗi mới nhất mới thử lại được; bấm lặp/cũ không gửi request.
    if not isinstance(retry, dict) or retry.get("id") != retry_id or user_message.get("role") != "user":
        return
    connection = ket_noi_llm_dang_dung(st)
    model = str(retry.get("model") or "")
    if use_alt:
        model = str(retry.get("alt_model") or "")
        if connection is None or model not in (connection.get("models") or []):
            return
        state["v3_chat_model"] = model
        provider = str(state.get("active_llm_provider") or "")
        connections = dict(state.get("llm_connections") or {})
        if provider in connections:
            connections[provider] = {**connections[provider], "model": model}
            state["llm_connections"] = connections
    state["v3_chat_messages"] = messages[:-1]  # bỏ thông báo lỗi cũ
    role = state.get("v3_chat_role") if state.get("v3_chat_role") in CHAT_ROLES else "underwriter"
    _v3_chat_send(st, str(user_message.get("content") or ""), str(role), model, retry_of=user_message)


def _v3_ai_generate(st: Any, settings: Mapping[str, Any]) -> None:
    from credit_underwriting_colab import ket_noi_llm_dang_dung, ngu_canh_tom_tat_ai, tao_dien_giai_bang_ai
    from privacy_gateway import cong_hoan_tat, lay_vault

    state = st.session_state
    result = state.get("result")
    if result is None or not cong_hoan_tat(state):
        _toast(state, "Chưa thể tạo diễn giải", "Hoàn tất Bước 0 · Bảo mật hồ sơ trước.", "warning")
        return
    connection = ket_noi_llm_dang_dung(st)
    if connection is None:
        _toast(state, "Chưa kết nối AI", "Mở Cài đặt → Kết nối AI. Hệ thống không tạo bản diễn giải mô phỏng.", "warning")
        return
    try:
        summary = tao_dien_giai_bang_ai(
            result,
            str(connection["api_key"]),
            str(connection["provider"]),
            str(connection["model"]),
            str(settings["system_prompt"]),
            lay_vault(state),
        )
    except (ValueError, RuntimeError) as exc:
        _toast(state, "Không thể tạo diễn giải", str(exc), "warning")
        return
    state["ai_summary"] = summary
    state["ai_summary_context"] = ngu_canh_tom_tat_ai(connection, result.ma_ho_so, str(settings["system_prompt"]))
    _toast(state, "Đã tạo diễn giải AI", "Nội dung hỗ trợ; không thay đổi kết quả xác định.", "success")


def handle_v3_event(st: Any, raw_event: Any, settings: dict[str, Any]) -> bool:
    """Validate + idempotency + action. Trả True khi cần rerun."""

    from credit_underwriting_colab import DEMO_CASES, GIOI_HAN_NGUONG, NGUONG, PAGES, mo_ho_so_minh_hoa, nguong_hieu_luc
    from privacy_gateway import (
        KEY_CONSENT,
        KEY_PENDING,
        bo_gia_tri_thu_cong,
        ho_so_cho_xac_nhan,
        them_gia_tri_thu_cong,
        trang_bi_khoa,
        xac_nhan_cong,
        xoa_ho_so_phien,
    )

    if not isinstance(raw_event, Mapping):
        return False
    event_id = raw_event.get("event_id")
    kind = raw_event.get("type")
    if not isinstance(event_id, str) or not _EVENT_ID.fullmatch(event_id) or not isinstance(kind, str):
        raise V3ContractError("Event v3 không hợp lệ.")
    state = st.session_state
    if not _claim(state, event_id):
        return False

    if kind == "navigate":
        page = raw_event.get("page")
        if page in PAGE_KEYS and not trang_bi_khoa(PAGES[PAGE_KEYS.index(page)], state):
            state["v3_active_page"] = page
    elif kind == "theme":
        mode = raw_event.get("mode")
        if mode in _THEMES:
            state["v3_theme"] = mode
            settings["che_do_giao_dien"] = {"light": "Sáng", "dark": "Tối", "system": "Theo hệ thống"}[mode]
    elif kind == "motion":
        if raw_event.get("level") in _MOTION:
            state["v3_motion"] = raw_event["level"]
    elif kind == "demo_select":
        if raw_event.get("case_name") in DEMO_CASES:
            state["v3_selected_demo"] = raw_event["case_name"]
    elif kind == "demo_open":
        name = raw_event.get("case_name")
        if name in DEMO_CASES:
            state["v3_selected_demo"] = name
            mo_ho_so_minh_hoa(st, name, nguong_hieu_luc(settings.get("nguong")))
            state["v3_active_page"] = PAGE_KEYS[0]
            _toast(state, "Đã quét hồ sơ minh họa", f"{name} · kiểm tra bảng xem trước ở Bước 0.", "success")
    elif kind == "clear_case":
        xoa_ho_so_phien(state)
        state.pop("v3_upload_plan", None)
        state.pop("v3_upload_plan_files", None)
        state["v3_active_page"] = PAGE_KEYS[0]
        state["v3_upload_nonce"] = int(state.get("v3_upload_nonce") or 0) + 1
        state["v3_upload_signature"] = ""
        _toast(state, "Đã đóng hồ sơ", "Đã xóa kết quả, tài liệu và vault giả danh hóa khỏi phiên.", "info")
    elif kind == "threshold":
        key, value = raw_event.get("key"), raw_event.get("value")
        if key in NGUONG and isinstance(value, (int, float)) and not isinstance(value, bool):
            low, high = GIOI_HAN_NGUONG[key]
            if low <= float(value) <= high:
                nguong = dict(settings.get("nguong") or NGUONG)
                nguong[key] = float(value)
                settings["nguong"] = nguong
                _recompute_result(st, settings)
                state.pop("evaluation_report", None)
                _toast(state, "Cập nhật ngưỡng kiểm tra", f"Đã điều chỉnh {key} sang {value}", "info")
    elif kind == "threshold_reset":
        settings["nguong"] = dict(NGUONG)
        _recompute_result(st, settings)
        state.pop("evaluation_report", None)
        _toast(state, "Khôi phục mặc định", "Đã đặt lại bộ ngưỡng kiểm tra ban đầu", "info")
    elif kind == "evaluation_run":
        state.pop("evaluation_report", None)
        _evaluation_report(st, settings)
        _toast(state, "Evaluation đã chạy", "Bộ đánh giá xác định của Python; không gọi LLM.", "success")
    elif kind == "ai_generate":
        _v3_ai_generate(st, settings)
    elif kind == "chat_send":
        text = raw_event.get("text")
        if isinstance(text, str) and text.strip():
            role = raw_event.get("role") if raw_event.get("role") in CHAT_ROLES else "underwriter"
            state["v3_chat_role"] = role
            model = str(raw_event.get("model") or "")[:160]
            _v3_chat_send(st, text.strip()[:4000], role, model)
    elif kind == "chat_retry":
        _v3_chat_retry(st, raw_event.get("retry_id"), bool(raw_event.get("alt")))
    elif kind == "chat_clear":
        state["v3_chat_messages"] = [
            _notice("Đã làm mới phiên hội thoại. Tôi sẵn sàng phân tích và giải đáp các nghiệp vụ tín dụng cùng bạn.")
        ]
    elif kind == "chat_role":
        if raw_event.get("role") in CHAT_ROLES:
            state["v3_chat_role"] = raw_event["role"]
    elif kind == "chat_model":
        state["v3_chat_model"] = str(raw_event.get("model") or "")[:160]
    elif kind == "provider":
        provider = raw_event.get("provider")
        if provider in (state.get("llm_connections") or {}):
            state["active_llm_provider"] = provider
            state["llm_active_selector"] = provider
        else:
            _toast(state, "Chưa kết nối provider này", "Xác thực API Key ở khung Kết nối AI bên dưới.", "warning")
    elif kind == "upload_assign":
        gan_loai_tep(state, raw_event.get("id"), raw_event.get("doc_type"))
    elif kind == "upload_continue":
        tiep_tuc_ke_hoach_tai_len(st, settings)
    elif kind == "upload_cancel":
        huy_ke_hoach_tai_len(state)
        _toast(state, "Đã hủy bảng phân loại", "Tệp đã tải chưa được trích xuất hay đưa vào cổng bảo mật.", "info")
    elif kind == "privacy_consent":
        state[KEY_CONSENT] = bool(raw_event.get("value"))
    elif kind == "privacy_confirm":
        try:
            vault = xac_nhan_cong(st)
            state["v3_upload_nonce"] = int(state.get("v3_upload_nonce") or 0) + 1
            _toast(state, "Đã giả danh hóa", f"{vault.so_truong} trường · các trang sau đã mở khóa.", "success")
        except ValueError as exc:
            _toast(state, "Chưa thể giả danh hóa", str(exc), "warning")
    elif kind == "privacy_cancel":
        xoa_ho_so_phien(state)
        state["v3_upload_nonce"] = int(state.get("v3_upload_nonce") or 0) + 1
        state["v3_upload_signature"] = ""
    elif kind == "privacy_mask_add":
        pending = ho_so_cho_xac_nhan(state)
        value = raw_event.get("value")
        if pending is not None and isinstance(value, str):
            try:
                updated = dict(pending)
                updated["findings"] = them_gia_tri_thu_cong(list(pending["findings"]), value[:120])
                state[KEY_PENDING] = updated
            except ValueError as exc:
                _toast(state, "Không thể thêm giá trị", str(exc), "warning")
    elif kind == "privacy_mask_remove":
        pending = ho_so_cho_xac_nhan(state)
        code = raw_event.get("code")
        if pending is not None and isinstance(code, str):
            updated = dict(pending)
            updated["findings"] = bo_gia_tri_thu_cong(list(pending["findings"]), code)
            state[KEY_PENDING] = updated
    else:
        raise V3ContractError("Loại event v3 không được phép.")
    return True


# ==========================================================
# Control native Streamlit (upload, kết nối AI, tải xuống)
# ==========================================================

def _upload_signature(files: list[Any]) -> str:
    digest = hashlib.sha256()
    for item in files:
        digest.update(f"{getattr(item, 'name', '')}|{getattr(item, 'size', 0)}".encode("utf-8"))
    return digest.hexdigest()


UPLOAD_TYPES = ("application", "income", "statement", "debt")
UPLOAD_MODE_DIRECTORY = "Tải cả thư mục hồ sơ"
UPLOAD_MODE_FILES = "Tải từng tệp"
UPLOAD_SKIP = "skip"
UPLOAD_MAX_FILES = 12
_SYSTEM_FILES = frozenset({"thumbs.db", "desktop.ini", ".ds_store", "icon\r"})


class _TepHoSo:
    """Bản sao tối thiểu của UploadedFile: tên gốc (basename) + bytes, dùng cho pipeline hiện có."""

    def __init__(self, name: str, data: bytes) -> None:
        self.name = name
        self._data = data
        self.size = len(data)

    def getvalue(self) -> bytes:
        return self._data


def duong_dan_tuong_doi(name: str) -> str:
    """Tên do trình duyệt gửi (có thể chứa thư mục con) → đường dẫn tương đối dạng a/b/c.pdf."""

    text = str(name or "").replace("\u2215", "/").replace("\\", "/").strip()
    parts = [part for part in text.split("/") if part not in {"", ".", ".."}]
    return "/".join(parts) or "tep-khong-ten"


def la_tep_an_hoac_he_thong(path: str) -> bool:
    parts = duong_dan_tuong_doi(path).split("/")
    if any(part.startswith(".") or part == "__MACOSX" for part in parts):
        return True
    return parts[-1].casefold() in _SYSTEM_FILES


def _kich_thuoc(size: int) -> str:
    return f"{size / (1024 * 1024):.1f} MB" if size >= 1024 * 1024 else f"{max(1, round(size / 1024))} KB"


def lap_ke_hoach_tai_len(files: list[Any]) -> tuple[dict[str, Any], dict[str, _TepHoSo]]:
    """Phân loại từng tệp (gợi ý tên tệp + nội dung PDF qua pypdf, cục bộ) để chuyên viên xác nhận.

    Không gửi tệp cho LLM. Tệp ẩn/hệ thống, không phải PDF, rỗng hoặc vượt 10 MB được liệt kê là bỏ qua.
    """

    import tempfile

    from credit_underwriting_colab import GIOI_HAN_TEP, doc_pdf, goi_y_loai_tu_ten_tep

    items: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    kept: dict[str, _TepHoSo] = {}
    with tempfile.TemporaryDirectory(prefix="creditlens_plan_") as temp_dir:
        for index, uploaded in enumerate(files, start=1):
            path = duong_dan_tuong_doi(getattr(uploaded, "name", ""))
            basename = path.rsplit("/", 1)[-1]
            if la_tep_an_hoac_he_thong(path):
                skipped.append({"path": path, "reason": "Tệp ẩn hoặc tệp hệ thống — bỏ qua."})
                continue
            if not basename.casefold().endswith(".pdf"):
                skipped.append({"path": path, "reason": "Không phải PDF — bỏ qua."})
                continue
            data = uploaded.getvalue()
            if len(data) > GIOI_HAN_TEP:
                skipped.append({"path": path, "reason": f"Vượt giới hạn 10 MB ({_kich_thuoc(len(data))})."})
                continue
            if len(kept) >= UPLOAD_MAX_FILES:
                skipped.append({"path": path, "reason": f"Vượt quá {UPLOAD_MAX_FILES} PDF cho một hồ sơ."})
                continue
            hint = goi_y_loai_tu_ten_tep(basename)
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", basename)
            temp_path = Path(temp_dir) / f"{index:02d}_{safe}"
            temp_path.write_bytes(data)
            try:
                document = doc_pdf(temp_path, hint or "application")
            except ValueError as exc:
                reason = str(exc).replace(temp_path.name, basename)
                skipped.append({"path": path, "reason": reason[:200]})
                continue
            detected = hint or document.loai_nhan_dien
            file_id = f"f{len(kept) + 1}"
            kept[file_id] = _TepHoSo(basename, data)
            items.append(
                {
                    "id": file_id,
                    "path": path,
                    "size_label": _kich_thuoc(len(data)),
                    "detected": detected if detected in UPLOAD_TYPES else "unknown",
                    "type": detected if detected in UPLOAD_TYPES else "unknown",
                    "confidence": round(float(document.do_tin_cay or 0.0), 2),
                    "basis": "Tên tệp + nội dung" if hint else "Nội dung PDF",
                    "readable": not document.loi,
                    "note": str(document.loi or "")[:160],
                }
            )
    return {"items": items, "skipped": skipped}, kept


def kiem_tra_ke_hoach(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Cảnh báo cho bảng xác nhận: thiếu bắt buộc, trùng loại, chưa xác định, tệp bị bỏ qua."""

    from credit_underwriting_colab import NHAN_LOAI_TAI_LIEU

    items = list(plan.get("items") or [])
    used = [item for item in items if item.get("type") in UPLOAD_TYPES]
    by_type: dict[str, list[str]] = {}
    for item in used:
        by_type.setdefault(str(item["type"]), []).append(str(item["path"]))
    duplicates = [
        f"Có {len(paths)} tệp cùng loại {NHAN_LOAI_TAI_LIEU[kind]}: " + ", ".join(paths) + "."
        for kind, paths in by_type.items()
        if len(paths) > 1
    ]
    missing = [NHAN_LOAI_TAI_LIEU[kind] for kind in ("application", "income", "statement") if kind not in by_type]
    unknown = [str(item["path"]) for item in items if item.get("type") == "unknown"]
    issues: list[dict[str, str]] = []
    for text in duplicates:
        issues.append({"level": "error", "text": text + " Chọn lại loại hoặc “Bỏ qua” một tệp."})
    if missing:
        issues.append({"level": "warning", "text": "Thiếu tài liệu bắt buộc: " + ", ".join(missing) + "."})
    if unknown:
        issues.append({"level": "warning", "text": "Chưa xác định loại: " + ", ".join(unknown) + " — chọn loại hoặc “Bỏ qua”."})
    for entry in plan.get("skipped") or []:
        issues.append({"level": "warning", "text": f"{entry['path']}: {entry['reason']}"})
    can_continue = bool(used) and not duplicates and not unknown
    return {"issues": issues, "can_continue": can_continue, "missing": missing, "duplicates": len(duplicates)}


def upload_plan_view(state: Any) -> dict[str, Any] | None:
    """View model bảng xác nhận phân loại (không có bytes tệp)."""

    from credit_underwriting_colab import NHAN_LOAI_TAI_LIEU

    plan = state.get("v3_upload_plan")
    if not isinstance(plan, Mapping):
        return None
    check = kiem_tra_ke_hoach(plan)
    options = [{"value": kind, "label": NHAN_LOAI_TAI_LIEU[kind]} for kind in UPLOAD_TYPES]
    options.append({"value": UPLOAD_SKIP, "label": "Bỏ qua (không dùng)"})
    rows = []
    for item in plan.get("items") or []:
        rows.append(
            {
                "id": item["id"],
                "path": item["path"],
                "size_label": item["size_label"],
                "type": item["type"],
                "detected_label": NHAN_LOAI_TAI_LIEU.get(item["detected"], "Chưa xác định"),
                "confidence": item["confidence"],
                "basis": item["basis"],
                "changed": item["type"] != item["detected"],
                "note": item.get("note") or "",
            }
        )
    return {
        "mode": str(plan.get("mode") or "directory"),
        "rows": rows,
        "skipped": list(plan.get("skipped") or []),
        "options": options,
        "issues": check["issues"],
        "can_continue": check["can_continue"],
    }


def xu_ly_tep_tai_len_v3(st: Any, files: list[Any], settings: Mapping[str, Any]) -> None:
    """Tệp mới → bảng xác nhận phân loại (chưa vào cổng). Chuyên viên bấm tiếp tục mới chạy pipeline."""

    from privacy_gateway import KEY_CONSENT

    state = st.session_state
    signature = _upload_signature(files)
    if not files or signature == state.get("v3_upload_signature"):
        return
    if not state.get(KEY_CONSENT):
        if state.get("v3_upload_warned") != signature:
            state["v3_upload_warned"] = signature
            _toast(state, "Cần xác nhận bảo mật", "Tick ô xác nhận ở Bước 0 trước; tệp sẽ được xử lý ngay sau đó.", "warning")
        return
    state["v3_upload_signature"] = signature
    plan, kept = lap_ke_hoach_tai_len(files)
    plan["mode"] = "directory" if state.get("v3_upload_mode") != UPLOAD_MODE_FILES else "files"
    state["v3_upload_plan"] = plan
    state["v3_upload_plan_files"] = kept
    state["v3_active_page"] = PAGE_KEYS[0]
    if not plan["items"]:
        _toast(state, "Không có PDF dùng được", "Kiểm tra bảng phân loại ở Bước 0 để xem lý do từng tệp.", "warning")
        return
    _toast(
        state,
        "Xác nhận phân loại tài liệu",
        f"Nhận {len(plan['items'])} PDF, bỏ qua {len(plan['skipped'])} tệp. Kiểm tra loại từng tệp ở Bước 0 rồi bấm tiếp tục.",
        "info",
    )


def gan_loai_tep(state: Any, file_id: Any, doc_type: Any) -> None:
    plan = state.get("v3_upload_plan")
    if not isinstance(plan, Mapping) or doc_type not in (*UPLOAD_TYPES, UPLOAD_SKIP):
        return
    items = []
    for item in plan.get("items") or []:
        if item.get("id") == file_id:
            item = {**item, "type": doc_type}
        items.append(item)
    state["v3_upload_plan"] = {**plan, "items": items}


def huy_ke_hoach_tai_len(state: Any) -> None:
    state.pop("v3_upload_plan", None)
    state.pop("v3_upload_plan_files", None)
    state["v3_upload_nonce"] = int(state.get("v3_upload_nonce") or 0) + 1
    state["v3_upload_signature"] = ""


def tiep_tuc_ke_hoach_tai_len(st: Any, settings: Mapping[str, Any]) -> None:
    """Theo phân loại đã xác nhận: pypdf → chuẩn hóa → công thức → Privacy Gateway (chờ xác nhận)."""

    from credit_underwriting_colab import lam_sach_ma_ho_so, nguong_hieu_luc, xu_ly_tai_lieu_tai_len
    from privacy_gateway import KEY_CONSENT, dua_vao_cong

    state = st.session_state
    plan = state.get("v3_upload_plan")
    kept = state.get("v3_upload_plan_files") or {}
    if not isinstance(plan, Mapping):
        return
    if not state.get(KEY_CONSENT):
        _toast(state, "Cần xác nhận bảo mật", "Tick ô xác nhận ở Bước 0 trước.", "warning")
        return
    check = kiem_tra_ke_hoach(plan)
    if not check["can_continue"]:
        _toast(state, "Chưa thể tiếp tục", "Xử lý các tệp trùng loại/chưa xác định trong bảng phân loại.", "warning")
        return
    uploads = {
        str(item["type"]): kept[item["id"]]
        for item in plan.get("items") or []
        if item.get("type") in UPLOAD_TYPES and item.get("id") in kept
    }
    case_id = lam_sach_ma_ho_so(f"UPLOAD-{datetime.now():%Y%m%d-%H%M%S}")
    try:
        result, docs, errors = xu_ly_tai_lieu_tai_len(case_id, uploads, nguong_hieu_luc(settings.get("nguong")))
    except ValueError as exc:
        _toast(state, "Không xử lý được tệp", str(exc), "warning")
        return
    state.pop("v3_upload_plan", None)
    state.pop("v3_upload_plan_files", None)
    findings = dua_vao_cong(st, result, docs, "Tài liệu")
    state["v3_active_page"] = PAGE_KEYS[0]
    if check["missing"]:
        errors = [*errors, "Thiếu tài liệu bắt buộc: " + ", ".join(check["missing"]) + "."]
    if errors:
        _toast(state, "Một số tệp chưa dùng được", " · ".join(errors)[:300], "warning")
    _toast(
        state,
        "Tải tài liệu thành công",
        f"Đã trích xuất {len(docs)} PDF và quét {len(findings)} giá trị định danh. Kiểm tra bảng xem trước ở Bước 0.",
        "success",
    )


def hien_thi_ket_noi_ai_v3(st: Any, settings: dict[str, Any]) -> None:
    """Kết nối AI bằng control gốc (st.text_input type=password); khóa chỉ lưu trong session Python."""

    from credit_underwriting_colab import (
        LUA_CHON_NHA_CUNG_CAP,
        NHA_CUNG_CAP_LLM,
        lay_danh_sach_model,
        nha_cung_cap_hieu_luc,
        nhan_ket_noi_llm,
        xoa_ket_noi_llm,
    )

    state = st.session_state
    st.markdown("<div id='v3-ai-connection'></div>", unsafe_allow_html=True)
    st.subheader("Kết nối AI (máy chủ Python)")
    st.caption(
        "API Key chỉ được giữ trong bộ nhớ phiên ở máy chủ và chỉ gửi đến nhà cung cấp bạn chọn. "
        "Khóa không có trong giao diện React, báo cáo hay log. Chủ ứng dụng có thể cấu hình GEMINI_API_KEY trong Secrets."
    )
    with st.form("v3_llm_connection_form", clear_on_submit=True):
        choice = st.selectbox("Nhà cung cấp", LUA_CHON_NHA_CUNG_CAP, index=2, key="v3_provider_choice")
        candidate = st.text_input("API Key cần xác thực", type="password", placeholder="Dán API Key")
        submitted = st.form_submit_button("Kết nối và tải danh sách model", type="primary", width="stretch")
    if submitted:
        key = candidate.strip()
        provider = nha_cung_cap_hieu_luc(choice, key)
        if len(key) < 12:
            state["llm_connection_error"] = "API Key chưa được nhập hoặc quá ngắn."
        elif provider is None:
            state["llm_connection_error"] = "Không thể nhận diện an toàn khóa này. Hãy chọn rõ nhà cung cấp rồi thử lại."
        else:
            try:
                with st.spinner(f"Đang xác thực {NHA_CUNG_CAP_LLM[provider]['nhan']}…"):
                    models = lay_danh_sach_model(provider, key)
                model, notice = chon_model_mac_dinh(provider, models)
                connections = dict(state.get("llm_connections") or {})
                connections[provider] = {
                    "provider": provider,
                    "api_key": key,
                    "fingerprint": hashlib.sha256(f"creditlens|{provider}|{key}".encode("utf-8")).hexdigest(),
                    "models": models,
                    "model": model,
                    "verified": True,
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                }
                state["llm_connections"] = connections
                state["active_llm_provider"] = provider
                state["llm_connection_error"] = ""
                settings["llm_provider"] = provider
                settings["model"] = model
                _toast(state, "Đã kết nối AI", f"{NHA_CUNG_CAP_LLM[provider]['nhan']} · {model}", "success")
                if notice:
                    _toast(state, "Model mặc định không khả dụng", notice, "warning")
                st.rerun()
            except (ValueError, RuntimeError) as exc:
                state["llm_connection_error"] = str(exc)
    if state.get("llm_connection_error"):
        st.error(state["llm_connection_error"])
    connections = state.get("llm_connections") or {}
    providers = [provider for provider in NHA_CUNG_CAP_LLM if provider in connections]
    if not providers:
        st.info("Chưa kết nối AI. Phân tích xác định vẫn hoạt động; chat và diễn giải AI chờ kết nối.")
        return
    if state.get("active_llm_provider") not in providers:
        state["active_llm_provider"] = providers[0]
    active = st.selectbox(
        "API Key sử dụng ngay",
        providers,
        index=providers.index(state["active_llm_provider"]),
        format_func=lambda value: nhan_ket_noi_llm(value, connections[value]),
        key="v3_active_provider_select",
    )
    state["active_llm_provider"] = active
    connection = dict(connections[active])
    models = list(connection.get("models") or [])
    current = connection.get("model") if connection.get("model") in models else models[0]
    selected = st.selectbox("Model", models, index=models.index(current), key=f"v3_model_{active}")
    if selected != connection.get("model"):
        connection["model"] = selected
        connection["generate_verified"] = False
        connection["generate_error"] = ""
        updated = dict(connections)
        updated[active] = connection
        state["llm_connections"] = updated
        state["v3_chat_model"] = selected
    if connection.get("source") == "secrets":
        st.caption("Khóa Gemini lấy từ Secrets của ứng dụng (không hiển thị).")
    if st.button("Kiểm tra kết nối", key="v3_ping_model", help="Gửi đúng 1 lệnh generateContent ngắn (“ping”) tới model đang chọn."):
        with st.spinner(f"Đang gọi thử {selected}…"):
            ok, detail = kiem_tra_ket_noi_model(st)
        _toast(state, "Đã kết nối" if ok else _ai_connection_status(st)["label"], detail, "success" if ok else "warning")
        st.rerun()
    latest = (state.get("llm_connections") or {}).get(active) or {}
    if latest.get("generate_verified"):
        st.success(f"Đã kết nối · đã gọi được model {latest.get('generate_model') or selected}.")
    elif latest.get("generate_error"):
        label = OVERLOADED_LABEL if latest.get("generate_overloaded") else PARTIAL_LABEL
        st.warning(f"{label}. {latest.get('generate_error')}")
    else:
        st.info(f"{PARTIAL_LABEL}. Bấm “Kiểm tra kết nối” để gọi thử model (1 request).")
    st.button("Xóa kết nối khỏi phiên", on_click=xoa_ket_noi_llm, args=(st, active), key="v3_remove_connection")


def hien_thi_xuat_bao_cao_v3(st: Any, settings: Mapping[str, Any]) -> None:
    from credit_underwriting_colab import (
        DINH_DANG_BAO_CAO,
        bao_cao_markdown,
        ket_noi_llm_dang_dung,
        lam_sach_ma_ho_so,
        nguong_hieu_luc,
        tom_tat_ai_hieu_luc,
    )
    from privacy_gateway import chon_phien_ban_bao_cao, hien_thi_noi_dung_ai, ket_qua_cho_bao_cao, lay_vault

    state = st.session_state
    result = state.get("result")
    if result is None:
        return
    vault = lay_vault(state)
    ai_text = tom_tat_ai_hieu_luc(st, ket_noi_llm_dang_dung(st), result.ma_ho_so, str(settings["system_prompt"]))
    st.subheader("Xuất báo cáo hồ sơ (Python)")
    version = chon_phien_ban_bao_cao(st)
    report_result, report_ai = ket_qua_cho_bao_cao(result, ai_text, vault, version)
    low = float(nguong_hieu_luc(settings.get("nguong"))["do_tin_cay_thap"])
    base = lam_sach_ma_ho_so(result.ma_ho_so)
    columns = st.columns(len(DINH_DANG_BAO_CAO))
    for column, (label, (extension, mime, generator)) in zip(columns, DINH_DANG_BAO_CAO.items()):
        with column:
            try:
                data = generator(report_result, report_ai, low)
                st.download_button(
                    f"Tải {label}",
                    data=data,
                    file_name=f"{base}_bao_cao_tham_dinh.{extension}",
                    mime=mime,
                    on_click="ignore",
                    width="stretch",
                    key=f"v3_dl_{extension}",
                )
            except Exception as exc:
                st.error(f"{label}: {type(exc).__name__}")
    md_column, json_column = st.columns(2)
    with md_column:
        st.download_button(
            "Tải Markdown (.md)",
            bao_cao_markdown(report_result) + (f"\n\n## Diễn giải AI\n{report_ai}" if report_ai else ""),
            file_name=f"{result.ma_ho_so}_tom_tat_tham_dinh.md",
            mime="text/markdown",
            on_click="ignore",
            width="stretch",
            key="v3_dl_markdown",
        )
    with json_column:
        st.download_button(
            "Tải JSON có cấu trúc (.json)",
            json.dumps(report_result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            file_name=f"{result.ma_ho_so}_ket_qua.json",
            mime="application/json",
            on_click="ignore",
            width="stretch",
            key="v3_dl_json",
        )
    if ai_text:
        with st.expander("Diễn giải AI cho chuyên viên (mặc định dạng mã)"):
            hien_thi_noi_dung_ai(st, ai_text, vault, key="privacy_show_real")


def hien_thi_tai_evaluation_v3(st: Any) -> None:
    from evaluation.evaluator import report_to_csv, report_to_json

    report = st.session_state.get("evaluation_report")
    if not isinstance(report, Mapping):
        return
    run_suffix = str(report["reproducibility"]["evaluation_run_id"]).split("-")[0]
    columns = st.columns(2)
    with columns[0]:
        st.download_button(
            "Tải Evaluation CSV", report_to_csv(dict(report)), file_name=f"creditlens_evaluation_{run_suffix}.csv",
            mime="text/csv", on_click="ignore", width="stretch", key="v3_dl_evaluation_csv",
        )
    with columns[1]:
        st.download_button(
            "Tải Evaluation JSON", report_to_json(dict(report)), file_name=f"creditlens_evaluation_{run_suffix}.json",
            mime="application/json", on_click="ignore", width="stretch", key="v3_dl_evaluation_json",
        )


def v3_host_styles(theme: str) -> str:
    """Ẩn header/footer/menu của Streamlit; control native nằm trong cột nội dung của App Shell."""

    dark = theme == "dark"
    surface, text, muted, border, canvas = (
        ("#101D39", "#F8FAFC", "#AEB8CB", "#33435F", "#081226") if dark else ("#FFFFFF", "#0F172A", "#526071", "#D8E0EC", "#F6F8FC")
    )
    system_dark = (
        "@media (prefers-color-scheme: dark){.stApp{--v3-surface:#101D39;--v3-text:#F8FAFC;--v3-muted:#AEB8CB;--v3-border:#33435F;--v3-canvas:#081226;}}"
        if theme == "system"
        else ""
    )
    return f"""
<style>
.stApp {{ --v3-surface:{surface}; --v3-text:{text}; --v3-muted:{muted}; --v3-border:{border}; --v3-canvas:{canvas};
  background:var(--v3-canvas); }}
{system_dark}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], footer, #MainMenu {{ display:none !important; }}
.stMainBlockContainer {{ max-width:none !important; padding:0 !important; }}
.stMainBlockContainer [data-testid="stVerticalBlock"] {{ gap:0.75rem; }}
.st-key-v3_native {{ position:relative; z-index:2; box-sizing:border-box; width:calc(100% - 320px) !important; margin:0 32px 48px 288px;
  padding:20px 24px; border:1px solid var(--v3-border); border-radius:12px; background:var(--v3-surface); color:var(--v3-text); }}
.st-key-v3_native h1, .st-key-v3_native h2, .st-key-v3_native h3, .st-key-v3_native label, .st-key-v3_native p {{ color:var(--v3-text); }}
.st-key-v3_native [data-testid="stCaptionContainer"] p {{ color:var(--v3-muted); }}
.st-key-v3_native button[kind="primary"], .st-key-v3_native button[kind="primaryFormSubmit"] {{ min-height:44px; border-radius:8px;
  background:#203469 !important; border-color:#203469 !important; }}
.st-key-v3_native button[kind="primary"] p, .st-key-v3_native button[kind="primaryFormSubmit"] p {{ color:#FFFFFF !important; }}
.st-key-v3_native input[type="password"] {{ font-family:ui-monospace, SFMono-Regular, Consolas, monospace; letter-spacing:.16em; }}
@media (max-width:1023px) {{ .st-key-v3_native {{ width:calc(100% - 32px) !important; margin:0 16px 32px; }} }}
@media (prefers-reduced-motion:reduce) {{ .stApp *, .stApp *::before, .stApp *::after {{ transition-duration:0ms !important; }} }}
</style>
"""


# ==========================================================
# Component
# ==========================================================

def load_v3_assets(asset_dir: str | Path | None = None) -> tuple[str, str]:
    directory = Path(asset_dir) if asset_dir is not None else _DIST_DIR
    try:
        javascript = (directory / "creditlens-v3.js").read_text(encoding="utf-8")
        stylesheet = (directory / "creditlens-v3.css").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise V3ComponentUnavailable("Bundle UI v3 chưa sẵn sàng.") from exc
    if not javascript.strip() or not stylesheet.strip():
        raise V3ComponentUnavailable("Bundle UI v3 không hợp lệ.")
    return javascript, stylesheet


def get_v3_renderer(st_module: Any, asset_dir: str | Path | None = None) -> Any:
    components = getattr(st_module, "components", None)
    v2 = getattr(components, "v2", None)
    factory = getattr(v2, "component", None)
    if not callable(factory):
        raise V3ComponentUnavailable("Streamlit Components v2 không khả dụng.")
    directory = Path(asset_dir) if asset_dir is not None else _DIST_DIR
    cache_key = (id(v2), str(directory.resolve()))
    if cache_key in _RENDERER_CACHE:
        return _RENDERER_CACHE[cache_key]
    javascript, stylesheet = load_v3_assets(directory)
    renderer = factory(
        COMPONENT_NAME,
        html='<div data-creditlens-v3-root="true"></div>',
        css=stylesheet,
        js=javascript,
        isolate_styles=True,
    )
    _RENDERER_CACHE[cache_key] = renderer
    return renderer


def _event_from(result: Any) -> Any:
    if isinstance(result, Mapping):
        return result.get("event")
    return getattr(result, "event", None)


def chay_ung_dung_streamlit_v3(st_module: Any | None = None, *, renderer: Callable[..., Any] | None = None) -> None:
    """Chạy giao diện 'Đánh giá tín dụng vay' (UI v3). Lỗi được app.py bắt để quay về v2."""

    if st_module is None:
        import streamlit as st_module

    from credit_underwriting_colab import LOGO_ICON_PATH, khoi_tao_trang_thai_phien

    st_module.set_page_config(
        page_title=APP_NAME,
        page_icon=str(LOGO_ICON_PATH) if LOGO_ICON_PATH.exists() else "🏦",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    khoi_tao_trang_thai_phien(st_module)
    settings = st_module.session_state.settings
    khoi_tao_phien_v3(st_module.session_state, settings)
    ket_noi_gemini_tu_secrets(st_module)
    component = renderer or get_v3_renderer(st_module)

    state = st_module.session_state
    active = state.get("v3_active_page")
    # Upload: control gốc của Streamlit (khung kéo-thả React chuyển tệp vào đây).
    upload_files: list[Any] = []
    payload = build_v3_payload(st_module, settings)
    st_module.markdown(v3_host_styles(payload["theme"]), unsafe_allow_html=True)
    result = component(key="creditlens_v3_app", data=payload, width="stretch", height="content")
    event = _event_from(result)

    needs_native = (
        active in {PAGE_KEYS[0], "8_settings"}
        or (active == "5_summary" and bool(payload["pages"].get("summary")))
        or (active == "7_evaluation" and isinstance(state.get("evaluation_report"), Mapping))
    )
    with st_module.container(key="v3_native") if needs_native else st_module.empty().container():
        if active == PAGE_KEYS[0]:
            mode = st_module.radio(
                "Cách tải hồ sơ",
                [UPLOAD_MODE_DIRECTORY, UPLOAD_MODE_FILES],
                index=0,
                horizontal=True,
                key="v3_upload_mode",
                help="Thư mục: chọn/kéo cả thư mục hồ sơ (gộp cả thư mục con, chỉ lấy PDF). Từng tệp: chọn nhiều PDF.",
            )
            directory = mode != UPLOAD_MODE_FILES
            with st_module.container(key="v3_upload_area"):
                st_module.caption("Bước 0 · Tải hồ sơ qua cổng bảo mật — control tải tệp gốc của Streamlit (PDF, tối đa 10 MB/tệp).")
                upload_files = list(
                    st_module.file_uploader(
                        "Chọn thư mục hồ sơ (3–4 PDF, có thể có thư mục con)" if directory else "Chọn từng PDF của hồ sơ",
                        type=["pdf"],
                        accept_multiple_files="directory" if directory else True,
                        key=f"v3_upload_{'dir' if directory else 'files'}_{int(state.get('v3_upload_nonce') or 0)}",
                    )
                    or []
                )
        elif active == "5_summary" and payload["pages"].get("summary"):
            hien_thi_xuat_bao_cao_v3(st_module, settings)
        elif active == "7_evaluation":
            hien_thi_tai_evaluation_v3(st_module)
        elif active == "8_settings":
            hien_thi_ket_noi_ai_v3(st_module, settings)

    rerun = False
    if event is not None:
        rerun = handle_v3_event(st_module, event, settings)
    if upload_files and _upload_signature(upload_files) != state.get("v3_upload_signature"):
        before = (state.get("v3_upload_signature"), state.get("v3_upload_warned"))
        xu_ly_tep_tai_len_v3(st_module, upload_files, settings)
        rerun = rerun or (state.get("v3_upload_signature"), state.get("v3_upload_warned")) != before
    if rerun:
        st_module.rerun()
