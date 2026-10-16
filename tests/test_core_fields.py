"""#5 — Tài liệu bắt buộc có mặt nhưng thiếu trường cốt lõi → INSUFFICIENT; benchmark PDF trong evaluation."""

from __future__ import annotations

import time
import unittest

import credit_underwriting_colab as cu
from evaluation.evaluator import run_evaluation
from tests.fixtures.synthetic_pdfs import case_uploads, synthetic_cases

BEFORE_REVIEW_READY = {"EVAL-013", "EVAL-014", "EVAL-016", "EVAL-017"}


def _result(update: dict, docs: dict | None = None) -> cu.KetQuaThamDinh:
    base, base_docs = cu.du_lieu_demo("CASE-01 — Hồ sơ bình thường", None)
    data = base.du_lieu.model_copy(update=update)
    return cu.phan_tich_tu_du_kien("T", "T", data, base.truong_trich_xuat, docs or base_docs, time.perf_counter(), None)


class CoreFieldTests(unittest.TestCase):
    def test_constant_is_declared_in_one_place(self) -> None:
        self.assertEqual({k for k in cu.TRUONG_COT_LOI_THEO_TAI_LIEU}, {"income", "statement"})

    def test_income_doc_without_salary_is_insufficient(self) -> None:
        result = _result({"luong_thuc_nhan": None})
        self.assertEqual(result.trang_thai, "INSUFFICIENT INFORMATION")
        self.assertIn("Lương thực nhận trên chứng từ thu nhập", result.thong_tin_thieu)

    def test_statement_without_income_or_balance_is_insufficient(self) -> None:
        for field, label in (("thu_nhap_qua_sao_ke", "Thu nhập qua sao kê (ghi có bình quân)"), ("so_du_binh_quan", "Số dư bình quân trên sao kê")):
            with self.subTest(field=field):
                result = _result({field: None})
                self.assertNotEqual(result.trang_thai, "REVIEW READY")
                self.assertEqual(result.trang_thai, "INSUFFICIENT INFORMATION")
                self.assertIn(label, result.thong_tin_thieu)

    def test_unreadable_document_is_still_reported_as_missing_document(self) -> None:
        base, docs = cu.du_lieu_demo("CASE-07 — Sao kê không đọc được", None)
        self.assertIn("Sao kê ngân hàng", base.thong_tin_thieu)
        self.assertNotIn("Số dư bình quân trên sao kê", base.thong_tin_thieu)  # không báo trùng khi cả tài liệu không đọc được

    def test_twenty_pdfs_only_intended_cases_change_and_metrics_identical(self) -> None:
        for case in synthetic_cases():
            result, _, _ = cu.xu_ly_thu_muc_tai_lieu(case.case_id, case_uploads(case), None)
            with self.subTest(case=case.case_id):
                if case.case_id in BEFORE_REVIEW_READY:
                    self.assertEqual(result.trang_thai, "INSUFFICIENT INFORMATION")
                else:
                    self.assertNotIn("Lương thực nhận trên chứng từ thu nhập", result.thong_tin_thieu)

    def test_run_evaluation_includes_pdf_benchmark_and_intentional_errors(self) -> None:
        report = run_evaluation()
        bench = report["pdf_benchmark"]
        self.assertTrue(bench["available"])
        self.assertEqual(bench["case_count"], 20)
        self.assertEqual(bench["extraction_total"], 400)
        self.assertEqual(bench["status_accuracy"], 1.0)
        self.assertEqual(report["reproducibility"]["llm_api_calls"], 0)
        fail11 = next(item for item in report["failure_cases"] if item["case_id"] == "FAIL-11")
        self.assertEqual(fail11["status"], "INTENTIONAL")
        self.assertIn("CÓ CHỦ ĐÍCH", fail11["probable_cause"])
        notes = [d.get("note") for c in __import__("evaluation.dataset", fromlist=["x"]).load_gold_cases() if c["case_id"] in BEFORE_REVIEW_READY for d in c["input_documents"].values()]
        self.assertTrue(any(note and "PDF đọc được nhưng thiếu trường" in note for note in notes))


if __name__ == "__main__":
    unittest.main()
