"""
search_strategy.py — 搜索策略知识库

供 LLM 生成搜索参数时参考，需与 docs/reference.md 保持一致

策略分组:
    ARXIV_SEARCH_STRATEGY       — arXiv 网页搜索语法规则
    ZHIHU_SEARCH_STRATEGY       — 知乎开发者 API 搜索规则
    COMBINED_SEARCH_STRATEGY    — 双数据源合并策略，供 smart_search.py 使用
"""

ARXIV_SEARCH_STRATEGY = """
arXiv网页搜索URL: https://arxiv.org/search/?searchtype=all&query={keywords}&abstracts=show&size={size}&order={order}
query: 只支持简单关键词组合
  正确: "attention mechanism" AND transformer
  错误: ti:transformer  abs:optimization  cat:cs.CL  ← 这是API语法，网页搜索不支持
size: 入门→25，深入/综述→50
order: announced_date_first(时间正序) | -announced_date_first(时间倒序) | 空(相关性)
规则: 学基础→空(相关性)+25; 追最新→-announced_date_first+50; 看脉络→announced_date_first+50
"""

ZHIHU_SEARCH_STRATEGY = """
知乎搜索API: GET /api/v1/content/zhihu_search?Query={keywords}&Count={count}
Query: 中文关键词，空格分隔多个词，如 "Transformer优化 LLM加速 模型压缩"
Count: 返回数量，默认10，最大10
规则:
  - 用中文关键词，知乎是中文社区
  - 2-4个词组，不要过长句子
  - 侧重实践/工程/经验类关键词（知乎优势）
  - 学术术语保留英文，如 "Flash Attention" "RAG" "GPTQ"
示例:
  用户问"Transformer优化最新进展" → Query: "Transformer优化 LLM加速 推理加速"
  用户问"如何入门深度学习" → Query: "深度学习入门 新手建议 学习路线"
  用户问"RAG评测方法" → Query: "RAG 评测 RAGAS 检索增强"
"""

COMBINED_SEARCH_STRATEGY = f"""
你需要同时为两个数据源生成搜索参数。

--- arXiv (学术论文) ---
{ARXIV_SEARCH_STRATEGY.strip()}

--- 知乎 (中文社区) ---
{ZHIHU_SEARCH_STRATEGY.strip()}

--- 输出规则 ---
1. arXiv 用英文关键词，知乎用中文关键词
2. arXiv 侧重理论研究，知乎侧重工程实践
3. 两个数据源的关键词应互补而非重复
"""
