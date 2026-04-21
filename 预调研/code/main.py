"""
预调研全流程主脚本
═══════════════════════════════════════════════════════
解码中国环境政策：基于大语言模型的政策文本分析 —— 预调研
═══════════════════════════════════════════════════════

方法论参考（文献支撑）：
  [1] Fang, Li & Lu (2025) "Decoding China's Industrial Policies", NBER WP 33814
      → 多LLM独立提取+交叉验证 "integrating multiple LLMs to mitigate hallucinations"
  [2] Zhang, Chen & Guo (2018), Journal of Public Economics
      → 中央监督与地方环境执法的制度参照
  [3] Kostka & Nahm (2017), The China Quarterly
      → recentralization / local discretion / vertical coordination
  [4] Chen, Liao & Yi (2025), Journal of Public Policy
      → policy textual learning / horizontal vs vertical learning
  [5] Gilardi, Alizadeh & Kubli (2023), PNAS
      → LLM 零样本文本标注的基准证据
  [6] Le Mens & Gallego (2025), Political Analysis
      → asking-and-averaging / 聚合提高稳定性
  [7] Fonseca & Cohen (2024), ACL Findings
      → annotation guideline 必须明确
  [8] Törnberg (2025), Social Science Computer Review
      → 跨语言、解释性任务下的 LLM 标注能力与边界

流程：
  Phase 1 → PDF文本提取与预处理
  Phase 2 → 多模型独立并行提取 + 交叉验证合并
  Phase 3 → 综合分析与可视化
  Phase 4 → 生成预调研报告
"""
import json
import time
import datetime
from pathlib import Path

from config import OUTPUT_DIR, LLM_RESULTS_DIR, FIGURES_DIR, MODEL_CONFIGS, LITERATURE_REFERENCES
from pdf_extractor import process_all_pdfs
from llm_extractor import extract_all_policies, generate_analysis_report
from visualizer import generate_all_figures


