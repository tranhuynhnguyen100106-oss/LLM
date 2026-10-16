"""Lỗi 5xx của Gemini (500/503/504): thông báo rõ là lỗi phía Google, nút Thử lại do người dùng bấm."""

from __future__ import annotations

import json
import logging
import unittest
from typing import Any
from unittest.mock import patch

import httpx

import creditlens_ui_v3 as v3
from tests.test_fix_folder_gemini import MODEL, FakeClient, FakeResponse, chat_ready, ok, send
from tests.test_ui_v3 import SECRET, event

ALT = "gemini-3.1-flash-lite"


def google_error(code: int, status: str) -> FakeResponse:
    return FakeResponse(code, {"error": {"code": code, "status": status, "message": "The model is overloaded. Please try again later."}})


EXPECTED = {
    503: ("UNAVAILABLE", f"Model {MODEL} đang quá tải phía Google (không phải lỗi API Key). Thử lại sau ít phút hoặc chọn model khác. (mã GEM-503)"),
    500: ("INTERNAL", "Gemini gặp lỗi nội bộ khi xử lý yêu cầu. Thử lại sau. (mã GEM-500)"),
    504: ("DEADLINE_EXCEEDED", "Gemini xử lý quá thời gian cho phép. Thử lại hoặc đặt câu hỏi ngắn hơn. (mã GEM-504)"),
}


def retry_event(st: Any, outcome: Any, alt: bool) -> list[dict[str, Any]]:
    retry = st.session_state["v3_chat_messages"][-1]["retry"]
    FakeClient.requests = []
    FakeClient.outcome = outcome
    with patch.object(httpx, "Client", FakeClient):
        v3.handle_v3_event(st, event("chat_retry", retry_id=retry["id"], alt=alt), st.settings)
    return list(FakeClient.requests)


def user_texts(st: Any) -> list[str]:
    return [m["content"] for m in st.session_state["v3_chat_messages"] if m["role"] == "user"]


