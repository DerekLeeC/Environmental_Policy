#!/usr/bin/env python3
"""Build a long-format human validation sheet from pilot extraction outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_FILE = PROJECT_ROOT / "data" / "metadata" / "pilot_validation_sample.csv"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "预调研" / "output" / "llm_results"
DEFAULT_OUTPUT_CSV = PROJECT_ROOT / "data" / "metadata" / "pilot_validation_sheet.csv"

VALIDATION_FIELDS = [
    "policy_tools",
    "vertical_coordination",
    "implementation_mechanism",
    "referenced_policies",
    "regulatory_stringency",
]


def read_sample_manifest(sample_file: Path) -> list[dict]:
    with sample_file.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_result(result_path: Path) -> dict | None:
    if not result_path.exists():
        return None
    with result_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def json_cell(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def summarize_invalid_details(result: dict) -> str:
    details = result.get("invalid_model_details", [])
    if not details:
        return ""
    return " | ".join(
        f"{item.get('model_label', 'unknown')}: {item.get('error_message', '')}"
        for item in details
    )


def has_substantive_content(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return any(has_substantive_content(item) for item in value)
    if isinstance(value, dict):
        return any(has_substantive_content(v) for v in value.values())
    text = str(value).strip()
    return text not in {"", "未提及", "None", "null"}


def has_substantive_result(result: dict) -> bool:
    final_result = result.get("final_result", {})
    if not isinstance(final_result, dict) or not final_result:
        return False
    return any(has_substantive_content(v) for v in final_result.values())


def classify_result_status(result: dict) -> tuple[str, str]:
    status = result.get("extraction_status", "")
    if status in {"failed_no_valid_model_output", "file_level_error"}:
        return "extraction_failed", summarize_invalid_details(result) or "No valid structured output"
    if not has_substantive_result(result):
        return "extraction_failed", summarize_invalid_details(result) or "No substantive extracted values"
    if status in {"partial_single_model_only", "partial_with_failures"}:
        return "needs_review", summarize_invalid_details(result)
    return "", ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build human validation sheet from pilot extraction results.")
    parser.add_argument("--sample-file", type=Path, default=DEFAULT_SAMPLE_FILE)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    args = parser.parse_args()

    sample_rows = read_sample_manifest(args.sample_file)
    output_rows = []

    for sample in sample_rows:
        file_name = sample["file_name"]
        stem = Path(file_name).stem
        result = load_result(args.results_dir / f"{stem}_result.json")

        if result is None:
            for field in VALIDATION_FIELDS:
                output_rows.append({
                    "file_name": file_name,
                    "pilot_role": sample.get("pilot_role", ""),
                    "validation_priority": sample.get("validation_priority", ""),
                    "text_source": "",
                    "extraction_status": "",
                    "field": field,
                    "consensus_value": "",
                    "agreement_rate": "",
                    "model_values": "",
                    "rescued_text_path": "",
                    "human_value": "",
                    "human_status": "missing_result",
                    "reviewer": "",
                    "reviewed_at": "",
                    "notes": "Result JSON not found",
                })
            continue

        cross_validation = result.get("cross_validation", {})
        disagreements = {
            item["dimension"]: item.get("values_by_model", {})
            for item in cross_validation.get("disagreements", [])
        }
        consensus = result.get("final_result", {})
        per_dim_agreement = result.get("per_dim_agreement", {})
        human_status, status_note = classify_result_status(result)
        extraction_status = result.get("extraction_status", "")
        if not extraction_status and human_status == "extraction_failed":
            extraction_status = "legacy_inferred_failure"

        for field in VALIDATION_FIELDS:
            output_rows.append({
                "file_name": file_name,
                "pilot_role": sample.get("pilot_role", ""),
                "validation_priority": sample.get("validation_priority", ""),
                "text_source": result.get("text_source", ""),
                "extraction_status": extraction_status,
                "field": field,
                "consensus_value": json_cell(consensus.get(field, "")),
                "agreement_rate": per_dim_agreement.get(field, ""),
                "model_values": json_cell(disagreements.get(field, {})),
                "rescued_text_path": result.get("rescued_text_path", ""),
                "human_value": "",
                "human_status": human_status,
                "reviewer": "",
                "reviewed_at": "",
                "notes": status_note,
            })

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file_name",
                "pilot_role",
                "validation_priority",
                "text_source",
                "extraction_status",
                "field",
                "consensus_value",
                "agreement_rate",
                "model_values",
                "rescued_text_path",
                "human_value",
                "human_status",
                "reviewer",
                "reviewed_at",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Validation sheet written to: {args.output_csv}")


if __name__ == "__main__":
    main()
