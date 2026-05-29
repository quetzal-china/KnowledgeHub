"""
report_generator.py — 报告生成模块

将 arXiv 论文数据 + 知乎讨论数据喂给 LLM，生成 Markdown 调研报告

方案 A: 知乎综合摘要 — LLM 汇总多条摘要，生成社区观点概述
方案 C: arXiv × 知乎交叉分析 — 理论与实践对照

对外接口:
    generate_report(query, arxiv_data, zhihu_data) → str (Markdown)
"""

import logging
from src.llm_client import chat_text

logger = logging.getLogger(__name__)

REPORT_SYSTEM_PROMPT = (
    "你是一位专业的技术调研分析师，擅长将学术论文和社区讨论"
    "整合为结构清晰的调研报告。输出纯 Markdown，不要用代码块包裹。"
)

REPORT_PROMPT_TEMPLATE = """请根据以下数据生成一份技术调研报告。

## 用户查询
{query}

## arXiv 论文数据 ({arxiv_count} 条)
{arxiv_section}

## 知乎讨论数据 ({zhihu_count} 条)
{zhihu_section}

## 报告要求

1. **标题**: 基于用户查询生成简洁的中文标题
2. **理论研究 (arXiv)**: 按主题分组，每组列出关键论文的标题和核心发现（2-3句话概括），附论文链接
3. **工程实践 (知乎)**: 先写一段综合摘要（方案A），概括社区关注的主要方向和观点；再列出精选高赞讨论，附点赞数和链接
4. **理论 × 实践对照** (方案C): 用表格对比，找出理论和实践的交叉点
5. **总结**: 一段话概括核心发现

格式要求:
- 用 Markdown 格式
- 论文标题用英文原文
- 链接用 Markdown 超链接格式
- 表格用 Markdown 表格语法
- 不要输出 ```markdown 代码块包裹，直接输出 Markdown 内容"""

MAX_ARXIV_PAPERS = 25
MAX_ZHIHU_ITEMS = 10
MAX_ABSTRACT_LEN = 200


def _truncate_text(text: str, max_len: int = MAX_ABSTRACT_LEN) -> str:
    """截断文本，超长时追加省略号，短文本不加"""
    if not text or len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _format_arxiv_section(arxiv_data: list[dict]) -> str:
    """将 arXiv 数据格式化为 LLM 可读的文本"""
    if not arxiv_data:
        return "（无 arXiv 数据）"

    papers = arxiv_data[:MAX_ARXIV_PAPERS]
    lines = []
    for i, paper in enumerate(papers, 1):
        title = paper.get("title", "无标题")
        abstract = _truncate_text(paper.get("abstract", ""))
        url = paper.get("paper_url", "")
        authors = ", ".join(paper.get("authors", [])[:3])
        if len(paper.get("authors", [])) > 3:
            authors += " et al."

        lines.append(f"{i}. **{title}**")
        lines.append(f"   作者: {authors}")
        lines.append(f"   摘要: {abstract}")
        if url:
            lines.append(f"   链接: {url}")
        lines.append("")

    if len(arxiv_data) > MAX_ARXIV_PAPERS:
        lines.append(f"（共 {len(arxiv_data)} 条，已截取前 {MAX_ARXIV_PAPERS} 条）")

    return "\n".join(lines)


def _format_zhihu_section(zhihu_data: list[dict]) -> str:
    """将知乎数据格式化为 LLM 可读的文本"""
    if not zhihu_data:
        return "（无知乎数据）"

    items = zhihu_data[:MAX_ZHIHU_ITEMS]
    lines = []
    for i, item in enumerate(items, 1):
        title = item.get("title", "无标题")
        excerpt = _truncate_text(item.get("excerpt", ""))
        url = item.get("url", "")
        votes = item.get("voteup_count", 0)
        author = item.get("author_name", "匿名")
        comments = item.get("comment_count", 0)

        lines.append(f"{i}. **{title}**")
        lines.append(f"   作者: {author} | ⬆️{votes}赞 | 💬{comments}评论")
        lines.append(f"   摘要: {excerpt}")
        if url:
            lines.append(f"   链接: {url}")
        lines.append("")

    if len(zhihu_data) > MAX_ZHIHU_ITEMS:
        lines.append(f"（共 {len(zhihu_data)} 条，已截取前 {MAX_ZHIHU_ITEMS} 条）")

    return "\n".join(lines)


def generate_report(
    query: str,
    arxiv_data: list[dict],
    zhihu_data: list[dict],
) -> str:
    """
    生成 Markdown 调研报告

    参数:
        query:      用户原始查询
        arxiv_data: arXiv 搜索结果列表 (来自 Scrapy 或 JSON)
        zhihu_data: 知乎搜索结果列表 (来自 zhihu_client)

    返回:
        Markdown 格式的调研报告字符串
    """
    arxiv_section = _format_arxiv_section(arxiv_data)
    zhihu_section = _format_zhihu_section(zhihu_data)

    prompt = REPORT_PROMPT_TEMPLATE.format(
        query=query,
        arxiv_count=len(arxiv_data),
        zhihu_count=len(zhihu_data),
        arxiv_section=arxiv_section,
        zhihu_section=zhihu_section,
    )

    logger.info(
        f"[Report] 生成报告: query='{query}' "
        f"arxiv={len(arxiv_data)} zhihu={len(zhihu_data)}"
    )

    report = chat_text(
        user_message=prompt,
        system_message=REPORT_SYSTEM_PROMPT,
        temperature=0.5,
        max_tokens=8192,
    )

    return report


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    mock_arxiv = [
        {
            "title": "Flash Attention 2: Faster and Better Attention",
            "authors": ["Tri Dao"],
            "abstract": "We propose Flash Attention 2, a faster and more memory-efficient attention algorithm that achieves 2x speedup over Flash Attention 1.",
            "paper_url": "https://arxiv.org/abs/2307.08691",
        },
        {
            "title": "GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers",
            "authors": ["Elias Frantar", "Saleh Ashkboos"],
            "abstract": "GPTQ enables efficient 4-bit quantization of large language models with minimal accuracy loss.",
            "paper_url": "https://arxiv.org/abs/2210.17323",
        },
    ]

    mock_zhihu = [
        {
            "title": "Transformer推理加速实战总结",
            "excerpt": "本文总结了Flash Attention、vLLM等主流加速方案的实际部署经验",
            "url": "https://zhuanlan.zhihu.com/p/example1",
            "voteup_count": 2345,
            "comment_count": 89,
            "author_name": "某工程师",
        },
        {
            "title": "LLM量化从GPTQ到AWQ全对比",
            "excerpt": "系统对比了GPTQ、AWQ、SmoothQuant等量化方案的精度和速度",
            "url": "https://zhuanlan.zhihu.com/p/example2",
            "voteup_count": 1890,
            "comment_count": 56,
            "author_name": "量化专家",
        },
    ]

    report = generate_report("Transformer优化", mock_arxiv, mock_zhihu)
    print(report)
