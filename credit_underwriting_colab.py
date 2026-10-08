"""
CREDITLENS — AI CREDIT UNDERWRITING COPILOT (STREAMLIT)

Chạy từ Jupyter Notebook trên máy tính:
1. Chạy: from credit_underwriting_colab import cai_dat_thu_vien; cai_dat_thu_vien()
2. Chạy ở ô kế tiếp: !python -m streamlit run credit_underwriting_colab.py
3. Mở http://localhost:8501

Để có URL ổn định, đưa project lên GitHub rồi triển khai trên Streamlit Community
Cloud hoặc một dịch vụ web luôn hoạt động. Ứng dụng có giao diện sáng/neon,
ô nhập API Key theo phiên cho OpenAI, Gemini, Claude hoặc DeepSeek và xuất báo cáo
Word, Excel, PDF trong bộ nhớ.
Khóa và nội dung tài liệu không được ghi vào tệp hay log.

Lưu ý:
- Chỉ dùng dữ liệu tổng hợp hoặc đã ẩn danh.
- Ứng dụng không phê duyệt hoặc từ chối khoản vay.
- Các ngưỡng là ngưỡng minh họa, không phải chính sách ngân hàng.
- Không cung cấp trình sửa/chạy source code từ website công khai.
"""

from __future__ import annotations

import importlib.util
import base64
import hashlib
import html
import io
import json
import logging
import math
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Mapping


CHAT_LOGGER = logging.getLogger("creditlens.chat")


def cai_dat_thu_vien() -> None:
    """Cài các thư viện còn thiếu trong Jupyter/Colab."""
    goi = {
        "streamlit": "streamlit>=1.64,<2",
        "openai": "openai>=1.100,<3",
        "pypdf": "pypdf>=5.0,<7",
        "pydantic": "pydantic>=2.0,<3",
        "docx": "python-docx>=1.1,<2",
        "openpyxl": "openpyxl>=3.1,<4",
        "reportlab": "reportlab>=4.2,<5",
        "jinja2": "Jinja2>=3.1,<4",
        "httpx": "httpx>=0.27,<1",
        "socksio": "socksio>=1.0,<2",
    }
    thieu = [yeu_cau for ten, yeu_cau in goi.items() if importlib.util.find_spec(ten) is None]
    if thieu:
        print("Đang cài thư viện:", ", ".join(thieu))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *thieu])


# Pydantic và pypdf phải có trước khi khai báo mô hình dữ liệu.
if importlib.util.find_spec("pydantic") is None or importlib.util.find_spec("pypdf") is None:
    cai_dat_thu_vien()

from pydantic import BaseModel, Field  # noqa: E402
from pypdf import PdfReader  # noqa: E402


# ==========================================================
# 1. CẤU HÌNH — NGƯỠNG MINH HỌA, KHÔNG PHẢI CHÍNH SÁCH
# ==========================================================

NGUONG = MappingProxyType({
    "do_tin_cay_thap": 0.75,
    "chenh_lech_thu_nhap": 0.15,
    "chenh_lech_thu_nhap_nghiem_trong": 0.30,
    "chenh_lech_no": 0.20,
    "dti_canh_bao": 0.40,
    "dsr_canh_bao": 0.45,
    "he_so_dem_so_du_thap": 1.00,
    "bien_dong_thu_nhap_cao": 0.25,
})
GIOI_HAN_NGUONG = MappingProxyType({
    "do_tin_cay_thap": (0.0, 1.0),
    "chenh_lech_thu_nhap": (0.0, 1.0),
    "chenh_lech_thu_nhap_nghiem_trong": (0.0, 1.0),
    "chenh_lech_no": (0.0, 5.0),
    "dti_canh_bao": (0.0, 2.0),
    "dsr_canh_bao": (0.0, 2.0),
    "he_so_dem_so_du_thap": (0.0, 20.0),
    "bien_dong_thu_nhap_cao": (0.0, 2.0),
})


def nguong_hieu_luc(candidate: Mapping[str, Any] | None = None) -> dict[str, float]:
    """Tạo snapshot ngưỡng riêng cho một lần chạy; không sửa trạng thái module dùng chung."""
    output = dict(NGUONG)
    if candidate:
        for key, default in output.items():
            value = candidate.get(key, default)
            lower, upper = GIOI_HAN_NGUONG[key]
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and lower <= float(value) <= upper
            ):
                output[key] = float(value)
    return output

GIOI_HAN_TEP = 10 * 1024 * 1024

NHAN_LOAI_TAI_LIEU = {
    "application": "Đơn đề nghị vay vốn",
    "income": "Chứng từ thu nhập",
    "statement": "Sao kê ngân hàng",
    "debt": "Thông tin nghĩa vụ nợ",
    "unknown": "Chưa xác định",
}

NHAN_TRANG_THAI = {
    "REVIEW READY": "SẴN SÀNG ĐỂ THẨM ĐỊNH",
    "HUMAN REVIEW REQUIRED": "CẦN CON NGƯỜI XEM XÉT",
    "INSUFFICIENT INFORMATION": "THÔNG TIN CHƯA ĐỦ",
}

NHAN_MUC_DO = {"HIGH": "CAO", "MEDIUM": "TRUNG BÌNH", "LOW": "THẤP", "INFO": "THÔNG TIN"}

NHAN_RUI_RO = {
    "INCOME_MISMATCH": "Thu nhập không nhất quán",
    "EMPLOYER_MISMATCH": "Đơn vị công tác không khớp",
    "POSSIBLE_UNDECLARED_DEBT": "Có thể có khoản nợ chưa kê khai",
    "JOB_TITLE_MISMATCH": "Chức danh không khớp",
    "EMPLOYMENT_DATE_MISMATCH": "Thời điểm làm việc không khớp",
    "HIGH_DTI_DEMO": "DTI cao theo ngưỡng minh họa",
    "HIGH_DSR_DEMO": "DSR cao theo ngưỡng minh họa",
    "LOW_BALANCE_BUFFER": "Hệ số đệm số dư thấp",
    "HIGH_INCOME_VOLATILITY": "Thu nhập biến động cao",
    "LOW_EXTRACTION_CONFIDENCE": "Độ tin cậy trích xuất thấp",
}


# ==========================================================
# 2. MÔ HÌNH DỮ LIỆU CÓ CẤU TRÚC (PYDANTIC)
# ==========================================================

class BangChung(BaseModel):
    tai_lieu: str
    trang: int | None = None
    truong_du_lieu: str
    gia_tri: str
    trich_doan: str | None = None


class TruongTrichXuat(BaseModel):
    ma_truong: str
    nhan: str
    gia_tri: str | float | int | None = None
    tai_lieu_nguon: str = "Không tìm thấy"
    trang: int | None = None
    do_tin_cay: float = Field(ge=0.0, le=1.0)
    bang_chung: BangChung | None = None


class DuLieuHoSo(BaseModel):
    ho_ten_khach_hang: str | None = None
    don_vi_cong_tac_ke_khai: str | None = None
    don_vi_cong_tac_chung_tu: str | None = None
    chuc_danh_ke_khai: str | None = None
    chuc_danh_chung_tu: str | None = None
    ngay_bat_dau_ke_khai: str | None = None
    ngay_bat_dau_chung_tu: str | None = None
    tham_nien_lam_viec_thang: float | None = None
    thu_nhap_ke_khai: float | None = None
    luong_thuc_nhan: float | None = None
    thu_nhap_qua_sao_ke: float | None = None
    so_tien_de_nghi_vay: float | None = None
    thoi_han_vay_thang: float | None = None
    khoan_tra_du_kien: float | None = None
    nghia_vu_no_ke_khai: float | None = None
    nghia_vu_no_quan_sat: float | None = None
    chi_phi_sinh_hoat: float | None = None
    so_du_binh_quan: float | None = None
    bien_dong_thu_nhap: float | None = None
    muc_dich_vay: str | None = None


class ChiSoTinDung(BaseModel):
    ma_chi_so: str
    ten: str
    gia_tri: float | None = None
    hien_thi: str
    cong_thuc: str
    trang_thai: Literal["Trong ngưỡng minh họa", "Cần chú ý", "Chưa đủ dữ liệu"]
    ghi_chu: str


class CanhBaoRuiRo(BaseModel):
    ma_rui_ro: str
    loai: str
    muc_do: Literal["HIGH", "MEDIUM", "LOW", "INFO"]
    giai_thich: str
    chenh_lech: str | None = None
    bang_chung: list[BangChung] = Field(default_factory=list)


class TaiLieu(BaseModel):
    loai_ky_vong: Literal["application", "income", "statement", "debt"]
    ten_tep: str
    van_ban: str = ""
    so_trang: int = 0
    dung_luong: int = 0
    trang_thai: Literal["Đã trích xuất", "Không đọc được"]
    loai_nhan_dien: str = "unknown"
    do_tin_cay: float = Field(ge=0.0, le=1.0)
    loi: str | None = None


class KetQuaThamDinh(BaseModel):
    ma_ho_so: str
    ten_ho_so: str
    du_lieu: DuLieuHoSo
    truong_trich_xuat: list[TruongTrichXuat]
    chi_so: list[ChiSoTinDung]
    canh_bao: list[CanhBaoRuiRo]
    thong_tin_thieu: list[str]
    cau_hoi_xac_minh: list[str]
    trang_thai: Literal["REVIEW READY", "HUMAN REVIEW REQUIRED", "INSUFFICIENT INFORMATION"]
    thu_nhap_dung_de_tinh: float | None = None
    nguon_thu_nhap_dung_de_tinh: str = "Không đủ dữ liệu"
    thu_nhap_duoc_xac_minh_doc_lap: bool = False
    thoi_diem_xu_ly: str
    thoi_gian_xu_ly_ms: int


# ==========================================================
# 3. HÀM TIỆN ÍCH
# ==========================================================

def tien(value: float | int | None) -> str:
    if value is None or not math.isfinite(float(value)):
        return "—"
    return f"{float(value):,.0f}".replace(",", ".") + " VND"


