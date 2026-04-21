#!/usr/bin/env python3
"""Build reusable tables and publication-style figures for the pre-study report."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402


SUMMARY_JSON = PROJECT_ROOT / "预调研" / "output" / "llm_results" / "all_results_summary.json"
RAW_JSON = PROJECT_ROOT / "预调研" / "output" / "llm_results" / "all_raw_results.json"
INVENTORY_CSV = PROJECT_ROOT / "data" / "metadata" / "policy_pdf_inventory.csv"
VALIDATION_SAMPLE_CSV = PROJECT_ROOT / "data" / "metadata" / "pilot_validation_sample.csv"
VALIDATION_SHEET_CSV = PROJECT_ROOT / "data" / "metadata" / "pilot_validation_sheet.csv"

TABLE_DIR = PROJECT_ROOT / "output" / "tables" / "prestudy_report"
FIG_DIR = PROJECT_ROOT / "output" / "figures" / "prestudy_report"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "prestudy_report"

RUC_RED = "#971F30"
RUC_RED_DARK = "#6D1423"
RUC_RED_SOFT = "#F4E8EB"
INK = "#2B2325"
MUTED = "#6D6063"
LINE = "#D8CCD0"
BG = "#FBF8F7"
ACCENT_BLUE = "#2C6E91"
ACCENT_GOLD = "#B28855"
ACCENT_TEAL = "#1F7A72"
ACCENT_ORANGE = "#C7782A"

TOOL_ORDER = ["命令控制型", "信息公开型", "经济激励型", "市场机制型", "自愿型"]
TOOL_LABELS_EN = {
    "命令控制型": "Command",
    "信息公开型": "Disclosure",
    "经济激励型": "Incentive",
    "市场机制型": "Market",
    "自愿型": "Voluntary",
}
DIMENSION_ALIAS = {
    "key_measures": "key_measures",
    "key_me措施": "key_measures",
    " innovation_points": "innovation_points",
    "innovation_points": "innovation_points",
    "创新_points": "innovation_points",
    "创新点": "innovation_points",
}
DIMENSION_LABELS = {
    "gov_level": "政府层级",
    "policy_intensity": "政策力度",
    "policy_tone": "政策语气",
    "policy_type": "政策类型",
    "regulatory_stringency": "规制严格度",
    "issuing_authority": "发文机关",
    "effective_date": "施行日期",
    "policy_objective_level": "目标层次",
    "policy_name": "政策名称",
    "policy_tools": "政策工具",
    "issue_date": "发布日期",
    "doc_number": "文号",
    "pollutant_types": "污染物覆盖",
    "referenced_policies": "引用政策",
    "penalty_provisions": "处罚条款",
    "vertical_coordination": "纵向协调",
    "innovation_points": "创新点",
    "quantitative_targets": "量化目标",
    "target_industries": "目标行业",
    "implementation_mechanism": "执行机制",
    "key_measures": "关键措施",
}
DIMENSION_LABELS_EN = {
    "gov_level": "Gov level",
    "policy_intensity": "Intensity",
    "policy_tone": "Tone",
    "policy_type": "Policy type",
    "regulatory_stringency": "Stringency",
    "issuing_authority": "Authority",
    "effective_date": "Effective date",
    "policy_objective_level": "Objective level",
    "policy_name": "Policy name",
    "policy_tools": "Policy tools",
    "issue_date": "Issue date",
    "doc_number": "Doc number",
    "pollutant_types": "Pollutants",
    "referenced_policies": "Referenced policies",
    "penalty_provisions": "Penalty provisions",
    "vertical_coordination": "Vertical coord.",
    "innovation_points": "Innovation points",
    "quantitative_targets": "Quantitative targets",
    "target_industries": "Target industries",
    "implementation_mechanism": "Implementation",
    "key_measures": "Key measures",
}
DOC_FAMILY_LABELS = {
    "law": "法律",
    "regulation": "条例/法规",
    "administrative_rule": "部门规章",
    "policy_document": "意见/行动计划",
    "technical_or_catalog": "技术标准/名录",
    "other": "其他",
}
DOC_FAMILY_LABELS_EN = {
    "法律": "Law",
    "条例/法规": "Regulation",
    "部门规章": "Admin rule",
    "意见/行动计划": "Policy doc",
    "技术标准/名录": "Tech std.",
    "其他": "Other",
}
GOV_LEVEL_COLORS = {
    "中央": RUC_RED,
    "省级": ACCENT_BLUE,
    "市级": ACCENT_TEAL,
}
GOV_LEVEL_LABELS_EN = {
    "中央": "Central",
    "省级": "Provincial",
    "市级": "Municipal",
}
OBJECTIVE_LABELS_EN = {
    "过程型": "Process",
    "产出型": "Output",
    "结果型": "Outcome",
}
REFERENCE_LABELS_EN = {
    "中华人民共和国环境保护法": "Environmental Protection Law",
    "中华人民共和国大气污染防治法": "Air Pollution Prevention Law",
    "中华人民共和国水污染防治法": "Water Pollution Prevention Law",
    "中华人民共和国固体废物污染环境防治法": "Solid Waste Law",
    "中华人民共和国海洋环境保护法": "Marine Environment Law",
    "中华人民共和国清洁生产促进法": "Cleaner Production Law",
    "中华人民共和国环境影响评价法": "EIA Law",
    "中华人民共和国土壤污染防治法": "Soil Pollution Law",
    "中华人民共和国渔业法": "Fisheries Law",
    "中华人民共和国水法": "Water Law",
    "中华人民共和国产品质量法": "Product Quality Law",
    "产业结构调整指导目录": "Industrial Structure Catalog",
    "节约能源法": "Energy Conservation Law",
    "电力法": "Electricity Law",
    "可再生能源法": "Renewable Energy Law",
    "规划环境影响评价条例": "Planning EIA Regulation",
}


def configure_style() -> None:
    font_candidates = [
        "Songti SC",
        "STSong",
        "PingFang SC",
        "Hiragino Sans GB",
        "Arial Unicode MS",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": font_candidates,
        "axes.unicode_minus": False,
        "figure.dpi": 200,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.facecolor": BG,
        "figure.facecolor": BG,
        "axes.edgecolor": LINE,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "axes.titleweight": "bold",
        "axes.titlesize": 14,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "axes.grid": True,
        "grid.color": "#E6DDE0",
        "grid.linestyle": "-",
        "grid.linewidth": 0.8,
    })


def ensure_dirs() -> None:
    for path in [TABLE_DIR, FIG_DIR, INTERIM_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_doc_summary() -> pd.DataFrame:
    rows = load_json(SUMMARY_JSON)
    inventory = pd.read_csv(INVENTORY_CSV)
    inventory["file_id"] = inventory["file_id"].astype(str).str.zfill(2)

    records = []
    for row in rows:
        final_result = row["final_result"]
        file_id = Path(row["file_name"]).stem.split("_")[0]
        policy_tools = final_result.get("policy_tools") or []
        pollutants = final_result.get("pollutant_types") or []
        industries = final_result.get("target_industries") or []
        impl = final_result.get("implementation_mechanism") or []
        refs = final_result.get("referenced_policies") or []
        targets = final_result.get("quantitative_targets") or []
        innovation = final_result.get("innovation_points") or []
        penalty = final_result.get("penalty_provisions") or ""
        vertical_coordination = final_result.get("vertical_coordination") or ""
        records.append({
            "file_id": file_id,
            "file_name": row["file_name"],
            "agreement_rate": row["agreement_rate"],
            "overall_confidence": row["overall_confidence"],
            "text_source": row["text_source"],
            "rescued_text_path": row.get("rescued_text_path", ""),
            "policy_name": final_result.get("policy_name"),
            "policy_type": final_result.get("policy_type"),
            "gov_level": final_result.get("gov_level"),
            "policy_intensity": final_result.get("policy_intensity"),
            "policy_tone": final_result.get("policy_tone"),
            "regulatory_stringency": pd.to_numeric(final_result.get("regulatory_stringency"), errors="coerce"),
            "policy_objective_level": final_result.get("policy_objective_level"),
            "issuing_authority": final_result.get("issuing_authority"),
            "policy_tools": json.dumps(policy_tools, ensure_ascii=False),
            "pollutant_types": json.dumps(pollutants, ensure_ascii=False),
            "target_industries": json.dumps(industries, ensure_ascii=False),
            "implementation_mechanism": json.dumps(impl, ensure_ascii=False),
            "referenced_policies": json.dumps(refs, ensure_ascii=False),
            "quantitative_targets": json.dumps(targets, ensure_ascii=False),
            "innovation_points": json.dumps(innovation, ensure_ascii=False),
            "penalty_provisions": penalty,
            "vertical_coordination": vertical_coordination,
            "n_tools": len(policy_tools),
            "n_pollutants": len(pollutants),
            "n_industries": len(industries),
            "n_impl": len(impl),
            "n_refs": len(refs),
            "n_targets": len(targets),
            "has_penalty": int(str(penalty).strip() not in {"", "未提及"}),
            "has_vertical_coordination": int(str(vertical_coordination).strip() not in {"", "未提及"}),
        })

    df = pd.DataFrame(records).merge(
        inventory[[
            "file_id",
            "relative_path",
            "inferred_year",
            "inferred_level",
            "inferred_doc_family",
            "page_count",
            "char_count",
        ]],
        on="file_id",
        how="left",
    )
    for column in ["inferred_year", "page_count", "char_count"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["doc_family_cn"] = df["inferred_doc_family"].map(DOC_FAMILY_LABELS).fillna("其他")
    df["rescue_flag"] = np.where(df["text_source"].eq("official_html_rescue"), "官方网页补源", "原生文本")
    for tool in TOOL_ORDER:
        df[f"tool_{tool}"] = df["policy_tools"].apply(lambda cell, t=tool: int(t in json.loads(cell)))
    return df


def load_dimension_agreement() -> pd.DataFrame:
    rows = load_json(RAW_JSON)
    dim_values: dict[str, list[float]] = {}
    for row in rows:
        for raw_key, value in row.get("per_dim_agreement", {}).items():
            key = DIMENSION_ALIAS.get(raw_key, raw_key)
            dim_values.setdefault(key, []).append(value)
    records = []
    for key, values in dim_values.items():
        avg = float(np.mean(values))
        if avg >= 0.8:
            band = "高一致性"
        elif avg >= 0.6:
            band = "中等一致性"
        elif avg >= 0.4:
            band = "需重点核验"
        else:
            band = "不宜直接入模"
        records.append({
            "dimension": key,
            "dimension_label": DIMENSION_LABELS.get(key, key),
            "agreement_mean": round(avg, 3),
            "n_docs": len(values),
            "quality_band": band,
        })
    df = pd.DataFrame(records).sort_values(["agreement_mean", "dimension_label"]).reset_index(drop=True)
    return df


def load_model_quality() -> pd.DataFrame:
    rows = load_json(RAW_JSON)
    records = []
    for row in rows:
        per_model = row.get("per_model_confidence", {})
        records.append({
            "file_name": row["file_name"],
            "agreement_rate": row["agreement_rate"],
            "extraction_status": row["extraction_status"],
            "valid_model_count": row.get("valid_model_count", 0),
            "failed_model_count": row.get("failed_model_count", 0),
            "disagreement_count": len(row.get("disagreements", [])),
            "DeepSeek-V3.2": per_model.get("DeepSeek-V3.2"),
            "MiniMax-M2.5": per_model.get("MiniMax-M2.5"),
            "Kimi-K2.5": per_model.get("Kimi-K2.5"),
        })
    return pd.DataFrame(records)


def build_tool_prevalence(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    grouped = df.groupby("policy_type", dropna=False)
    for policy_type, frame in grouped:
        for tool in TOOL_ORDER:
            records.append({
                "policy_type": policy_type,
                "tool": tool,
                "share": frame[f"tool_{tool}"].mean(),
                "count": int(frame[f"tool_{tool}"].sum()),
                "n_docs": len(frame),
            })
    out = pd.DataFrame(records)
    return out


def build_reference_table(df: pd.DataFrame) -> pd.DataFrame:
    counter = Counter()
    for refs in df["referenced_policies"]:
        counter.update(json.loads(refs))
    records = [{"referenced_policy": name, "count": count} for name, count in counter.most_common(15)]
    return pd.DataFrame(records)


def build_implementation_table(df: pd.DataFrame) -> pd.DataFrame:
    counter = Counter()
    for items in df["implementation_mechanism"]:
        counter.update(json.loads(items))
    records = [{"implementation_mechanism": name, "count": count} for name, count in counter.most_common(15)]
    return pd.DataFrame(records)


def build_validation_priority_table() -> pd.DataFrame:
    sample = pd.read_csv(VALIDATION_SAMPLE_CSV)
    validation = pd.read_csv(VALIDATION_SHEET_CSV)
    pilot_docs = sample[["file_name", "pilot_role", "validation_priority"]].drop_duplicates()
    validation_summary = (
        validation.groupby("file_name", dropna=False)["agreement_rate"]
        .agg(lambda s: pd.to_numeric(s, errors="coerce").mean())
        .reset_index()
        .rename(columns={"agreement_rate": "pilot_field_agreement_mean"})
    )
    return pilot_docs.merge(validation_summary, on="file_name", how="left")


def save_tables(doc_df: pd.DataFrame, dim_df: pd.DataFrame, model_df: pd.DataFrame) -> dict[str, Path]:
    tool_df = build_tool_prevalence(doc_df)
    ref_df = build_reference_table(doc_df)
    impl_df = build_implementation_table(doc_df)
    validation_df = build_validation_priority_table()

    paths = {
        "doc_summary": TABLE_DIR / "prestudy_doc_summary.csv",
        "dimension_agreement": TABLE_DIR / "prestudy_dimension_agreement.csv",
        "model_quality": TABLE_DIR / "prestudy_model_quality.csv",
        "tool_prevalence": TABLE_DIR / "prestudy_tool_prevalence.csv",
        "top_references": TABLE_DIR / "prestudy_top_referenced_policies.csv",
        "top_implementation": TABLE_DIR / "prestudy_top_implementation_mechanisms.csv",
        "validation_priority": TABLE_DIR / "prestudy_validation_priority.csv",
        "doc_summary_interim": INTERIM_DIR / "prestudy_doc_summary.csv",
        "dimension_agreement_interim": INTERIM_DIR / "prestudy_dimension_agreement.csv",
    }

    doc_df.to_csv(paths["doc_summary"], index=False, encoding="utf-8-sig")
    dim_df.to_csv(paths["dimension_agreement"], index=False, encoding="utf-8-sig")
    model_df.to_csv(paths["model_quality"], index=False, encoding="utf-8-sig")
    tool_df.to_csv(paths["tool_prevalence"], index=False, encoding="utf-8-sig")
    ref_df.to_csv(paths["top_references"], index=False, encoding="utf-8-sig")
    impl_df.to_csv(paths["top_implementation"], index=False, encoding="utf-8-sig")
    validation_df.to_csv(paths["validation_priority"], index=False, encoding="utf-8-sig")
    doc_df.to_csv(paths["doc_summary_interim"], index=False, encoding="utf-8-sig")
    dim_df.to_csv(paths["dimension_agreement_interim"], index=False, encoding="utf-8-sig")
    return paths


def finalize_figure(fig: plt.Figure, stem: str) -> None:
    svg_path = FIG_DIR / f"{stem}.svg"
    png_path = FIG_DIR / f"{stem}.png"
    pdf_path = FIG_DIR / f"{stem}.pdf"
    fig.savefig(svg_path, format="svg", facecolor=BG)
    fig.savefig(png_path, format="png", facecolor=BG)
    fig.savefig(pdf_path, format="pdf", facecolor=BG)
    plt.close(fig)


def fig_sample_timeline(df: pd.DataFrame) -> None:
    family_order = ["法律", "条例/法规", "部门规章", "意见/行动计划", "技术标准/名录", "其他"]
    family_to_y = {label: idx for idx, label in enumerate(family_order[::-1])}
    marker_map = {"中央": "o", "省级": "s", "市级": "^"}

    fig, ax = plt.subplots(figsize=(10.8, 5.6))
    ax.set_facecolor(BG)
    ax.grid(axis="x", color="#E8DDE0")
    ax.grid(axis="y", visible=False)

    for gov_level in ["中央", "省级", "市级"]:
        subset = df[df["gov_level"].eq(gov_level)].copy()
        if subset.empty:
            continue
        y = subset["doc_family_cn"].map(family_to_y)
        sizes = np.where(subset["text_source"].eq("official_html_rescue"), 150, 95)
        edgecolors = np.where(subset["text_source"].eq("official_html_rescue"), ACCENT_GOLD, "white")
        linewidths = np.where(subset["text_source"].eq("official_html_rescue"), 1.8, 0.8)
        ax.scatter(
            subset["inferred_year"],
            y,
            s=sizes,
            c=GOV_LEVEL_COLORS[gov_level],
            marker=marker_map[gov_level],
            edgecolors=edgecolors,
            linewidths=linewidths,
            alpha=0.9,
            label=GOV_LEVEL_LABELS_EN[gov_level],
            zorder=3,
        )

    rescue_subset = df[df["text_source"].eq("official_html_rescue")]
    for _, row in rescue_subset.iterrows():
        ax.annotate(
            row["file_id"],
            (row["inferred_year"], family_to_y[row["doc_family_cn"]]),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            fontsize=8.5,
            color=ACCENT_GOLD,
        )

    ax.set_yticks(list(family_to_y.values()))
    ax.set_yticklabels([DOC_FAMILY_LABELS_EN[label] for label in family_to_y.keys()])
    ax.set_xticks(sorted(df["inferred_year"].dropna().astype(int).unique()))
    ax.set_xlabel("Year")
    ax.set_ylabel("Document family")
    fig.suptitle("Figure 1. Sample coverage by year and document family", y=0.96, fontsize=15, fontweight="bold")
    fig.text(
        0.125,
        0.905,
        "Color denotes gov level; gold outline marks official_html_rescue files.",
        fontsize=10,
        color=MUTED,
    )
    ax.legend(frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0.0, -0.12))
    fig.subplots_adjust(top=0.86, bottom=0.18)
    finalize_figure(fig, "fig1_sample_timeline")


def fig_tool_heatmap(df: pd.DataFrame) -> None:
    heat = (
        df.groupby("policy_type", dropna=False)[[f"tool_{tool}" for tool in TOOL_ORDER]]
        .mean()
        .loc[:, [f"tool_{tool}" for tool in TOOL_ORDER]]
        .mul(100)
        .round(1)
    )
    heat.columns = [TOOL_LABELS_EN[tool] for tool in TOOL_ORDER]
    row_order = ["法律", "行政法规", "部门规章", "规范性文件", "地方性法规", "部门规章/技术标准", "未在文本中明确标注"]
    heat = heat.reindex([row for row in row_order if row in heat.index])
    heat.index = [
        {
            "法律": "Law",
            "行政法规": "Administrative regulation",
            "部门规章": "Admin rule",
            "规范性文件": "Policy document",
            "地方性法规": "Local regulation",
            "部门规章/技术标准": "Admin rule / technical",
            "未在文本中明确标注": "Not explicit in text",
        }.get(idx, idx)
        for idx in heat.index
    ]

    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    cmap = LinearSegmentedColormap.from_list("ruc_heat", ["#FBF8F7", "#E6C6CC", RUC_RED])
    image = ax.imshow(heat.to_numpy(), cmap=cmap, vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(np.arange(len(heat.columns)))
    ax.set_xticklabels(list(heat.columns))
    ax.set_yticks(np.arange(len(heat.index)))
    ax.set_yticklabels(list(heat.index))
    ax.set_xticks(np.arange(-0.5, len(heat.columns), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(heat.index), 1), minor=True)
    ax.grid(False)
    ax.grid(which="minor", color=BG, linestyle="-", linewidth=1.2)
    ax.tick_params(which="minor", bottom=False, left=False)
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            value = heat.iloc[i, j]
            label_color = "white" if value >= 60 else INK
            ax.text(j, i, f"{value:.1f}", ha="center", va="center", fontsize=10, color=label_color)
    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel("Share of documents (%)", rotation=90, va="bottom")
    ax.set_title("Figure 2. Tool prevalence by policy type")
    ax.set_xlabel("")
    ax.set_ylabel("")
    finalize_figure(fig, "fig2_tool_heatmap")


def fig_objective_profile(df: pd.DataFrame) -> None:
    profile = (
        df.groupby("policy_objective_level", dropna=False)[["regulatory_stringency", "n_targets", "n_impl"]]
        .mean()
        .reindex(["过程型", "产出型", "结果型"])
        .reset_index()
        .rename(columns={"policy_objective_level": "目标层次"})
    )
    profile["目标层次_en"] = profile["目标层次"].map(OBJECTIVE_LABELS_EN)

    fig, axes = plt.subplots(1, 3, figsize=(11.6, 4.2))
    metrics = [
        ("regulatory_stringency", "Mean stringency", ACCENT_ORANGE),
        ("n_targets", "Mean target count", RUC_RED),
        ("n_impl", "Mean implementation count", ACCENT_BLUE),
    ]
    for ax, (metric, title, color) in zip(axes, metrics):
        ax.bar(profile["目标层次_en"], profile[metric], color=color, width=0.6)
        ax.set_title(title, fontsize=12)
        ax.set_xlabel("")
        ax.grid(axis="y", color="#E8DDE0")
        ax.set_axisbelow(True)
        for idx, value in enumerate(profile[metric]):
            ax.text(idx, value + 0.05, f"{value:.2f}", ha="center", va="bottom", fontsize=10)
    axes[0].set_ylabel("Mean value")
    fig.suptitle("Figure 3. Content profile by objective level", y=1.03, fontsize=14, fontweight="bold")
    fig.tight_layout()
    finalize_figure(fig, "fig3_objective_profile")


def fig_dimension_agreement(dim_df: pd.DataFrame) -> None:
    plot_df = dim_df.copy()
    plot_df["dimension_label_en"] = plot_df["dimension"].map(DIMENSION_LABELS_EN).fillna(plot_df["dimension"])
    plot_df["color"] = plot_df["quality_band"].map({
        "高一致性": ACCENT_TEAL,
        "中等一致性": ACCENT_BLUE,
        "需重点核验": ACCENT_ORANGE,
        "不宜直接入模": RUC_RED,
    })

    fig, ax = plt.subplots(figsize=(8.4, 6.4))
    ax.barh(plot_df["dimension_label_en"], plot_df["agreement_mean"], color=plot_df["color"])
    ax.axvline(0.8, color=ACCENT_TEAL, linestyle="--", linewidth=1.2)
    ax.axvline(0.6, color=ACCENT_BLUE, linestyle="--", linewidth=1.2)
    ax.axvline(0.4, color=ACCENT_ORANGE, linestyle="--", linewidth=1.2)
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("Mean agreement rate")
    ax.set_ylabel("")
    ax.set_title("Figure 4. Agreement rate by extracted dimension")
    for y, value in enumerate(plot_df["agreement_mean"]):
        ax.text(value + 0.015, y, f"{value:.3f}", va="center", fontsize=9)
    finalize_figure(fig, "fig4_dimension_agreement")


def fig_document_agreement(df: pd.DataFrame) -> None:
    plot_df = df.sort_values("agreement_rate").reset_index(drop=True).copy()
    plot_df["rank"] = np.arange(1, len(plot_df) + 1)
    colors = plot_df["text_source"].map({
        "official_html_rescue": ACCENT_GOLD,
        "pdfplumber": RUC_RED,
    }).fillna(MUTED)

    fig, ax = plt.subplots(figsize=(10.6, 4.8))
    ax.hlines(plot_df["rank"], xmin=0.45, xmax=plot_df["agreement_rate"], color="#D8CCD0", linewidth=1.5)
    ax.scatter(plot_df["agreement_rate"], plot_df["rank"], s=58, color=colors, edgecolor="white", linewidth=0.8, zorder=3)
    ax.axvline(plot_df["agreement_rate"].mean(), color=ACCENT_BLUE, linestyle="--", linewidth=1.2)
    ax.text(plot_df["agreement_rate"].mean() + 0.005, 2, f"Mean {plot_df['agreement_rate'].mean():.3f}", color=ACCENT_BLUE, fontsize=9)

    highlight = pd.concat([
        plot_df.head(6),
        plot_df[plot_df["text_source"].eq("official_html_rescue")],
    ]).drop_duplicates("file_name")
    for _, row in highlight.iterrows():
        suffix = " rescue" if row["text_source"] == "official_html_rescue" else ""
        label = f"ID{row['file_id']}{suffix}"
        ax.annotate(
            label,
            (row["agreement_rate"], row["rank"]),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=8.5,
            color=INK if row["text_source"] == "pdfplumber" else ACCENT_GOLD,
        )

    ax.set_xlabel("Document-level agreement rate")
    ax.set_ylabel("Documents sorted by agreement")
    ax.set_yticks([])
    ax.set_xlim(0.44, 0.78)
    ax.set_title("Figure 5. Document-level agreement distribution")
    finalize_figure(fig, "fig5_document_agreement")


def fig_top_references(df: pd.DataFrame) -> None:
    plot_df = build_reference_table(df).head(10).iloc[::-1]
    plot_df["referenced_policy_en"] = [
        REFERENCE_LABELS_EN.get(name, f"Reference {idx}")
        for idx, name in enumerate(plot_df["referenced_policy"], start=1)
    ]
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    ax.barh(plot_df["referenced_policy_en"], plot_df["count"], color=RUC_RED)
    ax.set_xlabel("Reference count")
    ax.set_ylabel("")
    ax.set_title("Figure 6. Most frequently referenced higher-level laws/policies")
    for y, value in enumerate(plot_df["count"]):
        ax.text(value + 0.15, y, str(value), va="center", fontsize=9)
    finalize_figure(fig, "fig6_top_references")


def build_summary_note(doc_df: pd.DataFrame, dim_df: pd.DataFrame, model_df: pd.DataFrame) -> Path:
    tool_prevalence = (doc_df[[f"tool_{tool}" for tool in TOOL_ORDER]].mean() * 100).round(1)
    low_docs = doc_df.nsmallest(5, "agreement_rate")[["file_name", "agreement_rate"]]
    rescue_docs = doc_df[doc_df["text_source"].eq("official_html_rescue")][["file_name", "agreement_rate"]]
    partial_row = model_df[model_df["extraction_status"].ne("success")]

    lines = [
        "# 预调研报告资产生成摘要",
        "",
        f"- 文件总数：{len(doc_df)}",
        f"- 平均总体一致率：{doc_df['agreement_rate'].mean():.3f}",
        f"- 原生文本：{int((doc_df['text_source'] == 'pdfplumber').sum())} 份",
        f"- official_html_rescue：{int((doc_df['text_source'] == 'official_html_rescue').sum())} 份",
        "- 政策工具覆盖率：" + "; ".join(
            f"{tool} {tool_prevalence[f'tool_{tool}']:.1f}%"
            for tool in TOOL_ORDER
        ),
        "",
        "## 一致率最低的 5 份文件",
    ]
    for _, row in low_docs.iterrows():
        lines.append(f"- {row['file_name']}: {row['agreement_rate']:.3f}")
    lines.append("")
    lines.append("## official_html_rescue 文件")
    for _, row in rescue_docs.iterrows():
        lines.append(f"- {row['file_name']}: {row['agreement_rate']:.3f}")
    lines.append("")
    lines.append("## 一致率最低的字段")
    for _, row in dim_df.head(6).iterrows():
        lines.append(f"- {row['dimension_label']}: {row['agreement_mean']:.3f}（{row['quality_band']}）")
    if not partial_row.empty:
        row = partial_row.iloc[0]
        lines.append("")
        lines.append("## 非完全成功个案")
        lines.append(f"- {row['file_name']}：{row['extraction_status']}，总体一致率 {row['agreement_rate']:.3f}")

    output_path = TABLE_DIR / "prestudy_asset_summary.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> None:
    configure_style()
    ensure_dirs()
    doc_df = load_doc_summary()
    dim_df = load_dimension_agreement()
    model_df = load_model_quality()
    save_tables(doc_df, dim_df, model_df)
    fig_sample_timeline(doc_df)
    fig_tool_heatmap(doc_df)
    fig_objective_profile(doc_df)
    fig_dimension_agreement(dim_df)
    fig_document_agreement(doc_df)
    fig_top_references(doc_df)
    summary_path = build_summary_note(doc_df, dim_df, model_df)
    print(f"tables written to: {TABLE_DIR}")
    print(f"figures written to: {FIG_DIR}")
    print(f"summary note: {summary_path}")


if __name__ == "__main__":
    main()
