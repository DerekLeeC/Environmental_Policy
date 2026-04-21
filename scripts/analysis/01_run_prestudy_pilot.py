#!/usr/bin/env python3
"""Run a reusable pilot extraction subset for the pre-study pipeline."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRESTUDY_CODE_DIR = PROJECT_ROOT / "预调研" / "code"
PRESTUDY_OUTPUT_DIR = PROJECT_ROOT / "预调研" / "output"
DIAGNOSTICS_DIR = PROJECT_ROOT / "output" / "diagnostics"

if str(PRESTUDY_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(PRESTUDY_CODE_DIR))

from pdf_extractor import process_selected_pdfs  # noqa: E402
from llm_extractor import LLMAuthError, call_llm, extract_all_policies  # noqa: E402


DEFAULT_SAMPLE_FILE = PROJECT_ROOT / "data" / "metadata" / "pilot_validation_sample.csv"


def read_sample_manifest(sample_file: Path) -> list[dict]:
    with sample_file.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def archive_existing_sample_results(run_label: str, file_names: list[str]) -> list[str]:
    """归档当前 pilot 样本对应的旧结果，避免旧文件污染本轮运行。"""
    archived = []
    archive_dir = DIAGNOSTICS_DIR / f"{run_label}_archived_results"
    for file_name in file_names:
        result_path = PRESTUDY_OUTPUT_DIR / "llm_results" / f"{Path(file_name).stem}_result.json"
        if not result_path.exists():
            continue
        archive_dir.mkdir(parents=True, exist_ok=True)
        archived_path = archive_dir / result_path.name
        shutil.move(str(result_path), str(archived_path))
        archived.append(str(archived_path))
    return archived


def run_api_preflight() -> dict:
    """在正式抽取前做最小 API 可用性检查。"""
    response, model_label = call_llm("请只输出 OK。", model_key="deepseek", temperature=0.0)
    if not response:
        raise RuntimeError("LLM API preflight returned empty response")
    return {
        "model_label": model_label,
        "response_excerpt": response[:80],
    }


def build_failed_file_rows(results: list[dict]) -> list[dict]:
    failed_rows = []
    for result in results:
        status = result.get("extraction_status", "unknown")
        if status == "success":
            continue
        failed_rows.append({
            "file_name": result["file_name"],
            "extraction_status": status,
            "valid_model_count": result.get("valid_model_count", 0),
            "failed_model_count": result.get("failed_model_count", 0),
            "invalid_model_details": result.get("invalid_model_details", []),
        })
    return failed_rows


def write_blocker(run_label: str, sample_file: Path, file_names: list[str],
                  blocker_type: str, error_message: str,
                  partial_invalid_results: list[str] | None = None) -> Path:
    blocker_path = DIAGNOSTICS_DIR / f"{run_label}_blocker.json"
    blocker_payload = {
        "run_label": run_label,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": "blocked",
        "sample_file": str(sample_file),
        "files": file_names,
        "blocker_type": blocker_type,
        "error_message": error_message,
        "partial_invalid_results": partial_invalid_results or [],
    }
    write_json(blocker_path, blocker_payload)
    return blocker_path


def build_summary_rows(results: list[dict], manifest_by_name: dict[str, dict]) -> list[dict]:
    rows = []
    for result in results:
        name = result["file_name"]
        manifest = manifest_by_name.get(name, {})
        rows.append({
            "file_name": name,
            "pilot_role": manifest.get("pilot_role", ""),
            "validation_priority": manifest.get("validation_priority", ""),
            "text_source": result.get("text_source", "unknown"),
            "rescued_text_path": result.get("rescued_text_path", ""),
            "char_count": result.get("char_count", 0),
            "total_pages": result.get("total_pages", 0),
            "section_count": result.get("section_count", 0),
            "extraction_status": result.get("extraction_status", "unknown"),
            "valid_model_count": result.get("valid_model_count", 0),
            "failed_model_count": result.get("failed_model_count", 0),
            "agreement_rate": result.get("agreement_rate"),
            "overall_confidence": result.get("overall_confidence"),
            "disagreement_count": len(result.get("disagreements", [])),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pilot extraction on a selected pre-study subset.")
    parser.add_argument("--sample-file", type=Path, default=DEFAULT_SAMPLE_FILE)
    parser.add_argument("--run-label", default=f"pilot_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--preserve-existing-results", action="store_true")
    args = parser.parse_args()

    sample_rows = read_sample_manifest(args.sample_file)
    file_names = [row["file_name"] for row in sample_rows]
    manifest_by_name = {row["file_name"]: row for row in sample_rows}

    print("=" * 72)
    print("Running pre-study pilot subset")
    print(f"Sample file: {args.sample_file}")
    print(f"Run label: {args.run_label}")
    print(f"Files: {len(file_names)}")
    print("=" * 72)

    manifest_path = DIAGNOSTICS_DIR / f"{args.run_label}_manifest.json"
    manifest = {
        "run_label": args.run_label,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "sample_file": str(args.sample_file),
        "prestudy_output_dir": str(PRESTUDY_OUTPUT_DIR),
        "result_files_dir": str(PRESTUDY_OUTPUT_DIR / "llm_results"),
        "files": file_names,
        "status": "started",
    }
    write_json(manifest_path, manifest)

    if not args.preserve_existing_results:
        archived_results = archive_existing_sample_results(args.run_label, file_names)
        if archived_results:
            manifest["archived_existing_results"] = archived_results
            write_json(manifest_path, manifest)

    if not args.skip_preflight:
        try:
            preflight = run_api_preflight()
            manifest["api_preflight"] = preflight
            manifest["status"] = "preflight_passed"
            write_json(manifest_path, manifest)
        except (LLMAuthError, RuntimeError) as exc:
            blocker_path = write_blocker(
                run_label=args.run_label,
                sample_file=args.sample_file,
                file_names=file_names,
                blocker_type="api_authentication" if isinstance(exc, LLMAuthError) else "api_preflight_failed",
                error_message=str(exc),
                partial_invalid_results=[
                    path.name for path in sorted((PRESTUDY_OUTPUT_DIR / "llm_results").glob("*_result.json"))
                    if path.stem.replace("_result", "") in {Path(name).stem for name in file_names}
                ],
            )
            manifest["status"] = "blocked_preflight"
            manifest["blocker_path"] = str(blocker_path)
            write_json(manifest_path, manifest)
            print(f"Blocked before extraction. See: {blocker_path}")
            raise SystemExit(2)

    extracted = process_selected_pdfs(file_names)

    input_summary = [
        {
            "file_name": row["file_name"],
            "pilot_role": manifest_by_name[row["file_name"]]["pilot_role"],
            "expected_text_source": manifest_by_name[row["file_name"]]["expected_text_source"],
            "actual_text_source": row.get("text_source", "unknown"),
            "rescued_text_path": row.get("rescued_text_path", ""),
            "char_count": row.get("char_count", 0),
            "section_count": row.get("section_count", 0),
        }
        for row in extracted
    ]
    write_json(DIAGNOSTICS_DIR / f"{args.run_label}_input_summary.json", input_summary)

    results = extract_all_policies(extracted)
    failed_files = build_failed_file_rows(results)

    concise_summary = build_summary_rows(results, manifest_by_name)
    write_csv(
        DIAGNOSTICS_DIR / f"{args.run_label}_result_summary.csv",
        concise_summary,
        [
            "file_name",
            "pilot_role",
            "validation_priority",
            "text_source",
            "rescued_text_path",
            "char_count",
            "total_pages",
            "section_count",
            "extraction_status",
            "valid_model_count",
            "failed_model_count",
            "agreement_rate",
            "overall_confidence",
            "disagreement_count",
        ],
    )
    write_json(DIAGNOSTICS_DIR / f"{args.run_label}_result_summary.json", concise_summary)

    if failed_files:
        write_json(DIAGNOSTICS_DIR / f"{args.run_label}_failure_summary.json", failed_files)
        manifest["failed_files"] = failed_files
        manifest["status"] = "completed_with_failures"
    else:
        manifest["status"] = "completed"
    write_json(manifest_path, manifest)

    if failed_files and len(failed_files) == len(results):
        blocker_path = write_blocker(
            run_label=args.run_label,
            sample_file=args.sample_file,
            file_names=file_names,
            blocker_type="pilot_extraction_failed",
            error_message="All pilot files returned no valid extraction output.",
            partial_invalid_results=[row["file_name"] for row in failed_files],
        )
        print(f"Pilot finished but all files failed validation. See: {blocker_path}")
        raise SystemExit(3)

    print("-" * 72)
    print("Pilot run complete.")
    print(f"Input summary: {DIAGNOSTICS_DIR / f'{args.run_label}_input_summary.json'}")
    print(f"Result summary csv: {DIAGNOSTICS_DIR / f'{args.run_label}_result_summary.csv'}")
    print(f"Result summary json: {DIAGNOSTICS_DIR / f'{args.run_label}_result_summary.json'}")
    print(f"Manifest: {manifest_path}")
    print("-" * 72)


if __name__ == "__main__":
    main()
