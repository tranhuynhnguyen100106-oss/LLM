"""
CREDITLENS — AI CREDIT UNDERWRITING COPILOT (STREAMLIT)

Chạy từ Jupyter Notebook trên máy tính:
1. Chạy: from credit_underwriting_colab import cai_dat_thu_vien; cai_dat_thu_vien()
2. Chạy ở ô kế tiếp: !python -m streamlit run credit_underwriting_colab.py
3. Mở http://localhost:8501

Để có URL ổn định, đưa project lên GitHub rồi triển khai trên Streamlit Community
Cloud hoặc một dịch vụ web luôn hoạt động. Ứng dụng có giao diện sáng/neon,
ô nhập OpenAI API Key theo phiên và xuất báo cáo Word, Excel, PDF trong bộ nhớ.
Khóa và nội dung tài liệu không được ghi vào tệp hay log.

Lưu ý:
- Chỉ dùng dữ liệu tổng hợp hoặc đã ẩn danh.
- Ứng dụng không phê duyệt hoặc từ chối khoản vay.
- Các ngưỡng là ngưỡng minh họa, không phải chính sách ngân hàng.
- Không cung cấp trình sửa/chạy source code từ website công khai.
"""

from __future__ import annotations

import importlib.util
import html
import io
import json
import math
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


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

NGUONG = {
    "do_tin_cay_thap": 0.75,
    "chenh_lech_thu_nhap": 0.15,
    "chenh_lech_no": 0.20,
    "dti_canh_bao": 0.40,
    "dsr_canh_bao": 0.45,
    "he_so_dem_so_du_thap": 1.00,
    "bien_dong_thu_nhap_cao": 0.25,
}

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
    thu_nhap_da_xac_minh: float | None = None
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


def chuan_hoa_chuoi(value: str | None) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()
    text = re.sub(r"\b(cong ty|company|co|ltd|jsc|tnhh|cp)\b", "", text)
    return re.sub(r"[^a-z0-9]", "", text)


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


