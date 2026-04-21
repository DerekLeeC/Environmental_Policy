.PHONY: intake diagnose rescue pilot validation report-assets report-latex

intake:
	python3 scripts/build/01_project_intake_audit.py

diagnose:
	python3 scripts/build/02_pdf_extractability_diagnose.py --render-flagged

rescue:
	python3 scripts/build/03_policy_source_rescue.py

pilot:
	python3 scripts/analysis/00_run_prestudy_pilot_oneclick.py --preserve-existing-results

validation:
	python3 scripts/analysis/02_build_prestudy_validation_sheet.py

report-assets:
	MPLCONFIGDIR=.mplconfig python3 scripts/analysis/04_build_prestudy_report_assets.py

report-latex:
	python3 scripts/analysis/05_build_prestudy_report_latex.py
