# 解码中国环境政策：预调研开源复现包

本仓库是“解码中国环境政策”项目的预调研开源复现包，面向 GitHub 公开发布场景整理。它保留了预调研阶段的政策文本、结构化抽取代码、模型结果、图表与报告，同时移除了本机绝对路径、缓存文件、临时编译产物与 API 密钥。

## 包含内容

- `预调研/政策文件/`：50 份政策 PDF 样本
- `预调研/output/extracted_text/`：PDF 文本抽取结果
- `预调研/output/llm_results/`：LLM 结构化结果与汇总结果
- `data/raw/source_html/` 与 `data/interim/source_text/`：3 份 OCR 阻塞文件的官方网页补源缓存
- `data/metadata/`：变量字典、样本清单、抽取 schema、人工核验表与数据说明
- `scripts/build/`：项目盘点、PDF 可抽取性诊断、官方网页补源脚本
- `scripts/analysis/`：pilot 运行、人工核验表生成、图表生成、LaTeX 报告构建脚本
- `output/tables/prestudy_report/` 与 `output/figures/prestudy_report/`：报告表格与图形资产
- `paper/`：预调研报告的 Markdown、LaTeX 与 PDF 版本

## 未包含内容

- 原项目的聊天式工作日志、答辩材料、草稿幻灯片与与预调研无关的辅助目录
- `__pycache__`、`.aux/.log/.fdb_latexmk/.synctex.gz` 等编译缓存
- 已失效 token 的 blocker 日志与仅用于本地调试的临时文件
- 任何硬编码 API key、本机绝对路径和截图缓存

## 快速开始

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置 API

```bash
cp .env.example .env
export SILICONFLOW_API_KEY="YOUR_API_KEY_HERE"
```

本仓库不包含任何真实 API 密钥。预调研代码默认通过环境变量读取 `SILICONFLOW_API_KEY`；如兼容旧流程，也可设置 `DEEPSEEK_API_KEY`。

### 3. 常用复现命令

```bash
make pilot
make validation
make report-assets
make report-latex
```

若本机未安装 `make`，可直接运行 `REPLICATION_README.md` 中给出的命令。

## 目录说明

```text
.
├── README.md
├── REPLICATION_README.md
├── requirements.txt
├── .env.example
├── Makefile
├── LICENSE
├── 预调研/
├── data/
├── scripts/
├── output/
└── paper/
```

## 开源说明

本复现包中的原创代码、衍生元数据和整理文档按仓库 `LICENSE` 发布。样本政策文本与官方网页缓存来自公开政策资料，请在再分发和二次使用时遵循原始来源与适用规则。
