"""Offline runner for CreditLens model/pipeline evaluation."""

from __future__ import annotations

import csv
import io
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from credit_underwriting_colab import (
    BangChung,
    DuLieuHoSo,
    NGUONG,
    TaiLieu,
    TruongTrichXuat,
    nguong_hieu_luc,
    phan_tich_tu_du_kien,
)

from .dataset import DATASET_VERSION, load_gold_cases
from .failure_cases import build_failure_cases
from .metrics import (
    extraction_metrics,
    llm_grounding_metrics,
    risk_detection_metrics,
    status_classification_metrics,
)


EVALUATION_VERSION = "creditlens-evaluation-v1.0"
CROSS_DOCUMENT_RISKS = {
    "INCOME_MISMATCH",
    "EMPLOYER_MISMATCH",
    "POSSIBLE_UNDECLARED_DEBT",
    "JOB_TITLE_MISMATCH",
    "EMPLOYMENT_DATE_MISMATCH",
}


FIELD_SOURCES = {
    "ho_ten_khach_hang": "application",
    "don_vi_cong_tac_ke_khai": "application",
    "don_vi_cong_tac_chung_tu": "income",
    "chuc_danh_ke_khai": "application",
    "chuc_danh_chung_tu": "income",
    "ngay_bat_dau_ke_khai": "application",
    "ngay_bat_dau_chung_tu": "income",
    "tham_nien_lam_viec_thang": "application",
    "thu_nhap_ke_khai": "application",
    "luong_thuc_nhan": "income",
    "thu_nhap_qua_sao_ke": "statement",
    "so_tien_de_nghi_vay": "application",
    "thoi_han_vay_thang": "application",
    "khoan_tra_du_kien": "application",
    "nghia_vu_no_ke_khai": "application",
    "nghia_vu_no_quan_sat": "debt",
    "chi_phi_sinh_hoat": "application",
    "so_du_binh_quan": "statement",
    "bien_dong_thu_nhap": "statement",
    "muc_dich_vay": "application",
}


def _resolve_app_version(explicit_version: str | None) -> str:
    if explicit_version:
        return explicit_version
    for key in ("STREAMLIT_GIT_COMMIT", "GIT_COMMIT", "RENDER_GIT_COMMIT"):
        if os.environ.get(key):
            return str(os.environ[key])[:40]
    git_dir = Path(__file__).resolve().parents[1] / ".git"
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            return (git_dir / head[5:]).read_text(encoding="utf-8").strip()[:40]
        if head:
            return head[:40]
    except (OSError, UnicodeError):
        pass
    return EVALUATION_VERSION


def _documents(case: dict[str, Any]) -> dict[str, TaiLieu]:
    output: dict[str, TaiLieu] = {}
    for document_type, descriptor in case["input_documents"].items():
        output[document_type] = TaiLieu(
            loai_ky_vong=document_type,
            ten_tep=descriptor["file_name"],
            van_ban="Synthetic evaluation fixture",
            so_trang=1,
            dung_luong=1,
            trang_thai=descriptor["status"],
            loai_nhan_dien=document_type,
            do_tin_cay=0.95 if descriptor["status"] == "Đã trích xuất" else 0.0,
            loi=None if descriptor["status"] == "Đã trích xuất" else "Synthetic missing/unreadable fixture",
        )
    return output


def _fields(case: dict[str, Any]) -> list[TruongTrichXuat]:
    output = []
    for field, value in case["extracted_input"].items():
        source = FIELD_SOURCES.get(field, "application")
        descriptor = case["input_documents"].get(source, {})
        if value is None or descriptor.get("status") != "Đã trích xuất":
            evidence = None
            source_name = "Không tìm thấy"
            confidence = 0.95
        else:
            source_name = descriptor["file_name"]
            confidence = 0.95
            evidence = BangChung(
                tai_lieu=source_name,
                trang=1,
                truong_du_lieu=field,
                gia_tri=str(value),
                trich_doan="Synthetic evaluation evidence",
            )
        output.append(
            TruongTrichXuat(
                ma_truong=field,
                nhan=field,
                gia_tri=value,
                tai_lieu_nguon=source_name,
                trang=1 if evidence else None,
                do_tin_cay=confidence,
                bang_chung=evidence,
            )
        )
    return output


