"""CreditLens Privacy Gateway — Bước 0 · Bảo mật hồ sơ.

Giả danh hóa (pseudonymization/tokenization) thông tin định danh trước khi bất
kỳ dữ liệu nào rời hệ thống sang nhà cung cấp LLM bên ngoài. Không mã hóa toàn
bộ hồ sơ vì LLM cần đọc được số liệu để diễn giải.

Nguyên tắc:
- Vault (map mã ↔ giá trị thật) chỉ nằm trong ``st.session_state``; không ghi
  file, không log, không serialize sang React.
- CCCD/CMND/hộ chiếu, số điện thoại, email, số tài khoản/thẻ được che hoàn toàn
  và KHÔNG lưu giá trị thật: vault chỉ giữ dấu vân tay HMAC theo phiên để
  ``assert_no_pii`` phát hiện rò rỉ.
- Số tiền, tỷ lệ, kỳ hạn được giữ nguyên; phép tính và rule engine luôn chạy
  trên ``KetQuaThamDinh`` gốc, không chạy trên bản đã giả danh hóa.
- Fail-closed: nếu payload còn giá trị thật thì chặn gửi, không gửi bản chưa che.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import logging
import re
import secrets
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping


PRIVACY_LOGGER = logging.getLogger("creditlens.privacy")

PRIVACY_PROMPT_NOTE = (
    "Dữ liệu đã được giả danh hóa. Giữ nguyên các mã như KH_01, DN_A; "
    "không suy đoán danh tính thật."
)
CONSENT_TEXT = (
    "Tôi xác nhận hồ sơ được xử lý theo quy định bảo mật; dữ liệu định danh sẽ được "
    "giả danh hóa trước khi gửi đến dịch vụ AI bên ngoài."
)
PUBLIC_WARNING = (
    "Bản công khai chỉ dành cho dữ liệu tổng hợp hoặc đã ẩn danh. Không tải hồ sơ khách hàng thật."
)
LOCKED_PAGES = (
    "Trích xuất tài liệu",
    "Phân tích tín dụng",
    "Cảnh báo rủi ro",
    "Tóm tắt thẩm định",
)
LOCK_REASON = (
    "Đang khóa: hoàn tất Bước 0 · Bảo mật hồ sơ (xác nhận và giả danh hóa) để mở trang này."
)
CHAT_LOCK_REASON = (
    "Chat đang khóa: hoàn tất Bước 0 · Bảo mật hồ sơ để mọi nội dung gửi AI được giả danh hóa."
)

KEY_VAULT = "privacy_vault"
KEY_PENDING = "privacy_pending"
KEY_DONE = "privacy_gateway_done"
KEY_CONSENT = "privacy_consent"
KEY_SHOW_REAL = "privacy_show_real"
KEY_REPORT_VERSION = "privacy_report_version"
REPORT_VERSIONS = ("Bản giả danh hóa", "Bản đầy đủ")

PII_LABELS = {
    "HO_TEN": "Họ tên khách hàng",
    "NGUOI_LIEN_QUAN": "Họ tên người liên quan",
    "CCCD": "CCCD",
    "CMND": "CMND",
    "HO_CHIEU": "Hộ chiếu",
    "STK": "Số tài khoản",
    "SO_THE": "Số thẻ",
    "SDT": "Số điện thoại",
    "EMAIL": "Email",
    "DIA_CHI": "Địa chỉ",
    "DON_VI": "Đơn vị công tác",
    "NGAY_SINH": "Ngày sinh",
    "NGAY_BAT_DAU": "Ngày bắt đầu làm việc",
    "THU_CONG": "Giá trị che thủ công",
}
# Không lưu giá trị thật; chỉ giữ dấu vân tay HMAC theo phiên.
NON_REVERSIBLE = frozenset({"CCCD", "CMND", "HO_CHIEU", "STK", "SO_THE", "SDT", "EMAIL"})
# Có thể hiện lại cho chuyên viên trong phiên bằng reidentify_for_display.
REVERSIBLE = frozenset({"HO_TEN", "NGUOI_LIEN_QUAN", "DON_VI", "DIA_CHI", "THU_CONG"})
# Giá trị thật bị cấm xuất hiện trong payload gửi LLM.
ASSERTED = REVERSIBLE | {"NGAY_SINH"}
FIXED_MASKS = {
    "CCCD": "[CCCD_ĐÃ_CHE]",
    "CMND": "[CMND_ĐÃ_CHE]",
    "HO_CHIEU": "[HỘ_CHIẾU_ĐÃ_CHE]",
    "SDT": "[SĐT_ĐÃ_CHE]",
    "EMAIL": "[EMAIL_ĐÃ_CHE]",
}


class PrivacyLeakError(RuntimeError):
    """Payload còn thông tin định danh thật; request bị chặn (fail-closed)."""


# ==========================================================
# Chuẩn hóa: bỏ dấu, viết thường, gộp khoảng trắng — giữ nguyên độ dài để map vị trí.
# ==========================================================

def _fold_char(ch: str) -> str:
    if ch in "đĐ":
        return "d"
    if ch in "\n\r":
        return ch
    if ch.isspace():
        return " "
    base = "".join(c for c in unicodedata.normalize("NFD", ch) if unicodedata.category(c) != "Mn")
    lowered = (base or ch).lower()
    return lowered[0] if lowered else ch


def _fold(text: str) -> str:
    """Bản gấp có cùng độ dài với ``unicodedata.normalize('NFC', text)``."""

    return "".join(_fold_char(ch) for ch in text)


def normalize_key(value: str) -> str:
    """Khóa so khớp: bỏ dấu, viết thường, gộp khoảng trắng."""

    return " ".join(_fold(unicodedata.normalize("NFC", value or "")).split())


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def _needle_pattern(value: str) -> re.Pattern[str] | None:
    words = normalize_key(value).split()
    if not words:
        return None
    body = r"\s+".join(re.escape(word) for word in words)
    return re.compile(rf"(?<![0-9a-z]){body}(?![0-9a-z])")


def _contains_value(text: str, value: str) -> bool:
    pattern = _needle_pattern(value)
    return bool(pattern and pattern.search(_fold(_nfc(text))))


def _replace_value(text: str, value: str, replacement: str) -> str:
    pattern = _needle_pattern(value)
    if pattern is None:
        return text
    text = _nfc(text)
    folded = _fold(text)
    pieces: list[str] = []
    cursor = 0
    for match in pattern.finditer(folded):
        pieces.append(text[cursor:match.start()])
        pieces.append(replacement)
        cursor = match.end()
    if not pieces:
        return text
    pieces.append(text[cursor:])
    return "".join(pieces)


# ==========================================================
# Mô hình dữ liệu
# ==========================================================

@dataclass(frozen=True)
class PiiFinding:
    """Một giá trị định danh đã phát hiện. Chỉ ``gia_tri_che``/``ma_thay_the`` được hiển thị."""

    loai: str
    gia_tri_che: str
    ma_thay_the: str
    tai_lieu: str
    trang: int | None
    nguon: str
    bat_buoc: bool = True
    khoa: str = field(default="", repr=False)
    gia_tri: str | None = field(default=None, repr=False)
    van_tay: str | None = field(default=None, repr=False)
    salt: bytes = field(default=b"", repr=False, compare=False)

    @property
    def nhan_loai(self) -> str:
        return PII_LABELS.get(self.loai, self.loai)


class PseudonymVault:
    """Map mã ↔ giá trị thật cho một phiên. Không tuần tự hóa, không in giá trị."""

    __slots__ = ("_salt", "_reversible", "_replacements", "_fingerprints", "_counts", "_audit", "_created_at")

    def __init__(self, salt: bytes | None = None) -> None:
        self._salt = salt or secrets.token_bytes(32)
        self._reversible: dict[str, str] = {}
        self._replacements: dict[str, tuple[str, str, str]] = {}
        self._fingerprints: dict[str, str] = {}
        self._counts: Counter[str] = Counter()
        self._audit: list[dict[str, Any]] = []
        self._created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    @classmethod
    def empty(cls) -> "PseudonymVault":
        return cls()

    def __repr__(self) -> str:
        return f"<PseudonymVault {self.so_truong} trường đã giả danh hóa>"

    __str__ = __repr__

    def __reduce_ex__(self, _protocol: Any) -> Any:
        raise TypeError("PseudonymVault không được tuần tự hóa hoặc sao chép ra ngoài phiên.")

    def __deepcopy__(self, _memo: Any) -> Any:
        raise TypeError("PseudonymVault không được tuần tự hóa hoặc sao chép ra ngoài phiên.")

    # --- ghi ---
    def _fingerprint(self, raw: str) -> str:
        return hmac.new(self._salt, raw.encode("utf-8"), hashlib.sha256).hexdigest()

    def _register(self, finding: PiiFinding) -> None:
        self._counts[finding.loai] += 1
        if finding.loai in NON_REVERSIBLE:
            if finding.van_tay:
                self._fingerprints[finding.van_tay] = finding.loai
            return
        if not finding.gia_tri:
            return
        if finding.loai in REVERSIBLE:
            self._reversible[finding.ma_thay_the] = finding.gia_tri
        self._replacements[normalize_key(finding.gia_tri)] = (finding.gia_tri, finding.ma_thay_the, finding.loai)

    # --- đọc ---
    @property
    def so_truong(self) -> int:
        return int(sum(self._counts.values()))

    @property
    def dem_theo_loai(self) -> dict[str, int]:
        return {PII_LABELS.get(key, key): int(value) for key, value in sorted(self._counts.items())}

    @property
    def nhat_ky(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._audit]

    def ma_cho(self, value: str | None) -> str | None:
        entry = self._replacements.get(normalize_key(value or ""))
        return entry[1] if entry else None

    def _replacement_pairs(self) -> list[tuple[str, str]]:
        pairs = [(real, code) for real, code, _loai in self._replacements.values()]
        return sorted(pairs, key=lambda item: len(normalize_key(item[0])), reverse=True)

    def _asserted_values(self) -> list[tuple[str, str]]:
        return [(real, loai) for real, _code, loai in self._replacements.values() if loai in ASSERTED]

    def _fingerprint_hit(self, raw: str) -> str | None:
        return self._fingerprints.get(self._fingerprint(raw))

    def ghi_nhat_ky(self, su_kien: str, *, provider: str = "", ket_qua: str = "") -> None:
        """Audit chỉ ghi số liệu: số trường theo loại, thời điểm, provider, kết quả assert."""

        entry = {
            "thoi_diem": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "su_kien": su_kien[:60],
            "provider": provider[:40],
            "so_truong": self.so_truong,
            "theo_loai": self.dem_theo_loai,
            "ket_qua": ket_qua[:60],
        }
        self._audit.append(entry)
        del self._audit[:-200]
        PRIVACY_LOGGER.info(
            "PRIVACY_AUDIT event=%s provider=%s fields=%s result=%s",
            entry["su_kien"],
            entry["provider"] or "-",
            entry["so_truong"],
            entry["ket_qua"] or "-",
        )


# ==========================================================
# Che giá trị để hiển thị trong bảng xem trước
# ==========================================================

def _mask_words(value: str) -> str:
    words = value.split()
    if not words:
        return "***"
    return " ".join([words[0], *[word[0] + "*" * max(len(word) - 1, 2) for word in words[1:]]])


def _province(address: str) -> str:
    segment = [part.strip() for part in re.split(r"[,;\n]", address) if part.strip()]
    if not segment:
        return ""
    last = segment[-1]
    folded = normalize_key(last)
    if "ho chi minh" in folded or re.search(r"\bhcm\b", folded):
        return "TP.HCM"
    last = re.sub(r"(?i)^(thành phố|tp\.?|tỉnh)\s*", "", last).strip(" .")
    return last[:40]


def _parse_date(value: str | None) -> date | None:
    text = (value or "").strip()
    for pattern, fmt in (
        (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
        (r"\d{4}/\d{2}/\d{2}", "%Y/%m/%d"),
        (r"\d{1,2}/\d{1,2}/\d{4}", "%d/%m/%Y"),
        (r"\d{1,2}-\d{1,2}-\d{4}", "%d-%m-%Y"),
    ):
        match = re.search(rf"(?<!\d)({pattern})(?!\d)", text)
        if match:
            try:
                return datetime.strptime(match.group(1), fmt).date()
            except ValueError:
                return None
    return None


def _month_year(value: str | None) -> str | None:
    parsed = _parse_date(value)
    if parsed:
        return f"{parsed.month:02d}/{parsed.year}"
    match = re.search(r"(?<!\d)(\d{1,2})[/-](\d{4})(?!\d)", value or "")
    return f"{int(match.group(1)):02d}/{match.group(2)}" if match else None


def _age_group(value: str | None, reference: date | None = None) -> str:
    born = _parse_date(value)
    if born is None:
        return "[NGÀY_SINH_ĐÃ_CHE]"
    today = reference or date.today()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    if age < 0 or age > 120:
        return "[NGÀY_SINH_ĐÃ_CHE]"
    low = (age // 5) * 5
    return f"{low}–{low + 5} tuổi"


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _preview_mask(loai: str, value: str) -> str:
    if loai in {"HO_TEN", "NGUOI_LIEN_QUAN", "DON_VI", "THU_CONG"}:
        return _mask_words(value)
    if loai in {"CCCD", "CMND", "HO_CHIEU"}:
        return "*" * len(re.sub(r"\s", "", value))
    if loai == "SDT":
        return "*" * len(_digits(value))
    if loai == "EMAIL":
        local, _, domain = value.partition("@")
        return f"{local[:1]}***@{domain[:1]}***"
    if loai in {"STK", "SO_THE"}:
        digits = _digits(value)
        return "*" * max(len(digits) - 4, 4) + digits[-4:]
    if loai == "DIA_CHI":
        province = _province(value)
        return f"***, {province}" if province else "***"
    if loai == "NGAY_SINH":
        return "**/**/****"
    if loai == "NGAY_BAT_DAU":
        return f"**/{_month_year(value) or '**/****'}"
    return "***"


# ==========================================================
# Phát hiện PII
# ==========================================================

_LINE_VALUE = r"\s*[:：\-–]\s*([^\n\r|]{1,120})"
_LABELS = {
    "related": ("nguoi lien quan", "nguoi bao lanh", "nguoi dong vay", "nguoi than", "nguoi lien he", "vo/chong", "vo chong", "related person", "guarantor"),
    "name": ("ten khach hang", "ho va ten", "chu tai khoan", "ho ten", "khach hang", "applicant name", "customer name", "account holder"),
    "address": ("dia chi thuong tru", "dia chi lien he", "dia chi", "address"),
    "dob": ("ngay thang nam sinh", "ngay sinh", "date of birth", "dob"),
    "employer": ("don vi cong tac", "noi lam viec", "employer"),
    "start": ("ngay bat dau lam viec", "employment start date", "work start date"),
}
_ACCOUNT_CONTEXT = re.compile(r"(so tai khoan|tai khoan|stk|account|so the|the tin dung|the ghi no|card)")
_CARD_CONTEXT = re.compile(r"(so the|the tin dung|the ghi no|card)")
_CCCD_CONTEXT = re.compile(r"(cccd|can cuoc)")
_CMND_CONTEXT = re.compile(r"(cmnd|chung minh)")
_PASSPORT_CONTEXT = re.compile(r"(ho chieu|passport)")
_MONEY_SUFFIX = re.compile(r"^\s*(vnd|vnđ|đ\b|₫|dong|đồng|trieu|triệu|nghin|nghìn|%)", re.IGNORECASE)

EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\w.,/-])(?:\+84|0)[\s.-]?[35789](?:[\s.-]?\d){8}(?![\w]|[.,/-]\d)")
DIGIT_RUN_RE = re.compile(
    r"(?<![\w.,/-])(\d{4}(?:[ -]\d{4}){2,3}|\d{8,19})(?![\w]|[.,/-]\d)"
)
PASSPORT_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z]\d{7,8}(?![A-Za-z0-9])")
CODE_RE = re.compile(r"^(KH_\d+|NLQ_\d+|DN_[A-Z]+|ĐC_\d+|TC_\d+|TK_\*+\d{4}|THẺ_\*+\d{4}|\[[^\]]+\])")


def _label_regex(kind: str) -> re.Pattern[str]:
    alts = "|".join(re.escape(label) for label in sorted(_LABELS[kind], key=len, reverse=True))
    return re.compile(rf"(?<![0-9a-z])(?:{alts}){_LINE_VALUE}")


_LABEL_RES = {kind: _label_regex(kind) for kind in _LABELS}


def _labeled_values(text: str, kind: str) -> list[tuple[str, int]]:
    """Trả (giá trị gốc, vị trí) cho các dòng có nhãn; dò trên bản gấp, cắt trên bản NFC."""

    text = _nfc(text)
    folded = _fold(text)
    output: list[tuple[str, int]] = []
    for match in _LABEL_RES[kind].finditer(folded):
        raw = text[match.start(1):match.end(1)]
        raw = re.sub(r"\s{2,}.*", "", raw.strip()).strip(" .;,")
        if raw:
            output.append((raw, match.start()))
    return output


def _looks_like_name(value: str) -> bool:
    words = value.split()
    if not 2 <= len(words) <= 6:
        return False
    return all(_fold(word).replace("-", "").isalpha() for word in words) and not CODE_RE.match(value)


def _page_at(text: str, index: int) -> int | None:
    pages = re.findall(r"--- TRANG (\d+) ---", text[: max(index, 0)])
    return int(pages[-1]) if pages else None


def _nearest_context(context: str) -> str | None:
    """Chọn nhãn gần giá trị nhất trong 40 ký tự đứng trước (tránh nhầm nhãn của giá trị khác)."""

    best: tuple[int, str] | None = None
    for kind, pattern in (
        ("card", _CARD_CONTEXT),
        ("account", _ACCOUNT_CONTEXT),
        ("cccd", _CCCD_CONTEXT),
        ("cmnd", _CMND_CONTEXT),
        ("passport", _PASSPORT_CONTEXT),
    ):
        for match in pattern.finditer(context):
            if best is None or match.end() > best[0]:
                best = (match.end(), kind)
    return best[1] if best else None


def _classify_digits(raw: str, context: str, following: str) -> str | None:
    digits = _digits(raw)
    nearest = _nearest_context(context)
    if nearest == "card":
        return "SO_THE" if 13 <= len(digits) <= 19 else "STK"
    if nearest == "account":
        return "STK"
    if nearest == "cccd":
        return "CCCD"
    if nearest == "cmnd":
        return "CMND"
    if len(digits) == 12:
        return "CCCD"
    if len(digits) == 9:
        return "CMND"
    if _MONEY_SUFFIX.match(following):
        return None
    return "STK"


def _scan_patterns(text: str) -> list[tuple[str, str, int, int]]:
    """(loai, giá trị, start, end) cho email/SĐT/CCCD/CMND/hộ chiếu/STK/thẻ."""

    text = _nfc(text)
    folded = _fold(text)
    hits: list[tuple[str, str, int, int]] = []
    taken: list[tuple[int, int]] = []

    def free(start: int, end: int) -> bool:
        return all(end <= a or start >= b for a, b in taken)

    for match in EMAIL_RE.finditer(text):
        hits.append(("EMAIL", match.group(0), match.start(), match.end()))
        taken.append(match.span())
    for match in PHONE_RE.finditer(text):
        if not free(*match.span()):
            continue
        context = folded[max(0, match.start() - 40):match.start()]
        loai = "STK" if _nearest_context(context) in {"account", "card"} else "SDT"
        hits.append((loai, match.group(0), match.start(), match.end()))
        taken.append(match.span())
    for match in PASSPORT_RE.finditer(text):
        context = folded[max(0, match.start() - 40):match.start()]
        if free(*match.span()) and _nearest_context(context) == "passport":
            hits.append(("HO_CHIEU", match.group(0), match.start(), match.end()))
            taken.append(match.span())
    for match in DIGIT_RUN_RE.finditer(text):
        if not free(*match.span()):
            continue
        context = folded[max(0, match.start() - 40):match.start()]
        loai = _classify_digits(match.group(1), context, text[match.end():match.end() + 12])
        if loai:
            hits.append((loai, match.group(1), match.start(), match.end()))
            taken.append(match.span())
    return sorted(hits, key=lambda item: item[2])


class _Assigner:
    """Gán mã nhất quán: cùng giá trị chuẩn hóa → cùng mã trên mọi tài liệu."""

    def __init__(self, salt: bytes, reference: date | None) -> None:
        self.salt = salt
        self.reference = reference
        self.codes: dict[tuple[str, str], str] = {}
        self.counters: Counter[str] = Counter()
        self.findings: dict[tuple[str, str], PiiFinding] = {}

    def _next(self, loai: str, value: str) -> str:
        self.counters[loai] += 1
        n = self.counters[loai]
        if loai == "HO_TEN":
            return f"KH_{n:02d}"
        if loai == "NGUOI_LIEN_QUAN":
            return f"NLQ_{n:02d}"
        if loai == "DON_VI":
            letters = ""
            while n:
                n, rest = divmod(n - 1, 26)
                letters = chr(65 + rest) + letters
            return f"DN_{letters}"
        if loai == "DIA_CHI":
            province = _province(value)
            return f"ĐC_{n:02d} ({province})" if province else f"ĐC_{n:02d}"
        if loai == "THU_CONG":
            return f"TC_{n:02d}"
        if loai in {"STK", "SO_THE"}:
            prefix = "TK" if loai == "STK" else "THẺ"
            return f"{prefix}_****{_digits(value)[-4:]}"
        if loai == "NGAY_SINH":
            return _age_group(value, self.reference)
        if loai == "NGAY_BAT_DAU":
            return _month_year(value) or "[NGÀY_ĐÃ_CHE]"
        return FIXED_MASKS[loai]

    def add(self, loai: str, value: str, tai_lieu: str, trang: int | None, nguon: str, *, bat_buoc: bool = True) -> PiiFinding | None:
        value = _nfc(value).strip()
        if not value or CODE_RE.match(value):
            return None
        if loai in NON_REVERSIBLE:
            raw = value.lower() if loai == "EMAIL" else (_digits(value) or value.upper())
            key = hmac.new(self.salt, raw.encode("utf-8"), hashlib.sha256).hexdigest()
        else:
            key = normalize_key(value)
        identity = (loai, key)
        if identity in self.findings:
            return self.findings[identity]
        code = self._next(loai, value)
        finding = PiiFinding(
            loai=loai,
            gia_tri_che=_preview_mask(loai, value),
            ma_thay_the=code,
            tai_lieu=tai_lieu,
            trang=trang,
            nguon=nguon,
            bat_buoc=bat_buoc,
            khoa=key,
            gia_tri=None if loai in NON_REVERSIBLE else value,
            van_tay=key if loai in NON_REVERSIBLE else None,
            salt=self.salt,
        )
        self.findings[identity] = finding
        return finding


def _documents(tai_lieu: Any) -> list[Any]:
    if tai_lieu is None:
        return []
    if isinstance(tai_lieu, Mapping):
        return [doc for doc in tai_lieu.values() if doc is not None]
    if isinstance(tai_lieu, (list, tuple)):
        return list(tai_lieu)
    return [tai_lieu]


def detect_pii(
    tai_lieu: Any,
    result: Any | None = None,
    *,
    reference_date: date | None = None,
    salt: bytes | None = None,
) -> list[PiiFinding]:
    """Phát hiện kết hợp: (1) giá trị đã trích xuất vào DuLieuHoSo; (2) regex Việt Nam trên văn bản PDF."""

    assigner = _Assigner(salt or secrets.token_bytes(32), reference_date)
    source_of: dict[str, tuple[str, int | None]] = {}
    customer_key = ""
    if result is not None:
        for item in getattr(result, "truong_trich_xuat", []) or []:
            source_of[item.ma_truong] = (item.tai_lieu_nguon, item.trang)
        data = result.du_lieu
        if data.ho_ten_khach_hang:
            customer_key = normalize_key(data.ho_ten_khach_hang)
            assigner.add("HO_TEN", data.ho_ten_khach_hang, *source_of.get("ho_ten_khach_hang", ("DuLieuHoSo", None)), "Dữ liệu trích xuất")
        for key in ("don_vi_cong_tac_ke_khai", "don_vi_cong_tac_chung_tu"):
            value = getattr(data, key)
            if value:
                assigner.add("DON_VI", value, *source_of.get(key, ("DuLieuHoSo", None)), "Dữ liệu trích xuất")
        for key in ("ngay_bat_dau_ke_khai", "ngay_bat_dau_chung_tu"):
            value = getattr(data, key)
            if value:
                assigner.add("NGAY_BAT_DAU", value, *source_of.get(key, ("DuLieuHoSo", None)), "Dữ liệu trích xuất")

    for document in _documents(tai_lieu):
        text = _nfc(str(getattr(document, "van_ban", "") or ""))
        name = str(getattr(document, "ten_tep", "") or "Tài liệu")
        if not text.strip():
            continue
        for value, index in _labeled_values(text, "related"):
            if _looks_like_name(value):
                assigner.add("NGUOI_LIEN_QUAN", value, name, _page_at(text, index), "Regex nhãn")
        for value, index in _labeled_values(text, "name"):
            if not _looks_like_name(value):
                continue
            if not customer_key:
                customer_key = normalize_key(value)
            loai = "HO_TEN" if normalize_key(value) == customer_key else "NGUOI_LIEN_QUAN"
            assigner.add(loai, value, name, _page_at(text, index), "Regex nhãn")
        for value, index in _labeled_values(text, "address"):
            assigner.add("DIA_CHI", value, name, _page_at(text, index), "Regex nhãn")
        for value, index in _labeled_values(text, "dob"):
            if _parse_date(value):
                assigner.add("NGAY_SINH", value, name, _page_at(text, index), "Regex nhãn")
        for value, index in _labeled_values(text, "employer"):
            assigner.add("DON_VI", value, name, _page_at(text, index), "Regex nhãn")
        for value, index in _labeled_values(text, "start"):
            if _month_year(value):
                assigner.add("NGAY_BAT_DAU", value, name, _page_at(text, index), "Regex nhãn")
        for loai, value, start, _end in _scan_patterns(text):
            assigner.add(loai, value, name, _page_at(text, start), "Regex mẫu VN")
    return list(assigner.findings.values())


def them_gia_tri_thu_cong(findings: list[PiiFinding], value: str) -> list[PiiFinding]:
    """Chuyên viên đánh dấu thêm một giá trị cần che; không thể bỏ che trường bắt buộc."""

    value = _nfc(value).strip()
    if len(value) < 2:
        raise ValueError("Giá trị cần che phải có ít nhất 2 ký tự.")
    key = normalize_key(value)
    if any(item.khoa == key for item in findings):
        return list(findings)
    salt = findings[0].salt if findings else secrets.token_bytes(32)
    count = sum(1 for item in findings if item.loai == "THU_CONG") + 1
    manual = PiiFinding(
        loai="THU_CONG",
        gia_tri_che=_preview_mask("THU_CONG", value),
        ma_thay_the=f"TC_{count:02d}",
        tai_lieu="Thêm thủ công",
        trang=None,
        nguon="Chuyên viên",
        bat_buoc=False,
        khoa=key,
        gia_tri=value,
        salt=salt,
    )
    return [*findings, manual]


def bo_gia_tri_thu_cong(findings: list[PiiFinding], ma_thay_the: str) -> list[PiiFinding]:
    """Chỉ cho phép bỏ giá trị thêm thủ công; trường bắt buộc luôn được giữ."""

    return [item for item in findings if item.bat_buoc or item.ma_thay_the != ma_thay_the]


def build_vault(findings: Iterable[PiiFinding]) -> PseudonymVault:
    items = list(findings)
    vault = PseudonymVault(items[0].salt if items and items[0].salt else None)
    for finding in items:
        vault._register(finding)
    return vault


# ==========================================================
# Giả danh hóa
# ==========================================================

def _mask_patterns(text: str, vault: PseudonymVault | None) -> str:
    hits = _scan_patterns(text)
    if not hits:
        return text
    text = _nfc(text)
    pieces: list[str] = []
    cursor = 0
    for loai, value, start, end in hits:
        if start < cursor:
            continue
        pieces.append(text[cursor:start])
        if loai in {"STK", "SO_THE"}:
            prefix = "TK" if loai == "STK" else "THẺ"
            pieces.append(f"{prefix}_****{_digits(value)[-4:]}")
        else:
            pieces.append(FIXED_MASKS[loai])
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


_LABEL_MASKS = {
    "related": "[HỌ_TÊN_ĐÃ_CHE]",
    "name": "[HỌ_TÊN_ĐÃ_CHE]",
    "address": "[ĐỊA_CHỈ_ĐÃ_CHE]",
    "dob": "[NGÀY_SINH_ĐÃ_CHE]",
    "employer": "[ĐƠN_VỊ_ĐÃ_CHE]",
}


def _mask_unknown_labels(text: str) -> str:
    """Che giá trị có nhãn định danh nhưng chưa có trong vault (ví dụ chuyên viên gõ vào chat)."""

    for kind, mask in _LABEL_MASKS.items():
        for value, _index in reversed(_labeled_values(text, kind)):
            if CODE_RE.match(value) or value.startswith(("[", "KH_", "NLQ_", "DN_", "ĐC_", "TC_")):
                continue
            if kind in {"name", "related"} and not _looks_like_name(value):
                continue
            text = _replace_value(text, value, mask)
    return text


def pseudonymize_text(text: str, vault: PseudonymVault | None) -> str:
    """Thay giá trị trong vault bằng mã, rồi che mẫu CCCD/SĐT/email/STK và nhãn còn sót."""

    if not isinstance(text, str) or not text:
        return text
    output = _nfc(text)
    if vault is not None:
        for real, code in vault._replacement_pairs():
            output = _replace_value(output, real, code)
    output = _mask_patterns(output, vault)
    return _mask_unknown_labels(output)


def _walk_strings(value: Any, transform: Any) -> Any:
    if isinstance(value, str):
        return transform(value)
    if isinstance(value, list):
        return [_walk_strings(item, transform) for item in value]
    if isinstance(value, dict):
        return {key: _walk_strings(item, transform) for key, item in value.items()}
    return value


_STRUCTURED_FIELDS = {
    "ho_ten_khach_hang": "HO_TEN",
    "don_vi_cong_tac_ke_khai": "DON_VI",
    "don_vi_cong_tac_chung_tu": "DON_VI",
    "ngay_bat_dau_ke_khai": "NGAY_BAT_DAU",
    "ngay_bat_dau_chung_tu": "NGAY_BAT_DAU",
}


def _structured_value(key: str, value: Any, vault: PseudonymVault) -> Any:
    if not isinstance(value, str) or not value.strip():
        return value
    if _STRUCTURED_FIELDS[key] == "NGAY_BAT_DAU":
        return _month_year(value) or "[NGÀY_ĐÃ_CHE]"
    return vault.ma_cho(value) or "[ĐÃ_CHE]"


def pseudonymize_result(result: Any, vault: PseudonymVault) -> dict[str, Any]:
    """Bản sao JSON đã giả danh hóa; KHÔNG sửa ``result`` gốc. Số tiền/tỷ lệ/kỳ hạn giữ nguyên."""

    data = copy.deepcopy(result.model_dump(mode="json"))
    du_lieu = data.get("du_lieu") or {}
    for key in _STRUCTURED_FIELDS:
        if key in du_lieu:
            du_lieu[key] = _structured_value(key, du_lieu[key], vault)
    for item in data.get("truong_trich_xuat") or []:
        if item.get("ma_truong") in _STRUCTURED_FIELDS:
            item["gia_tri"] = _structured_value(item["ma_truong"], item.get("gia_tri"), vault)
    return _walk_strings(data, lambda text: pseudonymize_text(text, vault))


def reidentify_for_display(text: str, vault: PseudonymVault | None) -> str:
    """Chỉ dùng khi hiển thị cho chuyên viên trong phiên. KHÔNG BAO GIỜ gọi trước khi gửi LLM."""

    if not text or vault is None:
        return text
    output = text
    for code, real in sorted(vault._reversible.items(), key=lambda item: len(item[0]), reverse=True):
        base = code.split(" (", 1)[0]
        pattern = rf"(?<![\w]){re.escape(base)}(?:\s*\([^)]*\))?(?![\w])"
        output = re.sub(pattern, lambda _m, real=real: real, output)
    return output


def assert_no_pii(payload: str, vault: PseudonymVault | None) -> None:
    """Raise ``PrivacyLeakError`` nếu payload còn giá trị thật (fail-closed, không lộ giá trị)."""

    text = _nfc(payload or "")
    leaked: set[str] = set()
    if vault is not None:
        for real, loai in vault._asserted_values():
            if _contains_value(text, real):
                leaked.add(PII_LABELS.get(loai, loai))
    for match in EMAIL_RE.finditer(text):
        leaked.add(PII_LABELS["EMAIL"])
    for match in PHONE_RE.finditer(text):
        context = _fold(text[max(0, match.start() - 40):match.start()])
        leaked.add(PII_LABELS["STK" if _nearest_context(context) in {"account", "card"} else "SDT"])
    for match in DIGIT_RUN_RE.finditer(text):
        raw = _digits(match.group(1))
        hit = vault._fingerprint_hit(raw) if vault is not None else None
        context = _fold(text[max(0, match.start() - 40):match.start()])
        if hit:
            leaked.add(PII_LABELS.get(hit, hit))
        elif _nearest_context(context) is not None:
            leaked.add("Số định danh/tài khoản")
    if leaked:
        if vault is not None:
            vault.ghi_nhat_ky("Chặn request", ket_qua="FAIL: " + ", ".join(sorted(leaked)))
        raise PrivacyLeakError(
            "Đã chặn gửi đến dịch vụ AI: payload còn thông tin định danh chưa giả danh hóa ("
            + ", ".join(sorted(leaked))
            + "). Không có request nào được gửi."
        )


def payload_cho_llm(result: Any, vault: PseudonymVault | None) -> tuple[dict[str, Any], PseudonymVault]:
    """Luôn trả bản giả danh hóa; nếu chưa có vault thì tạo vault tạm từ chính kết quả."""

    active = vault if vault is not None else build_vault(detect_pii(None, result))
    return pseudonymize_result(result, active), active


# ==========================================================
# Trạng thái phiên Streamlit
# ==========================================================

def _get(state: Any, key: str, default: Any = None) -> Any:
    try:
        return state.get(key, default)
    except AttributeError:
        return getattr(state, key, default)


def lay_vault(session_state: Any) -> PseudonymVault | None:
    vault = _get(session_state, KEY_VAULT)
    return vault if isinstance(vault, PseudonymVault) else None


def cong_hoan_tat(session_state: Any) -> bool:
    return bool(_get(session_state, KEY_DONE)) and lay_vault(session_state) is not None and _get(session_state, "result") is not None


def trang_bi_khoa(page: str, session_state: Any) -> bool:
    return page in LOCKED_PAGES and not cong_hoan_tat(session_state)


def dua_vao_cong(st: Any, result: Any, docs: Mapping[str, Any], source: str) -> list[PiiFinding]:
    """Đưa hồ sơ vào Bước 0: quét PII, giữ chờ xác nhận; các bước sau bị khóa đến khi xác nhận."""

    findings = detect_pii(docs, result)
    state = st.session_state
    state[KEY_PENDING] = {"result": result, "docs": dict(docs), "findings": findings, "source": source}
    state[KEY_DONE] = False
    state[KEY_VAULT] = None
    state["result"] = None
    state["docs"] = {}
    state["ai_summary"] = ""
    state["ai_summary_context"] = {}
    return findings


def ho_so_cho_xac_nhan(session_state: Any) -> Mapping[str, Any] | None:
    pending = _get(session_state, KEY_PENDING)
    return pending if isinstance(pending, Mapping) else None


_UPLOAD_KEYS = ("application_pdf", "income_pdf", "statement_pdf", "debt_pdf", "credit_folder_pdfs")


def xac_nhan_cong(st: Any) -> PseudonymVault:
    """'Giả danh hóa và tiếp tục': tạo vault phiên, xóa file tạm, mở khóa các bước sau."""

    state = st.session_state
    pending = ho_so_cho_xac_nhan(state)
    if pending is None:
        raise ValueError("Chưa có hồ sơ chờ giả danh hóa.")
    if not _get(state, KEY_CONSENT):
        raise ValueError("Cần tick xác nhận bảo mật trước khi tiếp tục.")
    vault = build_vault(pending["findings"])
    vault.ghi_nhat_ky("Giả danh hóa hồ sơ", ket_qua="OK")
    from credit_underwriting_colab import cap_nhat_ho_so_phien

    cap_nhat_ho_so_phien(st, pending["result"], dict(pending["docs"]))
    state[KEY_VAULT] = vault
    state[KEY_DONE] = True
    state["ui_v2_case_source"] = str(pending.get("source") or "")
    state[KEY_PENDING] = None
    for key in _UPLOAD_KEYS:
        try:
            if key in state:
                del state[key]
        except Exception:
            pass
    return vault


def xoa_ho_so_phien(session_state: Any) -> None:
    """'Xóa hồ sơ khỏi phiên' — xóa kết quả, tài liệu, diễn giải AI, hồ sơ chờ và vault."""

    for key, value in (
        ("result", None),
        ("docs", {}),
        ("ai_summary", ""),
        ("ai_summary_context", {}),
        (KEY_PENDING, None),
        (KEY_VAULT, None),
        (KEY_DONE, False),
        (KEY_SHOW_REAL, False),
    ):
        session_state[key] = value


def bang_xem_truoc(findings: Iterable[PiiFinding]) -> list[dict[str, Any]]:
    """Bảng xem trước chỉ gồm giá trị ĐÃ CHE — an toàn để hiển thị và gửi sang React."""

    return [
        {
            "loai": item.nhan_loai,
            "gia_tri_che": item.gia_tri_che,
            "ma_thay_the": item.ma_thay_the,
            "tai_lieu": item.tai_lieu,
            "trang": item.trang,
            "nguon": item.nguon,
            "bat_buoc": item.bat_buoc,
        }
        for item in findings
    ]


def nhan_huy_hieu(session_state: Any) -> tuple[str, str, int]:
    """(state, label, count) cho huy hiệu trên App Shell."""

    vault = lay_vault(session_state)
    if cong_hoan_tat(session_state) and vault is not None:
        return "done", f"Đã giả danh hóa · {vault.so_truong} trường", vault.so_truong
    pending = ho_so_cho_xac_nhan(session_state)
    if pending is not None:
        count = len(pending["findings"])
        return "review", f"Chờ xác nhận · {count} trường", count
    return "pending", "Chưa qua Bước 0", 0


# ==========================================================
# Báo cáo và hiển thị cho chuyên viên
# ==========================================================

def ket_qua_cho_bao_cao(
    result: Any,
    ai_text: str,
    vault: PseudonymVault | None,
    phien_ban: str,
) -> tuple[Any, str]:
    """'Bản giả danh hóa' (mặc định) dùng bản sao đã che; 'Bản đầy đủ' giữ nguyên dữ liệu gốc."""

    if phien_ban == REPORT_VERSIONS[1]:
        return result, reidentify_for_display(ai_text or "", vault)
    payload, active = payload_cho_llm(result, vault)
    return type(result).model_validate(payload), pseudonymize_text(ai_text or "", active)


# ==========================================================
# UI Streamlit native (dùng chung legacy và UI v2)
# ==========================================================

def hien_thi_xac_nhan_bao_mat(st: Any, *, show_warning: bool = True) -> bool:
    if show_warning:
        st.warning(PUBLIC_WARNING, icon="⚠️")
    return bool(st.checkbox(CONSENT_TEXT, key=KEY_CONSENT))


def hien_thi_xem_truoc_va_xac_nhan(st: Any, *, v2_mode: bool = False) -> bool:
    """Bảng xem trước (legacy), thêm che thủ công, nút 'Giả danh hóa và tiếp tục'. Trả True khi cần rerun."""

    state = st.session_state
    pending = ho_so_cho_xac_nhan(state)
    if pending is None:
        if cong_hoan_tat(state):
            _state, label, _count = nhan_huy_hieu(state)
            st.success(f"{label}. Các bước sau đã được mở khóa.", icon="🔒")
        else:
            st.caption("Chưa có hồ sơ chờ giả danh hóa. Tải tài liệu hoặc mở hồ sơ minh họa để bắt đầu.")
        if v2_mode and (cong_hoan_tat(state) or _get(state, "result") is not None):
            if st.button("Xóa hồ sơ khỏi phiên", width="stretch", key="privacy_clear_case"):
                xoa_ho_so_phien(state)
                return True
        return False

    findings: list[PiiFinding] = list(pending["findings"])
    st.subheader("Bảng xem trước thông tin định danh")
    st.caption(
        f"Đã phát hiện {len(findings)} giá trị cần che. Bảng chỉ hiển thị giá trị đã che; "
        "các trường bắt buộc không thể bỏ che."
    )
    if not v2_mode:
        st.dataframe(
            [
                {
                    "Loại PII": row["loai"],
                    "Giá trị đã che": row["gia_tri_che"],
                    "Mã thay thế": row["ma_thay_the"],
                    "Tài liệu/trang": f"{row['tai_lieu']} · tr. {row['trang'] or '—'}",
                    "Bắt buộc": "Có" if row["bat_buoc"] else "Thủ công",
                }
                for row in bang_xem_truoc(findings)
            ],
            hide_index=True,
            width="stretch",
        )
    with st.form("privacy_manual_mask", clear_on_submit=True):
        manual_value = st.text_input(
            "Đánh dấu thêm một giá trị cần che (thủ công)",
            max_chars=120,
            help="Giá trị được thay bằng mã TC_xx trong mọi dữ liệu gửi AI. Không hiển thị lại giá trị này.",
        )
        if st.form_submit_button("Thêm vào danh sách che"):
            try:
                pending["findings"] = them_gia_tri_thu_cong(findings, manual_value)
                state[KEY_PENDING] = dict(pending)
                return True
            except ValueError as exc:
                st.error(str(exc))
    manual_codes = [item.ma_thay_the for item in findings if not item.bat_buoc]
    if manual_codes:
        remove_columns = st.columns([3, 1])
        chosen = remove_columns[0].selectbox("Bỏ giá trị thêm thủ công", manual_codes, key="privacy_manual_remove")
        if remove_columns[1].button("Bỏ", key="privacy_manual_remove_button"):
            pending["findings"] = bo_gia_tri_thu_cong(findings, chosen)
            state[KEY_PENDING] = dict(pending)
            return True

    consent = bool(_get(state, KEY_CONSENT))
    if not consent:
        st.caption("Tick ô xác nhận bảo mật để bật nút giả danh hóa.")
    if st.button(
        "Giả danh hóa và tiếp tục",
        type="primary",
        width="stretch",
        disabled=not consent,
        key="privacy_confirm",
    ):
        try:
            xac_nhan_cong(st)
            if v2_mode:
                state["ui_v2_notice"] = "Đã giả danh hóa. Các trang phân tích và bằng chứng đã được mở khóa."
                state["ui_v2_error"] = ""
            return True
        except ValueError as exc:
            st.error(str(exc))
    if st.button("Hủy hồ sơ đang chờ", width="stretch", key="privacy_cancel"):
        xoa_ho_so_phien(state)
        return True
    return False


def hien_thi_trang_bi_khoa(st: Any) -> None:
    st.warning(LOCK_REASON, icon="🔒")


def chon_phien_ban_bao_cao(st: Any) -> str:
    return str(
        st.radio(
            "Phiên bản báo cáo",
            list(REPORT_VERSIONS),
            index=0,
            horizontal=True,
            key=KEY_REPORT_VERSION,
            help="Mặc định là bản giả danh hóa. Bản đầy đủ chỉ dùng nội bộ trong phiên.",
        )
    )


def hien_thi_noi_dung_ai(st: Any, text: str, vault: PseudonymVault | None, *, key: str) -> None:
    """Mặc định hiển thị dạng mã; 'Hiện thông tin thật' chỉ áp dụng trong phiên."""

    if not text:
        return
    show_real = bool(st.toggle("Hiện thông tin thật (chỉ trong phiên)", key=key, value=False))
    st.markdown(reidentify_for_display(text, vault) if show_real else text)
