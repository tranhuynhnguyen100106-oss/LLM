import { useCreditLens } from "../context/CreditLensContext";

const STATUS_COPY: Record<string, string> = {
  confirmed: "Đã xác nhận — dùng để tính",
  rejected: "Không tìm thấy căn cứ",
  dismissed: "Đã bỏ qua"
};

/**
 * Trích xuất bổ sung bằng AI (tác vụ LLM #1) — bản Streamlit.
 * Chỉ các trường SỐ/NGÀY regex bỏ sót; 1 request cho cả hồ sơ khi chuyên viên bấm.
 * Giá trị AI chỉ được dùng để tính DTI/DSR sau khi chuyên viên bấm "Xác nhận" từng trường.
 */
export function AiExtractionPanel() {
  const { aiExtraction, aiExtractionActions, openAiSettings } = useCreditLens();
  if (!aiExtraction || !aiExtractionActions) return null;
  const { missing, items, connected, ran, error, running, pending_label } = aiExtraction;
  if (!missing.length && !items.length) return null;
  const pendingFields = new Set(items.filter((i) => i.status === "pending").map((i) => i.field));

  return (
    <section className="cl-ai-extract" aria-labelledby="cl-ai-extract-title">
      <header className="cl-ai-extract__header">
        <div>
          <p className="cl-core-eyebrow">LLM STRUCTURED EXTRACTION</p>
          <h2 id="cl-ai-extract-title">Bổ sung trích xuất bằng AI</h2>
          <p>
            Regex chưa đọc được {missing.length} trường số/ngày. AI chỉ đọc đoạn trích đã giả danh hóa; mỗi giá trị phải có
            trích dẫn nguyên văn trong đúng trang PDF và chỉ được dùng để tính sau khi chuyên viên xác nhận.
          </p>
        </div>
        {connected ? (
          <button
            type="button"
            className="cl-demo-panel__action cl-ai-extract__run"
            disabled={running || !missing.length}
            onClick={() => aiExtractionActions.run()}
          >
            {running ? "Đang trích xuất…" : ran ? "Chạy lại trích xuất AI (1 request)" : "Bổ sung trích xuất bằng AI"}
          </button>
        ) : (
          <button type="button" className="cl-close-case-btn" onClick={() => openAiSettings?.()}>
            Kết nối AI để dùng tính năng này
          </button>
        )}
      </header>

      {missing.length > 0 ? (
        <p className="cl-ai-extract__missing">
          <strong>Trường còn thiếu:</strong> {missing.map((m) => m.label).join(" · ")}
        </p>
      ) : null}
      {error ? (
        <p className="cl-ai-extract__error" role="alert">
          {error}
        </p>
      ) : null}

      {items.length > 0 ? (
        <ul className="cl-ai-extract__list" aria-label="Kết quả trích xuất AI">
          {items.map((item, index) => (
            <li key={`${item.field}-${index}`} className={`cl-ai-extract__item cl-ai-extract__item--${item.status}`}>
              <div className="cl-ai-extract__row">
                <strong>{item.label}</strong>
                <span className={`cl-badge cl-badge--${item.status === "pending" ? "warning" : item.status === "confirmed" ? "success" : "neutral"}`}>
                  {item.status === "pending" ? pending_label : STATUS_COPY[item.status] ?? item.status}
                </span>
              </div>
              {item.status !== "rejected" ? <div className="cl-ai-extract__value">{item.value_display}</div> : null}
              <div className="cl-ai-extract__evidence">
                📄 {item.document}
                {item.page ? ` · trang ${item.page}` : ""} — <q>{item.quote}</q>
              </div>
              {item.status === "rejected" ? <small className="cl-ai-extract__reason">{item.reason}</small> : null}
              {item.status === "pending" && pendingFields.has(item.field) ? (
                <div className="cl-ai-extract__actions">
                  <button type="button" className="cl-demo-panel__action" onClick={() => aiExtractionActions.confirm(item.field)}>
                    Xác nhận
                  </button>
                  <button type="button" className="cl-close-case-btn" onClick={() => aiExtractionActions.reject(item.field)}>
                    Bỏ qua
                  </button>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
