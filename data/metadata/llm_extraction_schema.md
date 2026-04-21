# LLM Extraction Schema

Status: `v1.1`
Last updated: `2026-04-21`

## Purpose

本文件把预调研中的 LLM 文本抽取任务写成一个可审计 schema，避免变量定义只存在于代码 prompt 里。

## A. Current direct extraction variables (v1)

### 1. Document identity

- `policy_name`
- `doc_number`
- `issuing_authority`
- `issue_date`
- `effective_date`

### 2. Policy classification

- `policy_type`
- `policy_tools`
- `policy_intensity`
- `policy_tone`
- `regulatory_stringency`

### 3. Regulatory scope

- `target_industries`
- `pollutant_types`
- `gov_level`

### 4. Governance / implementation

- `vertical_coordination`
- `policy_objective_level`
- `implementation_mechanism`

### 5. Substantive content

- `key_measures`
- `quantitative_targets`
- `penalty_provisions`
- `innovation_points`
- `referenced_policies`

## B. Provenance fields that must travel with every record

这些字段不是 LLM 直接抽取的“研究变量”，但必须伴随结果保存：

- `file_name`
- `file_path`
- `text_source`
  - `pdfplumber`
  - `official_html_rescue`
  - `unknown`
- `rescued_text_path`
- `total_pages`
- `char_count`
- `section_count`

## C. Audit artifacts already captured by code

单模型、单阶段层面必须保留：

- prompt
- model id / label
- temperature
- chunk index
- input excerpt
- raw response
- parsed output
- self-verification result
- confidence scores

这些内容当前保存在 `预调研/output/llm_results/*.json` 的 `stage_audit` 中。

## D. Variables intentionally NOT extracted directly in v1

以下变量很重要，但暂不建议让 LLM 在 v1 直接端到端生成：

- `local_flexibility_score`
- `accountability_index`
- `text_similarity_to_central`
- `text_similarity_to_peer`
- `central_reference_share`
- `tool_mix_entropy`
- `policy_layering_density`

原因：

1. 这些变量需要规则计算、跨文档比较或二次编码；
2. 直接让 LLM 一步产出，容易把 measurement 与 interpretation 混在一起；
3. 先把直接可核验的文本变量做稳，再构造 derived variables，更符合可复现研究流程。

## E. Planned derived variables (v2)

### 1. `accountability_index`

构造思路：
- 是否存在明确考核
- 是否存在问责或处罚
- 是否指定监督主体
- 是否要求定期报告

### 2. `local_flexibility_score`

构造思路：
- 是否要求地方制定配套细则
- 是否允许因地制宜
- 是否给出固定量化指标
- 是否保留地方裁量空间

### 3. `policy_learning_source`

构造思路：
- `central`
- `peer`
- `mixed`
- `unclear`

依据来源：
- `referenced_policies`
- 文本相似度
- 发文层级

### 4. `text_similarity_to_central` / `text_similarity_to_peer`

不应由 LLM 主观打分，而应通过独立脚本计算。

## F. Human validation priorities

优先抽检三类样本：

1. `official_html_rescue` 文件
2. 模型一致率低的文件
3. 长文本 / 章节较多的文件

优先抽检五个维度：

- `policy_tools`
- `vertical_coordination`
- `implementation_mechanism`
- `referenced_policies`
- `regulatory_stringency`

人工核验记录应写入：

- `data/metadata/llm_validation_log_template.csv`

## G. Go / no-go rule for moving to phase 2

只有在以下条件满足时，才建议从“预调研抽取”升级到“扩样本 + 传导面板”：

1. provenance 无缺口；
2. rescue 文件处理稳定；
3. 关键维度通过人工核验；
4. 关键变量存在足够 variation。