def tim_van_ban(text: str, aliases: list[str]) -> dict[str, Any] | None:
    for alias in aliases:
        match = re.search(rf"{re.escape(alias)}\s*[:\-–]?\s*([^\n\r|]{{2,100}})", text, re.IGNORECASE)
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
        pattern = rf"{re.escape(alias)}\s*[:\-–]?\s*(?:VND|VNĐ|₫|đ)?[ \t]*([0-9][0-9., \t]{{1,}})"
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
            rf"{re.escape(alias)}\s*[:\-–]?\s*([0-9]+(?:[.,][0-9]+)?)\s*%?",
            text,
            re.IGNORECASE,
        )
        if match:
            raw = float(match.group(1).replace(",", "."))
            number = raw / 100 if raw > 1 else raw
            return {
                "value": match.group(1),
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


def phan_loai_tai_lieu(filename: str, text: str) -> tuple[str, float]:
    input_text = f"{filename} {text[:1800]}".lower()
    scores = {key: sum(keyword in input_text for keyword in keywords) for key, keywords in TU_KHOA_PHAN_LOAI.items()}
    best = max(scores, key=scores.get)
    score = scores[best]
    return (best, min(0.98, 0.68 + score * 0.10)) if score else ("unknown", 0.35)


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
) -> KetQuaThamDinh:
    verified_candidates = [v for v in [data.luong_thuc_nhan, data.thu_nhap_qua_sao_ke] if v is not None and v > 0]
    verified_income = min(verified_candidates) if verified_candidates else data.thu_nhap_ke_khai
    debt = data.nghia_vu_no_quan_sat if data.nghia_vu_no_quan_sat is not None else data.nghia_vu_no_ke_khai

    dti = chia_an_toan(debt, verified_income)
    dsr = chia_an_toan(
        (debt + data.khoan_tra_du_kien) if debt is not None and data.khoan_tra_du_kien is not None else None,
        verified_income,
    )
    disposable = (
        verified_income - debt - data.chi_phi_sinh_hoat
        if verified_income is not None and debt is not None and data.chi_phi_sinh_hoat is not None
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
        ChiSoTinDung(ma_chi_so="dti", ten="DTI hiện hữu", gia_tri=dti, hien_thi=phan_tram(dti), cong_thuc="Nghĩa vụ nợ hiện hữu ÷ Thu nhập đã xác minh", trang_thai=status(dti, NGUONG["dti_canh_bao"]), ghi_chu="Gánh nặng nợ hiện hữu trước khi xét khoản vay mới."),
        ChiSoTinDung(ma_chi_so="dsr", ten="DSR dự kiến", gia_tri=dsr, hien_thi=phan_tram(dsr), cong_thuc="(Nợ hiện hữu + Khoản trả dự kiến) ÷ Thu nhập đã xác minh", trang_thai=status(dsr, NGUONG["dsr_canh_bao"]), ghi_chu="Chỉ tính khi có khoản trả dự kiến; hệ thống không tự suy đoán."),
        ChiSoTinDung(ma_chi_so="thu_nhap_kha_dung", ten="Thu nhập khả dụng", gia_tri=disposable, hien_thi=tien(disposable), cong_thuc="Thu nhập đã xác minh − Nợ − Chi phí sinh hoạt", trang_thai="Chưa đủ dữ liệu" if disposable is None else ("Cần chú ý" if disposable < 0 else "Trong ngưỡng minh họa"), ghi_chu="Giá trị trước khi trừ khoản trả của khoản vay mới."),
        ChiSoTinDung(ma_chi_so="he_so_dem_so_du", ten="Hệ số đệm số dư", gia_tri=balance_buffer, hien_thi="—" if balance_buffer is None else f"{so_thap_phan(balance_buffer)}×", cong_thuc="Số dư bình quân ÷ Khoản trả dự kiến", trang_thai=status(balance_buffer, NGUONG["he_so_dem_so_du_thap"], lower_is_bad=True), ghi_chu="Chỉ báo thanh khoản dựa trên số dư bình quân."),
        ChiSoTinDung(ma_chi_so="chenh_lech_thu_nhap", ten="Chênh lệch thu nhập", gia_tri=income_difference, hien_thi=phan_tram(income_difference), cong_thuc="(Nguồn cao nhất − Nguồn thấp nhất) ÷ Nguồn cao nhất", trang_thai=status(income_difference, NGUONG["chenh_lech_thu_nhap"]), ghi_chu="So sánh đơn vay, chứng từ thu nhập và sao kê."),
        ChiSoTinDung(ma_chi_so="bien_dong_thu_nhap", ten="Biến động thu nhập", gia_tri=data.bien_dong_thu_nhap, hien_thi=phan_tram(data.bien_dong_thu_nhap), cong_thuc="Độ lệch chuẩn dòng tiền vào tháng ÷ Dòng tiền vào bình quân", trang_thai=status(data.bien_dong_thu_nhap, NGUONG["bien_dong_thu_nhap_cao"]), ghi_chu="Hệ số biến thiên khi sao kê có đủ dữ liệu theo tháng."),
    ]

    risks: list[CanhBaoRuiRo] = []

    def add_risk(loai: str, muc_do: str, giai_thich: str, evidence: list[BangChung], difference: str | None = None) -> None:
        risks.append(CanhBaoRuiRo(ma_rui_ro=f"R-{len(risks) + 1:03d}", loai=loai, muc_do=muc_do, giai_thich=giai_thich, chenh_lech=difference, bang_chung=evidence))

    if income_difference is not None and income_difference > NGUONG["chenh_lech_thu_nhap"]:
        add_risk(
            "INCOME_MISMATCH",
            "HIGH" if income_difference > 0.30 else "MEDIUM",
            f"Các nguồn thu nhập chênh {phan_tram(income_difference)}, vượt ngưỡng minh họa {phan_tram(NGUONG['chenh_lech_thu_nhap'])}. Cần xác minh nguồn thu và kỳ ghi nhận.",
            bang_chung_cua(fields, "thu_nhap_ke_khai") + bang_chung_cua(fields, "luong_thuc_nhan") + bang_chung_cua(fields, "thu_nhap_qua_sao_ke"),
            phan_tram(income_difference),
        )
    if data.don_vi_cong_tac_ke_khai and data.don_vi_cong_tac_chung_tu and chuan_hoa_chuoi(data.don_vi_cong_tac_ke_khai) != chuan_hoa_chuoi(data.don_vi_cong_tac_chung_tu):
        add_risk("EMPLOYER_MISMATCH", "HIGH", "Tên đơn vị công tác trên đơn vay và chứng từ thu nhập không khớp sau chuẩn hóa.", bang_chung_cua(fields, "don_vi_cong_tac_ke_khai") + bang_chung_cua(fields, "don_vi_cong_tac_chung_tu"))
    if data.nghia_vu_no_ke_khai is not None and data.nghia_vu_no_quan_sat is not None:
        debt_diff = abs(data.nghia_vu_no_quan_sat - data.nghia_vu_no_ke_khai) / max(data.nghia_vu_no_ke_khai, 1)
        if debt_diff > NGUONG["chenh_lech_no"]:
            add_risk("POSSIBLE_UNDECLARED_DEBT", "HIGH" if data.nghia_vu_no_quan_sat > data.nghia_vu_no_ke_khai else "MEDIUM", f"Khoản trả nợ quan sát khác {phan_tram(debt_diff)} so với kê khai, vượt ngưỡng minh họa {phan_tram(NGUONG['chenh_lech_no'])}.", bang_chung_cua(fields, "nghia_vu_no_ke_khai") + bang_chung_cua(fields, "nghia_vu_no_quan_sat"), phan_tram(debt_diff))
    if data.chuc_danh_ke_khai and data.chuc_danh_chung_tu and chuan_hoa_chuoi(data.chuc_danh_ke_khai) != chuan_hoa_chuoi(data.chuc_danh_chung_tu):
        add_risk("JOB_TITLE_MISMATCH", "MEDIUM", "Chức danh công việc khác nhau giữa đơn vay và chứng từ thu nhập.", bang_chung_cua(fields, "chuc_danh_ke_khai") + bang_chung_cua(fields, "chuc_danh_chung_tu"))
    if data.ngay_bat_dau_ke_khai and data.ngay_bat_dau_chung_tu and chuan_hoa_chuoi(data.ngay_bat_dau_ke_khai) != chuan_hoa_chuoi(data.ngay_bat_dau_chung_tu):
        add_risk("EMPLOYMENT_DATE_MISMATCH", "MEDIUM", "Ngày bắt đầu làm việc không nhất quán giữa các chứng từ.", bang_chung_cua(fields, "ngay_bat_dau_ke_khai") + bang_chung_cua(fields, "ngay_bat_dau_chung_tu"))
    if dti is not None and dti > NGUONG["dti_canh_bao"]:
        add_risk("HIGH_DTI_DEMO", "HIGH", f"DTI {phan_tram(dti)} vượt ngưỡng cảnh báo minh họa {phan_tram(NGUONG['dti_canh_bao'])}. Đây không phải chính sách cấp tín dụng của ngân hàng.", bang_chung_cua(fields, "nghia_vu_no_quan_sat" if data.nghia_vu_no_quan_sat is not None else "nghia_vu_no_ke_khai") + bang_chung_cua(fields, "thu_nhap_qua_sao_ke" if data.thu_nhap_qua_sao_ke is not None else "luong_thuc_nhan"))
    if dsr is not None and dsr > NGUONG["dsr_canh_bao"]:
        add_risk("HIGH_DSR_DEMO", "HIGH", f"DSR dự kiến {phan_tram(dsr)} vượt ngưỡng cảnh báo minh họa {phan_tram(NGUONG['dsr_canh_bao'])}.", bang_chung_cua(fields, "nghia_vu_no_quan_sat") + bang_chung_cua(fields, "khoan_tra_du_kien") + bang_chung_cua(fields, "thu_nhap_qua_sao_ke"))
    if balance_buffer is not None and balance_buffer < NGUONG["he_so_dem_so_du_thap"]:
        add_risk("LOW_BALANCE_BUFFER", "MEDIUM", f"Hệ số đệm số dư {so_thap_phan(balance_buffer)}× thấp hơn ngưỡng minh họa {so_thap_phan(NGUONG['he_so_dem_so_du_thap'])}×.", bang_chung_cua(fields, "so_du_binh_quan") + bang_chung_cua(fields, "khoan_tra_du_kien"))
    if data.bien_dong_thu_nhap is not None and data.bien_dong_thu_nhap > NGUONG["bien_dong_thu_nhap_cao"]:
        add_risk("HIGH_INCOME_VOLATILITY", "MEDIUM", f"Biến động dòng tiền vào {phan_tram(data.bien_dong_thu_nhap)} vượt ngưỡng minh họa {phan_tram(NGUONG['bien_dong_thu_nhap_cao'])}.", bang_chung_cua(fields, "bien_dong_thu_nhap"))

    missing: list[str] = []
    for key, label in [("application", "Đơn đề nghị vay vốn"), ("income", "Chứng từ thu nhập"), ("statement", "Sao kê ngân hàng")]:
        if key not in docs or docs[key].trang_thai == "Không đọc được":
            missing.append(label)
    if not data.ho_ten_khach_hang:
        missing.append("Họ và tên khách hàng")
    if data.so_tien_de_nghi_vay is None:
        missing.append("Số tiền đề nghị vay")
    if verified_income is None:
        missing.append("Thu nhập hàng tháng đã xác minh")
    if data.thoi_han_vay_thang is None:
        missing.append("Thời hạn vay")

    low_confidence = [f for f in fields if f.gia_tri is not None and f.do_tin_cay < NGUONG["do_tin_cay_thap"]]
    if low_confidence:
        add_risk("LOW_EXTRACTION_CONFIDENCE", "MEDIUM", f"{len(low_confidence)} trường có độ tin cậy dưới {phan_tram(NGUONG['do_tin_cay_thap'])} và cần con người kiểm tra.", [f.bang_chung for f in low_confidence if f.bang_chung])

    questions: list[str] = []
    risk_types = {risk.loai for risk in risks}
    if "INCOME_MISMATCH" in risk_types:
        questions.append("Nguồn thu nhập nào là thường xuyên, có thể xác minh và thuộc đúng kỳ sao kê?")
    if "EMPLOYER_MISMATCH" in risk_types:
        questions.append("Khách hàng có thay đổi đơn vị công tác hay chứng từ nào đã lỗi thời?")
    if "POSSIBLE_UNDECLARED_DEBT" in risk_types:
        questions.append("Các khoản ghi nợ định kỳ nào là nghĩa vụ tín dụng hiện hữu của khách hàng?")
    if data.khoan_tra_du_kien is None:
        questions.append("Khoản trả nợ dự kiến hàng tháng theo phương án vay là bao nhiêu?")
    if missing:
        questions.append("Vui lòng bổ sung hoặc xác nhận: " + ", ".join(missing) + ".")
    if not questions:
        questions.append("Cán bộ tín dụng vui lòng xác nhận lại dữ kiện và bằng chứng trước khi đưa ra quyết định cuối cùng.")

    critical_missing = {"Đơn đề nghị vay vốn", "Chứng từ thu nhập", "Sao kê ngân hàng", "Số tiền đề nghị vay", "Thu nhập hàng tháng đã xác minh"}
    if any(item in critical_missing for item in missing):
        final_status = "INSUFFICIENT INFORMATION"
    elif risks:
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
        thu_nhap_da_xac_minh=verified_income,
        thoi_diem_xu_ly=datetime.now(timezone.utc).isoformat(),
        thoi_gian_xu_ly_ms=max(1, round((time.perf_counter() - started_at) * 1000)),
    )


