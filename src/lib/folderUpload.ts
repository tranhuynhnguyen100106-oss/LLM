/**
 * Thu thập tệp khi kéo-thả / chọn CẢ THƯ MỤC hồ sơ (đọc đệ quy thư mục con).
 *
 * - Kéo-thả: DataTransferItem.webkitGetAsEntry() → FileSystemDirectoryReader.readEntries (đọc theo lô).
 * - Chọn thư mục: <input webkitdirectory> → File.webkitRelativePath.
 * - Lọc: chỉ .pdf; bỏ tệp ẩn (".", "__MACOSX") và tệp hệ thống (Thumbs.db, desktop.ini, .DS_Store).
 * Đường dẫn tương đối được giữ để Python hiển thị trong bảng xác nhận phân loại.
 */

export interface CollectedFile {
  file: File;
  path: string;
}

export interface SkippedFile {
  path: string;
  reason: string;
}

const SYSTEM_FILES = new Set(["thumbs.db", "desktop.ini", ".ds_store"]);

interface FsEntry {
  isFile: boolean;
  isDirectory: boolean;
  name: string;
  fullPath?: string;
  file?: (ok: (file: File) => void, fail?: (err: unknown) => void) => void;
  createReader?: () => { readEntries: (ok: (entries: FsEntry[]) => void, fail?: (err: unknown) => void) => void };
}

function normalizePath(path: string): string {
  return path
    .replace(/\\/g, "/")
    .split("/")
    .filter((part) => part && part !== "." && part !== "..")
    .join("/");
}

export function isHiddenOrSystem(path: string): boolean {
  const parts = normalizePath(path).split("/");
  if (parts.some((part) => part.startsWith(".") || part === "__MACOSX")) return true;
  return SYSTEM_FILES.has((parts[parts.length - 1] ?? "").toLowerCase());
}

function readFile(entry: FsEntry): Promise<File> {
  return new Promise((resolve, reject) => entry.file!(resolve, reject));
}

function readBatch(reader: ReturnType<NonNullable<FsEntry["createReader"]>>): Promise<FsEntry[]> {
  return new Promise((resolve, reject) => reader.readEntries(resolve, reject));
}

async function walk(entry: FsEntry, prefix: string, out: CollectedFile[]): Promise<void> {
  const path = prefix ? `${prefix}/${entry.name}` : entry.name;
  if (entry.isFile && entry.file) {
    out.push({ file: await readFile(entry), path });
    return;
  }
  if (entry.isDirectory && entry.createReader) {
    const reader = entry.createReader();
    // readEntries trả theo lô (Chrome ~100 mục/lô): đọc tới khi rỗng.
    for (;;) {
      const batch = await readBatch(reader);
      if (!batch.length) break;
      for (const child of batch) await walk(child, path, out);
    }
  }
}

/** Gọi ĐỒNG BỘ trong onDrop (items chỉ còn hiệu lực trong event), phần đọc đệ quy chạy sau. */
export function collectFromDataTransfer(dt: DataTransfer): Promise<CollectedFile[]> {
  const entries: FsEntry[] = [];
  const plain: File[] = [];
  const items = dt.items ? Array.from(dt.items) : [];
  for (const item of items) {
    if (item.kind !== "file") continue;
    const entry = (item as DataTransferItem & { webkitGetAsEntry?: () => FsEntry | null }).webkitGetAsEntry?.();
    if (entry) entries.push(entry);
    else {
      const file = item.getAsFile();
      if (file) plain.push(file);
    }
  }
  if (!entries.length && !plain.length) plain.push(...Array.from(dt.files ?? []));
  return (async () => {
    const out: CollectedFile[] = plain.map((file) => ({ file, path: file.webkitRelativePath || file.name }));
    for (const entry of entries) await walk(entry, "", out);
    return out;
  })();
}

export function collectFromInput(list: FileList | File[]): CollectedFile[] {
  return Array.from(list).map((file) => ({ file, path: file.webkitRelativePath || file.name }));
}

export function filterCaseFiles(items: CollectedFile[]): { accepted: CollectedFile[]; skipped: SkippedFile[] } {
  const accepted: CollectedFile[] = [];
  const skipped: SkippedFile[] = [];
  for (const item of items) {
    const path = normalizePath(item.path) || item.file.name;
    if (isHiddenOrSystem(path)) skipped.push({ path, reason: "tệp ẩn/hệ thống" });
    else if (!path.toLowerCase().endsWith(".pdf")) skipped.push({ path, reason: "không phải PDF" });
    else accepted.push({ file: item.file, path });
  }
  return { accepted, skipped };
}

/** Gắn đường dẫn tương đối vào File để st.file_uploader gửi đúng tên (webkitRelativePath || name). */
export function withRelativePath(item: CollectedFile): File {
  const { file, path } = item;
  if (!path.includes("/") || file.webkitRelativePath === path) return file;
  try {
    Object.defineProperty(file, "webkitRelativePath", { value: path, configurable: true });
    if (file.webkitRelativePath === path) return file;
  } catch {
    /* rơi xuống phương án đổi tên */
  }
  // U+2215 (∕) thay "/" — Python chuẩn hóa lại thành đường dẫn tương đối.
  return new File([file], path.split("/").join("∕"), { type: file.type, lastModified: file.lastModified });
}
