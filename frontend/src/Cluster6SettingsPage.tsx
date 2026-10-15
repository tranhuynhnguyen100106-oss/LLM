import type { StatusTone, V2SettingsPageViewModel } from "./contracts";

interface SettingsPageProps {
  viewModel: V2SettingsPageViewModel;
}

const CONNECTION_COPY: Record<V2SettingsPageViewModel["connection_state"], string> = {
  connected: "Kết nối đã được xác minh trong phiên hiện tại.",
  not_configured: "Chưa có kết nối đã xác minh. Phân tích Python vẫn hoạt động.",
  error: "Kết nối chưa thể xác minh. Không có bí mật nào được chuyển sang React."
};

const CHAT_COPY: Record<V2SettingsPageViewModel["chat_state"], string> = {
  ready: "Sẵn sàng nhận tin nhắn mới",
  disabled: "Chờ kết nối và model hợp lệ",
  error: "Lượt gọi gần nhất cần được kiểm tra"
};

function ToneBadge({ tone, children }: { tone: StatusTone; children: string }) {
  return <span className={`cl-badge cl-badge--${tone}`}>{children}</span>;
}

export function SettingsPage({ viewModel }: SettingsPageProps) {
  const statusTone: StatusTone = viewModel.connection_state === "connected"
    ? "success"
    : viewModel.connection_state === "error"
      ? "danger"
      : "neutral";

  return (
    <main className="cl-support-page cl-settings-page" data-theme={viewModel.theme} aria-labelledby="cl-settings-title">
      <header className="cl-support-header cl-settings-header">
        <div>
          <p className="cl-core-eyebrow">SESSION SETTINGS</p>
          <h1 id="cl-settings-title">Cài đặt và trợ lý AI</h1>
          <p>Python giữ credential, provider state, thresholds, lịch sử hội thoại và toàn bộ inference execution.</p>
        </div>
        <ToneBadge tone={statusTone}>{viewModel.connection_status_label}</ToneBadge>
      </header>

      <section
        className={`cl-settings-status cl-tone--${statusTone}`}
        role={viewModel.connection_state === "error" ? "alert" : "status"}
        aria-live="polite"
        aria-labelledby="cl-settings-status-title"
      >
        <div>
          <p className="cl-core-eyebrow">CONNECTION STATUS</p>
          <h2 id="cl-settings-status-title">{viewModel.connection_status_label}</h2>
          <p>{viewModel.error_message ?? CONNECTION_COPY[viewModel.connection_state]}</p>
        </div>
        <dl className="cl-settings-status__facts">
          <div><dt>Provider</dt><dd>{viewModel.active_provider_label ?? "Chưa chọn"}</dd></div>
          <div><dt>Model</dt><dd><code>{viewModel.active_model ?? "Chưa chọn"}</code></dd></div>
          <div><dt>Hồ sơ hiện tại</dt><dd>{viewModel.current_case ?? "Chưa có"}</dd></div>
        </dl>
      </section>

      <section className="cl-core-section" aria-labelledby="cl-provider-title">
        <div className="cl-core-section__heading">
          <div>
            <p className="cl-core-eyebrow">AI CONNECTION</p>
            <h2 id="cl-provider-title">Provider và model trong phiên</h2>
          </div>
          <span>Không hard-code provider</span>
        </div>
        <div className="cl-provider-grid">
          {viewModel.providers.map((provider) => (
            <article className={`cl-provider-card${provider.active ? " is-active" : ""}`} key={provider.provider}>
              <div className="cl-provider-card__topline">
                <h3>{provider.label}</h3>
                <ToneBadge tone={provider.status_tone}>{provider.status_label}</ToneBadge>
              </div>
              <p>{provider.description}</p>
              <dl>
                <div><dt>Model</dt><dd><code>{provider.model ?? "Chưa có"}</code></dd></div>
                <div><dt>Model khả dụng</dt><dd>{provider.connected ? provider.model_count : "—"}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <div className="cl-settings-two-column">
        <section className="cl-core-section" aria-labelledby="cl-chat-session-title">
          <div className="cl-core-section__heading">
            <div>
              <p className="cl-core-eyebrow">CHAT SESSION</p>
              <h2 id="cl-chat-session-title">Chat và lịch sử</h2>
            </div>
            <ToneBadge tone={viewModel.chat_state === "ready" ? "success" : viewModel.chat_state === "error" ? "danger" : "neutral"}>
              {viewModel.chat_state === "ready" ? "READY" : viewModel.chat_state === "error" ? "ERROR" : "DISABLED"}
            </ToneBadge>
          </div>
          <p className="cl-settings-lead">{CHAT_COPY[viewModel.chat_state]}</p>
          <dl className="cl-session-facts">
            <div><dt>Lượt tin nhắn hợp lệ</dt><dd>{viewModel.chat_message_count}</dd></div>
            <div><dt>Context hồ sơ</dt><dd>{viewModel.current_case ?? "Không có"}</dd></div>
          </dl>
          <p className="cl-settings-note">
            Nội dung hội thoại không nằm trong view-model này. Streamlit native render lịch sử và chỉ gửi khi người dùng submit nội dung không rỗng.
          </p>
        </section>

        <section className="cl-core-section" aria-labelledby="cl-session-controls-title">
          <div className="cl-core-section__heading">
            <div>
              <p className="cl-core-eyebrow">SESSION CONTROLS</p>
              <h2 id="cl-session-controls-title">Trạng thái phiên</h2>
            </div>
            <span>Không persistence server-side</span>
          </div>
          <dl className="cl-session-facts">
            <div><dt>Hồ sơ đã xử lý</dt><dd>{viewModel.has_result ? "Có" : "Chưa có"}</dd></div>
            <div><dt>Evaluation đã chạy</dt><dd>{viewModel.evaluation_ready ? "Có" : "Chưa có"}</dd></div>
          </dl>
          <ul className="cl-settings-checklist">
            <li>Đổi provider hoặc model không gọi inference.</li>
            <li>Rerun và render history không gửi lại prompt.</li>
            <li>Mỗi provider giữ tối đa một kết nối đã xác minh trong phiên.</li>
          </ul>
        </section>
      </div>

      <section className="cl-core-section" aria-labelledby="cl-session-thresholds-title">
        <div className="cl-core-section__heading">
          <div>
            <p className="cl-core-eyebrow">SESSION THRESHOLDS</p>
            <h2 id="cl-session-thresholds-title">Ngưỡng minh họa hiện hành</h2>
          </div>
          <span>Python source of truth</span>
        </div>
        <p className="cl-core-disclaimer">Giá trị chỉ phục vụ minh họa, không phải chính sách tín dụng của ngân hàng.</p>
        <dl className="cl-settings-threshold-grid">
          {viewModel.thresholds.map((threshold) => (
            <div key={threshold.key}>
              <dt>{threshold.label}</dt>
              <dd>{threshold.value_display}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="cl-settings-security" aria-labelledby="cl-settings-security-title">
        <div aria-hidden="true" className="cl-settings-security__icon">✓</div>
        <div>
          <p className="cl-core-eyebrow">BACKEND-ONLY CREDENTIALS</p>
          <h2 id="cl-settings-security-title">Secure native controls ngay bên dưới</h2>
          <p>
            API Key dùng trường password của Streamlit, không đi qua React props, browser event, localStorage hoặc telemetry. Chat input và mọi request provider cũng chạy từ Python.
          </p>
        </div>
      </section>
    </main>
  );
}
