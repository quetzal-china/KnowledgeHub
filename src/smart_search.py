"""
smart_search.py — 智能搜索模块

流程: 用户自然语言 → LLM 生成双数据源搜索参数 → arXiv URL + 知乎 keywords

对外接口:
    smart_search(query) → dict
    返回: {
        "intent": "...",
        "arxiv": {"url": "...", "keywords": "...", "size": 50, "order": "..."},
        "zhihu": {"query": "...", "count": 10},
    }
"""

from urllib.parse import quote
from src.llm_client import chat_json
from src.search_strategy import COMBINED_SEARCH_STRATEGY

ARXIV_SEARCH_BASE = "https://arxiv.org/search/"


def build_llm_prompt(user_query: str) -> str:
    """构建 LLM prompt，要求输出双数据源搜索参数 JSON"""
    return f"""根据用户需求同时生成arXiv和知乎的搜索参数。

用户: {user_query}

搜索策略:
{COMBINED_SEARCH_STRATEGY}

输出JSON:
{{"intent":"","arxiv":{{"keywords":"","url":"","size":0,"order":""}},"zhihu":{{"query":"","count":0}}}}"""


def build_arxiv_url(keywords: str, order: str = "", size: int = 50) -> str:
    """
    根据 LLM 返回的参数构建 arXiv 搜索 URL

    格式: https://arxiv.org/search/?searchtype=all&query={keywords}&abstracts=show&size={size}&order={order}

    注意: arXiv 网页搜索要求空格用 %20 编码（不是 +），所以用 quote 替代 urlencode
    """
    encoded_query = quote(keywords, safe='":()')

    url = f"{ARXIV_SEARCH_BASE}?searchtype=all&query={encoded_query}&abstracts=show&size={size}"
    if order:
        url += f"&order={order}"

    return url


def _validate_arxiv_url(url: str) -> str:
    """
    校验并修复 LLM 生成的 arXiv URL

    常见问题:
        - 空格编码为 + (arXiv 要求 %20)
        - size 参数不在 25/50 范围内
    """
    if "+" in url:
        url = url.replace("+", "%20")

    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    size_values = params.get("size", [])
    if size_values:
        try:
            size = int(size_values[0])
            if size not in (25, 50):
                new_size = "25" if size < 40 else "50"
                url = url.replace(f"size={size_values[0]}", f"size={new_size}")
        except ValueError:
            url = url.replace(f"size={size_values[0]}", "size=25")

    return url


def smart_search(query: str, use_llm: bool = True) -> dict:
    """
    核心接口：用户自然语言 → 双数据源搜索参数

    参数:
        query:    用户自然语言查询，如 "Transformer优化的最新进展"
        use_llm:  是否调用 LLM，False 则使用 mock 规则

    返回:
        {
            "intent": "追踪Transformer优化最新进展",
            "arxiv": {
                "url": "https://arxiv.org/search/?searchtype=all&query=...",
                "keywords": "Transformer AND optimization",
                "size": 50,
                "order": "-announced_date_first",
            },
            "zhihu": {
                "query": "Transformer优化 LLM加速 推理加速",
                "count": 10,
            },
        }
    """
    if not use_llm:
        return _mock_search(query)

    llm_result = chat_json(
        user_message=build_llm_prompt(query),
        system_message="搜索参数生成器。只输出JSON，不要其他内容。",
        temperature=0.3,
        max_tokens=4096,
    )

    intent = llm_result.get("intent", "")

    # ─── arXiv 参数提取与校验 ───
    arxiv_raw = llm_result.get("arxiv", {})
    arxiv_keywords = arxiv_raw.get("keywords", "")
    arxiv_url = arxiv_raw.get("url", "")
    arxiv_size = arxiv_raw.get("size", 50)
    arxiv_order = arxiv_raw.get("order", "")

    if not isinstance(arxiv_size, int) or arxiv_size not in (25, 50):
        arxiv_size = 25 if arxiv_size < 40 else 50

    if arxiv_url:
        arxiv_url = _validate_arxiv_url(arxiv_url)
    else:
        arxiv_url = build_arxiv_url(arxiv_keywords, arxiv_order, arxiv_size)

    # ─── 知乎参数提取与校验 ───
    zhihu_raw = llm_result.get("zhihu", {})
    zhihu_query = zhihu_raw.get("query", "")
    zhihu_count = zhihu_raw.get("count", 10)

    if not isinstance(zhihu_count, int) or zhihu_count < 1:
        zhihu_count = 10
    zhihu_count = min(zhihu_count, 10)

    return {
        "intent": intent,
        "arxiv": {
            "url": arxiv_url,
            "keywords": arxiv_keywords,
            "size": arxiv_size,
            "order": arxiv_order,
        },
        "zhihu": {
            "query": zhihu_query,
            "count": zhihu_count,
        },
    }


def _mock_search(query: str) -> dict:
    """Mock 模式：不调用 LLM，用简单规则生成搜索参数，用于开发调试"""
    query_lower = query.lower()

    if any(w in query_lower for w in ["最新", "最近", "newest", "latest", "recent"]):
        arxiv_keywords = "Transformer optimization"
        arxiv_size = 50
        arxiv_order = "-announced_date_first"
        zhihu_query = "Transformer优化 LLM加速 推理加速"
        intent = "追踪最新动态"
    elif any(w in query_lower for w in ["学习", "入门", "learn", "beginner"]):
        arxiv_keywords = "Transformer attention mechanism"
        arxiv_size = 25
        arxiv_order = ""
        zhihu_query = "深度学习入门 新手建议 学习路线"
        intent = "入门学习"
    else:
        first_word = query.split()[0] if query.split() else "machine learning"
        arxiv_keywords = first_word
        arxiv_size = 25
        arxiv_order = ""
        zhihu_query = query
        intent = "通用搜索"

    return {
        "intent": intent,
        "arxiv": {
            "url": build_arxiv_url(arxiv_keywords, arxiv_order, arxiv_size),
            "keywords": arxiv_keywords,
            "size": arxiv_size,
            "order": arxiv_order,
        },
        "zhihu": {
            "query": zhihu_query,
            "count": 10,
        },
    }


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    test_queries = [
        "Transformer 优化的最新研究进展",
        "我是初学者，想系统学习 Attention Mechanism",
        "帮我梳理一下 GPT 系列模型的发展历程",
    ]

    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"查询: {q}")
        result = smart_search(q)
        print(f"意图:     {result['intent']}")
        print(f"arXiv:    {result['arxiv']['keywords']} | size={result['arxiv']['size']} | order={result['arxiv']['order']}")
        print(f"          URL: {result['arxiv']['url']}")
        print(f"知乎:     {result['zhihu']['query']} | count={result['zhihu']['count']}")
