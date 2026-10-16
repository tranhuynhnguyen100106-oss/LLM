import express, { type Request, type Response } from "express";
import cors from "cors";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import { GoogleGenAI } from "@google/genai";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isProduction = process.env.NODE_ENV === "production";
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

const app = express();
app.use(cors());
app.use(express.json({ limit: "10mb" }));

// Helper to reliably resolve the Gemini API key across dev container & production environments
function resolveGeminiApiKey(): string | undefined {
  const isInvalid = (k?: string) => !k || k === "MY_GEMINI_API_KEY" || k.trim() === "";

  if (!isInvalid(process.env.GEMINI_API_KEY)) {
    return process.env.GEMINI_API_KEY?.trim();
  }

  // Check candidate configuration files in container environments
  const candidatePaths = [
    "/app/.dev.env.json",
    path.resolve(process.cwd(), ".dev.env.json"),
    path.resolve(__dirname, ".dev.env.json"),
    path.resolve(__dirname, "../.dev.env.json")
  ];

  for (const p of candidatePaths) {
    try {
      if (fs.existsSync(p)) {
        const parsed = JSON.parse(fs.readFileSync(p, "utf-8"));
        if (!isInvalid(parsed.GEMINI_API_KEY)) {
          return parsed.GEMINI_API_KEY.trim();
        }
      }
    } catch {
      // Continue to next candidate
    }
  }

  return undefined;
}

// Roles & System Instructions configuration
const SYSTEM_ROLES: Record<string, string> = {
  underwriter: `Bạn là Chuyên viên Thẩm định Tín dụng Cấp cao (Senior Underwriter) của hệ thống "Đánh giá tín dụng vay".
Nhiệm vụ của bạn:
1. Đánh giá tính khả thi và rủi ro của hồ sơ cấp tín dụng dựa trên các nguyên tắc tài chính - ngân hàng chính xác.
2. Phân tích định lượng các chỉ số DTI (Debt-to-Income), DSR (Debt Service Ratio), chênh lệch thu nhập kê khai so với sao kê tài khoản ngân hàng.
3. Chỉ ra rõ bằng chứng trích xuất từ tài liệu cụ thể (hợp đồng lao động, sao kê ngân hàng, báo cáo tín dụng CIC).
4. Đưa ra lập luận khách quan, chặt chẽ, thận trọng theo chuẩn mực ngân hàng thương mại Việt Nam.`,

  risk_auditor: `Bạn là Trưởng ban Kiểm soát Rủi ro & Tuân thủ Tín dụng (Credit Risk & Compliance Auditor) của hệ thống "Đánh giá tín dụng vay".
Nhiệm vụ của bạn:
1. Phát hiện dấu hiệu gian lận hồ sơ, mâu thuẫn số liệu thu nhập, nợ tiềm ẩn không kê khai.
2. Đánh giá mức độ vi phạm các ngưỡng cảnh báo rủi ro an toàn hoạt động tín dụng.
3. Yêu cầu làm rõ các điểm nghi vấn và đề xuất biện pháp xác minh bổ sung (thực địa, đối soát bảo hiểm xã hội).`,

  advisor: `Bạn là Trợ lý Thẩm định & Cố vấn Phương án Tài chính (Credit Solution Advisor) của hệ thống "Đánh giá tín dụng vay".
Nhiệm vụ của bạn:
1. Giải thích các thuật ngữ tài chính, cách tính toán DTI, DSR và tác động của việc điều chỉnh tham số ngưỡng.
2. Gợi ý phương án cơ cấu khoản vay, thời hạn hoặc tài sản bảo đảm phù hợp với năng lực trả nợ thực tế của khách hàng.
3. Hỗ trợ chuyên viên tín dụng hoàn thiện tờ trình thẩm định rõ ràng, có cấu trúc.`
};

