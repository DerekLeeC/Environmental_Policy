#!/usr/bin/env python3
"""Fetch official HTML sources for PDFs that are image-only or OCR-blocked.

This rescue path is preferable to OCR whenever an official searchable text source
exists. The script:

1. reads `data/metadata/policy_source_map.csv`;
2. downloads raw HTML snapshots;
3. extracts normalized plain text;
4. writes a rescue summary for later provenance checks.
"""

from __future__ import annotations

import csv
import json
import re
import ssl
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
SOURCE_MAP = ROOT / "data" / "metadata" / "policy_source_map.csv"
RAW_HTML_DIR = ROOT / "data" / "raw" / "source_html"
INTERIM_TEXT_DIR = ROOT / "data" / "interim" / "source_text"
SUMMARY_PATH = ROOT / "output" / "diagnostics" / "policy_source_rescue_summary.json"


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def load_rows() -> list[dict]:
    with SOURCE_MAP.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=60, context=context) as resp:
        return resp.read().decode("utf-8", errors="replace")


def normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    candidates = []
    selectors = [
        "#UCAP-CONTENT",
        ".TRS_Editor",
        ".pages_content",
        ".article",
        ".content",
        "article",
        "main",
        "body",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if not node:
            continue
        text = normalize_text(node.get_text("\n", strip=True))
        if len(text) >= 200:
            candidates.append(text)
    if candidates:
        return max(candidates, key=len)
    return normalize_text(soup.get_text("\n", strip=True))


def file_safe_stem(row: dict) -> str:
    rel = row["pdf_relative_path"]
    stem = Path(rel).stem
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "_", stem)


def main() -> None:
    rows = load_rows()
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
    INTERIM_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for row in rows:
        stem = file_safe_stem(row)
        html_out = RAW_HTML_DIR / f"{stem}.html"
        text_out = INTERIM_TEXT_DIR / f"{stem}.txt"

        status = "ok"
        error = ""
        try:
            html = fetch_html(row["source_url"])
            html_out.write_text(html, encoding="utf-8")
            text = extract_visible_text(html)
            text_out.write_text(text, encoding="utf-8")
            char_count = len(text)
        except Exception as exc:
            status = "error"
            error = str(exc)
            char_count = 0

        summary_rows.append({
            "file_id": row["file_id"],
            "pdf_relative_path": row["pdf_relative_path"],
            "source_url": row["source_url"],
            "source_type": row["source_type"],
            "html_snapshot": html_out.relative_to(ROOT).as_posix(),
            "text_output": text_out.relative_to(ROOT).as_posix(),
            "status": status,
            "char_count": char_count,
            "error": error,
        })

    SUMMARY_PATH.write_text(
        json.dumps(summary_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Policy source rescue completed.")
    print(f"- Source map entries: {len(rows)}")
    print(f"- Summary: {SUMMARY_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
