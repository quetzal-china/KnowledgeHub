# KnowledgeHub - AI 驱动的知识检索与整理系统

> 将模糊需求转化为精准知识，自动采集、分析、可视化多源学术内容。
> 作者:刘雨鑫(2025303313)
---
## 项目简介

KnowledgeHub 是一个基于 AI 的知识检索系统，能够：

- 将用户的模糊描述转化为精准搜索关键词
- 从 arXiv、知乎等多源平台自动采集学术内容
- 利用 LLM 进行内容总结和质量评估
- 生成结构化 Markdown 文档，支持导入 Obsidian

## 技术栈

- 采集层: Scrapy + XPath (arXiv), Scrapy + API (知乎)
- 搜索层: TinyFish Search API (免费)
- 处理层: DeepSeek API (关键词提取、内容总结)
- 分析层: Pandas (数据处理), Matplotlib (可视化)
- 前端: Streamlit (简单 Web 界面)
- 输出: Markdown, JSON
  
---
## 快速开始

### 环境准备

创建虚拟环境与安装依赖

```bash
conda create -n knowledge-hub python=3.11
conda activate knowledge-hub
pip install -r requirements.txt
```

### 配置 API Key

编辑 .env 文件，填入你的 API Key(请在 DeepSeek、Mimo、TinyFish 等平台注册获取)

```bash
cp .env.example .env
```

### 运行

```bash
python main.py "Transformer 优化"
Web 界面
streamlit run src/app.py
```

### 开发流程

1. 需求分析 → docs/requirements.md
2. 架构设计 → docs/architecture.md
3. 模块开发 → 每次只开发一个模块，测试通过再继续
4. 版本控制 → 每个功能一个 Git 分支
5. 代码审查 → Pull Request + Code Review
   
---
## 许可证

MIT License
