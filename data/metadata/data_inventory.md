# Data Inventory

Last updated: `2026-04-21`

Generated support files:

- `data/metadata/project_asset_inventory.csv`
- `data/metadata/policy_pdf_inventory.csv`
- `output/diagnostics/intake_summary.json`

## Current asset map

| Asset group | Count | Current location | Classification | Overwrite rule |
|---|---:|---|---|---|
| Raw policy PDFs | 50 | `预调研/政策文件/` | `raw` | Never overwrite |
| Legacy extraction code | 6 files | `预调研/code/` | `code` | Edit only by tracked patch |
| Research plans | 7 files | `研究计划/` | `reference_doc` | Do not overwrite silently |
| Application materials | 5 files | `项目申报/` | `reference_doc` | Do not overwrite silently |
| Process documents | 9 files | `过程文档/` | `reference_doc` | Do not overwrite silently |
| Interim datasets | 0 | `data/interim/` | `interim` | Code-generated only |
| Final datasets | 0 | `data/final/` | `final` | Code-generated only |
| Canonical logs | initialized | `output/logs/` | `output` | Append / date-stamp |

## Raw / Interim / Final / Output rules

### Raw

Treat the following as immutable raw data for now:

- `预调研/政策文件/*.pdf`

These files are the current authoritative source corpus. They may later be mirrored or symlinked into `data/raw/`, but until then they must still be treated as `raw`.

### Interim

No interim datasets currently exist in the canonical pipeline. Future examples:

- OCR text
- extracted JSON text
- chunk-level LLM outputs
- policy exposure construction panels

All interim data must be code-generated and reproducible.

### Final

No final datasets currently exist. Future examples:

- province-year environmental policy exposure panel
- city-year policy diffusion panel
- firm-year matched policy exposure panel

Every final dataset must have:

- source inputs;
- generating script;
- command used;
- timestamp;
- unit of observation;
- row count;
- key variables;
- known limitations.

### Output

Use only code-generated outputs:

- `output/logs/`
- `output/tables/`
- `output/figures/`
- `output/diagnostics/`
- legacy `预调研/output/` for old pipeline products

## Quality-control findings from intake audit

1. Raw policy corpus count: `50`
2. Inferred coverage window: `2009-2024`
3. Quick extraction successes: `47/50`
4. Detailed extractability diagnosis on current folder view:
   - `46` native-text PDFs
   - `1` mixed-layer PDF: `04_环境保护税法_2016.pdf`
   - `4` OCR-needed PDFs in folder view, including one OCR-named duplicate copy
5. Immediate OCR / replacement candidates for the original problematic files:
   - `预调研/政策文件/36_国务院关于加快经济社会发展全面绿色转型的意见_2024公布.pdf`
   - `预调研/政策文件/37_关于推进污水资源化利用的指导意见_2021.pdf`
   - `预调研/政策文件/38_空气质量持续改善行动计划_2023公布.pdf`
6. Existing OCR-named but still non-searchable copy:
   - `预调研/政策文件/36_国务院关于加快经济社会发展全面绿色转型的意见_2024公布(OCR).pdf`
7. Official-source rescue status:
   - `36` rescued to `data/interim/source_text/36_国务院关于加快经济社会发展全面绿色转型的意见_2024公布.txt`
   - `37` rescued to `data/interim/source_text/37_关于推进污水资源化利用的指导意见_2021.txt`
   - `38` rescued to `data/interim/source_text/38_空气质量持续改善行动计划_2023公布.txt`
8. Structured panel data present in repo: `No`

## File status judgment

- `预调研/README.md` and `预调研/政策文件清单.md`: useful legacy documentation, not canonical project ledger
- `研究计划/研究计划.docx` and `项目申报/.../研究计划_解码中国环境政策.docx`: current research intent sources
- `过程文档/0315/*.pdf`: literature/context materials, not data
