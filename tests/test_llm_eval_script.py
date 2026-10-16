"""#2 — scripts/run_llm_eval.py chạy với Gemini GIẢ LẬP (không key thật), lưu output, chấm điểm offline."""

from __future__ import annotations

import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx

import credit_review_summary as crs
from evaluation.llm_live import score_llm_outputs
from tests.test_fix_folder_gemini import FakeResponse

ROOT = Path(__file__).resolve().parents[1]
MOCK_KEY = "MOCK-ONLY-NOT-A-REAL-KEY-000000000"
spec = importlib.util.spec_from_file_location("run_llm_eval", ROOT / "scripts" / "run_llm_eval.py")
run_llm_eval = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(run_llm_eval)

EXTRACT_LABELS = {
    "Thu nhập kê khai": ("thu_nhap_ke_khai", "application"),
    "Lương thực nhận": ("luong_thuc_nhan", "income"),
    "Bình quân ghi có": ("thu_nhap_qua_sao_ke", "statement"),
    "Số tiền đề nghị vay": ("so_tien_de_nghi_vay", "application"),
}


class SmartGemini:
    """Trả lời theo loại yêu cầu: Summary có JSON → bản trung thực; baseline → số bịa; extraction → đọc từ trang."""

    requests: list[dict[str, Any]] = []

    def __init__(self, *a: Any, **k: Any) -> None:
        pass

    def __enter__(self) -> "SmartGemini":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def post(self, url: str, headers: dict[str, str] | None = None, json: Any = None) -> FakeResponse:
        SmartGemini.requests.append({"url": url, "headers": dict(headers or {}), "body": json})
        text = json["contents"][-1]["parts"][0]["text"]
        if "Các trường cần trích xuất" in text:
            items, doc = [], None
            for line in text.splitlines():
                head = re.match(r"\[TÀI LIỆU (\w+) · trang (\d+)\]", line)
                if head:
                    doc, page = head.group(1), int(head.group(2))
                    continue
                for label, (field, source) in EXTRACT_LABELS.items():
                    if line.startswith(label + ":") and doc == source:
                        value = re.sub(r"\D", "", line.split(":", 1)[1])
                        items.append({"field": field, "value": value, "unit": "VND", "source_doc": doc, "page": page, "quote": line})
            items.append({"field": "so_du_binh_quan", "value": "123456789", "source_doc": "statement", "page": 1,
                          "quote": "Số dư bình quân: 123.456.789 VND"})  # bịa → phải bị loại
            out = {"items": items}
        elif "{" in text and "trang_thai" in text:
            payload = __import__("json").loads(text[text.index("{"):])
            out = crs.ban_tom_tat_tu_ket_qua(payload).model_dump()
        else:
            out = {"tong_quan": "Khách hàng KH_01 có thu nhập ổn định 50 triệu.", "de_nghi_vay": "Vay 1 tỷ.",
                   "tai_chinh_da_xac_minh": "Đã xác minh.", "chi_so": ["DTI 20%"], "kiem_tra_nhat_quan": "Khớp.",
                   "canh_bao": [], "thong_tin_thieu": [], "cau_hoi_xac_minh": [], "bang_chung": [],
                   "trang_thai_xem_xet": "REVIEW READY"}
        return FakeResponse(200, {"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"text": __import__("json").dumps(out, ensure_ascii=False)}]}}]})


class LlmEvalScriptTests(unittest.TestCase):
    def test_requires_env_key_and_never_writes_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            self.assertEqual(run_llm_eval.main(["--out", tmp, "--cases", "1"], sleeper=lambda _s: None), 2)

    def test_mock_run_saves_pseudonymized_outputs_and_scores_them(self) -> None:
        sleeps: list[float] = []
        SmartGemini.requests = []
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"GEMINI_API_KEY": MOCK_KEY}), patch.object(
            httpx, "Client", SmartGemini
        ):
            code = run_llm_eval.main(["--out", tmp, "--cases", "3", "--sleep", "1.5"], sleeper=sleeps.append)
            self.assertEqual(code, 0)
            self.assertEqual(len(SmartGemini.requests), 9)  # 3 hồ sơ × 3 tác vụ, mỗi tác vụ 1 request
            self.assertEqual(len(sleeps), 2 * 3 + 2)  # nghỉ giữa mọi lần gọi
            files = sorted((Path(tmp) / "gemini-3.8-flash").glob("*.json"))
            self.assertEqual([f.stem for f in files], ["EVAL-001", "EVAL-004", "EVAL-007"])
            for path in files:
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(MOCK_KEY, text)
                self.assertNotIn("Nguyễn Minh Anh", text)
                self.assertIn("KH_01", text)
                record = json.loads(text)
                self.assertTrue({"model", "run_at", "tasks"} <= set(record))
                self.assertIsNotNone(record["tasks"]["summary"]["latency_ms"])
            scored = score_llm_outputs(Path(tmp))
        model = scored["models"]["gemini-3.8-flash"]
        self.assertTrue(model["source_note"].startswith("Output LLM thật · model gemini-3.8-flash · ngày"))
        summary, baseline, extraction = model["summary"], model["summary_baseline_generic"], model["extraction"]
        self.assertEqual(summary["numeric_faithfulness"], 1.0)
        self.assertEqual(summary["completeness"], 1.0)
        self.assertEqual(summary["post_check_pass_rate"], 1.0)
        self.assertEqual(summary["guardrail_violation_rate"], 0.0)
        self.assertEqual(summary["risk_coverage"], 1.0)
        self.assertLess(baseline["numeric_faithfulness"], 0.5)
        self.assertEqual(baseline["post_check_pass_rate"], 0.0)
        self.assertLess(extraction["grounding_rate"], 1.0)  # giá trị bịa bị loại
        self.assertEqual(extraction["precision_vs_gold"], 1.0)
        self.assertIsNotNone(extraction["mean_latency_ms"])

        from creditlens_ui_v2 import build_evaluation_page_view_model, serialize_evaluation_page_view_model
        from evaluation.evaluator import run_evaluation

        report = run_evaluation()
        report["llm_live"] = scored
        view = serialize_evaluation_page_view_model(build_evaluation_page_view_model(report=report, theme="light"))
        self.assertIn("Output LLM thật · model gemini-3.8-flash", view["llm_live_note"])
        self.assertEqual([row["variant"] for row in view["llm_live"]],
                         ["Summary · có JSON ngữ cảnh", "BASELINE · prompt chung, không JSON", "LLM Extraction · grounding check"])
        self.assertTrue(any("MÔ PHỎNG" in row["variant"] for row in view["grounding"]))
        self.assertTrue(view["pdf_benchmark"])

    def test_api_error_is_recorded_without_retry(self) -> None:
        calls: list[Any] = []

        class Down(SmartGemini):
            def post(self, url: str, headers: dict[str, str] | None = None, json: Any = None) -> FakeResponse:
                calls.append(url)
                return FakeResponse(503, {"error": {"code": 503, "status": "UNAVAILABLE"}})

        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"GEMINI_API_KEY": MOCK_KEY}), patch.object(
            httpx, "Client", Down
        ):
            self.assertEqual(run_llm_eval.main(["--out", tmp, "--cases", "1", "--no-baseline"], sleeper=lambda _s: None), 0)
            record = json.loads(next((Path(tmp) / "gemini-3.8-flash").glob("*.json")).read_text(encoding="utf-8"))
            scored = score_llm_outputs(Path(tmp))
        self.assertEqual(len(calls), 2)  # Summary + Extraction, không retry
        self.assertIn("GEM-503", record["tasks"]["summary"]["error"])
        self.assertEqual(scored["models"]["gemini-3.8-flash"]["summary"]["errors"], 1)

    def test_evaluation_report_separates_live_from_simulated(self) -> None:
        from evaluation.evaluator import run_evaluation

        report = run_evaluation()
        self.assertIn("MÔ PHỎNG", report["llm_grounding"]["method"])
        self.assertIn("llm_live", report)
        self.assertEqual(report["reproducibility"]["llm_api_calls"], 0)


if __name__ == "__main__":
    unittest.main()
