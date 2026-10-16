"""Kiểm thử 2 lỗi: (1) tải cả thư mục hồ sơ + bảng xác nhận phân loại; (2) chat Gemini không phản hồi."""

from __future__ import annotations

import json
import logging
import unittest
from typing import Any
from unittest.mock import patch

import httpx

import credit_underwriting_colab as cu
import creditlens_ui_v3 as v3
import privacy_gateway as pg
from tests.fixtures.synthetic_pdfs import FakeUpload, case_uploads, deterministic_snapshot, synthetic_cases
from tests.test_ui_v3 import SECRET, FakeSt, connect, event, open_demo_through_gateway

MODEL = "gemini-3.8-flash"


class FakeResponse:
    def __init__(self, status: int, payload: Any) -> None:
        self.status_code = status
        self._payload = payload

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeClient:
    """Thay httpx.Client: ghi lại mọi request generateContent, trả phản hồi/ngoại lệ đã định."""

    requests: list[dict[str, Any]] = []
    outcome: Any = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def post(self, url: str, headers: dict[str, str] | None = None, json: Any = None) -> FakeResponse:
        FakeClient.requests.append({"url": url, "headers": dict(headers or {}), "body": json})
        outcome = FakeClient.outcome
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def ok(parts: list[dict[str, Any]], finish: str = "STOP") -> FakeResponse:
    return FakeResponse(200, {"candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": finish}]})


def chat_ready() -> FakeSt:
    st = FakeSt()
    connect(st, models=[MODEL, "gemini-3.1-flash-lite"])
    open_demo_through_gateway(st)
    return st


def send(st: FakeSt, outcome: Any, text: str = "hello") -> dict[str, Any]:
    FakeClient.requests = []
    FakeClient.outcome = outcome
    with patch.object(httpx, "Client", FakeClient):
        v3.handle_v3_event(st, event("chat_send", text=text, role="risk_auditor", model=MODEL), st.settings)
    return st.session_state["v3_chat_messages"][-1]


CASES = {
    "H1 MAX_TOKENS chỉ có thought": (
        ok([{"text": "suy nghĩ nội bộ", "thought": True}], "MAX_TOKENS"),
        "Model dùng hết giới hạn token trước khi trả lời. (mã GEM-MAXTOK)",
    ),
    "H1b MAX_TOKENS không có parts": (
        FakeResponse(200, {"candidates": [{"content": {"role": "model"}, "finishReason": "MAX_TOKENS"}]}),
        "Model dùng hết giới hạn token trước khi trả lời. (mã GEM-MAXTOK)",
    ),
    "H2 404": (FakeResponse(404, {}), f"Model {MODEL} không tồn tại hoặc không khả dụng với key này. (mã GEM-404)"),
    "H2 403": (FakeResponse(403, {}), f"API Key không có quyền dùng model {MODEL}. (mã GEM-403)"),
    "H2 401": (FakeResponse(401, {}), f"API Key không có quyền dùng model {MODEL}. (mã GEM-401)"),
    "H2 429": (FakeResponse(429, {}), "Đã vượt hạn mức/quota của Gemini. Thử lại sau hoặc chọn model khác. (mã GEM-429)"),
    "H3 blockReason": (
        FakeResponse(200, {"promptFeedback": {"blockReason": "SAFETY"}}),
        "Gemini từ chối trả lời vì lý do an toàn (SAFETY). (mã GEM-SAFETY)",
    ),
    "H3 RECITATION": (ok([], "RECITATION"), "Gemini từ chối trả lời vì lý do an toàn (RECITATION). (mã GEM-SAFETY)"),
    "H3 PROHIBITED_CONTENT": (
        ok([], "PROHIBITED_CONTENT"),
        "Gemini từ chối trả lời vì lý do an toàn (PROHIBITED_CONTENT). (mã GEM-SAFETY)",
    ),
    "H5 400": (FakeResponse(400, {}), f"Yêu cầu không hợp lệ với model {MODEL}. (mã GEM-400)"),
    "H7 timeout": (httpx.ReadTimeout("timed out"), "Gemini phản hồi quá lâu (timeout). (mã GEM-TIMEOUT)"),
    "H7 mạng": (httpx.ConnectError("dns"), "Không kết nối được tới Gemini (lỗi mạng). (mã GEM-NET)"),
}


