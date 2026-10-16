import { useState, type FormEvent } from "react";
import { useCreditLens } from "../context/CreditLensContext";

const STATE_COPY = {
  empty: {
    title: "Chưa có hồ sơ qua cổng",
    detail: "Tick xác nhận bảo mật, sau đó tải thư mục 3–4 PDF, từng tài liệu hoặc mở một hồ sơ minh họa."
  },
  review: {
    title: "Kiểm tra bảng xem trước",
    detail: "Các bước sau đang khóa. Rà soát giá trị đã che rồi bấm “Giả danh hóa và tiếp tục”."
  },
  done: {
    title: "Đã giả danh hóa",
    detail: "Mọi dữ liệu gửi dịch vụ AI chỉ dùng mã thay thế. Vault chỉ nằm trong phiên máy chủ Python."
  }
} as const;

/**
 * Bước 0 · Bảo mật hồ sơ (Privacy Gateway) — chỉ hiển thị giá trị ĐÃ CHE và mã thay thế.
 * Toàn bộ logic phát hiện/giả danh hóa nằm ở privacy_gateway.py; component này chỉ phát event.
 * Chỉ render khi backend Python cung cấp trạng thái cổng (bản Streamlit).
 */
export function PrivacyGatewayPanel() {
  const { privacy, privacyActions, theme } = useCreditLens();
  const [manualValue, setManualValue] = useState("");
  if (!privacy || !privacyActions) return null;
  const copy = STATE_COPY[privacy.state];

  const submitManual = (event: FormEvent) => {
    event.preventDefault();
    const value = manualValue.trim();
    if (value.length < 2) return;
    privacyActions.addMask(value);
    setManualValue("");
  };

  return (
    <section
      className="cl-support-page cl-privacy-page"
      data-theme={theme}
      aria-labelledby="cl-privacy-title"
    >
      <header className="cl-privacy-page__header">
        <div>
          <p className="cl-core-eyebrow">Privacy Gateway</p>
          <h2 id="cl-privacy-title">Bước 0 · Bảo mật hồ sơ</h2>
          <p>Phát hiện và giả danh hóa thông tin định danh trước mọi bước khác.</p>
        </div>
        <span className={`cl-privacy-badge cl-privacy-badge--${privacy.state}`} role="status">
          <span aria-hidden="true">{privacy.state === "done" ? "✓" : "🔒"}</span>
          {privacy.badge_label}
        </span>
      </header>

      <div className="cl-privacy-warning" role="alert">
        <strong>Cảnh báo dữ liệu</strong>
        <p>{privacy.public_warning}</p>
      </div>

      <label className="cl-privacy-consent-row">
        <input
          type="checkbox"
          checked={privacy.consent_given}
          onChange={(e) => privacyActions.setConsent(e.target.checked)}
        />
        <span>{privacy.consent_text}</span>
      </label>

      {privacy.upload_plan ? <UploadPlanPanel /> : null}

      <div className={`cl-privacy-state cl-privacy-state--${privacy.state}`}>
        <strong>{copy.title}</strong>
        <span>{copy.detail}</span>
      </div>

      {privacy.counts.length > 0 ? (
        <ul className="cl-privacy-counts" aria-label="Số trường theo loại PII">
          {privacy.counts.map((item) => (
            <li key={item.label}>
              <span>{item.label}</span>
              <strong>{item.count}</strong>
            </li>
          ))}
        </ul>
      ) : null}

      {privacy.rows.length > 0 ? (
        <div className="cl-table-scroll" tabIndex={0} aria-label="Bảng xem trước thông tin định danh">
          <table className="cl-data-table cl-privacy-table">
            <caption>
              Bảng xem trước{privacy.case_id ? ` · ${privacy.case_id}` : ""} — chỉ hiển thị giá trị đã che.
            </caption>
            <thead>
              <tr>
                <th scope="col">Loại PII</th>
                <th scope="col">Giá trị đã che</th>
                <th scope="col">Mã thay thế</th>
                <th scope="col">Tài liệu / trang</th>
                <th scope="col">Che</th>
              </tr>
            </thead>
            <tbody>
              {privacy.rows.map((row) => (
                <tr key={`${row.pii_type}-${row.replacement}-${row.masked_value}`}>
                  <th scope="row">{row.pii_type}</th>
                  <td>{row.masked_value}</td>
                  <td>
                    <code>{row.replacement}</code>
                  </td>
                  <td>
                    {row.document}
                    {row.page ? ` · tr. ${row.page}` : ""}
                  </td>
                  <td>
                    {row.required ? (
                      "Bắt buộc"
                    ) : (
                      <button
                        type="button"
                        className="cl-privacy-link"
                        onClick={() => privacyActions.removeMask(row.replacement)}
                      >
                        Bỏ (thủ công)
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {privacy.state === "review" ? (
        <>
          <form className="cl-privacy-manual" onSubmit={submitManual}>
            <label htmlFor="cl-privacy-manual-input">Đánh dấu thêm một giá trị cần che (thủ công)</label>
            <div>
              <input
                id="cl-privacy-manual-input"
                type="text"
                autoComplete="off"
                maxLength={120}
                value={manualValue}
                onChange={(e) => setManualValue(e.target.value)}
                placeholder="Ví dụ: tên người thân, mã nội bộ…"
              />
              <button type="submit" disabled={manualValue.trim().length < 2}>
                Thêm vào danh sách che
              </button>
            </div>
          </form>
          <div className="cl-privacy-actions">
            <button
              type="button"
              className="cl-demo-panel__action"
              disabled={!privacy.consent_given}
              onClick={() => privacyActions.confirm()}
            >
              Giả danh hóa và tiếp tục
            </button>
            <button type="button" className="cl-close-case-btn" onClick={() => privacyActions.cancel()}>
              Hủy hồ sơ đang chờ
            </button>
          </div>
          {!privacy.consent_given ? (
            <p className="cl-privacy-hint">Tick ô xác nhận bảo mật để bật nút giả danh hóa.</p>
          ) : null}
        </>
      ) : null}

      {privacy.audit.length > 0 ? (
        <details className="cl-privacy-audit">
          <summary>Nhật ký kiểm soát (chỉ số liệu, không có giá trị)</summary>
          <ul>
            {privacy.audit.map((entry, index) => (
              <li key={`${entry.time}-${index}`}>
                <time>{entry.time}</time> · {entry.event}
                {entry.provider ? ` · ${entry.provider}` : ""} · {entry.fields} trường
                {entry.result ? ` · ${entry.result}` : ""}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

/** Màn hình thay thế khi truy cập trực tiếp một trang bị khóa. */
export function LockedPageNotice({ reason, onGoToGateway }: { reason: string; onGoToGateway: () => void }) {
  const { theme } = useCreditLens();
  return (
    <section className="cl-support-page cl-privacy-page" data-theme={theme} role="alert">
      <header className="cl-privacy-page__header">
        <div>
          <p className="cl-core-eyebrow">Privacy Gateway</p>
          <h2>Trang đang khóa</h2>
          <p>{reason}</p>
        </div>
        <span className="cl-privacy-badge cl-privacy-badge--pending">🔒 Chưa qua Bước 0</span>
      </header>
      <div className="cl-privacy-actions">
        <button type="button" className="cl-demo-panel__action" onClick={onGoToGateway}>
          Đi tới Bước 0 · Bảo mật hồ sơ
        </button>
      </div>
    </section>
  );
}

/** Bảng xác nhận phân loại tài liệu (sau khi tải thư mục/tệp, trước khi trích xuất và giả danh hóa). */
export function UploadPlanPanel() {
  const { privacy, privacyActions } = useCreditLens();
  const plan = privacy?.upload_plan;
  if (!plan || !privacyActions) return null;
  return (
    <section className="cl-upload-plan" aria-labelledby="cl-upload-plan-title">
      <h3 id="cl-upload-plan-title">Xác nhận phân loại tài liệu</h3>
      <p className="cl-privacy-hint">
        Nhận diện bằng tên tệp và nội dung PDF (pypdf, trên máy chủ; không gửi tệp cho AI). Sửa loại nếu chưa đúng rồi bấm
        “Tiếp tục trích xuất”.
      </p>
      {plan.rows.length > 0 ? (
        <div className="cl-table-scroll" tabIndex={0} aria-label="Bảng phân loại tài liệu">
          <table className="cl-data-table cl-upload-plan__table">
            <thead>
              <tr>
                <th scope="col">Tên tệp</th>
                <th scope="col">Loại nhận diện</th>
                <th scope="col">Độ tin cậy</th>
              </tr>
            </thead>
            <tbody>
              {plan.rows.map((row) => (
                <tr key={row.id}>
                  <th scope="row">
                    <code>{row.path}</code>
                    <small> · {row.size_label}</small>
                    {row.note ? <small className="cl-upload-plan__note">{row.note}</small> : null}
                  </th>
                  <td>
                    <select
                      aria-label={`Loại tài liệu của ${row.path}`}
                      value={row.type}
                      onChange={(e) => privacyActions.assignUpload?.(row.id, e.target.value)}
                    >
                      {row.type === "unknown" ? <option value="unknown">Chưa xác định — chọn loại</option> : null}
                      {plan.options.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    {row.changed ? <small> · đã sửa (gợi ý: {row.detected_label})</small> : null}
                  </td>
                  <td>
                    {Math.round(row.confidence * 100)}%<small> · {row.basis}</small>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {plan.issues.length > 0 ? (
        <ul className="cl-upload-plan__issues" aria-label="Cảnh báo tải hồ sơ">
          {plan.issues.map((issue, index) => (
            <li key={index} className={`cl-upload-plan__issue cl-upload-plan__issue--${issue.level}`} role={issue.level === "error" ? "alert" : undefined}>
              {issue.level === "error" ? "⛔ " : "⚠️ "}
              {issue.text}
            </li>
          ))}
        </ul>
      ) : null}
      <div className="cl-privacy-actions">
        <button
          type="button"
          className="cl-demo-panel__action"
          disabled={!plan.can_continue}
          onClick={() => privacyActions.continueUpload?.()}
        >
          Tiếp tục trích xuất
        </button>
        <button type="button" className="cl-close-case-btn" onClick={() => privacyActions.cancelUpload?.()}>
          Hủy và tải lại
        </button>
      </div>
    </section>
  );
}
