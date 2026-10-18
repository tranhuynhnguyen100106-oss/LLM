"""Đọc output LLM THẬT đã lưu (evaluation/llm_outputs/<model>/<case_id>.json) và chấm điểm offline.

Không gọi API. Tách hoàn toàn khỏi số liệu mô phỏng (saved_llm_outputs trong gold_cases).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .metrics import extraction_output_metrics, summary_output_metrics

LLM_OUTPUT_DIR = Path(__file__).resolve().parent / "llm_outputs"
RECORD_SCHEMA = "creditlens-llm-eval-v1"


def load_llm_outputs(root: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    base = Path(root or LLM_OUTPUT_DIR)
    output: dict[str, list[dict[str, Any]]] = {}
    if not base.is_dir():
        return output
    for model_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        records = []
        for path in sorted(model_dir.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(record, dict) and record.get("schema") == RECORD_SCHEMA:
                records.append(record)
        if records:
            output[model_dir.name] = records
    return output


def score_llm_outputs(root: Path | None = None) -> dict[str, Any]:
    loaded = load_llm_outputs(root)
    if not loaded:
        return {
            "available": False,
            "note": "Chưa có output LLM thật. Chạy scripts/run_llm_eval.py bằng khóa Gemini của bạn (đặt trong biến môi trường).",
            "models": {},
        }
    models: dict[str, Any] = {}
    for model, records in loaded.items():
        # Ngày chạy gồm cả lần chạy bù (resumed_at) để nguồn số liệu minh bạch.
        dates = sorted(str(r[k])[:10] for r in records for k in ("run_at", "resumed_at") if r.get(k))
        models[model] = {
            "case_count": len(records),
            "provider": str(records[0].get("provider") or ""),
            "run_dates": [dates[0], dates[-1]] if dates else [],
            "source_note": f"Output LLM thật · model {model} · ngày {dates[0] if dates else 'N/A'}"
            + (f"–{dates[-1]}" if dates and dates[-1] != dates[0] else ""),
            "summary": summary_output_metrics(records, "summary"),
            "summary_baseline_generic": summary_output_metrics(records, "summary_baseline"),
            "extraction": extraction_output_metrics(records),
        }
    return {"available": True, "method": "Chấm offline output LLM thật đã lưu; không gọi API.", "models": models}
