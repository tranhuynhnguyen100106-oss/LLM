import { useEffect, useRef, type KeyboardEvent } from "react";
import { useCreditLens } from "../context/CreditLensContext";

/**
 * Hộp thoại "Hồ sơ còn thiếu thông tin" — bản Streamlit (UI v3).
 * Hiện ngay sau Bước 0 khi hồ sơ thiếu trường bắt buộc, trước khi xem kết quả và trước mọi lệnh gọi LLM.
 * Chỉ hiển thị nhãn trường (không có giá trị). Esc = "Bổ sung tài liệu"; focus mặc định ở nút an toàn đó.
 */
export function MissingFieldGateDialog() {
  const { missingGate, missingGateActions } = useCreditLens();
  const dialogRef = useRef<HTMLDivElement>(null);
  const safeRef = useRef<HTMLButtonElement>(null);
  const open = Boolean(missingGate?.open && missingGateActions);

  const supplement = missingGateActions?.supplementDocuments;
  useEffect(() => {
    if (!open || !dialogRef.current) return;
    const dialog = dialogRef.current;
    // Component Streamlit chạy trong shadow root: lắng nghe trên root chứa hộp thoại và trên document.
    const root = dialog.getRootNode() as Document | ShadowRoot;
    const timer = window.setTimeout(() => safeRef.current?.focus(), 0);
    const inside = (event: Event) => event.composedPath().includes(dialog);
    const keepFocusInside = (event: Event) => {
      if (!inside(event)) safeRef.current?.focus();
    };
    const onEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape" && !inside(event)) {
        event.preventDefault();
        supplement?.();
      }
    };
    root.addEventListener("focusin", keepFocusInside);
    document.addEventListener("keydown", onEscape);
    return () => {
      window.clearTimeout(timer);
      root.removeEventListener("focusin", keepFocusInside);
      document.removeEventListener("keydown", onEscape);
    };
  }, [open, supplement]);

  if (!open || !missingGate || !missingGateActions) return null;

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      missingGateActions.supplementDocuments();
      return;
    }
    if (event.key !== "Tab" || !dialogRef.current) return;
    const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLButtonElement>("button:not([disabled])"));
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <div className="cl-gate-backdrop" role="presentation">
      <div
        ref={dialogRef}
        className="cl-gate-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="cl-gate-title"
        aria-describedby="cl-gate-explanation"
        aria-label={missingGate.title}
        onKeyDown={onKeyDown}
      >
        <header className="cl-gate-dialog__header">
          <p className="cl-core-eyebrow">KIỂM SOÁT ĐỘ TIN CẬY · TRƯỚC KHI ĐÁNH GIÁ</p>
          <h2 id="cl-gate-title">{missingGate.title}</h2>
          <p className="cl-gate-dialog__count">
            {missingGate.required_count} mục bắt buộc còn thiếu. Chưa gọi AI cho hồ sơ này.
          </p>
        </header>

        <div className="cl-gate-dialog__groups">
          {missingGate.groups.map((group) => (
            <section key={group.doc} className="cl-gate-group" aria-label={`Thiếu ở ${group.doc_label}`}>
              <h3>{group.doc_label}</h3>
              <ul>
                {group.items.map((item) => (
                  <li key={item.field}>
                    <span>{item.label}</span>
                    <span className={`cl-gate-level cl-gate-level--${item.level === "Bắt buộc" ? "required" : "recommended"}`}>
                      {item.level}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>

        <p id="cl-gate-explanation" className="cl-gate-dialog__explanation">
          {missingGate.explanation}
        </p>

        <footer className="cl-gate-dialog__actions">
          <button
            ref={safeRef}
            type="button"
            className="cl-demo-panel__action"
            aria-label="Bổ sung tài liệu: quay về Bước 0, giữ các tệp đã tải"
            onClick={missingGateActions.supplementDocuments}
          >
            Bổ sung tài liệu
          </button>
          {missingGate.can_ai ? (
            <button
              type="button"
              className="cl-close-case-btn"
              aria-label="Bổ sung bằng AI: gửi 1 yêu cầu trích xuất các trường số hoặc ngày, chuyên viên xác nhận từng trường"
              onClick={missingGateActions.supplementWithAi}
            >
              Bổ sung bằng AI
            </button>
          ) : null}
          <button
            type="button"
            className="cl-close-case-btn"
            aria-label="Tiếp tục đánh giá khi còn thiếu thông tin, trạng thái do Python tính giữ nguyên"
            onClick={missingGateActions.continueReview}
          >
            Tiếp tục đánh giá
          </button>
          <button
            type="button"
            className="cl-close-case-btn cl-gate-dialog__danger"
            aria-label="Hủy hồ sơ: xóa hồ sơ và vault khỏi phiên"
            onClick={missingGateActions.cancelCase}
          >
            Hủy hồ sơ
          </button>
        </footer>
      </div>
    </div>
  );
}
