from __future__ import annotations

import unittest
from copy import deepcopy

from .dataset import load_gold_cases
from .evaluator import _predict_all, report_to_csv, report_to_json, run_evaluation


class EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_gold_cases()
        cls.report = run_evaluation()

    def test_dataset_has_36_independent_synthetic_cases(self) -> None:
        self.assertEqual(len(self.cases), 36)
        self.assertEqual(len({case["case_id"] for case in self.cases}), 36)
        self.assertTrue(all(case["synthetic"] for case in self.cases))
        for case in self.cases:
            self.assertTrue({"fields", "expected_risk_flags", "expected_status", "expected_evidence"}.issubset(case["ground_truth"]))

    def test_prediction_stage_does_not_read_ground_truth(self) -> None:
        class GoldMustNotBeRead:
            def __getattribute__(self, name: str) -> object:
                raise AssertionError("Ground truth was accessed during prediction")

            def __getitem__(self, key: str) -> object:
                raise AssertionError("Ground truth was accessed during prediction")

        case = deepcopy(self.cases[0])
        case["ground_truth"] = GoldMustNotBeRead()
        predictions = _predict_all([case], {})
        self.assertEqual(len(predictions), 1)

    def test_extraction_metrics_have_field_and_overall_scores(self) -> None:
        metrics = self.report["extraction_metrics"]
        self.assertEqual(metrics["total"], 36 * 20)
        self.assertGreater(metrics["overall_accuracy"], 0.90)
        self.assertLess(metrics["overall_accuracy"], 1.0)
        self.assertEqual(len(metrics["by_field"]), 20)

    def test_risk_metrics_include_confusion_counts_and_scores(self) -> None:
        metrics = self.report["risk_detection"]
        for key in ("tp", "fp", "fn", "tn", "precision", "recall", "f1", "by_risk"):
            self.assertIn(key, metrics)
        self.assertGreater(metrics["f1"], 0.0)
        self.assertLess(metrics["f1"], 1.0)

    def test_status_metrics_include_three_class_matrix(self) -> None:
        metrics = self.report["status_classification"]
        self.assertEqual(len(metrics["confusion_matrix"]), 3)
        self.assertEqual(len(metrics["by_status"]), 3)
        self.assertIn("accuracy", metrics)
        self.assertIn("macro_f1", metrics)
        self.assertLess(metrics["accuracy"], 1.0)

    def test_grounding_metrics_use_saved_outputs_without_api(self) -> None:
        metadata = self.report["reproducibility"]
        self.assertEqual(metadata["llm_api_calls"], 0)
        structured = self.report["llm_grounding"]["structured_grounded"]
        generic = self.report["llm_grounding"]["generic_prompt"]
        for key in ("evidence_coverage", "unsupported_claim_rate", "factual_consistency"):
            self.assertIn(key, structured)
            self.assertIn(key, generic)
        self.assertGreater(structured["evidence_coverage"], generic["evidence_coverage"])

    def test_both_baselines_are_reported(self) -> None:
        self.assertIn("baseline_a", self.report["baselines"])
        self.assertIn("baseline_b", self.report["baselines"])

    def test_exactly_ten_failure_cases(self) -> None:
        self.assertEqual(len(self.report["failure_cases"]), 10)
        required = {"case_id", "input", "ground_truth", "actual_output", "failure_type", "probable_cause", "mitigation", "status"}
        self.assertTrue(all(required.issubset(case) for case in self.report["failure_cases"]))

    def test_reproducibility_has_no_api_key(self) -> None:
        metadata = self.report["reproducibility"]
        for key in ("evaluation_run_id", "timestamp", "dataset_version", "app_version", "threshold_config", "provider", "model"):
            self.assertIn(key, metadata)
        self.assertNotIn("api_key", str(self.report).casefold())

    def test_json_and_csv_exports(self) -> None:
        self.assertIn('"dataset_version"', report_to_json(self.report))
        self.assertTrue(report_to_csv(self.report).startswith("metric_path,value"))


if __name__ == "__main__":
    unittest.main()