class GeminiErrorTests(unittest.TestCase):
    def test_each_error_shows_specific_message_and_one_request(self) -> None:
        for name, (outcome, expected) in CASES.items():
            with self.subTest(name):
                st = chat_ready()
                with self.assertLogs("creditlens.chat", logging.ERROR) as logs:
                    last = send(st, outcome)
                self.assertEqual(len(FakeClient.requests), 1)  # 1 Send = 1 request, không retry model khác
                self.assertTrue(last.get("notice"))
                self.assertIn(expected, last["content"])
                self.assertNotIn("Không thể nhận phản hồi từ model", last["content"])
                self.assertNotIn("suy nghĩ nội bộ", last["content"])
                self.assertNotIn(SECRET, " ".join(logs.output) + last["content"])
                encoded = json.dumps(v3.build_v3_payload(st, st.settings), ensure_ascii=False)
                self.assertIn(expected, encoded)
                self.assertNotIn(SECRET, encoded)

    def test_h6_privacy_leak_is_not_hidden_behind_generic_message(self) -> None:
        st = chat_ready()
        with patch.object(pg, "assert_no_pii", side_effect=pg.PrivacyLeakError("Chặn gửi: còn PII.")):
            last = send(st, ok([{"text": "x"}]))
        self.assertEqual(FakeClient.requests, [])  # fail-closed: không có request nào
        self.assertIn("Chặn gửi", last["content"])

    def test_thought_parts_are_hidden_only_text_is_shown(self) -> None:
        st = chat_ready()
        last = send(st, ok([{"text": "Đang cân nhắc DTI…", "thought": True}, {"text": "DTI của hồ sơ là **42%**."}]))
        self.assertEqual(last["role"], "assistant")
        self.assertEqual(last["content"], "DTI của hồ sơ là **42%**.")
        body = FakeClient.requests[0]["body"]
        self.assertEqual(body["generationConfig"]["maxOutputTokens"], 8192)
        self.assertEqual(body["generationConfig"]["thinkingConfig"], {"thinkingLevel": "low"})
        self.assertEqual(FakeClient.requests[0]["headers"]["x-goog-api-key"], SECRET)
        self.assertIn(":generateContent", FakeClient.requests[0]["url"])

    def test_history_after_failure_is_valid(self) -> None:
        st = chat_ready()
        send(st, FakeResponse(429, {}), "hello")
        send(st, ok([{"text": "Chào bạn."}]), "DTI bao nhiêu?")
        contents = FakeClient.requests[0]["body"]["contents"]
        roles = [item["role"] for item in contents]
        self.assertEqual(roles[0], "user")
        self.assertTrue(all(a != b for a, b in zip(roles, roles[1:])), roles)
        self.assertEqual(contents[-1]["parts"][0]["text"], "DTI bao nhiêu?")
        self.assertNotIn("hello", json.dumps(contents, ensure_ascii=False))
        send(st, ok([{"text": "Ổn."}]), "Còn DSR?")
        roles = [item["role"] for item in FakeClient.requests[0]["body"]["contents"]]
        self.assertEqual(roles, ["user", "model", "user"])

    def test_history_is_limited_and_starts_with_user(self) -> None:
        messages: list[dict[str, Any]] = [{"role": "assistant", "content": "chào", "notice": True}]
        for i in range(20):
            messages += [{"role": "user", "content": f"q{i}"}, {"role": "assistant", "content": f"a{i}"}]
        messages += [{"role": "user", "content": "lỗi", "failed": True}, {"role": "user", "content": "mới"}]
        turns = v3.lich_su_hop_le(messages)
        self.assertLessEqual(len(turns), v3.CHAT_HISTORY_LIMIT)
        self.assertEqual(turns[0]["role"], "user")
        self.assertEqual(turns[-1], {"role": "user", "content": "mới"})

    def test_summary_generation_uses_same_gemini_config(self) -> None:
        st = chat_ready()
        FakeClient.requests = []
        FakeClient.outcome = ok([{"text": "x", "thought": True}], "MAX_TOKENS")
        with patch.object(httpx, "Client", FakeClient):
            v3.handle_v3_event(st, event("ai_generate"), st.settings)
        self.assertEqual(len(FakeClient.requests), 1)
        self.assertIn("GEM-MAXTOK", st.session_state["v3_toasts"][-1]["description"])


