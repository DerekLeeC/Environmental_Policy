# 解码中国环境政策 —— 基于大语言模型的政策文本分析（预调研）

## 项目简介

本项目是"解码中国环境政策"研究的**预调研阶段**，旨在利用多个大语言模型（LLM）对中国环境政策文本进行多维度结构化信息提取，验证方法可行性并改进研究设计。

预调研选取 **50 份**具有代表性的环境政策文件（2009—2024），覆盖法律、行政法规、部门规章和地方性法规等多种政策类型，涉及大气、水、土壤、固废、噪声、碳排放、海洋等多个环境领域。

## 文献支撑

本研究的方法论设计和分析维度以“环境治理 + 政策文本学习 + LLM 标注方法”三条文献线索为基础：

| 文献 | 核心贡献 | 对本项目的影响 |
|------|---------|--------------|
| **Fang, Li & Lu (2025)** NBER WP 33814 | 多LLM独立提取+交叉验证 | 架构设计：三模型独立全流程+共识合并 |
| **Kostka & Nahm (2017)** The China Quarterly | 央地关系与环境治理 | 新增维度：纵向协调机制 |
| **Zhang, Chen & Guo (2018)** J. Public Economics | 中央督察与政策执行 | 新增维度：执行保障机制 |
| **Chen, Liao & Yi (2025)** Journal of Public Policy | policy textual learning | 新增维度：政策引用与学习关系 |
| **Gilardi et al. (2023)** PNAS | LLM 零样本文本标注基准 | 必须保留人工验证与错误审计 |
| **Le Mens & Gallego (2025)** Political Analysis | asking-and-averaging | 后续关键维度采用重复提问聚合 |
| **Fonseca & Cohen (2024)** ACL Findings | annotation guideline 明确性 | Prompt 与变量字典必须更清晰 |
| **Törnberg (2025)** Social Science Computer Review | 解释性任务中的 LLM 标注表现 | 强化对主观维度的边界意识 |

说明：
- 先前 README 中引用的 `Tong, Ye & Hao (2024)` 当前无法从一手来源核实，已移出核心文献集。
- `regulatory_stringency` 与 `policy_objective_level` 目前是项目自定义编码维度，不再错误归因给单篇文献。

## 技术路线

```
PDF 政策文件（50份）
  │
  ▼
Phase 1  文本提取与预处理（pdfplumber）
  │       └─ 自动识别章节结构
  ▼
Phase 2  多模型独立并行提取 + 交叉验证
  │
  │  ┌──→ [DeepSeek-V3.2] Zero-shot → Few-shot → 自校验 → 独立结果A ─┐
  ├──┤                                                               │
  │  ├──→ [MiniMax-M2.5]  Zero-shot → Few-shot → 自校验 → 独立结果B ─┼→ 交叉验证 → 共识结果
  │  │                                                               │
  │  └──→ [Kimi-K2.5]     Zero-shot → Few-shot → 自校验 → 独立结果C ─┘
  │       └─ 超长文本自动分段提取 + 官方正文 rescue 接入
  ▼
Phase 3  综合分析与可视化（matplotlib）
  │
  ▼
Phase 4  生成预调研报告（Markdown）
```

## 项目结构

```
Environment_Policy/
├── README.md                 # 项目说明（本文件）
├── 技术路线图.pdf              # 研究技术路线图
├── 政策文件清单.md             # 50份政策文件完整清单与来源
├── 政策文件/                   # 50 份样本 PDF 政策文件
│   ├── 01-10                 # 已有10份
│   └── 11-50                 # 待下载40份（运行download_policies.py）
├── code/                     # 源代码
│   ├── config.py             # 配置（API、模型、20维度定义、文献列表）
│   ├── pdf_extractor.py      # 模块1：PDF 文本提取与预处理
│   ├── llm_extractor.py      # 模块2：多模型独立提取 + 交叉验证
│   ├── visualizer.py         # 模块3：可视化图表生成
│   ├── main.py               # 主脚本（全流程入口）
│   └── download_policies.py  # 政策文件批量下载脚本
└── output/                   # 输出目录（运行后自动生成）
```

## 提取维度（21个直接抽取变量）