def phan_tram(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "—"
    return f"{value * 100:.1f}".replace(".", ",") + "%"


def so_thap_phan(value: float | None, so_chu_so: int = 2) -> str:
    if value is None or not math.isfinite(value):
        return "—"
    return f"{value:.{so_chu_so}f}".replace(".", ",")


def chia_an_toan(tu_so: float | None, mau_so: float | None) -> float | None:
    if tu_so is None or mau_so is None or mau_so <= 0:
        return None
    ket_qua = tu_so / mau_so
    return ket_qua if math.isfinite(ket_qua) else None


def chon_thu_nhap_dung_de_tinh(data: DuLieuHoSo) -> tuple[float | None, str, bool]:
    """Chọn nguồn thu nhập có thể giải thích và không gắn nhãn xác minh sai lệch."""
    doi_chieu = [
        (data.luong_thuc_nhan, "Lương thực nhận"),
        (data.thu_nhap_qua_sao_ke, "Ghi có bình quân sao kê"),
    ]
    hop_le = [
        (float(value), label)
        for value, label in doi_chieu
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0
    ]
    if hop_le:
        value, label = min(hop_le, key=lambda item: item[0])
        suffix = "giá trị thận trọng hơn" if len(hop_le) > 1 else "nguồn đối chiếu hiện có"
        return value, f"{label} ({suffix})", True
    if (
        isinstance(data.thu_nhap_ke_khai, (int, float))
        and not isinstance(data.thu_nhap_ke_khai, bool)
        and math.isfinite(float(data.thu_nhap_ke_khai))
        and float(data.thu_nhap_ke_khai) > 0
    ):
        return float(data.thu_nhap_ke_khai), "Thu nhập kê khai (chưa xác minh độc lập)", False
    return None, "Không đủ dữ liệu", False


def chuan_hoa_chuoi(value: str | None) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()
    text = re.sub(r"\b(cong ty|company|co|ltd|jsc|tnhh|cp)\b", "", text)
    return re.sub(r"[^a-z0-9]", "", text)


def chuan_hoa_ngay(value: str | None) -> date | None:
    """Chuẩn hóa các định dạng ngày phổ biến trước khi đối chiếu chéo."""
    text = (value or "").strip()
    if not text:
        return None
    patterns = (
        (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
        (r"\d{4}/\d{2}/\d{2}", "%Y/%m/%d"),
        (r"\d{2}/\d{2}/\d{4}", "%d/%m/%Y"),
        (r"\d{2}-\d{2}-\d{4}", "%d-%m-%Y"),
    )
    for pattern, format_string in patterns:
        match = re.search(rf"(?<!\d)({pattern})(?!\d)", text)
        if not match:
            continue
        try:
            return datetime.strptime(match.group(1), format_string).date()
        except ValueError:
            return None
    return None


def doc_so(raw: str) -> float | None:
    compact = re.sub(r"(?i)vnd|vnđ|đ|₫", "", raw).replace(" ", "")
    value = re.sub(r"[^0-9,.-]", "", compact)
    if not value or value in {"-", ".", ","}:
        return None
    separators = len(re.findall(r"[.,]", value))
    if separators > 1 or re.search(r"[.,]\d{3}$", value):
        value = re.sub(r"[.,]", "", value)
    else:
        value = value.replace(",", ".")
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except ValueError:
        return None


def trang_tai_vi_tri(text: str, index: int) -> int:
    return max(1, len(re.findall(r"--- TRANG \d+ ---", text[: max(index, 0)])))


def mau_bi_danh(alias: str) -> str:
    """Tạo regex cho nhãn, cho phép PDF ngắt dòng tại vị trí khoảng trắng."""
    return r"\s+".join(re.escape(part) for part in alias.split())


def tim_van_ban(text: str, aliases: list[str]) -> dict[str, Any] | None:
    for alias in aliases:
        match = re.search(rf"{mau_bi_danh(alias)}\s*[:\-–]?\s*([^\n\r|]{{2,100}})", text, re.IGNORECASE)
        if match:
            value = re.sub(r"\s{2,}.*", "", match.group(1).strip())
            return {
                "value": value,
                "page": trang_tai_vi_tri(text, match.start()),
                "confidence": 0.90,
                "excerpt": match.group(0)[:160],
            }
    return None


def tim_so_tien(text: str, aliases: list[str]) -> dict[str, Any] | None:
    for alias in aliases:
        # Không nhận phần đầu của ngày/tháng (ví dụ ``08/2026``) làm số tiền.
        # Trường hợp này thường xuất hiện khi PDF có bảng: tiêu đề cột nằm ở
        # một dòng, còn kỳ lương nằm ngay dòng kế tiếp. Negative lookahead buộc
        # regex bỏ lần xuất hiện đó và tiếp tục tìm nhãn + giá trị hợp lệ sau.
        pattern = rf"{mau_bi_danh(alias)}\s*[:\-–]?\s*(?:VND|VNĐ|₫|đ)?[ \t]*([0-9][0-9., \t]{{1,}})(?![/0-9])"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            number = doc_so(match.group(1))
            if number is not None:
                return {
                    "value": match.group(1).strip(),
                    "number": number,
                    "page": trang_tai_vi_tri(text, match.start()),
                    "confidence": 0.93,
                    "excerpt": match.group(0)[:160],
                }
    return None


def tim_ty_le(text: str, aliases: list[str]) -> dict[str, Any] | None:
    for alias in aliases:
        match = re.search(
            rf"{mau_bi_danh(alias)}\s*[:\-–]?\s*(?P<raw>[0-9]+(?:[.,][0-9]+)?)\s*(?P<unit>%?)",
            text,
            re.IGNORECASE,
        )
        if match:
            raw_text = match.group("raw")
            raw = float(raw_text.replace(",", "."))
            # Có dấu % thì luôn là phần trăm. Không có đơn vị: 1 trở lên được
            # hiểu là điểm phần trăm; số nhỏ hơn 1 được hiểu là tỷ lệ thập phân.
            number = raw / 100 if match.group("unit") == "%" or raw >= 1 else raw
            return {
                "value": raw_text + match.group("unit"),
                "number": number,
                "page": trang_tai_vi_tri(text, match.start()),
                "confidence": 0.88,
                "excerpt": match.group(0)[:160],
            }
    return None


# ==========================================================
# 4. DOCUMENT AI: KIỂM TRA, ĐỌC, PHÂN LOẠI PDF
# ==========================================================

TU_KHOA_PHAN_LOAI = {
    "application": ["loan application", "đơn đề nghị vay", "requested loan", "số tiền vay"],
    "income": ["salary", "payslip", "phiếu lương", "net pay", "xác nhận việc làm"],
    "statement": ["bank statement", "sao kê", "opening balance", "credit", "debit", "ghi có", "ghi nợ"],
    "debt": ["debt obligation", "credit obligation", "nghĩa vụ nợ", "outstanding debt"],
}


def goi_y_loai_tu_ten_tep(filename: str) -> str | None:
    """Nhận diện loại tài liệu từ tên tệp, dùng cho chế độ tải cả thư mục."""
    normalized = chuan_hoa_chuoi(Path(filename).stem)
    hints = {
        "debt": ("nghiavuno", "thongtinnghiavu", "debt", "obligation"),
        "statement": ("saokenganhang", "bankstatement", "accountstatement", "statement"),
        "income": (
            "chungtuthunhap",
            "xacnhanvieclam",
            "xacnhancongtac",
            "xacnhanthunhap",
            "hopdonglaodong",
            "phieuluong",
            "payslip",
            "salary",
            "income",
        ),
        "application": ("dondenghivay", "hosovay", "loanapplication", "applicationform"),
    }
    for doc_type, aliases in hints.items():
        if any(alias in normalized for alias in aliases):
            return doc_type
    return None


def phan_loai_tai_lieu(filename: str, text: str) -> tuple[str, float]:
    input_text = f"{filename} {text[:1800]}".lower()
    scores = {key: sum(keyword in input_text for keyword in keywords) for key, keywords in TU_KHOA_PHAN_LOAI.items()}
    filename_hint = goi_y_loai_tu_ten_tep(filename)
    if filename_hint:
        scores[filename_hint] += 4
    best = max(scores, key=scores.get)
    score = scores[best]
    return (best, min(0.98, 0.68 + score * 0.06)) if score else ("unknown", 0.35)


def doc_pdf(path_value: str | Path, loai_ky_vong: str) -> TaiLieu:
    path = Path(path_value)
    if not path.exists() or not path.is_file():
        raise ValueError("Không tìm thấy tệp đã tải lên.")
    size = path.stat().st_size
    if size == 0:
        raise ValueError(f"Tệp {path.name} trống nên không thể xử lý.")
    if size > GIOI_HAN_TEP:
        raise ValueError(f"Tệp {path.name} vượt giới hạn 10 MB.")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"{path.name}: phiên bản Colab hiện chỉ nhận PDF.")
    if path.read_bytes()[:5] != b"%PDF-":
        raise ValueError(f"{path.name}: nội dung tệp không đúng định dạng PDF.")

    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise ValueError(f"{path.name}: PDF có mật khẩu, vui lòng gỡ bảo vệ trước khi tải lên.")
        page_texts: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                extracted = page.extract_text() or ""
            except Exception:
                extracted = ""
            page_texts.append(f"\n--- TRANG {index} ---\n{extracted}\n")
        full_text = "".join(page_texts)
        readable = re.sub(r"--- TRANG \d+ ---", "", full_text).strip()
        predicted, confidence = phan_loai_tai_lieu(path.name, full_text)
        if len(readable) < 20:
            return TaiLieu(
                loai_ky_vong=loai_ky_vong,
                ten_tep=path.name,
                van_ban="",
                so_trang=len(reader.pages),
                dung_luong=size,
                trang_thai="Không đọc được",
                loai_nhan_dien=predicted,
                do_tin_cay=confidence,
                loi="Không có đủ lớp văn bản; có thể cần OCR hoặc con người xác nhận.",
            )
        return TaiLieu(
            loai_ky_vong=loai_ky_vong,
            ten_tep=path.name,
            van_ban=full_text,
            so_trang=len(reader.pages),
            dung_luong=size,
            trang_thai="Đã trích xuất",
            loai_nhan_dien=predicted,
            do_tin_cay=confidence,
        )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Không thể đọc {path.name}: PDF có thể lỗi hoặc dùng cấu trúc chưa hỗ trợ.") from exc


# ==========================================================
# 5. INFORMATION EXTRACTION + SCHEMA NORMALIZATION
# ==========================================================

def tao_truong(
    ma: str,
    nhan: str,
    value: str | float | int | None,
    tai_lieu: TaiLieu | None,
    found: dict[str, Any] | None,
) -> TruongTrichXuat:
    bang_chung = None
    if tai_lieu and found and value is not None:
        bang_chung = BangChung(
            tai_lieu=tai_lieu.ten_tep,
            trang=found.get("page"),
            truong_du_lieu=nhan,
            gia_tri=tien(value) if isinstance(value, (int, float)) else str(value),
            trich_doan=found.get("excerpt"),
        )
    return TruongTrichXuat(
        ma_truong=ma,
        nhan=nhan,
        gia_tri=value,
        tai_lieu_nguon=tai_lieu.ten_tep if tai_lieu else "Không tìm thấy",
        trang=found.get("page") if found else None,
        do_tin_cay=0.0 if value is None else float(found.get("confidence", 0.70) if found else 0.70),
        bang_chung=bang_chung,
    )


def trich_xuat_du_lieu(tai_lieu: dict[str, TaiLieu]) -> tuple[DuLieuHoSo, list[TruongTrichXuat]]:
    app = tai_lieu.get("application")
    income = tai_lieu.get("income")
    statement = tai_lieu.get("statement")
    debt_doc = tai_lieu.get("debt")

    app_text = app.van_ban if app and app.trang_thai == "Đã trích xuất" else ""
    income_text = income.van_ban if income and income.trang_thai == "Đã trích xuất" else ""
    statement_text = statement.van_ban if statement and statement.trang_thai == "Đã trích xuất" else ""
    debt_text = debt_doc.van_ban if debt_doc and debt_doc.trang_thai == "Đã trích xuất" else ""

    found: dict[str, dict[str, Any] | None] = {
        "ho_ten_khach_hang": tim_van_ban(app_text, ["Applicant Name", "Customer Name", "Họ và tên", "Tên khách hàng"]),
        "don_vi_cong_tac_ke_khai": tim_van_ban(app_text, ["Employer", "Company", "Đơn vị công tác", "Công ty"]),
        "don_vi_cong_tac_chung_tu": tim_van_ban(income_text, ["Employer", "Company", "Đơn vị công tác", "Công ty"]),
        "chuc_danh_ke_khai": tim_van_ban(app_text, ["Job Title", "Occupation", "Chức danh", "Nghề nghiệp"]),
        "chuc_danh_chung_tu": tim_van_ban(income_text, ["Job Title", "Position", "Chức danh", "Vị trí"]),
        "ngay_bat_dau_ke_khai": tim_van_ban(app_text, ["Employment Start Date", "Work Start Date", "Ngày bắt đầu làm việc"]),
        "ngay_bat_dau_chung_tu": tim_van_ban(income_text, ["Employment Start Date", "Start Date", "Ngày bắt đầu làm việc"]),
        "tham_nien_lam_viec_thang": tim_so_tien(app_text or income_text, ["Employment Duration Months", "Employment Months", "Thâm niên tháng"]),
        "thu_nhap_ke_khai": tim_so_tien(app_text, ["Declared Monthly Income", "Monthly Income", "Thu nhập kê khai", "Thu nhập hàng tháng"]),
        "luong_thuc_nhan": tim_so_tien(income_text, ["Net Salary", "Net Pay", "Salary", "Lương thực nhận", "Thu nhập sau thuế"]),
        "thu_nhap_qua_sao_ke": tim_so_tien(statement_text, ["Average Monthly Credit", "Average Salary Credit", "Average Income", "Thu nhập bình quân", "Bình quân ghi có"]),
        "so_tien_de_nghi_vay": tim_so_tien(app_text, ["Requested Loan Amount", "Loan Amount", "Số tiền đề nghị vay", "Số tiền vay"]),
        "thoi_han_vay_thang": tim_so_tien(app_text, ["Loan Term Months", "Term Months", "Thời hạn vay tháng", "Kỳ hạn tháng"]),
        "khoan_tra_du_kien": tim_so_tien(app_text, ["Proposed Monthly Payment", "Estimated Monthly Payment", "Trả nợ khoản vay mới hàng tháng"]),
        "nghia_vu_no_ke_khai": tim_so_tien(app_text, ["Declared Monthly Debt", "Existing Monthly Debt", "Nợ hàng tháng kê khai", "Nghĩa vụ nợ kê khai"]),
        "nghia_vu_no_quan_sat_sao_ke": tim_so_tien(statement_text, ["Recurring Debt Payment", "Observed Monthly Debt", "Monthly Debt Payment", "Thanh toán nợ định kỳ"]),
        "nghia_vu_no_quan_sat_tai_lieu": tim_so_tien(debt_text, ["Monthly Debt Payment", "Debt Obligation", "Nghĩa vụ nợ hàng tháng", "Thanh toán nợ hàng tháng"]),
        "chi_phi_sinh_hoat": tim_so_tien(app_text, ["Living Expenses", "Monthly Expenses", "Chi phí sinh hoạt", "Chi phí hàng tháng"]),
        "so_du_binh_quan": tim_so_tien(statement_text, ["Average Balance", "Average Account Balance", "Số dư bình quân"]),
        "bien_dong_thu_nhap": tim_ty_le(statement_text, ["Income Volatility", "Coefficient of Variation", "Biến động thu nhập"]),
        "muc_dich_vay": tim_van_ban(app_text, ["Loan Purpose", "Purpose", "Mục đích vay"]),
    }

    debt_found = found["nghia_vu_no_quan_sat_tai_lieu"] or found["nghia_vu_no_quan_sat_sao_ke"]
    debt_source = debt_doc if found["nghia_vu_no_quan_sat_tai_lieu"] else statement

    def text_value(key: str) -> str | None:
        return str(found[key]["value"]).strip() if found.get(key) else None

    def number_value(key: str) -> float | None:
        return float(found[key]["number"]) if found.get(key) else None

    data = DuLieuHoSo(
        ho_ten_khach_hang=text_value("ho_ten_khach_hang"),
        don_vi_cong_tac_ke_khai=text_value("don_vi_cong_tac_ke_khai"),
        don_vi_cong_tac_chung_tu=text_value("don_vi_cong_tac_chung_tu"),
        chuc_danh_ke_khai=text_value("chuc_danh_ke_khai"),
        chuc_danh_chung_tu=text_value("chuc_danh_chung_tu"),
        ngay_bat_dau_ke_khai=text_value("ngay_bat_dau_ke_khai"),
        ngay_bat_dau_chung_tu=text_value("ngay_bat_dau_chung_tu"),
        tham_nien_lam_viec_thang=number_value("tham_nien_lam_viec_thang"),
        thu_nhap_ke_khai=number_value("thu_nhap_ke_khai"),
        luong_thuc_nhan=number_value("luong_thuc_nhan"),
        thu_nhap_qua_sao_ke=number_value("thu_nhap_qua_sao_ke"),
        so_tien_de_nghi_vay=number_value("so_tien_de_nghi_vay"),
        thoi_han_vay_thang=number_value("thoi_han_vay_thang"),
        khoan_tra_du_kien=number_value("khoan_tra_du_kien"),
        nghia_vu_no_ke_khai=number_value("nghia_vu_no_ke_khai"),
        nghia_vu_no_quan_sat=float(debt_found["number"]) if debt_found else None,
        chi_phi_sinh_hoat=number_value("chi_phi_sinh_hoat"),
        so_du_binh_quan=number_value("so_du_binh_quan"),
        bien_dong_thu_nhap=number_value("bien_dong_thu_nhap"),
        muc_dich_vay=text_value("muc_dich_vay"),
    )

    definitions = [
        ("ho_ten_khach_hang", "Họ và tên khách hàng", data.ho_ten_khach_hang, app, found["ho_ten_khach_hang"]),
        ("thu_nhap_ke_khai", "Thu nhập hàng tháng kê khai", data.thu_nhap_ke_khai, app, found["thu_nhap_ke_khai"]),
        ("luong_thuc_nhan", "Lương thực nhận", data.luong_thuc_nhan, income, found["luong_thuc_nhan"]),
        ("thu_nhap_qua_sao_ke", "Ghi có bình quân hàng tháng", data.thu_nhap_qua_sao_ke, statement, found["thu_nhap_qua_sao_ke"]),
        ("don_vi_cong_tac_ke_khai", "Đơn vị công tác trên đơn vay", data.don_vi_cong_tac_ke_khai, app, found["don_vi_cong_tac_ke_khai"]),
        ("don_vi_cong_tac_chung_tu", "Đơn vị công tác trên chứng từ thu nhập", data.don_vi_cong_tac_chung_tu, income, found["don_vi_cong_tac_chung_tu"]),
        ("chuc_danh_ke_khai", "Chức danh trên đơn vay", data.chuc_danh_ke_khai, app, found["chuc_danh_ke_khai"]),
        ("chuc_danh_chung_tu", "Chức danh trên chứng từ thu nhập", data.chuc_danh_chung_tu, income, found["chuc_danh_chung_tu"]),
        ("ngay_bat_dau_ke_khai", "Ngày bắt đầu làm việc trên đơn vay", data.ngay_bat_dau_ke_khai, app, found["ngay_bat_dau_ke_khai"]),
        ("ngay_bat_dau_chung_tu", "Ngày bắt đầu làm việc trên chứng từ thu nhập", data.ngay_bat_dau_chung_tu, income, found["ngay_bat_dau_chung_tu"]),
        ("tham_nien_lam_viec_thang", "Thâm niên làm việc", data.tham_nien_lam_viec_thang, app or income, found["tham_nien_lam_viec_thang"]),
        ("so_tien_de_nghi_vay", "Số tiền đề nghị vay", data.so_tien_de_nghi_vay, app, found["so_tien_de_nghi_vay"]),
        ("thoi_han_vay_thang", "Thời hạn vay", data.thoi_han_vay_thang, app, found["thoi_han_vay_thang"]),
        ("khoan_tra_du_kien", "Khoản trả nợ dự kiến hàng tháng", data.khoan_tra_du_kien, app, found["khoan_tra_du_kien"]),
        ("nghia_vu_no_ke_khai", "Khoản trả nợ kê khai hàng tháng", data.nghia_vu_no_ke_khai, app, found["nghia_vu_no_ke_khai"]),
        ("nghia_vu_no_quan_sat", "Khoản trả nợ quan sát hàng tháng", data.nghia_vu_no_quan_sat, debt_source, debt_found),
        ("chi_phi_sinh_hoat", "Chi phí sinh hoạt", data.chi_phi_sinh_hoat, app, found["chi_phi_sinh_hoat"]),
        ("so_du_binh_quan", "Số dư tài khoản bình quân", data.so_du_binh_quan, statement, found["so_du_binh_quan"]),
        ("bien_dong_thu_nhap", "Mức biến động thu nhập", data.bien_dong_thu_nhap, statement, found["bien_dong_thu_nhap"]),
        ("muc_dich_vay", "Mục đích vay", data.muc_dich_vay, app, found["muc_dich_vay"]),
    ]
    fields = [tao_truong(*item) for item in definitions]
    return data, fields


# ==========================================================
# 6. CREDIT METRICS + CROSS-DOCUMENT RULE ENGINE
# ==========================================================

def bang_chung_cua(fields: list[TruongTrichXuat], key: str) -> list[BangChung]:
    for field in fields:
        if field.ma_truong == key and field.bang_chung:
            return [field.bang_chung]
    return []


def phan_tich_tu_du_kien(
    ma_ho_so: str,
    ten_ho_so: str,
    data: DuLieuHoSo,
    fields: list[TruongTrichXuat],
    docs: dict[str, TaiLieu],
    started_at: float,
    thresholds: Mapping[str, Any] | None = None,
) -> KetQuaThamDinh:
    nguong = nguong_hieu_luc(thresholds)
    income_for_calculation, income_source, income_independently_verified = chon_thu_nhap_dung_de_tinh(data)
    debt = data.nghia_vu_no_quan_sat if data.nghia_vu_no_quan_sat is not None else data.nghia_vu_no_ke_khai

    dti = chia_an_toan(debt, income_for_calculation)
    dsr = chia_an_toan(
        (debt + data.khoan_tra_du_kien) if debt is not None and data.khoan_tra_du_kien is not None else None,
        income_for_calculation,
    )
    disposable = (
        income_for_calculation - debt - data.chi_phi_sinh_hoat
        if income_for_calculation is not None and debt is not None and data.chi_phi_sinh_hoat is not None
        else None
    )
    balance_buffer = chia_an_toan(data.so_du_binh_quan, data.khoan_tra_du_kien)
    incomes = [v for v in [data.thu_nhap_ke_khai, data.luong_thuc_nhan, data.thu_nhap_qua_sao_ke] if v is not None and v > 0]
    income_difference = (max(incomes) - min(incomes)) / max(incomes) if len(incomes) >= 2 else None

    def status(value: float | None, threshold: float, lower_is_bad: bool = False) -> str:
        if value is None:
            return "Chưa đủ dữ liệu"
        is_attention = value < threshold if lower_is_bad else value > threshold
        return "Cần chú ý" if is_attention else "Trong ngưỡng minh họa"

    metrics = [
        ChiSoTinDung(ma_chi_so="dti", ten="DTI hiện hữu", gia_tri=dti, hien_thi=phan_tram(dti), cong_thuc="Nghĩa vụ nợ hiện hữu ÷ Thu nhập dùng để tính", trang_thai=status(dti, nguong["dti_canh_bao"]), ghi_chu=f"Nguồn thu nhập: {income_source}."),
        ChiSoTinDung(ma_chi_so="dsr", ten="DSR dự kiến", gia_tri=dsr, hien_thi=phan_tram(dsr), cong_thuc="(Nợ hiện hữu + Khoản trả dự kiến) ÷ Thu nhập dùng để tính", trang_thai=status(dsr, nguong["dsr_canh_bao"]), ghi_chu="Khoản trả dự kiến là đầu vào thủ công; hệ thống không tự đặt lãi suất."),
        ChiSoTinDung(ma_chi_so="thu_nhap_kha_dung", ten="Thu nhập còn lại trước khoản vay mới", gia_tri=disposable, hien_thi=tien(disposable), cong_thuc="Thu nhập dùng để tính − Nợ hiện hữu − Chi phí sinh hoạt", trang_thai="Chưa đủ dữ liệu" if disposable is None else ("Cần chú ý" if disposable < 0 else "Trong ngưỡng minh họa"), ghi_chu="Chưa trừ khoản trả dự kiến của khoản vay mới."),
        ChiSoTinDung(ma_chi_so="he_so_dem_so_du", ten="Hệ số đệm số dư", gia_tri=balance_buffer, hien_thi="—" if balance_buffer is None else f"{so_thap_phan(balance_buffer)}×", cong_thuc="Số dư bình quân ÷ Khoản trả dự kiến", trang_thai=status(balance_buffer, nguong["he_so_dem_so_du_thap"], lower_is_bad=True), ghi_chu="Chỉ báo thanh khoản dựa trên số dư bình quân."),
        ChiSoTinDung(ma_chi_so="chenh_lech_thu_nhap", ten="Chênh lệch thu nhập", gia_tri=income_difference, hien_thi=phan_tram(income_difference), cong_thuc="(Nguồn cao nhất − Nguồn thấp nhất) ÷ Nguồn cao nhất", trang_thai=status(income_difference, nguong["chenh_lech_thu_nhap"]), ghi_chu="So sánh đơn vay, chứng từ thu nhập và sao kê."),
        ChiSoTinDung(ma_chi_so="bien_dong_thu_nhap", ten="Biến động thu nhập", gia_tri=data.bien_dong_thu_nhap, hien_thi=phan_tram(data.bien_dong_thu_nhap), cong_thuc="Độ lệch chuẩn dòng tiền vào tháng ÷ Dòng tiền vào bình quân", trang_thai=status(data.bien_dong_thu_nhap, nguong["bien_dong_thu_nhap_cao"]), ghi_chu="Hệ số biến thiên khi sao kê có đủ dữ liệu theo tháng."),
    ]

    risks: list[CanhBaoRuiRo] = []

    def add_risk(loai: str, muc_do: str, giai_thich: str, evidence: list[BangChung], difference: str | None = None) -> None:
        risks.append(CanhBaoRuiRo(ma_rui_ro=f"R-{len(risks) + 1:03d}", loai=loai, muc_do=muc_do, giai_thich=giai_thich, chenh_lech=difference, bang_chung=evidence))

    if income_difference is not None and income_difference > nguong["chenh_lech_thu_nhap"]:
        add_risk(
            "INCOME_MISMATCH",
            "HIGH" if income_difference > nguong["chenh_lech_thu_nhap_nghiem_trong"] else "MEDIUM",
            f"Các nguồn thu nhập chênh {phan_tram(income_difference)}, vượt ngưỡng minh họa {phan_tram(nguong['chenh_lech_thu_nhap'])}. Cần xác minh nguồn thu và kỳ ghi nhận.",
            bang_chung_cua(fields, "thu_nhap_ke_khai") + bang_chung_cua(fields, "luong_thuc_nhan") + bang_chung_cua(fields, "thu_nhap_qua_sao_ke"),
            phan_tram(income_difference),
        )
    if data.don_vi_cong_tac_ke_khai and data.don_vi_cong_tac_chung_tu and chuan_hoa_chuoi(data.don_vi_cong_tac_ke_khai) != chuan_hoa_chuoi(data.don_vi_cong_tac_chung_tu):
        add_risk("EMPLOYER_MISMATCH", "HIGH", "Tên đơn vị công tác trên đơn vay và chứng từ thu nhập không khớp sau chuẩn hóa.", bang_chung_cua(fields, "don_vi_cong_tac_ke_khai") + bang_chung_cua(fields, "don_vi_cong_tac_chung_tu"))
    debt_input_invalid = False
    if data.nghia_vu_no_ke_khai is not None and data.nghia_vu_no_quan_sat is not None:
        declared_debt = float(data.nghia_vu_no_ke_khai)
        observed_debt = float(data.nghia_vu_no_quan_sat)
        debt_input_invalid = (
            not math.isfinite(declared_debt)
            or not math.isfinite(observed_debt)
            or declared_debt < 0
            or observed_debt < 0
        )
        debt_evidence = bang_chung_cua(fields, "nghia_vu_no_ke_khai") + bang_chung_cua(fields, "nghia_vu_no_quan_sat")
        if not debt_input_invalid and declared_debt == 0 and observed_debt > 0:
            absolute_difference = observed_debt - declared_debt
            add_risk(
                "POSSIBLE_UNDECLARED_DEBT",
                "HIGH",
                f"Nghĩa vụ nợ kê khai là 0 VND nhưng quan sát thấy {tien(observed_debt)}. Không tính tỷ lệ vì mẫu số bằng 0.",
                debt_evidence,
                tien(absolute_difference),
            )
        elif not debt_input_invalid and declared_debt > 0:
            debt_diff = abs(observed_debt - declared_debt) / declared_debt
            if debt_diff > nguong["chenh_lech_no"]:
                add_risk("POSSIBLE_UNDECLARED_DEBT", "HIGH" if observed_debt > declared_debt else "MEDIUM", f"Khoản trả nợ quan sát khác {phan_tram(debt_diff)} so với kê khai, vượt ngưỡng minh họa {phan_tram(nguong['chenh_lech_no'])}.", debt_evidence, phan_tram(debt_diff))
    if data.chuc_danh_ke_khai and data.chuc_danh_chung_tu and chuan_hoa_chuoi(data.chuc_danh_ke_khai) != chuan_hoa_chuoi(data.chuc_danh_chung_tu):
        add_risk("JOB_TITLE_MISMATCH", "MEDIUM", "Chức danh công việc khác nhau giữa đơn vay và chứng từ thu nhập.", bang_chung_cua(fields, "chuc_danh_ke_khai") + bang_chung_cua(fields, "chuc_danh_chung_tu"))
    employment_date_unparseable = False
    if data.ngay_bat_dau_ke_khai and data.ngay_bat_dau_chung_tu:
        declared_start_date = chuan_hoa_ngay(data.ngay_bat_dau_ke_khai)
        documented_start_date = chuan_hoa_ngay(data.ngay_bat_dau_chung_tu)
        employment_date_unparseable = declared_start_date is None or documented_start_date is None
        if not employment_date_unparseable and declared_start_date != documented_start_date:
            add_risk("EMPLOYMENT_DATE_MISMATCH", "MEDIUM", "Ngày bắt đầu làm việc không nhất quán giữa các chứng từ sau khi chuẩn hóa định dạng.", bang_chung_cua(fields, "ngay_bat_dau_ke_khai") + bang_chung_cua(fields, "ngay_bat_dau_chung_tu"))
    if dti is not None and dti > nguong["dti_canh_bao"]:
        add_risk("HIGH_DTI_DEMO", "HIGH", f"DTI {phan_tram(dti)} vượt ngưỡng cảnh báo minh họa {phan_tram(nguong['dti_canh_bao'])}. Đây không phải chính sách cấp tín dụng của ngân hàng.", bang_chung_cua(fields, "nghia_vu_no_quan_sat" if data.nghia_vu_no_quan_sat is not None else "nghia_vu_no_ke_khai") + bang_chung_cua(fields, "thu_nhap_qua_sao_ke" if data.thu_nhap_qua_sao_ke is not None else "luong_thuc_nhan"))
    if dsr is not None and dsr > nguong["dsr_canh_bao"]:
        add_risk("HIGH_DSR_DEMO", "HIGH", f"DSR dự kiến {phan_tram(dsr)} vượt ngưỡng cảnh báo minh họa {phan_tram(nguong['dsr_canh_bao'])}.", bang_chung_cua(fields, "nghia_vu_no_quan_sat") + bang_chung_cua(fields, "khoan_tra_du_kien") + bang_chung_cua(fields, "thu_nhap_qua_sao_ke"))
    if balance_buffer is not None and balance_buffer < nguong["he_so_dem_so_du_thap"]:
        add_risk("LOW_BALANCE_BUFFER", "MEDIUM", f"Hệ số đệm số dư {so_thap_phan(balance_buffer)}× thấp hơn ngưỡng minh họa {so_thap_phan(nguong['he_so_dem_so_du_thap'])}×.", bang_chung_cua(fields, "so_du_binh_quan") + bang_chung_cua(fields, "khoan_tra_du_kien"))
    if data.bien_dong_thu_nhap is not None and data.bien_dong_thu_nhap > nguong["bien_dong_thu_nhap_cao"]:
        add_risk("HIGH_INCOME_VOLATILITY", "MEDIUM", f"Biến động dòng tiền vào {phan_tram(data.bien_dong_thu_nhap)} vượt ngưỡng minh họa {phan_tram(nguong['bien_dong_thu_nhap_cao'])}.", bang_chung_cua(fields, "bien_dong_thu_nhap"))

    missing: list[str] = []
    for key, label in [("application", "Đơn đề nghị vay vốn"), ("income", "Chứng từ thu nhập"), ("statement", "Sao kê ngân hàng")]:
        if key not in docs or docs[key].trang_thai == "Không đọc được":
            missing.append(label)
    if not data.ho_ten_khach_hang:
        missing.append("Họ và tên khách hàng")
    if data.so_tien_de_nghi_vay is None:
        missing.append("Số tiền đề nghị vay")
    if income_for_calculation is None:
        missing.append("Thu nhập dùng để tính")
    if data.thoi_han_vay_thang is None:
        missing.append("Thời hạn vay")

    low_confidence = [f for f in fields if f.gia_tri is not None and f.do_tin_cay < nguong["do_tin_cay_thap"]]
    if low_confidence:
        add_risk("LOW_EXTRACTION_CONFIDENCE", "MEDIUM", f"{len(low_confidence)} trường có độ tin cậy dưới {phan_tram(nguong['do_tin_cay_thap'])} và cần con người kiểm tra.", [f.bang_chung for f in low_confidence if f.bang_chung])

    questions: list[str] = []
    risk_types = {risk.loai for risk in risks}
    if "INCOME_MISMATCH" in risk_types:
        questions.append("Nguồn thu nhập nào là thường xuyên, có thể xác minh và thuộc đúng kỳ sao kê?")
    if "EMPLOYER_MISMATCH" in risk_types:
        questions.append("Khách hàng có thay đổi đơn vị công tác hay chứng từ nào đã lỗi thời?")
    if "POSSIBLE_UNDECLARED_DEBT" in risk_types:
        questions.append("Các khoản ghi nợ định kỳ nào là nghĩa vụ tín dụng hiện hữu của khách hàng?")
    if not income_independently_verified and income_for_calculation is not None:
        questions.append("Thu nhập dùng để tính hiện chỉ dựa trên kê khai; vui lòng bổ sung chứng từ hoặc sao kê để xác minh độc lập.")
    if employment_date_unparseable:
        questions.append("Một hoặc cả hai ngày bắt đầu làm việc không ở định dạng được hỗ trợ; vui lòng chuẩn hóa và đối chiếu lại.")
    if debt_input_invalid:
        questions.append("Nghĩa vụ nợ có giá trị âm hoặc không hợp lệ; vui lòng xác nhận dữ liệu trước khi tính chênh lệch.")
    if data.khoan_tra_du_kien is None:
        questions.append("Khoản trả nợ dự kiến hàng tháng theo phương án vay là bao nhiêu?")
    if missing:
        questions.append("Vui lòng bổ sung hoặc xác nhận: " + ", ".join(missing) + ".")
    if not questions:
        questions.append("Cán bộ tín dụng vui lòng xác nhận lại dữ kiện và bằng chứng trước khi đưa ra quyết định cuối cùng.")

    critical_missing = {"Đơn đề nghị vay vốn", "Chứng từ thu nhập", "Sao kê ngân hàng", "Số tiền đề nghị vay", "Thu nhập dùng để tính"}
    if any(item in critical_missing for item in missing):
        final_status = "INSUFFICIENT INFORMATION"
    elif risks or not income_independently_verified or employment_date_unparseable or debt_input_invalid:
        final_status = "HUMAN REVIEW REQUIRED"
    else:
        final_status = "REVIEW READY"

    return KetQuaThamDinh(
        ma_ho_so=ma_ho_so,
        ten_ho_so=ten_ho_so,
        du_lieu=data,
        truong_trich_xuat=fields,
        chi_so=metrics,
        canh_bao=risks,
        thong_tin_thieu=missing,
        cau_hoi_xac_minh=questions,
        trang_thai=final_status,
        thu_nhap_dung_de_tinh=income_for_calculation,
        nguon_thu_nhap_dung_de_tinh=income_source,
        thu_nhap_duoc_xac_minh_doc_lap=income_independently_verified,
        thoi_diem_xu_ly=datetime.now(timezone.utc).isoformat(),
        thoi_gian_xu_ly_ms=max(1, round((time.perf_counter() - started_at) * 1000)),
    )


def phan_tich_tai_lieu(
    ma_ho_so: str,
    docs: dict[str, TaiLieu],
    thresholds: Mapping[str, Any] | None = None,
) -> KetQuaThamDinh:
    started = time.perf_counter()
    data, fields = trich_xuat_du_lieu(docs)
    return phan_tich_tu_du_kien(
        ma_ho_so,
        data.ho_ten_khach_hang or "Hồ sơ tín dụng đã tải lên",
        data,
        fields,
        docs,
        started,
        thresholds,
    )


# ==========================================================
# 7. 10 HỒ SƠ TỔNG HỢP MINH HỌA
# ==========================================================

BASE_DATA = DuLieuHoSo(
    ho_ten_khach_hang="Nguyễn Minh Anh",
    don_vi_cong_tac_ke_khai="Công ty Cổ phần Công nghệ Aurora",
    don_vi_cong_tac_chung_tu="Công ty Cổ phần Công nghệ Aurora",
    chuc_danh_ke_khai="Chuyên viên phân tích dữ liệu",
    chuc_danh_chung_tu="Chuyên viên phân tích dữ liệu",
    ngay_bat_dau_ke_khai="2022-06-01",
    ngay_bat_dau_chung_tu="2022-06-01",
    tham_nien_lam_viec_thang=48,
    thu_nhap_ke_khai=25_000_000,
    luong_thuc_nhan=24_000_000,
    thu_nhap_qua_sao_ke=23_800_000,
    so_tien_de_nghi_vay=300_000_000,
    thoi_han_vay_thang=36,
    khoan_tra_du_kien=7_500_000,
    nghia_vu_no_ke_khai=2_000_000,
    nghia_vu_no_quan_sat=2_000_000,
    chi_phi_sinh_hoat=9_000_000,
    so_du_binh_quan=18_000_000,
    bien_dong_thu_nhap=0.06,
    muc_dich_vay="Sửa chữa nhà ở",
)

DEMO_CASES = {
    "CASE-01 — Hồ sơ bình thường": ({}, {}, []),
    "CASE-02 — Thiếu thu nhập": ({"luong_thuc_nhan": None, "thu_nhap_qua_sao_ke": None, "thu_nhap_ke_khai": None}, {}, []),
    "CASE-03 — Thu nhập không nhất quán": ({"thu_nhap_ke_khai": 25_000_000, "luong_thuc_nhan": 18_000_000, "thu_nhap_qua_sao_ke": 14_000_000}, {}, []),
    "CASE-04 — Đơn vị công tác không khớp": ({"don_vi_cong_tac_chung_tu": "Công ty TNHH Bán lẻ Zenith"}, {}, []),
    "CASE-05 — Nghĩa vụ nợ không nhất quán": ({"nghia_vu_no_ke_khai": 2_000_000, "nghia_vu_no_quan_sat": 5_000_000}, {}, []),
    "CASE-06 — DTI cao": ({"thu_nhap_ke_khai": 18_000_000, "luong_thuc_nhan": 18_000_000, "thu_nhap_qua_sao_ke": 18_000_000, "nghia_vu_no_ke_khai": 8_000_000, "nghia_vu_no_quan_sat": 8_000_000}, {}, []),
    "CASE-07 — Sao kê không đọc được": ({"thu_nhap_qua_sao_ke": None, "so_du_binh_quan": None, "bien_dong_thu_nhap": None}, {}, ["statement"]),
    "CASE-08 — Đơn vay chưa đầy đủ": ({"so_tien_de_nghi_vay": None, "thoi_han_vay_thang": None}, {}, []),
    "CASE-09 — Độ tin cậy thấp": ({}, {"luong_thuc_nhan": 0.58, "don_vi_cong_tac_chung_tu": 0.61}, []),
    "CASE-10 — Nhiều cảnh báo đồng thời": ({"thu_nhap_ke_khai": 28_000_000, "luong_thuc_nhan": 19_000_000, "thu_nhap_qua_sao_ke": 15_000_000, "don_vi_cong_tac_chung_tu": "Công ty TNHH Bán lẻ Zenith", "nghia_vu_no_ke_khai": 2_000_000, "nghia_vu_no_quan_sat": 8_000_000, "khoan_tra_du_kien": 9_000_000, "so_du_binh_quan": 5_000_000, "bien_dong_thu_nhap": 0.34}, {}, []),
}

FIELD_LABELS = {
    "ho_ten_khach_hang": "Họ và tên khách hàng",
    "don_vi_cong_tac_ke_khai": "Đơn vị công tác trên đơn vay",
    "don_vi_cong_tac_chung_tu": "Đơn vị công tác trên chứng từ thu nhập",
    "chuc_danh_ke_khai": "Chức danh trên đơn vay",
    "chuc_danh_chung_tu": "Chức danh trên chứng từ thu nhập",
    "ngay_bat_dau_ke_khai": "Ngày bắt đầu làm việc trên đơn vay",
    "ngay_bat_dau_chung_tu": "Ngày bắt đầu làm việc trên chứng từ thu nhập",
    "tham_nien_lam_viec_thang": "Thâm niên làm việc",
    "thu_nhap_ke_khai": "Thu nhập hàng tháng kê khai",
    "luong_thuc_nhan": "Lương thực nhận",
    "thu_nhap_qua_sao_ke": "Ghi có bình quân hàng tháng",
    "so_tien_de_nghi_vay": "Số tiền đề nghị vay",
    "thoi_han_vay_thang": "Thời hạn vay",
    "khoan_tra_du_kien": "Khoản trả nợ dự kiến hàng tháng",
    "nghia_vu_no_ke_khai": "Khoản trả nợ kê khai hàng tháng",
    "nghia_vu_no_quan_sat": "Khoản trả nợ quan sát hàng tháng",
    "chi_phi_sinh_hoat": "Chi phí sinh hoạt",
    "so_du_binh_quan": "Số dư tài khoản bình quân",
    "bien_dong_thu_nhap": "Mức biến động thu nhập",
    "muc_dich_vay": "Mục đích vay",
}


def du_lieu_demo(
    case_name: str,
    thresholds: Mapping[str, Any] | None = None,
) -> tuple[KetQuaThamDinh, dict[str, TaiLieu]]:
    if case_name not in DEMO_CASES:
        raise ValueError("Không tìm thấy hồ sơ minh họa.")
    changes, confidence_overrides, missing_docs = DEMO_CASES[case_name]
    raw = BASE_DATA.model_dump()
    raw.update(changes)
    data = DuLieuHoSo(**raw)
    source_map = {
        "ho_ten_khach_hang": ("don_de_nghi_vay.pdf", 1), "thu_nhap_ke_khai": ("don_de_nghi_vay.pdf", 1),
        "don_vi_cong_tac_ke_khai": ("don_de_nghi_vay.pdf", 1), "chuc_danh_ke_khai": ("don_de_nghi_vay.pdf", 1),
        "ngay_bat_dau_ke_khai": ("don_de_nghi_vay.pdf", 1), "so_tien_de_nghi_vay": ("don_de_nghi_vay.pdf", 2),
        "thoi_han_vay_thang": ("don_de_nghi_vay.pdf", 2), "khoan_tra_du_kien": ("don_de_nghi_vay.pdf", 2),
        "nghia_vu_no_ke_khai": ("don_de_nghi_vay.pdf", 2), "chi_phi_sinh_hoat": ("don_de_nghi_vay.pdf", 2),
        "muc_dich_vay": ("don_de_nghi_vay.pdf", 2), "luong_thuc_nhan": ("chung_tu_thu_nhap.pdf", 1),
        "don_vi_cong_tac_chung_tu": ("chung_tu_thu_nhap.pdf", 1), "chuc_danh_chung_tu": ("chung_tu_thu_nhap.pdf", 1),
        "ngay_bat_dau_chung_tu": ("chung_tu_thu_nhap.pdf", 1), "tham_nien_lam_viec_thang": ("chung_tu_thu_nhap.pdf", 1),
        "thu_nhap_qua_sao_ke": ("sao_ke_ngan_hang_6_thang.pdf", 4), "nghia_vu_no_quan_sat": ("sao_ke_ngan_hang_6_thang.pdf", 5),
        "so_du_binh_quan": ("sao_ke_ngan_hang_6_thang.pdf", 6), "bien_dong_thu_nhap": ("sao_ke_ngan_hang_6_thang.pdf", 6),
    }
    fields: list[TruongTrichXuat] = []
    for key, value in data.model_dump().items():
        filename, page = source_map.get(key, ("don_de_nghi_vay.pdf", 1))
        display = phan_tram(value) if key == "bien_dong_thu_nhap" and isinstance(value, (int, float)) else (tien(value) if isinstance(value, (int, float)) and key not in {"tham_nien_lam_viec_thang", "thoi_han_vay_thang"} else str(value or ""))
        evidence = None if value is None else BangChung(tai_lieu=filename, trang=page, truong_du_lieu=FIELD_LABELS[key], gia_tri=display, trich_doan=f"{FIELD_LABELS[key]}: {display}")
        fields.append(TruongTrichXuat(ma_truong=key, nhan=FIELD_LABELS[key], gia_tri=value, tai_lieu_nguon="Không tìm thấy" if value is None else filename, trang=None if value is None else page, do_tin_cay=0.0 if value is None else confidence_overrides.get(key, 0.96), bang_chung=evidence))

    def fake_doc(key: str, name: str, pages: int) -> TaiLieu:
        return TaiLieu(loai_ky_vong=key, ten_tep=name, van_ban="Tài liệu tổng hợp minh họa", so_trang=pages, dung_luong=48_000, trang_thai="Đã trích xuất", loai_nhan_dien=key, do_tin_cay=0.99)

    docs: dict[str, TaiLieu] = {}
    if "application" not in missing_docs:
        docs["application"] = fake_doc("application", "don_de_nghi_vay.pdf", 2)
    if "income" not in missing_docs:
        docs["income"] = fake_doc("income", "chung_tu_thu_nhap.pdf", 2)
    if "statement" not in missing_docs:
        docs["statement"] = fake_doc("statement", "sao_ke_ngan_hang_6_thang.pdf", 6)
    docs["debt"] = fake_doc("debt", "thong_tin_nghia_vu_no.pdf", 1)
    case_id = case_name.split(" — ")[0]
    result = phan_tich_tu_du_kien(
        case_id,
        case_name,
        data,
        fields,
        docs,
        time.perf_counter() - 0.12,
        thresholds,
    )
    return result, docs


# ==========================================================
# 8. TẠO BÁO CÁO VÀ BẢNG HIỂN THỊ
# ==========================================================

def bao_cao_markdown(result: KetQuaThamDinh) -> str:
    d = result.du_lieu
    metric_lines = "\n".join(f"- **{m.ten}:** {m.hien_thi} — {m.cong_thuc}" for m in result.chi_so)
    risk_lines = "\n".join(f"- **{r.ma_rui_ro} · {NHAN_RUI_RO.get(r.loai, r.loai)} [{NHAN_MUC_DO[r.muc_do]}]:** {r.giai_thich}" for r in result.canh_bao) or "- Không phát hiện mâu thuẫn trọng yếu theo các quy tắc minh họa đã cấu hình."
    missing_lines = "\n".join(f"- {item}" for item in result.thong_tin_thieu) or "- Không phát hiện hạng mục bắt buộc còn thiếu."
    question_lines = "\n".join(f"- {item}" for item in result.cau_hoi_xac_minh)
    evidence_lines = "\n".join(f"- **{r.ma_rui_ro}:** {e.tai_lieu}, trang {e.trang or 'không xác định'}, {e.truong_du_lieu} = {e.gia_tri}" for r in result.canh_bao for e in r.bang_chung) or "- Không có bằng chứng rủi ro được tạo."
    return f"""# TÓM TẮT THẨM ĐỊNH TÍN DỤNG

**Mã hồ sơ:** {result.ma_ho_so}  
**Trạng thái:** {NHAN_TRANG_THAI[result.trang_thai]}

## 1. Tổng quan khách hàng
- Khách hàng: {d.ho_ten_khach_hang or 'Thông tin chưa đủ'}
- Đơn vị công tác: {d.don_vi_cong_tac_ke_khai or 'Thông tin chưa đủ'}
- Chức danh: {d.chuc_danh_ke_khai or 'Thông tin chưa đủ'}

## 2. Đề nghị vay vốn
- Số tiền đề nghị vay: {tien(d.so_tien_de_nghi_vay)}
- Thời hạn: {so_thap_phan(d.thoi_han_vay_thang, 0) if d.thoi_han_vay_thang is not None else '—'} tháng
- Mục đích: {d.muc_dich_vay or 'Thông tin chưa đủ'}

## 3. Thông tin tài chính dùng để tính
- Thu nhập dùng để tính: {tien(result.thu_nhap_dung_de_tinh)}
- Nguồn/cơ sở: {result.nguon_thu_nhap_dung_de_tinh}
- Trạng thái nguồn: {'Đã có nguồn đối chiếu độc lập' if result.thu_nhap_duoc_xac_minh_doc_lap else 'Chỉ kê khai hoặc chưa đủ dữ liệu'}
- Khoản trả nợ quan sát hàng tháng: {tien(d.nghia_vu_no_quan_sat)}
- Số dư bình quân: {tien(d.so_du_binh_quan)}

## 4. Chỉ số tín dụng
{metric_lines}

## 5. Kiểm tra nhất quán và cảnh báo rủi ro
{risk_lines}

## 6. Thông tin còn thiếu
{missing_lines}

## 7. Câu hỏi cần xác minh
{question_lines}

## 8. Bằng chứng
{evidence_lines}

## 9. Trạng thái xem xét của con người
**{NHAN_TRANG_THAI[result.trang_thai]}**. Ứng dụng này chỉ hỗ trợ thẩm định tín dụng, không phê duyệt hoặc từ chối khoản vay. Quyết định cuối cùng bắt buộc do con người xem xét.
"""


def gia_tri_truong_hien_thi(field: TruongTrichXuat) -> str:
    """Định dạng một trường trích xuất để dùng thống nhất trên web và báo cáo."""
    if isinstance(field.gia_tri, (int, float)):
        if field.ma_truong == "bien_dong_thu_nhap":
            return phan_tram(float(field.gia_tri))
        if field.ma_truong in {"tham_nien_lam_viec_thang", "thoi_han_vay_thang"}:
            return f"{float(field.gia_tri):.0f} tháng"
        return tien(field.gia_tri)
    return str(field.gia_tri) if field.gia_tri not in (None, "") else "Không tìm thấy"


def _noi_dung_tong_quan(result: KetQuaThamDinh) -> list[tuple[str, str]]:
    d = result.du_lieu
    return [
        ("Mã hồ sơ", result.ma_ho_so),
        ("Tên hồ sơ", result.ten_ho_so),
        ("Trạng thái", NHAN_TRANG_THAI[result.trang_thai]),
        ("Khách hàng", d.ho_ten_khach_hang or "Thông tin chưa đủ"),
        ("Đơn vị công tác kê khai", d.don_vi_cong_tac_ke_khai or "Thông tin chưa đủ"),
        ("Chức danh kê khai", d.chuc_danh_ke_khai or "Thông tin chưa đủ"),
        ("Số tiền đề nghị vay", tien(d.so_tien_de_nghi_vay)),
        ("Thời hạn vay", f"{so_thap_phan(d.thoi_han_vay_thang, 0)} tháng" if d.thoi_han_vay_thang is not None else "Thông tin chưa đủ"),
        ("Mục đích vay", d.muc_dich_vay or "Thông tin chưa đủ"),
        ("Thu nhập dùng để tính", tien(result.thu_nhap_dung_de_tinh)),
        ("Nguồn thu nhập dùng để tính", result.nguon_thu_nhap_dung_de_tinh),
        (
            "Trạng thái nguồn thu nhập",
            "Đã có nguồn đối chiếu độc lập"
            if result.thu_nhap_duoc_xac_minh_doc_lap
            else "Chỉ kê khai hoặc chưa đủ dữ liệu",
        ),
        ("Nghĩa vụ nợ quan sát", tien(d.nghia_vu_no_quan_sat)),
        ("Số dư bình quân", tien(d.so_du_binh_quan)),
        ("Thời điểm xử lý", result.thoi_diem_xu_ly),
        ("Thời gian xử lý", f"{result.thoi_gian_xu_ly_ms} ms"),
    ]


def _xoa_markdown(text: str) -> str:
    plain = re.sub(r"^#{1,6}\s*", "", text or "", flags=re.MULTILINE)
    plain = plain.replace("**", "").replace("`", "")
    return plain.strip()


def tao_bao_cao_word(
    result: KetQuaThamDinh,
    ai_summary: str = "",
    low_confidence_threshold: float | None = None,
) -> bytes:
    """Tạo báo cáo DOCX trong bộ nhớ, không ghi dữ liệu khách hàng xuống máy chủ."""
    from docx import Document
    from docx.enum.section import WD_SECTION
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt, RGBColor

    navy = "123B5D"
    pale_blue = "EAF6FF"
    pale_gray = "F5F8FC"
    border = "D5E2EE"

    def shade(cell, fill: str) -> None:
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = tc_pr.find(qn("w:shd"))
        if shd is None:
            shd = OxmlElement("w:shd")
            tc_pr.append(shd)
        shd.set(qn("w:fill"), fill)

    def borders(cell) -> None:
        tc_pr = cell._tc.get_or_add_tcPr()
        tc_borders = tc_pr.first_child_found_in("w:tcBorders")
        if tc_borders is None:
            tc_borders = OxmlElement("w:tcBorders")
            tc_pr.append(tc_borders)
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            tag = "w:" + edge
            element = tc_borders.find(qn(tag))
            if element is None:
                element = OxmlElement(tag)
                tc_borders.append(element)
            element.set(qn("w:val"), "single")
            element.set(qn("w:sz"), "4")
            element.set(qn("w:color"), border)

    def cell_text(cell, value: Any, *, bold: bool = False, color: str = "1F2D3D") -> None:
        cell.text = ""
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(str(value))
        run.bold = bold
        run.font.name = "Arial"
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor.from_string(color)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        borders(cell)

    def add_table(headers: list[str], rows: list[list[Any]], widths_mm: list[float] | None = None):
        table = doc.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True
        for index, header in enumerate(headers):
            cell_text(table.rows[0].cells[index], header, bold=True, color="FFFFFF")
            shade(table.rows[0].cells[index], navy)
            if widths_mm:
                table.rows[0].cells[index].width = Mm(widths_mm[index])
        for row_index, row in enumerate(rows):
            cells = table.add_row().cells
            for col_index, value in enumerate(row):
                cell_text(cells[col_index], value)
                if row_index % 2:
                    shade(cells[col_index], pale_gray)
                if widths_mm:
                    cells[col_index].width = Mm(widths_mm[col_index])
        doc.add_paragraph().paragraph_format.space_after = Pt(0)
        return table

    doc = Document()
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(17)
    section.bottom_margin = Mm(17)
    section.left_margin = Mm(17)
    section.right_margin = Mm(17)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(31, 45, 61)
    normal.paragraph_format.space_after = Pt(5)
    for style_name, size in (("Title", 19), ("Heading 1", 14), ("Heading 2", 11)):
        style = doc.styles[style_name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.bold = True

    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("BÁO CÁO THẨM ĐỊNH TÍN DỤNG")
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run(f"Hồ sơ {result.ma_ho_so} | Báo cáo hỗ trợ chuyên viên tín dụng").bold = True
    intro = doc.add_paragraph(
        "Báo cáo tổng hợp dữ kiện, kết quả tính toán Python, cảnh báo và bằng chứng của hồ sơ. "
        "Báo cáo không phê duyệt hoặc từ chối khoản vay. Quyết định cuối cùng thuộc về người có thẩm quyền."
    )
    intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    doc.add_heading("1 Tổng quan hồ sơ", level=1)
    add_table(["Thông tin", "Giá trị"], [[label, value] for label, value in _noi_dung_tong_quan(result)], [58, 118])

    doc.add_heading("2 Chỉ số tín dụng", level=1)
    metric_rows = [[m.ma_chi_so, m.ten, m.hien_thi, m.trang_thai, m.cong_thuc] for m in result.chi_so]
    add_table(["Mã", "Chỉ số", "Kết quả", "Trạng thái", "Công thức"], metric_rows, [20, 36, 25, 35, 60])

    doc.add_heading("3 Cảnh báo rủi ro", level=1)
    risk_rows = [
        [r.ma_rui_ro, NHAN_RUI_RO.get(r.loai, r.loai), NHAN_MUC_DO[r.muc_do], r.chenh_lech or "-", r.giai_thich]
        for r in result.canh_bao
    ]
    if not risk_rows:
        risk_rows = [["-", "Không phát hiện cảnh báo trọng yếu", "THÔNG TIN", "-", "Theo các quy tắc và ngưỡng minh họa hiện tại."]]
    add_table(["Mã", "Loại", "Mức độ", "Chênh lệch", "Giải thích"], risk_rows, [18, 39, 22, 26, 71])

    doc.add_heading("4 Thông tin còn thiếu", level=1)
    for item in result.thong_tin_thieu or ["Không phát hiện hạng mục bắt buộc còn thiếu."]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_heading("5 Câu hỏi cần xác minh", level=1)
    for item in result.cau_hoi_xac_minh:
        doc.add_paragraph(item, style="List Number")

    doc.add_heading("6 Bằng chứng", level=1)
    evidence_rows = [
        [r.ma_rui_ro, e.tai_lieu, e.trang or "Không xác định", e.truong_du_lieu, e.gia_tri]
        for r in result.canh_bao for e in r.bang_chung
    ]
    if evidence_rows:
        add_table(["Rủi ro", "Tài liệu", "Trang", "Trường dữ liệu", "Giá trị"], evidence_rows, [20, 48, 18, 48, 42])
    else:
        doc.add_paragraph("Không có bằng chứng rủi ro được tạo.")

    doc.add_heading("7 Dữ kiện đã trích xuất", level=1)
    extracted_rows = [
        [
            f.nhan,
            gia_tri_truong_hien_thi(f),
            f.tai_lieu_nguon,
            f.trang or "-",
            nhan_luu_y_tin_cay(
                f.do_tin_cay,
                missing=f.gia_tri is None,
                low_confidence_threshold=low_confidence_threshold,
            ),
        ]
        for f in result.truong_trich_xuat
    ]
    add_table(["Trường", "Giá trị", "Nguồn", "Trang", "Lưu ý"], extracted_rows, [46, 44, 45, 15, 26])

    if ai_summary.strip():
        doc.add_heading("8 Diễn giải bổ sung bằng AI", level=1)
        for line in _xoa_markdown(ai_summary).splitlines():
            if line.strip():
                doc.add_paragraph(line.strip())

    doc.add_heading("Trạng thái xem xét của con người", level=1)
    final_paragraph = doc.add_paragraph()
    final_paragraph.add_run(NHAN_TRANG_THAI[result.trang_thai]).bold = True
    final_paragraph.add_run(". Chuyên viên tín dụng phải xác minh dữ kiện, xử lý mâu thuẫn và chịu trách nhiệm về quyết định cuối cùng.")

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer.add_run("CreditLens | Dữ liệu demo hoặc đã ẩn danh | Không phải quyết định tín dụng")
    footer_run.font.name = "Arial"
    footer_run.font.size = Pt(8)
    footer_run.font.color.rgb = RGBColor(95, 107, 122)

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def tao_bao_cao_excel(
    result: KetQuaThamDinh,
    ai_summary: str = "",
    low_confidence_threshold: float | None = None,
) -> bytes:
    """Tạo workbook XLSX nhiều sheet với giá trị số giữ nguyên kiểu dữ liệu."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    navy = "123B5D"
    blue = "2B7BBB"
    cyan = "19BFD3"
    pale = "EAF6FF"
    pale_alt = "F7FAFD"
    border_color = "D5E2EE"
    thin = Side(style="thin", color=border_color)

    wb = Workbook()
    wb.remove(wb.active)

    def title(ws, text: str, last_col: int) -> None:
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)
        cell = ws.cell(1, 1, text)
        cell.font = Font(name="Aptos Display", size=18, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=navy)
        cell.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[1].height = 30

    def header(ws, row: int, values: list[str]) -> None:
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row, col, value)
            cell.font = Font(name="Aptos", bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor=blue)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
        ws.row_dimensions[row].height = 24

    def body_style(ws, min_row: int, max_row: int, max_col: int) -> None:
        for row in range(min_row, max_row + 1):
            for col in range(1, max_col + 1):
                cell = ws.cell(row, col)
                cell.font = Font(name="Aptos", size=10, color="1F2D3D")
                cell.fill = PatternFill("solid", fgColor=pale_alt if row % 2 else "FFFFFF")
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)

    def set_widths(ws, widths: list[float]) -> None:
        for idx, width in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(idx)].width = width

    ws = wb.create_sheet("Tong quan")
    title(ws, "BÁO CÁO THẨM ĐỊNH TÍN DỤNG", 2)
    ws["A3"] = "Lưu ý"
    ws["B3"] = "Báo cáo hỗ trợ chuyên viên tín dụng. Không phê duyệt hoặc từ chối khoản vay."
    for cell in ws[3]:
        cell.fill = PatternFill("solid", fgColor=pale)
        cell.font = Font(name="Aptos", bold=cell.column == 1, color="123B5D")
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
    header(ws, 5, ["Thông tin", "Giá trị"])
    for row_index, (label, value) in enumerate(_noi_dung_tong_quan(result), start=6):
        ws.cell(row_index, 1, label)
        ws.cell(row_index, 2, value)
    body_style(ws, 6, 5 + len(_noi_dung_tong_quan(result)), 2)
    set_widths(ws, [34, 78])
    ws.freeze_panes = "A6"

    ws = wb.create_sheet("Chi so")
    title(ws, "CHỈ SỐ TÍN DỤNG", 7)
    header(ws, 3, ["Mã", "Chỉ số", "Giá trị số", "Hiển thị", "Công thức", "Trạng thái", "Ghi chú"])
    for row_index, metric in enumerate(result.chi_so, start=4):
        values = [metric.ma_chi_so, metric.ten, metric.gia_tri, metric.hien_thi, metric.cong_thuc, metric.trang_thai, metric.ghi_chu]
        for col_index, value in enumerate(values, start=1):
            ws.cell(row_index, col_index, value)
        if metric.ma_chi_so in {"dti", "dsr", "chenh_lech_thu_nhap", "bien_dong_thu_nhap"}:
            ws.cell(row_index, 3).number_format = "0.0%"
        elif metric.ma_chi_so == "thu_nhap_kha_dung":
            ws.cell(row_index, 3).number_format = "#,##0\" VND\""
        elif metric.ma_chi_so == "he_so_dem_so_du":
            ws.cell(row_index, 3).number_format = "0.00x"
    body_style(ws, 4, 3 + len(result.chi_so), 7)
    set_widths(ws, [20, 27, 16, 16, 48, 24, 48])
    ws.freeze_panes = "A4"
    ws.auto_filter.ref = f"A3:G{3 + len(result.chi_so)}"

    ws = wb.create_sheet("Canh bao")
    title(ws, "CẢNH BÁO RỦI RO", 6)
    header(ws, 3, ["Mã rủi ro", "Loại", "Mức độ", "Chênh lệch", "Giải thích", "Số bằng chứng"])
    risks = result.canh_bao or [CanhBaoRuiRo(ma_rui_ro="-", loai="Không phát hiện cảnh báo trọng yếu", muc_do="INFO", giai_thich="Theo các quy tắc và ngưỡng minh họa hiện tại.")]
    for row_index, risk in enumerate(risks, start=4):
        values = [risk.ma_rui_ro, NHAN_RUI_RO.get(risk.loai, risk.loai), NHAN_MUC_DO[risk.muc_do], risk.chenh_lech or "-", risk.giai_thich, len(risk.bang_chung)]
        for col_index, value in enumerate(values, start=1):
            ws.cell(row_index, col_index, value)
    body_style(ws, 4, 3 + len(risks), 6)
    set_widths(ws, [15, 34, 15, 18, 78, 16])
    ws.freeze_panes = "A4"
    ws.auto_filter.ref = f"A3:F{3 + len(risks)}"

    ws = wb.create_sheet("Bang chung")
    title(ws, "BẰNG CHỨNG CẢNH BÁO", 7)
    header(ws, 3, ["Mã rủi ro", "Loại rủi ro", "Tài liệu", "Trang", "Trường dữ liệu", "Giá trị", "Trích đoạn"])
    evidence_rows = [
        [risk.ma_rui_ro, NHAN_RUI_RO.get(risk.loai, risk.loai), evidence.tai_lieu, evidence.trang, evidence.truong_du_lieu, evidence.gia_tri, evidence.trich_doan or ""]
        for risk in result.canh_bao for evidence in risk.bang_chung
    ]
    for row_index, row in enumerate(evidence_rows, start=4):
        for col_index, value in enumerate(row, start=1):
            ws.cell(row_index, col_index, value)
    if evidence_rows:
        body_style(ws, 4, 3 + len(evidence_rows), 7)
        ws.auto_filter.ref = f"A3:G{3 + len(evidence_rows)}"
    set_widths(ws, [15, 32, 40, 10, 36, 25, 72])
    ws.freeze_panes = "A4"

    ws = wb.create_sheet("Trich xuat")
    title(ws, "DỮ KIỆN ĐÃ TRÍCH XUẤT", 7)
    header(ws, 3, ["Mã trường", "Trường dữ liệu", "Giá trị", "Tài liệu nguồn", "Trang", "Lưu ý", "Trích đoạn bằng chứng"])
    for row_index, field in enumerate(result.truong_trich_xuat, start=4):
        raw_value: Any = field.gia_tri
        note = nhan_luu_y_tin_cay(
            field.do_tin_cay,
            missing=field.gia_tri is None,
            low_confidence_threshold=low_confidence_threshold,
        )
        values = [field.ma_truong, field.nhan, raw_value, field.tai_lieu_nguon, field.trang, note, field.bang_chung.trich_doan if field.bang_chung else ""]
        for col_index, value in enumerate(values, start=1):
            ws.cell(row_index, col_index, value)
        if isinstance(raw_value, (int, float)) and field.ma_truong not in {"tham_nien_lam_viec_thang", "thoi_han_vay_thang", "bien_dong_thu_nhap"}:
            ws.cell(row_index, 3).number_format = "#,##0\" VND\""
        elif field.ma_truong == "bien_dong_thu_nhap" and isinstance(raw_value, (int, float)):
            ws.cell(row_index, 3).number_format = "0.0%"
    body_style(ws, 4, 3 + len(result.truong_trich_xuat), 7)
    for row_index in range(4, 4 + len(result.truong_trich_xuat)):
        note_cell = ws.cell(row_index, 6)
        note_text = str(note_cell.value or "")
        if note_text.startswith("Tin cậy cao"):
            note_cell.fill = PatternFill("solid", fgColor="DCFCE7")
            note_cell.font = Font(name="Aptos", size=10, bold=True, color="15803D")
        elif note_text.startswith("Cần đối chiếu"):
            note_cell.fill = PatternFill("solid", fgColor="FEF3C7")
            note_cell.font = Font(name="Aptos", size=10, bold=True, color="A75605")
        elif "xác minh" in note_text.lower() or "không đọc được" in note_text.lower():
            note_cell.fill = PatternFill("solid", fgColor="FEE2E2")
            note_cell.font = Font(name="Aptos", size=10, bold=True, color="B91C1C")
        else:
            note_cell.fill = PatternFill("solid", fgColor="E2E8F0")
            note_cell.font = Font(name="Aptos", size=10, bold=True, color="596579")
    set_widths(ws, [28, 42, 24, 42, 10, 24, 72])
    ws.freeze_panes = "A4"
    ws.auto_filter.ref = f"A3:G{3 + len(result.truong_trich_xuat)}"

    ws = wb.create_sheet("Can xac minh")
    title(ws, "THÔNG TIN THIẾU VÀ CÂU HỎI XÁC MINH", 3)
    header(ws, 3, ["Nhóm", "STT", "Nội dung"])
    review_rows = [["Thông tin còn thiếu", index, item] for index, item in enumerate(result.thong_tin_thieu, 1)]
    review_rows += [["Câu hỏi xác minh", index, item] for index, item in enumerate(result.cau_hoi_xac_minh, 1)]
    if not result.thong_tin_thieu:
        review_rows.insert(0, ["Thông tin còn thiếu", 1, "Không phát hiện hạng mục bắt buộc còn thiếu."])
    for row_index, row in enumerate(review_rows, start=4):
        for col_index, value in enumerate(row, start=1):
            ws.cell(row_index, col_index, value)
    body_style(ws, 4, 3 + len(review_rows), 3)
    set_widths(ws, [28, 10, 105])
    ws.freeze_panes = "A4"

    if ai_summary.strip():
        ws = wb.create_sheet("Dien giai AI")
        title(ws, "DIỄN GIẢI BỔ SUNG BẰNG AI", 1)
        for row_index, line in enumerate(_xoa_markdown(ai_summary).splitlines(), start=3):
            ws.cell(row_index, 1, line)
            ws.cell(row_index, 1).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row_index, 1).font = Font(name="Aptos", size=10, color="1F2D3D")
        set_widths(ws, [120])

    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.oddFooter.center.text = "CreditLens - Không phải quyết định tín dụng"
        ws.oddFooter.center.size = 8
        ws.oddFooter.center.color = "5F6B7A"

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def _tim_font_pdf() -> tuple[str, str] | None:
    """Tìm cặp font TrueType có đủ ký tự tiếng Việt.

    Streamlit Community Cloud có thể đặt font ở các thư mục khác nhau tùy image
    hệ điều hành. Danh sách ưu tiên Noto Sans và DejaVu Sans; Liberation Sans là
    phương án dự phòng. ``packages.txt`` cài cả Noto và DejaVu để PDF không phụ
    thuộc font mặc định (Helvetica không hỗ trợ đầy đủ Unicode tiếng Việt).
    """
    custom_dir = os.environ.get("CREDITLENS_FONT_DIR", "").strip()
    candidates = [
        (str(Path(custom_dir) / "NotoSans-Regular.ttf"), str(Path(custom_dir) / "NotoSans-Bold.ttf")) if custom_dir else ("", ""),
        ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        ("/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/opentype/noto/NotoSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/local/share/fonts/DejaVuSans.ttf", "/usr/local/share/fonts/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ]
    for regular, bold in candidates:
        if Path(regular).is_file() and Path(bold).is_file():
            return regular, bold
    return None


def tao_bao_cao_pdf(
    result: KetQuaThamDinh,
    ai_summary: str = "",
    low_confidence_threshold: float | None = None,
) -> bytes:
    """Tạo PDF Unicode trong bộ nhớ bằng ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import KeepTogether, LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    fonts = _tim_font_pdf()
    if fonts is None:
        raise RuntimeError("Không tìm thấy font Unicode để tạo PDF tiếng Việt. Hãy cài gói fonts-dejavu-core.")
    regular_path, bold_path = fonts
    if "CreditLensSans" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("CreditLensSans", regular_path))
        pdfmetrics.registerFont(TTFont("CreditLensSans-Bold", bold_path))

    navy = colors.HexColor("#123B5D")
    blue = colors.HexColor("#2B7BBB")
    pale = colors.HexColor("#EAF6FF")
    pale_alt = colors.HexColor("#F7FAFD")
    border = colors.HexColor("#D5E2EE")
    ink = colors.HexColor("#1F2D3D")
    muted = colors.HexColor("#5F6B7A")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CreditTitle", parent=styles["Title"], fontName="CreditLensSans-Bold", fontSize=18, leading=22, textColor=colors.black, alignment=TA_CENTER, spaceAfter=8)
    subtitle_style = ParagraphStyle("CreditSubtitle", parent=styles["Normal"], fontName="CreditLensSans", fontSize=9, leading=12, textColor=muted, alignment=TA_CENTER, spaceAfter=10)
    heading_style = ParagraphStyle("CreditHeading", parent=styles["Heading1"], fontName="CreditLensSans-Bold", fontSize=12, leading=15, textColor=colors.black, spaceBefore=8, spaceAfter=5)
    body_style = ParagraphStyle("CreditBody", parent=styles["BodyText"], fontName="CreditLensSans", fontSize=8.5, leading=11.5, textColor=ink, spaceAfter=4)
    small_style = ParagraphStyle("CreditSmall", parent=body_style, fontSize=7.5, leading=10)
    header_style = ParagraphStyle("CreditTableHeader", parent=small_style, fontName="CreditLensSans-Bold", textColor=colors.white)

    def clean(value: Any) -> str:
        text = str(value if value is not None else "-")
        # Giữ nguyên dấu tiếng Việt và các ký hiệu tài chính; font Noto/DejaVu
        # đã được nhúng trực tiếp vào PDF.
        return html.escape(text)

    def para(value: Any, style=body_style) -> Paragraph:
        return Paragraph(clean(value), style)

    def table(headers: list[str], rows: list[list[Any]], widths_mm: list[float]):
        content = [[para(h, header_style) for h in headers]] + [[para(value, small_style) for value in row] for row in rows]
        output_table = LongTable(content, colWidths=[w * mm for w in widths_mm], repeatRows=1, hAlign="LEFT")
        output_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, border),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, pale_alt]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return output_table

    output = io.BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=18 * mm, bottomMargin=17 * mm, title=f"Báo cáo thẩm định {result.ma_ho_so}",
        author="CreditLens",
    )
    story: list[Any] = [
        Paragraph("BÁO CÁO THẨM ĐỊNH TÍN DỤNG", title_style),
        Paragraph(clean(f"Hồ sơ {result.ma_ho_so} - Báo cáo hỗ trợ chuyên viên tín dụng"), subtitle_style),
        para(
            "Báo cáo tổng hợp dữ kiện, kết quả tính toán Python, cảnh báo và bằng chứng của hồ sơ. "
            "Báo cáo không phê duyệt hoặc từ chối khoản vay. Quyết định cuối cùng thuộc về người có thẩm quyền."
        ),
        Paragraph("1 Tổng quan hồ sơ", heading_style),
        table(["Thông tin", "Giá trị"], [[label, value] for label, value in _noi_dung_tong_quan(result)], [57, 125]),
        Paragraph("2 Chỉ số tín dụng", heading_style),
        table(
            ["Chỉ số", "Kết quả", "Trạng thái", "Công thức"],
            [[m.ten, m.hien_thi, m.trang_thai, m.cong_thuc] for m in result.chi_so],
            [38, 25, 38, 81],
        ),
        Paragraph("3 Cảnh báo rủi ro", heading_style),
    ]
    if result.canh_bao:
        for risk in result.canh_bao:
            risk_block: list[Any] = [
                para(
                    f"{risk.ma_rui_ro} - {NHAN_RUI_RO.get(risk.loai, risk.loai)} - {NHAN_MUC_DO[risk.muc_do]}",
                    ParagraphStyle(
                        f"RiskTitle-{risk.ma_rui_ro}",
                        parent=body_style,
                        fontName="CreditLensSans-Bold",
                        textColor=navy,
                        spaceBefore=4,
                    ),
                ),
                para(risk.giai_thich),
            ]
            for evidence in risk.bang_chung:
                risk_block.append(
                    para(
                        f"Bằng chứng: {evidence.tai_lieu}, trang {evidence.trang or 'không xác định'}, "
                        f"{evidence.truong_du_lieu} = {evidence.gia_tri}",
                        small_style,
                    )
                )
            # Giữ tiêu đề, giải thích và ít nhất một bằng chứng cùng trang.
            # Các bằng chứng còn lại được phép ngắt trang để tránh tạo một trang
            # cuối gần như trống khi khối cảnh báo dài.
            story.append(KeepTogether(risk_block[:3]))
            story.extend(risk_block[3:])
    else:
        story.append(para("Không phát hiện mâu thuẫn trọng yếu theo các quy tắc minh họa hiện tại."))

    story += [Paragraph("4 Thông tin còn thiếu", heading_style)]
    for item in result.thong_tin_thieu or ["Không phát hiện hạng mục bắt buộc còn thiếu."]:
        story.append(para(f"- {item}"))
    story.append(Paragraph("5 Câu hỏi cần xác minh", heading_style))
    for index, item in enumerate(result.cau_hoi_xac_minh, 1):
        story.append(para(f"{index}. {item}"))
    story += [
        Paragraph("6 Dữ kiện đã trích xuất", heading_style),
        table(
            ["Trường", "Giá trị", "Nguồn", "Trang", "Lưu ý"],
            [
                [
                    f.nhan,
                    gia_tri_truong_hien_thi(f),
                    f.tai_lieu_nguon,
                    f.trang or "-",
                    nhan_luu_y_tin_cay(
                        f.do_tin_cay,
                        missing=f.gia_tri is None,
                        low_confidence_threshold=low_confidence_threshold,
                    ),
                ]
                for f in result.truong_trich_xuat
            ],
            [46, 45, 46, 15, 30],
        ),
    ]
    if ai_summary.strip():
        story.append(Paragraph("7 Diễn giải bổ sung bằng AI", heading_style))
        for line in _xoa_markdown(ai_summary).splitlines():
            if line.strip():
                story.append(para(line.strip()))
    story.append(
        KeepTogether(
            [
                Paragraph("Trạng thái xem xét của con người", heading_style),
                para(
                    f"{NHAN_TRANG_THAI[result.trang_thai]}. Chuyên viên tín dụng phải xác minh dữ kiện, "
                    "xử lý mâu thuẫn và chịu trách nhiệm về quyết định cuối cùng."
                ),
            ]
        )
    )

    def decorate(canvas, doc) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(navy)
        canvas.rect(0, height - 9 * mm, width, 9 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("CreditLensSans-Bold", 7.5)
        canvas.drawString(14 * mm, height - 5.8 * mm, "CREDITLENS")
        canvas.setFont("CreditLensSans", 7.2)
        canvas.drawRightString(width - 14 * mm, height - 5.8 * mm, clean(result.ma_ho_so).replace("&amp;", "&"))
        canvas.setStrokeColor(border)
        canvas.line(14 * mm, 12 * mm, width - 14 * mm, 12 * mm)
        canvas.setFillColor(muted)
        canvas.setFont("CreditLensSans", 6.8)
        canvas.drawString(14 * mm, 7.5 * mm, "Không phải quyết định tín dụng - Bắt buộc con người xem xét")
        canvas.drawRightString(width - 14 * mm, 7.5 * mm, f"Trang {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return output.getvalue()


DINH_DANG_BAO_CAO = {
    "Word (.docx)": ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", tao_bao_cao_word),
    "Excel (.xlsx)": ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", tao_bao_cao_excel),
    "PDF (.pdf)": ("pdf", "application/pdf", tao_bao_cao_pdf),
}


def render_outputs(result: KetQuaThamDinh, docs: dict[str, TaiLieu]):
    status_icon = {"REVIEW READY": "🟢", "HUMAN REVIEW REQUIRED": "🟡", "INSUFFICIENT INFORMATION": "⚪"}[result.trang_thai]
    status_md = f"""### {status_icon} {NHAN_TRANG_THAI[result.trang_thai]}
**Hồ sơ:** `{result.ma_ho_so}` · **{len(result.truong_trich_xuat)}** trường · **{len(result.canh_bao)}** cảnh báo · **{result.thoi_gian_xu_ly_ms} ms**

> Kết quả chỉ hỗ trợ thẩm định. Không phải quyết định phê duyệt hoặc từ chối.
"""
    doc_rows = [[doc.ten_tep, NHAN_LOAI_TAI_LIEU[doc.loai_ky_vong], NHAN_LOAI_TAI_LIEU.get(doc.loai_nhan_dien, "Chưa xác định"), doc.so_trang, doc.trang_thai, f"{doc.do_tin_cay * 100:.0f}%"] for doc in docs.values()]
    field_rows = []
    for f in result.truong_trich_xuat:
        if isinstance(f.gia_tri, (int, float)):
            display = phan_tram(float(f.gia_tri)) if f.ma_truong == "bien_dong_thu_nhap" else (f"{float(f.gia_tri):.0f} tháng" if f.ma_truong in {"tham_nien_lam_viec_thang", "thoi_han_vay_thang"} else tien(f.gia_tri))
        else:
            display = f.gia_tri or "Không tìm thấy"
        field_rows.append([f.ma_truong, f.nhan, display, f.tai_lieu_nguon, f.trang or "—", f"{f.do_tin_cay * 100:.0f}%"])
    metric_rows = [[m.ten, m.hien_thi, m.cong_thuc, m.trang_thai, m.ghi_chu] for m in result.chi_so]
    risk_rows = [[r.ma_rui_ro, NHAN_RUI_RO.get(r.loai, r.loai), NHAN_MUC_DO[r.muc_do], r.giai_thich, len(r.bang_chung)] for r in result.canh_bao]
    if not risk_rows:
        risk_rows = [["—", "Không phát hiện cảnh báo trọng yếu", "THÔNG TIN", "Theo các quy tắc và ngưỡng minh họa hiện tại.", 0]]
    evidence_parts = []
    for risk in result.canh_bao:
        evidence_parts.append(f"### {risk.ma_rui_ro} — {NHAN_RUI_RO.get(risk.loai, risk.loai)}")
        evidence_parts.append(risk.giai_thich)
        if risk.bang_chung:
            for evidence in risk.bang_chung:
                evidence_parts.append(f"- **{evidence.tai_lieu} · Trang {evidence.trang or 'không xác định'}:** {evidence.truong_du_lieu} = `{evidence.gia_tri}`")
        else:
            evidence_parts.append("- Thông tin chưa đủ — không có bằng chứng hỗ trợ.")
    evidence_md = "\n".join(evidence_parts) or "Không có cảnh báo cần hiển thị bằng chứng."
    summary_md = bao_cao_markdown(result)

    temp_dir = Path(tempfile.mkdtemp(prefix="creditlens_"))
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", result.ma_ho_so)[:80] or "CASE"
    md_path = temp_dir / f"{safe_id}_tom_tat_tham_dinh.md"
    json_path = temp_dir / f"{safe_id}_ket_qua_co_cau_truc.json"
    md_path.write_text(summary_md, encoding="utf-8")
    json_path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    return status_md, doc_rows, field_rows, metric_rows, risk_rows, evidence_md, summary_md, str(md_path), str(json_path)


# ==========================================================
# 9. STREAMLIT WEB + CÀI ĐẶT AI AN TOÀN
# ==========================================================

DEFAULT_SYSTEM_PROMPT = """Bạn là trợ lý hỗ trợ cán bộ thẩm định tín dụng.
Chỉ sử dụng dữ kiện, phép tính, kết quả quy tắc và bằng chứng trong JSON đầu vào.
Không được bịa dữ liệu còn thiếu. Không được thay đổi kết quả do Python tính.
Mọi nhận định rủi ro phải chỉ ra bằng chứng hỗ trợ. Nếu chưa đủ bằng chứng, ghi rõ
“Thông tin chưa đủ”. Tách rõ DỮ KIỆN và DIỄN GIẢI. Không tạo chính sách ngân hàng,
lãi suất hoặc ngưỡng pháp lý. Không phê duyệt, từ chối hoặc khuyến nghị quyết định
tín dụng. Kết thúc bằng trạng thái cần con người xem xét. Viết bằng tiếng Việt."""

NHA_CUNG_CAP_LLM = {
    "openai": {
        "nhan": "OpenAI · GPT",
        "mo_ta": "GPT và các model suy luận được cấp cho OpenAI API Key",
        "placeholder": "sk-proj-… hoặc sk-…",
    },
    "gemini": {
        "nhan": "Google · Gemini",
        "mo_ta": "Các model Gemini hỗ trợ generateContent",
        "placeholder": "AIza…",
    },
    "anthropic": {
        "nhan": "Anthropic · Claude",
        "mo_ta": "Các model Claude được Anthropic API Key cho phép",
        "placeholder": "sk-ant-…",
    },
    "deepseek": {
        "nhan": "DeepSeek",
        "mo_ta": "Các model chat/reasoner được DeepSeek API Key cho phép",
        "placeholder": "sk-…",
    },
}

TU_DONG_NHAN_DIEN = "Tự động nhận diện an toàn"
LUA_CHON_NHA_CUNG_CAP = [TU_DONG_NHAN_DIEN] + [item["nhan"] for item in NHA_CUNG_CAP_LLM.values()]
MA_NHA_CUNG_CAP_THEO_NHAN = {item["nhan"]: key for key, item in NHA_CUNG_CAP_LLM.items()}

DEFAULT_SETTINGS = {
    "ten_ung_dung": "CreditLens — Trợ lý thẩm định tín dụng",
    "mau_chu_dao": "#203469",
    "mau_nhan": "#A71B28",
    "che_do_giao_dien": "Theo hệ thống",
    "llm_provider": "openai",
    "model": "gpt-5-mini",
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "nguong": dict(NGUONG),
}

CHE_DO_GIAO_DIEN = ("Theo hệ thống", "Sáng", "Tối", "Ấm áp", "Hiện đại")

THEME_PALETTES = {
    "Theo hệ thống": {
        "page": "#F5F7FB", "page_alt": "#E9EDF6", "surface": "rgba(255,255,255,.96)",
        "surface_solid": "#FFFFFF", "text": "#14213D", "muted": "#5C667A",
        "border": "rgba(32,52,105,.18)", "sidebar_top": "#FFFFFF", "sidebar_bottom": "#E8EDF7",
    },
    "Sáng": {
        "page": "#F8F9FC", "page_alt": "#EEF1F7", "surface": "rgba(255,255,255,.98)",
        "surface_solid": "#FFFFFF", "text": "#14213D", "muted": "#626C80",
        "border": "rgba(32,52,105,.16)", "sidebar_top": "#FFFFFF", "sidebar_bottom": "#EEF1F8",
    },
    "Tối": {
        "page": "#081226", "page_alt": "#101D39", "surface": "rgba(16,29,57,.96)",
        "surface_solid": "#142342", "text": "#F5F7FC", "muted": "#B7C0D4",
        "border": "rgba(185,196,221,.22)", "sidebar_top": "#0A1530", "sidebar_bottom": "#111E3B",
    },
    "Ấm áp": {
        "page": "#FBF7F4", "page_alt": "#F3EAE7", "surface": "rgba(255,253,251,.97)",
        "surface_solid": "#FFFDFC", "text": "#2C2430", "muted": "#74636A",
        "border": "rgba(167,27,40,.18)", "sidebar_top": "#FFFDFC", "sidebar_bottom": "#F6ECEA",
    },
    "Hiện đại": {
        "page": "#F2F5FA", "page_alt": "#E4EAF5", "surface": "rgba(255,255,255,.91)",
        "surface_solid": "#FFFFFF", "text": "#15213C", "muted": "#5B667C",
        "border": "rgba(32,52,105,.20)", "sidebar_top": "#FFFFFF", "sidebar_bottom": "#E6EBF5",
    },
}

THEME_ACCENTS = {
    "Theo hệ thống": ("#203469", "#A71B28"),
    "Sáng": ("#203469", "#A71B28"),
    "Tối": ("#9CB4F0", "#FF7180"),
    "Ấm áp": ("#203469", "#A71B28"),
}

PAGES = [
    "Trang chủ & hồ sơ",
    "Trích xuất tài liệu",
    "Phân tích tín dụng",
    "Cảnh báo rủi ro",
    "Tóm tắt thẩm định",
    "Đánh giá & phương pháp",
    "Evaluation",
    "Cài đặt",
]

NHAN_DIEU_HUONG = {
    "Trang chủ & hồ sơ": "⌂  Tổng quan và hồ sơ",
    "Trích xuất tài liệu": "▦  Trích xuất tài liệu",
    "Phân tích tín dụng": "◈  Phân tích tín dụng",
    "Cảnh báo rủi ro": "△  Cảnh báo rủi ro",
    "Tóm tắt thẩm định": "≡  Tóm tắt thẩm định",
    "Đánh giá & phương pháp": "◎  Phương pháp và giới hạn",
    "Evaluation": "▤  Evaluation",
    "Cài đặt": "⚙  Cài đặt",
}

PROJECT_ROOT = Path(__file__).resolve().parent
LOGO_PATH = PROJECT_ROOT / "static" / "hub-creditlens-lockup.png"
LOGO_ICON_PATH = PROJECT_ROOT / "static" / "hub-favicon.png"
CREDITLENS_LOGO_PATH = PROJECT_ROOT / "static" / "creditlens-logo-hub.png"
WATERMARK_PATH = PROJECT_ROOT / "static" / "creditlens-watermark.png"


def anh_data_uri(path: Path) -> str:
    """Nhúng tài sản thương hiệu cục bộ, không phụ thuộc hotlink bên ngoài."""
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def anh_nen_data_uri(path: Path) -> str:
    """Đổi tài sản thương hiệu thành CSS background-image ổn định trên cloud."""
    data_uri = anh_data_uri(path)
    return f'url("{data_uri}")' if data_uri else "none"

STREAMLIT_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
  :root {
    --credit-primary: PRIMARY_COLOR;
    --credit-accent: ACCENT_COLOR;
    --credit-page: PAGE_COLOR;
    --credit-page-alt: PAGE_ALT_COLOR;
    --credit-surface: SURFACE_COLOR;
    --credit-surface-solid: SURFACE_SOLID_COLOR;
    --credit-text: TEXT_COLOR;
    --credit-muted: MUTED_COLOR;
    --credit-border: BORDER_COLOR;
    --credit-sidebar-top: SIDEBAR_TOP_COLOR;
    --credit-sidebar-bottom: SIDEBAR_BOTTOM_COLOR;
    --credit-metric-ok: METRIC_OK_COLOR;
    --credit-metric-warn: METRIC_WARN_COLOR;
    --credit-metric-missing: METRIC_MISSING_COLOR;
    --credit-radius: 16px;
    --credit-control-radius: 8px;
    --credit-shadow: 0 10px 28px rgba(20, 39, 84, .075);
    --credit-focus: 0 0 0 3px color-mix(in srgb, var(--credit-primary) 28%, transparent);
    --credit-success: #15803D;
    --credit-warning: #B45309;
    --credit-danger: #B91C1C;
    --credit-info: #1D4ED8;
    --credit-grid: color-mix(in srgb, var(--credit-primary) 4%, transparent);
    --credit-ambient-blue: color-mix(in srgb, var(--credit-primary) 7%, transparent);
    --credit-ambient-red: color-mix(in srgb, var(--credit-accent) 5%, transparent);
  }
  * { box-sizing: border-box; }
  html, body, .stApp {
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
    font-size: 15px;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
  }
  html { scroll-behavior: smooth; }
  .stApp, [data-testid="stAppViewContainer"] {
    color: var(--credit-text);
    background:
      linear-gradient(var(--credit-grid) 1px, transparent 1px),
      linear-gradient(90deg, var(--credit-grid) 1px, transparent 1px),
      linear-gradient(180deg, var(--credit-page) 0%, var(--credit-page-alt) 100%);
    background-size: 48px 48px, 48px 48px, 100% 100%;
    background-attachment: fixed;
  }
  [data-testid="stAppViewContainer"]::before {
    content: ""; position: fixed; z-index: 0; pointer-events: none;
    width: min(46vw, 680px); height: min(46vw, 680px); right: 4vw; top: 19vh;
    background-image: WATERMARK_IMAGE; background-repeat: no-repeat;
    background-size: contain; background-position: center;
    opacity: .035; filter: saturate(.86); transform: rotate(-6deg);
  }
  [data-testid="stAppViewContainer"]::after {
    content: ""; position: fixed; z-index: 0; pointer-events: none; inset: -10%;
    background:
      radial-gradient(circle at 12% 12%, var(--credit-ambient-blue), transparent 29rem),
      radial-gradient(circle at 86% 15%, var(--credit-ambient-red), transparent 27rem),
      radial-gradient(circle at 62% 88%, color-mix(in srgb, var(--credit-primary) 4%, transparent), transparent 31rem);
    opacity: .84; transform: translate3d(-.6%, -.4%, 0) scale(1.01);
    animation: credit-ambient-drift 22s ease-in-out infinite alternate;
    will-change: transform, opacity;
  }
  [data-testid="stHeader"] { background: transparent; }
  .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label,
  .stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stMarkdownContainer"] {
    color: var(--credit-text);
  }
  .stApp h1 { font-size: clamp(1.75rem, 2.6vw, 2rem); line-height: 1.18; font-weight: 780; letter-spacing: -.025em; }
  .stApp h2 { font-size: clamp(1.35rem, 2vw, 1.5rem); line-height: 1.24; font-weight: 720; letter-spacing: -.018em; }
  .stApp h3 { font-size: 1.08rem; line-height: 1.32; font-weight: 680; letter-spacing: -.008em; }
  .stApp h4 { font-size: .95rem; line-height: 1.38; font-weight: 650; }
  .stApp p, .stApp label, .stApp li { line-height: 1.55; }
  .stApp [data-testid="stCaptionContainer"] { color: var(--credit-muted); font-size: .78rem; line-height: 1.45; }
  .block-container {
    position: relative; z-index: 1; max-width: 1440px;
    padding: 1.35rem clamp(1rem, 2.2vw, 2rem) 2.5rem;
    animation: credit-page-enter .18s cubic-bezier(.22, .85, .35, 1) both;
  }
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--credit-sidebar-top), var(--credit-sidebar-bottom));
    border-right: 1px solid var(--credit-border);
  }
  [data-testid="stSidebarContent"] { padding-top: .85rem; }
  [data-testid="stSidebar"] * { color: var(--credit-text); }
  [data-testid="stSidebar"] [data-testid="stImage"] {
    background: color-mix(in srgb, var(--credit-surface-solid) 94%, transparent);
    border: 1px solid color-mix(in srgb, var(--credit-primary) 18%, transparent); border-radius: 12px;
    padding: 8px 10px; margin: 2px 0 10px; box-shadow: 0 7px 20px rgba(20, 39, 84, .065);
  }
  [data-testid="stSidebar"] [data-testid="stImage"] img {
    display: block; width: 100%; height: auto; max-height: 104px; object-fit: contain; border-radius: 8px;
  }
  [data-testid="stSidebar"] .stRadio label {
    min-height: 40px; border-radius: 8px; padding: 6px 9px; margin: 2px 0;
    transition: transform 140ms cubic-bezier(.2,.8,.2,1), background-color 160ms ease,
      border-color 160ms ease, box-shadow 160ms ease;
  }
  [data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(32,52,105,.09); transform: translateX(3px);
  }
  [data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background: linear-gradient(105deg, #172A59, #203469);
    border-left: 4px solid #A71B28;
    box-shadow: 0 8px 20px rgba(32,52,105,.22); transform: translateX(2px);
  }
  [data-testid="stSidebar"] .stRadio label:has(input:checked) * { color: #FFFFFF !important; font-weight: 760 !important; }
  [data-testid="stSidebar"] .stRadio label:active { transform: translateX(2px) scale(.985); }
  .brand-caption { display: grid; gap: 2px; margin: -5px 2px 12px; }
  .brand-caption strong { color: var(--credit-primary); font-size: .9rem; letter-spacing: .01em; }
  .brand-caption span { color: var(--credit-muted); font-size: .72rem; }
  .sidebar-section-label {
    color: var(--credit-muted); font-size: .69rem; font-weight: 850; letter-spacing: .12em;
    margin: 10px 0 5px; text-transform: uppercase;
  }
  .credit-hero {
    position: relative; overflow: hidden;
    background: linear-gradient(125deg, #142451 0%, #203469 66%, #7D1723 100%);
    color: white; border: 1px solid rgba(255,255,255,.36);
    border-radius: 18px; padding: 21px 25px; margin-bottom: 12px;
    box-shadow: 0 16px 42px rgba(20,39,84,.21), 0 0 24px rgba(167,27,40,.09);
  }
  .credit-hero-inner {
    position: relative; z-index: 1; display: grid; grid-template-columns: minmax(0, 1fr) auto;
    align-items: center; gap: clamp(1rem, 2.4vw, 2rem);
  }
  .credit-hero-copy { min-width: 0; }
  .credit-brand-lockup {
    display: grid; place-items: center; width: clamp(112px, 11vw, 148px);
    padding: 8px 10px; border: 1px solid rgba(255,255,255,.64); border-radius: 12px;
    background: rgba(255,255,255,.95); box-shadow: 0 8px 24px rgba(8,18,38,.18);
  }
  .credit-brand-lockup img { display: block; width: 100%; height: auto; max-height: 84px; object-fit: contain; }
  .credit-hero:after {
    content: ""; position: absolute; width: 280px; height: 280px; right: -80px; top: -120px;
    border: 1px solid rgba(255,255,255,.28); border-radius: 50%;
    box-shadow: 0 0 55px rgba(255,255,255,.18), inset 0 0 40px rgba(255,255,255,.08);
  }
  .credit-kicker { font-size: .72rem; font-weight: 750; letter-spacing: .12em; opacity: .88; margin-bottom: 7px; }
  .credit-hero, .credit-hero h1, .credit-hero p, .credit-hero .credit-kicker, .credit-hero .credit-chip {
    color: #FFFFFF !important;
  }
  .credit-hero h1 { margin: 0 0 7px; font-size: clamp(1.65rem, 2.8vw, 2.05rem); line-height: 1.15; letter-spacing: -.025em; }
  .credit-hero p { margin: 0; max-width: 850px; font-size: .93rem; opacity: .94; }
  .credit-chip {
    display: inline-block; margin-top: 12px; padding: 5px 10px; border-radius: 999px;
    background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.34);
    font-size: .74rem; font-weight: 650; backdrop-filter: blur(6px);
  }
  .credit-notice, .credit-privacy, .status-card, .evidence-card {
    background: var(--credit-surface); color: var(--credit-text); border: 1px solid var(--credit-border);
    border-radius: var(--credit-radius); padding: 15px 17px; margin: 10px 0 18px;
    box-shadow: var(--credit-shadow); backdrop-filter: blur(9px);
  }
  .credit-notice { border-left: 5px solid #D49A26; }
  .credit-privacy { border-left: 5px solid ACCENT_COLOR; }
  .status-card { border-left: 5px solid PRIMARY_COLOR; }
  .public-pill {
    display: inline-flex; align-items: center; gap: 7px; padding: 7px 11px; border-radius: 999px;
    color: #203469; background: #EDF1FA; border: 1px solid rgba(32,52,105,.28);
    font-size: .74rem; font-weight: 820; box-shadow: 0 0 18px rgba(32,52,105,.10);
  }
  .public-dot { width: 8px; height: 8px; border-radius: 50%; background: #A71B28; box-shadow: 0 0 10px rgba(167,27,40,.55); }
  div[data-testid="stMetric"] {
    background: var(--credit-surface);
    border: 1px solid var(--credit-border); border-radius: 12px; padding: 12px 14px;
    box-shadow: var(--credit-shadow);
  }
  [data-testid="stMetricLabel"] { color: var(--credit-muted); font-size: .78rem; font-weight: 600; }
  [data-testid="stMetricValue"], .metric-value, .financial-num {
    font-variant-numeric: tabular-nums lining-nums;
    font-feature-settings: "tnum" 1, "lnum" 1;
  }
  [data-testid="stMetricValue"] { font-size: clamp(1.45rem, 2.4vw, 1.9rem); font-weight: 700; letter-spacing: -.025em; }
  [data-testid="stFileUploaderDropzone"] {
    min-height: 104px; color: var(--credit-text) !important;
    background: var(--credit-surface-solid) !important;
    border: 1.5px dashed color-mix(in srgb, var(--credit-primary) 66%, var(--credit-border)) !important;
    border-radius: 12px !important;
  }
  [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] {
    color: var(--credit-text) !important; background: var(--credit-surface) !important;
    border: 1px solid var(--credit-border) !important; border-radius: var(--credit-control-radius) !important;
  }
  [data-testid="stFileUploaderDropzone"] [data-testid="stMarkdownContainer"] p,
  [data-testid="stFileUploaderDropzone"] [data-testid="stIconMaterial"],
  [data-testid="stFileUploaderDropzone"] small,
  [data-testid="stFileUploaderDropzone"] > div {
    color: var(--credit-text) !important;
  }
  .stTextInput input, .stNumberInput input, .stTextArea textarea,
  [data-testid="stChatInput"] textarea {
    color: var(--credit-text) !important; border-radius: var(--credit-control-radius) !important;
    border-color: var(--credit-border) !important;
    background: var(--credit-surface-solid) !important;
    transition: border-color 160ms ease, box-shadow 160ms ease, background-color 160ms ease;
  }
  [data-testid="stSelectbox"] [role="group"] {
    color: var(--credit-text) !important; background: var(--credit-surface-solid) !important;
    border: 1px solid var(--credit-border) !important; border-radius: var(--credit-control-radius) !important;
    box-shadow: none !important; min-height: 40px;
    transition: border-color 160ms ease, box-shadow 160ms ease, background-color 160ms ease;
  }
  [data-testid="stSelectbox"] input[role="combobox"],
  [data-testid="stSelectbox"] button[aria-label="Open"] {
    color: var(--credit-text) !important; background: transparent !important;
    -webkit-text-fill-color: var(--credit-text) !important;
  }
  [role="listbox"] { color: var(--credit-text) !important; background: var(--credit-surface-solid) !important; }
  [role="option"] { color: var(--credit-text) !important; background: var(--credit-surface-solid) !important; }
  [role="option"][aria-selected="true"], [role="option"]:hover {
    background: rgba(32,52,105,.14) !important;
  }
  [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
  [data-testid="stChatInput"] {
    border-radius: var(--credit-control-radius) !important;
    border-color: var(--credit-border) !important;
    background: var(--credit-surface-solid) !important;
    transition: border-color 160ms ease, box-shadow 160ms ease;
  }
  .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus,
  [data-testid="stChatInput"] textarea:focus,
  [data-testid="stSelectbox"] [role="group"]:focus-within,
  [data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within,
  [data-testid="stChatInput"]:focus-within {
    border-color: var(--credit-primary) !important; box-shadow: var(--credit-focus) !important;
  }
  .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button,
  [data-testid="stLinkButton"] a {
    min-height: 40px; color: var(--credit-text) !important; background: var(--credit-surface-solid) !important;
    border-radius: var(--credit-control-radius) !important; border: 1px solid var(--credit-border) !important;
    box-shadow: 0 2px 7px rgba(20,39,84,.045);
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
    font-size: .84rem; font-weight: 650 !important; letter-spacing: .002em; cursor: pointer;
    transition: background-color 160ms ease, border-color 160ms ease, box-shadow 160ms ease,
      color 160ms ease, transform 140ms cubic-bezier(.2,.8,.2,1) !important;
  }
  .stButton > button:not(:disabled):hover, .stDownloadButton > button:not(:disabled):hover,
  [data-testid="stFormSubmitButton"] button:not(:disabled):hover, [data-testid="stLinkButton"] a:hover {
    transform: translateY(-1px); color: var(--credit-primary) !important;
    background: color-mix(in srgb, var(--credit-primary) 5%, var(--credit-surface-solid)) !important;
    border-color: color-mix(in srgb, var(--credit-primary) 70%, var(--credit-border)) !important;
    box-shadow: 0 7px 18px rgba(20,39,84,.11) !important;
  }
  .stButton > button:not(:disabled):active, .stDownloadButton > button:not(:disabled):active,
  [data-testid="stFormSubmitButton"] button:not(:disabled):active, [data-testid="stLinkButton"] a:active {
    transform: translateY(0) scale(.985) !important; box-shadow: 0 2px 7px rgba(20,39,84,.07) !important;
  }
  .stButton > button:focus-visible, .stDownloadButton > button:focus-visible,
  [data-testid="stFormSubmitButton"] button:focus-visible, [data-testid="stLinkButton"] a:focus-visible,
  input:focus-visible, textarea:focus-visible, [role="combobox"]:focus-visible,
  [role="tab"]:focus-visible, summary:focus-visible {
    outline: 2px solid var(--credit-primary) !important; outline-offset: 2px;
  }
  .stButton > button:disabled, .stDownloadButton > button:disabled,
  [data-testid="stFormSubmitButton"] button:disabled {
    cursor: not-allowed; opacity: .48; transform: none !important; box-shadow: none !important;
    filter: saturate(.55);
  }
  .stButton > button[aria-busy="true"], [data-testid="stFormSubmitButton"] button[aria-busy="true"] {
    cursor: progress; opacity: .72; transform: none !important;
  }
  button[kind="primary"], button[kind="primaryFormSubmit"], .stDownloadButton > button[kind="primary"] {
    color: white !important; border: 0 !important;
    background: linear-gradient(110deg, #203469, #152347) !important;
    box-shadow: 0 7px 18px rgba(32,52,105,.22) !important;
  }
  button[kind="primary"] *, button[kind="primaryFormSubmit"] *, .stDownloadButton > button[kind="primary"] * { color: #FFFFFF !important; }
  button[kind="primary"]:not(:disabled):hover, button[kind="primaryFormSubmit"]:not(:disabled):hover,
  .stDownloadButton > button[kind="primary"]:not(:disabled):hover {
    color: #FFFFFF !important; background: linear-gradient(110deg, #263E7B, #17284F) !important;
    box-shadow: 0 9px 22px rgba(32,52,105,.27) !important;
  }
  button[kind="primary"]:not(:disabled):hover *, button[kind="primaryFormSubmit"]:not(:disabled):hover * { color: #FFFFFF !important; }
  .stApp [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] [data-testid="stMarkdownContainer"] p {
    color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important;
  }
  [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:disabled {
    background: var(--credit-primary) !important;
    border-color: var(--credit-primary) !important;
    opacity: .64;
  }
  [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:disabled * { color: #FFFFFF !important; }
  [data-testid="stExpander"] { background: var(--credit-surface); border: 1px solid var(--credit-border); border-radius: 12px; overflow: hidden; }
  [data-testid="stExpander"] details > summary {
    transition: background-color 160ms ease, color 160ms ease; min-height: 42px;
  }
  [data-testid="stExpander"] details > summary:hover { background: color-mix(in srgb, var(--credit-primary) 5%, transparent); }
  [data-testid="stDataFrame"] {
    background: var(--credit-surface-solid); border: 1px solid var(--credit-border); border-radius: 10px;
    overflow: hidden; box-shadow: 0 6px 18px rgba(20,39,84,.055);
    font-variant-numeric: tabular-nums lining-nums; font-feature-settings: "tnum" 1, "lnum" 1;
  }
  [data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--credit-surface); border-color: var(--credit-border) !important;
    border-radius: var(--credit-radius) !important; box-shadow: 0 8px 24px rgba(20,39,84,.07);
  }
  .credit-upload-panel {
    background: var(--credit-surface); border: 1px solid var(--credit-border); border-radius: var(--credit-radius);
    padding: 16px 18px 5px; margin: 8px 0 16px; box-shadow: 0 8px 24px rgba(20,39,84,.07);
  }
  .credit-process-grid {
    display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 13px; margin: 5px 0 22px;
  }
  .credit-process-card {
    min-height: 142px; background: var(--credit-surface); border: 1px solid var(--credit-border);
    border-radius: 13px; padding: 15px; box-shadow: 0 7px 20px rgba(20,39,84,.055);
  }
  .process-step {
    display: grid; place-items: center; width: 31px; height: 31px; border-radius: 10px;
    color: #FFFFFF; background: linear-gradient(135deg, #203469, #A71B28);
    font-size: .78rem; font-weight: 900; margin-bottom: 11px;
  }
  .process-title { color: var(--credit-text); font-size: .92rem; font-weight: 820; margin-bottom: 5px; }
  .process-copy { color: var(--credit-muted); font-size: .78rem; line-height: 1.48; }
  .credit-metric-grid {
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; margin: 8px 0 20px;
  }
  .credit-metric-card {
    min-height: 218px; display: flex; flex-direction: column; box-sizing: border-box;
    background: var(--credit-surface); border: 1px solid var(--credit-border); border-radius: 13px;
    padding: 17px; box-shadow: var(--credit-shadow);
  }
  .metric-name { color: var(--credit-muted); font-size: .82rem; font-weight: 650; margin-bottom: 7px; }
  .metric-value { color: var(--credit-text); font-size: clamp(1.65rem, 2.6vw, 2.15rem); font-weight: 700; line-height: 1.08; margin-bottom: 11px; letter-spacing: -.025em; }
  .metric-badge { width: fit-content; border-radius: 999px; padding: 5px 10px; font-size: .78rem; font-weight: 800; }
  .metric-ok { color: var(--credit-metric-ok); background: rgba(34,197,94,.14); }
  .metric-warn { color: var(--credit-metric-warn); background: rgba(245,158,11,.17); }
  .metric-missing { color: var(--credit-metric-missing); background: rgba(148,163,184,.18); }
  .metric-formula { color: var(--credit-muted); font-size: .78rem; line-height: 1.45; margin-top: auto; padding-top: 16px; font-weight: 650; }
  .metric-note { color: var(--credit-muted); font-size: .78rem; line-height: 1.45; margin-top: 7px; }
  .confidence-legend {
    display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 14px; color: var(--credit-muted); font-size: .78rem;
  }
  .confidence-legend span { border: 1px solid var(--credit-border); border-radius: 999px; padding: 5px 9px; background: var(--credit-surface); }
  .legend-high { border-left: 4px solid #22C55E !important; }
  .legend-review { border-left: 4px solid #F59E0B !important; }
  .legend-check { border-left: 4px solid #EF4444 !important; }
  .legend-missing { border-left: 4px solid #94A3B8 !important; }
  [data-testid="stTabs"] [role="tablist"] { gap: 8px; border-bottom-color: var(--credit-border); }
  [data-testid="stTabs"] button[role="tab"] {
    min-height: 40px; border-radius: 8px 8px 0 0; padding-inline: 12px; font-size: .84rem; font-weight: 650;
    transition: color .15s ease, background .15s ease, transform .15s ease;
  }
  [data-testid="stTabs"] button[role="tab"]:hover { background: rgba(32,52,105,.07); }
  [data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color: var(--credit-primary) !important; background: rgba(32,52,105,.09); }
  [data-testid="stTabs"] button[role="tab"]:active { transform: scale(.98); }
  [data-testid="stStatusWidget"] { border-radius: var(--credit-radius); border-color: var(--credit-border); background: var(--credit-surface); }
  hr { border-color: rgba(32,52,105,.13) !important; }
  @keyframes credit-page-enter {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes credit-ambient-drift {
    0% { opacity: .72; transform: translate3d(-.6%, -.4%, 0) scale(1.01); }
    50% { opacity: .9; }
    100% { opacity: .78; transform: translate3d(.8%, .6%, 0) scale(1.025); }
  }
  @media (max-width: 1080px) { .credit-process-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 950px) { .credit-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 820px) {
    .block-container { padding-top: 1.1rem; }
    .credit-hero { padding: 18px 20px; }
    .credit-brand-lockup { width: 112px; }
  }
  @media (max-width: 640px) {
    .block-container { padding-inline: 1rem; }
    .credit-hero { padding: 17px 18px; border-radius: 14px; }
    .credit-hero-inner { grid-template-columns: 1fr; gap: 12px; }
    .credit-brand-lockup { width: 100px; padding: 6px 8px; order: -1; }
    .credit-brand-lockup img { max-height: 64px; }
    .credit-process-grid, .credit-metric-grid { grid-template-columns: 1fr; }
    .credit-metric-card { min-height: 198px; }
    [data-testid="stTabs"] [role="tablist"] { overflow-x: auto; }
  }
  @media (prefers-reduced-motion: reduce) {
    html { scroll-behavior: auto; }
    *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
    [data-testid="stAppViewContainer"]::after { animation: none !important; transform: none !important; }
    .block-container,
    .stButton > button:hover, .stDownloadButton > button:hover,
    [data-testid="stFormSubmitButton"] button:hover, [data-testid="stLinkButton"] a:hover,
    [data-testid="stSidebar"] .stRadio label:hover { transform: none !important; }
  }
  SYSTEM_THEME_MEDIA
</style>
"""


def tao_css_giao_dien(settings: dict[str, Any]) -> str:
    mode = settings.get("che_do_giao_dien", "Theo hệ thống")
    if mode not in CHE_DO_GIAO_DIEN:
        mode = "Theo hệ thống"
    palette = THEME_PALETTES[mode]
    primary = lam_sach_mau(settings.get("mau_chu_dao", "#203469"), "#203469")
    accent = lam_sach_mau(settings.get("mau_nhan", "#A71B28"), "#A71B28")
    if mode in THEME_ACCENTS:
        primary, accent = THEME_ACCENTS[mode]

    system_media = ""
    if mode == "Theo hệ thống":
        dark = THEME_PALETTES["Tối"]
        system_media = """@media (prefers-color-scheme: dark) {
          :root {
            --credit-primary: #9CB4F0; --credit-accent: #FF7180;
            --credit-page: DARK_PAGE; --credit-page-alt: DARK_PAGE_ALT;
            --credit-surface: DARK_SURFACE; --credit-surface-solid: DARK_SURFACE_SOLID;
            --credit-text: DARK_TEXT; --credit-muted: DARK_MUTED; --credit-border: DARK_BORDER;
            --credit-sidebar-top: DARK_SIDEBAR_TOP; --credit-sidebar-bottom: DARK_SIDEBAR_BOTTOM;
            --credit-metric-ok: #86EFAC; --credit-metric-warn: #FCD34D;
            --credit-metric-missing: #CBD5E1;
          }
        }"""
        for key in sorted(dark, key=len, reverse=True):
            system_media = system_media.replace(f"DARK_{key.upper()}", dark[key])

    replacements = {
        "PRIMARY_COLOR": primary,
        "ACCENT_COLOR": accent,
        "PAGE_COLOR": palette["page"],
        "PAGE_ALT_COLOR": palette["page_alt"],
        "SURFACE_COLOR": palette["surface"],
        "SURFACE_SOLID_COLOR": palette["surface_solid"],
        "TEXT_COLOR": palette["text"],
        "MUTED_COLOR": palette["muted"],
        "BORDER_COLOR": palette["border"],
        "SIDEBAR_TOP_COLOR": palette["sidebar_top"],
        "SIDEBAR_BOTTOM_COLOR": palette["sidebar_bottom"],
        "METRIC_OK_COLOR": "#86EFAC" if mode == "Tối" else "#15803D",
        "METRIC_WARN_COLOR": "#FCD34D" if mode == "Tối" else "#B45309",
        "METRIC_MISSING_COLOR": "#CBD5E1" if mode == "Tối" else "#64748B",
        "WATERMARK_IMAGE": anh_nen_data_uri(WATERMARK_PATH),
        "SYSTEM_THEME_MEDIA": system_media,
    }
    css = STREAMLIT_CSS
    for token, value in replacements.items():
        css = css.replace(token, value)
    return css


def cau_hinh_mac_dinh() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_SETTINGS, ensure_ascii=False))


def lam_sach_mau(value: str, mac_dinh: str = "#203469") -> str:
    return value.upper() if re.fullmatch(r"#[0-9A-Fa-f]{6}", value or "") else mac_dinh


def lam_sach_ma_ho_so(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "-", (value or "").strip())[:80]
    return cleaned or "CASE-CHUA-XAC-DINH"


def xu_ly_tai_lieu_tai_len(
    ma_ho_so: str,
    uploads: dict[str, Any],
    thresholds: Mapping[str, Any] | None = None,
) -> tuple[KetQuaThamDinh, dict[str, TaiLieu], list[str]]:
    docs: dict[str, TaiLieu] = {}
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="creditlens_upload_") as temp_dir:
        for key, uploaded in uploads.items():
            if uploaded is None:
                continue
            safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(uploaded.name).name)
            path = Path(temp_dir) / f"{key}_{safe_name}"
            path.write_bytes(uploaded.getvalue())
            try:
                docs[key] = doc_pdf(path, key)
                docs[key].ten_tep = Path(uploaded.name).name
            except ValueError as exc:
                errors.append(str(exc))
    if not docs:
        raise ValueError("Không có tài liệu PDF hợp lệ để phân tích.")
    return phan_tich_tai_lieu(lam_sach_ma_ho_so(ma_ho_so), docs, thresholds), docs, errors


def xu_ly_thu_muc_tai_lieu(
    ma_ho_so: str,
    uploaded_files: list[Any],
    thresholds: Mapping[str, Any] | None = None,
) -> tuple[KetQuaThamDinh, dict[str, TaiLieu], list[str]]:
    """Đọc một thư mục gồm 3–4 PDF và tự phân loại từng tài liệu.

    Tên tệp chỉ dùng làm gợi ý; nội dung vẫn được kiểm tra, phân loại và hiển thị
    để chuyên viên đối chiếu. Tệp trùng loại hoặc chưa nhận diện không được gán
    âm thầm sang một schema khác.
    """
    files = [item for item in (uploaded_files or []) if item is not None]
    if not 3 <= len(files) <= 4:
        raise ValueError("Thư mục của một hồ sơ phải chứa 3 hoặc 4 tệp PDF (đơn vay, thu nhập, sao kê và nghĩa vụ nợ tùy chọn).")

    docs: dict[str, TaiLieu] = {}
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="creditlens_folder_") as temp_dir:
        for index, uploaded in enumerate(files, start=1):
            original_name = Path(uploaded.name).name
            safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", original_name)
            path = Path(temp_dir) / f"{index:02d}_{safe_name}"
            path.write_bytes(uploaded.getvalue())
            hinted_type = goi_y_loai_tu_ten_tep(uploaded.name)
            try:
                document = doc_pdf(path, hinted_type or "application")
            except ValueError as exc:
                errors.append(str(exc))
                continue

            assigned_type = hinted_type or document.loai_nhan_dien
            if assigned_type not in {"application", "income", "statement", "debt"}:
                errors.append(f"{original_name}: chưa xác định được loại tài liệu; vui lòng đổi tên rõ nghĩa hoặc tải từng tệp.")
                continue
            if assigned_type in docs:
                errors.append(
                    f"{original_name}: trùng loại {NHAN_LOAI_TAI_LIEU[assigned_type]} với {docs[assigned_type].ten_tep}; "
                    "tệp này chưa được dùng."
                )
                continue

            document.loai_ky_vong = assigned_type
            document.ten_tep = original_name
            docs[assigned_type] = document

    if not docs:
        raise ValueError("Không có tài liệu PDF hợp lệ trong thư mục để phân tích.")
    required_missing = [
        NHAN_LOAI_TAI_LIEU[key]
        for key in ("application", "income", "statement")
        if key not in docs
    ]
    if required_missing:
        errors.append("Chưa nhận diện được tài liệu bắt buộc: " + ", ".join(required_missing) + ".")
    return phan_tich_tai_lieu(lam_sach_ma_ho_so(ma_ho_so), docs, thresholds), docs, errors


def du_lieu_gui_llm(result: KetQuaThamDinh) -> str:
    payload = result.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, indent=2)


def nhan_dien_nha_cung_cap_tu_khoa(api_key: str) -> str | None:
    """Nhận diện provider chỉ khi tiền tố đủ đặc trưng; không gửi thử khóa sang nhiều hãng."""
    key = (api_key or "").strip()
    if key.startswith("sk-ant-"):
        return "anthropic"
    if key.startswith("AIza"):
        return "gemini"
    if key.startswith(("sk-proj-", "sk-svcacct-")):
        return "openai"
    # OpenAI legacy và DeepSeek có thể cùng dùng tiền tố sk-. Không đoán để tránh
    # truyền một khóa bí mật đến nhầm nhà cung cấp.
    return None


def nha_cung_cap_hieu_luc(lua_chon: str, api_key: str) -> str | None:
    if lua_chon == TU_DONG_NHAN_DIEN:
        return nhan_dien_nha_cung_cap_tu_khoa(api_key)
    return MA_NHA_CUNG_CAP_THEO_NHAN.get(lua_chon)


def _model_hop_le(provider: str, model_id: str) -> bool:
    model = model_id.lower()
    if not re.fullmatch(r"[A-Za-z0-9._:-]{2,160}", model_id):
        return False
    if provider == "openai":
        excluded = (
            "embedding", "whisper", "tts", "dall-e", "image", "moderation",
            "transcribe", "audio", "realtime", "sora", "babbage", "davinci",
        )
        return model.startswith(("gpt-", "chatgpt-", "o1", "o3", "o4", "o5", "ft:gpt-")) and not any(
            token in model for token in excluded
        )
    if provider == "gemini":
        return model.startswith("gemini-") and "embedding" not in model
    if provider == "anthropic":
        return model.startswith("claude-")
    if provider == "deepseek":
        return model.startswith("deepseek-")
    return False


def trich_danh_sach_model(provider: str, payload: dict[str, Any]) -> list[str]:
    """Chuẩn hóa response /models của bốn nhà cung cấp về list model ID."""
    if not isinstance(payload, dict):
        return []
    raw_models: list[str] = []
    if provider == "gemini":
        for item in payload.get("models", []):
            if not isinstance(item, dict):
                continue
            methods = item.get("supportedGenerationMethods") or []
            if "generateContent" not in methods:
                continue
            raw_models.append(str(item.get("name", "")).removeprefix("models/"))
    else:
        for item in payload.get("data", []):
            if isinstance(item, dict):
                raw_models.append(str(item.get("id", "")))

    result: list[str] = []
    seen: set[str] = set()
    for model_id in raw_models:
        model_id = model_id.strip()
        if model_id not in seen and _model_hop_le(provider, model_id):
            seen.add(model_id)
            result.append(model_id)
    return result[:120]


def _loi_api_theo_status(provider: str, status_code: int) -> RuntimeError:
    label = NHA_CUNG_CAP_LLM[provider]["nhan"]
    if status_code in {401, 403}:
        message = "API Key không hợp lệ hoặc chưa có quyền truy cập model."
    elif status_code == 429:
        message = "API đang giới hạn tần suất hoặc tài khoản đã hết hạn mức."
    elif status_code >= 500:
        message = "Dịch vụ nhà cung cấp đang tạm thời không sẵn sàng."
    else:
        message = f"API trả về mã lỗi HTTP {status_code}."
    return RuntimeError(f"{label}: {message}")


def lay_danh_sach_model(provider: str, api_key: str) -> list[str]:
    """Xác thực khóa và tải các model text-generation mà chính khóa nhìn thấy."""
    if provider not in NHA_CUNG_CAP_LLM:
        raise ValueError("Nhà cung cấp LLM không được hỗ trợ.")
    key = (api_key or "").strip()
    if len(key) < 12:
        raise ValueError("API Key chưa được nhập hoặc quá ngắn.")
    try:
        import httpx

        headers: dict[str, str] = {"Accept": "application/json"}
        params: dict[str, Any] = {}
        if provider == "openai":
            url = "https://api.openai.com/v1/models"
            headers["Authorization"] = f"Bearer {key}"
        elif provider == "gemini":
            url = "https://generativelanguage.googleapis.com/v1beta/models"
            headers["x-goog-api-key"] = key
            params["pageSize"] = 1000
        elif provider == "anthropic":
            url = "https://api.anthropic.com/v1/models"
            headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
            params["limit"] = 100
        else:
            url = "https://api.deepseek.com/models"
            headers["Authorization"] = f"Bearer {key}"

        with httpx.Client(timeout=18.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers, params=params)
        if response.status_code >= 400:
            raise _loi_api_theo_status(provider, response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError(f"{NHA_CUNG_CAP_LLM[provider]['nhan']}: phản hồi danh sách model không phải JSON hợp lệ.") from exc
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Không thể kết nối {NHA_CUNG_CAP_LLM[provider]['nhan']} ({type(exc).__name__})."
        ) from exc

    models = trich_danh_sach_model(provider, payload)
    if not models:
        raise RuntimeError(
            f"{NHA_CUNG_CAP_LLM[provider]['nhan']}: khóa hợp lệ nhưng không tìm thấy model hội thoại phù hợp."
        )
    return models


def _noi_dung_yeu_cau_llm(result: KetQuaThamDinh) -> str:
    return (
        "Hãy soạn Credit Review Summary theo đúng 10 mục: tổng quan khách hàng, "
        "đề nghị vay, thông tin tài chính đã xác minh, chỉ số, kiểm tra nhất quán, "
        "cảnh báo, thông tin thiếu, câu hỏi xác minh, bằng chứng và trạng thái xem xét.\n\n"
        + du_lieu_gui_llm(result)
    )


def trich_noi_dung_phan_hoi(provider: str, payload: dict[str, Any]) -> str:
    """Chuẩn hóa output text của Gemini, Claude và DeepSeek."""
    if not isinstance(payload, dict):
        return ""
    if provider == "gemini":
        candidates = payload.get("candidates") or []
        parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
        return "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict)).strip()
    if provider == "anthropic":
        blocks = payload.get("content") or []
        return "\n".join(
            str(block.get("text", "")) for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
    if provider == "deepseek":
        choices = payload.get("choices") or []
        return str(((choices[0].get("message") or {}).get("content", "")) if choices else "").strip()
    return ""


def tao_dien_giai_bang_ai(
    result: KetQuaThamDinh,
    api_key: str,
    provider: str,
    model: str,
    system_prompt: str,
) -> str:
    if not api_key or len(api_key.strip()) < 12:
        raise ValueError("API Key chưa được nhập hoặc không hợp lệ.")
    if provider not in NHA_CUNG_CAP_LLM:
        raise ValueError("Nhà cung cấp LLM không được hỗ trợ.")
    if not _model_hop_le(provider, model or ""):
        raise ValueError("Tên model không hợp lệ.")
    key = api_key.strip()
    prompt = system_prompt[:8000]
    user_input = _noi_dung_yeu_cau_llm(result)
    try:
        if provider == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=key)
            response = client.responses.create(
                model=model,
                instructions=prompt,
                input=user_input,
                max_output_tokens=1800,
                store=False,
            )
            output = (response.output_text or "").strip()
        else:
            import httpx

            headers: dict[str, str] = {"Accept": "application/json", "Content-Type": "application/json"}
            if provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                headers["x-goog-api-key"] = key
                body = {
                    "system_instruction": {"parts": [{"text": prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_input}]}],
                    "generationConfig": {"maxOutputTokens": 1800},
                }
            elif provider == "anthropic":
                url = "https://api.anthropic.com/v1/messages"
                headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
                body = {
                    "model": model,
                    "max_tokens": 1800,
                    "system": prompt,
                    "messages": [{"role": "user", "content": user_input}],
                }
            else:
                url = "https://api.deepseek.com/chat/completions"
                headers["Authorization"] = f"Bearer {key}"
                body = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_input},
                    ],
                    "max_tokens": 1800,
                    "stream": False,
                }

            with httpx.Client(timeout=60.0, follow_redirects=True) as http_client:
                http_response = http_client.post(url, headers=headers, json=body)
            if http_response.status_code >= 400:
                raise _loi_api_theo_status(provider, http_response.status_code)
            try:
                payload = http_response.json()
            except ValueError as exc:
                raise RuntimeError(
                    f"{NHA_CUNG_CAP_LLM[provider]['nhan']}: phản hồi diễn giải không phải JSON hợp lệ."
                ) from exc

            output = trich_noi_dung_phan_hoi(provider, payload)
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Không thể gọi {NHA_CUNG_CAP_LLM[provider]['nhan']} ({type(exc).__name__}). "
            "Hãy kiểm tra API Key, model, hạn mức và kết nối mạng."
        ) from exc
    if not output:
        raise RuntimeError("API không trả về nội dung.")
    prohibited = [
        r"khuyến nghị\s+(phê duyệt|từ chối)",
        r"nên\s+(phê duyệt|từ chối)",
        r"quyết định\s*:\s*(approve|reject|phê duyệt|từ chối)",
    ]
    if any(re.search(pattern, output, re.IGNORECASE) for pattern in prohibited):
        raise RuntimeError("Đầu ra AI chứa khuyến nghị quyết định tín dụng nên đã bị chặn. Hãy siết lại system prompt.")
    provider_label = NHA_CUNG_CAP_LLM[provider]["nhan"]
    return (
        output
        + f"\n\n---\n**Mô hình diễn giải:** {provider_label} · `{model}`  "
        + "\n**Bắt buộc con người xem xét. Nội dung AI không phải quyết định tín dụng.**"
    )


def chuan_hoa_lich_su_chat(messages: Any) -> list[dict[str, str]]:
    """Chỉ giữ các lượt hội thoại hợp lệ trước khi gửi đến provider."""
    if not isinstance(messages, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            normalized.append({"role": role, "content": content})
    return normalized


def _ghi_log_loi_chat_an_toan(exc: Exception, provider: str, model: str, api_key: str) -> None:
    """Ghi lỗi provider/model để chẩn đoán mà không ghi prompt hoặc API Key."""
    message = str(exc)
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    message = re.sub(r"(?i)bearer\s+[A-Za-z0-9._-]+", "Bearer [REDACTED]", message)
    status_code = getattr(exc, "status_code", None)
    CHAT_LOGGER.error(
        "CHAT_API_ERROR provider=%s model=%s exception=%s status=%s message=%s",
        provider,
        model,
        type(exc).__name__,
        status_code if status_code is not None else "n/a",
        message[:1200],
    )


def tao_phan_hoi_chat_ai(
    messages: list[dict[str, str]],
    api_key: str,
    provider: str,
    model: str,
) -> str:
    """Gửi đúng một request chat đến provider/model đang hoạt động."""
    key = (api_key or "").strip()
    if len(key) < 12:
        raise ValueError("API Key chưa được nhập hoặc không hợp lệ.")
    if provider not in NHA_CUNG_CAP_LLM:
        raise ValueError("Nhà cung cấp LLM không được hỗ trợ.")
    if not _model_hop_le(provider, model or ""):
        raise ValueError("Tên model không hợp lệ.")
    history = chuan_hoa_lich_su_chat(messages)
    if not history or history[-1]["role"] != "user":
        raise ValueError("Tin nhắn người dùng đang trống hoặc không hợp lệ.")

    try:
        if provider == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=key)
            response = client.responses.create(
                model=model,
                input=history,
                max_output_tokens=1800,
                store=False,
            )
            output = (response.output_text or "").strip()
        else:
            import httpx

            headers: dict[str, str] = {"Accept": "application/json", "Content-Type": "application/json"}
            if provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                headers["x-goog-api-key"] = key
                body = {
                    "contents": [
                        {
                            "role": "model" if message["role"] == "assistant" else "user",
                            "parts": [{"text": message["content"]}],
                        }
                        for message in history
                    ],
                    "generationConfig": {"maxOutputTokens": 1800},
                }
            elif provider == "anthropic":
                url = "https://api.anthropic.com/v1/messages"
                headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
                body = {"model": model, "max_tokens": 1800, "messages": history}
            else:
                url = "https://api.deepseek.com/chat/completions"
                headers["Authorization"] = f"Bearer {key}"
                body = {"model": model, "messages": history, "max_tokens": 1800, "stream": False}

            with httpx.Client(timeout=60.0, follow_redirects=True) as http_client:
                http_response = http_client.post(url, headers=headers, json=body)
            if http_response.status_code >= 400:
                raise _loi_api_theo_status(provider, http_response.status_code)
            try:
                payload = http_response.json()
            except ValueError as exc:
                raise RuntimeError(
                    f"{NHA_CUNG_CAP_LLM[provider]['nhan']}: phản hồi chat không phải JSON hợp lệ."
                ) from exc
            output = trich_noi_dung_phan_hoi(provider, payload)
    except (ValueError, RuntimeError) as exc:
        _ghi_log_loi_chat_an_toan(exc, provider, model, key)
        raise
    except Exception as exc:
        _ghi_log_loi_chat_an_toan(exc, provider, model, key)
        raise RuntimeError(
            f"Không thể gọi {NHA_CUNG_CAP_LLM[provider]['nhan']} ({type(exc).__name__}). "
            "Hãy kiểm tra API Key, model, hạn mức và kết nối mạng."
        ) from exc
    if not output:
        exc = RuntimeError("API không trả về nội dung.")
        _ghi_log_loi_chat_an_toan(exc, provider, model, key)
        raise exc
    return output


def hien_thi_header(st, settings: dict[str, Any]) -> None:
    st.markdown(tao_css_giao_dien(settings), unsafe_allow_html=True)
    title = html.escape(str(settings["ten_ung_dung"])[:90])
    logo_data_uri = anh_data_uri(LOGO_PATH)
    logo_html = (
        "<div class='credit-brand-lockup' aria-label='Logo chính thức HUB và CreditLens'>"
        f"<img src='{logo_data_uri}' alt='HUB × CreditLens' decoding='async'></div>"
        if logo_data_uri
        else ""
    )
    st.markdown(
        "<div class='credit-hero'><div class='credit-hero-inner'>"
        "<div class='credit-hero-copy'>"
        "<div class='credit-kicker'>HUB × CREDITLENS · AI CREDIT UNDERWRITING COPILOT</div>"
        f"<h1>{title}</h1><p>Dữ kiện → Phép tính Python → Quy tắc → Bằng chứng → Con người xem xét</p>"
        "<span class='credit-chip'>Minh bạch nguồn số · Phản hồi tức thời · Human-in-the-loop</span>"
        f"</div>{logo_html}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='credit-notice'><b>Ứng dụng này chỉ hỗ trợ thẩm định tín dụng.</b> "
        "Hệ thống không phê duyệt hoặc từ chối khoản vay. Quyết định cuối cùng bắt buộc do con người xem xét.</div>",
        unsafe_allow_html=True,
    )


def hien_thi_trang_thai(st, result: KetQuaThamDinh | None) -> None:
    if result is None:
        st.info("Chưa có kết quả. Hãy tải PDF hoặc mở một hồ sơ minh họa.")
        return
    icon = {"REVIEW READY": "🟢", "HUMAN REVIEW REQUIRED": "🟡", "INSUFFICIENT INFORMATION": "⚪"}[result.trang_thai]
    st.markdown(
        f"<div class='status-card'><b>{icon} {NHAN_TRANG_THAI[result.trang_thai]}</b><br>"
        f"Hồ sơ: <code>{result.ma_ho_so}</code> · {len(result.truong_trich_xuat)} trường · "
        f"{len(result.canh_bao)} cảnh báo · {result.thoi_gian_xu_ly_ms} ms</div>",
        unsafe_allow_html=True,
    )


def nhan_luu_y_tin_cay(
    confidence: float,
    *,
    missing: bool = False,
    unreadable: bool = False,
    type_mismatch: bool = False,
    low_confidence_threshold: float | None = None,
) -> str:
    """Đổi điểm confidence thành chỉ dẫn hành động dễ hiểu."""
    if unreadable:
        return "Không đọc được — cần xử lý"
    if missing:
        return "Thiếu dữ liệu"
    if type_mismatch:
        return "Sai lệch loại — cần xác minh"
    threshold = NGUONG["do_tin_cay_thap"] if low_confidence_threshold is None else low_confidence_threshold
    if confidence < threshold:
        return "Cần xác minh"
    if confidence >= 0.90:
        return "Tin cậy cao"
    return "Cần đối chiếu"


def kieu_o_luu_y(value: Any) -> str:
    text = str(value)
    base = "font-weight:700; border-radius:8px;"
    if text.startswith("Tin cậy cao"):
        return base + "background-color:#DCFCE7;color:#14532D;"
    if text.startswith("Cần đối chiếu"):
        return base + "background-color:#FEF3C7;color:#78350F;"
    if "cần xác minh" in text.lower() or "không đọc được" in text.lower():
        return base + "background-color:#FEE2E2;color:#7F1D1D;"
    return base + "background-color:#E2E8F0;color:#334155;"


def hien_thi_bang_luu_y(st, rows: list[dict[str, Any]], *, height: int | None = None) -> None:
    import pandas as pd

    frame = pd.DataFrame(rows)
    styled = frame.style.map(kieu_o_luu_y, subset=["Lưu ý"]) if "Lưu ý" in frame.columns else frame.style
    kwargs: dict[str, Any] = {"width": "stretch", "hide_index": True}
    if height is not None:
        kwargs["height"] = height
    st.dataframe(styled, **kwargs)


def hien_thi_chu_giai_tin_cay(st) -> None:
    st.markdown(
        "<div class='confidence-legend' aria-label='Chú giải mức tin cậy'>"
        "<span class='legend-high'>Xanh · Tin cậy cao</span>"
        "<span class='legend-review'>Vàng · Cần đối chiếu</span>"
        "<span class='legend-check'>Đỏ · Cần xác minh</span>"
        "<span class='legend-missing'>Xám · Thiếu dữ liệu</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def hien_thi_luoi_chi_so(st, metrics: list[ChiSoTinDung]) -> None:
    cards: list[str] = []
    for metric in metrics:
        if metric.trang_thai == "Trong ngưỡng minh họa":
            badge_class, prefix = "metric-ok", "✓"
        elif metric.trang_thai == "Cần chú ý":
            badge_class, prefix = "metric-warn", "!"
        else:
            badge_class, prefix = "metric-missing", "·"
        cards.append(
            "<article class='credit-metric-card'>"
            f"<div class='metric-name'>{html.escape(metric.ten)}</div>"
            f"<div class='metric-value'>{html.escape(metric.hien_thi)}</div>"
            f"<div class='metric-badge {badge_class}'>{prefix} {html.escape(metric.trang_thai)}</div>"
            f"<div class='metric-formula'>{html.escape(metric.cong_thuc)}</div>"
            f"<div class='metric-note'>{html.escape(metric.ghi_chu)}</div>"
            "</article>"
        )
    st.markdown("<div class='credit-metric-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def trang_ho_so(st, thresholds: Mapping[str, Any]) -> None:
    st.header("Tạo hồ sơ thẩm định mới")
    st.markdown(
        "<div class='credit-process-grid' aria-label='Quy trình CreditLens'>"
        "<article class='credit-process-card'><div class='process-step'>01</div>"
        "<div class='process-title'>Tiếp nhận và chuẩn hóa</div>"
        "<div class='process-copy'>Kiểm tra PDF, phân loại tài liệu và gắn từng dữ kiện với nguồn.</div></article>"
        "<article class='credit-process-card'><div class='process-step'>02</div>"
        "<div class='process-title'>Tính toán xác định</div>"
        "<div class='process-copy'>Python tính các chỉ số; dữ liệu thiếu không được tự suy diễn.</div></article>"
        "<article class='credit-process-card'><div class='process-step'>03</div>"
        "<div class='process-title'>Đối chiếu bằng chứng</div>"
        "<div class='process-copy'>Mỗi cảnh báo liên kết trở lại tài liệu, trang và giá trị liên quan.</div></article>"
        "<article class='credit-process-card'><div class='process-step'>04</div>"
        "<div class='process-title'>Con người xem xét</div>"
        "<div class='process-copy'>Chuyên viên xác minh, diễn giải và xuất báo cáo; hệ thống không ra quyết định.</div></article>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='credit-privacy'><b>Hệ thống minh họa.</b> Không tải lên thông tin ngân hàng thật hoặc dữ liệu mật. "
        "Tệp tạm được xóa ngay sau khi đọc; kết quả chỉ giữ trong phiên Streamlit.</div>",
        unsafe_allow_html=True,
    )
    case_id = st.text_input("Mã hồ sơ", value=f"CASE-{datetime.now():%Y%m%d}-01", max_chars=80)
    upload_mode = st.radio(
        "Cách tải hồ sơ",
        ["Tải từng tài liệu", "Tải một thư mục"],
        horizontal=True,
        key="credit_upload_mode",
        help="Chế độ thư mục dành cho 3–4 PDF của cùng một khách hàng, không phải nhiều khách hàng.",
    )
    application = income = statement = debt = None
    folder_files: list[Any] = []
    with st.container(border=True):
        if upload_mode == "Tải từng tài liệu":
            st.caption("Tải riêng từng tài liệu. Ba tài liệu đầu là bắt buộc để hồ sơ đầy đủ.")
            cols = st.columns(4)
            application = cols[0].file_uploader("Đơn đề nghị vay vốn", type=["pdf"], key="application_pdf")
            income = cols[1].file_uploader("Chứng từ thu nhập", type=["pdf"], key="income_pdf")
            statement = cols[2].file_uploader("Sao kê ngân hàng", type=["pdf"], key="statement_pdf")
            debt = cols[3].file_uploader("Nghĩa vụ nợ · tùy chọn", type=["pdf"], key="debt_pdf")
        else:
            st.caption(
                "Chọn một thư mục chứa 3–4 PDF của cùng hồ sơ. Hệ thống tự phân loại đơn vay, chứng từ thu nhập, "
                "sao kê và nghĩa vụ nợ dựa trên tên tệp + nội dung."
            )
            folder_files = st.file_uploader(
                "Thư mục hồ sơ PDF",
                type=["pdf"],
                accept_multiple_files="directory",
                key="credit_folder_pdfs",
                help="Khuyến nghị đặt tên rõ nghĩa, ví dụ 01_Don_de_nghi_vay.pdf, 02_Chung_tu_thu_nhap.pdf.",
            ) or []
            if folder_files:
                st.caption(f"Đã chọn {len(folder_files)} tệp PDF. Chỉ dữ liệu trong phiên hiện tại được sử dụng.")
    if st.button("Chạy quy trình thẩm định", type="primary", width="stretch"):
        no_files = not folder_files if upload_mode == "Tải một thư mục" else not any([application, income, statement, debt])
        if no_files:
            st.error("Hãy tải lên ít nhất một PDF hoặc chọn hồ sơ minh họa.")
        else:
            try:
                with st.status("Đang xử lý hồ sơ", expanded=True) as process_status:
                    st.write("Kiểm tra định dạng, dung lượng và phân loại tài liệu…")
                    if upload_mode == "Tải một thư mục":
                        result, docs, errors = xu_ly_thu_muc_tai_lieu(case_id, folder_files, thresholds)
                    else:
                        result, docs, errors = xu_ly_tai_lieu_tai_len(
                            case_id,
                            {"application": application, "income": income, "statement": statement, "debt": debt},
                            thresholds,
                        )
                    st.write("Chuẩn hóa dữ kiện, tính chỉ số và liên kết cảnh báo với bằng chứng…")
                    process_status.update(label="Đã hoàn tất quy trình thẩm định", state="complete", expanded=False)
                st.session_state.result = result
                st.session_state.docs = docs
                st.session_state.ai_summary = ""
                st.session_state.ai_summary_context = {}
                if errors:
                    st.warning("Một số tệp không xử lý được: " + " · ".join(errors))
                st.success("Đã hoàn tất. Các trang phân tích và bằng chứng đã sẵn sàng.")
            except ValueError as exc:
                st.error(str(exc))

    st.divider()
    st.subheader("Hồ sơ tổng hợp minh họa")
    demo_choice = st.selectbox("Chọn tình huống", list(DEMO_CASES), index=2)
    if st.button("Mở hồ sơ minh họa", width="stretch"):
        result, docs = du_lieu_demo(demo_choice, thresholds)
        st.session_state.result = result
        st.session_state.docs = docs
        st.session_state.ai_summary = ""
        st.session_state.ai_summary_context = {}
        st.success(f"Đã mở {demo_choice}.")
    hien_thi_trang_thai(st, st.session_state.result)


def trang_trich_xuat(
    st,
    result: KetQuaThamDinh | None,
    docs: dict[str, TaiLieu],
    thresholds: Mapping[str, Any],
) -> None:
    st.header("Trích xuất tài liệu")
    if result is None:
        st.warning("Chưa có hồ sơ để hiển thị.")
        return
    hien_thi_chu_giai_tin_cay(st)
    if docs:
        st.subheader("Danh mục tài liệu")
        document_rows = []
        for doc in docs.values():
            mismatch = doc.loai_nhan_dien not in {"unknown", doc.loai_ky_vong}
            document_rows.append(
                {
                    "Tài liệu": doc.ten_tep,
                    "Loại dự kiến": NHAN_LOAI_TAI_LIEU[doc.loai_ky_vong],
                    "Loại nhận diện": NHAN_LOAI_TAI_LIEU.get(doc.loai_nhan_dien, "Chưa xác định"),
                    "Số trang": doc.so_trang,
                    "Trạng thái": doc.trang_thai,
                    "Lưu ý": nhan_luu_y_tin_cay(
                        doc.do_tin_cay,
                        unreadable=doc.trang_thai == "Không đọc được",
                        type_mismatch=mismatch,
                        low_confidence_threshold=float(thresholds["do_tin_cay_thap"]),
                    ),
                }
            )
        hien_thi_bang_luu_y(st, document_rows)
    st.subheader("Dữ kiện đã chuẩn hóa")
    rows = []
    for field in result.truong_trich_xuat:
        display = gia_tri_truong_hien_thi(field)
        rows.append(
            {
                "Trường dữ liệu": field.nhan,
                "Giá trị": display,
                "Nguồn": field.tai_lieu_nguon,
                "Trang": field.trang or "—",
                "Lưu ý": nhan_luu_y_tin_cay(
                    field.do_tin_cay,
                    missing=field.gia_tri is None,
                    low_confidence_threshold=float(thresholds["do_tin_cay_thap"]),
                ),
            }
        )
    hien_thi_bang_luu_y(st, rows, height=485)
    low = [
        field.nhan
        for field in result.truong_trich_xuat
        if field.gia_tri is not None and field.do_tin_cay < float(thresholds["do_tin_cay_thap"])
    ]
    if low:
        st.warning("Các trường cần con người xác nhận: " + ", ".join(low))


def trang_phan_tich(st, result: KetQuaThamDinh | None, thresholds: Mapping[str, Any]) -> None:
    st.header("Phân tích tín dụng bằng Python")
    if result is None:
        st.warning("Chưa có hồ sơ để phân tích.")
        return
    income_col, source_col = st.columns([1, 2])
    income_col.metric("Thu nhập dùng để tính", tien(result.thu_nhap_dung_de_tinh))
    source_status = (
        "Đã có nguồn đối chiếu độc lập"
        if result.thu_nhap_duoc_xac_minh_doc_lap
        else "Chỉ kê khai - cần xác minh"
    )
    source_col.metric("Trạng thái nguồn", source_status)
    st.caption(f"Cơ sở lựa chọn: {result.nguon_thu_nhap_dung_de_tinh}.")
    hien_thi_luoi_chi_so(st, result.chi_so)
    st.info(
        f"Ngưỡng minh họa: chênh lệch thu nhập > {phan_tram(float(thresholds['chenh_lech_thu_nhap']))}; "
        f"DTI > {phan_tram(float(thresholds['dti_canh_bao']))}; "
        f"DSR > {phan_tram(float(thresholds['dsr_canh_bao']))}; "
        f"hệ số đệm số dư < {so_thap_phan(float(thresholds['he_so_dem_so_du_thap']))}×. "
        "Không phải chính sách ngân hàng."
    )


def trang_rui_ro(st, result: KetQuaThamDinh | None) -> None:
    st.header("Cảnh báo rủi ro và bằng chứng")
    if result is None:
        st.warning("Chưa có hồ sơ để kiểm tra.")
        return
    hien_thi_trang_thai(st, result)
    if not result.canh_bao:
        st.success("Không phát hiện mâu thuẫn trọng yếu theo các quy tắc minh họa hiện tại.")
        return
    for risk in result.canh_bao:
        with st.expander(f"{risk.ma_rui_ro} · {NHAN_RUI_RO.get(risk.loai, risk.loai)} · {NHAN_MUC_DO[risk.muc_do]}"):
            st.write(risk.giai_thich)
            if risk.bang_chung:
                st.dataframe(
                    [{"Tài liệu": e.tai_lieu, "Trang": e.trang or "Không xác định", "Trường": e.truong_du_lieu, "Giá trị": e.gia_tri, "Trích đoạn": e.trich_doan or "—"} for e in risk.bang_chung],
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.warning("Thông tin chưa đủ — không có bằng chứng hỗ trợ.")


def trang_tom_tat(st, result: KetQuaThamDinh | None, settings: dict[str, Any]) -> None:
    st.header("Tóm tắt thẩm định tín dụng")
    if result is None:
        st.warning("Chưa có hồ sơ để tạo báo cáo.")
        return
    deterministic = bao_cao_markdown(result)
    st.markdown(deterministic)
    connection = ket_noi_llm_dang_dung(st)
    ai_text = tom_tat_ai_hieu_luc(st, connection, result.ma_ho_so, settings["system_prompt"])

    st.divider()
    st.subheader("Xuất báo cáo hồ sơ")
    st.caption("Chuyên viên chọn một trong ba định dạng. Báo cáo được tạo trong bộ nhớ và không lưu lâu dài trên máy chủ.")
    if _tim_font_pdf():
        st.success("PDF Unicode tiếng Việt đã sẵn sàng (font được nhúng vào tệp).", icon="✅")
    else:
        st.error("Máy chủ chưa tìm thấy font Unicode. PDF tạm thời chưa thể tạo; Word và Excel vẫn hoạt động.")
    selected_format = st.radio(
        "Định dạng báo cáo",
        list(DINH_DANG_BAO_CAO),
        horizontal=True,
        key="report_format",
    )
    extension, mime_type, generator = DINH_DANG_BAO_CAO[selected_format]
    try:
        report_bytes = generator(
            result,
            ai_text,
            float(nguong_hieu_luc(settings.get("nguong"))["do_tin_cay_thap"]),
        )
        file_name = f"{lam_sach_ma_ho_so(result.ma_ho_so)}_bao_cao_tham_dinh.{extension}"
        st.download_button(
            f"Tải báo cáo {selected_format}",
            data=report_bytes,
            file_name=file_name,
            mime=mime_type,
            type="primary",
            width="stretch",
        )
        if ai_text:
            st.caption("Bản tải xuống có kèm diễn giải AI đã tạo trong phiên. Các số liệu vẫn lấy từ kết quả Python.")
    except Exception as exc:
        st.error(f"Không thể tạo báo cáo {selected_format}: {type(exc).__name__}. {exc}")

    with st.expander("Dữ liệu kỹ thuật dành cho kiểm thử"):
        col1, col2 = st.columns(2)
        col1.download_button("Tải Markdown", deterministic, file_name=f"{result.ma_ho_so}_tom_tat_tham_dinh.md", mime="text/markdown", width="stretch")
        col2.download_button("Tải JSON có cấu trúc", json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), file_name=f"{result.ma_ho_so}_ket_qua.json", mime="application/json", width="stretch")

    st.divider()
    st.subheader("Diễn giải bổ sung bằng LLM")
    st.caption("LLM chỉ nhận dữ liệu có cấu trúc và kết quả Python; không nhận toàn bộ PDF và không được thay đổi phép tính.")
    api_key = connection.get("api_key", "") if connection else ""
    provider = connection.get("provider", "") if connection else ""
    model = connection.get("model", "") if connection else ""
    llm_ready = bool(connection and provider in NHA_CUNG_CAP_LLM and _model_hop_le(provider, model))
    if not connection:
        st.info("Hãy mở Cài đặt → Kết nối AI, xác thực khóa và chọn “API Key sử dụng ngay”.")
    elif llm_ready:
        st.success(f"Đang dùng **{NHA_CUNG_CAP_LLM[provider]['nhan']}** · model **{model}**.")
    else:
        st.warning("Kết nối chưa sẵn sàng. Hãy kiểm tra API Key và model trong Cài đặt.")
    if st.button("Tạo diễn giải bằng AI", type="primary", disabled=not llm_ready, width="stretch"):
        try:
            with st.spinner("Đang tạo diễn giải có căn cứ…"):
                generated_summary = tao_dien_giai_bang_ai(
                    result,
                    api_key,
                    provider,
                    model,
                    settings["system_prompt"],
                )
                st.session_state.ai_summary = generated_summary
                st.session_state.ai_summary_context = ngu_canh_tom_tat_ai(
                    connection,
                    result.ma_ho_so,
                    settings["system_prompt"],
                )
                st.rerun()
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
    current_ai_text = tom_tat_ai_hieu_luc(
        st,
        connection,
        result.ma_ho_so,
        settings["system_prompt"],
    )
    if current_ai_text:
        st.markdown(current_ai_text)


def trang_danh_gia(st) -> None:
    st.header("Đánh giá, phương pháp và giới hạn")
    st.subheader("Ba lớp của thuật toán")
    st.markdown(
        """
1. **DỮ KIỆN:** kiểm tra PDF, đọc lớp văn bản theo trang, phân loại tài liệu, tìm nhãn/bí danh và chuẩn hóa bằng Pydantic. Không điền dữ liệu không tìm thấy.
2. **PHÂN TÍCH XÁC ĐỊNH:** Python tính DTI, DSR, thu nhập khả dụng, hệ số đệm số dư, chênh lệch và biến động thu nhập. Mẫu số bằng 0 hoặc thiếu dữ liệu trả về “Chưa đủ dữ liệu”.
3. **DIỄN GIẢI AI:** LLM chỉ nhận facts + calculations + rules + evidence. Nếu API lỗi, báo cáo xác định vẫn hoạt động.
"""
    )
    st.subheader("Khả năng đọc PDF")
    st.dataframe(
        [
            {"Loại PDF": "PDF số/có lớp văn bản", "Mức hỗ trợ": "Hỗ trợ", "Giới hạn": "Tốt nhất khi nhãn và giá trị có thứ tự đọc rõ ràng"},
            {"Loại PDF": "PDF có bảng", "Mức hỗ trợ": "Một phần", "Giới hạn": "Bảng nhiều cột có thể mất liên kết theo hàng"},
            {"Loại PDF": "PDF quét ảnh", "Mức hỗ trợ": "Chưa đọc nội dung", "Giới hạn": "Cần OCR và xác nhận của con người"},
            {"Loại PDF": "PDF hỗn hợp", "Mức hỗ trợ": "Một phần", "Giới hạn": "Dữ kiện chỉ nằm trong ảnh có thể bị bỏ sót"},
            {"Loại PDF": "PDF có mật khẩu", "Mức hỗ trợ": "Không hỗ trợ", "Giới hạn": "Phải gỡ bảo vệ trước khi tải"},
        ],
        width="stretch",
        hide_index=True,
    )
    st.warning("Giới hạn: chưa tích hợp OCR; bí danh không bao phủ mọi mẫu; bảng phức tạp có thể sai thứ tự; ngưỡng chỉ minh họa; dữ liệu tổng hợp không chứng minh hiệu năng sản xuất; mọi diễn giải AI cần kiểm chứng.")


def trang_evaluation(st, settings: Mapping[str, Any]) -> None:
    """Render the isolated, explicit-run evaluation subsystem."""
    from evaluation.evaluator import report_to_csv, report_to_json, run_evaluation

    def display_rate(value: float | None) -> str:
        return "N/A" if value is None else f"{value * 100:.1f}%"

    st.header("Model / Pipeline Evaluation")
    st.caption(
        "Bộ đánh giá độc lập gồm dữ liệu tổng hợp/ẩn danh. Chỉ chạy khi bấm nút; "
        "không gọi LLM, không xác thực lại kết nối và không thay đổi hồ sơ đang mở."
    )
    if st.button("Run Evaluation", type="primary", width="stretch"):
        connection = ket_noi_llm_dang_dung(st)
        provider = str(connection.get("provider")) if connection else "not-used"
        model = str(connection.get("model")) if connection else "deterministic-saved-output"
        with st.spinner("Đang chạy bộ đánh giá xác định…"):
            st.session_state.evaluation_report = run_evaluation(
                threshold_config=settings.get("nguong"),
                provider=provider,
                model=model,
            )

    report = st.session_state.get("evaluation_report")
    if not isinstance(report, dict):
        st.info("Bấm **Run Evaluation** để tạo báo cáo. Streamlit rerun chỉ hiển thị lại kết quả đã lưu.")
        return

    reproducibility = report["reproducibility"]
    dataset = report["dataset_summary"]
    summary = report["overall_summary"]

    st.subheader("1. Reproducibility")
    st.dataframe(
        [
            {"Thuộc tính": "Run ID", "Giá trị": str(reproducibility["evaluation_run_id"])},
            {"Thuộc tính": "Timestamp (UTC)", "Giá trị": str(reproducibility["timestamp"])},
            {"Thuộc tính": "Dataset version", "Giá trị": str(reproducibility["dataset_version"])},
            {"Thuộc tính": "App version", "Giá trị": str(reproducibility["app_version"])},
            {"Thuộc tính": "Provider / model", "Giá trị": f"{reproducibility['provider']} / {reproducibility['model']}"},
            {"Thuộc tính": "LLM API calls", "Giá trị": str(reproducibility["llm_api_calls"])},
        ],
        hide_index=True,
        width="stretch",
    )
    with st.expander("Threshold config của lần chạy"):
        st.json(reproducibility["threshold_config"])

    st.subheader("2. Dataset summary")
    columns = st.columns(3)
    columns[0].metric("Test cases", dataset["case_count"])
    columns[1].metric("Scenarios", dataset["scenario_count"])
    columns[2].metric("Synthetic / anonymized", dataset["synthetic_case_count"])
    st.caption(dataset["scope_note"])

    st.subheader("3. Extraction metrics")
    st.metric("Overall field accuracy", display_rate(summary["extraction_accuracy"]))
    extraction_rows = []
    for row in report["extraction_metrics"]["by_field"]:
        extraction_rows.append({**row, "accuracy": display_rate(row["accuracy"])})
    st.dataframe(extraction_rows, hide_index=True, width="stretch")
    with st.expander("Numeric/date/text tolerances"):
        st.json(report["extraction_metrics"]["tolerances"])

    st.subheader("4. Risk detection")
    risk = report["risk_detection"]
    risk_columns = st.columns(6)
    for column, label, value in zip(
        risk_columns,
        ("TP", "FP", "FN", "TN", "Precision", "Recall"),
        (risk["tp"], risk["fp"], risk["fn"], risk["tn"], display_rate(risk["precision"]), display_rate(risk["recall"])),
        strict=True,
    ):
        column.metric(label, value)
    st.metric("Risk F1", display_rate(risk["f1"]))
    risk_rows = []
    for row in risk["by_risk"]:
        risk_rows.append(
            {
                **row,
                "precision": display_rate(row["precision"]),
                "recall": display_rate(row["recall"]),
                "f1": display_rate(row["f1"]),
            }
        )
    st.dataframe(risk_rows, hide_index=True, width="stretch")

    st.subheader("5. Status classification")
    status_metrics = report["status_classification"]
    status_columns = st.columns(2)
    status_columns[0].metric("Accuracy", display_rate(status_metrics["accuracy"]))
    status_columns[1].metric("Macro F1", display_rate(status_metrics["macro_f1"]))
    matrix_rows = [
        {"Actual \\ Predicted": actual, **predicted_counts}
        for actual, predicted_counts in status_metrics["confusion_matrix"].items()
    ]
    st.dataframe(matrix_rows, hide_index=True, width="stretch")
    status_rows = []
    for row in status_metrics["by_status"]:
        status_rows.append(
            {
                **row,
                "precision": display_rate(row["precision"]),
                "recall": display_rate(row["recall"]),
                "f1": display_rate(row["f1"]),
            }
        )
    st.dataframe(status_rows, hide_index=True, width="stretch")

    st.subheader("6. LLM grounding (saved outputs, no API)")
    grounding_rows = []
    for name, label in (("structured_grounded", "Structured + evidence"), ("generic_prompt", "Generic prompt")):
        metrics = report["llm_grounding"][name]
        grounding_rows.append(
            {
                "Variant": label,
                "Evidence coverage": display_rate(metrics["evidence_coverage"]),
                "Unsupported claim rate": display_rate(metrics["unsupported_claim_rate"]),
                "Factual consistency": display_rate(metrics["factual_consistency"]),
            }
        )
    st.dataframe(grounding_rows, hide_index=True, width="stretch")

    st.subheader("7. Baselines")
    baseline_a = report["baselines"]["baseline_a"]
    baseline_rows = []
    for key, label in (("current", "Current multi-document pipeline"), ("no_cross_document", "No cross-document checks")):
        values = baseline_a[key]
        baseline_rows.append(
            {
                "Variant": label,
                "Risk precision": display_rate(values["risk_precision"]),
                "Risk recall": display_rate(values["risk_recall"]),
                "Risk F1": display_rate(values["risk_f1"]),
                "Status accuracy": display_rate(values["status_accuracy"]),
                "Status macro F1": display_rate(values["status_macro_f1"]),
            }
        )
    st.dataframe(baseline_rows, hide_index=True, width="stretch")
    st.caption(report["baselines"]["baseline_b"]["note"])

    st.subheader("8. Processing time")
    st.dataframe([report["processing_time"]], hide_index=True, width="stretch")

    st.subheader("9. Failure cases")
    failure_rows = []
    for row in report["failure_cases"]:
        failure_rows.append(
            {
                **row,
                "actual_output": json.dumps(row["actual_output"], ensure_ascii=False)
                if isinstance(row["actual_output"], (dict, list))
                else row["actual_output"],
            }
        )
    st.dataframe(failure_rows, hide_index=True, width="stretch")

    st.subheader("10. Limitations")
    for limitation in report["limitations"]:
        st.markdown(f"- {limitation}")

    st.subheader("11. Overall summary & export")
    st.dataframe(
        [{key: display_rate(value) for key, value in summary.items()}],
        hide_index=True,
        width="stretch",
    )
    download_columns = st.columns(2)
    run_suffix = reproducibility["evaluation_run_id"].split("-")[0]
    download_columns[0].download_button(
        "Tải Evaluation JSON",
        report_to_json(report),
        file_name=f"creditlens_evaluation_{run_suffix}.json",
        mime="application/json",
        width="stretch",
    )
    download_columns[1].download_button(
        "Tải Evaluation CSV",
        report_to_csv(report),
        file_name=f"creditlens_evaluation_{run_suffix}.csv",
        mime="text/csv",
        width="stretch",
    )


def nhap_cau_hinh_json(raw: bytes) -> dict[str, Any]:
    candidate = json.loads(raw.decode("utf-8"))
    if not isinstance(candidate, dict):
        raise ValueError("Tệp cấu hình phải là một JSON object.")
    output = cau_hinh_mac_dinh()
    if isinstance(candidate.get("ten_ung_dung"), str):
        output["ten_ung_dung"] = candidate["ten_ung_dung"][:90]
    if isinstance(candidate.get("mau_chu_dao"), str):
        output["mau_chu_dao"] = lam_sach_mau(candidate["mau_chu_dao"])
    if isinstance(candidate.get("mau_nhan"), str):
        output["mau_nhan"] = lam_sach_mau(candidate["mau_nhan"], "#A71B28")
    if candidate.get("che_do_giao_dien") in CHE_DO_GIAO_DIEN:
        output["che_do_giao_dien"] = candidate["che_do_giao_dien"]
    if candidate.get("llm_provider") in NHA_CUNG_CAP_LLM:
        output["llm_provider"] = candidate["llm_provider"]
    if isinstance(candidate.get("model"), str) and re.fullmatch(r"[A-Za-z0-9._:-]{2,160}", candidate["model"]):
        output["model"] = candidate["model"]
    if isinstance(candidate.get("system_prompt"), str):
        output["system_prompt"] = candidate["system_prompt"][:8000]
    if isinstance(candidate.get("nguong"), dict):
        for key, default in output["nguong"].items():
            value = candidate["nguong"].get(key, default)
            lower, upper = GIOI_HAN_NGUONG[key]
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and lower <= float(value) <= upper
            ):
                output["nguong"][key] = float(value)
    return output


def nhan_ket_noi_llm(provider: str, connection: dict[str, Any]) -> str:
    provider_label = NHA_CUNG_CAP_LLM.get(provider, {}).get("nhan", provider)
    model = str(connection.get("model") or "chưa chọn model")
    return f"{provider_label} · {model}"


def ket_noi_llm_dang_dung(st) -> dict[str, Any] | None:
    connections = st.session_state.get("llm_connections", {})
    provider = st.session_state.get("active_llm_provider", "")
    connection = connections.get(provider) if isinstance(connections, dict) else None
    if not isinstance(connection, dict):
        return None
    if not connection.get("verified") or not connection.get("api_key") or not connection.get("model"):
        return None
    return connection


def ngu_canh_tom_tat_ai(
    connection: Mapping[str, Any],
    case_id: str,
    system_prompt: str = "",
) -> dict[str, str]:
    return {
        "provider": str(connection.get("provider") or ""),
        "model": str(connection.get("model") or ""),
        "fingerprint": str(connection.get("fingerprint") or ""),
        "case_id": str(case_id or ""),
        "prompt_fingerprint": hashlib.sha256(str(system_prompt or "").encode("utf-8")).hexdigest(),
    }


def tom_tat_ai_hieu_luc(
    st,
    connection: Mapping[str, Any] | None,
    case_id: str,
    system_prompt: str = "",
) -> str:
    summary = str(st.session_state.get("ai_summary") or "")
    if not summary:
        return ""
    expected = ngu_canh_tom_tat_ai(connection, case_id, system_prompt) if connection else None
    if st.session_state.get("ai_summary_context") != expected:
        st.session_state.ai_summary = ""
        st.session_state.ai_summary_context = {}
        return ""
    return summary


def xoa_ket_noi_llm(st, provider: str) -> None:
    connections = dict(st.session_state.get("llm_connections", {}))
    removed = connections.pop(provider, None)
    st.session_state.llm_connections = connections
    st.session_state.active_llm_provider = next(iter(connections), "")
    st.session_state.llm_connection_error = ""
    if isinstance(removed, dict) and st.session_state.get("llm_api_key_draft", "").strip() == str(
        removed.get("api_key") or ""
    ).strip():
        st.session_state.llm_api_key_draft = ""
    st.session_state.pop("api_key_session", None)
    if st.session_state.get("ai_summary_context", {}).get("provider") == provider:
        st.session_state.ai_summary = ""
        st.session_state.ai_summary_context = {}
    st.session_state.pop("llm_active_selector", None)
    st.session_state.pop(f"llm_model_selector_{provider}", None)


def hien_thi_chat_ai(st, connection: Mapping[str, Any] | None) -> None:
    """Hiển thị chat nhiều lượt; chỉ gọi inference khi người dùng submit."""
    st.subheader("Trò chuyện với AI")
    messages = chuan_hoa_lich_su_chat(st.session_state.get("llm_chat_messages", []))
    st.session_state.llm_chat_messages = messages

    if connection is None:
        st.info("Vui lòng kết nối API Key trước khi bắt đầu trò chuyện.")
        st.chat_input("Nhập câu hỏi của bạn...", key="llm_chat_prompt", disabled=True)
        return

    provider = str(connection.get("provider") or "")
    model = str(connection.get("model") or "")
    api_key = str(connection.get("api_key") or "")
    if not model:
        st.info("Vui lòng chọn model trước khi bắt đầu trò chuyện.")
        st.chat_input("Nhập câu hỏi của bạn...", key="llm_chat_prompt", disabled=True)
        return

    if not messages:
        with st.chat_message("assistant"):
            st.markdown("Xin chào, tôi có thể hỗ trợ gì cho bạn?")
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    submitted = st.chat_input("Nhập câu hỏi của bạn...", key="llm_chat_prompt")
    prompt = (submitted or "").strip()
    if not prompt:
        return

    messages.append({"role": "user", "content": prompt})
    st.session_state.llm_chat_messages = messages
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Đang tạo phản hồi..."):
                response = tao_phan_hoi_chat_ai(messages, api_key, provider, model)
        except (ValueError, RuntimeError):
            st.error("Không thể nhận phản hồi từ model. Vui lòng kiểm tra kết nối hoặc API Key.")
            return
        st.markdown(response)
    messages.append({"role": "assistant", "content": response})
    st.session_state.llm_chat_messages = messages


def trang_cai_dat(st, settings: dict[str, Any]) -> None:
    st.header("Cài đặt")
    st.caption("Kết nối AI, giao diện, ngưỡng và guardrails chỉ có hiệu lực trong phiên trình duyệt hiện tại.")
    tab_ai, tab_ui, tab_thresholds, tab_guardrails = st.tabs(
        ["Kết nối AI", "Giao diện", "Ngưỡng minh họa", "Guardrails và cấu hình"]
    )

    with tab_ai:
        st.warning(
            "API Key chỉ được giữ trong bộ nhớ của phiên này và chỉ gửi đến nhà cung cấp bạn chọn. "
            "Khóa không được ghi vào source, JSON, báo cáo hoặc log."
        )
        st.subheader("Thêm hoặc thay thế kết nối")
        with st.form("llm_connection_form", clear_on_submit=True):
            provider_choice = st.selectbox(
                "Nhà cung cấp",
                LUA_CHON_NHA_CUNG_CAP,
                key="llm_provider_choice",
                help=(
                    "Tự động chỉ nhận diện tiền tố không mơ hồ. Nếu khóa bắt đầu bằng sk-, hãy chọn rõ OpenAI hoặc "
                    "DeepSeek để hệ thống không thử khóa với sai nhà cung cấp."
                ),
            )
            selected_provider = MA_NHA_CUNG_CAP_THEO_NHAN.get(provider_choice)
            placeholder = (
                NHA_CUNG_CAP_LLM[selected_provider]["placeholder"]
                if selected_provider in NHA_CUNG_CAP_LLM
                else "Dán API Key của OpenAI, Gemini, Claude hoặc DeepSeek"
            )
            api_key_candidate = st.text_input(
                "API Key cần xác thực",
                type="password",
                placeholder=placeholder,
                help="Mỗi nhà cung cấp giữ tối đa một kết nối trong phiên. Xác thực lại sẽ thay thế khóa cũ của cùng nhà cung cấp.",
            )
            verify_connection = st.form_submit_button(
                "Kết nối và tải danh sách model",
                type="primary",
                width="stretch",
                help="Nút gửi rõ ràng giúp xác thực mà không cần dùng tổ hợp phím.",
            )
        if verify_connection:
            normalized_key = api_key_candidate.strip()
            provider = nha_cung_cap_hieu_luc(provider_choice, normalized_key)
            if len(normalized_key) < 12:
                st.session_state.llm_connection_error = "API Key chưa được nhập hoặc quá ngắn."
            elif provider is None:
                st.session_state.llm_connection_error = (
                    "Không thể nhận diện an toàn khóa này. Hãy chọn rõ nhà cung cấp rồi thử lại."
                )
            else:
                try:
                    with st.status(f"Đang xác thực {NHA_CUNG_CAP_LLM[provider]['nhan']}", expanded=True) as status:
                        st.write("Kiểm tra khóa trực tiếp với nhà cung cấp đã chọn…")
                        models = lay_danh_sach_model(provider, normalized_key)
                        st.write(f"Đã tải {len(models)} model hội thoại khả dụng.")
                        status.update(label="Kết nối đã được xác minh", state="complete", expanded=False)
                    previous = st.session_state.llm_connections.get(provider, {})
                    preferred_model = previous.get("model") if previous.get("model") in models else models[0]
                    connections = dict(st.session_state.llm_connections)
                    connections[provider] = {
                        "provider": provider,
                        "api_key": normalized_key,
                        "fingerprint": hashlib.sha256(
                            f"creditlens|{provider}|{normalized_key}".encode("utf-8")
                        ).hexdigest(),
                        "models": models,
                        "model": preferred_model,
                        "verified": True,
                        "verified_at": datetime.now(timezone.utc).isoformat(),
                    }
                    st.session_state.llm_connections = connections
                    st.session_state.active_llm_provider = provider
                    st.session_state.llm_active_selector = provider
                    st.session_state.llm_connection_error = ""
                    settings["llm_provider"] = provider
                    settings["model"] = preferred_model
                    st.session_state.llm_connection_notice = (
                        f"Đã kết nối {NHA_CUNG_CAP_LLM[provider]['nhan']} và chọn {preferred_model}."
                    )
                    st.rerun()
                except (ValueError, RuntimeError) as exc:
                    st.session_state.llm_connection_error = str(exc)

        if st.session_state.get("llm_connection_error"):
            st.error(st.session_state.llm_connection_error)
        if st.session_state.get("llm_connection_notice"):
            st.success(st.session_state.pop("llm_connection_notice"))

        st.subheader("Kết nối dùng ngay")
        connections = st.session_state.get("llm_connections", {})
        providers = [provider for provider in NHA_CUNG_CAP_LLM if provider in connections]
        if providers:
            if st.session_state.get("llm_active_selector") not in providers:
                preferred = st.session_state.get("active_llm_provider")
                st.session_state.llm_active_selector = preferred if preferred in providers else providers[0]
            active_provider = st.selectbox(
                "API Key sử dụng ngay",
                providers,
                key="llm_active_selector",
                format_func=lambda value: nhan_ket_noi_llm(value, connections[value]),
                help="Chọn kết nối mà trang Tóm tắt sẽ dùng để tạo diễn giải AI.",
            )
            st.session_state.active_llm_provider = active_provider
            connection = dict(connections[active_provider])
            models = list(connection.get("models", []))
            model_key = f"llm_model_selector_{active_provider}"
            if st.session_state.get(model_key) not in models:
                st.session_state[model_key] = connection.get("model") if connection.get("model") in models else models[0]
            selected_model = st.selectbox(
                "Model dùng để tạo diễn giải",
                models,
                key=model_key,
                help="Danh sách lấy trực tiếp từ API; không cần nhập tên model thủ công.",
            )
            connection["model"] = selected_model
            connections[active_provider] = connection
            st.session_state.llm_connections = connections
            settings["llm_provider"] = active_provider
            settings["model"] = selected_model
            current_result = st.session_state.get("result")
            tom_tat_ai_hieu_luc(
                st,
                connection,
                current_result.ma_ho_so if current_result is not None else "",
                settings["system_prompt"],
            )

            status_cols = st.columns(3)
            status_cols[0].metric("Nhà cung cấp", NHA_CUNG_CAP_LLM[active_provider]["nhan"])
            status_cols[1].metric("Model đang dùng", selected_model)
            status_cols[2].metric("Trạng thái", "Đã xác minh")

            refresh_col, delete_col = st.columns(2)
            refresh_models = refresh_col.button("Làm mới danh sách model", width="stretch")
            delete_col.button(
                "Xóa kết nối khỏi phiên",
                width="stretch",
                on_click=xoa_ket_noi_llm,
                args=(st, active_provider),
            )
            if refresh_models:
                try:
                    with st.status("Đang làm mới danh sách model", expanded=False) as status:
                        refreshed_models = lay_danh_sach_model(active_provider, connection["api_key"])
                        status.update(label="Danh sách model đã cập nhật", state="complete")
                    connection["models"] = refreshed_models
                    connection["model"] = selected_model if selected_model in refreshed_models else refreshed_models[0]
                    connections[active_provider] = connection
                    st.session_state.llm_connections = connections
                    st.rerun()
                except (ValueError, RuntimeError) as exc:
                    st.error(str(exc))
        else:
            st.selectbox("API Key sử dụng ngay", ["Chưa có kết nối đã xác minh"], disabled=True)
            st.info("Thêm một API Key ở trên. Sau khi xác thực, kết nối và model sẽ xuất hiện tại đây.")

        hien_thi_chat_ai(st, ket_noi_llm_dang_dung(st))

    with tab_ui:
        st.subheader("Nhận diện và chế độ hiển thị")
        st.caption("Chế độ Theo hệ thống tự động theo cài đặt sáng hoặc tối của thiết bị.")
        with st.form("appearance_settings"):
            new_theme = st.selectbox(
                "Chế độ giao diện",
                CHE_DO_GIAO_DIEN,
                index=CHE_DO_GIAO_DIEN.index(settings.get("che_do_giao_dien", "Theo hệ thống")),
            )
            new_title = st.text_input("Tên ứng dụng", value=settings["ten_ung_dung"], max_chars=90)
            color_col1, color_col2 = st.columns(2)
            new_color = color_col1.color_picker(
                "Màu chủ đạo của chế độ Hiện đại",
                value=lam_sach_mau(settings["mau_chu_dao"]),
            )
            new_accent = color_col2.color_picker(
                "Màu nhấn của chế độ Hiện đại",
                value=lam_sach_mau(settings.get("mau_nhan", "#A71B28"), "#A71B28"),
            )
            apply_appearance = st.form_submit_button("Áp dụng giao diện", type="primary", width="stretch")
        if apply_appearance:
            settings["ten_ung_dung"] = new_title.strip() or DEFAULT_SETTINGS["ten_ung_dung"]
            settings["mau_chu_dao"] = lam_sach_mau(new_color)
            settings["mau_nhan"] = lam_sach_mau(new_accent, "#A71B28")
            settings["che_do_giao_dien"] = new_theme
            st.session_state.settings = settings
            st.rerun()

    with tab_thresholds:
        st.subheader("Ngưỡng phục vụ minh họa")
        st.warning("Các giá trị này không phải quy định pháp lý hoặc chính sách của bất kỳ ngân hàng nào.")
        with st.form("threshold_settings"):
            c1, c2, c3, c4 = st.columns(4)
            income_mismatch = c1.number_input("Chênh lệch thu nhập (%)", 0.0, 100.0, settings["nguong"]["chenh_lech_thu_nhap"] * 100, 1.0)
            severe_income_mismatch = c2.number_input("Chênh lệch thu nhập nghiêm trọng (%)", 0.0, 100.0, settings["nguong"]["chenh_lech_thu_nhap_nghiem_trong"] * 100, 1.0)
            debt_mismatch = c3.number_input("Chênh lệch nợ (%)", 0.0, 500.0, settings["nguong"]["chenh_lech_no"] * 100, 1.0)
            low_confidence = c4.number_input("Độ tin cậy tối thiểu (%)", 0.0, 100.0, settings["nguong"]["do_tin_cay_thap"] * 100, 1.0)
            c5, c6, c7 = st.columns(3)
            dti = c5.number_input("Cảnh báo DTI (%)", 0.0, 200.0, settings["nguong"]["dti_canh_bao"] * 100, 1.0)
            dsr = c6.number_input("Cảnh báo DSR (%)", 0.0, 200.0, settings["nguong"]["dsr_canh_bao"] * 100, 1.0)
            buffer = c7.number_input("Hệ số đệm số dư tối thiểu", 0.0, 20.0, settings["nguong"]["he_so_dem_so_du_thap"], 0.1)
            volatility = st.number_input("Biến động thu nhập cao (%)", 0.0, 200.0, settings["nguong"]["bien_dong_thu_nhap_cao"] * 100, 1.0)
            apply_thresholds = st.form_submit_button("Áp dụng ngưỡng", type="primary", width="stretch")
        if apply_thresholds:
            if severe_income_mismatch < income_mismatch:
                st.error("Ngưỡng chênh lệch nghiêm trọng phải lớn hơn hoặc bằng ngưỡng cảnh báo thông thường.")
            else:
                settings["nguong"] = {
                    "do_tin_cay_thap": low_confidence / 100,
                    "chenh_lech_thu_nhap": income_mismatch / 100,
                    "chenh_lech_thu_nhap_nghiem_trong": severe_income_mismatch / 100,
                    "chenh_lech_no": debt_mismatch / 100,
                    "dti_canh_bao": dti / 100,
                    "dsr_canh_bao": dsr / 100,
                    "he_so_dem_so_du_thap": buffer,
                    "bien_dong_thu_nhap_cao": volatility / 100,
                }
                st.session_state.settings = settings
                st.session_state.result = None
                st.session_state.docs = {}
                st.session_state.ai_summary = ""
                st.session_state.ai_summary_context = {}
                st.success("Đã áp dụng. Hãy chạy lại hồ sơ vì ngưỡng mới có thể làm thay đổi cảnh báo.")

    with tab_guardrails:
        st.subheader("Guardrails của LLM")
        with st.form("guardrail_settings"):
            new_prompt = st.text_area("System prompt", value=settings["system_prompt"], height=270, max_chars=8000)
            apply_prompt = st.form_submit_button("Lưu guardrails trong phiên", type="primary", width="stretch")
        if apply_prompt:
            if len(new_prompt.strip()) < 50:
                st.error("System prompt quá ngắn để bảo đảm guardrails.")
            else:
                normalized_prompt = new_prompt.strip()
                if normalized_prompt != settings["system_prompt"]:
                    st.session_state.ai_summary = ""
                    st.session_state.ai_summary_context = {}
                settings["system_prompt"] = normalized_prompt
                st.session_state.settings = settings
                st.success("Đã cập nhật guardrails cho phiên hiện tại.")

        st.subheader("Nhập và xuất cấu hình")
        st.caption("Tệp JSON chỉ chứa giao diện, ngưỡng, provider/model và guardrails; không bao giờ chứa API Key.")
        col1, col2 = st.columns(2)
        col1.download_button(
            "Xuất cấu hình JSON",
            json.dumps(settings, ensure_ascii=False, indent=2),
            file_name="creditlens_config.json",
            mime="application/json",
            width="stretch",
        )
        config_upload = col2.file_uploader("Nhập cấu hình JSON", type=["json"], key="config_json")
        load_col, reset_col = st.columns(2)
        load_config = load_col.button("Nạp cấu hình đã chọn", disabled=config_upload is None, width="stretch")
        reset_defaults = reset_col.button("Khôi phục cấu hình mặc định", width="stretch")
        if config_upload and load_config:
            try:
                st.session_state.settings = nhap_cau_hinh_json(config_upload.getvalue())
                st.session_state.result = None
                st.session_state.docs = {}
                st.session_state.ai_summary = ""
                st.session_state.ai_summary_context = {}
                st.success("Đã nạp cấu hình. Kho API Key theo phiên không bị thay đổi.")
                st.rerun()
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                st.error(f"Không thể nạp cấu hình: {exc}")
        if reset_defaults:
            st.session_state.settings = cau_hinh_mac_dinh()
            st.session_state.result = None
            st.session_state.docs = {}
            st.session_state.ai_summary = ""
            st.session_state.ai_summary_context = {}
            st.rerun()

        st.info(
            "Các tinh chỉnh chỉ áp dụng trong phiên. Việc khôi phục cấu hình không tự xóa API Key; "
            "hãy xóa từng kết nối trong tab Kết nối AI khi không còn sử dụng."
        )


def chay_ung_dung_streamlit() -> None:
    import streamlit as st

    page_icon: str = (
        str(LOGO_ICON_PATH)
        if LOGO_ICON_PATH.exists()
        else (str(LOGO_PATH) if LOGO_PATH.exists() else "🏦")
    )
    st.set_page_config(page_title="CreditLens", page_icon=page_icon, layout="wide", initial_sidebar_state="auto")
    if "settings" not in st.session_state:
        st.session_state.settings = cau_hinh_mac_dinh()
    if "result" not in st.session_state:
        st.session_state.result = None
    if "docs" not in st.session_state:
        st.session_state.docs = {}
    if "ai_summary" not in st.session_state:
        st.session_state.ai_summary = ""
    if "ai_summary_context" not in st.session_state:
        st.session_state.ai_summary_context = {}
    if "llm_connections" not in st.session_state:
        st.session_state.llm_connections = {}
    if "active_llm_provider" not in st.session_state:
        st.session_state.active_llm_provider = ""
    if "llm_api_key_draft" not in st.session_state:
        st.session_state.llm_api_key_draft = ""
    if "llm_connection_error" not in st.session_state:
        st.session_state.llm_connection_error = ""
    if "llm_chat_messages" not in st.session_state:
        st.session_state.llm_chat_messages = []

    settings = st.session_state.settings
    if LOGO_PATH.exists():
        st.sidebar.image(str(LOGO_PATH), width="stretch")
        st.sidebar.markdown(
            "<div class='brand-caption'><strong>HUB × CreditLens</strong><span>Thẩm định có thể kiểm chứng</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown("## CreditLens")
    st.sidebar.markdown(
        "<div class='public-pill'><span class='public-dot'></span> BẢN MINH HỌa CÔNG KHAI</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Khi deploy trên cloud, ứng dụng hoạt động độc lập với máy cá nhân.")
    thresholds = nguong_hieu_luc(settings["nguong"])
    hien_thi_header(st, settings)

    st.sidebar.markdown("<div class='sidebar-section-label'>Điều hướng</div>", unsafe_allow_html=True)
    page = st.sidebar.radio(
        "Điều hướng",
        PAGES,
        format_func=lambda value: NHAN_DIEU_HUONG[value],
        label_visibility="collapsed",
    )
    active_connection = ket_noi_llm_dang_dung(st)
    if active_connection:
        st.sidebar.caption(
            f"AI đang dùng · {NHA_CUNG_CAP_LLM[active_connection['provider']]['nhan']} · "
            f"{active_connection['model']}"
        )
    else:
        st.sidebar.caption("AI chưa kết nối · Phân tích Python vẫn hoạt động")
    st.sidebar.divider()
    if st.sidebar.button("Xóa hồ sơ khỏi phiên", width="stretch"):
        st.session_state.result = None
        st.session_state.docs = {}
        st.session_state.ai_summary = ""
        st.session_state.ai_summary_context = {}
        st.rerun()
    st.sidebar.caption("Ngưỡng minh họa · Không phải chính sách ngân hàng · Bắt buộc con người xem xét")

    result = st.session_state.result
    docs = st.session_state.docs
    if page == "Trang chủ & hồ sơ":
        trang_ho_so(st, thresholds)
    elif page == "Trích xuất tài liệu":
        trang_trich_xuat(st, result, docs, thresholds)
    elif page == "Phân tích tín dụng":
        trang_phan_tich(st, result, thresholds)
    elif page == "Cảnh báo rủi ro":
        trang_rui_ro(st, result)
    elif page == "Tóm tắt thẩm định":
        trang_tom_tat(st, result, settings)
    elif page == "Đánh giá & phương pháp":
        trang_danh_gia(st)
    elif page == "Evaluation":
        trang_evaluation(st, settings)
    else:
        trang_cai_dat(st, settings)


# ==========================================================
# 10. TỰ KIỂM TRA NHANH
# ==========================================================

def chay_tu_kiem_tra() -> None:
    defaults_before = dict(NGUONG)
    normal, normal_docs = du_lieu_demo("CASE-01 — Hồ sơ bình thường")
    strict_normal, _ = du_lieu_demo(
        "CASE-01 — Hồ sơ bình thường",
        {**defaults_before, "dti_canh_bao": 0.01},
    )
    strict_confidence, _ = du_lieu_demo(
        "CASE-01 — Hồ sơ bình thường",
        {**defaults_before, "do_tin_cay_thap": 0.97},
    )
    mismatch, _ = du_lieu_demo("CASE-03 — Thu nhập không nhất quán")
    missing, _ = du_lieu_demo("CASE-08 — Đơn vay chưa đầy đủ")
    zero_ratio = chia_an_toan(10, 0)
    assert normal.trang_thai == "REVIEW READY"
    assert any(r.loai == "HIGH_DTI_DEMO" for r in strict_normal.canh_bao)
    assert any(r.loai == "LOW_EXTRACTION_CONFIDENCE" for r in strict_confidence.canh_bao)
    assert dict(NGUONG) == defaults_before
    assert any(r.loai == "INCOME_MISMATCH" for r in mismatch.canh_bao)
    assert missing.trang_thai == "INSUFFICIENT INFORMATION"
    assert zero_ratio is None
    assert all(r.bang_chung for r in mismatch.canh_bao if r.loai == "INCOME_MISMATCH")

    one_percent = tim_ty_le("Income Volatility: 1%", ["Income Volatility"])
    one_without_unit = tim_ty_le("Income Volatility: 1", ["Income Volatility"])
    decimal_ratio = tim_ty_le("Income Volatility: 0.25", ["Income Volatility"])
    assert one_percent and one_percent["number"] == 0.01
    assert one_without_unit and one_without_unit["number"] == 0.01
    assert decimal_ratio and decimal_ratio["number"] == 0.25
    assert chuan_hoa_ngay("2022-06-01") == chuan_hoa_ngay("01/06/2022")
    assert chuan_hoa_ngay("2022/06/01") == chuan_hoa_ngay("01-06-2022")
    assert chuan_hoa_ngay("31/02/2022") is None

    same_date_data = BASE_DATA.model_copy(update={"ngay_bat_dau_chung_tu": "01/06/2022"})
    same_date_result = phan_tich_tu_du_kien(
        "TEST-DATE-SAME", "Định dạng ngày tương đương", same_date_data,
        normal.truong_trich_xuat, normal_docs, time.perf_counter(), defaults_before,
    )
    assert not any(r.loai == "EMPLOYMENT_DATE_MISMATCH" for r in same_date_result.canh_bao)

    zero_declared_debt_data = BASE_DATA.model_copy(
        update={"nghia_vu_no_ke_khai": 0, "nghia_vu_no_quan_sat": 2_000_000}
    )
    zero_declared_debt = phan_tich_tu_du_kien(
        "TEST-DEBT-ZERO", "Nợ kê khai bằng 0", zero_declared_debt_data,
        normal.truong_trich_xuat, normal_docs, time.perf_counter(), defaults_before,
    )
    zero_debt_risk = next(r for r in zero_declared_debt.canh_bao if r.loai == "POSSIBLE_UNDECLARED_DEBT")
    assert zero_debt_risk.muc_do == "HIGH" and "%" not in (zero_debt_risk.chenh_lech or "")
    assert "mẫu số bằng 0" in zero_debt_risk.giai_thich

    moderate_income_data = BASE_DATA.model_copy(
        update={"thu_nhap_ke_khai": 32_000_000, "luong_thuc_nhan": 30_000_000, "thu_nhap_qua_sao_ke": 24_000_000}
    )
    moderate_income = phan_tich_tu_du_kien(
        "TEST-INCOME-MEDIUM", "Mốc nghiêm trọng theo phiên", moderate_income_data,
        normal.truong_trich_xuat, normal_docs, time.perf_counter(),
        {**defaults_before, "chenh_lech_thu_nhap_nghiem_trong": 0.30},
    )
    severe_income = phan_tich_tu_du_kien(
        "TEST-INCOME-HIGH", "Mốc nghiêm trọng theo phiên", moderate_income_data,
        normal.truong_trich_xuat, normal_docs, time.perf_counter(),
        {**defaults_before, "chenh_lech_thu_nhap_nghiem_trong": 0.20},
    )
    assert next(r for r in moderate_income.canh_bao if r.loai == "INCOME_MISMATCH").muc_do == "MEDIUM"
    assert next(r for r in severe_income.canh_bao if r.loai == "INCOME_MISMATCH").muc_do == "HIGH"

    declared_only_data = BASE_DATA.model_copy(
        update={"luong_thuc_nhan": None, "thu_nhap_qua_sao_ke": None, "thu_nhap_ke_khai": 25_000_000}
    )
    declared_only = phan_tich_tu_du_kien(
        "TEST-INCOME-FALLBACK", "Fallback kê khai", declared_only_data,
        normal.truong_trich_xuat, normal_docs, time.perf_counter(), defaults_before,
    )
    assert declared_only.thu_nhap_dung_de_tinh == 25_000_000
    assert declared_only.nguon_thu_nhap_dung_de_tinh.startswith("Thu nhập kê khai")
    assert not declared_only.thu_nhap_duoc_xac_minh_doc_lap
    assert declared_only.trang_thai == "HUMAN REVIEW REQUIRED"
    declared_markdown = bao_cao_markdown(declared_only)
    assert "Thu nhập dùng để tính" in declared_markdown and "Thu nhập đã xác minh" not in declared_markdown
    assert "api_key" not in json.dumps(cau_hinh_mac_dinh(), ensure_ascii=False).lower()
    assert nhap_cau_hinh_json(b'{"mau_chu_dao":"#112233"}')["mau_chu_dao"] == "#112233"
    imported_thresholds = nhap_cau_hinh_json(
        b'{"nguong":{"he_so_dem_so_du_thap":12,"do_tin_cay_thap":4}}'
    )["nguong"]
    assert imported_thresholds["he_so_dem_so_du_thap"] == 12
    assert imported_thresholds["do_tin_cay_thap"] == NGUONG["do_tin_cay_thap"]
    imported_llm = nhap_cau_hinh_json(b'{"llm_provider":"gemini","model":"gemini-test"}')
    assert imported_llm["llm_provider"] == "gemini" and imported_llm["model"] == "gemini-test"
    assert nhan_dien_nha_cung_cap_tu_khoa("sk-ant-demo-123456789") == "anthropic"
    assert nhan_dien_nha_cung_cap_tu_khoa("AIzaDemoKey123456789") == "gemini"
    assert nhan_dien_nha_cung_cap_tu_khoa("sk-proj-demo-123456789") == "openai"
    assert nhan_dien_nha_cung_cap_tu_khoa("sk-ambiguous-123456789") is None
    assert nha_cung_cap_hieu_luc("DeepSeek", "sk-ambiguous-123456789") == "deepseek"
    prompt_context_a = ngu_canh_tom_tat_ai(
        {"provider": "openai", "model": "gpt-test", "fingerprint": "key-test"},
        "CASE-TEST",
        "Guardrail A",
    )
    prompt_context_b = ngu_canh_tom_tat_ai(
        {"provider": "openai", "model": "gpt-test", "fingerprint": "key-test"},
        "CASE-TEST",
        "Guardrail B",
    )
    assert prompt_context_a != prompt_context_b and "Guardrail A" not in json.dumps(prompt_context_a)
    assert trich_danh_sach_model(
        "openai",
        {"data": [{"id": "gpt-5.6-sol"}, {"id": "text-embedding-3-large"}]},
    ) == ["gpt-5.6-sol"]
    assert trich_danh_sach_model(
        "gemini",
        {"models": [
            {"name": "models/gemini-3-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
        ]},
    ) == ["gemini-3-flash"]
    assert trich_danh_sach_model("anthropic", {"data": [{"id": "claude-sonnet-demo"}]}) == ["claude-sonnet-demo"]
    assert trich_danh_sach_model("deepseek", {"data": [{"id": "deepseek-chat"}]}) == ["deepseek-chat"]
    assert trich_noi_dung_phan_hoi(
        "gemini",
        {"candidates": [{"content": {"parts": [{"text": "Tóm tắt Gemini"}]}}]},
    ) == "Tóm tắt Gemini"
    assert trich_noi_dung_phan_hoi(
        "anthropic",
        {"content": [{"type": "text", "text": "Tóm tắt Claude"}]},
    ) == "Tóm tắt Claude"
    assert trich_noi_dung_phan_hoi(
        "deepseek",
        {"choices": [{"message": {"content": "Tóm tắt DeepSeek"}}]},
    ) == "Tóm tắt DeepSeek"
    chat_history = chuan_hoa_lich_su_chat([
        {"role": "user", "content": " Xin chào "},
        {"role": "assistant", "content": "Chào bạn"},
        {"role": "system", "content": "Không được gửi"},
        {"role": "user", "content": "   "},
    ])
    assert chat_history == [
        {"role": "user", "content": "Xin chào"},
        {"role": "assistant", "content": "Chào bạn"},
    ]
    salary_after_period = tim_so_tien(
        "Kỳ lương\nLương thực nhận\n08/2026\n"
        "Lương thực nhận\n28.000.000 VND",
        ["Lương thực nhận"],
    )
    assert salary_after_period and salary_after_period["number"] == 28_000_000
    wrapped_payment = tim_so_tien(
        "Trả nợ khoản vay mới hàng\ntháng\n7.200.000 VND",
        ["Trả nợ khoản vay mới hàng tháng"],
    )
    assert wrapped_payment and wrapped_payment["number"] == 7_200_000
    assert goi_y_loai_tu_ten_tep("04_Thong_tin_nghia_vu_no.pdf") == "debt"
    assert goi_y_loai_tu_ten_tep("03_Sao_ke_ngan_hang_6_thang.pdf") == "statement"
    assert nhan_luu_y_tin_cay(0.95) == "Tin cậy cao"
    assert nhan_luu_y_tin_cay(0.80) == "Cần đối chiếu"
    assert nhan_luu_y_tin_cay(0.88) == "Cần đối chiếu"
    assert nhan_luu_y_tin_cay(0.60) == "Cần xác minh"
    assert nhan_luu_y_tin_cay(0.93, low_confidence_threshold=0.95) == "Cần xác minh"
    assert nhan_luu_y_tin_cay(0.0, missing=True) == "Thiếu dữ liệu"
    assert "background-color:#DCFCE7;color:#14532D" in kieu_o_luu_y("Tin cậy cao")
    for mode in CHE_DO_GIAO_DIEN:
        theme_settings = cau_hinh_mac_dinh()
        theme_settings["che_do_giao_dien"] = mode
        css = tao_css_giao_dien(theme_settings)
        assert "PRIMARY_COLOR" not in css and "SYSTEM_THEME_MEDIA" not in css and "METRIC_OK_COLOR" not in css
        assert "WATERMARK_IMAGE" not in css
        assert "font-family: Inter" in css
        if mode == "Tối":
            assert "--credit-metric-ok: #86EFAC" in css and "--credit-metric-warn: #FCD34D" in css
        if mode == "Theo hệ thống":
            assert "@media (prefers-color-scheme: dark)" in css and "--credit-metric-missing: #CBD5E1" in css
    docx_data = tao_bao_cao_word(mismatch)
    xlsx_data = tao_bao_cao_excel(mismatch)
    pdf_data = tao_bao_cao_pdf(mismatch)
    assert docx_data[:2] == b"PK" and len(docx_data) > 5_000
    assert xlsx_data[:2] == b"PK" and len(xlsx_data) > 5_000
    assert pdf_data[:5] == b"%PDF-" and len(pdf_data) > 5_000
    pdf_text = "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf_data)).pages)
    assert "THẨM ĐỊNH TÍN DỤNG" in pdf_text and "Nguyễn Minh Anh" in pdf_text

    # Nhãn trong mọi định dạng xuất phải dùng đúng ngưỡng của phiên, không quay về mặc định module.
    low_case, _ = du_lieu_demo(
        "CASE-09 — Độ tin cậy thấp",
        {**defaults_before, "do_tin_cay_thap": 0.50},
    )
    from docx import Document as DocxDocument
    from openpyxl import load_workbook

    threshold_docx = DocxDocument(io.BytesIO(tao_bao_cao_word(low_case, "", 0.50)))
    word_note = next(
        row.cells[4].text
        for table in threshold_docx.tables
        for row in table.rows
        if len(row.cells) >= 5 and row.cells[0].text == "Lương thực nhận"
    )
    threshold_xlsx = load_workbook(io.BytesIO(tao_bao_cao_excel(low_case, "", 0.50)), data_only=True)
    excel_note = next(
        row[5]
        for row in threshold_xlsx["Trich xuat"].iter_rows(min_row=4, values_only=True)
        if row[1] == "Lương thực nhận"
    )
    threshold_pdf_text = "\n".join(
        (page.extract_text() or "")
        for page in PdfReader(io.BytesIO(tao_bao_cao_pdf(low_case, "", 0.50))).pages
    )
    assert word_note == "Cần đối chiếu" and excel_note == "Cần đối chiếu"
    assert "Cần đối chiếu" in threshold_pdf_text and "Cần xác minh" not in threshold_pdf_text
    print(
        "SELF_TEST_PASS: session-isolated thresholds, five themes, four LLM providers, "
        "regression fixes, chat history, key/model detection, prompt provenance, and consistent Word/Excel/PDF labels."
    )


if __name__ == "__main__":
    if os.environ.get("CREDITLENS_SELF_TEST") == "1":
        chay_tu_kiem_tra()
    else:
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx

            running_in_streamlit = get_script_run_ctx(suppress_warning=True) is not None
        except (ImportError, ModuleNotFoundError):
            running_in_streamlit = False
        if running_in_streamlit:
            chay_ung_dung_streamlit()
        else:
            print(
                "CreditLens là ứng dụng Streamlit.\n"
                "Trong Jupyter, chạy hai ô sau:\n"
                "1) from credit_underwriting_colab import cai_dat_thu_vien; cai_dat_thu_vien()\n"
                "2) !python -m streamlit run credit_underwriting_colab.py\n"
                "Sau đó mở http://localhost:8501"
            )