class ModelAndPingTests(unittest.TestCase):
    def test_no_hardcoded_model_list(self) -> None:
        self.assertFalse(hasattr(v3, "MODEL_LABELS"))
        st = FakeSt()
        connect(st, models=["gemini-2.5-flash", "gemini-2.5-pro"])
        models = v3._chat_models(st)
        self.assertEqual([m["id"] for m in models], ["gemini-2.5-flash", "gemini-2.5-pro"])
        self.assertEqual(models[0], {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "badge": "ĐANG DÙNG"})
        self.assertEqual(models[1]["badge"], "KHẢ DỤNG")

    def test_default_falls_back_to_first_flash(self) -> None:
        model, notice = v3.chon_model_mac_dinh("gemini", ["gemini-2.5-pro", "gemini-2.5-flash-lite", "gemini-2.5-flash"])
        self.assertEqual(model, "gemini-2.5-flash-lite")
        self.assertIn("không khả dụng", notice or "")

    def test_thinking_config_by_family(self) -> None:
        self.assertEqual(cu.cau_hinh_sinh_gemini("gemini-2.5-flash")["thinkingConfig"], {"thinkingBudget": 512})
        self.assertNotIn("thinkingConfig", cu.cau_hinh_sinh_gemini("gemini-2.0-flash"))

    def test_badge_partial_until_ping_succeeds(self) -> None:
        st = chat_ready()
        status = v3._ai_connection_status(st)
        self.assertEqual((status["state"], status["label"]), ("partial", "Key hợp lệ — chưa gọi được model"))
        FakeClient.requests = []
        FakeClient.outcome = FakeResponse(429, {})
        with patch.object(httpx, "Client", FakeClient):
            good, detail = v3.kiem_tra_ket_noi_model(st)
        self.assertFalse(good)
        self.assertIn("GEM-429", detail)
        self.assertEqual(len(FakeClient.requests), 1)
        self.assertEqual(v3._ai_connection_status(st)["state"], "partial")
        FakeClient.requests = []
        FakeClient.outcome = ok([{"text": "OK"}])
        with patch.object(httpx, "Client", FakeClient):
            good, _ = v3.kiem_tra_ket_noi_model(st)
        self.assertTrue(good)
        self.assertEqual(len(FakeClient.requests), 1)
        self.assertEqual(FakeClient.requests[0]["body"]["contents"], [{"role": "user", "parts": [{"text": "ping"}]}])
        status = v3._ai_connection_status(st)
        self.assertEqual((status["state"], status["label"]), ("connected", "Đã kết nối"))
        self.assertNotIn(SECRET, json.dumps(v3.build_v3_payload(st, st.settings), ensure_ascii=False))

    def test_building_payload_never_calls_model(self) -> None:
        st = chat_ready()
        FakeClient.requests = []
        with patch.object(httpx, "Client", FakeClient):
            for page in v3.PAGE_KEYS:
                st.session_state["v3_active_page"] = page
                v3.build_v3_payload(st, st.settings)
        self.assertEqual(FakeClient.requests, [])


def folder_uploads(case: Any) -> list[FakeUpload]:
    """4 PDF tổng hợp trong thư mục có thư mục con + 1 .txt + tệp ẩn/hệ thống."""

    files = case_uploads(case)
    sub = {0: "HOSO/", 1: "HOSO/thu_nhap/", 2: "HOSO/ngan_hang/2025/", 3: "HOSO/no/"}
    output = [FakeUpload(sub[i] + upload.name, upload.getvalue()) for i, upload in enumerate(files)]
    output += [
        FakeUpload("HOSO/ghi_chu.txt", b"ghi chu"),
        FakeUpload("HOSO/.DS_Store", b"\x00\x01"),
        FakeUpload("HOSO/thu_nhap/._" + files[1].name, b"%PDF-1.4 resource fork"),
        FakeUpload("HOSO/Thumbs.db", b"x"),
    ]
    return output


