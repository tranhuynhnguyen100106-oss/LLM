import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from "react";
import { useCreditLens, type ChatRoleKey, type ChatModelKey } from "../context/CreditLensContext";
import { Markdown } from "../lib/markdown";
import { getStoredApiKey, setStoredApiKey, testGeminiKey, IS_STANDALONE } from "../lib/gemini";

const QUICK_PROMPTS: { label: string; text: string; role?: ChatRoleKey }[] = [
  {
    label: "Kiểm tra DTI & DSR",
    text: "Phân tích chi tiết tỷ lệ DTI và DSR của hồ sơ hiện tại, đánh giá rủi ro vượt ngưỡng nếu có.",
    role: "underwriter"
  },
  {
    label: "Đối chiếu thu nhập",
    text: "Kiểm tra sự nhất quán giữa thu nhập kê khai trong hợp đồng và số tiền lương thực nhận trên sao kê ngân hàng.",
    role: "risk_auditor"
  },
  {
    label: "Tổng hợp cảnh báo rủi ro",
    text: "Liệt kê và phân loại mức độ nghiêm trọng của toàn bộ các cảnh báo rủi ro trong hồ sơ này.",
    role: "risk_auditor"
  },
  {
    label: "Đề xuất phương án cấp tín dụng",
    text: "Dựa trên tình hình tài chính của khách hàng, hãy nêu phương án cơ cấu khoản vay, biện pháp giảm thiểu rủi ro và các điểm cần xác minh thêm (không đề xuất phê duyệt hay từ chối).",
    role: "advisor"
  }
];

const ROLES_CONFIG: Record<
  ChatRoleKey,
  { label: string; title: string; desc: string; icon: string }
> = {
  underwriter: {
    label: "Thẩm định viên",
    title: "Senior Credit Underwriter",
    desc: "Đánh giá DTI/DSR, nguồn thu nhập, năng lực trả nợ theo chuẩn mực ngân hàng",
    icon: "💼"
  },
  risk_auditor: {
    label: "Kiểm soát rủi ro",
    title: "Risk & Compliance Auditor",
    desc: "So soát mâu thuẫn chứng từ, dấu hiệu bất thường, gian lận và tuân thủ",
    icon: "🛡️"
  },
  advisor: {
    label: "Cố vấn giải pháp",
    title: "Credit Solution Advisor",
    desc: "Đề xuất cơ cấu khoản vay, hạn mức và phương án giảm thiểu rủi ro",
    icon: "📊"
  }
};

const MODELS_CONFIG: Record<
  ChatModelKey,
  { label: string; badge: string; desc: string; speed: string }
> = {
  "gemini-3.8-flash": {
    label: "Gemini 3.8 Flash",
    badge: "MẶC ĐỊNH",
    desc: "Xử lý tác vụ thẩm định chung, phân tích đa chiều và giải thích hồ sơ",
    speed: "Nhanh & Ổn định"
  },
  "gemini-3.1-flash-lite": {
    label: "Gemini 3.1 Flash Lite",
    badge: "TỐC ĐỘ CAO",
    desc: "Phù hợp tác vụ tra cứu nhanh, tóm tắt tức thì với độ trễ thấp nhất",
    speed: "Rất nhanh"
  },
  "gemini-4-argon": {
    label: "Gemini 4 Argon",
    badge: "SUY LUẬN SÂU",
    desc: "Dành cho bài toán rủi ro phức tạp, phân tích dòng tiền và đối soát đa tầng",
    speed: "Chuyên sâu"
  }
};

interface GeminiChatbotProps {
  embedded?: boolean;
  onClose?: () => void;
}

