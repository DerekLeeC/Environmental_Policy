#!/usr/bin/env python3
"""One-click runner for the pre-study pilot subset."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "output" / "logs"
PILOT_SCRIPT = PROJECT_ROOT / "scripts" / "analysis" / "01_run_prestudy_pilot.py"
VALIDATION_SCRIPT = PROJECT_ROOT / "scripts" / "analysis" / "02_build_prestudy_validation_sheet.py"
PY_COMPILE_TARGETS = [
    PROJECT_ROOT / "预调研" / "code" / "config.py",
    PROJECT_ROOT / "预调研" / "code" / "pdf_extractor.py",
    PROJECT_ROOT / "预调研" / "code" / "llm_extractor.py",
    PROJECT_ROOT / "预调研" / "code" / "main.py",
    PROJECT_ROOT / "预调研" / "code" / "visualizer.py",
    PROJECT_ROOT / "scripts" / "analysis" / "01_run_prestudy_pilot.py",
    PROJECT_ROOT / "scripts" / "analysis" / "02_build_prestudy_validation_sheet.py",
]


def run_and_tee(cmd: list[str], log_file) -> int:
    process = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
        log_file.write(line)
    return process.wait()


def main() -> None:
    parser = argparse.ArgumentParser(description="One-click runner for the environmental-policy pre-study pilot.")
    parser.add_argument("--run-label", default=f"pilot_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--preserve-existing-results", action="store_true")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"00_run_prestudy_pilot_oneclick_{args.run_label}.log"

    env = os.environ.copy()
    if not env.get("SILICONFLOW_API_KEY") and not env.get("DEEPSEEK_API_KEY"):
        print("未检测到 SILICONFLOW_API_KEY 或 DEEPSEEK_API_KEY。")
        print("请先配置环境变量，再运行一键脚本。")
        raise SystemExit(2)

    with log_path.open("w", encoding="utf-8") as log_file:
        header = (
            f"[oneclick] run_label={args.run_label}\n"
            f"[oneclick] log_path={log_path}\n"
            f"[oneclick] cwd={PROJECT_ROOT}\n"
        )
        print(header, end="")
        log_file.write(header)

        compile_cmd = [sys.executable, "-m", "py_compile", *[str(p) for p in PY_COMPILE_TARGETS]]
        print("[oneclick] Step 1/3: py_compile")
        log_file.write("[oneclick] Step 1/3: py_compile\n")
        compile_code = run_and_tee(compile_cmd, log_file)
        if compile_code != 0:
            print(f"[oneclick] 编译检查失败，退出码 {compile_code}")
            raise SystemExit(compile_code)

        pilot_cmd = [sys.executable, str(PILOT_SCRIPT), "--run-label", args.run_label]
        if args.skip_preflight:
            pilot_cmd.append("--skip-preflight")
        if args.preserve_existing_results:
            pilot_cmd.append("--preserve-existing-results")
        print("[oneclick] Step 2/3: run pilot subset")
        log_file.write("[oneclick] Step 2/3: run pilot subset\n")
        pilot_code = run_and_tee(pilot_cmd, log_file)

        validation_cmd = [sys.executable, str(VALIDATION_SCRIPT)]
        print("[oneclick] Step 3/3: build validation sheet")
        log_file.write("[oneclick] Step 3/3: build validation sheet\n")
        validation_code = run_and_tee(validation_cmd, log_file)
        if validation_code != 0:
            print(f"[oneclick] 人工核验表生成失败，退出码 {validation_code}")
            raise SystemExit(validation_code)

    print(f"[oneclick] 日志已保存: {log_path}")
    print(f"[oneclick] pilot manifest: {PROJECT_ROOT / 'output' / 'diagnostics' / f'{args.run_label}_manifest.json'}")
    print(f"[oneclick] validation sheet: {PROJECT_ROOT / 'data' / 'metadata' / 'pilot_validation_sheet.csv'}")

    if pilot_code != 0:
        print(f"[oneclick] Pilot 未完全成功，退出码 {pilot_code}。请查看 blocker / log。")
        raise SystemExit(pilot_code)

    print("[oneclick] Pilot 已完成。")


if __name__ == "__main__":
    main()
