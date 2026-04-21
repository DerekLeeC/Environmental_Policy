"""
项目配置
═══════════════════════════════════════════════════════
中国环境政策文本结构化分析（预调研）

本文件只保留当前已核实、且会直接影响预调研代码设计的文献与规则：
  [1] Fang, Li & Lu (2025), NBER WP 33814
      → 多模型独立抽取 + 交叉核验 + 审计导向的数据构建思路
  [2] Zhang, Chen & Guo (2018), Journal of Public Economics
      → 中央监督与地方执行：environmental enforcement 的核心制度参照
  [3] Kostka & Nahm (2017), The China Quarterly
      → recentralization / local discretion / vertical coordination
  [4] Chen, Liao & Yi (2025), Journal of Public Policy
      → policy textual learning：横向学习 vs 纵向学习
  [5] Gilardi, Alizadeh & Kubli (2023), PNAS
      → LLM 零样本文本标注的准确率与人工对比
  [6] Le Mens & Gallego (2025), Political Analysis
      → asking-and-averaging：重复提问 / 聚合有助于提高稳定性
  [7] Fonseca & Cohen (2024), Findings of ACL
      → 概念标注任务要靠明确的 annotation guideline，而不是模糊提示
  [8] Törnberg (2025), Social Science Computer Review
      → LLM 在跨语境、解释性较强任务上的能力与边界

注意：
  - 先前代码中引用的 `Tong, Ye & Hao (2024)` 当前无法从一手来源核实，
    已移出核心方法文献集合，避免把不稳引用写进可复现骨架。
  - `policy_objective_level` 与 `regulatory_stringency` 现阶段属于项目自定义编码维度，
    不是某一篇文献的直接搬运变量。
"""
import os
from pathlib import Path

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
PDF_DIR = PROJECT_ROOT / "政策文件"
OUTPUT_DIR = PROJECT_ROOT / "output"
FIGURES_DIR = OUTPUT_DIR / "figures"
EXTRACTED_TEXT_DIR = OUTPUT_DIR / "extracted_text"
LLM_RESULTS_DIR = OUTPUT_DIR / "llm_results"

