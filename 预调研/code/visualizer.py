"""模块3：政策分析可视化"""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from collections import Counter
from pathlib import Path
from config import FIGURES_DIR, LLM_RESULTS_DIR

# ─── 中文字体设置 ───
def setup_chinese_font():
    """设置中文字体（兼容 macOS / Linux / Windows）"""
    font_candidates = [
        # macOS
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        # Linux（常见 CJK 字体路径）
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        # Windows
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for fp in font_candidates:
        if Path(fp).exists():
            font_manager.fontManager.addfont(fp)
            prop = font_manager.FontProperties(fname=fp)
            plt.rcParams['font.family'] = prop.get_name()
            plt.rcParams['axes.unicode_minus'] = False
            return prop.get_name()

    # fallback: 不指定字体，让 matplotlib 自行查找
    plt.rcParams['font.sans-serif'] = [
        'WenQuanYi Zen Hei', 'WenQuanYi Micro Hei',
        'Noto Sans CJK SC', 'Noto Sans SC',
        'Arial Unicode MS', 'SimHei', 'Heiti SC', 'STHeiti',
        'DejaVu Sans',
    ]
    plt.rcParams['axes.unicode_minus'] = False
    return 'sans-serif'

FONT_NAME = setup_chinese_font()


def load_all_results() -> list[dict]:
    """加载所有提取结果"""
    summary_path = LLM_RESULTS_DIR / "all_results_summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)


def short_name(file_name: str) -> str:
    """缩短文件名用于图表显示"""
    name = file_name.replace(".pdf", "")
    # 去掉编号前缀
    if name[:3].replace("_", "").isdigit():
        name = name[3:]
    # 截断
    if len(name) > 15:
        name = name[:15] + "…"
    return name


def fig1_policy_tools_distribution(results: list[dict]):
    """图1：政策工具类型分布（堆叠条形图）"""
    tool_types = ["命令控制型", "经济激励型", "市场机制型", "信息公开型", "自愿型", "综合型"]
    colors = ['#2C3E50', '#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6']

    names = []
    tool_matrix = {t: [] for t in tool_types}

    for r in results:
        fr = r.get("final_result", {})
        tools = fr.get("policy_tools", [])
        if isinstance(tools, str):
            tools = [tools]
        names.append(short_name(r["file_name"]))
        for t in tool_types:
            tool_matrix[t].append(1 if t in tools else 0)

    fig, ax = plt.subplots(figsize=(12, 6))
    bottom = [0] * len(names)
    for i, t in enumerate(tool_types):
        vals = tool_matrix[t]
        ax.barh(names, vals, left=bottom, label=t, color=colors[i % len(colors)])
        bottom = [b + v for b, v in zip(bottom, vals)]

    ax.set_xlabel("政策工具类型数量")
    ax.set_title("图1：各政策文件的政策工具类型分布")
    ax.legend(loc='lower right', fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig1_policy_tools.png", dpi=150)
    plt.close()
    print("  ✓ fig1_policy_tools.png")


def fig2_intensity_tone_matrix(results: list[dict]):
    """图2：政策力度与语气矩阵"""
    intensity_map = {"强制性": 3, "鼓励性": 2, "引导性": 1}
    tone_map = {"严厉": 3, "中性": 2, "温和": 1}

    fig, ax = plt.subplots(figsize=(10, 7))
    for r in results:
        fr = r.get("final_result", {})
        x = intensity_map.get(fr.get("policy_intensity", ""), 2)
        y = tone_map.get(fr.get("policy_tone", ""), 2)
        name = short_name(r["file_name"])
        ax.scatter(x, y, s=200, zorder=5, alpha=0.8, edgecolors='black')
        ax.annotate(name, (x, y), textcoords="offset points",
                    xytext=(8, 8), fontsize=7, ha='left')

    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(["引导性", "鼓励性", "强制性"])
    ax.set_yticks([1, 2, 3])
    ax.set_yticklabels(["温和", "中性", "严厉"])
    ax.set_xlabel("政策力度")
    ax.set_ylabel("政策语气")
    ax.set_title("图2：政策力度 × 语气 矩阵")
    ax.set_xlim(0.5, 3.5)
    ax.set_ylim(0.5, 3.5)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig2_intensity_tone.png", dpi=150)
    plt.close()
    print("  ✓ fig2_intensity_tone.png")


def fig3_pollutant_coverage(results: list[dict]):
    """图3：污染物类型覆盖热力图"""
    pollutant_types = ["大气污染物", "水污染物", "固体废物", "噪声", "温室气体", "综合"]
    names = []
    matrix = []

    for r in results:
        fr = r.get("final_result", {})
        pollutants = fr.get("pollutant_types", [])
        if isinstance(pollutants, str):
            pollutants = [pollutants]
        names.append(short_name(r["file_name"]))
        row = [1 if p in pollutants else 0 for p in pollutant_types]
        matrix.append(row)

    fig, ax = plt.subplots(figsize=(10, 7))
    import numpy as np
    data = np.array(matrix)
    im = ax.imshow(data, cmap='YlOrRd', aspect='auto')

    ax.set_xticks(range(len(pollutant_types)))
    ax.set_xticklabels(pollutant_types, rotation=45, ha='right')
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)

    # 标注
    for i in range(len(names)):
        for j in range(len(pollutant_types)):
            text = "●" if data[i, j] else ""
            ax.text(j, i, text, ha="center", va="center", fontsize=14)

    ax.set_title("图3：各政策文件污染物类型覆盖矩阵")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig3_pollutant_coverage.png", dpi=150)
    plt.close()
    print("  ✓ fig3_pollutant_coverage.png")


def fig4_timeline(results: list[dict]):
    """图4：政策时间线与类型分布"""
    import re

    type_colors = {
        "法律": "#E74C3C",
        "行政法规": "#3498DB",
        "部门规章": "#2ECC71",
        "规范性文件": "#F39C12",
        "地方性法规": "#9B59B6",
    }

    fig, ax = plt.subplots(figsize=(14, 5))
    y_pos = 0
    for r in results:
        fr = r.get("final_result", {})
        date_str = fr.get("issue_date", "")
        # 提取年份
        year_match = re.search(r'(20\d{2})', str(date_str))
        if not year_match:
            continue
        year = int(year_match.group(1))
        ptype = fr.get("policy_type", "其他")
        color = type_colors.get(ptype, "#7F8C8D")
        name = short_name(r["file_name"])

        ax.scatter(year, y_pos, s=150, c=color, zorder=5, edgecolors='black')
        ax.annotate(name, (year, y_pos), textcoords="offset points",
                    xytext=(10, 5), fontsize=7, ha='left', rotation=15)
        y_pos += 1

    # 图例
    for ptype, color in type_colors.items():
        ax.scatter([], [], c=color, label=ptype, s=80, edgecolors='black')
    ax.legend(loc='upper left', fontsize=8)

    ax.set_xlabel("发布年份")
    ax.set_title("图4：政策发布时间线与政策类型")
    ax.set_yticks([])
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig4_timeline.png", dpi=150)
    plt.close()
    print("  ✓ fig4_timeline.png")


def fig5_confidence_scores(results: list[dict]):
    """图5：各文件多模型交叉验证一致率"""
    names = []
    scores = []
    valid_flags = []
    for r in results:
        names.append(short_name(r.get("file_name", "")))
        conf = r.get("overall_confidence", 0)
        if conf is None:
            conf = 0
            valid_flags.append(False)
        else:
            valid_flags.append(True)
        scores.append(float(conf))

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['#2ECC71' if s >= 0.8 else '#F39C12' if s >= 0.6 else '#E74C3C' for s in scores]
    bars = ax.barh(names, scores, color=colors, edgecolor='black', linewidth=0.5)

    for bar, score, is_valid in zip(bars, scores, valid_flags):
        label = f'{score:.1%}' if is_valid else 'N/A'
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                label, va='center', fontsize=9)

    ax.set_xlim(0, 1.1)
    ax.set_xlabel("模型间一致率")
    ax.set_title("图5：多模型交叉验证一致率")
    ax.axvline(x=0.8, color='green', linestyle='--', alpha=0.5, label='高一致率阈值(80%)')
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig5_confidence.png", dpi=150)
    plt.close()
    print("  ✓ fig5_confidence.png")