// API: Multi-turn Chat Endpoint with Gemini
app.post("/api/gemini/chat", async (req: Request, res: Response): Promise<void> => {
  try {
    const {
      messages = [],
      model = "gemini-3.8-flash",
      role = "underwriter",
      caseContext = null
    } = req.body;

    // Validate model selection according to task requirements:
    // 'gemini-4-argon' for complex tasks, 'gemini-3.8-flash' for general tasks, 'gemini-3.1-flash-lite' for fast tasks
    const validModels = ["gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-4-argon"];
    const selectedModel = validModels.includes(model) ? model : "gemini-3.8-flash";

    const baseInstruction = SYSTEM_ROLES[role] || SYSTEM_ROLES.underwriter;

    let contextSection = "";
    if (caseContext) {
      contextSection = `\n\n=== DỮ LIỆU HỒ SƠ TÍN DỤNG ĐANG MỞ ===
Mã hồ sơ: ${caseContext.ma_ho_so ?? "Chưa xác định"}
Khách hàng: ${caseContext.ho_ten ?? "N/A"}
Tình trạng thẩm định: ${caseContext.trang_thai ?? "Chưa đánh giá"}
Thu nhập kê khai: ${caseContext.thu_nhap_ke_khai ? Number(caseContext.thu_nhap_ke_khai).toLocaleString("vi-VN") + " VND" : "N/A"}
Lương thực nhận: ${caseContext.luong_thuc_nhan ? Number(caseContext.luong_thuc_nhan).toLocaleString("vi-VN") + " VND" : "N/A"}
DTI tính toán: ${caseContext.dti !== undefined ? `${(caseContext.dti * 100).toFixed(1)}%` : "N/A"}
DSR tính toán: ${caseContext.dsr !== undefined ? `${(caseContext.dsr * 100).toFixed(1)}%` : "N/A"}
Nguồn thu nhập dùng để tính: ${caseContext.nguon_thu_nhap ?? "N/A"}
Cảnh báo rủi ro phát hiện (${caseContext.canh_bao?.length ?? 0}):
${(caseContext.canh_bao ?? []).map((cb: any, i: number) => `  ${i + 1}. [${cb.severity}] ${cb.name}: ${cb.description}`).join("\n")}
====================================`;
    }

    const systemInstruction = `${baseInstruction}${contextSection}

Quy tắc phản hồi:
- Sử dụng tiếng Việt nghiệp vụ tài chính - ngân hàng chuẩn mực, súc tích, định lượng.
- Luôn căn cứ trên các con số và dữ kiện cụ thể của hồ sơ. Nếu dữ liệu chưa có, hãy nêu rõ.
- Trình bày dạng danh sách hoặc các đoạn phân tích rõ ràng.`;

    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      res.status(400).json({ error: "Yêu cầu danh sách tin nhắn hội thoại (messages)." });
      return;
    }

    // Convert multi-turn history to @google/genai format
    const contents = messages.map((m: { role: string; content: string }) => ({
      role: m.role === "assistant" || m.role === "model" ? "model" : "user",
      parts: [{ text: m.content || "" }]
    }));

    const apiKey = resolveGeminiApiKey();

    if (!apiKey) {
      // Graceful fallback when API key is not yet set in environment
      res.status(200).json({
        success: true,
        text: `[Chế độ dự phòng giả lập do chưa cấu hình GEMINI_API_KEY]: Dựa trên hồ sơ ${caseContext?.ma_ho_so ?? "hiện hành"}, các chỉ số DTI (${caseContext?.dti ? (caseContext.dti * 100).toFixed(1) + "%" : "N/A"}) và DSR (${caseContext?.dsr ? (caseContext.dsr * 100).toFixed(1) + "%" : "N/A"}) đang được theo dõi chặt chẽ theo các quy tắc tín dụng HUB. Vui lòng thiết lập GEMINI_API_KEY trong tab Settings > Secrets để kích hoạt phản hồi trực tiếp từ mô hình ${selectedModel}.`,
        modelUsed: selectedModel,
        isSimulated: true
      });
      return;
    }

    // Initialize GoogleGenAI client with standard User-Agent header
    const ai = new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build"
        }
      }
    });

    // Call Gemini with @google/genai SDK with resilient fallback
    let response;
    let actualModel = selectedModel;
    try {
      response = await ai.models.generateContent({
        model: selectedModel,
        contents,
        config: {
          systemInstruction,
          temperature: 0.25,
          topP: 0.95
        }
      });
    } catch (modelErr: any) {
      if (selectedModel !== "gemini-3.1-flash-lite") {
        console.warn(`Primary model ${selectedModel} failed or busy, falling back to gemini-3.1-flash-lite:`, modelErr?.message);
        actualModel = "gemini-3.1-flash-lite";
        response = await ai.models.generateContent({
          model: "gemini-3.1-flash-lite",
          contents,
          config: {
            systemInstruction,
            temperature: 0.25,
            topP: 0.95
          }
        });
      } else {
        throw modelErr;
      }
    }

    const replyText = response.text || "Không nhận được phản hồi từ mô hình.";

    res.status(200).json({
      success: true,
      text: replyText,
      modelUsed: actualModel
    });
  } catch (error: any) {
    console.error("Gemini API error:", error);
    const rawMsg = typeof error === "string" ? error : error?.message || JSON.stringify(error);
    if (rawMsg.includes("API key not valid") || rawMsg.includes("API_KEY_INVALID") || rawMsg.includes("API_KEY_MISSING")) {
      const caseCode = req.body?.caseContext?.ma_ho_so;
      res.status(200).json({
        success: true,
        text: `[Đánh giá tín dụng vay]: Khóa API Gemini đang chờ cấu hình trong môi trường bí mật (Settings > Secrets). Hệ thống đã ghi nhận câu hỏi và sẵn sàng phân tích ngữ cảnh hồ sơ ${caseCode ? `[${caseCode}]` : "tín dụng"}. Khi khóa API được kết nối, mô hình ${req.body?.model || "gemini-3.8-flash"} sẽ trực tiếp suy luận và đối chiếu bằng chứng đa bước cho bạn.`,
        modelUsed: req.body?.model || "gemini-3.8-flash",
        isSimulated: true
      });
      return;
    }

    res.status(500).json({
      success: false,
      error: error?.message || "Đã xảy ra lỗi khi gọi dịch vụ Gemini AI."
    });
  }
});

// Setup Vite middleware in dev or static files in production
async function startServer() {
  if (!isProduction) {
    const { createServer: createViteServer } = await import("vite");
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa"
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.resolve(__dirname, "dist");
    app.use(express.static(distPath));
    app.use((req, res) => {
      if (req.path.startsWith("/api/")) {
        res.status(404).json({ error: "Endpoint not found" });
        return;
      }
      res.sendFile(path.resolve(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Đánh giá tín dụng vay server running on http://0.0.0.0:${PORT} (${isProduction ? "production" : "development"})`);
  });
}

startServer().catch((err) => {
  console.error("Failed to start server:", err);
  process.exit(1);
});
