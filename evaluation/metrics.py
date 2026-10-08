"""Metric implementations for deterministic CreditLens evaluation."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Any, Iterable


STATUS_CLASSES = ["REVIEW READY", "HUMAN REVIEW REQUIRED", "INSUFFICIENT INFORMATION"]
RISK_CLASSES = [
    "INCOME_MISMATCH",
    "EMPLOYER_MISMATCH",
    "POSSIBLE_UNDECLARED_DEBT",
    "JOB_TITLE_MISMATCH",
    "EMPLOYMENT_DATE_MISMATCH",
    "HIGH_DTI_DEMO",
    "HIGH_DSR_DEMO",
    "LOW_BALANCE_BUFFER",
    "HIGH_INCOME_VOLATILITY",
    "LOW_EXTRACTION_CONFIDENCE",
]

DATE_FIELDS = {"ngay_bat_dau_ke_khai", "ngay_bat_dau_chung_tu"}
MONETARY_FIELDS = {
    "thu_nhap_ke_khai",
    "luong_thuc_nhan",
    "thu_nhap_qua_sao_ke",
    "so_tien_de_nghi_vay",
    "khoan_tra_du_kien",
    "nghia_vu_no_ke_khai",
    "nghia_vu_no_quan_sat",
    "chi_phi_sinh_hoat",
    "so_du_binh_quan",
}
INTEGER_FIELDS = {"tham_nien_lam_viec_thang", "thoi_han_vay_thang"}
RATIO_FIELDS = {"bien_dong_thu_nhap"}
DEFAULT_TOLERANCE_CONFIG = {
    "monetary_absolute": 1_000.0,
    "numeric_relative": 0.001,
    "ratio_absolute": 0.001,
}


def safe_divide(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"\s+", " ", text).strip().casefold()


def normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def field_matches(
    field: str,
    predicted: Any,
    expected: Any,
    tolerance_config: dict[str, float] | None = None,
) -> bool:
    tolerances = {**DEFAULT_TOLERANCE_CONFIG, **(tolerance_config or {})}
    if predicted is None or expected is None:
        return predicted is None and expected is None
    if field in DATE_FIELDS:
        return normalize_date(predicted) is not None and normalize_date(predicted) == normalize_date(expected)
    if field in MONETARY_FIELDS:
        try:
            predicted_number = float(predicted)
            expected_number = float(expected)
        except (TypeError, ValueError):
            return False
        tolerance = max(tolerances["monetary_absolute"], abs(expected_number) * tolerances["numeric_relative"])
        return math.isclose(
            predicted_number,
            expected_number,
            rel_tol=tolerances["numeric_relative"],
            abs_tol=tolerance,
        )
    if field in INTEGER_FIELDS:
        try:
            return math.isclose(float(predicted), float(expected), abs_tol=0.0)
        except (TypeError, ValueError):
            return False
    if field in RATIO_FIELDS:
        try:
            return math.isclose(
                float(predicted),
                float(expected),
                rel_tol=tolerances["numeric_relative"],
                abs_tol=tolerances["ratio_absolute"],
            )
        except (TypeError, ValueError):
            return False
    return normalize_text(predicted) == normalize_text(expected)


def extraction_metrics(
    predictions: list[dict[str, Any]],
    golds: list[dict[str, Any]],
    tolerance_config: dict[str, float] | None = None,
) -> dict[str, Any]:
    tolerances = {**DEFAULT_TOLERANCE_CONFIG, **(tolerance_config or {})}
    field_counts: dict[str, Counter[str]] = {}
    total = 0
    correct = 0
    for predicted, expected in zip(predictions, golds, strict=True):
        for field, expected_value in expected.items():
            matched = field_matches(field, predicted.get(field), expected_value, tolerances)
            counts = field_counts.setdefault(field, Counter())
            counts["total"] += 1
            counts["correct"] += int(matched)
            total += 1
            correct += int(matched)
    by_field = []
    for field in sorted(field_counts):
        counts = field_counts[field]
        by_field.append(
            {
                "field": field,
                "correct": counts["correct"],
                "total": counts["total"],
                "accuracy": safe_divide(counts["correct"], counts["total"]),
                "comparison": (
                    "normalized date"
                    if field in DATE_FIELDS
                    else "numeric tolerance"
                    if field in MONETARY_FIELDS | INTEGER_FIELDS | RATIO_FIELDS
                    else "normalized text"
                ),
            }
        )
    return {
        "overall_accuracy": safe_divide(correct, total),
        "correct": correct,
        "total": total,
        "by_field": by_field,
        "tolerances": {
            "monetary_absolute": tolerances["monetary_absolute"],
            "numeric_relative": tolerances["numeric_relative"],
            "ratio_absolute": tolerances["ratio_absolute"],
            "integer": "exact",
            "date": "ISO-normalized",
            "text": "Unicode NFKC + whitespace + casefold",
        },
    }


def _classification_counts(expected: Iterable[str], predicted: Iterable[str]) -> dict[str, int]:
    expected_set = set(expected)
    predicted_set = set(predicted)
    return {
        "tp": len(expected_set & predicted_set),
        "fp": len(predicted_set - expected_set),
        "fn": len(expected_set - predicted_set),
    }


def _scores(tp: int, fp: int, fn: int) -> dict[str, float | None]:
    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)
    f1 = None if precision is None or recall is None or precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def risk_detection_metrics(
    predicted_flags: list[list[str]],
    expected_flags: list[list[str]],
    classes: list[str] | None = None,
) -> dict[str, Any]:
    labels = classes or RISK_CLASSES
    overall = Counter({"tp": 0, "fp": 0, "fn": 0, "tn": 0})
    per_class: list[dict[str, Any]] = []
    for label in labels:
        counts = Counter({"tp": 0, "fp": 0, "fn": 0, "tn": 0})
        for predicted, expected in zip(predicted_flags, expected_flags, strict=True):
            predicted_positive = label in predicted
            expected_positive = label in expected
            if predicted_positive and expected_positive:
                counts["tp"] += 1
            elif predicted_positive:
                counts["fp"] += 1
            elif expected_positive:
                counts["fn"] += 1
            else:
                counts["tn"] += 1
        overall.update(counts)
        per_class.append({"risk": label, **dict(counts), **_scores(counts["tp"], counts["fp"], counts["fn"])})
    return {**dict(overall), **_scores(overall["tp"], overall["fp"], overall["fn"]), "by_risk": per_class}


def status_classification_metrics(predicted: list[str], expected: list[str]) -> dict[str, Any]:
    matrix = {actual: {guess: 0 for guess in STATUS_CLASSES} for actual in STATUS_CLASSES}
    for guess, actual in zip(predicted, expected, strict=True):
        matrix[actual][guess] += 1
    by_class = []
    f1_values = []
    for label in STATUS_CLASSES:
        tp = matrix[label][label]
        fp = sum(matrix[actual][label] for actual in STATUS_CLASSES if actual != label)
        fn = sum(matrix[label][guess] for guess in STATUS_CLASSES if guess != label)
        scores = _scores(tp, fp, fn)
        if scores["f1"] is not None:
            f1_values.append(scores["f1"])
        by_class.append({"status": label, "tp": tp, "fp": fp, "fn": fn, **scores})
    correct = sum(matrix[label][label] for label in STATUS_CLASSES)
    return {
        "accuracy": safe_divide(correct, len(expected)),
        "macro_f1": safe_divide(sum(f1_values), len(f1_values)),
        "confusion_matrix": matrix,
        "by_status": by_class,
    }


def llm_grounding_metrics(
    cases: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    output_name: str,
) -> dict[str, Any]:
    important_total = 0
    important_with_evidence = 0
    claim_total = 0
    unsupported = 0
    factual_total = 0
    factually_consistent = 0
    for case, prediction in zip(cases, predictions, strict=True):
        allowed_evidence = set(case["ground_truth"]["expected_evidence"])
        predicted_risks = set(prediction["risk_flags"])
        comparable = {**prediction["fields"], "status": prediction["status"]}
        for claim in case["saved_llm_outputs"][output_name]:
            claim_total += 1
            refs = claim.get("evidence_refs", [])
            valid_refs = [ref for ref in refs if ref in allowed_evidence]
            if claim.get("important"):
                important_total += 1
                important_with_evidence += int(bool(valid_refs))

            facts = claim.get("facts", {})
            fact_matches = []
            for field, expected_value in facts.items():
                factual_total += 1
                matched = field_matches(field, comparable.get(field), expected_value)
                fact_matches.append(matched)
                factually_consistent += int(matched)
            risk_refs = set(claim.get("risk_refs", []))
            risks_supported = bool(risk_refs) and risk_refs.issubset(predicted_risks)
            facts_supported = bool(fact_matches) and all(fact_matches)
            if not valid_refs and not facts_supported and not risks_supported:
                unsupported += 1
    return {
        "evidence_coverage": safe_divide(important_with_evidence, important_total),
        "unsupported_claim_rate": safe_divide(unsupported, claim_total),
        "factual_consistency": safe_divide(factually_consistent, factual_total),
        "important_claims_with_evidence": important_with_evidence,
        "important_claims": important_total,
        "unsupported_claims": unsupported,
        "claims": claim_total,
        "consistent_facts": factually_consistent,
        "factual_claims": factual_total,
    }