def fig6_industry_wordcloud(results: list[dict]):
    """图6：目标行业词频统计"""
    industry_counter = Counter()
    for r in results:
        fr = r.get("final_result", {})
        industries = fr.get("target_industries", [])
        if isinstance(industries, str):
            industries = [industries]
        for ind in industries:
            if ind and ind != "未提及":
                industry_counter[ind] += 1

    if not industry_counter:
        print("  ⚠ 无行业数据，跳过fig6")
        return

    # 取前15个高频行业
    top_industries = industry_counter.most_common(15)
    labels, counts = zip(*top_industries)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(list(reversed(labels)), list(reversed(counts)), color='#3498DB', edgecolor='black', linewidth=0.5)
    ax.set_xlabel("出现次数（份文件数）")
    ax.set_title("图6：目标行业覆盖频率（Top 15）")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig6_industry_freq.png", dpi=150)
    plt.close()
    print("  ✓ fig6_industry_freq.png")


def generate_all_figures(results: list[dict] = None):
    """生成所有可视化图表"""
    if results is None:
        results = load_all_results()

    print("\n生成可视化图表...")
    fig1_policy_tools_distribution(results)
    fig2_intensity_tone_matrix(results)
    fig3_pollutant_coverage(results)
    fig4_timeline(results)
    fig5_confidence_scores(results)
    fig6_industry_wordcloud(results)
    print(f"\n所有图表已保存到: {FIGURES_DIR}")


if __name__ == "__main__":
    generate_all_figures()