class FolderUploadTests(unittest.TestCase):
    def _plan(self, files: list[FakeUpload], mode: str = v3.UPLOAD_MODE_DIRECTORY) -> FakeSt:
        st = FakeSt()
        st.session_state[pg.KEY_CONSENT] = True
        st.session_state["v3_upload_mode"] = mode
        v3.xu_ly_tep_tai_len_v3(st, files, st.settings)
        return st

    def test_folder_gives_exactly_four_pdfs_classified_and_same_metrics(self) -> None:
        case = next(c for c in synthetic_cases() if len(case_uploads(c)) == 4)
        st = self._plan(folder_uploads(case))
        self.assertIsNone(pg.ho_so_cho_xac_nhan(st.session_state))  # chưa vào cổng trước khi xác nhận
        view = v3.upload_plan_view(st.session_state)
        assert view is not None
        self.assertEqual(len(view["rows"]), 4)
        self.assertTrue(all(row["path"].startswith("HOSO/") for row in view["rows"]))
        self.assertIn("HOSO/ngan_hang/2025/" + case_uploads(case)[2].name, [row["path"] for row in view["rows"]])
        self.assertEqual(sorted(row["type"] for row in view["rows"]), sorted(["application", "income", "statement", "debt"]))
        self.assertTrue(all(row["confidence"] >= 0.68 for row in view["rows"]))
        self.assertEqual(len(view["skipped"]), 4)
        self.assertTrue(view["can_continue"])
        encoded = json.dumps(v3.build_v3_payload(st, st.settings), ensure_ascii=False)
        self.assertIn("HOSO/ngan_hang/2025/", encoded)
        v3.handle_v3_event(st, event("upload_continue"), st.settings)
        self.assertIsNotNone(pg.ho_so_cho_xac_nhan(st.session_state))
        self.assertIsNone(v3.upload_plan_view(st.session_state))
        pg.xac_nhan_cong(st)
        folder_result = st.session_state.result

        # Cùng hồ sơ tải từng tệp (chế độ "Tải từng tệp") và qua pipeline per-file trực tiếp.
        st_files = self._plan(case_uploads(case), v3.UPLOAD_MODE_FILES)
        self.assertEqual(v3.upload_plan_view(st_files.session_state)["mode"], "files")
        v3.handle_v3_event(st_files, event("upload_continue"), st_files.settings)
        pg.xac_nhan_cong(st_files)
        mapping = {cu.goi_y_loai_tu_ten_tep(u.name): u for u in case_uploads(case)}
        direct, _, _ = cu.xu_ly_tai_lieu_tai_len("X", mapping, cu.nguong_hieu_luc(None))
        for other in (st_files.session_state.result, direct):
            a, b = deterministic_snapshot(folder_result), deterministic_snapshot(other)
            for key in ("chi_so", "canh_bao", "trang_thai", "thu_nhap_dung_de_tinh"):
                self.assertEqual(json.dumps(a[key], sort_keys=True), json.dumps(b[key], sort_keys=True), key)
        metrics = {m["ma_chi_so"]: m["gia_tri"] for m in deterministic_snapshot(folder_result)["chi_so"]}
        self.assertIsNotNone(metrics.get("dti"))
        self.assertIsNotNone(metrics.get("dsr"))

    def test_duplicates_missing_oversize_and_manual_override(self) -> None:
        case = synthetic_cases()[0]
        files = case_uploads(case)
        dup = FakeUpload("HOSO/ban_sao/" + files[0].name, files[0].getvalue())
        big = FakeUpload("HOSO/scan_lon.pdf", b"%PDF-1.4" + b"0" * (cu.GIOI_HAN_TEP + 1))
        st = self._plan([files[0], dup, files[2], big])
        view = v3.upload_plan_view(st.session_state)
        assert view is not None
        texts = " ".join(issue["text"] for issue in view["issues"])
        self.assertIn("Có 2 tệp cùng loại Đơn đề nghị vay vốn", texts)
        self.assertIn("Thiếu tài liệu bắt buộc: Chứng từ thu nhập", texts)
        self.assertIn("Vượt giới hạn 10 MB", texts)
        self.assertFalse(view["can_continue"])
        v3.handle_v3_event(st, event("upload_continue"), st.settings)
        self.assertIsNone(pg.ho_so_cho_xac_nhan(st.session_state))  # bị chặn khi trùng loại
        dup_id = next(row["id"] for row in view["rows"] if row["path"].startswith("HOSO/ban_sao/"))
        v3.handle_v3_event(st, event("upload_assign", id=dup_id, doc_type="skip"), st.settings)
        v3.handle_v3_event(st, event("upload_assign", id=dup_id, doc_type="BAD"), st.settings)  # bị bỏ qua
        view = v3.upload_plan_view(st.session_state)
        self.assertTrue(view["can_continue"])
        self.assertTrue(next(r for r in view["rows"] if r["id"] == dup_id)["changed"])
        v3.handle_v3_event(st, event("upload_continue"), st.settings)
        self.assertIsNotNone(pg.ho_so_cho_xac_nhan(st.session_state))
        self.assertIn("Thiếu tài liệu bắt buộc", " ".join(t["description"] for t in st.session_state["v3_toasts"]))

    def test_cancel_plan_and_no_llm_call_during_upload(self) -> None:
        FakeClient.requests = []
        with patch.object(httpx, "Client", FakeClient):
            st = self._plan(folder_uploads(synthetic_cases()[1]))
            v3.handle_v3_event(st, event("upload_cancel"), st.settings)
        self.assertEqual(FakeClient.requests, [])
        self.assertIsNone(v3.upload_plan_view(st.session_state))

    def test_path_helpers(self) -> None:
        self.assertEqual(v3.duong_dan_tuong_doi("HOSO∕sub∕a.pdf"), "HOSO/sub/a.pdf")
        self.assertEqual(v3.duong_dan_tuong_doi("./HOSO/../a.pdf"), "HOSO/a.pdf")
        self.assertTrue(v3.la_tep_an_hoac_he_thong("HOSO/.hidden/a.pdf"))
        self.assertTrue(v3.la_tep_an_hoac_he_thong("__MACOSX/a.pdf"))
        self.assertFalse(v3.la_tep_an_hoac_he_thong("HOSO/a.pdf"))


if __name__ == "__main__":
    unittest.main()
