ARXIV_SEARCH_STRATEGY = """
# arXiv 搜索参数指南

## 一、排序策略选择

### 1. sortBy（排序依据）
- **relevance**: 按相关性排序
  - 适用场景：用户想找最相关、最重要的论文
  - 示例："我想了解 Transformer 的核心原理"
  - 特点：优先显示引用多、匹配度高的经典论文

- **submittedDate**: 按提交日期排序
  - 适用场景：用户想看最新研究进展
  - 示例："最近有什么关于 LLM 的新论文？"
  - 特点：优先显示最新提交的论文

- **lastUpdatedDate**: 按最后更新日期排序
  - 适用场景：用户关注论文的最新版本
  - 示例："这篇论文有新版了吗？"
  - 特点：包含修订和更正的版本

### 2. sortOrder（排序方向）
- **ascending**: 升序（从旧到新）
  - 适用场景：历史回顾、发展脉络梳理
  - 示例："Transformer 从诞生到现在的发展历程"

- **descending**: 降序（从新到旧）【默认推荐】
  - 适用场景：追踪最新动态、前沿研究
  - 示例："最新的优化方法有哪些"

## 二、搜索字段选择

### 字段限定符说明
- ti: 标题搜索（精确匹配标题中的关键词）
- au: 作者搜索（查找特定作者的论文）
- abs: 摘要搜索（在摘要中查找关键词）
- cat: 分类搜索（限定学科分类，如 cs.AI, cs.LG, stat.ML）
- all: 全字段搜索（在所有字段中查找）

### 分类代码参考
计算机科学类：
- cs.AI: 人工智能
- cs.LG: 机器学习
- cv.CV: 计算机视觉
- cs.CL: 计算语言学/NLP
- cs.CR: 密码学与安全
- cs.DS: 数据结构
- cs.DB: 数据库
- cs.DC: 分布式计算
- cs.NI: 网络与互联网架构
- cs.SE: 软件工程

数学类：
- math.AG: 代数几何
- stat.ML: 机器学习（统计角度）

## 三、典型使用场景与推荐参数

### 场景1：入门学习某个主题
用户意图："我是初学者，想系统学习 XXX"
推荐参数：
- sortBy: relevance（先学经典的、重要的）
- sortOrder: descending（新的在前，但相关性优先）
- search_query: all:关键词 OR ti:关键词
- max_results: 20（适中数量）

示例：
```
query = "all:transformer AND (cat:cs.LG OR cat:cs.CL)"
sortBy = "relevance"
sortOrder = "descending"
max_results = 20
```

### 场景2：追踪最新研究动态
用户意图："最近有什么新进展？"
推荐参数：
- sortBy: submittedDate（最新提交的）
- sortOrder: descending（最新的在前）
- search_query: all:关键词
- max_results: 30（多看一些）

示例：
```
query = "all:LLM optimization"
sortBy = "submittedDate"
sortOrder = "descending"
max_results = 30
```

### 场景3：找特定作者的工作
用户意图："XXX 作者在这个领域做了什么工作？"
推荐参数：
- sortBy: submittedDate（看时间线）
- sortOrder: descending
- search_query: au:"作者名" AND all:领域关键词
- max_results: 50（作者可能有很多论文）

示例：
```
query = 'au:"Hinton, G" AND all:deep learning'
sortBy = "submittedDate"
sortOrder = "descending"
max_results = 50
```

### 场景4：跨领域交叉研究
用户意图："XXX 技术在 YYY 领域的应用"
推荐参数：
- sortBy: relevance（找最相关的应用）
- sortOrder: descending
- search_query: (ti:技术 OR abs:技术) AND (cat:领域1 OR cat:领域2)
- max_results: 25

示例：
```
query = "(ti:transformer OR abs:transformer) AND (cat:cs.CV OR cat:cs.MED)"
sortBy = "relevance"
sortOrder = "descending"
max_results = 25
```

### 场景5：文献综述/历史回顾
用户意图："帮我梳理 XXX 领域的发展脉络"
推荐参数：
- sortBy: submittedDate（按时间线排列）
- sortOrder: ascending（从旧到新，看清发展脉络）
- search_query: all:核心概念
- max_results: 100（需要较多文献）

示例：
```
query = "all:attention mechanism"
sortBy = "submittedDate"
sortOrder = "ascending"
max_results = 100
```

## 四、参数组合规则

### 规则1：相关性 vs 时效性权衡
- 学习基础知识 → relevance 优先
- 追踪前沿动态 → submittedDate 优先
- 综合了解 → relevance + 较大的 max_results

### 规则2：查询复杂度控制
- 关键词简单（1-2个词）→ 用 all: 字段
- 关键词具体 → 用 ti: 或 abs:
- 多条件组合 → 用 AND/OR 逻辑

### 规则3：结果数量建议
- 快速浏览：10-15 篇
- 深入学习：20-30 篇
- 文献综述：50-100 篇
- 全面调研：100+ 篇（需分页获取）

## 五、高级技巧

### 技巧1：排除不相关内容
使用 NOT 操作符：
```
query = "all:transformer NOT cat:physics"  # 排除物理类别
```

### 技巧2：短语搜索
使用引号精确匹配：
```
query = 'ti:"large language model"'  # 标题必须包含完整短语
```

### 技巧3：通配符
部分 API 支持 * 通配符（需测试）：
```
query = "ti:optim*"  # 匹配 optimize, optimization, optimizer 等
```

### 技巧4：组合多个分类
```
query = "cat:(cs.AI OR cs.LG OR stat.ML)"  # 在多个分类中搜索
"""
