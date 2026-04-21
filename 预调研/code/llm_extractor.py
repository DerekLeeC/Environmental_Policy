"""
模块2：基于LLM的多模型独立提取与交叉验证
═══════════════════════════════════════════════════
参考方法论：
  [1] Fang, Li & Lu (2025) "Decoding China's Industrial Policies", NBER WP 33814
      → 多LLM独立提取+交叉验证 "integrating multiple LLMs to mitigate hallucinations"
  [2] Kostka & Nahm (2017) "Central–local relations"
      → 央地关系 / vertical coordination / recentralization
  [3] Chen, Liao & Yi (2025) "Multilevel policy textual learning..."
      → 文本学习与政策扩散的内容层测量
  [4] Gilardi, Alizadeh & Kubli (2023)
      → LLM 文本标注可行，但必须做人工验证
  [5] Le Mens & Gallego (2025)
      → asking-and-averaging / aggregation 提高稳定性
  [6] Fonseca & Cohen (2024)
      → annotation guideline 必须足够明确
═══════════════════════════════════════════════════

架构：
  对每份政策文件：
    1. 三个模型（DeepSeek / MiniMax / Kimi）并行、独立完成全流程
       (Zero-shot 初提取 → Few-shot 精提取 → 自校验)
    2. 三份独立结果进行交叉验证，生成共识结果 + 分歧报告
  多份文件之间也支持并行处理
  对超长文本支持分段提取后合并
"""
import json
import re
import time
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI
from config import (
    SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL,
    MODEL_CONFIGS, ANALYSIS_MODEL,
    MAX_MODEL_WORKERS, MAX_FILE_WORKERS,
    API_MAX_RETRIES, API_RETRY_DELAY, API_TIMEOUT,
    EXTRACTED_TEXT_DIR, LLM_RESULTS_DIR, EXTRACTION_DIMENSIONS,
    MAX_CHARS_PER_CALL, ENABLE_SECTIONED_EXTRACTION,
    LITERATURE_REFERENCES,
)

# ──────────────────────────────────────────────
# API 客户端（共用同一个硅基流动 API Key）
# ──────────────────────────────────────────────
_client = OpenAI(
    api_key=SILICONFLOW_API_KEY,
    base_url=SILICONFLOW_BASE_URL,
    timeout=API_TIMEOUT,
)

# 列表维度合并时的共识阈值（≥此数的模型提及才保留）
CONSENSUS_THRESHOLD = 2

# JSON 解析失败时保留的原始响应最大长度
MAX_ERROR_RESPONSE_LENGTH = 500

# 鉴权失败关键词：命中后立即停止重试，避免把无效 token 当作暂时性波动
AUTH_ERROR_PATTERNS = (
    "401",
    "invalid token",
    "unauthorized",
    "authentication",
    "incorrect api key",
    "invalid api key",
    "api key",
)


class LLMAuthError(RuntimeError):
    """LLM 鉴权失败，调用方应视为 blocker。"""

# ──────────────────────────────────────────────
# Prompt 模板
# ──────────────────────────────────────────────

ZERO_SHOT_PROMPT = """你是一位中国环境政策研究专家。请阅读以下环境政策文件全文，并按要求提取结构化信息。

## 提取维度说明
{dimensions_desc}

## 输出要求
- 严格以JSON格式输出，key为英文维度名
- 列表类字段用JSON数组
- 如果文件中没有相关信息，填"未提及"
- 不要编造信息，所有提取内容必须有原文依据
- regulatory_stringency 字段请给出1-5的整数评分
- policy_objective_level 请从"投入型/过程型/产出型/结果型"中选择最主要的一个
- referenced_policies 请列出本文明确提及的上位法或依据的其他政策名称

## 政策文件全文
{policy_text}

请直接输出JSON，不要有其他文字："""

