#!/usr/bin/env python3
"""Diagnose whether PDFs are native-text, mixed-layer, or OCR-needed.

This script is designed to be reusable for future policy corpora. It inspects
PDFs with PyMuPDF and classifies them into extractability buckets based on:

1. text/word availability;
2. font presence;
3. image coverage;
4. full-page image prevalence.

Optional outputs:
- CSV report
- JSON summary
- rendered first-page PNGs for flagged PDFs
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "预调研" / "政策文件"
DEFAULT_CSV = ROOT / "output" / "diagnostics" / "pdf_extractability_report.csv"
DEFAULT_JSON = ROOT / "output" / "diagnostics" / "pdf_extractability_summary.json"
DEFAULT_RENDER_DIR = ROOT / "output" / "diagnostics" / "pdf_extractability_renders"


def discover_pdfs(inputs: list[str], recursive: bool) -> list[Path]:
    paths: list[Path] = []
    for raw in inputs:
        path = Path(raw)
        if not path.is_absolute():
            path = (ROOT / path).resolve()
        if path.is_file() and path.suffix.lower() == ".pdf":
            paths.append(path)
        elif path.is_dir():
            iterator = path.rglob("*.pdf") if recursive else path.glob("*.pdf")
            paths.extend(sorted(iterator))
    deduped = []
    seen = set()
    for path in sorted(paths):
        if path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


def safe_rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def run_command(cmd: list[str]) -> str:
    if not shutil.which(cmd[0]):
        return ""
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return completed.stdout.strip()
    except Exception:
        return ""


def pdffonts_count(pdf_path: Path) -> int:
    output = run_command(["pdffonts", str(pdf_path)])
    if not output:
        return 0
    lines = [line for line in output.splitlines() if line.strip()]
    # header + divider + font rows
    if len(lines) <= 2:
        return 0
    return max(0, len(lines) - 2)


def pdfinfo_pages(pdf_path: Path) -> int | None:
    output = run_command(["pdfinfo", str(pdf_path)])
    if not output:
        return None
    for line in output.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def image_coverage(page: fitz.Page) -> tuple[float, bool, int]:
    page_area = float(page.rect.width * page.rect.height) or 1.0
    total_coverage = 0.0
    full_page_like = False
    seen = set()
    image_count = 0
    for image in page.get_images(full=True):
        image_count += 1
        xref = image[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        for rect in rects:
            key = (round(rect.x0, 1), round(rect.y0, 1), round(rect.x1, 1), round(rect.y1, 1))
            if key in seen:
                continue
            seen.add(key)
            coverage = max(0.0, (rect.width * rect.height) / page_area)
            total_coverage += coverage
            if coverage >= 0.85:
                full_page_like = True
    return min(total_coverage, 1.0), full_page_like, image_count


def classify_pdf(metrics: dict) -> tuple[str, str, str]:
    page_count = metrics["page_count"] or 1
    pages_with_text = metrics["pages_with_text"]
    text_ratio = pages_with_text / page_count
    avg_chars = metrics["total_chars"] / page_count
    full_page_image_ratio = metrics["pages_with_full_page_image"] / page_count
    avg_image_coverage = metrics["avg_image_coverage"]
    font_count = metrics["font_count"]

    if text_ratio >= 0.95 and avg_chars >= 40:
        return (
            "native_text",
            "fitz/pdfplumber",
            f"text on {pages_with_text}/{page_count} pages; avg chars/page={avg_chars:.1f}",
        )

    if 0 < text_ratio < 0.95:
        return (
            "mixed_layer_partial_ocr",
            "fitz + page-level OCR fallback",
            f"text on {pages_with_text}/{page_count} pages; mixed text/image layers likely",
        )

    if pages_with_text == 0 and full_page_image_ratio >= 0.8 and font_count == 0:
        return (
            "needs_ocr_scanned",
            "OCR required",
            f"0 text pages; full-page images on {metrics['pages_with_full_page_image']}/{page_count} pages; no fonts detected",
        )

    if pages_with_text == 0 and avg_image_coverage >= 0.5 and font_count == 0:
        return (
            "needs_ocr_scanned",
            "OCR required",
            f"0 text pages; avg image coverage={avg_image_coverage:.2f}; no fonts detected",
        )

    if pages_with_text == 0 and font_count == 0:
        return (
            "needs_ocr_scanned",
            "OCR required",
            "0 text pages and 0 fonts detected; visually readable content is likely image-only or rasterized",
        )

    if pages_with_text == 0 and font_count > 0:
        return (
            "manual_review_encoded_or_protected",
            "manual review / alternate extractor",
            f"0 text pages but {font_count} fonts detected; may be encoded, protected, or malformed",
        )

    return (
        "manual_review_unclear",
        "manual review",
        "insufficient signal for confident classification",
    )


def analyze_pdf(pdf_path: Path) -> dict:
    metrics = {
        "file_path": str(pdf_path),
        "relative_path": safe_rel(pdf_path),
        "file_size_bytes": pdf_path.stat().st_size,
        "page_count": 0,
        "pdfinfo_pages": pdfinfo_pages(pdf_path),
        "total_chars": 0,
        "total_words": 0,
        "pages_with_text": 0,
        "pages_with_full_page_image": 0,
        "avg_image_coverage": 0.0,
        "max_image_coverage": 0.0,
        "image_count": 0,
        "font_count": 0,
        "pdffonts_count": pdffonts_count(pdf_path),
        "status": "error",
        "recommended_extractor": "",
        "reason": "",
    }

    try:
        with fitz.open(pdf_path) as doc:
            metrics["page_count"] = doc.page_count
            total_coverage = 0.0
            font_names = set()
            for page in doc:
                text = page.get_text("text") or ""
                words = page.get_text("words") or []
                metrics["total_chars"] += len(text)
                metrics["total_words"] += len(words)
                if text.strip():
                    metrics["pages_with_text"] += 1

                coverage, full_page_like, image_count = image_coverage(page)
                total_coverage += coverage
                metrics["image_count"] += image_count
                metrics["max_image_coverage"] = max(metrics["max_image_coverage"], coverage)
                if full_page_like:
                    metrics["pages_with_full_page_image"] += 1

                for font_row in page.get_fonts(full=True):
                    if len(font_row) >= 4 and font_row[3]:
                        font_names.add(str(font_row[3]))

            metrics["font_count"] = len(font_names)
            if metrics["page_count"]:
                metrics["avg_image_coverage"] = round(total_coverage / metrics["page_count"], 4)

            status, extractor, reason = classify_pdf(metrics)
            metrics["status"] = status
            metrics["recommended_extractor"] = extractor
            metrics["reason"] = reason
            return metrics
    except Exception as exc:
        metrics["reason"] = f"analysis_error: {exc}"
        return metrics


def render_flagged_pdfs(results: list[dict], render_dir: Path, max_count: int) -> list[str]:
    render_dir.mkdir(parents=True, exist_ok=True)
    rendered = []
    flagged = [
        row for row in results
        if row["status"] in {"needs_ocr_scanned", "mixed_layer_partial_ocr", "manual_review_encoded_or_protected", "manual_review_unclear"}
    ]
    for row in flagged[:max_count]:
        pdf_path = Path(row["file_path"])
        out_path = render_dir / f"{pdf_path.stem}_page1.png"
        with fitz.open(pdf_path) as doc:
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            pix.save(out_path)
        rendered.append(safe_rel(out_path))
    return rendered


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_summary(results: list[dict], rendered: list[str]) -> dict:
    status_counts = Counter(row["status"] for row in results)
    return {
        "project_root": str(ROOT),
        "input_count": len(results),
        "status_counts": dict(status_counts),
        "ocr_ready": shutil.which("tesseract") is not None,
        "rendered_examples": rendered,
        "flagged_relative_paths": [
            row["relative_path"]
            for row in results
            if row["status"] != "native_text"
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose PDF extractability and OCR need.")
    parser.add_argument(
        "inputs",
        nargs="*",
        default=[str(DEFAULT_INPUT)],
        help="PDF files or directories. Defaults to 预调研/政策文件.",
    )
    parser.add_argument("--recursive", action="store_true", help="Recursively search directories for PDFs.")
    parser.add_argument("--csv-out", default=str(DEFAULT_CSV), help="CSV output path.")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON), help="JSON summary output path.")
    parser.add_argument("--render-flagged", action="store_true", help="Render first page of flagged PDFs.")
    parser.add_argument("--render-dir", default=str(DEFAULT_RENDER_DIR), help="Directory for rendered PNGs.")
    parser.add_argument("--max-render", type=int, default=20, help="Maximum number of flagged PDFs to render.")
    args = parser.parse_args()

    pdf_paths = discover_pdfs(args.inputs, recursive=args.recursive)
    if not pdf_paths:
        raise SystemExit("No PDF files found.")

    results = [analyze_pdf(path) for path in pdf_paths]

    csv_out = Path(args.csv_out)
    if not csv_out.is_absolute():
        csv_out = (ROOT / csv_out).resolve()
    write_csv(csv_out, results)

    rendered = []
    if args.render_flagged:
        render_dir = Path(args.render_dir)
        if not render_dir.is_absolute():
            render_dir = (ROOT / render_dir).resolve()
        rendered = render_flagged_pdfs(results, render_dir, args.max_render)

    summary = build_summary(results, rendered)
    json_out = Path(args.json_out)
    if not json_out.is_absolute():
        json_out = (ROOT / json_out).resolve()
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("PDF extractability diagnosis completed.")
    print(f"- Inputs analyzed: {len(results)}")
    print(f"- CSV report: {safe_rel(csv_out)}")
    print(f"- JSON summary: {safe_rel(json_out)}")
    for status, count in sorted(summary["status_counts"].items()):
        print(f"- {status}: {count}")
    if rendered:
        print(f"- Rendered examples: {len(rendered)}")


if __name__ == "__main__":
    main()
