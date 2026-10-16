import { describe, expect, it } from "vitest";

import { collectFromDataTransfer, filterCaseFiles, isHiddenOrSystem, withRelativePath } from "../../src/lib/folderUpload";

type Entry = Record<string, unknown>;

function fileEntry(name: string, body = "%PDF-1.4"): Entry {
  return { isFile: true, isDirectory: false, name, file: (ok: (f: File) => void) => ok(new File([body], name)) };
}

function dirEntry(name: string, children: Entry[]): Entry {
  return {
    isFile: false,
    isDirectory: true,
    name,
    createReader: () => {
      // Trả theo 2 lô rồi rỗng — giống readEntries thật.
      const batches = [children.slice(0, 2), children.slice(2), []];
      return { readEntries: (ok: (e: Entry[]) => void) => ok(batches.shift() ?? []) };
    }
  };
}

function transferOf(entries: Entry[]): DataTransfer {
  return {
    items: entries.map((entry) => ({ kind: "file", webkitGetAsEntry: () => entry, getAsFile: () => null })),
    files: []
  } as unknown as DataTransfer;
}

describe("tải cả thư mục hồ sơ", () => {
  it("đọc đệ quy thư mục con, chỉ giữ PDF, bỏ tệp ẩn/hệ thống và .txt", async () => {
    const root = dirEntry("HOSO-01", [
      fileEntry("don_de_nghi_vay.pdf"),
      fileEntry("sao_ke_ngan_hang.pdf"),
      fileEntry("ghi_chu.txt", "note"),
      fileEntry(".DS_Store", "x"),
      dirEntry("thu_nhap", [fileEntry("chung_tu_thu_nhap.pdf"), fileEntry("._chung_tu_thu_nhap.pdf")]),
      dirEntry("no", [fileEntry("thong_tin_nghia_vu_no.pdf"), fileEntry("Thumbs.db", "x")])
    ]);
    const collected = await collectFromDataTransfer(transferOf([root]));
    expect(collected).toHaveLength(8);
    const { accepted, skipped } = filterCaseFiles(collected);
    expect(accepted.map((item) => item.path).sort()).toEqual([
      "HOSO-01/don_de_nghi_vay.pdf",
      "HOSO-01/no/thong_tin_nghia_vu_no.pdf",
      "HOSO-01/sao_ke_ngan_hang.pdf",
      "HOSO-01/thu_nhap/chung_tu_thu_nhap.pdf"
    ]);
    expect(skipped).toHaveLength(4);
    expect(isHiddenOrSystem("a/__MACOSX/x.pdf")).toBe(true);
  });

  it("giữ đường dẫn tương đối khi chuyển tệp cho st.file_uploader", () => {
    const file = withRelativePath({ file: new File(["%PDF"], "x.pdf"), path: "HOSO/thu_nhap/x.pdf" });
    const sent = file.webkitRelativePath || file.name;
    expect(sent.replace(/∕/g, "/")).toBe("HOSO/thu_nhap/x.pdf");
  });
});
