# arXiv 搜索策略知识库
# 供 LLM 生成搜索参数时参考，需与 docs/reference.md 保持一致
# 注意: 这是网页搜索，不是 API 搜索，query 只支持简单关键词 + AND/OR/NOT

ARXIV_SEARCH_STRATEGY = """
arXiv网页搜索URL: https://arxiv.org/search/?searchtype=all&query={keywords}&abstracts=show&size={size}&order={order}
query: 只支持简单关键词组合，用 AND OR NOT 连接，引号精确匹配
  正确: "attention mechanism" AND transformer
  错误: ti:transformer  abs:optimization  cat:cs.CL  ← 这是API语法，网页搜索不支持
size: 入门→25，深入/综述→50
order: announced_date_first(时间正序) | -announced_date_first(时间倒序) | 空(相关性)
规则: 学基础→空(相关性)+25; 追最新→-announced_date_first+50; 看脉络→announced_date_first+50
"""
