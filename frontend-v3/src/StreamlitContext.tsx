/**
 * StreamlitContext — thay CreditLensProvider của bản AI Studio khi chạy trong Streamlit (UI v3).
 *
 * Python (creditlens_ui_v3.py) là server và source of truth: trích xuất PDF, Privacy Gateway, công thức,
 * rules, evaluation, gọi LLM, export. Provider này chỉ:
 *   - ánh xạ view model JSON (allowlist, đã giả danh hóa) sang đúng interface CreditLensContextType
 *     để các component trong ../src/components dùng lại nguyên vẹn;
 *   - phát event có kiểu (event_id duy nhất) về Python qua setTriggerValue.
 * Không có API key, không gọi LLM, không chạy engine.ts ở đây.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import type {
  AiConnectionStatus,
  ChatMessage,
  ChatModelKey,
  ChatModelOption,
  ChatRoleKey,
  CreditLensContextType,
  ExportKind,
  PrivacyGatewayState
} from "@original-context";
import type {
  CaseContext,
  DemoCaseItem,
  MotionLevel,
  NavigationItem,
  ProcessCard,
  ProviderStatus,
  ThemeMode,
  V2CorePageViewModel,
  V2EvaluationPageViewModel,
  V2MethodologyPageViewModel,
  V2SummaryPageViewModel,
  WorkflowStep
} from "../../src/domain/contracts";
import type { ToastItem } from "../../src/components/Toast";
import { collectFromInput, filterCaseFiles, withRelativePath } from "../../src/lib/folderUpload";

export type { ChatRoleKey, ChatModelKey, ChatMessage, CreditLensContextType } from "@original-context";

export const V3_COMPONENT = "creditlens_v3_app" as const;
export const V3_SCHEMA = "3.0" as const;

export type Thresholds = Record<
  | "do_tin_cay_thap"
  | "chenh_lech_thu_nhap"
  | "chenh_lech_thu_nhap_nghiem_trong"
  | "chenh_lech_no"
  | "dti_canh_bao"
  | "dsr_canh_bao"
  | "he_so_dem_so_du_thap"
  | "bien_dong_thu_nhap_cao",
  number
>;

export interface V3ResultSummary {
  ma_ho_so: string;
  ten_ho_so: string;
  trang_thai: "REVIEW READY" | "HUMAN REVIEW REQUIRED" | "INSUFFICIENT INFORMATION";
  nguon_thu_nhap_dung_de_tinh: string;
  du_lieu: { ho_ten_khach_hang: string | null };
  documents: { name: string }[];
  fields: { key: string }[];
  canh_bao: { severity: string; name: string; description: string }[];
}

export interface V3AppPayload {
  schema_version: typeof V3_SCHEMA;
  component: typeof V3_COMPONENT;
  revision: number;
  theme: ThemeMode;
  motion_level: MotionLevel;
  active_page: string;
  navigation: NavigationItem[];
  case_context: CaseContext;
  workflow: WorkflowStep[];
  process_cards: ProcessCard[];
  demo_cases: DemoCaseItem[];
  selected_demo: string;
  custom_case_name: string | null;
  result: V3ResultSummary | null;
  thresholds: Thresholds;
  pages: {
    core?: V2CorePageViewModel | null;
    summary?: V2SummaryPageViewModel | null;
    methodology?: V2MethodologyPageViewModel | null;
    evaluation?: V2EvaluationPageViewModel | null;
  };
  ai: { explanation: string | null };
  chat: { messages: ChatMessage[]; role: ChatRoleKey; model: string; models: ChatModelOption[] };
  providers: ProviderStatus[];
  active_provider: string;
  ai_connection: AiConnectionStatus;
  privacy: PrivacyGatewayState;
  toasts: { id: string; title: string; description?: string; type?: "info" | "success" | "warning" }[];
  assets: Record<string, string>;
}

export interface V3Event {
  event_id: string;
  type: string;
  [key: string]: unknown;
}

const PROHIBITED = new Set(["api_key", "apikey", "authorization", "auth", "credential", "credentials", "password", "secret", "token"]);

/** Từ chối payload có khóa bị cấm (phòng thủ chiều sâu, Python đã allowlist). */
export function assertSafePayload(value: unknown): void {
  if (Array.isArray(value)) {
    value.forEach(assertSafePayload);
    return;
  }
  if (value === null || typeof value !== "object") return;
  for (const [key, nested] of Object.entries(value as Record<string, unknown>)) {
    if (PROHIBITED.has(key.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, ""))) {
      throw new Error("Payload contains a prohibited field.");
    }
    assertSafePayload(nested);
  }
}