def phan_tich_tai_lieu(ma_ho_so: str, docs: dict[str, TaiLieu]) -> KetQuaThamDinh:
    started = time.perf_counter()
    data, fields = trich_xuat_du_lieu(docs)
    return phan_tich_tu_du_kien(ma_ho_so, data.ho_ten_khach_hang or "Hồ sơ tín dụng đã tải lên", data, fields, docs, started)


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


def du_lieu_demo(case_name: str) -> tuple[KetQuaThamDinh, dict[str, TaiLieu]]:
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
    result = phan_tich_tu_du_kien(case_id, case_name, data, fields, docs, time.perf_counter() - 0.12)
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

## 3. Thông tin tài chính đã xác minh
- Thu nhập đã xác minh: {tien(result.thu_nhap_da_xac_minh)}
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
        ("Thu nhập đã xác minh", tien(result.thu_nhap_da_xac_minh)),
        ("Nghĩa vụ nợ quan sát", tien(d.nghia_vu_no_quan_sat)),
        ("Số dư bình quân", tien(d.so_du_binh_quan)),
        ("Thời điểm xử lý", result.thoi_diem_xu_ly),
        ("Thời gian xử lý", f"{result.thoi_gian_xu_ly_ms} ms"),
    ]


def _xoa_markdown(text: str) -> str:
    plain = re.sub(r"^#{1,6}\s*", "", text or "", flags=re.MULTILINE)
    plain = plain.replace("**", "").replace("`", "")
    return plain.strip()


def tao_bao_cao_word(result: KetQuaThamDinh, ai_summary: str = "") -> bytes:
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
    extracted_rows = [[f.nhan, gia_tri_truong_hien_thi(f), f.tai_lieu_nguon, f.trang or "-", f"{f.do_tin_cay:.0%}"] for f in result.truong_trich_xuat]
    add_table(["Trường", "Giá trị", "Nguồn", "Trang", "Tin cậy"], extracted_rows, [48, 46, 47, 15, 20])

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


