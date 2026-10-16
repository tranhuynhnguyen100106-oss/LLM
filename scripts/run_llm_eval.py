#!/usr/bin/env python3
"""Đánh giá OUTPUT LLM THẬT của CreditLens (tác vụ #2 Summary và #1 Extraction) trên hồ sơ PDF tổng hợp.

Cách chạy (khóa của NGƯỜI CHẠY, đọc từ biến môi trường; script không in, không ghi khóa):

    export GEMINI_API_KEY=...            # Windows PowerShell: $env:GEMINI_API_KEY="..."
    python scripts/run_llm_eval.py --model gemini-3.8-flash --cases 12

Mỗi hồ sơ gửi tối đa 3 request, mỗi request 1 tác vụ: Summary có ngữ cảnh JSON; Summary baseline
(prompt chung, không JSON, bỏ bằng --no-baseline); LLM Extraction. Giữa các lần gọi có nghỉ (--sleep)
để tránh 429/503. Không retry tự động; lỗi được ghi mã (GEM-xxx) và chuyển sang hồ sơ tiếp theo.
Output thô (đã giả danh hóa) lưu ở evaluation/llm_outputs/<model>/<case_id>.json kèm model, thời gian, latency.
Sau đó: python -c "from evaluation.llm_live import score_llm_outputs; import json; print(json.dumps(score_llm_outputs(), ensure_ascii=False, indent=2))"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_MODEL = "gemini-3.8-flash"
PROVIDER = "gemini"


def _timed(call: Callable[[], Any]) -> tuple[Any, float, str | None]:
    started = time.perf_counter()
    try:
        value = call()
        return value, round((time.perf_counter() - started) * 1000, 1), None
    except (ValueError, RuntimeError) as exc:
        return None, round((time.perf_counter() - started) * 1000, 1), str(exc)[:300]


def _redact(value: Any, key: str) -> Any:
    text = json.dumps(value, ensure_ascii=False)
    if key and key in text:
        text = text.replace(key, "[REDACTED]")
    return json.loads(text)


def _thang_nam(value: Any) -> Any:
    """Ngày chỉ lưu tháng/năm (giống Privacy Gateway) — không lưu ngày đầy đủ vào repo."""

    from credit_underwriting_colab import chuan_hoa_ngay

    parsed = chuan_hoa_ngay(str(value)) if isinstance(value, str) else None
    return f"{parsed.month:02d}/{parsed.year}" if parsed else value


def chon_ho_so(limit: int) -> list[Any]:
    """12 kịch bản biến thể 'exact' trước (bao phủ mọi nhóm cảnh báo), sau đó 'normalized-equivalent'."""

    from tests.fixtures.synthetic_pdfs import synthetic_cases

    return synthetic_cases()[: max(1, min(limit, 20))]


def danh_gia_mot_ho_so(
    case: Any,
    *,
    key: str,
    model: str,
    sleep: float,
    baseline: bool,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    import credit_underwriting_colab as cu
    import llm_extraction as le
    import privacy_gateway as pg
    from evaluation.dataset import load_gold_cases
    from tests.fixtures.synthetic_pdfs import case_uploads

    result, docs, _errors = cu.xu_ly_thu_muc_tai_lieu(case.case_id, case_uploads(case), None)
    vault = pg.build_vault(pg.detect_pii(docs, result))
    payload = json.loads(cu.du_lieu_gui_llm(result, vault))  # bản giả danh hóa — chỉ bản này được lưu
    gold = next(c for c in load_gold_cases() if c["case_id"] == case.case_id)["ground_truth"]["fields"]
    system = cu.DEFAULT_SYSTEM_PROMPT
    tasks: dict[str, Any] = {}

    raw, latency, error = _timed(lambda: cu.goi_llm_tom_tat_tho(result, key, PROVIDER, model, system, vault))
    tasks["summary"] = {"raw": raw, "latency_ms": latency, "error": error}
    if baseline:
        sleeper(sleep)
        raw, latency, error = _timed(
            lambda: cu.goi_llm_tom_tat_tho(result, key, PROVIDER, model, system, vault, co_ngu_canh=False)
        )
        tasks["summary_baseline"] = {"raw": raw, "latency_ms": latency, "error": error}

    sleeper(sleep)
    fields = list(le.TRUONG_AI)  # đánh giá: yêu cầu mọi trường số/ngày để đo grounding + precision
    pages = le.trang_da_gia_danh(docs, fields, vault)
    connection = {"api_key": key, "provider": PROVIDER, "model": model}
    raw, latency, error = _timed(
        lambda: cu.tao_phan_hoi_chat_ai(
            [{"role": "user", "content": le.noi_dung_yeu_cau(fields, pages)}],
            connection["api_key"],
            PROVIDER,
            model,
            vault,
            system_prompt=le.SYSTEM_PROMPT,
            response_schema=le.gemini_response_schema(),
        )
    )
    items: list[dict[str, Any]] = []
    if raw is not None:
        try:
            items = le.cham_output_trich_xuat(raw, fields, pages, docs)
        except RuntimeError as exc:
            error = str(exc)
    tasks["extraction"] = {
        "raw": raw,
        "latency_ms": latency,
        "error": error,
        "requested": fields,
        "items": [
            {**item, "value": _thang_nam(item["value"])} if le.TRUONG_AI[item["field"]][2] == "date" and "value" in item else item
            for item in items
        ],
        "gold": {field: _thang_nam(gold.get(field)) if le.TRUONG_AI[field][2] == "date" else gold.get(field) for field in fields},
    }
    record = {
        "schema": "creditlens-llm-eval-v1",
        "case_id": case.case_id,
        "scenario": case.scenario,
        "provider": PROVIDER,
        "model": model,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": {"payload": payload, "status": payload.get("trang_thai")},
        "tasks": tasks,
    }
    pg.assert_no_pii(json.dumps({k: v for k, v in record.items() if k != "tasks"} | {"tasks": {
        name: {"raw": entry.get("raw")} for name, entry in tasks.items()}}, ensure_ascii=False), vault)
    return _redact(record, key)


def main(argv: list[str] | None = None, *, sleeper: Callable[[float], None] = time.sleep) -> int:
    parser = argparse.ArgumentParser(description="Đánh giá output LLM thật của CreditLens (không lưu API key).")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--cases", type=int, default=12, help="Số hồ sơ (10–12 khuyến nghị, tối đa 20).")
    parser.add_argument("--sleep", type=float, default=6.0, help="Giây nghỉ giữa các lần gọi (tránh 429/503).")
    parser.add_argument("--no-baseline", action="store_true", help="Bỏ Summary baseline (prompt chung).")
    parser.add_argument("--out", default=str(ROOT / "evaluation" / "llm_outputs"))
    args = parser.parse_args(argv)

    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if len(key) < 12:
        print("Thiếu biến môi trường GEMINI_API_KEY. Ví dụ: export GEMINI_API_KEY=...", file=sys.stderr)
        return 2
    if not all(ch.isalnum() or ch in "-._" for ch in args.model):
        print("Tên model không hợp lệ.", file=sys.stderr)
        return 2

    out_dir = Path(args.out) / args.model
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = chon_ho_so(args.cases)
    print(f"Đánh giá {len(cases)} hồ sơ · model {args.model} · nghỉ {args.sleep}s giữa các lần gọi")
    for index, case in enumerate(cases, start=1):
        if index > 1:
            sleeper(args.sleep)
        record = danh_gia_mot_ho_so(
            case, key=key, model=args.model, sleep=args.sleep, baseline=not args.no_baseline, sleeper=sleeper
        )
        text = json.dumps(record, ensure_ascii=False, indent=2)
        if key in text:  # phòng thủ lần cuối: không bao giờ ghi khóa
            raise SystemExit("Dừng: phát hiện API key trong output.")
        (out_dir / f"{case.case_id}.json").write_text(text + "\n", encoding="utf-8")
        status = {name: ("lỗi " + entry["error"][:60]) if entry.get("error") else f"{entry['latency_ms']} ms"
                  for name, entry in record["tasks"].items()}
        print(f"[{index}/{len(cases)}] {case.case_id}: {status}")

    from evaluation.llm_live import score_llm_outputs

    scored = score_llm_outputs(Path(args.out))
    print(json.dumps(scored["models"].get(args.model, {}), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
