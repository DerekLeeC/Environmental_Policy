#!/usr/bin/env python3
"""Build a polished LaTeX version of the prestudy report from Markdown."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from textwrap import dedent


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAPER_DIR = PROJECT_ROOT / "paper"
REPORT_MD = PAPER_DIR / "prestudy_report_20260421.md"
BODY_TEX = PAPER_DIR / "prestudy_report_20260421_body.tex"
MAIN_TEX = PAPER_DIR / "prestudy_report_20260421.tex"
PDF_PATH = PAPER_DIR / "prestudy_report_20260421.pdf"

TITLE = "中国环境政策文本结构化抽取预调研报告"
SUBTITLE = "基于 50 份环境政策文本与多模型交叉抽取结果的阶段性分析"
VERSION_DATE = "2026年4月21日"

FIGURE_SPECS = {
    "../output/figures/prestudy_report/fig1_sample_timeline.png": {
        "caption": "预调研样本的年份—文件类型分布",
        "label": "fig:sample_timeline",
        "width": r"0.98\textwidth",
    },
    "../output/figures/prestudy_report/fig2_tool_heatmap.png": {
        "caption": "不同政策类型中的政策工具覆盖率",
        "label": "fig:tool_heatmap",
        "width": r"0.96\textwidth",
    },
    "../output/figures/prestudy_report/fig3_objective_profile.png": {
        "caption": "不同目标层次文件的内容画像",
        "label": "fig:objective_profile",
        "width": r"0.98\textwidth",
    },
    "../output/figures/prestudy_report/fig4_dimension_agreement.png": {
        "caption": "各抽取维度的平均一致率",
        "label": "fig:dimension_agreement",
        "width": r"0.98\textwidth",
    },
    "../output/figures/prestudy_report/fig5_document_agreement.png": {
        "caption": "文件层级总体一致率分布",
        "label": "fig:document_agreement",
        "width": r"0.98\textwidth",
    },
    "../output/figures/prestudy_report/fig6_top_references.png": {
        "caption": "样本中最常被引用的上位法/政策",
        "label": "fig:top_references",
        "width": r"0.96\textwidth",
    },
}

TABLE_1_LATEX = dedent(
    r"""
    \begin{table}[H]
    \centering
    \caption{预调研样本基础事实}
    \label{tab:basic_facts}
    \begin{tabular}{L{0.58\linewidth}C{0.20\linewidth}}
    \toprule
    指标 & 数值 \\
    \midrule
    样本文件数 & 50 \\
    时间范围 & 2009---2024 \\
    中央 / 省级 / 市级 & 43 / 6 / 1 \\
    原生文本 / 官方补源 & 47 / 3 \\
    平均总体一致率 & 0.593 \\
    成功 / 部分成功 & 49 / 1 \\
    平均规制严格度 & 4.48 \\
    \bottomrule
    \end{tabular}
    \end{table}
    """
).strip()

MAIN_TEX_TEMPLATE = dedent(
    r"""
    \documentclass[12pt,a4paper,fontset=none]{ctexart}

    \usepackage[a4paper,left=2.7cm,right=2.7cm,top=2.9cm,bottom=2.8cm,headheight=18pt,footskip=26pt]{geometry}
    \usepackage{fontspec}
    \usepackage{xeCJK}
    \usepackage{microtype}
    \usepackage{setspace}
    \usepackage{indentfirst}
    \usepackage{graphicx}
    \usepackage{booktabs}
    \usepackage{array}
    \usepackage{tabularx}
    \usepackage{longtable}
    \usepackage{float}
    \usepackage{caption}
    \usepackage{enumitem}
    \usepackage{hyperref}
    \usepackage{xurl}
    \usepackage{fancyhdr}
    \usepackage{lastpage}
    \usepackage{titlesec}
    \usepackage[most]{tcolorbox}
    \usepackage{fvextra}
    \usepackage{ragged2e}
    \usepackage{etoolbox}
    \usepackage{calc}

    \IfFontExistsTF{Times New Roman}{\setmainfont{Times New Roman}}{\setmainfont{TeX Gyre Termes}}
    \IfFontExistsTF{Songti SC}{\setCJKmainfont{Songti SC}}{\setCJKmainfont{FandolSong}}
    \IfFontExistsTF{PingFang SC}{\setCJKsansfont{PingFang SC}}{\setCJKsansfont{FandolHei}}
    \IfFontExistsTF{Menlo}{\setmonofont{Menlo}}{\setmonofont{Courier New}}
    \IfFontExistsTF{PingFang SC}{\setCJKmonofont{PingFang SC}}{\setCJKmonofont{FandolFang}}

    \definecolor{RUCRed}{HTML}{971F30}
    \definecolor{RUCSoft}{HTML}{F7F1F2}
    \definecolor{Ink}{HTML}{2B2325}
    \definecolor{Muted}{HTML}{6D6063}
    \definecolor{Line}{HTML}{D9CCD0}
    \definecolor{CodeBG}{HTML}{FBF8F7}
    \definecolor{LinkBlue}{HTML}{1F5A7A}

    \setstretch{1.32}
    \setlength{\parindent}{2em}
    \setlength{\parskip}{0.35em}
    \setlength{\emergencystretch}{3em}
    \widowpenalty=10000
    \clubpenalty=10000
    \displaywidowpenalty=10000

    \setcounter{secnumdepth}{0}
    \setcounter{tocdepth}{2}
    \renewcommand{\contentsname}{目录}
    \setlist[itemize]{leftmargin=2.2em,itemsep=0.2em,topsep=0.4em}
    \setlist[enumerate]{leftmargin=2.2em,itemsep=0.2em,topsep=0.4em}

    \hypersetup{
      colorlinks=true,
      linkcolor=RUCRed,
      urlcolor=LinkBlue,
      citecolor=RUCRed,
      pdftitle={中国环境政策文本结构化抽取预调研报告},
      pdfauthor={环境政策项目},
      pdfsubject={预调研报告},
      pdfcreator={LaTeX build pipeline}
    }
    \urlstyle{same}

    \pagestyle{fancy}
    \fancyhf{}
    \fancyhead[L]{\small\color{Muted}中国环境政策文本结构化抽取预调研报告}
    \fancyhead[R]{\small\color{Muted}2026年4月21日}
    \fancyfoot[C]{\small\color{Muted}\thepage}
    \renewcommand{\headrulewidth}{0.4pt}
    \renewcommand{\footrulewidth}{0pt}

    \titleformat{\section}
      {\zihao{-3}\bfseries\color{RUCRed}}
      {}
      {0pt}
      {}
    \titleformat{\subsection}
      {\zihao{4}\bfseries\color{Ink}}
      {}
      {0pt}
      {}
    \titlespacing*{\section}{0pt}{2.2ex plus .3ex minus .2ex}{1.1ex}
    \titlespacing*{\subsection}{0pt}{1.6ex plus .2ex minus .2ex}{0.6ex}

    \captionsetup{
      font={small},
      labelfont={bf,color=RUCRed},
      textfont={small},
      skip=8pt
    }

    \newcolumntype{L}[1]{>{\RaggedRight\arraybackslash}p{#1}}
    \newcolumntype{C}[1]{>{\Centering\arraybackslash}p{#1}}
    \providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}

    \DefineVerbatimEnvironment{CodeBlock}{Verbatim}{
      fontsize=\small,
      breaklines=true,
      breaksymbolleft={},
      frame=single,
      rulecolor=\color{Line},
      framesep=4mm,
      baselinestretch=1.0,
      formatcom=\color{Ink}
    }

    \newtcolorbox{MetaBox}{
      enhanced,
      colback=RUCSoft,
      colframe=RUCRed,
      boxrule=0.8pt,
      arc=2pt,
      left=8pt,
      right=8pt,
      top=8pt,
      bottom=8pt
    }

    \begin{document}

    \begin{titlepage}
    \thispagestyle{empty}
    \centering
    \vspace*{2.8cm}

    {\zihao{2}\bfseries\color{RUCRed}__TITLE__\par}
    \vspace{0.9cm}
    {\zihao{-3}\color{Ink}__SUBTITLE__\par}

    \vspace{1.8cm}

    \begin{minipage}{0.88\textwidth}
    \begin{MetaBox}
    \renewcommand{\arraystretch}{1.25}
    \begin{tabularx}{\textwidth}{>{\bfseries}l X}
    版本时间 & __VERSION_DATE__ \\
    结果版本 & \path{llm_results/all_results_summary.json}（2026-04-21 06:29） \\
     & \path{llm_results/all_raw_results.json}（2026-04-21 06:33） \\
    图表版本 & \path{output/figures/prestudy_report/}（2026-04-21 07:22） \\
    工作属性 & 可追溯版本，用于阶段汇报、专家讨论与正式研究推进 \\
    \end{tabularx}
    \end{MetaBox}
    \end{minipage}

    \vfill
    {\large\color{Ink}环境政策项目工作底稿\par}
    \vspace{0.3cm}
    {\normalsize\color{Muted}生成路径：Markdown 报告 $\rightarrow$ LaTeX 模板 $\rightarrow$ XeLaTeX 编译\par}
    \vspace{1.2cm}
    {\normalsize\color{Muted}__VERSION_DATE__\par}
    \end{titlepage}

    \pagenumbering{Roman}
    \tableofcontents
    \clearpage
    \pagenumbering{arabic}

    \input{prestudy_report_20260421_body.tex}

    \end{document}
    """
).strip()


def run_pandoc() -> str:
    result = subprocess.run(
        [
            "pandoc",
            str(REPORT_MD),
            "--from",
            "gfm",
            "--to",
            "latex",
            "--no-highlight",
            "--resource-path=paper:.",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def simplify_pandoc_output(text: str) -> str:
    text = re.sub(r"\\hypertarget\{[^}]+\}\{%[\r\n]*", "", text)
    text = re.sub(
        r"\\(section|subsection|subsubsection)\{([^}]*)\}\\label\{[^}]+\}\}",
        lambda m: f"\\{m.group(1)}{{{m.group(2)}}}",
        text,
    )
    start = text.find(r"\subsection{摘要}")
    if start == -1:
        raise RuntimeError("Could not locate abstract heading in pandoc output.")
    text = text[start:].lstrip()

    text = text.replace(r"\subsubsection{", r"\__TMP_SUBSECTION__{")
    text = text.replace(r"\subsection{", r"\section{")
    text = text.replace(r"\__TMP_SUBSECTION__{", r"\subsection{")
    text = text.replace(
        r"\section{摘要}",
        r"\section*{摘要}" + "\n" + r"\addcontentsline{toc}{section}{摘要}",
        1,
    )

    text = re.sub(
        r"\\begin\{longtable\}\[\]\{@\{\}lr@\{\}\}.*?\\end\{longtable\}",
        lambda _: TABLE_1_LATEX,
        text,
        flags=re.S,
    )

    for path, spec in FIGURE_SPECS.items():
        figure_block = dedent(
            f"""
            \\begin{{figure}}[H]
            \\centering
            \\includegraphics[width={spec['width']}]{{{path}}}
            \\caption{{{spec['caption']}}}
            \\label{{{spec['label']}}}
            \\end{{figure}}
            """
        ).strip()
        text = text.replace(f"\\includegraphics{{{path}}}", figure_block)

    text = text.replace(r"\begin{verbatim}", r"\begin{CodeBlock}")
    text = text.replace(r"\end{verbatim}", r"\end{CodeBlock}")
    text = re.sub(r"\\texttt\{([^{}]+)\}", lambda m: rf"\path{{{m.group(1)}}}", text)
    text = text.replace(
        r"\section{附录：复现入口与核心输出}",
        r"\clearpage" + "\n" + r"\appendix" + "\n" + r"\section{复现入口与核心输出}",
    )
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


def write_main_tex() -> None:
    tex = (
        MAIN_TEX_TEMPLATE.replace("__TITLE__", TITLE)
        .replace("__SUBTITLE__", SUBTITLE)
        .replace("__VERSION_DATE__", VERSION_DATE)
    )
    MAIN_TEX.write_text(tex + "\n", encoding="utf-8")


def compile_pdf() -> None:
    subprocess.run(
        [
            "latexmk",
            "-xelatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            MAIN_TEX.name,
        ],
        cwd=PAPER_DIR,
        check=True,
    )


def main() -> None:
    BODY_TEX.write_text(simplify_pandoc_output(run_pandoc()), encoding="utf-8")
    write_main_tex()
    compile_pdf()
    print(f"body written to: {BODY_TEX}")
    print(f"tex written to: {MAIN_TEX}")
    print(f"pdf written to: {PDF_PATH}")


if __name__ == "__main__":
    main()