def tao_bao_cao_excel(result: KetQuaThamDinh, ai_summary: str = "") -> bytes:
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
    header(ws, 3, ["Mã trường", "Trường dữ liệu", "Giá trị", "Tài liệu nguồn", "Trang", "Độ tin cậy", "Trích đoạn bằng chứng"])
    for row_index, field in enumerate(result.truong_trich_xuat, start=4):
        raw_value: Any = field.gia_tri
        values = [field.ma_truong, field.nhan, raw_value, field.tai_lieu_nguon, field.trang, field.do_tin_cay, field.bang_chung.trich_doan if field.bang_chung else ""]
        for col_index, value in enumerate(values, start=1):
            ws.cell(row_index, col_index, value)
        ws.cell(row_index, 6).number_format = "0%"
        if isinstance(raw_value, (int, float)) and field.ma_truong not in {"tham_nien_lam_viec_thang", "thoi_han_vay_thang", "bien_dong_thu_nhap"}:
            ws.cell(row_index, 3).number_format = "#,##0\" VND\""
        elif field.ma_truong == "bien_dong_thu_nhap" and isinstance(raw_value, (int, float)):
            ws.cell(row_index, 3).number_format = "0.0%"
    body_style(ws, 4, 3 + len(result.truong_trich_xuat), 7)
    set_widths(ws, [28, 42, 24, 42, 10, 16, 72])
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
    candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/local/share/fonts/DejaVuSans.ttf", "/usr/local/share/fonts/DejaVuSans-Bold.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ]
    for regular, bold in candidates:
        if Path(regular).is_file() and Path(bold).is_file():
            return regular, bold
    return None


