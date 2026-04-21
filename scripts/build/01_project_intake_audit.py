#!/usr/bin/env python3
"""Stage-0 intake audit for the environmental policy research project.

This script creates reproducible inventories of:
1. existing project assets (plans, applications, notes, code, policy PDFs);
2. legacy raw policy PDFs under ``预调研/政策文件``;
3. a compact JSON summary for kickoff memos.

It does not modify raw data.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[2]
RAW_POLICY_DIR = ROOT / "预调研" / "政策文件"
METADATA_DIR = ROOT / "data" / "metadata"
DIAGNOSTICS_DIR = ROOT / "output" / "diagnostics"

ASSET_INVENTORY_PATH = METADATA_DIR / "project_asset_inventory.csv"
PDF_INVENTORY_PATH = METADATA_DIR / "policy_pdf_inventory.csv"
SUMMARY_PATH = DIAGNOSTICS_DIR / "intake_summary.json"

TRACKED_SUFFIXES = {
    ".pdf",
    ".docx",
    ".doc",
    ".md",
    ".py",
    ".tex",
    ".html",
    ".png",
    ".jpg",
    ".jpeg",
}


@dataclass
class AssetRow:
    relative_path: str
    category: str
    suffix: str
    size_bytes: int


@dataclass
class PolicyPdfRow:
    file_id: str
    relative_path: str
    stem_title: str
    inferred_year: str
    inferred_level: str
    inferred_doc_family: str
    size_bytes: int
    page_count: int
    char_count: int
    extraction_ok: int


def asset_category(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith("预调研/政策文件/"):
        return "raw_policy_pdf"
    if rel.startswith("预调研/code/"):
        return "legacy_code"
    if rel.startswith("研究计划/"):
        return "research_plan"
    if rel.startswith("项目申报/"):
        return "application_material"
    if rel.startswith("过程文档/"):
        return "process_document"
    if rel.startswith("scripts/"):
        return "canonical_script"
    if rel.startswith("data/metadata/"):
        return "metadata"
    if rel.startswith("memos/"):
        return "memo"
    if rel.startswith("paper/"):
        return "paper"
    return "other"


def infer_year(text: str) -> str:
    matches = re.findall(r"(?:19|20)\d{2}", text)
    return matches[-1] if matches else ""


def infer_level(text: str) -> str:
    local_tokens = ("省", "市", "特区", "自治区")
    if any(token in text for token in local_tokens):
        return "local"
    return "central"


def infer_doc_family(text: str) -> str:
    if "法" in text and "办法" not in text and "方案" not in text and "意见" not in text:
        return "law"
    if "条例" in text:
        return "regulation"
    if "办法" in text or "规则" in text:
        return "administrative_rule"
    if "行动计划" in text or "方案" in text or "意见" in text or "指导" in text:
        return "policy_document"
    if "名录" in text or "导则" in text:
        return "technical_or_catalog"
    return "other"


def iter_project_assets() -> list[AssetRow]:
    rows: list[AssetRow] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if path.name == ".DS_Store":
            continue
        if path.suffix.lower() not in TRACKED_SUFFIXES:
            continue
        rows.append(
            AssetRow(
                relative_path=path.relative_to(ROOT).as_posix(),
                category=asset_category(path),
                suffix=path.suffix.lower(),
                size_bytes=path.stat().st_size,
            )
        )
    return rows


def read_pdf_stats(pdf_path: Path) -> tuple[int, int, int]:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            char_count = 0
            for page in pdf.pages:
                char_count += len(page.extract_text() or "")
        extraction_ok = int(char_count > 0)
        return page_count, char_count, extraction_ok
    except Exception:
        return 0, 0, 0


def iter_policy_pdfs() -> list[PolicyPdfRow]:
    rows: list[PolicyPdfRow] = []
    for pdf_path in sorted(RAW_POLICY_DIR.glob("*.pdf")):
        stem = pdf_path.stem
        file_id = stem.split("_", 1)[0] if "_" in stem else ""
        title = stem.split("_", 1)[1] if "_" in stem else stem
        page_count, char_count, extraction_ok = read_pdf_stats(pdf_path)
        rows.append(
            PolicyPdfRow(
                file_id=file_id,
                relative_path=pdf_path.relative_to(ROOT).as_posix(),
                stem_title=title,
                inferred_year=infer_year(stem),
                inferred_level=infer_level(stem),
                inferred_doc_family=infer_doc_family(stem),
                size_bytes=pdf_path.stat().st_size,
                page_count=page_count,
                char_count=char_count,
                extraction_ok=extraction_ok,
            )
        )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_summary(asset_rows: list[AssetRow], pdf_rows: list[PolicyPdfRow]) -> dict:
    asset_counter = Counter(row.category for row in asset_rows)
    suffix_counter = Counter(row.suffix for row in asset_rows)
    doc_years = sorted(int(row.inferred_year) for row in pdf_rows if row.inferred_year)
    page_counts = [row.page_count for row in pdf_rows]
    char_counts = [row.char_count for row in pdf_rows]
    extraction_ok_count = sum(row.extraction_ok for row in pdf_rows)

    return {
        "project_root": str(ROOT),
        "asset_counts_by_category": dict(asset_counter),
        "asset_counts_by_suffix": dict(suffix_counter),
        "raw_policy_pdf_count": len(pdf_rows),
        "raw_policy_year_min": doc_years[0] if doc_years else None,
        "raw_policy_year_max": doc_years[-1] if doc_years else None,
        "raw_policy_level_counts": dict(Counter(row.inferred_level for row in pdf_rows)),
        "raw_policy_family_counts": dict(Counter(row.inferred_doc_family for row in pdf_rows)),
        "raw_policy_total_pages": sum(page_counts),
        "raw_policy_total_chars": sum(char_counts),
        "raw_policy_avg_pages": round(sum(page_counts) / len(page_counts), 2) if page_counts else 0,
        "raw_policy_avg_chars": round(sum(char_counts) / len(char_counts), 2) if char_counts else 0,
        "raw_policy_extraction_ok_count": extraction_ok_count,
        "structured_dataset_files_present": any(
            row.suffix in {".csv", ".xlsx", ".xls", ".dta", ".parquet"} for row in asset_rows
        ),
        "notes": [
            "This summary inventories current project assets only; it does not validate causal identification.",
            "Policy PDF metadata are inferred from filenames and quick text extraction.",
        ],
    }


def main() -> None:
    asset_rows = iter_project_assets()
    pdf_rows = iter_policy_pdfs()

    write_csv(ASSET_INVENTORY_PATH, [asdict(row) for row in asset_rows])
    write_csv(PDF_INVENTORY_PATH, [asdict(row) for row in pdf_rows])

    summary = build_summary(asset_rows, pdf_rows)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Intake audit completed.")
    print(f"- Project assets inventoried: {len(asset_rows)}")
    print(f"- Raw policy PDFs inventoried: {len(pdf_rows)}")
    print(f"- Policy PDF extraction successes: {summary['raw_policy_extraction_ok_count']}")
    print(f"- Summary written to: {SUMMARY_PATH.relative_to(ROOT)}")
    print(f"- Asset inventory written to: {ASSET_INVENTORY_PATH.relative_to(ROOT)}")
    print(f"- PDF inventory written to: {PDF_INVENTORY_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
