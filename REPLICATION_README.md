# 复现说明

## 一、推荐复现顺序

1. 盘点政策 PDF 与项目资产

```bash
python3 scripts/build/01_project_intake_audit.py
```

2. 诊断 PDF 是否需要 OCR / 补源

```bash
python3 scripts/build/02_pdf_extractability_diagnose.py --render-flagged
```

3. 对 OCR 阻塞文件执行官方网页补源

```bash
python3 scripts/build/03_policy_source_rescue.py
```

4. 跑 10 份 pilot 子样本

```bash
python3 scripts/analysis/00_run_prestudy_pilot_oneclick.py --preserve-existing-results
```

5. 生成人工核验表

```bash
python3 scripts/analysis/02_build_prestudy_validation_sheet.py
```

6. 生成报告图表与表格

```bash
MPLCONFIGDIR=.mplconfig python3 scripts/analysis/04_build_prestudy_report_assets.py
```

7. 构建 LaTeX 报告

```bash
python3 scripts/analysis/05_build_prestudy_report_latex.py
```

## 二、环境依赖

- Python 3.11+
- `pandoc`、`latexmk`、`xelatex` 用于 PDF 报告构建
- 需要可用的 `SILICONFLOW_API_KEY` 或兼容旧流程的 `DEEPSEEK_API_KEY`

## 三、关键输入与输出

- 输入政策文本：`预调研/政策文件/*.pdf`
- 抽取中间结果：`预调研/output/extracted_text/*.json`
- LLM 结果：`预调研/output/llm_results/*.json`
- 报告表格：`output/tables/prestudy_report/`
- 报告图表：`output/figures/prestudy_report/`
- 预调研报告：`paper/prestudy_report_20260421.pdf`

## 四、结果解释边界

本复现包对应的是预调研阶段：目标是验证文本结构化方案与变量质量，而非直接给出正式因果识别结论。稳定字段与需人工核验字段的划分，请结合 `paper/prestudy_report_20260421.md` 与 `data/metadata/llm_extraction_schema.md` 阅读。
