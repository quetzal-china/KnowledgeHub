"""
智能搜索参数生成器

功能：根据用户的模糊描述，结合搜索策略知识库，让 LLM 生成最优的搜索参数
"""

import json


def build_llm_prompt(user_query: str) -> str:
    """
    构建 LLM 的 Prompt，包含用户需求和搜索策略知识库
    
    参数:
        user_query: 用户的模糊查询（中文或英文）
    
    返回:
        完整的 Prompt 字符串
    """

    from search_strategy import ARXIV_SEARCH_STRATEGY

    prompt = f"""你是一个学术搜索引擎的智能参数优化器。请根据用户的需求，选择最合适的 arXiv 搜索参数。

## 用户需求
{user_query}

## 搜索策略知识库
{ARXIV_SEARCH_STRATEGY}

## 你的任务
1. 分析用户的真实意图（学习/追踪/调研/找作者等）
2. 提取 3-5 个精准的搜索关键词
3. 选择最合适的排序方式（relevance/submittedDate）
4. 确定合适的排序方向和结果数量
5. 构建最优的 search_query

## 输出格式（严格 JSON）
```json
{{
  "intent": "用户意图分析（一句话）",
  "keywords": ["关键词1", "关键词2", ...],
  "search_query": "构建的查询语句",
  "sortBy": "relevance 或 submittedDate 或 lastUpdatedDate",
  "sortOrder": "ascending 或 descending",
  "max_results": 数字（10-100之间）,
  "reasoning": "为什么这样选择的理由"
}}
```

请只输出 JSON，不要其他内容。
"""

    return prompt


def generate_search_params(user_query: str, llm_client=None) -> dict:
    """
    调用 LLM 生成搜索参数
    
    参数:
        user_query: 用户输入
        llm_client: LLM 客户端对象（如 DeepSeek）
    
    返回:
        包含搜索参数的字典
    """
    
    # 1. 构建 Prompt
    prompt = build_llm_prompt(user_query)
    print("📝 已构建 Prompt（前200字符）:")
    print(prompt[:200] + "...\n")

    # 2. 调用 LLM（这里先模拟，实际需要接入真实的 LLM）
    if llm_client is None:
        print("⚠️  未提供 LLM 客户端，使用模拟数据")
        return get_mock_params(user_query)

    # TODO: 实际调用 LLM 的代码
    # response = llm_client.chat(prompt)
    # params = json.loads(response)
    # return params


def get_mock_params(user_query: str) -> dict:
    """
    模拟 LLM 的输出（用于测试）
    
    在实际项目中，这个函数会被真正的 LLM 调用替代
    """
    
    query_lower = user_query.lower()

    if any(word in query_lower for word in ['最新', '最近', '新进展', 'newest', 'latest', 'recent']):
        return {
            "intent": "追踪最新研究动态",
            "keywords": ["transformer", "optimization", "efficiency"],
            "search_query": "all:transformer AND all:optimization",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": 30,
            "reasoning": "用户要求'最新'，使用 submittedDate 降序排列获取最新论文"
        }

    elif any(word in query_lower for word in ['学习', '入门', '了解', 'learn', 'introduction', 'beginner']):
        return {
            "intent": "入门学习某个主题",
            "keywords": ["transformer", "architecture", "attention mechanism"],
            "search_query": "(ti:transformer OR abs:transformer) AND (cat:cs.LG OR cat:cs.CL)",
            "sortBy": "relevance",
            "sortOrder": "descending",
            "max_results": 20,
            "reasoning": "用户是初学者，优先显示相关性高的经典论文"
        }

    elif any(word in query_lower for word in ['综述', '发展', '历史', 'survey', 'history', 'review']):
        return {
            "intent": "文献综述/历史回顾",
            "keywords": ["transformer", "evolution", "development"],
            "search_query": "all:transformer",
            "sortBy": "submittedDate",
            "sortOrder": "ascending",
            "max_results": 50,
            "reasoning": "用户想看发展脉络，按时间升序排列"
        }

    else:
        return {
            "intent": "通用搜索",
            "keywords": [word for word in query_lower.split() if len(word) > 2][:3],
            "search_query": f"all:{query_lower.split()[0] if query_lower.split() else 'machine learning'}",
            "sortBy": "relevance",
            "sortOrder": "descending",
            "max_results": 25,
            "reasoning": "默认使用相关性排序，平衡质量和时效性"
        }


def apply_search_params_to_spider(params: dict):
    """
    将生成的参数应用到爬虫
    
    参数:
        params: LLM 生成的搜索参数字典
    
    返回:
        配置好参数的 URL
    """
    
    base_url = "https://arxiv.org/search/"
    
    query = params.get('search_query', '')
    sort_by = params.get('sortBy', 'relevance')
    sort_order = params.get('sortOrder', 'descending')
    
    url = f"{base_url}?query={query}&searchtype=all&order={sort_by}"
    
    print(f"\n🔗 生成的搜索 URL:")
    print(url)
    print(f"\n📊 搜索配置:")
    print(f"  - 关键词: {params.get('keywords')}")
    print(f"  - 排序方式: {sort_by}")
    print(f"  - 排序方向: {sort_order}")
    print(f"  - 结果数量: {params.get('max_results')}")
    print(f"  - 选择理由: {params.get('reasoning')}")
    
    return url


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 智能搜索参数生成器 - 测试")
    print("=" * 60)

    test_queries = [
        "Transformer 优化的最新研究进展",
        "我是初学者，想系统学习 Attention Mechanism",
        "帮我梳理一下 GPT 系列模型的发展历程",
        "李飞飞在计算机视觉领域的重要工作"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"📌 测试 {i}: {query}")
        print('='*60)

        params = generate_search_params(query)
        apply_search_params_to_spider(params)

    print("\n✅ 测试完成！")
