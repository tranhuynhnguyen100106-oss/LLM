import type { V2PrivacyGatewayViewModel } from "./contracts";

interface PrivacyGatewayPageProps {
  viewModel: V2PrivacyGatewayViewModel;
}

const STATE_COPY: Record<V2PrivacyGatewayViewModel["state"], { title: string; detail: string }> = {
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
    detail: "Mọi dữ liệu gửi dịch vụ AI chỉ dùng mã thay thế. Vault chỉ nằm trong phiên máy chủ."
  }
};

/**
 * Bước 0 · Bảo mật hồ sơ — chỉ hiển thị giá trị ĐÃ CHE và mã thay thế.
 * Vault (giá trị thật) không bao giờ được gửi sang React; mọi hành động vẫn là control native Streamlit.
 */
export function PrivacyGatewayPage({ viewModel }: PrivacyGatewayPageProps) {
  const copy = STATE_COPY[viewModel.state];
  return (
    <section
      className="cl-support-page cl-privacy-page"
      data-theme={viewModel.theme}
      aria-labelledby="cl-privacy-title"
    >
      <header className="cl-privacy-page__header">
        <div>
          <p className="cl-core-eyebrow">Privacy Gateway</p>
          <h1 id="cl-privacy-title">Bước 0 · Bảo mật hồ sơ</h1>
          <p>Phát hiện và giả danh hóa thông tin định danh trước mọi bước khác.</p>
        </div>
        <span className={`cl-privacy-badge cl-privacy-badge--${viewModel.state}`} role="status">
          <span aria-hidden="true">{viewModel.state === "done" ? "✓" : "🔒"}</span>
          {viewModel.badge_label}
        </span>
      </header>

      <div className="cl-privacy-warning" role="alert">
        <strong>Cảnh báo dữ liệu</strong>
        <p>{viewModel.public_warning}</p>
      </div>

      <div className={`cl-privacy-state cl-privacy-state--${viewModel.state}`}>
        <strong>{copy.title}</strong>
        <span>{copy.detail}</span>
        <span className="cl-privacy-consent">
          {viewModel.consent_given ? "Đã xác nhận quy định bảo mật." : "Chưa xác nhận quy định bảo mật."}
        </span>
      </div>

      {viewModel.counts.length > 0 ? (
        <ul className="cl-privacy-counts" aria-label="Số trường theo loại PII">
          {viewModel.counts.map((item) => (
            <li key={item.label}>
              <span>{item.label}</span>
              <strong>{item.count}</strong>
            </li>
          ))}
        </ul>
      ) : null}

      {viewModel.rows.length > 0 ? (
        <div className="cl-table-scroll" tabIndex={0} aria-label="Bảng xem trước thông tin định danh">
          <table className="cl-data-table cl-privacy-table">
            <caption>
              Bảng xem trước{viewModel.case_id ? ` · ${viewModel.case_id}` : ""} — chỉ hiển thị giá trị đã che.
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
              {viewModel.rows.map((row) => (
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
                  <td>{row.required ? "Bắt buộc" : "Thủ công"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {viewModel.audit.length > 0 ? (
        <details className="cl-privacy-audit">
          <summary>Nhật ký kiểm soát (chỉ số liệu, không có giá trị)</summary>
          <ul>
            {viewModel.audit.map((entry, index) => (
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
