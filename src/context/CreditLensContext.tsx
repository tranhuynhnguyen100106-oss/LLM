import {
  createContext,
  useContext,
  useState,
  useMemo,
  useCallback,
  type ReactNode
} from "react";
import {
  type UnderwritingThresholds,
  DEFAULT_THRESHOLDS,
  type UnderwritingResult,
  runUnderwriting,
  type RawCaseData,
  type DocumentDescriptor
} from "../domain/engine";
import { DEMO_CASES, evaluateDemoCase, getDemoCaseItems } from "../domain/demoCases";
import { runFullEvaluation } from "../domain/evaluation";
import type {
  ThemeMode,
  MotionLevel,
  StatusTone,
  V2EvaluationPageViewModel,
  ProviderStatus,
  NavigationItem,
  WorkflowStep,
  ProcessCard,
  CaseContext,
  DemoCaseItem
} from "../domain/contracts";

import type { ToastItem } from "../components/Toast";
import { askGemini, hasDirectKey, IS_STANDALONE } from "../lib/gemini";
import { buildSystemInstruction, type PromptCaseContext } from "../lib/prompts";

export type ChatRoleKey = "underwriter" | "risk_auditor" | "advisor";
export type ChatModelKey = "gemini-3.8-flash" | "gemini-3.1-flash-lite" | "gemini-4-argon" | (string & {});

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  modelUsed?: string;
  timestamp?: number;
  /** Lỗi 5xx phía Google (bản Streamlit): cho phép người dùng bấm thử lại. */
  retry?: { id: string; label: string; alt_label: string | null };
}

export interface CreditLensContextType {
  theme: ThemeMode;
  setTheme: (t: ThemeMode) => void;
  motionLevel: MotionLevel;
  setMotionLevel: (level: MotionLevel) => void;
  activePage: string;
  setActivePage: (p: string) => void;
  selectedDemoCase: string;
  setSelectedDemoCase: (c: string) => void;
  demoCases: DemoCaseItem[];
  thresholds: UnderwritingThresholds;
  updateThreshold: (key: keyof UnderwritingThresholds, val: number) => void;
  resetThresholds: () => void;
  result: UnderwritingResult | null;
  openDemoCase: (name: string) => void;
  clearCase: () => void;
  handleFileUpload: (files: FileList | File[]) => Promise<void>;
  aiExplanation: string | null;
  aiLoading: boolean;
  generateAiExplanation: () => Promise<void>;
  evaluationReport: V2EvaluationPageViewModel;
  runEvaluation: () => void;
  chatMessages: ChatMessage[];
  chatLoading: boolean;
  chatRole: ChatRoleKey;
  setChatRole: (role: ChatRoleKey) => void;
  chatModel: ChatModelKey;
  setChatModel: (model: ChatModelKey) => void;
  sendChatMessage: (msg: string) => Promise<void>;
  /** Bản Streamlit: gửi lại câu hỏi vừa lỗi 5xx (alt = dùng model Flash khác). 1 lần bấm = 1 request. */
  retryChatMessage?: (retryId: string, alt: boolean) => void;
  clearChatMessages: () => void;
  providers: ProviderStatus[];
  activeProvider: string;
  setActiveProvider: (p: string) => void;
  customCaseName: string | null;
  caseContext: CaseContext;
  workflowSteps: WorkflowStep[];
  processCards: ProcessCard[];
  navigationItems: NavigationItem[];
  toasts: ToastItem[];
  addToast: (title: string, description?: string, type?: "info" | "success" | "warning") => void;
  dismissToast: (id: string) => void;
  /* ---- Các trường tùy chọn: chỉ bản Streamlit (UI v3) cung cấp. Bản Node/standalone bỏ trống. ---- */
  /** Python là backend: không gọi LLM hay lưu khóa ở trình duyệt. */
  serverMode?: boolean;
  /** Xuất tệp qua Python (st.download_button). */
  exportFile?: (kind: ExportKind) => void;
  /** Trạng thái kết nối AI thật do Python cung cấp. */
  aiConnection?: AiConnectionStatus;
  /** Danh sách model lấy từ API của nhà cung cấp (không giả định tên model). */
  chatModels?: ChatModelOption[];
  /** Mở Cài đặt → Kết nối AI (thay cho ô nhập khóa trong chat). */
  openAiSettings?: () => void;
  /** Bước 0 · Bảo mật hồ sơ (Privacy Gateway). */
  privacy?: PrivacyGatewayState;
  privacyActions?: PrivacyGatewayActions;
  /** Logo nhúng (data URI) khi chạy trong component Streamlit. */
  assetUrl?: (name: string) => string;
}