export function parseV3Payload(value: unknown): V3AppPayload {
  if (!value || typeof value !== "object") throw new Error("Payload v3 không hợp lệ.");
  const data = value as V3AppPayload;
  if (data.component !== V3_COMPONENT || data.schema_version !== V3_SCHEMA) throw new Error("Sai component v3.");
  if (!Array.isArray(data.navigation) || data.navigation.length !== 8) throw new Error("Điều hướng v3 không hợp lệ.");
  assertSafePayload(data);
  return data;
}

function newEventId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") return `v3_${globalThis.crypto.randomUUID()}`;
  return `v3_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`;
}

/* Trạng thái giao diện thuần client giữ qua các lần rerun (không chứa dữ liệu hồ sơ). */
const seenToastIds = new Set<string>();
const animatedMessages = new Set<string>();

function messageKey(message: ChatMessage): string {
  return `${message.timestamp ?? 0}:${message.content.length}`;
}

const CreditLensContext = createContext<CreditLensContextType | null>(null);

export function useCreditLens(): CreditLensContextType {
  const ctx = useContext(CreditLensContext);
  if (!ctx) throw new Error("useCreditLens must be used within a StreamlitCreditLensProvider");
  return ctx;
}

/** Bản AI Studio export CreditLensProvider; bản Streamlit không dùng nó. */
export function CreditLensProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

function findNative(selector: string): HTMLElement | null {
  try {
    return document.querySelector<HTMLElement>(selector);
  } catch {
    return null;
  }
}

interface ProviderProps {
  payload: V3AppPayload;
  emit: (event: V3Event) => void;
  children: ReactNode;
}

