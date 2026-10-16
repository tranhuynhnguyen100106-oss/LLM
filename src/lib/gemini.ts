/**
 * Gemini client for "Đánh giá tín dụng vay".
 *
 * Two transport modes:
 *  1. Backend proxy (`/api/gemini/chat`) — used when the Node server (server.ts) is running and
 *     holds GEMINI_API_KEY server-side. This is the recommended mode for production.
 *  2. Direct browser call to the Gemini REST API with a key the user enters in the app. Used for
 *     the standalone static build (any static host / independent domain) where no backend exists.
 *     The key is kept only in this browser's localStorage.
 */

export const GEMINI_DEFAULT_MODEL = "gemini-3.8-flash";
export const GEMINI_FALLBACK_MODEL = "gemini-3.1-flash-lite";
const API_BASE = "https://generativelanguage.googleapis.com/v1beta/models";
const KEY_STORAGE = "dtv_gemini_api_key";

export interface GeminiTurn {
  role: "user" | "assistant";
  content: string;
}

export interface GeminiRequest {
  messages: GeminiTurn[];
  model: string;
  systemInstruction: string;
  /** Backend extra fields (role key + structured case context), ignored in direct mode. */
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

declare const __STANDALONE__: boolean | undefined;
export const IS_STANDALONE: boolean =
  typeof __STANDALONE__ !== "undefined" ? Boolean(__STANDALONE__) : false;

export function getStoredApiKey(): string {
  try {
    return localStorage.getItem(KEY_STORAGE)?.trim() ?? "";
  } catch {
    return "";
  }
}

export function setStoredApiKey(key: string): void {
  try {
    if (key.trim()) localStorage.setItem(KEY_STORAGE, key.trim());
    else localStorage.removeItem(KEY_STORAGE);
  } catch {
    /* storage unavailable (private mode) — key lives only for this session */
  }
  sessionKey = key.trim();
}

let sessionKey = "";
function currentKey(): string {
  return getStoredApiKey() || sessionKey;
}

export function hasDirectKey(): boolean {
  return currentKey().length > 0;
}

function toContents(messages: GeminiTurn[]) {
  // Gemini requires the conversation to start with a user turn.
  const firstUser = messages.findIndex((m) => m.role === "user");
  return messages.slice(Math.max(0, firstUser)).map((m) => ({
    role: m.role === "assistant" ? "model" : "user",
    parts: [{ text: m.content }]
  }));
}

async function callDirect(req: GeminiRequest, model: string): Promise<GeminiResponse> {
  const key = currentKey();
  if (!key) throw new Error("NO_KEY");

  const body = JSON.stringify({
    contents: toContents(req.messages),
    systemInstruction: { parts: [{ text: req.systemInstruction }] },
    generationConfig: { temperature: req.temperature ?? 0.25, topP: 0.95 }
  });

  const res = await fetch(`${API_BASE}/${encodeURIComponent(model)}:streamGenerateContent?alt=sse`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-goog-api-key": key },
    body,
    signal: req.signal
  });

  if (!res.ok || !res.body) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      detail = j?.error?.message || detail;
    } catch {
      /* ignore */
    }
    const err = new Error(detail) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let text = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data:")) continue;
      try {
        const chunk = JSON.parse(line.slice(5).trim());
        const parts = chunk?.candidates?.[0]?.content?.parts ?? [];
        for (const p of parts) if (typeof p.text === "string" && !p.thought) text += p.text;
        req.onChunk?.(text);
      } catch {
        /* partial line — ignore */
      }
    }
  }
  return { text: text || "Mô hình không trả về nội dung.", modelUsed: model, transport: "direct" };
}

async function callBackend(req: GeminiRequest): Promise<GeminiResponse> {
  const res = await fetch("/api/gemini/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: req.messages,
      model: req.model,
      systemInstruction: req.systemInstruction,
      ...req.backendPayload
    }),
    signal: req.signal
  });
  const type = res.headers.get("content-type") ?? "";
  if (!res.ok || !type.includes("application/json")) {
    throw new Error(`BACKEND_UNAVAILABLE (${res.status})`);
  }
  const data = await res.json();
  if (!data?.success) throw new Error(data?.error || "Lỗi từ máy chủ Gemini");
  req.onChunk?.(data.text);
  return {
    text: data.text,
    modelUsed: data.modelUsed || req.model,
    transport: "backend",
    isSimulated: Boolean(data.isSimulated)
  };
}

/**
 * Sends a request to Gemini, choosing the best available transport.
 * Order: direct (if the user saved a key) → backend → error "NO_KEY".
 * Falls back to the lite model once if the primary model is busy (429/5xx).
 */
export async function askGemini(req: GeminiRequest): Promise<GeminiResponse> {
  if (hasDirectKey()) {
    try {
      return await callDirect(req, req.model);
    } catch (e) {
      const status = (e as { status?: number }).status ?? 0;
      if ((status === 429 || status >= 500 || status === 404) && req.model !== GEMINI_FALLBACK_MODEL) {
        return await callDirect(req, GEMINI_FALLBACK_MODEL);
      }
      throw e;
    }
  }

  if (!IS_STANDALONE) {
    const r = await callBackend(req);
    // Backend without a configured key returns a simulated reply; surface it as such.
    return r;
  }

  throw new Error("NO_KEY");
}

/** Quick connectivity check used by the settings panel. */
export async function testGeminiKey(key: string, model = GEMINI_DEFAULT_MODEL): Promise<string> {
  const res = await fetch(`${API_BASE}/${encodeURIComponent(model)}:generateContent`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-goog-api-key": key.trim() },
    body: JSON.stringify({
      contents: [{ role: "user", parts: [{ text: "Trả lời đúng một từ: OK" }] }],
      generationConfig: { maxOutputTokens: 16 }
    })
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(j?.error?.message || `HTTP ${res.status}`);
  return model;
}
