"""
smart_search.py — 智能搜索模块

流程: 用户自然语言 → LLM 生成搜索参数 → 构建 arXiv URL → 供 Scrapy 爬虫使用

对外接口:
    smart_search(query) → dict
    返回: {"url": "https://arxiv.org/search/...", "keywords": [...], "order": "...", "size": 30}
    Scrapy 通过 scrapy crawl arxiv -a url=<url> 调用
"""

import json
from urllib.parse import quote
from src.llm_client import chat_json
from src.search_strategy import ARXIV_SEARCH_STRATEGY

# arXiv 搜索 URL 模板，与 docs/reference.md 保持一致
ARXIV_SEARCH_BASE = "https://arxiv.org/search/"

# order 参数值 → 含义映射
ORDER_MAP = {
    "announced_date_first": "时间正序（旧→新）",
    "-announced_date_first": "时间倒序（新→旧）",
    "": "相关性排序",
}


def build_llm_prompt(user_query: str) -> str:
    """构建 LLM prompt，要求输出标准化的搜索参数 JSON"""
    return f"""根据用户需求生成arXiv搜索参数。

用户: {user_query}

arXiv语法:
{ARXIV_SEARCH_STRATEGY}

输出JSON:
{{"intent":"","keywords":"","order":"","size":0}}"""


def build_arxiv_url(keywords: str, order: str = "", size: int = 50) -> str:
    """
    根据 LLM 返回的参数构建 arXiv 搜索 URL

    格式: https://arxiv.org/search/?searchtype=all&query={keywords}&abstracts=show&size={size}&order={order}
    参考: docs/reference.md

    注意: arXiv 网页搜索要求空格用 %20 编码（不是 +），所以用 quote 替代 urlencode
    """
    # 对 keywords 中的空格和特殊字符做 %20 编码，保持 AND/OR/NOT 等逻辑运算符
    encoded_query = quote(keywords, safe='":()')

    url = f"{ARXIV_SEARCH_BASE}?searchtype=all&query={encoded_query}&abstracts=show&size={size}"
    # order 为空字符串时表示相关性排序，不需要传 order 参数
    if order:
        url += f"&order={order}"

    return url


def smart_search(query: str, use_llm: bool = True) -> dict:
    """
    核心接口：用户自然语言 → arXiv 搜索 URL

    参数:
        query:    用户自然语言查询，如 "Transformer优化的最新进展"
        use_llm:  是否调用 LLM，False 则使用 mock 规则

    返回:
        {
            "url":      "https://arxiv.org/search/?searchtype=all&query=...&abstracts=show&size=50&order=...",
            "keywords": "Transformer AND optimization",   # LLM 构建的查询语句
            "order":    "-announced_date_first",          # 排序方式
            "size":     50,                                # 结果数量
            "intent":   "追踪Transformer优化最新进展"       # 意图描述
        }
    """
    if not use_llm:
        return _mock_search(query)

    # 调用 LLM 生成搜索参数
    llm_result = chat_json(
        user_message=build_llm_prompt(query),
        system_message="arXiv搜索参数生成器。只输出JSON。",
        temperature=0.3,
        max_tokens=4096,
    )

    # 从 LLM 返回值中提取参数，提供默认值兜底
    keywords = llm_result.get("keywords", "")
    order = llm_result.get("order", "")
    size = llm_result.get("size", 50)
    intent = llm_result.get("intent", "")

    # size 校验：arXiv 网页搜索只接受 25 或 50，其他值会返回 400
    if not isinstance(size, int) or size not in (25, 50):
        size = 25 if size < 40 else 50

    # 构建 arXiv URL
    url = build_arxiv_url(keywords, order, size)

    return {
        "url": url,
        "keywords": keywords,
        "order": order,
        "size": size,
        "intent": intent,
    }


def _mock_search(query: str) -> dict:
    """Mock 模式：不调用 LLM，用简单规则生成搜索参数，用于开发调试"""
    query_lower = query.lower()

    if any(w in query_lower for w in ["最新", "最近", "newest", "latest", "recent"]):
        keywords = "all:transformer AND all:optimization"
        order = "-announced_date_first"
        size = 50
        intent = "追踪最新动态"
    elif any(w in query_lower for w in ["学习", "入门", "learn", "beginner"]):
        keywords = "transformer attention mechanism"
        order = ""
        size = 25
        intent = "入门学习"
    else:
        keywords = f"all:{query.split()[0] if query.split() else 'machine learning'}"
        order = ""
        size = 25
        intent = "通用搜索"

    return {
        "url": build_arxiv_url(keywords, order, size),
        "keywords": keywords,
        "order": order,
        "size": size,
        "intent": intent,
    }


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    test_queries = [
        "Transformer 优化的最新研究进展",
        "我是初学者，想系统学习 Attention Mechanism",
        "帮我梳理一下 GPT 系列模型的发展历程",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"查询: {query}")
        result = smart_search(query)
        print(f"意图:   {result['intent']}")
        print(f"关键词: {result['keywords']}")
        print(f"排序:   {ORDER_MAP.get(result['order'], result['order'])}")
        print(f"数量:   {result['size']}")
        print(f"URL:    {result['url']}")
