/** Client-side file download helpers. */

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

/** Serialize rows to CSV (Excel-compatible, UTF-8 BOM) and download. */
export function downloadCsv(
  columns: string[],
  rows: (string | number | null | undefined)[][],
  filename: string,
): void {
  const escape = (cell: string | number | null | undefined) => {
    const text = cell === null || cell === undefined ? "" : String(cell);
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const csv = [columns, ...rows]
    .map((row) => row.map(escape).join(","))
    .join("\r\n");
  downloadBlob(
    new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }),
    filename,
  );
}