FEW_SHOT_PROMPT = """你是一位中国环境政策研究专家。请阅读以下环境政策文件，按照维度定义提取结构化信息。

参考政策工具研究中的经典 sticks / carrots / sermons 与 policy-mix 思路：
- 命令控制型(CAC)：排放标准、禁令、许可证、环评审批等
- 经济激励型(MBI)：税收、补贴、收费、生态补偿等
- 市场机制型(MKT)：排污权交易、碳交易等
- 信息公开型(INFO)：环境信息披露、公众参与、举报制度等
- 自愿型(VOL)：清洁生产审核、环境标志、自愿协议等

项目将政策目标层次编码为：
- 投入型(Input)：资金投入、人员配备等投入侧要求
- 过程型(Process)：制度建设、能力建设、机制构建
- 产出型(Output)：排放标准、削减量、达标率等直接产出
- 结果型(Outcome)：环境质量改善目标（如PM2.5浓度下降）

## 示例1：
输入：《中华人民共和国大气污染防治法》（2015年修订），全国人大常委会通过...
输出：
```json
{{
  "policy_name": "中华人民共和国大气污染防治法（2015年修订）",
  "doc_number": "主席令第三十一号",
  "issuing_authority": "全国人民代表大会常务委员会",
  "issue_date": "2015-08-29",
  "effective_date": "2016-01-01",
  "policy_type": "法律",
  "policy_tools": ["命令控制型", "经济激励型"],
  "target_industries": ["工业", "电力", "交通运输", "建筑施工"],
  "pollutant_types": ["大气污染物"],
  "policy_intensity": "强制性",
  "policy_tone": "严厉",
  "regulatory_stringency": 5,
  "gov_level": "中央",
  "vertical_coordination": "是，明确划分各级政府职责，要求地方制定配套实施细则，设立目标考核问责机制",
  "policy_objective_level": "产出型",
  "implementation_mechanism": ["排污许可制度", "环评审批", "总量控制", "区域联防联控", "目标责任考核"],
  "key_measures": ["实行大气污染物排放总量控制", "建立重点区域联防联控机制", "实行排污许可管理制度", "加强机动车船排放控制", "加大处罚力度最高按日计罚"],
  "quantitative_targets": ["未设定具体数值目标"],
  "penalty_provisions": "违法排污最高罚款100万元；情节严重的责令停产整治；拒不改正的按日连续处罚",
  "innovation_points": "首次引入按日连续处罚制度；建立重点区域大气污染联合防治机制",
  "referenced_policies": ["中华人民共和国环境保护法"]
}}
```

## 提取维度说明
{dimensions_desc}

## 待分析的政策文件全文
{policy_text}

请直接输出JSON，不要有其他文字："""

SELF_VERIFY_PROMPT = """你是一位严谨的政策文本审核专家。以下是你自己之前从一份环境政策文件中提取的结构化数据。
请逐字段核查是否与原文一致，修正任何错误，并给出置信度评分。

## 你之前的提取结果
{extraction_result}

## 政策原文（节选）
{policy_text_excerpt}

## 核查要求
对每个字段进行核查，输出JSON格式：
{{
  "verified_result": {{ ... 修正后的完整提取结果 ... }},
  "confidence_scores": {{
    "字段名": {{
      "score": 0.0到1.0的置信度,
      "evidence": "原文中的支撑证据（引用原文）",
      "issue": "如有问题，说明修正原因；如无问题填'准确'"
    }}
  }},
  "overall_confidence": 0.0到1.0
}}

请直接输出JSON："""

ANALYSIS_PROMPT = """你是一位资深的环境政策研究学者。请基于以下{num_files}份中国环境政策文件的结构化提取数据，
撰写一份深入的分析报告。

## 方法论背景
本研究参考以下前沿文献的分析框架：
- Fang, Li & Lu (2025): 多LLM交叉验证降低幻觉
- Kostka & Nahm (2017): 央地关系与环境治理
- Zhang et al. (2018): 中央监督与地方环境执法
- Chen, Liao & Yi (2025): policy textual learning / horizontal vs vertical learning
- Gilardi et al. (2023), Törnberg (2025): LLM 文本标注能力与人工对照
- Le Mens & Gallego (2025): asking-and-averaging / repeated elicitation
- Fonseca & Cohen (2024): 概念标注 guideline 的重要性

## 提取数据汇总
{all_results_json}

## 分析要求
请从以下角度进行系统分析，输出Markdown格式的报告：

### 1. 政策工具组合分析
- 各类政策工具（命令控制/经济激励/市场机制/信息公开/自愿）的使用频率
- 不同时期政策工具组合的变化趋势
- 政策工具类型与政策力度的关系
- 从"命令控制主导"向"多元工具组合"的演进分析

### 2. 政策强度与规制严格度分析
- 各文件的政策强度、语气和规制严格度评分分布
- 从法律到指导意见，不同法律位阶对应的规制严格度特征
- 时间维度上规制严格度的变化趋势

### 3. 央-地关系与纵向协调分析（参考Kostka & Nahm 2017）
- 中央与地方政策的关系模式
- 纵向协调机制的特征（权责划分、配套要求、考核问责）
- 地方政策对中央政策的响应模式

### 4. 政策目标层次分析
- 投入型/过程型/产出型/结果型目标的分布
- 不同政策类型的目标层次偏好
- 量化目标的设定特征

### 5. 目标行业与污染物覆盖分析
- 各文件涉及的行业和污染物类型分布
- 从大气→水→土壤→碳排放的政策关注点演变
- 行业覆盖的广度与深度

### 6. 政策关联网络分析
- 政策间引用关系的特征
- 核心法律（如环保法）的辐射范围
- 政策体系的层次结构

### 7. 多模型交叉验证可靠性评估
- 多模型独立提取的一致性分析（基于模型间一致率数据）
- 哪些维度模型间高度一致，哪些存在分歧
- 新增维度（规制严格度/目标层次/纵向协调）的提取质量评估
- 对后续大规模提取的方法论建议

请直接输出完整的Markdown格式报告："""


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def build_dimensions_desc() -> str:
    """构建维度描述文本"""
    lines = []
    for key, desc in EXTRACTION_DIMENSIONS.items():
        lines.append(f"- {key}: {desc}")
    return "\n".join(lines)