export type ExportKind = "markdown" | "json" | "evaluation_csv" | "evaluation_json";

export interface AiConnectionStatus {
  state: "connected" | "partial" | "disconnected" | "error";
  label: string;
  message: string;
  provider_label: string | null;
  model: string | null;
  source: "secrets" | "session" | null;
}

export interface ChatModelOption {
  id: string;
  label: string;
  badge: string;
}

export interface PrivacyPreviewRow {
  pii_type: string;
  masked_value: string;
  replacement: string;
  document: string;
  page: number | null;
  source: string;
  required: boolean;
}

export interface PrivacyGatewayState {
  state: "empty" | "review" | "done";
  badge_label: string;
  field_count: number;
  public_warning: string;
  consent_text: string;
  consent_given: boolean;
  case_id: string | null;
  rows: PrivacyPreviewRow[];
  counts: { label: string; count: number }[];
  audit: { time: string; event: string; provider: string; fields: number; result: string }[];
  lock_reason: string;
  /** Bảng xác nhận phân loại tài liệu sau khi tải (chỉ bản Streamlit). */
  upload_plan?: UploadPlan | null;
}

export interface UploadPlanRow {
  id: string;
  path: string;
  size_label: string;
  type: string;
  detected_label: string;
  confidence: number;
  basis: string;
  changed: boolean;
  note: string;
}

export interface UploadPlan {
  mode: string;
  rows: UploadPlanRow[];
  skipped: { path: string; reason: string }[];
  options: { value: string; label: string }[];
  issues: { level: "error" | "warning"; text: string }[];
  can_continue: boolean;
}

export interface PrivacyGatewayActions {
  setConsent: (value: boolean) => void;
  confirm: () => void;
  cancel: () => void;
  addMask: (value: string) => void;
  removeMask: (code: string) => void;
  assignUpload?: (id: string, docType: string) => void;
  continueUpload?: () => void;
  cancelUpload?: () => void;
}

const CreditLensContext = createContext<CreditLensContextType | null>(null);

export const NAVIGATION_PAGES: NavigationItem[] = [
  { page: "1_overview", label: "1. Tổng quan và hồ sơ", group: "Hồ sơ", ordinal: 1 },
  { page: "2_extraction", label: "2. Trích xuất tài liệu", group: "Hồ sơ", ordinal: 2 },
  { page: "3_analysis", label: "3. Phân tích tín dụng", group: "Hồ sơ", ordinal: 3 },
  { page: "4_risk", label: "4. Cảnh báo rủi ro", group: "Hồ sơ", ordinal: 4 },
  { page: "5_summary", label: "5. Tóm tắt thẩm định", group: "Hồ sơ", ordinal: 5 },
  { page: "6_methodology", label: "6. Phương pháp và giới hạn", group: "Kiểm chứng", ordinal: 6 },
  { page: "7_evaluation", label: "7. Evaluation", group: "Kiểm chứng", ordinal: 7 },
  { page: "8_settings", label: "8. Cài đặt", group: "Hệ thống", ordinal: 8 }
];

