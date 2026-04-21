"""模块1：PDF文本提取与预处理"""
import re
import json
import pdfplumber
from pathlib import Path
from config import PDF_DIR, EXTRACTED_TEXT_DIR

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
RESCUED_TEXT_DIR = WORKSPACE_ROOT / "data" / "interim" / "source_text"


def extract_text_from_pdf(pdf_path: Path) -> dict:
    """从单个PDF中提取全文文本，返回结构化结果"""
    result = {
        "file_name": pdf_path.name,
        "file_path": str(pdf_path),
        "total_pages": 0,
        "pages": [],
        "full_text": "",
        "char_count": 0,
        "text_source": "pdfplumber",
        "rescued_text_path": "",
    }

    rescued_text_path = RESCUED_TEXT_DIR / f"{pdf_path.stem}.txt"
    if rescued_text_path.exists():
        rescued_text = clean_text(rescued_text_path.read_text(encoding="utf-8"))
        try:
            with pdfplumber.open(pdf_path) as pdf:
                result["total_pages"] = len(pdf.pages)
        except Exception:
            result["total_pages"] = 0
        result["pages"] = [{
            "page_num": 1,
            "text": rescued_text,
            "char_count": len(rescued_text),
            "source": "official_html_rescue",
        }]
        result["full_text"] = rescued_text
        result["char_count"] = len(rescued_text)
        result["text_source"] = "official_html_rescue"
        result["rescued_text_path"] = str(rescued_text_path)
        return result

    with pdfplumber.open(pdf_path) as pdf:
        result["total_pages"] = len(pdf.pages)
        all_text = []
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            text = clean_text(text)
            result["pages"].append({
                "page_num": i + 1,
                "text": text,
                "char_count": len(text),
            })
            all_text.append(text)

        result["full_text"] = "\n\n".join(all_text)
        result["char_count"] = len(result["full_text"])

    return result


def clean_text(text: str) -> str:
    """清洗文本：去除多余空白、修复断行"""
    # 去除多余空格（保留换行）
    text = re.sub(r'[ \t]+', ' ', text)
    # 去除页码行（如 "- 1 -" 或 "— 3 —"）
    text = re.sub(r'^[\s]*[-—]\s*\d+\s*[-—][\s]*$', '', text, flags=re.MULTILINE)
    # 合并非段落的断行（中文字符间的断行）
    text = re.sub(r'(?<=[\u4e00-\u9fff])\n(?=[\u4e00-\u9fff])', '', text)
    # 去除首尾空白
    text = text.strip()
    return text


def split_into_sections(full_text: str) -> list[dict]:
    """将全文按章节/条款分段"""
    sections = []
    # 匹配常见的章节标题模式
    patterns = [
        r'(第[一二三四五六七八九十百]+章\s*.+)',      # 第X章
        r'(第[一二三四五六七八九十百]+条\s*.+)',      # 第X条（法律）
        r'([一二三四五六七八九十]+、\s*.+)',           # 一、二、三、
        r'(（[一二三四五六七八九十]+）\s*.+)',         # （一）（二）
    ]

    # 先尝试按"章"分
    chapter_pattern = r'(第[一二三四五六七八九十百]+章[\s　]*[^\n]+)'
    chapter_splits = re.split(chapter_pattern, full_text)

    if len(chapter_splits) > 2:
        # 有章节结构
        # chapter_splits: [前文, 章标题1, 章内容1, 章标题2, 章内容2, ...]
        if chapter_splits[0].strip():
            sections.append({"title": "前言/总则", "content": chapter_splits[0].strip()})
        for i in range(1, len(chapter_splits), 2):
            title = chapter_splits[i].strip() if i < len(chapter_splits) else ""
            content = chapter_splits[i + 1].strip() if i + 1 < len(chapter_splits) else ""
            sections.append({"title": title, "content": f"{title}\n{content}"})
    else:
        # 无章节结构，尝试按大标题分（一、二、三、）
        item_pattern = r'([一二三四五六七八九十]+、[^\n]+)'
        item_splits = re.split(item_pattern, full_text)
        if len(item_splits) > 2:
            if item_splits[0].strip():
                sections.append({"title": "总体要求", "content": item_splits[0].strip()})
            for i in range(1, len(item_splits), 2):
                title = item_splits[i].strip() if i < len(item_splits) else ""
                content = item_splits[i + 1].strip() if i + 1 < len(item_splits) else ""
                sections.append({"title": title, "content": f"{title}\n{content}"})
        else:
            # 无明显结构，整篇作为一段
            sections.append({"title": "全文", "content": full_text})

    return sections


def process_pdf_paths(pdf_files: list[Path]) -> list[dict]:
    """处理指定 PDF 路径列表，返回提取结果列表"""
    results = []

    for pdf_path in pdf_files:
        print(f"  提取中: {pdf_path.name}")
        extracted = extract_text_from_pdf(pdf_path)
        extracted["sections"] = split_into_sections(extracted["full_text"])
        extracted["section_count"] = len(extracted["sections"])

        # 保存提取的文本到文件
        out_path = EXTRACTED_TEXT_DIR / f"{pdf_path.stem}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(extracted, f, ensure_ascii=False, indent=2)

        results.append(extracted)
        print(f"    → {extracted['total_pages']}页, {extracted['char_count']}字, {extracted['section_count']}段")

    return results


def process_selected_pdfs(file_names: list[str]) -> list[dict]:
    """按文件名处理指定 PDF，文件名需与 `PDF_DIR` 下实际文件一致。"""
    selected_paths = []
    missing = []
    for file_name in file_names:
        pdf_path = PDF_DIR / file_name
        if pdf_path.exists():
            selected_paths.append(pdf_path)
        else:
            missing.append(file_name)

    if missing:
        raise FileNotFoundError(
            "Selected PDF files not found: " + ", ".join(missing)
        )

    return process_pdf_paths(selected_paths)


def process_all_pdfs() -> list[dict]:
    """处理所有PDF文件，返回提取结果列表"""
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    return process_pdf_paths(pdf_files)


if __name__ == "__main__":
    print("=" * 60)
    print("PDF文本提取与预处理")
    print("=" * 60)
    results = process_all_pdfs()
    print(f"\n共处理 {len(results)} 份文件")
    total_chars = sum(r["char_count"] for r in results)
    print(f"总字符数: {total_chars:,}")