def generate_report_markdown(all_results: list[dict], analysis_text: str) -> str:
    """生成完整的预调研Markdown报告"""

    # ─── 统计数据 ───
    total_files = len(all_results)
    total_chars = sum(r.get("char_count", 0) for r in all_results)
    total_pages = sum(r.get("total_pages", 0) for r in all_results)
    source_counts = {}
    for r in all_results:
        src = r.get("text_source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    # ─── 模型间一致率 ───
    agreement_list = []
    for r in all_results:
        a = r.get("agreement_rate")
        if a is not None:
            agreement_list.append(float(a))
    avg_agreement = sum(agreement_list) / len(agreement_list) if agreement_list else None
    agreement_base_n = len(agreement_list)

    # ─── 各模型自校验置信度 ───
    model_conf_sums = {}
    model_conf_counts = {}
    for r in all_results:
        for label, conf in r.get("per_model_confidence", {}).items():
            if conf is not None:
                model_conf_sums[label] = model_conf_sums.get(label, 0) + float(conf)
                model_conf_counts[label] = model_conf_counts.get(label, 0) + 1

    # ─── 构建提取结果汇总表 ───
    table_rows = []
    for i, r in enumerate(all_results):
        fr = r.get("final_result", {})
        name = fr.get("policy_name", r.get("file_name", ""))
        if len(name) > 25:
            name = name[:25] + "…"
        ptype = fr.get("policy_type", "")
        tools = fr.get("policy_tools", [])
        if isinstance(tools, list):
            tools_str = "、".join(tools)
        else:
            tools_str = str(tools)
        if len(tools_str) > 20:
            tools_str = tools_str[:20] + "…"
        intensity = fr.get("policy_intensity", "")
        tone = fr.get("policy_tone", "")
        level = fr.get("gov_level", "")
        agree = r.get("agreement_rate", "N/A")
        if isinstance(agree, (int, float)):
            agree = f"{agree:.1%}"
        table_rows.append(
            f"| {i+1} | {name} | {ptype} | {tools_str} | {intensity} | {tone} | {level} | {agree} |"
        )
    table_str = "\n".join(table_rows)

    # ─── 多模型独立提取对比表 ───
    comparison_rows = []
    for r in all_results:
        fname = r.get("file_name", "")[:20]
        mr_list = r.get("model_results", [])
        for mr in mr_list:
            label = mr.get("model_label", "?")
            fr = mr.get("final_result", {})
            tools = str(fr.get("policy_tools", ""))[:25]
            ptype = fr.get("policy_type", "")
            tone = fr.get("policy_tone", "")
            conf = mr.get("overall_confidence", "N/A")
            if isinstance(conf, (int, float)):
                conf = f"{conf:.2f}"
            comparison_rows.append(f"| {fname} | {label} | {ptype} | {tools} | {tone} | {conf} |")
    comparison_str = "\n".join(comparison_rows) if comparison_rows else "| 暂无数据 | - | - | - | - | - |"

    # ─── 维度一致性统计 ───
    dim_agreement_sums = {}
    dim_agreement_counts = {}
    for r in all_results:
        for dim, rate in r.get("per_dim_agreement", {}).items():
            if rate is None:
                continue
            dim_agreement_sums[dim] = dim_agreement_sums.get(dim, 0) + rate
            dim_agreement_counts[dim] = dim_agreement_counts.get(dim, 0) + 1
    dim_table_rows = []
    for dim in sorted(dim_agreement_sums.keys()):
        avg = dim_agreement_sums[dim] / dim_agreement_counts[dim]
        dim_table_rows.append(f"| {dim} | {avg:.1%} |")
    dim_table_str = "\n".join(dim_table_rows) if dim_table_rows else "| 暂无数据 | - |"

    # ─── 分歧汇总 ───
    disagree_rows = []
    for r in all_results:
        fname = r.get("file_name", "")[:15]
        for d in r.get("disagreements", []):
            dim = d["dimension"]
            vals = d.get("values_by_model", {})
            vals_str = " / ".join(f"{k}: {str(v)[:20]}" for k, v in vals.items())
            disagree_rows.append(f"| {fname} | {dim} | {vals_str} |")
    disagree_str = "\n".join(disagree_rows[:30]) if disagree_rows else "| 暂无 | - | - |"

    # ─── 模型使用统计 ───
    model_info_lines = []
    for key, cfg in MODEL_CONFIGS.items():
        avg_conf = ""
        if cfg["label"] in model_conf_sums and model_conf_counts.get(cfg["label"], 0) > 0:
            avg_c = model_conf_sums[cfg["label"]] / model_conf_counts[cfg["label"]]
            avg_conf = f"（平均自校验置信度: {avg_c:.2f}）"
        model_info_lines.append(f"  - **{cfg['label']}**：独立全流程提取 {avg_conf}")
    model_info_str = "\n".join(model_info_lines)

    now = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")

    avg_agreement_text = f"{avg_agreement:.1%}" if avg_agreement is not None else "N/A"

    report = f"""# 预调研报告：基于多LLM独立提取与交叉验证的中国环境政策文本结构化分析

> 项目：解码中国环境政策——基于大语言模型的政策文本分析
> 生成时间：{now}
> 分析文件数：{total_files} 份

### 使用模型（多模型独立提取 + 交叉验证）

{model_info_str}

---

## 一、预调研概述

### 1.1 研究目的

本预调研旨在验证基于多个大语言模型（LLM）独立提取与交叉验证的方法论，对中国环境政策文本
进行多维度结构化信息提取。

### 1.2 文献支撑与理论框架

本研究的方法论设计和分析维度得到以下前沿文献的支撑：

| 文献 | 贡献 |
|------|------|
| Fang, Li & Lu (2025), NBER WP 33814 | 多LLM独立提取+交叉验证架构，降低幻觉风险 |
| Kostka & Nahm (2017), The China Quarterly | 央地关系、再集中化与地方裁量 |
| Zhang, Chen & Guo (2018), J. Public Economics | 中央监督如何改变地方环境执法 |
| Chen, Liao & Yi (2025), Journal of Public Policy | 环境政策文本学习：横向学习强于纵向学习 |
| Gilardi et al. (2023), PNAS | LLM 零样本标注可行，但要做人工验证 |
| Le Mens & Gallego (2025), Political Analysis | asking-and-averaging 有助于提高文本定位稳定性 |
| Fonseca & Cohen (2024), ACL Findings | annotation guideline 设计会直接影响抽取质量 |
| Törnberg (2025), Social Science Computer Review | LLM 在解释性、跨语境任务中的能力与边界 |

### 1.3 方法论设计

**核心思路**：每个模型独立完成全流程，多模型结果交叉对比后合并（Fang et al. 2025）

```
PDF文件 → 文本提取(pdfplumber) → 并行多模型独立提取：
  ┌──→ [DeepSeek-V3.2] Zero-shot → Few-shot → 自校验 → 独立结果A ─┐
  ├──→ [MiniMax-M2.5]  Zero-shot → Few-shot → 自校验 → 独立结果B ─┼─→ 交叉验证 → 共识结果
  └──→ [Kimi-K2.5]     Zero-shot → Few-shot → 自校验 → 独立结果C ─┘
```

**关键设计**：
- 三个模型完全独立完成各自的全流程，互不影响（Fang et al. 2025）
- 分类维度（政策类型/力度/语气/层级/规制严格度/目标层次）采用多数投票
- 列表维度（政策工具/行业/污染物/执行机制/引用政策）采用共识合并（≥2个模型提及）
- 文本维度（政策名称/文号/纵向协调等）取信息量最大的版本
- 长文本按章节切块后聚合，减少单次长上下文遗漏
- 对无文字层 PDF，允许使用 `official_html_rescue` 的官方正文替代源
- 自动生成分歧报告，标注模型间不一致的维度

### 1.4 提取维度设计（文献驱动）

本研究提取 **21 个直接抽取维度**，其中最关键的、与主线研究问题直接相关的维度如下：

| 新增维度 | 文献来源 | 说明 |
|---------|---------|------|
| regulatory_stringency | 项目自定义 ordinal coding | 规制严格度1-5分 |
| policy_objective_level | 项目自定义 IPOO 编码 | 投入/过程/产出/结果 |
| vertical_coordination | Kostka & Nahm (2017) | 央地纵向协调机制 |
| implementation_mechanism | Zhang et al. (2018) | 执行保障机制列表 |
| referenced_policies | Chen et al. (2025) | 引用的上位法/政策学习入口 |

### 1.5 样本选取

从2009—2024年间选取了{total_files}份具有代表性的中国环境政策文件，覆盖：
- **政府层级**：中央法律、国务院行政法规、部门规章、地方性法规
- **政策工具类型**：命令控制型、经济激励型、市场机制型、信息公开型、自愿型
- **污染领域**：大气、水、土壤、固废、噪声、碳排放、海洋、综合

---

## 二、数据预处理结果

### 2.1 文本提取统计

| 指标 | 数值 |
|------|------|
| 文件总数 | {total_files} 份 |
| 总页数 | {total_pages} 页 |
| 总字符数 | {total_chars:,} 字 |
| 平均页数 | {total_pages / total_files:.1f} 页/份 |
| 平均字符数 | {total_chars / total_files:,.0f} 字/份 |

### 2.2 文本质量评估

本轮文本来源并不完全同质，需按 provenance 区分：
- `pdfplumber` 直接提取：{source_counts.get('pdfplumber', 0)} 份
- `official_html_rescue` 官方正文替代源：{source_counts.get('official_html_rescue', 0)} 份
- 其他/未知：{source_counts.get('unknown', 0)} 份

说明：
- 多数 PDF 为可直接抽取文本的原生电子文件；
- 少数无文字层文件已通过官方网页正文 rescue 进入可复现流程；
- 因而本项目不能再假设“全部 PDF 都无需 OCR / rescue”。

---

## 三、多模型提取结果与交叉验证

### 3.1 共识结果汇总

| # | 政策名称 | 类型 | 政策工具 | 力度 | 语气 | 层级 | 模型一致率 |
|---|---------|------|---------|------|------|------|-----------|
{table_str}

### 3.2 各模型独立提取结果对比

| 文件 | 模型 | 类型 | 政策工具 | 语气 | 自校验置信度 |
|------|------|------|---------|------|-------------|
{comparison_str}

### 3.3 各维度模型间一致率

| 维度 | 平均一致率 |
|------|----------|
{dim_table_str}

### 3.4 模型间分歧明细（部分）

| 文件 | 分歧维度 | 各模型取值 |
|------|---------|----------|
{disagree_str}

### 3.5 整体交叉验证评估

- **平均模型间一致率**：{avg_agreement_text}
- **可计算一致率的文件数**：{agreement_base_n}/{total_files}
- **一致率≥80%的文件数**：{sum(1 for a in agreement_list if a >= 0.8)}/{agreement_base_n if agreement_base_n else total_files}
- **一致率≥60%的文件数**：{sum(1 for a in agreement_list if a >= 0.6)}/{agreement_base_n if agreement_base_n else total_files}

---

## 四、综合分析

{analysis_text}

---

## 五、可视化图表

### 图1：政策工具类型分布
![政策工具分布](figures/fig1_policy_tools.png)

### 图2：政策力度×语气矩阵
![力度语气矩阵](figures/fig2_intensity_tone.png)

### 图3：污染物类型覆盖矩阵
![污染物覆盖](figures/fig3_pollutant_coverage.png)

### 图4：政策发布时间线
![时间线](figures/fig4_timeline.png)

### 图5：多模型交叉验证一致率
![一致率](figures/fig5_confidence.png)

### 图6：目标行业覆盖频率
![行业频率](figures/fig6_industry_freq.png)

---

## 六、方法论评估与改进建议

### 6.1 多模型独立提取方法的优势（Fang et al. 2025）

1. **模型间独立性验证**：三个模型各自独立完成全流程，结果的一致性可作为可靠性指标
2. **幻觉检测**：模型间分歧点往往指向潜在的幻觉或歧义，便于人工复核
3. **信息互补**：不同模型对文本的理解角度不同，合并后覆盖更全面
4. **自动质量控制**：交叉验证一致率为每份文件提供了量化的质量分数

### 6.2 发现的问题

1. **语气判断主观性强**：LLM对"严厉/中性/温和"的判断标准不够统一，模型间分歧率高
2. **长文本仍有遗漏风险**：超过12000字的文件即使分段，也可能在合并阶段损失跨章节信息
3. **量化目标提取不稳定**：不同文件的量化目标表述差异大，提取格式不统一
4. **列表维度粒度差异**：不同模型对行业/工具的列举粒度不同，影响合并效果
5. **项目自定义维度验证需求高**：`regulatory_stringency`、`policy_objective_level` 等维度必须做人工标注校验
6. **文本来源异质**：原生 PDF 与 official-source rescue 并存，后续必须跟踪来源差异是否影响抽取稳定性

### 6.3 改进建议

1. **语气量化**：设计更细粒度的语气指标体系（如使用1-5分制+关键词锚定）
2. **重复提问与聚合**：对关键维度引入 asking-and-averaging 式重复抽取，而不是单次作答
3. **加权投票**：根据各模型在不同维度上的历史准确率，分配差异化权重
4. **人工标注基准**：优先完成{total_files}份文件的人工标注，作为Gold Standard
5. **Prompt迭代**：针对低一致率维度，把 annotation guideline 写得更明确、更可执行
6. **政策网络分析**：利用`referenced_policies`构建政策引用网络，并区分中央来源与同级来源
7. **央地对比**：利用vertical_coordination分析央地政策传导（Kostka & Nahm 2017）
8. **来源分层抽检**：优先人工复核 rescue 文件、低一致率文件、长文本文件

### 6.4 大规模扩展可行性

| 指标 | 本次预调研 | 大规模扩展(预估) |
|------|----------|----------------|
| 文件数 | {total_files} | 1,000+ |
| 提取维度 | 21 | 21（可扩展） |
| 平均token/份 | ~4,000 | ~4,000 |
| API调用次数/份 | 9次(3模型×3阶段) | 9次（或择优缩减） |
| 使用模型 | DeepSeek-V3.2+MiniMax-M2.5+Kimi-K2.5 独立全流程 | 择优选择（可扩展GLM-5/Qwen） |
| 并行处理 | 模型间+文件间双层并行 | 相同策略 |
| 预估总成本 | < ¥30 | ¥3,000-6,000 |
| 预估耗时 | ~10-15分钟（并行加速） | ~5-8小时 |

---

## 七、参考文献

"""

    # 动态添加参考文献
    for ref in LITERATURE_REFERENCES:
        report += f"{ref['id']}. {ref['text']}\n\n"

    report += """---

## 八、结论

本预调研验证了基于多LLM独立提取与交叉验证的方法论用于环境政策文本结构化分析的可行性。
参考 Fang, Li & Lu (2025) "integrating multiple LLMs to mitigate hallucinations" 的思路，
三个模型（DeepSeek-V3.2、MiniMax-M2.5、Kimi-K2.5）各自独立完成全流程提取，再通过多数投票、共识合并等
策略得到最终结果。

基于环境治理、policy textual learning 与 LLM 标注方法三条文献线索，
本研究将提取维度从16个扩展到21个，并把 `text_source` / `official_html_rescue`
纳入 provenance 链条，使“文本从哪里来、如何被抽取、哪些维度最不稳”都可以回溯。

后续工作应重点解决低一致率维度的Prompt优化、长文本分段处理优化、新增维度的验证、以及
构建人工标注的Gold Standard数据集，为大规模数据库构建奠定基础。

---

*报告由预调研分析管线自动生成*
"""
    return report


def main():
    """主流程"""
    start_time = time.time()

    print("═" * 60)
    print("  解码中国环境政策 —— 预调研全流程")
    print("  方法论：多模型独立提取 + 并行处理 + 交叉验证")
    print("═" * 60)

    # ─── Phase 1: 文本提取 ───
    print("\n" + "▶" * 3 + " Phase 1: PDF文本提取与预处理")
    print("─" * 50)
    extracted_texts = process_all_pdfs()
    print(f"\n✓ Phase 1 完成：{len(extracted_texts)}份文件已提取")

    # ─── Phase 2: 多模型并行提取 + 交叉验证 ───
    print("\n" + "▶" * 3 + " Phase 2: 多模型独立并行提取 + 交叉验证")
    print("─" * 50)
    all_results = extract_all_policies(extracted_texts)
    print(f"\n✓ Phase 2 完成：{len(all_results)}份文件已提取")

    # 汇总一致率
    rates = [r.get("agreement_rate", 0) for r in all_results if r.get("agreement_rate") is not None]
    if rates:
        print(f"  平均模型间一致率: {sum(rates)/len(rates):.1%}")

    # ─── Phase 3: 综合分析 ───
    print("\n" + "▶" * 3 + " Phase 3: 综合分析与可视化")
    print("─" * 50)

    summary_data = []
    for r in all_results:
        summary_data.append({
            "file_name": r["file_name"],
            "final_result": r["final_result"],
            "overall_confidence": r["overall_confidence"],
        })
    generate_all_figures(summary_data)

    analysis_text = generate_analysis_report(all_results)
    print("✓ 综合分析报告已生成")

    # ─── Phase 4: 生成报告 ───
    print("\n" + "▶" * 3 + " Phase 4: 生成预调研报告")
    print("─" * 50)
    report = generate_report_markdown(all_results, analysis_text)

    report_path = OUTPUT_DIR / "预调研报告.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✓ 报告已保存: {report_path}")

    raw_path = LLM_RESULTS_DIR / "all_raw_results.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print("\n" + "═" * 60)
    print(f"  全流程完成！耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    print(f"  报告位置: {report_path}")
    print(f"  图表位置: {FIGURES_DIR}")
    print(f"  原始数据: {raw_path}")
    print("═" * 60)


if __name__ == "__main__":
    main()