export function CreditLensProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeMode>("system");
  const [activePage, setActivePage] = useState<string>("1_overview");
  const [selectedDemoCase, setSelectedDemoCase] = useState<string>("CASE-03 — Thu nhập không nhất quán");
  const [thresholds, setThresholds] = useState<UnderwritingThresholds>(DEFAULT_THRESHOLDS);
  const [customData, setCustomData] = useState<{
    caseId: string;
    caseName: string;
    data: RawCaseData;
    docs: DocumentDescriptor[];
  } | null>(null);
  const [customCaseName, setCustomCaseName] = useState<string | null>(null);
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [activeProvider, setActiveProvider] = useState<string>("gemini");

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Xin chào, tôi là Trợ lý **Đánh giá tín dụng vay** chạy trên Google Gemini 3.8 Flash. Hãy hỏi tôi về DTI/DSR, đối chiếu thu nhập hoặc các cảnh báo rủi ro của hồ sơ đang mở.",
      modelUsed: "gemini-3.8-flash",
      timestamp: Date.now()
    }
  ]);
  const [chatLoading, setChatLoading] = useState<boolean>(false);
  const [chatRole, setChatRole] = useState<ChatRoleKey>("underwriter");
  const [chatModel, setChatModel] = useState<ChatModelKey>("gemini-3.8-flash");

  const [evaluationReport, setEvaluationReport] = useState<V2EvaluationPageViewModel>(() =>
    runFullEvaluation(DEFAULT_THRESHOLDS, "system")
  );

  // Motion level: 'full' | 'light' | 'off' (stored in localStorage via try/catch, fallback on reduced-motion)
  const [motionLevel, setMotionLevelState] = useState<MotionLevel>(() => {
    try {
      const saved = localStorage.getItem("cl_motion_level");
      if (saved === "full" || saved === "light" || saved === "off") {
        return saved as MotionLevel;
      }
    } catch {
      // LocalStorage access may fail in restricted iframes
    }
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return "light";
    }
    return "full";
  });

  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((title: string, description?: string, type?: "info" | "success" | "warning") => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setToasts((prev) => [...prev.slice(-3), { id, title, description, type, timestamp: Date.now() }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const setMotionLevel = useCallback((level: MotionLevel) => {
    setMotionLevelState(level);
    try {
      localStorage.setItem("cl_motion_level", level);
    } catch {
      // Ignore quota or security errors
    }
    const labels: Record<MotionLevel, string> = {
      full: "Đầy đủ (Độ sâu Ken Burns, Aurora & Parallax)",
      light: "Nhẹ (Ảnh tĩnh, chuyển động tối giản)",
      off: "Tắt (Tĩnh hoàn toàn)"
    };
    addToast("Hiệu ứng giao diện", `Đã lưu: ${labels[level]}`, "info");
  }, [addToast]);

  // Sync with system reduced-motion dynamically
  useState(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handler = (e: MediaQueryListEvent) => {
      if (e.matches) {
        setMotionLevelState((prev) => (prev === "full" ? "light" : prev));
      }
    };
    mq.addEventListener("change", handler);
  });

  const setThemeWithNotify = useCallback((t: ThemeMode) => {
    setTheme(t);
    const labels: Record<ThemeMode, string> = {
      light: "Giao diện Sáng (Light Mode)",
      dark: "Giao diện Tối (Dark Mode)",
      system: "Theo thiết lập hệ điều hành (System)"
    };
    addToast("Chuyển chế độ hiển thị", labels[t], "info");
  }, [addToast]);

  const demoCases = useMemo(() => getDemoCaseItems(), []);

  // Compute result whenever selectedDemoCase, thresholds, or customData changes
  const result: UnderwritingResult | null = useMemo(() => {
    if (customData) {
      return runUnderwriting(customData.caseId, customData.caseName, customData.data, customData.docs, thresholds);
    }
    if (!selectedDemoCase) return null;
    return evaluateDemoCase(selectedDemoCase, thresholds);
  }, [customData, selectedDemoCase, thresholds]);

  const openDemoCase = useCallback((name: string) => {
    setCustomData(null);
    setCustomCaseName(null);
    setSelectedDemoCase(name);
    setAiExplanation(null);
    addToast("Đã tải hồ sơ minh họa", name, "success");
  }, [addToast]);

  const clearCase = useCallback(() => {
    setCustomData(null);
    setCustomCaseName(null);
    setSelectedDemoCase("");
    setAiExplanation(null);
    addToast("Đã đóng hồ sơ", "Chuyển sang trạng thái sẵn sàng tiếp nhận", "info");
  }, [addToast]);

  const updateThreshold = useCallback((key: keyof UnderwritingThresholds, val: number) => {
    setThresholds((prev) => ({ ...prev, [key]: val }));
    addToast("Cập nhật ngưỡng kiểm tra", `Đã điều chỉnh ${String(key)} sang ${val}`, "info");
  }, [addToast]);

  const resetThresholds = useCallback(() => {
    setThresholds(DEFAULT_THRESHOLDS);
    addToast("Khôi phục mặc định", "Đã đặt lại bộ ngưỡng kiểm tra ban đầu", "info");
  }, [addToast]);

  const runEvaluation = useCallback(() => {
    const rep = runFullEvaluation(thresholds, theme);
    setEvaluationReport(rep);
  }, [thresholds, theme]);

  const handleFileUpload = useCallback(
    async (fileList: FileList | File[]) => {
      const files = Array.from(fileList);
      if (files.length === 0) return;

      const caseId = `UPLOAD-${Date.now().toString(36).slice(-4).toUpperCase()}`;
      const caseName = `Hồ sơ tự tải lên (${files.length} tệp)`;

      // Map files to document descriptors
      const docs: DocumentDescriptor[] = files.map((file, idx) => {
        const lower = file.name.toLowerCase();
        let expected: DocumentDescriptor["expectedType"] = "application";
        if (lower.includes("income") || lower.includes("luong") || lower.includes("thu_nhap")) {
          expected = "income";
        } else if (lower.includes("statement") || lower.includes("sao_ke")) {
          expected = "statement";
        } else if (lower.includes("debt") || lower.includes("no")) {
          expected = "debt";
        } else if (idx === 1) {
          expected = "income";
        } else if (idx === 2) {
          expected = "statement";
        }

        return {
          name: file.name,
          expectedType: expected,
          detectedType: expected,
          pages: Math.max(1, Math.ceil(file.size / 50000)),
          status: "Đã trích xuất" as const,
          confidence: 0.95
        };
      });

      // Sample data populated for custom upload
      const uploadedData: RawCaseData = {
        ho_ten_khach_hang: "Trần Anh Vũ (Đã tải lên)",
        don_vi_cong_tac_ke_khai: "Tập đoàn VinaTech",
        don_vi_cong_tac_chung_tu: "Tập đoàn VinaTech",
        chuc_danh_ke_khai: "Trưởng phòng Kỹ thuật",
        chuc_danh_chung_tu: "Trưởng phòng Kỹ thuật",
        ngay_bat_dau_ke_khai: "2021-03-01",
        ngay_bat_dau_chung_tu: "2021-03-01",
        tham_nien_lam_viec_thang: 60,
        thu_nhap_ke_khai: 32_000_000,
        luong_thuc_nhan: 31_500_000,
        thu_nhap_qua_sao_ke: 31_200_000,
        so_tien_de_nghi_vay: 500_000_000,
        thoi_han_vay_thang: 48,
        khoan_tra_du_kien: 11_500_000,
        nghia_vu_no_ke_khai: 3_000_000,
        nghia_vu_no_quan_sat: 3_000_000,
        chi_phi_sinh_hoat: 10_000_000,
        so_du_binh_quan: 25_000_000,
        bien_dong_thu_nhap: 0.08,
        muc_dich_vay: "Mua xe ô tô phục vụ công việc"
      };

      setCustomData({
        caseId,
        caseName,
        data: uploadedData,
        docs
      });
      setCustomCaseName(caseName);
      setAiExplanation(null);
      addToast(
        "Tải tài liệu thành công",
        `Đã nạp ${files.length} tệp chứng từ vào luồng thẩm định`,
        "success"
      );
    },
    [addToast]
  );

  const buildPromptContext = useCallback((): PromptCaseContext | null => {
    if (!result) return null;
    return {
      ma_ho_so: result.ma_ho_so,
      ho_ten: result.du_lieu.ho_ten_khach_hang ?? undefined,
      trang_thai: result.trang_thai,
      thu_nhap_ke_khai: result.du_lieu.thu_nhap_ke_khai ?? undefined,
      luong_thuc_nhan: result.du_lieu.luong_thuc_nhan ?? undefined,
      so_tien_de_nghi_vay: result.du_lieu.so_tien_de_nghi_vay ?? undefined,
      thoi_han_vay_thang: result.du_lieu.thoi_han_vay_thang ?? undefined,
      dti: result.chi_so.find((m) => m.key === "dti")?.raw_value as number | undefined,
      dsr: result.chi_so.find((m) => m.key === "dsr")?.raw_value as number | undefined,
      nguon_thu_nhap: result.nguon_thu_nhap_dung_de_tinh,
      canh_bao: result.canh_bao.map((cb) => ({
        severity: String(cb.severity),
        name: cb.name,
        description: cb.description
      }))
    };
  }, [result]);

  const generateAiExplanation = useCallback(async () => {
    if (!result) return;
    setAiLoading(true);

    // 1) Try a real Gemini 3.8 explanation grounded in the deterministic JSON.
    if (hasDirectKey() || !IS_STANDALONE) {
      try {
        const ctx = buildPromptContext();
        const r = await askGemini({
          model: chatModel,
          systemInstruction: buildSystemInstruction("underwriter", ctx),
          messages: [
            {
              role: "user",
              content:
                "Viết diễn giải hỗ trợ thẩm định cho hồ sơ này theo 4 mục: 1) Khách hàng & khoản vay, 2) Khả năng trả nợ (DTI/DSR), 3) Điểm cần kiểm chứng, 4) Kết luận và điều kiện đề xuất. Tối đa 250 từ."
            }
          ],
          backendPayload: { role: "underwriter", caseContext: ctx },
          onChunk: (t) => setAiExplanation(t)
        });
        if (!r.isSimulated) {
          setAiExplanation(r.text);
          setAiLoading(false);
          return;
        }
      } catch {
        /* fall through to deterministic template */
      }
    }
    await new Promise((res) => setTimeout(res, 300));

    const applicant = result.du_lieu.ho_ten_khach_hang ?? "Khách hàng";
    const amount = result.du_lieu.so_tien_de_nghi_vay ? (result.du_lieu.so_tien_de_nghi_vay / 1e6) + " triệu VND" : "N/A";
    const dtiVal = result.chi_so.find((m) => m.key === "dti")?.value_display ?? "N/A";
    const dsrVal = result.chi_so.find((m) => m.key === "dsr")?.value_display ?? "N/A";
    const risksCount = result.canh_bao.length;

    let narrative = `### Diễn giải hỗ trợ thẩm định (AI Explanation)\n\n`;
    narrative += `**1. Đánh giá khách hàng & Khoản vay:** Hồ sơ **${result.ma_ho_so}** của khách hàng **${applicant}** đề nghị vay **${amount}**. Nguồn thu nhập cơ sở dùng để tính là **${result.nguon_thu_nhap_dung_de_tinh}**.\n\n`;
    narrative += `**2. Chỉ số khả năng trả nợ:** DTI hiện hữu đạt **${dtiVal}** và DSR dự kiến là **${dsrVal}**. `;
    if (result.chi_so.find((m) => m.key === "dsr")?.status_tone === "danger") {
      narrative += `DSR vượt ngưỡng an toàn cảnh báo, cho thấy gánh nặng trả nợ tương lai cần được xem xét thận trọng.\n\n`;
    } else {
      narrative += `Các chỉ số trả nợ nằm trong biên độ chấp nhận được theo ngưỡng minh họa.\n\n`;
    }

    if (risksCount > 0) {
      narrative += `**3. Điểm cần lưu ý kiểm chứng:** Hệ thống phát hiện **${risksCount}** cảnh báo rủi ro xác định. `;
      narrative += `Cụ thể: ${result.canh_bao.map((r) => `*${r.name}* (${r.severity})`).join(", ")}. Cán bộ tín dụng cần kiểm tra các bằng chứng trích xuất đối chiếu trước khi lập tờ trình phê duyệt.\n\n`;
    } else {
      narrative += `**3. Nhất quán dữ liệu:** Toàn bộ dữ kiện thu nhập, đơn vị công tác và nghĩa vụ nợ đồng nhất trên các chứng từ nộp kèm.\n\n`;
    }

    narrative += `**4. Kết luận:** Trạng thái đề xuất: **${result.trang_thai}**. Quyết định cuối cùng thuộc thẩm quyền của Hội đồng Tín dụng theo quy định hiện hành.`;

    setAiExplanation(narrative + "\n\n_(Bản mẫu xác định — nhập khóa Gemini API để có diễn giải từ mô hình.)_");
    setAiLoading(false);
  }, [result, chatModel, buildPromptContext]);

  const clearChatMessages = useCallback(() => {
    setChatMessages([
      {
        role: "assistant",
        content:
          "Đã làm mới phiên hội thoại. Tôi sẵn sàng phân tích và giải đáp các nghiệp vụ tín dụng cùng bạn.",
        modelUsed: chatModel,
        timestamp: Date.now()
      }
    ]);
    addToast("Làm mới hội thoại", "Đã xóa lịch sử tin nhắn của phiên", "info");
  }, [chatModel, addToast]);

  const sendChatMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || chatLoading) return;

      const userMsg: ChatMessage = {
        role: "user",
        content: trimmed,
        timestamp: Date.now()
      };

      const updatedHistory = [...chatMessages, userMsg];
      setChatMessages(updatedHistory);
      setChatLoading(true);

      const placeholderTs = Date.now() + 1;
      try {
        const ctx = buildPromptContext();
        let streamed = false;
        const r = await askGemini({
          model: chatModel,
          systemInstruction: buildSystemInstruction(chatRole, ctx),
          messages: updatedHistory.map((m) => ({ role: m.role, content: m.content })),
          backendPayload: { role: chatRole, caseContext: ctx },
          onChunk: (t) => {
            setChatMessages((prev) => {
              const last = prev[prev.length - 1];
              if (streamed && last?.timestamp === placeholderTs) {
                return [...prev.slice(0, -1), { ...last, content: t }];
              }
              streamed = true;
              return [...prev, { role: "assistant", content: t, modelUsed: chatModel, timestamp: placeholderTs }];
            });
          }
        });
        setChatMessages((prev) => {
          const base = prev[prev.length - 1]?.timestamp === placeholderTs ? prev.slice(0, -1) : prev;
          return [
            ...base,
            {
              role: "assistant",
              content: r.text,
              modelUsed: r.isSimulated ? `${r.modelUsed} · mô phỏng` : r.modelUsed,
              timestamp: placeholderTs
            }
          ];
        });
      } catch (err: any) {
        console.error("Gemini chat error:", err);
        // Fallback response with offline calculated metrics
        const noKey = err?.message === "NO_KEY" || String(err?.message ?? "").startsWith("BACKEND_UNAVAILABLE");
        let fallbackMsg = noKey
          ? "Chưa kết nối Gemini. Bấm nút **🔑 Khóa API** ở đầu khung chat và dán khóa Gemini (lấy miễn phí tại aistudio.google.com/apikey)."
          : "Không thể kết nối với dịch vụ Gemini.";
        if (result) {
          fallbackMsg += `\n\n[Dữ liệu xác minh cục bộ cho hồ sơ ${result.ma_ho_so}]:\n- Trạng thái: ${result.trang_thai}\n- DTI: ${result.chi_so.find((m) => m.key === "dti")?.value_display ?? "N/A"}\n- DSR: ${result.chi_so.find((m) => m.key === "dsr")?.value_display ?? "N/A"}\n- Cảnh báo rủi ro: ${result.canh_bao.length} cảnh báo.`;
        }
        setChatMessages((prev) => [
          ...(prev[prev.length - 1]?.timestamp === placeholderTs ? prev.slice(0, -1) : prev),
          {
            role: "assistant",
            content: noKey ? fallbackMsg : `${fallbackMsg}\n(Chi tiết: ${err?.message || "Lỗi mạng"})`,
            modelUsed: chatModel,
            timestamp: Date.now()
          }
        ]);
        addToast("Lỗi Gemini Chat", "Không thể hoàn thành yêu cầu gửi tin nhắn", "warning");
      } finally {
        setChatLoading(false);
      }
    },
    [chatMessages, chatLoading, chatModel, chatRole, buildPromptContext, addToast]
  );

  const providers: ProviderStatus[] = useMemo(
    () => [
      {
        provider: "gemini",
        label: "Google · Gemini",
        description: "Các model Gemini hỗ trợ phân tích đa phương thức và suy luận ngữ cảnh dài.",
        connected: true,
        active: activeProvider === "gemini",
        model: "gemini-3.8-flash",
        model_count: 5,
        status_label: activeProvider === "gemini" ? "ĐANG DÙNG" : "ĐÃ KẾT NỐI",
        status_tone: activeProvider === "gemini" ? "success" : "info"
      },
      {
        provider: "openai",
        label: "OpenAI · GPT",
        description: "GPT-4o và các model suy luận logic của OpenAI.",
        connected: true,
        active: activeProvider === "openai",
        model: "gpt-4o",
        model_count: 4,
        status_label: activeProvider === "openai" ? "ĐANG DÙNG" : "ĐÃ KẾT NỐI",
        status_tone: activeProvider === "openai" ? "success" : "info"
      },
      {
        provider: "anthropic",
        label: "Anthropic · Claude",
        description: "Claude 3.5 Sonnet với năng lực phân tích tài liệu và cấu trúc chặt chẽ.",
        connected: true,
        active: activeProvider === "anthropic",
        model: "claude-3-5-sonnet",
        model_count: 3,
        status_label: activeProvider === "anthropic" ? "ĐANG DÙNG" : "ĐÃ KẾT NỐI",
        status_tone: activeProvider === "anthropic" ? "success" : "info"
      },
      {
        provider: "deepseek",
        label: "DeepSeek",
        description: "DeepSeek-V3 / DeepSeek-R1 mô hình mã nguồn mở tối ưu tính toán.",
        connected: true,
        active: activeProvider === "deepseek",
        model: "deepseek-chat",
        model_count: 2,
        status_label: activeProvider === "deepseek" ? "ĐANG DÙNG" : "ĐÃ KẾT NỐI",
        status_tone: activeProvider === "deepseek" ? "success" : "info"
      }
    ],
    [activeProvider]
  );

  const caseContext: CaseContext = useMemo(() => {
    if (!result) {
      return {
        case_id: null,
        source: null,
        status_label: "Chưa có hồ sơ đang mở",
        status_tone: "neutral",
        summary: "Tải tài liệu hoặc mở hồ sơ minh họa để bắt đầu."
      };
    }
    const tone: StatusTone =
      result.trang_thai === "REVIEW READY"
        ? "success"
        : result.trang_thai === "HUMAN REVIEW REQUIRED"
        ? "warning"
        : "neutral";

    return {
      case_id: result.ma_ho_so,
      source: customCaseName ? "Tệp người dùng tải lên" : "Hồ sơ minh họa xác định",
      status_label: result.trang_thai,
      status_tone: tone,
      summary: `${result.ten_ho_so} · ${result.fields.length} trường · ${result.canh_bao.length} cảnh báo rủi ro.`
    };
  }, [result, customCaseName]);

  const workflowSteps: WorkflowStep[] = useMemo(() => {
    const isReady = Boolean(result);
    const hasRisks = (result?.canh_bao.length ?? 0) > 0;
    return [
      {
        key: "intake",
        label: "Tiếp nhận hồ sơ",
        description: "Kiểm tra định dạng PDF, lớp văn bản và phân loại loại tài liệu",
        state: isReady ? "complete" : "current",
        status_label: isReady ? "Đã tiếp nhận" : "Hiện tại"
      },
      {
        key: "compute",
        label: "Tính toán xác định",
        description: "Tính toán DTI, DSR, thu nhập khả dụng và đệm số dư bằng công thức",
        state: isReady ? "complete" : "upcoming",
        status_label: isReady ? "Đã tính toán" : "Chưa thực hiện"
      },
      {
        key: "crosscheck",
        label: "Đối chiếu đa chứng từ",
        description: "Kiểm tra chéo thu nhập 3 nguồn, đơn vị công tác và nợ quan sát",
        state: isReady ? (hasRisks ? "warning" : "complete") : "upcoming",
        status_label: isReady ? (hasRisks ? "Có mâu thuẫn" : "Nhất quán") : "Chưa thực hiện"
      },
      {
        key: "human",
        label: "Con người xem xét",
        description: "Chuyên viên tín dụng kiểm tra bằng chứng và đưa ra quyết định cuối",
        state: isReady ? "current" : "upcoming",
        status_label: isReady ? "Chờ chuyên viên" : "Chưa thực hiện"
      }
    ];
  }, [result]);

  const processCards: ProcessCard[] = useMemo(
    () => [
      {
        key: "card-1",
        label: "Tiếp nhận và OCR",
        description: "Kiểm tra tính toàn vẹn của PDF và trích xuất dữ liệu lớp văn bản.",
        state: result ? "complete" : "current"
      },
      {
        key: "card-2",
        label: "Chuẩn hóa Schema",
        description: "Ép kiểu dữ liệu số, ngày tháng, tên công ty và loại bỏ khoảng trắng.",
        state: result ? "complete" : "upcoming"
      },
      {
        key: "card-3",
        label: "Động cơ quy tắc tín dụng",
        description: "Kiểm tra các ngưỡng DTI, DSR, chênh lệch nợ và độ tin cậy trích xuất.",
        state: result ? (result.canh_bao.length > 0 ? "warning" : "complete") : "upcoming"
      },
      {
        key: "card-4",
        label: "Tóm tắt & Xuất báo cáo",
        description: "Tạo tóm tắt có căn cứ bằng chứng phục vụ phê duyệt cấp tín dụng.",
        state: result ? "current" : "upcoming"
      }
    ],
    [result]
  );

  return (
    <CreditLensContext.Provider
      value={{
        theme,
        setTheme: setThemeWithNotify,
        motionLevel,
        setMotionLevel,
        activePage,
        setActivePage,
        selectedDemoCase,
        setSelectedDemoCase,
        demoCases,
        thresholds,
        updateThreshold,
        resetThresholds,
        result,
        openDemoCase,
        clearCase,
        handleFileUpload,
        aiExplanation,
        aiLoading,
        generateAiExplanation,
        evaluationReport,
        runEvaluation,
        chatMessages,
        chatLoading,
        chatRole,
        setChatRole,
        chatModel,
        setChatModel,
        sendChatMessage,
        clearChatMessages,
        providers,
        activeProvider,
        setActiveProvider,
        customCaseName,
        caseContext,
        workflowSteps,
        processCards,
        navigationItems: NAVIGATION_PAGES,
        toasts,
        addToast,
        dismissToast
      }}
    >
      {children}
    </CreditLensContext.Provider>
  );
}

export function useCreditLens() {
  const ctx = useContext(CreditLensContext);
  if (!ctx) {
    throw new Error("useCreditLens must be used within a CreditLensProvider");
  }
  return ctx;
}
