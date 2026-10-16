/**
 * Thay thế src/lib/gemini.ts khi đóng gói cho Streamlit (UI v3).
 *
 * Nguyên tắc dự án: API key chỉ nằm ở Python backend session. Bản Streamlit KHÔNG gọi Gemini
 * từ trình duyệt và KHÔNG đọc/ghi khóa vào localStorage. Mọi lần gọi LLM đi qua event → Python
 * (privacy_gateway + provider hiện có). Module này giữ đúng tên export để component biên dịch được.
 */

export const GEMINI_DEFAULT_MODEL = "gemini-3.8-flash";
export const GEMINI_FALLBACK_MODEL = "gemini-3.1-flash-lite";
export const IS_STANDALONE = false;

export interface GeminiTurn {
  role: "user" | "assistant";
  content: string;
}

export interface GeminiRequest {
  messages: GeminiTurn[];
  model: string;
  systemInstruction: string;
  backendPayload?: Record<string, unknown>;
  temperature?: number;
  onChunk?: (fullTextSoFar: string) => void;
  signal?: AbortSignal;
}

export interface GeminiResponse {
  text: string;
  modelUsed: string;
  transport: "backend" | "direct" | "offline";
  isSimulated?: boolean;
}

const SERVER_ONLY = "SERVER_ONLY: bản Streamlit gọi AI qua máy chủ Python.";

export function getStoredApiKey(): string {
  return "";
}

export function setStoredApiKey(_key: string): void {
  /* Không lưu khóa ở trình duyệt. */
}

export function hasDirectKey(): boolean {
  return false;
}

export async function askGemini(_req: GeminiRequest): Promise<GeminiResponse> {
  throw new Error(SERVER_ONLY);
}

export async function testGeminiKey(_key: string, _model = GEMINI_DEFAULT_MODEL): Promise<string> {
  throw new Error(SERVER_ONLY);
}