export function StreamlitCreditLensProvider({ payload, emit, children }: ProviderProps) {
  const [theme, setThemeState] = useState<ThemeMode>(payload.theme);
  const [motionLevel, setMotionState] = useState<MotionLevel>(payload.motion_level);
  const [activePage, setActivePageState] = useState(payload.active_page);
  const [selectedDemoCase, setSelectedDemoState] = useState(payload.selected_demo);
  const [thresholds, setThresholdsState] = useState<Thresholds>(payload.thresholds);
  const [chatRole, setChatRoleState] = useState<ChatRoleKey>(payload.chat.role);
  const [chatModel, setChatModelState] = useState<string>(payload.chat.model);
  const [chatPending, setChatPending] = useState(false);
  const [pendingUser, setPendingUser] = useState<ChatMessage | null>(null);
  const [aiPending, setAiPending] = useState(false);
  const [localToasts, setLocalToasts] = useState<ToastItem[]>([]);
  const [typed, setTyped] = useState<{ key: string; length: number } | null>(null);
  const thresholdTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const send = useCallback(
    (type: string, extra: Record<string, unknown> = {}) => emit({ event_id: newEventId(), type, ...extra }),
    [emit]
  );

  // Mỗi lần Python trả view model mới (rerun), đồng bộ lại theo source of truth.
  useEffect(() => {
    setThemeState(payload.theme);
    setMotionState(payload.motion_level);
    setActivePageState(payload.active_page);
    setSelectedDemoState(payload.selected_demo);
    setThresholdsState(payload.thresholds);
    setChatRoleState(payload.chat.role);
    setChatModelState(payload.chat.model);
    setChatPending(false);
    setPendingUser(null);
    setAiPending(false);
    const fresh = payload.toasts.filter((t) => !seenToastIds.has(t.id));
    if (fresh.length) {
      fresh.forEach((t) => seenToastIds.add(t.id));
      setLocalToasts((prev) => [...prev, ...fresh.map((t) => ({ ...t, timestamp: Date.now() }))].slice(-4));
    }
  }, [payload]);

  // Hiệu ứng gõ cho câu trả lời mới nhất của trợ lý (Python không stream vào component).
  useEffect(() => {
    const last = payload.chat.messages[payload.chat.messages.length - 1];
    if (!last || last.role !== "assistant") return;
    const key = messageKey(last);
    if (animatedMessages.has(key)) return;
    animatedMessages.add(key);
    if (motionLevel === "off" || payload.chat.messages.length <= 1) return;
    const total = last.content.length;
    let length = 0;
    setTyped({ key, length });
    const step = Math.max(4, Math.ceil(total / 60));
    const timer = setInterval(() => {
      length += step;
      if (length >= total) {
        clearInterval(timer);
        setTyped(null);
      } else {
        setTyped({ key, length });
      }
    }, 24);
    return () => clearInterval(timer);
  }, [payload.chat.messages, motionLevel]);

  const chatMessages = useMemo(() => {
    const base = !typed
      ? payload.chat.messages
      : payload.chat.messages.map((m) =>
          messageKey(m) === typed.key ? { ...m, content: m.content.slice(0, typed.length) } : m
        );
    return pendingUser ? [...base, pendingUser] : base;
  }, [payload.chat.messages, typed, pendingUser]);

  const addToast = useCallback((title: string, description?: string, type?: "info" | "success" | "warning") => {
    const id = `local-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setLocalToasts((prev) => [...prev.slice(-3), { id, title, description, type, timestamp: Date.now() }]);
  }, []);
  const dismissToast = useCallback((id: string) => setLocalToasts((prev) => prev.filter((t) => t.id !== id)), []);

  const setTheme = useCallback((t: ThemeMode) => {
    setThemeState(t);
    send("theme", { mode: t });
  }, [send]);
  const setMotionLevel = useCallback((level: MotionLevel) => {
    setMotionState(level);
    try {
      localStorage.setItem("cl_motion_level", level);
    } catch {
      /* iframe/private mode — session Python vẫn giữ giá trị */
    }
    send("motion", { level });
  }, [send]);
  const setActivePage = useCallback((page: string) => {
    const item = payload.navigation.find((n) => n.page === page);
    if (!item || item.locked) return;
    setActivePageState(page);
    send("navigate", { page });
  }, [payload.navigation, send]);
  const setSelectedDemoCase = useCallback((name: string) => {
    setSelectedDemoState(name);
    send("demo_select", { case_name: name });
  }, [send]);
  const openDemoCase = useCallback((name: string) => send("demo_open", { case_name: name }), [send]);
  const clearCase = useCallback(() => send("clear_case"), [send]);
  const updateThreshold = useCallback((key: string, val: number) => {
    setThresholdsState((prev) => ({ ...prev, [key]: val }));
    if (thresholdTimer.current) clearTimeout(thresholdTimer.current);
    // Thanh trượt phát nhiều giá trị khi kéo: chỉ gửi giá trị cuối cùng.
    thresholdTimer.current = setTimeout(() => send("threshold", { key, value: val }), 450);
  }, [send]);
  const resetThresholds = useCallback(() => send("threshold_reset"), [send]);
  const runEvaluation = useCallback(() => send("evaluation_run"), [send]);
  const generateAiExplanation = useCallback(async () => {
    if (aiPending) return;
    setAiPending(true);
    send("ai_generate");
  }, [aiPending, send]);
  const sendChatMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || chatPending) return; // submit rỗng hoặc đang chờ: không gửi event, không gọi LLM
    setChatPending(true);
    setPendingUser({ role: "user", content: trimmed, timestamp: Date.now() });
    send("chat_send", { text: trimmed, role: chatRole, model: chatModel });
  }, [chatPending, chatModel, chatRole, send]);
  const clearChatMessages = useCallback(() => send("chat_clear"), [send]);
  const setChatRole = useCallback((role: ChatRoleKey) => {
    setChatRoleState(role);
    send("chat_role", { role });
  }, [send]);
  const setChatModel = useCallback((model: ChatModelKey) => {
    setChatModelState(model);
    send("chat_model", { model });
  }, [send]);
  const setActiveProvider = useCallback((provider: string) => send("provider", { provider }), [send]);

  const handleFileUpload = useCallback(async (fileList: FileList | File[]) => {
    // Chỉ PDF; bỏ tệp ẩn/hệ thống; giữ đường dẫn tương đối của thư mục con.
    const { accepted, skipped } = filterCaseFiles(collectFromInput(fileList));
    if (skipped.length) {
      addToast(
        "Đã bỏ qua tệp không dùng được",
        skipped.slice(0, 6).map((item) => `${item.path} (${item.reason})`).join(" · "),
        "warning"
      );
    }
    const files = accepted.map(withRelativePath);
    if (!files.length) return;
    // Tệp được chuyển cho st.file_uploader gốc → Python đọc PDF thật (pypdf) qua Privacy Gateway.
    const input = findNative('.st-key-v3_upload_area input[type="file"]') as HTMLInputElement | null;
    if (!input) {
      addToast("Chưa sẵn sàng tải tệp", "Dùng khung tải tệp gốc của Streamlit bên dưới trang.", "warning");
      return;
    }
    try {
      const transfer = new DataTransfer();
      files.forEach((file) => transfer.items.add(file));
      input.files = transfer.files;
      input.dispatchEvent(new Event("change", { bubbles: true }));
      addToast("Đang tải tài liệu", `${files.length} tệp được gửi tới máy chủ Python để trích xuất.`, "info");
    } catch {
      input.click();
    }
  }, [addToast]);

  const exportFile = useCallback((kind: ExportKind) => {
    const button = findNative(`.st-key-v3_dl_${kind} button`);
    if (button) {
      button.click();
      return;
    }
    addToast("Chưa thể tải xuống", "Mở khung xuất báo cáo bên dưới trang để tải tệp do Python tạo.", "warning");
  }, [addToast]);

  const openAiSettings = useCallback(() => setActivePage("8_settings"), [setActivePage]);

  const privacyActions = useMemo(
    () => ({
      setConsent: (value: boolean) => send("privacy_consent", { value }),
      confirm: () => send("privacy_confirm"),
      cancel: () => send("privacy_cancel"),
      addMask: (value: string) => send("privacy_mask_add", { value }),
      removeMask: (code: string) => send("privacy_mask_remove", { code }),
      assignUpload: (id: string, docType: string) => send("upload_assign", { id, doc_type: docType }),
      continueUpload: () => send("upload_continue"),
      cancelUpload: () => send("upload_cancel")
    }),
    [send]
  );

  const assetUrl = useCallback((name: string) => payload.assets[name] ?? "", [payload.assets]);

  const value: CreditLensContextType = {
    theme,
    setTheme,
    motionLevel,
    setMotionLevel,
    activePage,
    setActivePage,
    selectedDemoCase,
    setSelectedDemoCase,
    demoCases: payload.demo_cases,
    thresholds: thresholds as CreditLensContextType["thresholds"],
    updateThreshold: updateThreshold as CreditLensContextType["updateThreshold"],
    resetThresholds,
    result: payload.result as unknown as CreditLensContextType["result"],
    openDemoCase,
    clearCase,
    handleFileUpload,
    aiExplanation: payload.ai.explanation,
    aiLoading: aiPending,
    generateAiExplanation,
    evaluationReport: (payload.pages.evaluation ?? null) as unknown as V2EvaluationPageViewModel,
    runEvaluation,
    chatMessages,
    chatLoading: chatPending,
    chatRole,
    setChatRole,
    chatModel,
    setChatModel,
    sendChatMessage,
    clearChatMessages,
    providers: payload.providers,
    activeProvider: payload.active_provider,
    setActiveProvider,
    customCaseName: payload.custom_case_name,
    caseContext: payload.case_context,
    workflowSteps: payload.workflow,
    processCards: payload.process_cards,
    navigationItems: payload.navigation,
    toasts: localToasts,
    addToast,
    dismissToast,
    serverMode: true,
    exportFile,
    aiConnection: payload.ai_connection,
    chatModels: payload.chat.models,
    openAiSettings,
    privacy: payload.privacy,
    privacyActions,
    assetUrl
  };

  return <CreditLensContext.Provider value={value}>{children}</CreditLensContext.Provider>;
}