class Gemini5xxTests(unittest.TestCase):
    def test_messages_log_and_buttons_for_500_503_504(self) -> None:
        for code, (status, expected) in EXPECTED.items():
            with self.subTest(code=code):
                st = chat_ready()
                with self.assertLogs("creditlens.chat", logging.ERROR) as logs:
                    last = send(st, google_error(code, status))
                self.assertEqual(len(FakeClient.requests), 1)  # không tự retry
                self.assertIn(expected, last["content"])
                log = " ".join(logs.output)
                self.assertIn(f"google_status={status}", log)
                self.assertIn(f"model={MODEL}", log)
                self.assertNotIn("The model is overloaded", log)
                self.assertNotIn(SECRET, log)
                chat = v3.build_v3_payload(st, st.settings)["chat"]["messages"][-1]
                self.assertEqual(chat["retry"]["label"], "Gemini 3.8 Flash")
                self.assertEqual(chat["retry"]["alt_label"], "Gemini 3.1 Flash Lite")
                self.assertNotIn(SECRET, json.dumps(chat, ensure_ascii=False))

    def test_non_5xx_errors_have_no_retry_buttons(self) -> None:
        for outcome in (FakeResponse(429, {}), FakeResponse(404, {}), ok([], "MAX_TOKENS")):
            st = chat_ready()
            last = send(st, outcome)
            self.assertNotIn("retry", last)

    def test_retry_same_model_one_request_no_duplicate_user_message(self) -> None:
        st = chat_ready()
        send(st, google_error(503, "UNAVAILABLE"), "DTI bao nhiêu?")
        requests = retry_event(st, ok([{"text": "DTI là 42%."}]), alt=False)
        self.assertEqual(len(requests), 1)
        self.assertIn(f"/models/{MODEL}:generateContent", requests[0]["url"])
        contents = requests[0]["body"]["contents"]
        self.assertEqual([c["role"] for c in contents], ["user"])
        self.assertEqual(contents[0]["parts"][0]["text"], "DTI bao nhiêu?")
        self.assertEqual(user_texts(st), ["DTI bao nhiêu?"])
        self.assertEqual(st.session_state["v3_chat_messages"][-1]["content"], "DTI là 42%.")
        self.assertFalse(any(m.get("retry") for m in st.session_state["v3_chat_messages"]))
        # Lần gửi tiếp theo: lịch sử hợp lệ, không nhân đôi.
        send(st, ok([{"text": "Ổn."}]), "Còn DSR?")
        self.assertEqual([c["role"] for c in FakeClient.requests[0]["body"]["contents"]], ["user", "model", "user"])

    def test_retry_with_alt_model_switches_selected_model(self) -> None:
        st = chat_ready()
        send(st, google_error(503, "UNAVAILABLE"), "hello")
        requests = retry_event(st, ok([{"text": "Chào bạn."}]), alt=True)
        self.assertEqual(len(requests), 1)
        self.assertIn(f"/models/{ALT}:generateContent", requests[0]["url"])
        self.assertEqual(st.session_state["v3_chat_model"], ALT)
        self.assertEqual(v3.build_v3_payload(st, st.settings)["chat"]["model"], ALT)
        self.assertEqual(user_texts(st), ["hello"])

    def test_repeated_or_stale_click_sends_nothing(self) -> None:
        st = chat_ready()
        send(st, google_error(503, "UNAVAILABLE"))
        retry_id = st.session_state["v3_chat_messages"][-1]["retry"]["id"]
        retry_event(st, google_error(503, "UNAVAILABLE"), alt=False)  # lỗi lần 2 → thông báo mới
        self.assertEqual(user_texts(st), ["hello"])
        self.assertEqual(sum(1 for m in st.session_state["v3_chat_messages"] if m.get("notice") and "GEM-503" in m["content"]), 1)
        FakeClient.requests = []
        with patch.object(httpx, "Client", FakeClient):
            v3.handle_v3_event(st, event("chat_retry", retry_id=retry_id, alt=False), st.settings)  # id cũ
            v3.handle_v3_event(st, event("chat_retry", retry_id="bogus", alt=True), st.settings)
        self.assertEqual(FakeClient.requests, [])

    def test_no_alt_button_when_no_other_flash_model(self) -> None:
        st = chat_ready()
        connection = st.session_state["llm_connections"]["gemini"]
        st.session_state["llm_connections"] = {"gemini": {**connection, "models": [MODEL, "gemini-2.5-pro"]}}
        send(st, google_error(503, "UNAVAILABLE"))
        chat = v3.build_v3_payload(st, st.settings)["chat"]["messages"][-1]
        self.assertIsNone(chat["retry"]["alt_label"])
        self.assertEqual(retry_event(st, ok([{"text": "x"}]), alt=True), [])  # nút ẩn → event alt không gửi gì

    def test_ping_5xx_shows_overloaded_badge_other_cases_unchanged(self) -> None:
        st = chat_ready()
        FakeClient.requests = []
        FakeClient.outcome = google_error(503, "UNAVAILABLE")
        with patch.object(httpx, "Client", FakeClient):
            good, detail = v3.kiem_tra_ket_noi_model(st)
        self.assertFalse(good)
        self.assertEqual(len(FakeClient.requests), 1)
        self.assertIn("GEM-503", detail)
        self.assertEqual(v3._ai_connection_status(st)["label"], "Key hợp lệ — model đang quá tải phía Google")
        FakeClient.outcome = FakeResponse(429, {})
        with patch.object(httpx, "Client", FakeClient):
            v3.kiem_tra_ket_noi_model(st)
        self.assertEqual(v3._ai_connection_status(st)["label"], "Key hợp lệ — chưa gọi được model")
        FakeClient.outcome = ok([{"text": "OK"}])
        with patch.object(httpx, "Client", FakeClient):
            v3.kiem_tra_ket_noi_model(st)
        self.assertEqual(v3._ai_connection_status(st)["label"], "Đã kết nối")


if __name__ == "__main__":
    unittest.main()