# 确保目录存在
for d in [OUTPUT_DIR, FIGURES_DIR, EXTRACTED_TEXT_DIR, LLM_RESULTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# 硅基流动 API 通用配置
# ──────────────────────────────────────────────
SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"

# 兼容旧环境变量：如果设置了 DEEPSEEK_API_KEY 则回退使用
if not SILICONFLOW_API_KEY:
    SILICONFLOW_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# ──────────────────────────────────────────────
# 多模型配置（均通过硅基流动平台调用）
# 每个模型独立完成全流程提取，然后交叉验证合并
# 参考 [1] Fang et al. (2025): "integrating multiple LLMs to mitigate hallucinations"
# ──────────────────────────────────────────────
MODEL_CONFIGS = {
    "deepseek": {
        "model": os.environ.get("DEEPSEEK_MODEL", "Pro/deepseek-ai/DeepSeek-V3.2"),
        "label": "DeepSeek-V3.2",
    },
    "minimax": {
        "model": os.environ.get("MINIMAX_MODEL", "Pro/MiniMaxAI/MiniMax-M2.5"),
        "label": "MiniMax-M2.5",
    },
    "kimi": {
        "model": os.environ.get("KIMI_MODEL", "Pro/moonshotai/Kimi-K2.5"),
        "label": "Kimi-K2.5",
    },
}

# 可选扩展模型（必要时可加入提取流程）
OPTIONAL_MODEL_CONFIGS = {
    "glm": {
        "model": os.environ.get("GLM_MODEL", "Pro/zai-org/GLM-5"),
        "label": "GLM-5",
    },
    "qwen": {
        "model": os.environ.get("QWEN_MODEL", "qwen3.6-plus"),
        "label": "Qwen-3.6-Plus",
    },
}

# 综合分析报告使用的模型
ANALYSIS_MODEL = "deepseek"

# ──────────────────────────────────────────────
# 并行调用配置
# ──────────────────────────────────────────────
# 同一文件 3 个模型并行提取
MAX_MODEL_WORKERS = int(os.environ.get("MAX_MODEL_WORKERS", "3"))
# 多文件同时处理（50份文件量适当增大）
MAX_FILE_WORKERS = int(os.environ.get("MAX_FILE_WORKERS", "5"))

# API 调用参数
API_MAX_RETRIES = 3
API_RETRY_DELAY = 5   # 秒
API_TIMEOUT = 120      # 秒

# ──────────────────────────────────────────────
# 长文本分段提取配置
# 经验依据：长文本分段 + 结果聚合，可降低长序列遗漏与单次回答波动
# ──────────────────────────────────────────────
# 单次 LLM 调用最大输入字符数
MAX_CHARS_PER_CALL = int(os.environ.get("MAX_CHARS_PER_CALL", "12000"))
# 分段提取时是否启用（对超过 MAX_CHARS_PER_CALL 的文本自动分段）
ENABLE_SECTIONED_EXTRACTION = os.environ.get("ENABLE_SECTIONED_EXTRACTION", "true").lower() == "true"

# ──────────────────────────────────────────────
# 提取维度定义
# v1 保持 21 个直接抽取变量，避免破坏当前预调研结果的可比性。
# 更进一步的 derived variables（如 flexibility score / accountability index /
# textual similarity）在 `data/metadata/llm_extraction_schema.md` 里单列规划。
# ──────────────────────────────────────────────
EXTRACTION_DIMENSIONS = {
    # ─── 基本信息（参考 [1] Fang et al. 2025）───
    "policy_name": "政策全称",
    "doc_number": "文号",
    "issuing_authority": "发布机构",
    "issue_date": "发布日期",
    "effective_date": "生效日期",

    # ─── 政策分类（stick/carrot/sermon + policy mix 思路）───
    "policy_type": "政策类型（法律/行政法规/部门规章/规范性文件/地方性法规）",
    "policy_tools": (
        "政策工具类型列表，按政策工具研究中的经典 typology 编码："
        "命令控制型(CAC)/经济激励型(MBI)/市场机制型(MKT)/"
        "信息公开型(INFO)/自愿型(VOL)/综合型(MIX)"
    ),

    # ─── 规制对象 ───
    "target_industries": "目标行业列表",
    "pollutant_types": (
        "涉及污染物类型列表（大气污染物/水污染物/固体废物/"
        "噪声/温室气体/海洋污染物/综合）"
    ),

    # ─── 政策强度（项目自定义 ordinal coding）───
    "policy_intensity": "政策力度（强制性/鼓励性/引导性）",
    "policy_tone": "政策语气（严厉/中性/温和）",
    "regulatory_stringency": (
        "规制严格度评分(1-5)：1=纯倡导无约束, 2=鼓励但无罚则, "
        "3=有明确要求和期限, 4=有罚则和问责, 5=严厉处罚+按日计罚/停产"
    ),

    # ─── 央-地关系（参考 [3] Kostka & Nahm 2017）───
    "gov_level": "政府层级（中央/省级/市级）",
    "vertical_coordination": (
        "纵向协调机制：是否涉及央-地权责划分、"
        "是否要求地方配套、是否设立考核问责（是/否/部分，并简述）"
    ),

    # ─── 政策目标层次（项目自定义的 Input-Process-Output-Outcome 编码）───
    "policy_objective_level": (
        "政策目标层次：投入型(Input,如资金/人员投入要求)/"
        "过程型(Process,如制度建设/能力建设)/"
        "产出型(Output,如排放标准/削减量)/"
        "结果型(Outcome,如环境质量改善目标)"
    ),

    # ─── 执行机制（参考 [4] Zhang et al. 2018 政策演进）───
    "implementation_mechanism": (
        "执行保障机制列表（最多5条），如：排污许可/环评审批/"
        "总量控制/目标责任制/生态补偿/信息公开/公众参与/司法保障"
    ),

    # ─── 核心内容 ───
    "key_measures": "核心措施列表（最多5条）",
    "quantitative_targets": "量化目标列表（如有）",
    "penalty_provisions": "处罚条款摘要（如有）",
    "innovation_points": "政策创新点（如有）",

    # ─── 政策关联（textual learning / diffusion 入口变量）───
    "referenced_policies": (
        "本政策明确引用或依据的其他法律法规名称列表（最多5条）"
    ),
}

# ──────────────────────────────────────────────
# 参考文献列表（供报告引用）
# ──────────────────────────────────────────────
LITERATURE_REFERENCES = [
    {
        "id": 1,
        "cite_key": "Fang2025",
        "text": (
            "Fang, H., Li, M., & Lu, G. (2025). Decoding China's Industrial "
            "Policies. NBER Working Paper No. 33814."
        ),
    },
    {
        "id": 2,
        "cite_key": "Zhang2018",
        "text": (
            "Zhang, B., Chen, X., & Guo, H. (2018). Does central supervision "
            "enhance local environmental enforcement? Quasi-experimental "
            "evidence from China. Journal of Public Economics, 164, 70–90."
        ),
    },
    {
        "id": 3,
        "cite_key": "Kostka2017",
        "text": (
            "Kostka, G., & Nahm, J. (2017). Central–local relations: "
            "Recentralization and environmental governance in China. "
            "The China Quarterly, 231, 567–582."
        ),
    },
    {
        "id": 4,
        "cite_key": "Chen2025",
        "text": (
            "Chen, W., Liao, L., & Yi, H. (2025). Multilevel policy textual "
            "learning in Chinese local environmental policies. Journal of Public "
            "Policy, 45(3), 500–521."
        ),
    },
    {
        "id": 5,
        "cite_key": "Lo2014",
        "text": (
            "Lo, K. (2014). China's low-carbon city initiatives: The "
            "implementation gap and the limits of the target responsibility "
            "system. Habitat International, 42, 236–244."
        ),
    },
    {
        "id": 6,
        "cite_key": "Gilardi2023",
        "text": (
            "Gilardi, F., Alizadeh, M., & Kubli, M. (2023). ChatGPT outperforms "
            "crowd workers for text-annotation tasks. Proceedings of the "
            "National Academy of Sciences, 120(30), e2305016120."
        ),
    },
    {
        "id": 7,
        "cite_key": "LeMens2025",
        "text": (
            "Le Mens, G., & Gallego, A. (2025). Positioning political texts with "
            "large language models by asking and averaging. Political Analysis, "
            "33(3), 274–282."
        ),
    },
    {
        "id": 8,
        "cite_key": "Fonseca2024",
        "text": (
            "Fonseca, M., & Cohen, S. (2024). Can large language models follow "
            "concept annotation guidelines? A case study on scientific and "
            "financial domains. Findings of the Association for Computational "
            "Linguistics: ACL 2024."
        ),
    },
    {
        "id": 9,
        "cite_key": "Tornberg2025",
        "text": (
            "Törnberg, P. (2025). Large language models outperform expert coders "
            "and supervised classifiers at annotating political social media "
            "messages. Social Science Computer Review, 43(6), 1181–1195."
        ),
    },
    {
        "id": 10,
        "cite_key": "Ziems2024",
        "text": (
            "Ziems, C., Held, W., Shaikh, O., Chen, J., Zhang, Z., & Yang, D. "
            "(2024). Can large language models transform computational social "
            "science? Computational Linguistics. Available via ACL Anthology."
        ),
    },
]