def truncate_text(text: str, max_chars: int = 12000) -> str:
    """截断文本以适应上下文窗口"""
    if len(text) <= max_chars:
        return text
    head = text[:max_chars // 2]
    tail = text[-(max_chars // 2):]
    return f"{head}\n\n[...中间部分省略...]\n\n{tail}"


def _is_auth_error_message(message: str) -> bool:
    """判断报错是否属于鉴权失败。"""
    lowered = (message or "").lower()
    return any(pattern in lowered for pattern in AUTH_ERROR_PATTERNS)


def _has_substantive_content(value) -> bool:
    """判断字段是否含有可用信息。"""
    if value is None:
        return False
    if isinstance(value, list):
        return any(_has_substantive_content(item) for item in value)
    if isinstance(value, dict):
        return any(_has_substantive_content(v) for v in value.values())
    text = str(value).strip()
    return text not in {"", "未提及", "None", "null"}


def _is_valid_final_result(result: dict) -> bool:
    """判断模型输出是否构成可用的结构化提取结果。"""
    if not isinstance(result, dict) or not result:
        return False
    if "error" in result:
        return False
    return any(_has_substantive_content(v) for v in result.values())


def split_text_for_extraction(full_text: str, sections: list = None) -> list[str]:
    """将超长文本分段以支持分段提取
    经验规则：对长文本按章节分段调用 LLM，再做结果聚合

    如果文本长度 ≤ MAX_CHARS_PER_CALL，直接返回 [full_text]。
    否则优先按已识别的章节分段；若无章节则按字符数均分。
    """
    if len(full_text) <= MAX_CHARS_PER_CALL or not ENABLE_SECTIONED_EXTRACTION:
        return [full_text]

    # 优先使用章节分段
    if sections and len(sections) > 1:
        chunks = []
        current_chunk = ""
        for sec in sections:
            content = sec.get("content", "")
            if len(current_chunk) + len(content) > MAX_CHARS_PER_CALL and current_chunk:
                chunks.append(current_chunk)
                current_chunk = content
            else:
                current_chunk += "\n\n" + content if current_chunk else content
        if current_chunk:
            chunks.append(current_chunk)
        return chunks if chunks else [full_text]

    # 无章节结构时按段落均分
    paragraphs = full_text.split("\n\n")
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) > MAX_CHARS_PER_CALL and current_chunk:
            chunks.append(current_chunk)
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para
    if current_chunk:
        chunks.append(current_chunk)
    return chunks if chunks else [full_text]


def call_llm(prompt: str, model_key: str = "deepseek",
             temperature: float = 0.1) -> tuple[str, str]:
    """调用 LLM API（带重试和错误处理）

    Args:
        prompt: 提示词
        model_key: 模型配置键名（deepseek / minimax / kimi）
        temperature: 温度参数

    Returns:
        (response_text, model_label) 元组
    """
    cfg = MODEL_CONFIGS[model_key]
    model_id = cfg["model"]
    model_label = cfg["label"]

    for attempt in range(1, API_MAX_RETRIES + 1):
        try:
            response = _client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=4096,
            )
            if not response.choices:
                raise ValueError("API返回空的choices列表")
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("API返回的content为None")
            return content.strip(), model_label

        except Exception as e:
            error_message = str(e)
            if _is_auth_error_message(error_message):
                print(f"    ✗ [{model_label}] 鉴权失败，停止重试: {error_message}")
                raise LLMAuthError(f"{model_label}: {error_message}") from e

            print(f"    ⚠ [{model_label}] API调用失败 (尝试 {attempt}/{API_MAX_RETRIES}): {error_message}")
            if attempt < API_MAX_RETRIES:
                wait = API_RETRY_DELAY * attempt
                print(f"    ⏳ {wait}秒后重试...")
                time.sleep(wait)
            else:
                print(f"    ✗ [{model_label}] 已达最大重试次数")
                return "", model_label


def parse_json_response(text: str) -> dict:
    """从LLM响应中解析JSON"""
    if not text:
        return {"error": "空响应", "raw_response": ""}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return {"error": "无法解析JSON", "raw_response": text[:MAX_ERROR_RESPONSE_LENGTH]}


# ──────────────────────────────────────────────
# 单模型全流程提取（三步：Zero-shot → Few-shot → 自校验）
# ──────────────────────────────────────────────

def _build_stage_audit(stage_name: str, model_key: str, temperature: float,
                       prompt: str, input_text: str, response_text: str,
                       parsed_result: dict, chunk_index: int | None = None) -> dict:
    """构建单次 LLM 调用的可审计记录。"""
    cfg = MODEL_CONFIGS[model_key]
    return {
        "stage": stage_name,
        "chunk_index": chunk_index,
        "model_key": model_key,
        "model_label": cfg["label"],
        "model_id": cfg["model"],
        "temperature": temperature,
        "input_chars": len(input_text),
        "input_excerpt": truncate_text(input_text, max_chars=1200),
        "prompt": prompt,
        "raw_response": response_text,
        "parsed_result": parsed_result,
    }


def _run_pipeline_on_text(text_input: str, model_key: str,
                          chunk_index: int | None = None) -> dict:
    """在单段文本上执行完整三阶段抽取，并保存审计轨迹。"""
    dims_desc = build_dimensions_desc()
    stage_audit = []

    prompt_zs = ZERO_SHOT_PROMPT.format(
        dimensions_desc=dims_desc,
        policy_text=truncate_text(text_input),
    )
    resp_zs, _ = call_llm(prompt_zs, model_key=model_key, temperature=0.1)
    zero_shot_result = parse_json_response(resp_zs)
    stage_audit.append(_build_stage_audit(
        stage_name="zero_shot",
        model_key=model_key,
        temperature=0.1,
        prompt=prompt_zs,
        input_text=text_input,
        response_text=resp_zs,
        parsed_result=zero_shot_result,
        chunk_index=chunk_index,
    ))

    prompt_fs = FEW_SHOT_PROMPT.format(
        dimensions_desc=dims_desc,
        policy_text=truncate_text(text_input),
    )
    resp_fs, _ = call_llm(prompt_fs, model_key=model_key, temperature=0.05)
    few_shot_result = parse_json_response(resp_fs)
    stage_audit.append(_build_stage_audit(
        stage_name="few_shot",
        model_key=model_key,
        temperature=0.05,
        prompt=prompt_fs,
        input_text=text_input,
        response_text=resp_fs,
        parsed_result=few_shot_result,
        chunk_index=chunk_index,
    ))

    prompt_vf = SELF_VERIFY_PROMPT.format(
        extraction_result=json.dumps(few_shot_result, ensure_ascii=False, indent=2),
        policy_text_excerpt=truncate_text(text_input, max_chars=8000),
    )
    resp_vf, _ = call_llm(prompt_vf, model_key=model_key, temperature=0.05)
    verification = parse_json_response(resp_vf)
    stage_audit.append(_build_stage_audit(
        stage_name="self_verify",
        model_key=model_key,
        temperature=0.05,
        prompt=prompt_vf,
        input_text=text_input,
        response_text=resp_vf,
        parsed_result=verification,
        chunk_index=chunk_index,
    ))

    return {
        "chunk_index": chunk_index,
        "zero_shot_result": zero_shot_result,
        "few_shot_result": few_shot_result,
        "verification": verification,
        "final_result": verification.get("verified_result", few_shot_result),
        "overall_confidence": verification.get("overall_confidence", None),
        "confidence_scores": verification.get("confidence_scores", {}),
        "stage_audit": stage_audit,
    }


def _merge_chunk_outputs(chunk_runs: list[dict], field: str) -> dict:
    """使用与跨模型一致的规则合并分段结果。"""
    pseudo_results = []
    for idx, chunk_run in enumerate(chunk_runs, start=1):
        pseudo_results.append({
            "model_label": f"chunk_{idx}",
            "final_result": chunk_run.get(field, {}),
            "overall_confidence": chunk_run.get("overall_confidence"),
        })
    return cross_validate_and_merge(pseudo_results)


def _run_single_model_pipeline(policy_text: str, model_key: str,
                               sections: list = None) -> dict:
    """单个模型独立完成三阶段全流程提取

    每个模型自行完成：
      Step A: Zero-shot 初步提取
      Step B: Few-shot + CoT 精细提取
      Step C: 自校验（验证并修正 Step B 的结果）

    对超长文本支持分段提取。

    Args:
        policy_text: 政策文件全文
        model_key: 模型键名
        sections: 已识别的章节列表（用于分段提取）

    Returns:
        单模型完整提取结果 dict
    """
    label = MODEL_CONFIGS[model_key]["label"]

    # 分段提取：对超长文本按章节分段调用LLM
    text_chunks = split_text_for_extraction(policy_text, sections)
    use_sectioned = len(text_chunks) > 1
    if use_sectioned:
        print(f"      [{label}] 启用分段提取 ({len(text_chunks)} 段)")
    if not use_sectioned:
        single_run = _run_pipeline_on_text(policy_text, model_key=model_key)
        return {
            "model_key": model_key,
            "model_label": label,
            "zero_shot_result": single_run["zero_shot_result"],
            "few_shot_result": single_run["few_shot_result"],
            "verification": single_run["verification"],
            "final_result": single_run["final_result"],
            "overall_confidence": single_run["overall_confidence"],
            "confidence_scores": single_run["confidence_scores"],
            "used_sectioned_extraction": False,
            "chunk_count": 1,
            "chunk_results": [],
            "stage_audit": single_run["stage_audit"],
        }

    chunk_runs = []
    for idx, chunk_text in enumerate(text_chunks, start=1):
        print(f"        [{label}] 处理分段 {idx}/{len(text_chunks)}")
        chunk_runs.append(_run_pipeline_on_text(chunk_text, model_key=model_key, chunk_index=idx))

    zero_merge = _merge_chunk_outputs(chunk_runs, "zero_shot_result")
    few_merge = _merge_chunk_outputs(chunk_runs, "few_shot_result")
    final_merge = _merge_chunk_outputs(chunk_runs, "final_result")

    return {
        "model_key": model_key,
        "model_label": label,
        "zero_shot_result": zero_merge["consensus_result"],
        "few_shot_result": few_merge["consensus_result"],
        "verification": {
            "mode": "chunk_merged",
            "chunk_level_verification": [cr["verification"] for cr in chunk_runs],
            "merge_disagreements": final_merge["disagreements"],
        },
        "final_result": final_merge["consensus_result"],
        "overall_confidence": final_merge["agreement_rate"],
        "confidence_scores": {
            "_chunk_confidence": {
                f"chunk_{cr['chunk_index']}": cr.get("overall_confidence")
                for cr in chunk_runs
            }
        },
        "used_sectioned_extraction": True,
        "chunk_count": len(chunk_runs),
        "chunk_results": [
            {
                "chunk_index": cr["chunk_index"],
                "overall_confidence": cr.get("overall_confidence"),
                "final_result": cr.get("final_result", {}),
            }
            for cr in chunk_runs
        ],
        "stage_audit": [
            audit_record
            for cr in chunk_runs
            for audit_record in cr["stage_audit"]
        ],
    }


# ──────────────────────────────────────────────
# 多模型交叉验证与共识合并
# ──────────────────────────────────────────────

# 需要投票判定的分类维度
_CATEGORICAL_DIMS = {
    "policy_type", "policy_intensity", "policy_tone", "gov_level",
    "regulatory_stringency", "policy_objective_level",
}
# 需要取并集的列表维度
_LIST_DIMS = {
    "policy_tools", "target_industries", "pollutant_types",
    "key_measures", "quantitative_targets",
    "implementation_mechanism", "referenced_policies",
}
# 取最长 / 信息量最大的文本维度
_TEXT_DIMS = {
    "policy_name", "doc_number", "issuing_authority",
    "issue_date", "effective_date",
    "penalty_provisions", "innovation_points",
    "vertical_coordination",
}


def _majority_vote(values: list):
    """多数投票：返回出现次数最多的值"""
    if not values:
        return None
    counter = Counter(str(v) for v in values)
    winner, _ = counter.most_common(1)[0]
    # 返回原始类型
    for v in values:
        if str(v) == winner:
            return v
    return values[0]


def _merge_lists(lists: list[list]) -> list:
    """合并多个列表，保留所有出现≥2次的元素（多数共识），不足2份则保留全部"""
    if not lists:
        return []
    all_items = []
    for lst in lists:
        if isinstance(lst, list):
            all_items.extend(lst)
        elif isinstance(lst, str) and lst != "未提及":
            all_items.append(lst)
    counter = Counter(all_items)
    n_models = len(lists)
    threshold = CONSENSUS_THRESHOLD if n_models >= 3 else 1
    consensus = [item for item, cnt in counter.most_common() if cnt >= threshold]
    if not consensus and all_items:
        consensus = list(dict.fromkeys(all_items))  # 去重保序
    return consensus


def _pick_best_text(texts: list[str]) -> str:
    """从多份文本中选取信息量最大的（最长非空）"""
    valid = [t for t in texts if t and str(t) != "未提及"]
    if not valid:
        return texts[0] if texts else "未提及"
    return max(valid, key=lambda t: len(str(t)))


def cross_validate_and_merge(model_results: list[dict]) -> dict:
    """对多个模型的独立提取结果进行交叉验证与共识合并

    Returns:
        {
            "consensus_result": { 合并后的最终结果 },
            "agreement_rate": float (0~1),
            "per_dim_agreement": { dim: rate },
            "disagreements": [ { dim, values_by_model } ],
            "per_model_confidence": { model_label: confidence },
        }
    """
    # 收集可用输出，并单独记录失败模型，避免“全失败也算一致”
    valid_pairs = []
    invalid_model_details = []
    for mr in model_results:
        model_label = mr.get("model_label", "unknown_model")
        final_result = mr.get("final_result", {})
        if _is_valid_final_result(final_result):
            valid_pairs.append((model_label, final_result))
            continue

        error_message = ""
        if isinstance(final_result, dict):
            error_message = str(final_result.get("error", ""))
        if not error_message:
            error_message = str(mr.get("error", "")) or "无有效结构化输出"

        invalid_model_details.append({
            "model_label": model_label,
            "error_type": mr.get("error_type", "invalid_output"),
            "error_message": error_message,
        })

    valid_model_count = len(valid_pairs)
    failed_model_count = len(invalid_model_details)

    if not valid_pairs:
        return {
            "consensus_result": {},
            "agreement_rate": None,
            "per_dim_agreement": {},
            "disagreements": [],
            "per_model_confidence": {},
            "status": "failed_no_valid_model_output",
            "valid_model_count": 0,
            "failed_model_count": failed_model_count,
            "usable_model_labels": [],
            "invalid_model_details": invalid_model_details,
        }

    all_finals = [fr for _, fr in valid_pairs]
    labels = [lbl for lbl, _ in valid_pairs]
    agreement_defined = valid_model_count >= 2

    # 合并
    consensus = {}
    per_dim_agreement = {}
    disagreements = []

    all_dims = set()
    for fr in all_finals:
        all_dims.update(fr.keys())
    # 也加入预定义维度
    all_dims.update(EXTRACTION_DIMENSIONS.keys())

    for dim in sorted(all_dims):
        values = [fr.get(dim) for fr in all_finals]

        if dim in _CATEGORICAL_DIMS:
            merged = _majority_vote(values)
            agree = (
                sum(1 for v in values if str(v) == str(merged)) / len(values)
                if agreement_defined and values else None
            )
        elif dim in _LIST_DIMS:
            lists = [v if isinstance(v, list) else [v] for v in values if v is not None]
            merged = _merge_lists(lists)
            # 一致性：Jaccard 相似度
            if agreement_defined and len(lists) >= 2:
                sets = [set(str(x) for x in lst) for lst in lists]
                union = set().union(*sets)
                inter = sets[0]
                for s in sets[1:]:
                    inter = inter.intersection(s)
                agree = len(inter) / len(union) if union else 1.0
            else:
                agree = None
        elif dim in _TEXT_DIMS:
            str_values = [str(v) if v is not None else "" for v in values]
            merged = _pick_best_text(str_values)
            agree = (
                sum(1 for v in str_values if v == str(merged)) / len(str_values)
                if agreement_defined and str_values else None
            )
        else:
            # 未知维度：多数投票
            merged = _majority_vote([v for v in values if v is not None])
            agree = (
                sum(1 for v in values if str(v) == str(merged)) / len(values)
                if agreement_defined and values else None
            )

        consensus[dim] = merged
        per_dim_agreement[dim] = round(agree, 3) if agree is not None else None

        if agree is not None and agree < 1.0:
            disagreements.append({
                "dimension": dim,
                "values_by_model": {lbl: values[i] for i, lbl in enumerate(labels) if i < len(values)},
                "merged_value": merged,
                "agreement": round(agree, 3),
            })

    valid_agreement_values = [v for v in per_dim_agreement.values() if v is not None]
    overall_agreement = (
        round(sum(valid_agreement_values) / len(valid_agreement_values), 3)
        if valid_agreement_values else None
    )

    per_model_conf = {}
    for mr in model_results:
        c = mr.get("overall_confidence")
        if c is not None:
            per_model_conf[mr["model_label"]] = c

    if valid_model_count == len(model_results):
        status = "success"
    elif valid_model_count == 1:
        status = "partial_single_model_only"
    else:
        status = "partial_with_failures"

    return {
        "consensus_result": consensus,
        "agreement_rate": overall_agreement,
        "per_dim_agreement": per_dim_agreement,
        "disagreements": disagreements,
        "per_model_confidence": per_model_conf,
        "status": status,
        "valid_model_count": valid_model_count,
        "failed_model_count": failed_model_count,
        "usable_model_labels": labels,
        "invalid_model_details": invalid_model_details,
    }


# ──────────────────────────────────────────────
# 单份文件提取入口（三模型并行 + 交叉验证）
# ──────────────────────────────────────────────

def extract_single_policy(extracted_data: dict) -> dict:
    """对单份政策文件执行多模型独立提取 + 交叉验证

    三个模型并行、各自独立完成全流程，然后合并结果。
    """
    file_name = extracted_data["file_name"]
    full_text = extracted_data["full_text"]
    sections = extracted_data.get("sections", [])
    print(f"\n{'─' * 50}")
    print(f"处理: {file_name}")

    model_keys = list(MODEL_CONFIGS.keys())
    model_results = []

    # 三个模型并行独立提取
    print(f"  ⚡ 并行启动 {len(model_keys)} 个模型独立提取...")
    with ThreadPoolExecutor(max_workers=MAX_MODEL_WORKERS) as executor:
        future_to_key = {
            executor.submit(_run_single_model_pipeline, full_text, mk, sections): mk
            for mk in model_keys
        }
        for future in as_completed(future_to_key):
            mk = future_to_key[future]
            label = MODEL_CONFIGS[mk]["label"]
            try:
                res = future.result()
                model_results.append(res)
                conf = res.get("overall_confidence", "N/A")
                print(f"    ✓ {label} 完成 (置信度: {conf})")
            except Exception as e:
                print(f"    ✗ {label} 失败: {e}")
                traceback.print_exc()
                error_type = "auth_error" if isinstance(e, LLMAuthError) else "runtime_error"
                model_results.append({
                    "model_key": mk,
                    "model_label": label,
                    "zero_shot_result": {},
                    "few_shot_result": {},
                    "verification": {},
                    "final_result": {"error": str(e)},
                    "overall_confidence": None,
                    "confidence_scores": {},
                    "error_type": error_type,
                    "error": str(e),
                })

    # 交叉验证合并
    print("  🔀 交叉验证合并结果...")
    cross_val = cross_validate_and_merge(model_results)

    result = {
        "file_name": file_name,
        "char_count": extracted_data["char_count"],
        "total_pages": extracted_data["total_pages"],
        "section_count": extracted_data.get("section_count", 0),
        "text_source": extracted_data.get("text_source", "unknown"),
        "rescued_text_path": extracted_data.get("rescued_text_path", ""),
        "model_results": model_results,
        "cross_validation": cross_val,
        "final_result": cross_val["consensus_result"],
        "overall_confidence": cross_val["agreement_rate"],
        "agreement_rate": cross_val["agreement_rate"],
        "extraction_status": cross_val.get("status", "unknown"),
        "per_dim_agreement": cross_val["per_dim_agreement"],
        "disagreements": cross_val["disagreements"],
        "per_model_confidence": cross_val.get("per_model_confidence", {}),
        "valid_model_count": cross_val.get("valid_model_count", 0),
        "failed_model_count": cross_val.get("failed_model_count", 0),
        "usable_model_labels": cross_val.get("usable_model_labels", []),
        "invalid_model_details": cross_val.get("invalid_model_details", []),
    }

    # 保存单份结果
    out_path = LLM_RESULTS_DIR / f"{Path(file_name).stem}_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    n_disagree = len(cross_val["disagreements"])
    total_dims = len(cross_val["per_dim_agreement"])
    agreement_rate = cross_val["agreement_rate"]
    print(f"  → 提取状态: {cross_val.get('status', 'unknown')}")
    if agreement_rate is None:
        print("  → 模型间一致率: N/A（有效输出不足两模型）")
    else:
        print(f"  → 模型间一致率: {agreement_rate:.1%}")
    print(f"  → 分歧维度: {n_disagree}/{total_dims}")
    if cross_val.get("invalid_model_details"):
        print(f"  → 无效模型输出: {len(cross_val['invalid_model_details'])}")
    for mc, cv in cross_val.get("per_model_confidence", {}).items():
        print(f"    {mc}: 置信度 {cv}")

    return result


# ──────────────────────────────────────────────
# 所有文件并行提取
# ──────────────────────────────────────────────

def extract_all_policies(extracted_texts: list[dict]) -> list[dict]:
    """对所有政策文件执行并行提取"""
    total = len(extracted_texts)
    all_results = [None] * total  # 保持顺序

    print(f"\n⚡ 启动并行文件处理 (最多 {MAX_FILE_WORKERS} 个文件同时处理)")

    with ThreadPoolExecutor(max_workers=MAX_FILE_WORKERS) as executor:
        future_to_idx = {
            executor.submit(extract_single_policy, data): i
            for i, data in enumerate(extracted_texts)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            fname = extracted_texts[idx]["file_name"]
            try:
                result = future.result()
                all_results[idx] = result
                print(f"\n[{sum(1 for r in all_results if r is not None)}/{total}] "
                      f"✓ {fname}")
            except Exception as e:
                print(f"\n[?/{total}] ✗ {fname}: {e}")
                traceback.print_exc()
                all_results[idx] = {
                    "file_name": fname,
                    "char_count": extracted_texts[idx].get("char_count", 0),
                    "total_pages": extracted_texts[idx].get("total_pages", 0),
                    "section_count": extracted_texts[idx].get("section_count", 0),
                    "text_source": extracted_texts[idx].get("text_source", "unknown"),
                    "rescued_text_path": extracted_texts[idx].get("rescued_text_path", ""),
                    "model_results": [],
                    "cross_validation": {},
                    "final_result": {},
                    "overall_confidence": None,
                    "agreement_rate": None,
                    "extraction_status": "file_level_error",
                    "per_dim_agreement": {},
                    "disagreements": [],
                    "per_model_confidence": {},
                    "valid_model_count": 0,
                    "failed_model_count": 0,
                    "usable_model_labels": [],
                    "invalid_model_details": [],
                    "error": str(e),
                }

    # 保存汇总
    summary_path = LLM_RESULTS_DIR / "all_results_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        summary = []
        for r in all_results:
            summary.append({
                "file_name": r["file_name"],
                "final_result": r["final_result"],
                "overall_confidence": r["overall_confidence"],
                "agreement_rate": r.get("agreement_rate"),
                "extraction_status": r.get("extraction_status", "unknown"),
                "per_model_confidence": r.get("per_model_confidence", {}),
                "text_source": r.get("text_source", "unknown"),
                "rescued_text_path": r.get("rescued_text_path", ""),
            })
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return all_results


# ──────────────────────────────────────────────
# 综合分析报告
# ──────────────────────────────────────────────

def generate_analysis_report(all_results: list[dict]) -> str:
    """基于提取结果生成综合分析报告"""
    print("\n" + "=" * 60)
    print("生成综合分析报告...")

    summary_data = []
    for r in all_results:
        summary_data.append({
            "file_name": r["file_name"],
            "final_result": r["final_result"],
            "overall_confidence": r["overall_confidence"],
            "agreement_rate": r.get("agreement_rate"),
            "text_source": r.get("text_source", "unknown"),
        })

    prompt = ANALYSIS_PROMPT.format(
        num_files=len(summary_data),
        all_results_json=json.dumps(summary_data, ensure_ascii=False, indent=2),
    )

    response, model_label = call_llm(prompt, model_key=ANALYSIS_MODEL,
                                     temperature=0.3)
    print(f"  使用模型: {model_label}")
    return response if response else "（综合分析报告生成失败，请检查API配置后重试）"