| 维度 | 说明 | 文献来源 |
|------|------|---------|
| `policy_name` | 政策全称 | Fang et al. (2025) |
| `doc_number` | 文号 | Fang et al. (2025) |
| `issuing_authority` | 发布机构 | Fang et al. (2025) |
| `issue_date` | 发布日期 | Fang et al. (2025) |
| `effective_date` | 生效日期 | Fang et al. (2025) |
| `policy_type` | 政策类型 | Fang et al. (2025) |
| `policy_tools` | 政策工具类型列表 | sticks / carrots / sermons + policy mix 思路 |
| `target_industries` | 目标行业列表 | — |
| `pollutant_types` | 污染物类型列表 | — |
| `policy_intensity` | 政策力度 | — |
| `policy_tone` | 政策语气 | — |
| `regulatory_stringency` | 规制严格度(1-5) | 项目自定义 ordinal coding |
| `gov_level` | 政府层级 | — |
| `vertical_coordination` | 央地纵向协调 | **Kostka & Nahm (2017)** |
| `policy_objective_level` | 目标层次 | 项目自定义 IPOO 编码 |
| `implementation_mechanism` | 执行保障机制 | **Zhang et al. (2018)** |
| `key_measures` | 核心措施 | — |
| `quantitative_targets` | 量化目标 | — |
| `penalty_provisions` | 处罚条款 | — |
| `innovation_points` | 政策创新点 | — |
| `referenced_policies` | 引用政策列表 | **Chen et al. (2025)** |

更进一步的派生变量（如 `local_flexibility_score`、`accountability_index`、`text_similarity_to_central`）不直接在 v1 抽取，而是在后续脚本中构造，见 `data/metadata/llm_extraction_schema.md`。

## 快速开始

### 1. 环境准备

```bash
pip install openai pdfplumber matplotlib numpy
```

### 2. 下载政策文件

```bash
cd code
python download_policies.py
```

或参照 [政策文件清单.md](政策文件清单.md) 手动下载。

### 3. 配置 API 密钥

```bash
export SILICONFLOW_API_KEY="YOUR_API_KEY_HERE"
```

### 4. 运行

```bash
cd code
python main.py
```

### 5. 预调研 pilot 一键运行

如果你想先跑当前已经治理好的 10 份 MVP 样本，而不是直接全量 50 份，推荐从项目根目录运行：

```bash
python3 scripts/analysis/00_run_prestudy_pilot_oneclick.py
```

这条命令会自动完成：

1. 语法编译检查；
2. pilot subset 抽取；
3. manifest / blocker 落盘；
4. `pilot_validation_sheet.csv` 生成人工核验表；
5. 保存运行日志到 `output/logs/`。

说明：
- 默认会把当前 pilot 样本对应的旧结果归档到 `output/diagnostics/<run_label>_archived_results/`，避免旧文件污染本轮结果；
- 如果只想保留旧结果不动，可加 `--preserve-existing-results`；
- 如果 API token 无效，脚本会在 preflight 阶段停止，并生成 blocker 文件，而不是继续盲跑。

## 参考文献

1. Fang, H., Li, M., & Lu, G. (2025). *Decoding China's Industrial Policies*. NBER Working Paper No. 33814.
2. Zhang, B., Chen, X., & Guo, H. (2018). Does central supervision enhance local environmental enforcement? *Journal of Public Economics*, 164, 70–90.
3. Kostka, G., & Nahm, J. (2017). Central–local relations: Recentralization and environmental governance in China. *The China Quarterly*, 231, 567–582.
4. Chen, W., Liao, L., & Yi, H. (2025). Multilevel policy textual learning in Chinese local environmental policies. *Journal of Public Policy*, 45(3), 500–521.
5. Gilardi, F., Alizadeh, M., & Kubli, M. (2023). ChatGPT outperforms crowd workers for text-annotation tasks. *PNAS*, 120(30), e2305016120.
6. Le Mens, G., & Gallego, A. (2025). Positioning political texts with large language models by asking and averaging. *Political Analysis*, 33(3), 274–282.
7. Fonseca, M., & Cohen, S. (2024). Can large language models follow concept annotation guidelines? *Findings of ACL 2024*.
8. Törnberg, P. (2025). Large language models outperform expert coders and supervised classifiers at annotating political social media messages. *Social Science Computer Review*, 43(6), 1181–1195.
9. Lo, K. (2014). China's low-carbon city initiatives: The implementation gap and the limits of the target responsibility system. *Habitat International*, 42, 236–244.

## 样本文件

完整50份文件清单见 [政策文件清单.md](政策文件清单.md)。