def _predict_all(cases: list[dict[str, Any]], thresholds: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Create and persist every prediction before any gold label is inspected."""
    predictions = []
    for case in cases:
        predicted_fields = dict(case["extracted_input"])
        data = DuLieuHoSo(**predicted_fields)
        result = phan_tich_tu_du_kien(
            case["case_id"],
            case["scenario"],
            data,
            _fields(case),
            _documents(case),
            time.perf_counter(),
            thresholds,
        )
        predictions.append(
            {
                "case_id": case["case_id"],
                "fields": predicted_fields,
                "risk_flags": [risk.loai for risk in result.canh_bao],
                "status": result.trang_thai,
                "missing_information": list(result.thong_tin_thieu),
                "processing_time_ms": result.thoi_gian_xu_ly_ms,
            }
        )
    return predictions


def _baseline_without_cross_document(prediction: dict[str, Any]) -> dict[str, Any]:
    risks = [risk for risk in prediction["risk_flags"] if risk not in CROSS_DOCUMENT_RISKS]
    if prediction["status"] == "INSUFFICIENT INFORMATION":
        status = "INSUFFICIENT INFORMATION"
    elif risks:
        status = "HUMAN REVIEW REQUIRED"
    else:
        status = "REVIEW READY"
    return {"risk_flags": risks, "status": status}


def run_evaluation(
    threshold_config: Mapping[str, Any] | None = None,
    extraction_tolerance_config: dict[str, float] | None = None,
    provider: str = "not-used",
    model: str = "deterministic-saved-output",
    app_version: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    cases = load_gold_cases()
    thresholds = nguong_hieu_luc(threshold_config or NGUONG)

    # Evaluation invariant: inference first; gold labels are read only afterward.
    predictions = _predict_all(cases, thresholds)
    gold_fields = [case["ground_truth"]["fields"] for case in cases]
    expected_risks = [case["ground_truth"]["expected_risk_flags"] for case in cases]
    expected_status = [case["ground_truth"]["expected_status"] for case in cases]
    predicted_risks = [prediction["risk_flags"] for prediction in predictions]
    predicted_status = [prediction["status"] for prediction in predictions]

    extraction = extraction_metrics(
        [prediction["fields"] for prediction in predictions],
        gold_fields,
        extraction_tolerance_config,
    )
    risk_metrics = risk_detection_metrics(predicted_risks, expected_risks)
    status_metrics = status_classification_metrics(predicted_status, expected_status)
    grounded = llm_grounding_metrics(cases, predictions, "structured_grounded")
    generic = llm_grounding_metrics(cases, predictions, "generic_prompt")

    baseline_predictions = [_baseline_without_cross_document(prediction) for prediction in predictions]
    baseline_a_risk = risk_detection_metrics(
        [prediction["risk_flags"] for prediction in baseline_predictions],
        expected_risks,
    )
    baseline_a_status = status_classification_metrics(
        [prediction["status"] for prediction in baseline_predictions],
        expected_status,
    )

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    run_id = str(uuid.uuid4())
    report = {
        "reproducibility": {
            "evaluation_run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset_version": DATASET_VERSION,
            "evaluation_version": EVALUATION_VERSION,
            "app_version": _resolve_app_version(app_version),
            "threshold_config": thresholds,
            "extraction_tolerance_config": extraction["tolerances"],
            "provider": provider,
            "model": model,
            "llm_api_calls": 0,
        },
        "dataset_summary": {
            "case_count": len(cases),
            "scenario_count": len({case["scenario"] for case in cases}),
            "synthetic_case_count": sum(bool(case["synthetic"]) for case in cases),
            "variants": sorted({case["variant"] for case in cases}),
            "scope_note": "Synthetic/anonymized fixtures; metrics do not establish production performance.",
        },
        "extraction_metrics": extraction,
        "risk_detection": risk_metrics,
        "status_classification": status_metrics,
        "llm_grounding": {
            "method": "Deterministic scoring over saved annotated outputs; no inference request.",
            "structured_grounded": grounded,
            "generic_prompt": generic,
        },
        "baselines": {
            "baseline_a": {
                "name": "Current multi-document rules vs no cross-document checks",
                "current": {
                    "risk_precision": risk_metrics["precision"],
                    "risk_recall": risk_metrics["recall"],
                    "risk_f1": risk_metrics["f1"],
                    "status_accuracy": status_metrics["accuracy"],
                    "status_macro_f1": status_metrics["macro_f1"],
                },
                "no_cross_document": {
                    "risk_precision": baseline_a_risk["precision"],
                    "risk_recall": baseline_a_risk["recall"],
                    "risk_f1": baseline_a_risk["f1"],
                    "status_accuracy": baseline_a_status["accuracy"],
                    "status_macro_f1": baseline_a_status["macro_f1"],
                },
            },
            "baseline_b": {
                "name": "Structured + evidence output vs generic prompt saved output",
                "structured_grounded": grounded,
                "generic_prompt": generic,
                "note": "Reuses saved fixtures; no automatic provider call.",
            },
        },
        "processing_time": {
            "evaluation_runtime_ms": elapsed_ms,
            "creditlens_processing_time_ms": round(sum(item["processing_time_ms"] for item in predictions), 2),
            "mean_case_runtime_ms": round(sum(item["processing_time_ms"] for item in predictions) / len(predictions), 2),
            "manual_processing_time": "N/A – requires user study",
            "time_saved_percentage": "N/A – requires user study",
        },
        "failure_cases": build_failure_cases(predictions, cases),
        "limitations": [
            "Dataset is synthetic/anonymized and small; results are regression evidence, not production validation.",
            "PDF OCR and complex table extraction require a separately labeled document benchmark.",
            "LLM grounding uses saved annotated outputs and does not measure live provider variability.",
            "No measured manual baseline exists; time-saving claims remain N/A pending a user study.",
            "Thresholds are illustrative and are not a bank credit policy.",
        ],
        "overall_summary": {
            "extraction_accuracy": extraction["overall_accuracy"],
            "risk_f1": risk_metrics["f1"],
            "status_accuracy": status_metrics["accuracy"],
            "status_macro_f1": status_metrics["macro_f1"],
            "grounded_evidence_coverage": grounded["evidence_coverage"],
            "grounded_unsupported_claim_rate": grounded["unsupported_claim_rate"],
            "grounded_factual_consistency": grounded["factual_consistency"],
        },
        "case_results": [
            {
                "case_id": case["case_id"],
                "scenario": case["scenario"],
                "variant": case["variant"],
                "expected_risks": case["ground_truth"]["expected_risk_flags"],
                "predicted_risks": prediction["risk_flags"],
                "expected_status": case["ground_truth"]["expected_status"],
                "predicted_status": prediction["status"],
            }
            for case, prediction in zip(cases, predictions, strict=True)
        ],
    }
    return report


def report_to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


def report_to_csv(report: dict[str, Any]) -> str:
    """Flatten report sections into a portable two-column CSV."""
    rows: list[tuple[str, Any]] = []

    def visit(path: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                visit(f"{path}.{key}" if path else str(key), child)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(f"{path}[{index}]", child)
        else:
            rows.append((path, value))

    visit("", report)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["metric_path", "value"])
    writer.writerows(rows)
    return stream.getvalue()