export function GeminiChatbot({ embedded = false, onClose }: GeminiChatbotProps) {
  const {
    chatMessages,
    chatLoading,
    chatRole,
    setChatRole,
    chatModel,
    setChatModel,
    sendChatMessage,
    clearChatMessages,
    result,
    serverMode,
    aiConnection,
    chatModels,
    openAiSettings
  } = useCreditLens();
  const modelOptions: { id: string; label: string; badge: string }[] =
    chatModels ??
    (Object.keys(MODELS_CONFIG) as ChatModelKey[]).map((m) => ({
      id: m,
      label: MODELS_CONFIG[m]!.label,
      badge: MODELS_CONFIG[m]!.badge
    }));
  const modelLabel = (id: string) =>
    !id
      ? "Chưa kết nối AI"
      : modelOptions.find((m) => m.id === id)?.label ?? MODELS_CONFIG[id as keyof typeof MODELS_CONFIG]?.label ?? id;
  const serverConnected = aiConnection?.state === "connected";

  const [input, setInput] = useState("");
  const [showRoleInfo, setShowRoleInfo] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [keyOpen, setKeyOpen] = useState(false);
  const [keyDraft, setKeyDraft] = useState(() => getStoredApiKey());
  const [keySaved, setKeySaved] = useState(() => Boolean(getStoredApiKey()));
  const [keyStatus, setKeyStatus] = useState<string>("");
  const [keyTesting, setKeyTesting] = useState(false);

  const saveKey = async () => {
    const k = keyDraft.trim();
    if (!k) {
      setStoredApiKey("");
      setKeySaved(false);
      setKeyStatus("Đã xóa khóa khỏi trình duyệt.");
      return;
    }
    setKeyTesting(true);
    setKeyStatus("Đang kiểm tra kết nối với Gemini 3.8 Flash…");
    try {
      await testGeminiKey(k);
      setStoredApiKey(k);
      setKeySaved(true);
      setKeyStatus("✓ Kết nối thành công. Khóa chỉ lưu trong trình duyệt này.");
      setTimeout(() => setKeyOpen(false), 900);
    } catch (e: any) {
      setKeyStatus(`✕ Khóa không hợp lệ hoặc bị chặn: ${e?.message ?? "lỗi"}`);
    } finally {
      setKeyTesting(false);
    }
  };
  const lastIsUser = chatMessages[chatMessages.length - 1]?.role === "user";
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, chatLoading]);

  const handleSubmit = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || chatLoading) return;
    const msg = input.trim();
    setInput("");
    await sendChatMessage(msg);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard?.writeText(text);
    setCopiedId(index);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleQuickPrompt = (promptText: string, suggestedRole?: ChatRoleKey) => {
    if (suggestedRole && suggestedRole !== chatRole) {
      setChatRole(suggestedRole);
    }
    sendChatMessage(promptText);
  };

  return (
    <div className={`cl-gemini-chat ${embedded ? "cl-gemini-chat--embedded" : "cl-gemini-chat--drawer"}`}>
      {/* Header */}
      <header className="cl-gemini-chat__header">
        <div className="cl-gemini-chat__brand">
          <div className="cl-gemini-chat__avatar">
            <span className="cl-gemini-chat__sparkle">✦</span>
          </div>
          <div>
            <div className="cl-gemini-chat__title-row">
              <h3 className="cl-gemini-chat__title">
                {serverMode ? `Trợ lý ${aiConnection?.provider_label ?? "AI"}` : "Trợ lý Gemini 3.8"}
              </h3>
              <span className="cl-gemini-chat__badge">AI</span>
            </div>
            <p className="cl-gemini-chat__subtitle">
              Hỏi đáp nghiệp vụ dựa trên hồ sơ vay đang mở
            </p>
          </div>
        </div>

        <div className="cl-gemini-chat__header-actions">
          {serverMode ? (
            <button
              type="button"
              className={`cl-gemini-chat__key-btn${serverConnected ? " is-on" : ""}`}
              onClick={() => {
                openAiSettings?.();
                onClose?.();
              }}
              title="Cài đặt → Kết nối AI (khóa chỉ nằm ở máy chủ Python)"
            >
              🔑 {serverConnected ? "Đã kết nối" : aiConnection?.state === "partial" ? "Key hợp lệ" : "Kết nối AI"}
            </button>
          ) : (
            <button
              type="button"
              className={`cl-gemini-chat__key-btn${keySaved ? " is-on" : ""}`}
              onClick={() => setKeyOpen((v) => !v)}
              aria-expanded={keyOpen}
              title="Cấu hình khóa Gemini API"
            >
              🔑 {keySaved ? "Đã kết nối" : "Khóa API"}
            </button>
          )}
          <button
            type="button"
            className="cl-gemini-chat__btn-icon"
            onClick={clearChatMessages}
            title="Làm mới phiên hội thoại"
            aria-label="Làm mới phiên hội thoại"
          >
            ↺
          </button>
          {!embedded && onClose && (
            <button
              type="button"
              className="cl-gemini-chat__btn-icon"
              onClick={onClose}
              title="Đóng trợ lý"
              aria-label="Đóng trợ lý"
            >
              ✕
            </button>
          )}
        </div>
      </header>

      {serverMode && !serverConnected ? (
        <div className="cl-gemini-chat__key-panel" role="status">
          <strong>{aiConnection?.label ?? "Chưa kết nối AI"}</strong>
          <small>{aiConnection?.message ?? "Mở Cài đặt → Kết nối AI để nhập khóa trên máy chủ."}</small>
        </div>
      ) : null}

      {!serverMode && keyOpen && (
        <div className="cl-gemini-chat__key-panel">
          <label htmlFor="cl-gemini-key">
            Khóa Gemini API {IS_STANDALONE ? "(bắt buộc ở bản độc lập)" : "(tùy chọn — ưu tiên hơn khóa máy chủ)"}
          </label>
          <div className="cl-gemini-chat__key-row">
            <input
              id="cl-gemini-key"
              type="password"
              autoComplete="off"
              spellCheck={false}
              placeholder="AIza…"
              value={keyDraft}
              onChange={(e) => setKeyDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveKey()}
            />
            <button type="button" onClick={saveKey} disabled={keyTesting}>
              {keyTesting ? "…" : "Lưu & kiểm tra"}
            </button>
          </div>
          <small>
            Lấy khóa miễn phí tại{" "}
            <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">aistudio.google.com/apikey</a>.
            Khóa chỉ lưu trên trình duyệt của bạn và gửi thẳng tới Google.
          </small>
          {keyStatus && <p className="cl-gemini-chat__key-status">{keyStatus}</p>}
        </div>
      )}

      {/* Grounding & Active Case Banner */}
      <div className="cl-gemini-chat__context-bar">
        <span className="cl-gemini-chat__context-dot" />
        <span className="cl-gemini-chat__context-text">
          {result ? (
            <>
              Đang gắn ngữ cảnh: <strong>{result.ma_ho_so}</strong> — {result.du_lieu.ho_ten_khach_hang || "Khách hàng"} ({result.canh_bao.length} rủi ro)
            </>
          ) : (
            "Chưa mở hồ sơ cụ thể (sử dụng kiến thức nghiệp vụ tín dụng tổng quát)"
          )}
        </span>
      </div>

      {/* Controls: Role selection & Model selection */}
      <div className="cl-gemini-chat__controls">
        <div className="cl-gemini-chat__role-select">
          <label htmlFor="cl-chat-role" className="cl-gemini-chat__ctrl-label">
            Vai trò trợ lý:
          </label>
          <div className="cl-gemini-chat__role-tabs">
            {(Object.keys(ROLES_CONFIG) as ChatRoleKey[]).map((r) => {
              const info = ROLES_CONFIG[r];
              const isActive = chatRole === r;
              return (
                <button
                  key={r}
                  type="button"
                  className={`cl-gemini-chat__role-btn${isActive ? " is-active" : ""}`}
                  onClick={() => setChatRole(r)}
                  title={info.desc}
                >
                  <span>{info.icon}</span>
                  <span>{info.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="cl-gemini-chat__model-select">
          <label htmlFor="cl-chat-model" className="cl-gemini-chat__ctrl-label">
            Mô hình:
          </label>
          <select
            id="cl-chat-model"
            className="cl-gemini-chat__model-dropdown"
            value={chatModel}
            onChange={(e) => setChatModel(e.target.value as ChatModelKey)}
          >
            {modelOptions.length === 0 ? <option value={chatModel}>Chưa có model khả dụng</option> : null}
            {modelOptions.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label} ({m.badge})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Role explanation bar */}
      <div className="cl-gemini-chat__role-banner">
        <strong>{ROLES_CONFIG[chatRole].title}:</strong> {ROLES_CONFIG[chatRole].desc}
      </div>

      {/* Scrollable Message Thread */}
      <div className="cl-gemini-chat__messages" role="log" aria-live="polite">
        {chatMessages.map((msg, index) => {
          const isUser = msg.role === "user";
          return (
            <article
              key={index}
              className={`cl-gemini-msg ${isUser ? "cl-gemini-msg--user" : "cl-gemini-msg--bot"}`}
            >
              <div className="cl-gemini-msg__meta">
                <span className="cl-gemini-msg__sender">
                  {isUser ? "Chuyên viên thẩm định" : "Trợ lý tín dụng"}
                </span>
                {!isUser && msg.modelUsed && (
                  <span className="cl-gemini-msg__model-tag">{msg.modelUsed}</span>
                )}
                {msg.timestamp && (
                  <span className="cl-gemini-msg__time">
                    {new Date(msg.timestamp).toLocaleTimeString("vi-VN", {
                      hour: "2-digit",
                      minute: "2-digit"
                    })}
                  </span>
                )}
              </div>

              <div className="cl-gemini-msg__body">
                {isUser ? msg.content : <Markdown text={msg.content} />}
              </div>

              <div className="cl-gemini-msg__footer">
                <button
                  type="button"
                  className="cl-gemini-msg__action-btn"
                  onClick={() => handleCopy(msg.content, index)}
                  title="Sao chép nội dung"
                >
                  {copiedId === index ? "✓ Đã sao chép" : "Sao chép"}
                </button>
              </div>
            </article>
          );
        })}

        {chatLoading && lastIsUser && (
          <div className="cl-gemini-msg cl-gemini-msg--bot cl-gemini-msg--loading">
            <div className="cl-gemini-msg__meta">
              <span className="cl-gemini-msg__sender">Trợ lý tín dụng</span>
              <span className="cl-gemini-msg__model-tag">{chatModel}</span>
            </div>
            <div className="cl-gemini-loading-dots">
              <span className="cl-gemini-dot" />
              <span className="cl-gemini-dot" />
              <span className="cl-gemini-dot" />
              <span className="cl-gemini-loading-text">Đang suy luận dữ kiện tín dụng...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts Bar */}
      <div className="cl-gemini-chat__quick-prompts">
        <span className="cl-gemini-chat__quick-title">Gợi ý nhanh:</span>
        <div className="cl-gemini-chat__quick-list">
          {QUICK_PROMPTS.map((p, idx) => (
            <button
              key={idx}
              type="button"
              className="cl-gemini-chat__quick-pill"
              onClick={() => handleQuickPrompt(p.text, p.role)}
              disabled={chatLoading}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Input Form */}
      <form onSubmit={handleSubmit} className="cl-gemini-chat__form">
        <div className="cl-gemini-chat__input-wrapper">
          <textarea
            ref={inputRef}
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Đặt câu hỏi về DTI, rủi ro, đối chiếu thu nhập... (Enter để gửi, Shift+Enter xuống dòng)"
            disabled={chatLoading}
            className="cl-gemini-chat__textarea"
          />
          <button
            type="submit"
            disabled={!input.trim() || chatLoading}
            className="cl-gemini-chat__send-btn"
            title="Gửi câu hỏi"
            aria-label="Gửi câu hỏi"
          >
            {chatLoading ? "..." : "➤"}
          </button>
        </div>
        <div className="cl-gemini-chat__footer-info">
          <span>Mô hình: {modelLabel(chatModel)}</span>
          <span>Phản hồi có tính chất hỗ trợ quyết định</span>
        </div>
      </form>
    </div>
  );
}
