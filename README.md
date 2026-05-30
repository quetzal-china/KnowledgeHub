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

- 采集层: Scrapy + XPath (arXiv), 知乎开发者 API (知乎)
- 搜索层: LLM 智能分析 (MiMo / DeepSeek)
- 分析层: LLM 综合摘要 + 交叉分析
- 可视化: matplotlib + numpy (图表生成)
- 前端: FastAPI + Jinja2 + 现代 CSS (Web 界面)
- 输出: Markdown, JSON, PDF

---
## 快速开始

### 1. 环境准备

**方式 A：使用 conda（推荐）**

```bash
conda create -n knowledge-hub python=3.11 -y
conda activate knowledge-hub
```

**方式 B：使用 venv（无需 conda）**

```bash
python3.11 -m venv venv
source venv/bin/activate    # Linux/macOS
# 或 venv\Scripts\activate   # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

> **注意（Linux 用户）**：PDF 导出功能依赖 `weasyprint`，需要先安装系统级依赖：
> ```bash
> sudo apt-get install libpango1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
> ```
> 如果不需要 PDF 导出，可跳过此步，使用 `--no-pdf` 参数运行。

### 3. 配置 API Key

编辑 `.env` 文件，填入你的 API Key（请在 DeepSeek、Mimo 等平台注册获取）

```bash
cp .env.example .env
# 用文本编辑器打开 .env 填入你的 API Key
```

### 4. 运行

**命令行模式：**

```bash
# 完整流程（arXiv + 知乎 + 可视化 + PDF）
python main.py "Transformer 优化"

# 只搜索知乎
python main.py "Transformer优化" --no-arxiv

# 只搜索 arXiv
python main.py "Transformer优化" --no-zhihu

# Mock 模式（不调用 LLM，用于测试）
python main.py "快速测试" --mock

# 不导出 PDF（跳过 weasyprint）
python main.py "Transformer 优化" --no-pdf
```

**Web 界面：**

```bash
python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000
```

访问 http://localhost:8000 即可使用 Web 界面进行搜索、查看报告和图表。

### 5. 运行测试

```bash
pytest tests/ -v
```

---

## 项目结构

```
KnowledgeHub/
├── main.py                      # CLI 入口
├── src/                         # 核心模块
│   ├── config.py                # 配置管理
│   ├── llm_client.py            # LLM 客户端
│   ├── smart_search.py          # 智能搜索参数生成
│   ├── zhihu_client.py          # 知乎 API 封装
│   ├── report_generator.py      # 报告生成器
│   ├── visualizer.py            # 数据可视化
│   ├── pdf_exporter.py          # PDF 导出
│   └── web/
│       ├── app.py               # FastAPI 应用
│       ├── static/css/          # 样式文件
│       └── templates/           # HTML 模板
├── knowledge_hub/               # Scrapy 爬虫项目
│   └── spiders/arxiv.py         # arXiv 爬虫
├── tests/                       # 单元测试
├── docs/                        # 设计文档
├── .env.example                 # 环境变量模板
├── requirements.txt             # Python 依赖
├── report.md                    # 课程实验报告
└── README.md
```

## 许可证

MIT License