def tao_bao_cao_pdf(result: KetQuaThamDinh, ai_summary: str = "") -> bytes:
    """Tạo PDF Unicode trong bộ nhớ bằng ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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
        text = text.replace("—", "-").replace("–", "-").replace("×", "x").replace("−", "-")
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
            story.append(para(f"{risk.ma_rui_ro} - {NHAN_RUI_RO.get(risk.loai, risk.loai)} - {NHAN_MUC_DO[risk.muc_do]}", ParagraphStyle("RiskTitle", parent=body_style, fontName="CreditLensSans-Bold", textColor=navy, spaceBefore=4)))
            story.append(para(risk.giai_thich))
            for evidence in risk.bang_chung:
                story.append(para(f"Bằng chứng: {evidence.tai_lieu}, trang {evidence.trang or 'không xác định'}, {evidence.truong_du_lieu} = {evidence.gia_tri}", small_style))
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
            ["Trường", "Giá trị", "Nguồn", "Trang", "Tin cậy"],
            [[f.nhan, gia_tri_truong_hien_thi(f), f.tai_lieu_nguon, f.trang or "-", f"{f.do_tin_cay:.0%}"] for f in result.truong_trich_xuat],
            [48, 47, 48, 16, 23],
        ),
    ]
    if ai_summary.strip():
        story.append(Paragraph("7 Diễn giải bổ sung bằng AI", heading_style))
        for line in _xoa_markdown(ai_summary).splitlines():
            if line.strip():
                story.append(para(line.strip()))
    story += [
        Paragraph("Trạng thái xem xét của con người", heading_style),
        para(f"{NHAN_TRANG_THAI[result.trang_thai]}. Chuyên viên tín dụng phải xác minh dữ kiện, xử lý mâu thuẫn và chịu trách nhiệm về quyết định cuối cùng."),
    ]

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

DEFAULT_SETTINGS = {
    "ten_ung_dung": "CreditLens — Trợ lý thẩm định tín dụng",
    "mau_chu_dao": "#5B5FEF",
    "mau_nhan": "#18C6D9",
    "model": "gpt-5-mini",
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "nguong": dict(NGUONG),
}

PAGES = [
    "Trang chủ & hồ sơ",
    "Trích xuất tài liệu",
    "Phân tích tín dụng",
    "Cảnh báo rủi ro",
    "Tóm tắt thẩm định",
    "Đánh giá & phương pháp",
    "Cài đặt AI",
]

STREAMLIT_CSS = """
<style>
  :root {
    --credit-primary: PRIMARY_COLOR;
    --credit-accent: ACCENT_COLOR;
    --credit-navy: #102A43;
    --credit-ink: #19324A;
    --credit-border: rgba(93, 119, 146, .22);
  }
  .stApp {
    color: var(--credit-ink);
    background:
      radial-gradient(circle at 8% 4%, rgba(24, 198, 217, .13), transparent 25rem),
      radial-gradient(circle at 91% 7%, rgba(91, 95, 239, .13), transparent 26rem),
      linear-gradient(180deg, #fbfdff 0%, #f3f8ff 52%, #f8fbff 100%);
  }
  .block-container { max-width: 1440px; padding-top: 1.25rem; padding-bottom: 4rem; }
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(239,248,255,.98));
    border-right: 1px solid rgba(91,95,239,.16);
  }
  [data-testid="stSidebar"] .stRadio label {
    border-radius: 12px; padding: 5px 8px; transition: all .2s ease;
  }
  [data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(91,95,239,.08); transform: translateX(2px);
  }
  .credit-hero {
    position: relative; overflow: hidden;
    background: linear-gradient(125deg, #102A43 0%, PRIMARY_COLOR 58%, ACCENT_COLOR 130%);
    color: white; border: 1px solid rgba(255,255,255,.36);
    border-radius: 26px; padding: 31px 34px; margin-bottom: 17px;
    box-shadow: 0 18px 55px rgba(35,79,150,.20), 0 0 28px rgba(24,198,217,.22);
  }
  .credit-hero:after {
    content: ""; position: absolute; width: 280px; height: 280px; right: -80px; top: -120px;
    border: 1px solid rgba(255,255,255,.28); border-radius: 50%;
    box-shadow: 0 0 55px rgba(255,255,255,.18), inset 0 0 40px rgba(255,255,255,.08);
  }
  .credit-kicker { font-size: .76rem; font-weight: 800; letter-spacing: .14em; opacity: .86; margin-bottom: 9px; }
  .credit-hero h1 { margin: 0 0 9px; font-size: clamp(1.75rem, 3.4vw, 2.55rem); line-height: 1.12; }
  .credit-hero p { margin: 0; max-width: 850px; opacity: .94; }
  .credit-chip {
    display: inline-block; margin-top: 16px; padding: 6px 11px; border-radius: 999px;
    background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.34);
    font-size: .78rem; font-weight: 700; backdrop-filter: blur(6px);
  }
  .credit-notice, .credit-privacy, .status-card, .evidence-card {
    background: rgba(255,255,255,.88); border: 1px solid var(--credit-border);
    border-radius: 16px; padding: 15px 17px; margin: 10px 0 18px;
    box-shadow: 0 10px 28px rgba(35,79,120,.07); backdrop-filter: blur(9px);
  }
  .credit-notice { border-left: 5px solid #FFB020; background: linear-gradient(100deg, #FFF9E8, rgba(255,255,255,.94)); }
  .credit-privacy { border-left: 5px solid ACCENT_COLOR; background: linear-gradient(100deg, #E9FBFD, rgba(255,255,255,.94)); }
  .status-card { border-left: 5px solid PRIMARY_COLOR; }
  .public-pill {
    display: inline-flex; align-items: center; gap: 7px; padding: 7px 11px; border-radius: 999px;
    color: #0B5560; background: #E4FBFD; border: 1px solid rgba(24,198,217,.38);
    font-size: .76rem; font-weight: 800; box-shadow: 0 0 18px rgba(24,198,217,.15);
  }
  .public-dot { width: 8px; height: 8px; border-radius: 50%; background: #00B884; box-shadow: 0 0 10px #00B884; }
  div[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(255,255,255,.98), rgba(244,250,255,.94));
    border: 1px solid var(--credit-border); border-radius: 18px; padding: 15px 17px;
    box-shadow: 0 11px 30px rgba(36,78,120,.08); transition: transform .2s ease, box-shadow .2s ease;
  }
  div[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 14px 36px rgba(36,78,120,.13), 0 0 18px rgba(24,198,217,.10); }
  div[data-testid="stFileUploaderDropzone"] {
    background: linear-gradient(145deg, rgba(255,255,255,.96), rgba(237,248,255,.94));
    border: 1.5px dashed rgba(91,95,239,.38); border-radius: 16px;
  }
  .stTextInput input, .stNumberInput input, .stTextArea textarea, div[data-baseweb="select"] > div {
    border-radius: 12px !important; border-color: rgba(91,95,239,.22) !important;
    background: rgba(255,255,255,.96) !important;
  }
  .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
    border-color: ACCENT_COLOR !important; box-shadow: 0 0 0 3px rgba(24,198,217,.14) !important;
  }
  .stButton > button, .stDownloadButton > button {
    border-radius: 13px !important; border: 1px solid rgba(91,95,239,.20) !important;
    font-weight: 750 !important; transition: all .2s ease !important;
  }
  .stButton > button:hover, .stDownloadButton > button:hover {
    transform: translateY(-1px); border-color: ACCENT_COLOR !important;
    box-shadow: 0 9px 24px rgba(35,79,150,.14), 0 0 16px rgba(24,198,217,.18) !important;
  }
  button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    color: white !important; border: 0 !important;
    background: linear-gradient(110deg, PRIMARY_COLOR, ACCENT_COLOR) !important;
    box-shadow: 0 10px 25px rgba(91,95,239,.25), 0 0 16px rgba(24,198,217,.16) !important;
  }
  [data-testid="stExpander"] { background: rgba(255,255,255,.84); border: 1px solid var(--credit-border); border-radius: 15px; overflow: hidden; }
  [data-testid="stDataFrame"] { border: 1px solid var(--credit-border); border-radius: 15px; overflow: hidden; box-shadow: 0 8px 25px rgba(36,78,120,.06); }
  hr { border-color: rgba(91,95,239,.13) !important; }
</style>
"""


def cau_hinh_mac_dinh() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_SETTINGS, ensure_ascii=False))


def lam_sach_mau(value: str, mac_dinh: str = "#5B5FEF") -> str:
    return value.upper() if re.fullmatch(r"#[0-9A-Fa-f]{6}", value or "") else mac_dinh


def lam_sach_ma_ho_so(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "-", (value or "").strip())[:80]
    return cleaned or "CASE-CHUA-XAC-DINH"


def xu_ly_tai_lieu_tai_len(ma_ho_so: str, uploads: dict[str, Any]) -> tuple[KetQuaThamDinh, dict[str, TaiLieu], list[str]]:
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
    return phan_tich_tai_lieu(lam_sach_ma_ho_so(ma_ho_so), docs), docs, errors


def du_lieu_gui_llm(result: KetQuaThamDinh) -> str:
    payload = result.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, indent=2)


def tao_dien_giai_bang_ai(result: KetQuaThamDinh, api_key: str, model: str, system_prompt: str) -> str:
    if not api_key or len(api_key.strip()) < 12:
        raise ValueError("API Key chưa được nhập hoặc không hợp lệ.")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{2,120}", model or ""):
        raise ValueError("Tên model không hợp lệ.")
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key.strip())
        response = client.responses.create(
            model=model.strip(),
            instructions=system_prompt[:8000],
            input=(
                "Hãy soạn Credit Review Summary theo đúng 10 mục: tổng quan khách hàng, "
                "đề nghị vay, thông tin tài chính đã xác minh, chỉ số, kiểm tra nhất quán, "
                "cảnh báo, thông tin thiếu, câu hỏi xác minh, bằng chứng và trạng thái xem xét.\n\n"
                + du_lieu_gui_llm(result)
            ),
            max_output_tokens=1800,
            store=False,
        )
        output = (response.output_text or "").strip()
    except Exception as exc:
        raise RuntimeError(
            f"Không thể gọi OpenAI API ({type(exc).__name__}). Hãy kiểm tra API Key, model, hạn mức và kết nối mạng."
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
    return output + "\n\n---\n**Bắt buộc con người xem xét. Nội dung AI không phải quyết định tín dụng.**"


def hien_thi_header(st, settings: dict[str, Any]) -> None:
    primary = lam_sach_mau(settings["mau_chu_dao"])
    accent = lam_sach_mau(settings.get("mau_nhan", "#18C6D9"), "#18C6D9")
    css = STREAMLIT_CSS.replace("PRIMARY_COLOR", primary).replace("ACCENT_COLOR", accent)
    st.markdown(css, unsafe_allow_html=True)
    title = html.escape(str(settings["ten_ung_dung"])[:90])
    st.markdown(
        f"<div class='credit-hero'><div class='credit-kicker'>AI CREDIT UNDERWRITING COPILOT</div>"
        f"<h1>{title}</h1><p>Dữ kiện → Phép tính Python → Quy tắc → Bằng chứng → Con người xem xét</p>"
        "<span class='credit-chip'>Multi-stage pipeline · Evidence grounded · Human-in-the-loop</span></div>",
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


def trang_ho_so(st) -> None:
    st.header("Tạo hồ sơ thẩm định mới")
    st.markdown(
        "<div class='credit-privacy'><b>Hệ thống minh họa.</b> Không tải lên thông tin ngân hàng thật hoặc dữ liệu mật. "
        "Tệp tạm được xóa ngay sau khi đọc; kết quả chỉ giữ trong phiên Streamlit.</div>",
        unsafe_allow_html=True,
    )
    case_id = st.text_input("Mã hồ sơ", value=f"CASE-{datetime.now():%Y%m%d}-01", max_chars=80)
    cols = st.columns(4)
    application = cols[0].file_uploader("Đơn đề nghị vay vốn", type=["pdf"], key="application_pdf")
    income = cols[1].file_uploader("Chứng từ thu nhập", type=["pdf"], key="income_pdf")
    statement = cols[2].file_uploader("Sao kê ngân hàng", type=["pdf"], key="statement_pdf")
    debt = cols[3].file_uploader("Nghĩa vụ nợ · tùy chọn", type=["pdf"], key="debt_pdf")
    if st.button("Chạy quy trình thẩm định", type="primary", width="stretch"):
        if not any([application, income, statement, debt]):
            st.error("Hãy tải lên ít nhất một PDF hoặc chọn hồ sơ minh họa.")
        else:
            try:
                with st.spinner("Đang kiểm tra, đọc, trích xuất và tính toán…"):
                    result, docs, errors = xu_ly_tai_lieu_tai_len(
                        case_id,
                        {"application": application, "income": income, "statement": statement, "debt": debt},
                    )
                st.session_state.result = result
                st.session_state.docs = docs
                st.session_state.ai_summary = ""
                if errors:
                    st.warning("Một số tệp không xử lý được: " + " · ".join(errors))
                st.success("Đã hoàn tất quy trình. Mở các mục bên trái để xem chi tiết.")
            except ValueError as exc:
                st.error(str(exc))

    st.divider()
    st.subheader("Hồ sơ tổng hợp minh họa")
    demo_choice = st.selectbox("Chọn tình huống", list(DEMO_CASES), index=2)
    if st.button("Mở hồ sơ minh họa", width="stretch"):
        result, docs = du_lieu_demo(demo_choice)
        st.session_state.result = result
        st.session_state.docs = docs
        st.session_state.ai_summary = ""
        st.success(f"Đã mở {demo_choice}.")
    hien_thi_trang_thai(st, st.session_state.result)


def trang_trich_xuat(st, result: KetQuaThamDinh | None, docs: dict[str, TaiLieu]) -> None:
    st.header("Trích xuất tài liệu")
    if result is None:
        st.warning("Chưa có hồ sơ để hiển thị.")
        return
    if docs:
        st.subheader("Danh mục tài liệu")
        st.dataframe(
            [
                {
                    "Tài liệu": doc.ten_tep,
                    "Loại dự kiến": NHAN_LOAI_TAI_LIEU[doc.loai_ky_vong],
                    "Loại nhận diện": NHAN_LOAI_TAI_LIEU.get(doc.loai_nhan_dien, "Chưa xác định"),
                    "Số trang": doc.so_trang,
                    "Trạng thái": doc.trang_thai,
                    "Độ tin cậy": f"{doc.do_tin_cay * 100:.0f}%",
                }
                for doc in docs.values()
            ],
            width="stretch",
            hide_index=True,
        )
    st.subheader("Dữ kiện đã chuẩn hóa")
    rows = []
    for field in result.truong_trich_xuat:
        display = gia_tri_truong_hien_thi(field)
        rows.append({"Mã trường": field.ma_truong, "Trường dữ liệu": field.nhan, "Giá trị": display, "Nguồn": field.tai_lieu_nguon, "Trang": field.trang or "—", "Độ tin cậy": f"{field.do_tin_cay * 100:.0f}%"})
    st.dataframe(rows, width="stretch", hide_index=True)
    low = [field.nhan for field in result.truong_trich_xuat if field.gia_tri is not None and field.do_tin_cay < NGUONG["do_tin_cay_thap"]]
    if low:
        st.warning("Các trường cần con người xác nhận: " + ", ".join(low))


def trang_phan_tich(st, result: KetQuaThamDinh | None) -> None:
    st.header("Phân tích tín dụng bằng Python")
    if result is None:
        st.warning("Chưa có hồ sơ để phân tích.")
        return
    cols = st.columns(3)
    for index, metric in enumerate(result.chi_so):
        with cols[index % 3]:
            st.metric(metric.ten, metric.hien_thi, metric.trang_thai)
            st.caption(metric.cong_thuc)
            st.caption(metric.ghi_chu)
    st.info(
        f"Ngưỡng minh họa: chênh lệch thu nhập > {phan_tram(NGUONG['chenh_lech_thu_nhap'])}; "
        f"DTI > {phan_tram(NGUONG['dti_canh_bao'])}; DSR > {phan_tram(NGUONG['dsr_canh_bao'])}; "
        f"hệ số đệm số dư < {so_thap_phan(NGUONG['he_so_dem_so_du_thap'])}×. Không phải chính sách ngân hàng."
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

    st.divider()
    st.subheader("Xuất báo cáo hồ sơ")
    st.caption("Chuyên viên chọn một trong ba định dạng. Báo cáo được tạo trong bộ nhớ và không lưu lâu dài trên máy chủ.")
    selected_format = st.radio(
        "Định dạng báo cáo",
        list(DINH_DANG_BAO_CAO),
        horizontal=True,
        key="report_format",
    )
    extension, mime_type, generator = DINH_DANG_BAO_CAO[selected_format]
    ai_text = st.session_state.get("ai_summary", "")
    try:
        report_bytes = generator(result, ai_text)
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
    api_key = st.session_state.get("api_key_session", "")
    if not api_key:
        st.info("Hãy nhập API Key tại mục “Cài đặt AI”. Khóa chỉ giữ trong phiên hiện tại.")
    if st.button("Tạo diễn giải bằng AI", type="primary", disabled=not bool(api_key), width="stretch"):
        try:
            with st.spinner("Đang tạo diễn giải có căn cứ…"):
                st.session_state.ai_summary = tao_dien_giai_bang_ai(result, api_key, settings["model"], settings["system_prompt"])
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
    if st.session_state.get("ai_summary"):
        st.markdown(st.session_state.ai_summary)


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
        output["mau_nhan"] = lam_sach_mau(candidate["mau_nhan"], "#18C6D9")
    if isinstance(candidate.get("model"), str) and re.fullmatch(r"[A-Za-z0-9._:-]{2,120}", candidate["model"]):
        output["model"] = candidate["model"]
    if isinstance(candidate.get("system_prompt"), str):
        output["system_prompt"] = candidate["system_prompt"][:8000]
    if isinstance(candidate.get("nguong"), dict):
        for key, default in output["nguong"].items():
            value = candidate["nguong"].get(key, default)
            if isinstance(value, (int, float)) and 0 <= float(value) <= 5:
                output["nguong"][key] = float(value)
    return output


def trang_cai_dat(st, settings: dict[str, Any]) -> None:
    st.header("Cài đặt AI và tùy chỉnh web an toàn")
    st.warning("API Key chỉ dùng để gọi LLM trong phiên hiện tại. Không ghi khóa vào source code, JSON tải xuống hoặc log. Không nhập khóa vào website do người khác quản lý mà bạn không tin cậy.")
    st.text_input("OpenAI API Key", type="password", key="api_key_session", placeholder="sk-…", help="Khóa nằm trong session_state và bị xóa khi phiên kết thúc.")
    if st.button("Xóa API Key khỏi phiên"):
        st.session_state.api_key_session = ""
        st.success("Đã xóa API Key khỏi phiên.")

    st.subheader("Giao diện")
    new_title = st.text_input("Tên ứng dụng", value=settings["ten_ung_dung"], max_chars=90)
    color_col1, color_col2 = st.columns(2)
    new_color = color_col1.color_picker("Màu chủ đạo", value=lam_sach_mau(settings["mau_chu_dao"]))
    new_accent = color_col2.color_picker("Màu neon nhấn", value=lam_sach_mau(settings.get("mau_nhan", "#18C6D9"), "#18C6D9"))
    st.subheader("LLM")
    new_model = st.text_input("Tên model OpenAI", value=settings["model"], max_chars=120)
    new_prompt = st.text_area("System prompt", value=settings["system_prompt"], height=260, max_chars=8000)

    st.subheader("Ngưỡng minh họa")
    c1, c2, c3 = st.columns(3)
    income_mismatch = c1.number_input("Chênh lệch thu nhập (%)", 0.0, 100.0, settings["nguong"]["chenh_lech_thu_nhap"] * 100, 1.0)
    debt_mismatch = c2.number_input("Chênh lệch nợ (%)", 0.0, 500.0, settings["nguong"]["chenh_lech_no"] * 100, 1.0)
    low_confidence = c3.number_input("Độ tin cậy tối thiểu (%)", 0.0, 100.0, settings["nguong"]["do_tin_cay_thap"] * 100, 1.0)
    c4, c5, c6 = st.columns(3)
    dti = c4.number_input("Cảnh báo DTI (%)", 0.0, 200.0, settings["nguong"]["dti_canh_bao"] * 100, 1.0)
    dsr = c5.number_input("Cảnh báo DSR (%)", 0.0, 200.0, settings["nguong"]["dsr_canh_bao"] * 100, 1.0)
    buffer = c6.number_input("Hệ số đệm số dư tối thiểu", 0.0, 20.0, settings["nguong"]["he_so_dem_so_du_thap"], 0.1)
    volatility = st.number_input("Biến động thu nhập cao (%)", 0.0, 200.0, settings["nguong"]["bien_dong_thu_nhap_cao"] * 100, 1.0)

    if st.button("Áp dụng cấu hình", type="primary", width="stretch"):
        if not re.fullmatch(r"[A-Za-z0-9._:-]{2,120}", new_model or ""):
            st.error("Tên model chỉ được chứa chữ, số, dấu chấm, gạch, gạch dưới và dấu hai chấm.")
        elif len(new_prompt.strip()) < 50:
            st.error("System prompt quá ngắn để bảo đảm guardrails.")
        else:
            st.session_state.settings = {
                "ten_ung_dung": new_title.strip() or DEFAULT_SETTINGS["ten_ung_dung"],
                "mau_chu_dao": lam_sach_mau(new_color),
                "mau_nhan": lam_sach_mau(new_accent, "#18C6D9"),
                "model": new_model.strip(),
                "system_prompt": new_prompt.strip(),
                "nguong": {
                    "do_tin_cay_thap": low_confidence / 100,
                    "chenh_lech_thu_nhap": income_mismatch / 100,
                    "chenh_lech_no": debt_mismatch / 100,
                    "dti_canh_bao": dti / 100,
                    "dsr_canh_bao": dsr / 100,
                    "he_so_dem_so_du_thap": buffer,
                    "bien_dong_thu_nhap_cao": volatility / 100,
                },
            }
            NGUONG.update(st.session_state.settings["nguong"])
            st.session_state.result = None
            st.session_state.docs = {}
            st.session_state.ai_summary = ""
            st.success("Đã áp dụng. Hãy chạy lại hồ sơ vì thay đổi ngưỡng làm thay đổi kết quả quy tắc.")
            st.rerun()

    col1, col2 = st.columns(2)
    col1.download_button("Xuất cấu hình JSON", json.dumps(settings, ensure_ascii=False, indent=2), file_name="creditlens_config.json", mime="application/json", width="stretch")
    config_upload = col2.file_uploader("Nhập cấu hình JSON", type=["json"], key="config_json")
    if config_upload and st.button("Nạp cấu hình đã chọn"):
        try:
            st.session_state.settings = nhap_cau_hinh_json(config_upload.getvalue())
            NGUONG.update(st.session_state.settings["nguong"])
            st.session_state.result = None
            st.session_state.docs = {}
            st.session_state.ai_summary = ""
            st.success("Đã nạp cấu hình. API Key không được nhập từ tệp JSON.")
            st.rerun()
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            st.error(f"Không thể nạp cấu hình: {exc}")
    if st.button("Khôi phục cấu hình mặc định"):
        st.session_state.settings = cau_hinh_mac_dinh()
        NGUONG.update(st.session_state.settings["nguong"])
        st.session_state.result = None
        st.session_state.docs = {}
        st.session_state.ai_summary = ""
        st.rerun()

    st.info("Phần này chỉ chỉnh giao diện, prompt và ngưỡng trong từng phiên. Source code phải sửa qua GitHub/Jupyter rồi triển khai lại; web không cho chạy mã tùy ý.")


def chay_ung_dung_streamlit() -> None:
    import streamlit as st

    st.set_page_config(page_title="CreditLens", page_icon="🏦", layout="wide", initial_sidebar_state="expanded")
    if "settings" not in st.session_state:
        st.session_state.settings = cau_hinh_mac_dinh()
    if "result" not in st.session_state:
        st.session_state.result = None
    if "docs" not in st.session_state:
        st.session_state.docs = {}
    if "ai_summary" not in st.session_state:
        st.session_state.ai_summary = ""
    if "api_key_session" not in st.session_state:
        st.session_state.api_key_session = ""

    settings = st.session_state.settings
    NGUONG.update(settings["nguong"])
    hien_thi_header(st, settings)

    st.sidebar.markdown("## CreditLens")
    st.sidebar.markdown(
        "<div class='public-pill'><span class='public-dot'></span> SẴN SÀNG TRIỂN KHAI CÔNG KHAI</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Khi deploy trên cloud, ứng dụng hoạt động độc lập với máy cá nhân.")
    page = st.sidebar.radio("Điều hướng", PAGES)
    st.sidebar.divider()
    if st.sidebar.button("Xóa hồ sơ khỏi phiên", width="stretch"):
        st.session_state.result = None
        st.session_state.docs = {}
        st.session_state.ai_summary = ""
        st.rerun()
    st.sidebar.caption("Ngưỡng minh họa · Không phải chính sách ngân hàng · Bắt buộc con người xem xét")

    result = st.session_state.result
    docs = st.session_state.docs
    if page == "Trang chủ & hồ sơ":
        trang_ho_so(st)
    elif page == "Trích xuất tài liệu":
        trang_trich_xuat(st, result, docs)
    elif page == "Phân tích tín dụng":
        trang_phan_tich(st, result)
    elif page == "Cảnh báo rủi ro":
        trang_rui_ro(st, result)
    elif page == "Tóm tắt thẩm định":
        trang_tom_tat(st, result, settings)
    elif page == "Đánh giá & phương pháp":
        trang_danh_gia(st)
    else:
        trang_cai_dat(st, settings)


# ==========================================================
# 10. TỰ KIỂM TRA NHANH
# ==========================================================

def chay_tu_kiem_tra() -> None:
    normal, _ = du_lieu_demo("CASE-01 — Hồ sơ bình thường")
    mismatch, _ = du_lieu_demo("CASE-03 — Thu nhập không nhất quán")
    missing, _ = du_lieu_demo("CASE-08 — Đơn vay chưa đầy đủ")
    zero_ratio = chia_an_toan(10, 0)
    assert normal.trang_thai == "REVIEW READY"
    assert any(r.loai == "INCOME_MISMATCH" for r in mismatch.canh_bao)
    assert missing.trang_thai == "INSUFFICIENT INFORMATION"
    assert zero_ratio is None
    assert all(r.bang_chung for r in mismatch.canh_bao if r.loai == "INCOME_MISMATCH")
    assert "API" not in json.dumps(cau_hinh_mac_dinh(), ensure_ascii=False)
    assert nhap_cau_hinh_json(b'{"mau_chu_dao":"#112233"}')["mau_chu_dao"] == "#112233"
    docx_data = tao_bao_cao_word(mismatch)
    xlsx_data = tao_bao_cao_excel(mismatch)
    pdf_data = tao_bao_cao_pdf(mismatch)
    assert docx_data[:2] == b"PK" and len(docx_data) > 5_000
    assert xlsx_data[:2] == b"PK" and len(xlsx_data) > 5_000
    assert pdf_data[:5] == b"%PDF-" and len(pdf_data) > 5_000
    print("✅ Tự kiểm tra thành công: quy tắc tín dụng, dữ liệu thiếu, mẫu số bằng 0, bằng chứng, cấu hình và ba định dạng báo cáo.")


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
