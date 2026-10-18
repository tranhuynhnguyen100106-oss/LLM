#!/usr/bin/env python3
"""Đánh giá OUTPUT LLM THẬT của CreditLens (tác vụ #2 Summary và #1 Extraction) trên hồ sơ PDF tổng hợp.

Cách chạy (khóa của NGƯỜI CHẠY, đọc từ biến môi trường; script không in, không ghi khóa):

    export GEMINI_API_KEY=...            # Windows PowerShell: $env:GEMINI_API_KEY="..."
    python scripts/run_llm_eval.py --model gemini-3.8-flash --cases 12

Mỗi hồ sơ gửi tối đa 3 request, mỗi request 1 tác vụ: Summary có ngữ cảnh JSON; Summary baseline
(prompt chung, không JSON, bỏ bằng --no-baseline); LLM Extraction. Giữa các lần gọi có nghỉ (--sleep)
để tránh 429/503. Không retry tự động; lỗi được ghi mã (GEM-xxx) và chuyển sang hồ sơ tiếp theo.
Chạy bù (--resume): đọc output đã lưu, GIỮ NGUYÊN tác vụ đã thành công, chỉ gọi lại tác vụ bị lỗi/thiếu
(tiết kiệm hạn mức). Hồ sơ đã đủ thì bỏ qua, không gửi request nào.
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


def tac_vu_can_chay(existing: Any, baseline: bool) -> list[str]:
    """Tác vụ còn lỗi/thiếu trong output đã lưu (không có output → chạy tất cả)."""

    names = ["summary", *(["summary_baseline"] if baseline else []), "extraction"]
    tasks = existing.get("tasks") if isinstance(existing, dict) else None
    if not isinstance(tasks, dict):
        return names
    return [n for n in names if not isinstance(tasks.get(n), dict) or tasks[n].get("error") or tasks[n].get("raw") is None]


def doc_output_cu(path: Path, case_id: str, model: str) -> dict[str, Any] | None:
    """Output đã lưu của đúng hồ sơ + model (sai schema/hỏng → coi như chưa có)."""

    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    ok = isinstance(record, dict) and record.get("schema") == "creditlens-llm-eval-v1"
    return record if ok and record.get("case_id") == case_id and record.get("model") == model else None


def danh_gia_mot_ho_so(
    case: Any,
    *,
    key: str,
    model: str,
    sleep: float,
    baseline: bool,
    sleeper: Callable[[float], None] = time.sleep,
    existing: dict[str, Any] | None = None,
    pacer: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """``existing``: output đã lưu — tác vụ đã thành công được giữ nguyên, chỉ gọi lại tác vụ lỗi/thiếu.

    ``pacer``: gọi trước MỖI request thật (nghỉ giữa các lần gọi); mặc định nghỉ ``sleep`` giây trừ lần đầu.
    """
    import credit_underwriting_colab as cu
    import privacy_gateway as pg
    from evaluation.dataset import load_gold_cases
    from tests.fixtures.synthetic_pdfs import case_uploads

    result, docs, _errors = cu.xu_ly_thu_muc_tai_lieu(case.case_id, case_uploads(case), None)
    vault = pg.build_vault(pg.detect_pii(docs, result))
    payload = json.loads(cu.du_lieu_gui_llm(result, vault))  # bản giả danh hóa — chỉ bản này được lưu
    gold = next(c for c in load_gold_cases() if c["case_id"] == case.case_id)["ground_truth"]["fields"]
    system = cu.DEFAULT_SYSTEM_PROMPT
    todo = tac_vu_can_chay(existing, baseline)
    old_tasks: dict[str, Any] = dict((existing or {}).get("tasks") or {})
    tasks: dict[str, Any] = {name: old_tasks[name] for name in ("summary", "summary_baseline", "extraction")
                             if name in old_tasks and name not in todo and (baseline or name != "summary_baseline")}
    if pacer is None:
        calls = [0]

        def pacer() -> None:
            if calls[0]:
                sleeper(sleep)
            calls[0] += 1

    if "summary" in todo:
        pacer()
        raw, latency, error = _timed(lambda: cu.goi_llm_tom_tat_tho(result, key, PROVIDER, model, system, vault))
        tasks["summary"] = {"raw": raw, "latency_ms": latency, "error": error}
    if "summary_baseline" in todo:
        pacer()
        raw, latency, error = _timed(
            lambda: cu.goi_llm_tom_tat_tho(result, key, PROVIDER, model, system, vault, co_ngu_canh=False)
        )
        tasks["summary_baseline"] = {"raw": raw, "latency_ms": latency, "error": error}

    if "extraction" in todo:
        tasks["extraction"] = _trich_xuat(key=key, model=model, pacer=pacer, docs=docs, vault=vault, gold=gold)
    tasks = {name: tasks[name] for name in ("summary", "summary_baseline", "extraction") if name in tasks}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record = {
        "schema": "creditlens-llm-eval-v1",
        "case_id": case.case_id,
        "scenario": case.scenario,
        "provider": PROVIDER,
        "model": model,
        "run_at": str((existing or {}).get("run_at") or now),
        "python": {"payload": payload, "status": payload.get("trang_thai")},
        "tasks": tasks,
    }
    if existing is not None:
        record["resumed_at"] = now
        record["resumed_tasks"] = todo
    pg.assert_no_pii(json.dumps({k: v for k, v in record.items() if k != "tasks"} | {"tasks": {
        name: {"raw": entry.get("raw")} for name, entry in tasks.items()}}, ensure_ascii=False), vault)
    return _redact(record, key)


def _trich_xuat(*, key: str, model: str, pacer: Callable[[], None], docs: Any, vault: Any, gold: Any) -> dict[str, Any]:
    import credit_underwriting_colab as cu
    import llm_extraction as le

    pacer()
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
    return {
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


def main(argv: list[str] | None = None, *, sleeper: Callable[[float], None] = time.sleep) -> int:
    parser = argparse.ArgumentParser(description="Đánh giá output LLM thật của CreditLens (không lưu API key).")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--cases", type=int, default=12, help="Số hồ sơ (10–12 khuyến nghị, tối đa 20).")
    parser.add_argument("--sleep", type=float, default=6.0, help="Giây nghỉ giữa các lần gọi (tránh 429/503).")
    parser.add_argument("--no-baseline", action="store_true", help="Bỏ Summary baseline (prompt chung).")
    parser.add_argument("--out", default=str(ROOT / "evaluation" / "llm_outputs"))
    parser.add_argument(
        "--resume", action="store_true",
        help="Chạy bù: giữ tác vụ đã thành công trong output đã lưu, chỉ gọi lại tác vụ lỗi/thiếu.",
    )
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
    mode = " · CHẠY BÙ (chỉ gọi lại tác vụ lỗi/thiếu)" if args.resume else ""
    print(f"Đánh giá {len(cases)} hồ sơ · model {args.model} · nghỉ {args.sleep}s giữa các lần gọi{mode}")
    calls = [0]

    def pacer() -> None:  # nghỉ giữa MỌI lần gọi thật, kể cả giữa các hồ sơ
        if calls[0]:
            sleeper(args.sleep)
        calls[0] += 1

    for index, case in enumerate(cases, start=1):
        path = out_dir / f"{case.case_id}.json"
        existing = doc_output_cu(path, case.case_id, args.model) if args.resume else None
        if existing is not None and not tac_vu_can_chay(existing, not args.no_baseline):
            print(f"[{index}/{len(cases)}] {case.case_id}: giữ nguyên (đã đủ, 0 request)")
            continue
        record = danh_gia_mot_ho_so(
            case, key=key, model=args.model, sleep=args.sleep, baseline=not args.no_baseline, sleeper=sleeper,
            existing=existing, pacer=pacer,
        )
        text = json.dumps(record, ensure_ascii=False, indent=2)
        if key in text:  # phòng thủ lần cuối: không bao giờ ghi khóa
            raise SystemExit("Dừng: phát hiện API key trong output.")
        path.write_text(text + "\n", encoding="utf-8")
        status = {name: ("lỗi " + entry["error"][:60]) if entry.get("error") else f"{entry['latency_ms']} ms"
                  for name, entry in record["tasks"].items()}
        print(f"[{index}/{len(cases)}] {case.case_id}: {status}")

    from evaluation.llm_live import score_llm_outputs

    scored = score_llm_outputs(Path(args.out))
    print(json.dumps(scored["models"].get(args.model, {}), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
