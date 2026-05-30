"""
app.py — KnowledgeHub Web 服务

基于 FastAPI + Jinja2 的 Web 界面，提供：
- 首页搜索
- 报告浏览
- 图表展示
- PDF 下载

用法 (conda 环境):
    conda run -n knowledge-hub uvicorn src.web.app:app --reload --port 8000
"""

import sys
import json
import logging
import re
import zipfile
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.config import Config
from src.smart_search import smart_search
from src.zhihu_client import zhihu_search
from src.report_generator import generate_report
from src.visualizer import generate_charts
from src.pdf_exporter import export_pdf

logger = logging.getLogger(__name__)

app = FastAPI(title="KnowledgeHub", version="1.0.0")

BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"
CHARTS_DIR = OUTPUT_DIR / "charts"

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "src" / "web" / "static")), name="static")
app.mount("/charts", StaticFiles(directory=str(CHARTS_DIR)), name="charts")

from jinja2 import Environment, FileSystemLoader

_jinja_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "src" / "web" / "templates")),
    cache_size=0,
    autoescape=True,
)
templates = Jinja2Templates(env=_jinja_env)


# ─── 工具函数 ───────────────────────────────────────────────


def _list_reports() -> list[dict]:
    """列出所有报告文件（Markdown + PDF）"""
    reports = []
    if not OUTPUT_DIR.exists():
        return reports

    md_files = sorted(OUTPUT_DIR.glob("report_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    for md in md_files:
        pdf = md.with_suffix(".pdf")
        reports.append({
            "name": md.stem,
            "md_path": str(md),
            "pdf_path": str(pdf) if pdf.exists() else None,
            "mtime": datetime.fromtimestamp(md.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return reports


def _list_charts() -> list[dict]:
    """列出所有图表文件"""
    charts = []
    if not CHARTS_DIR.exists():
        return charts

    for f in sorted(CHARTS_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True):
        charts.append({
            "name": f.stem,
            "path": f"/charts/{f.name}",
            "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return charts


# ─── 页面路由 ───────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页 — 搜索入口 + 历史报告列表"""
    reports = _list_reports()
    charts = _list_charts()
    return templates.TemplateResponse(request, "index.html", {
        "reports": reports,
        "charts": charts,
    })


@app.get("/report/{report_name}", response_class=HTMLResponse)
async def view_report(request: Request, report_name: str):
    """查看报告详情（Markdown 渲染为 HTML）"""
    md_file = OUTPUT_DIR / f"{report_name}.md"
    if not md_file.exists():
        return templates.TemplateResponse(request, "error.html", {
            "message": f"报告不存在: {report_name}",
        })

    import markdown
    md_text = md_file.read_text(encoding="utf-8")
    html_content = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

    def _replace_img_src(match):
        alt = match.group(1)
        src = match.group(2)
        if not src.startswith(("http://", "https://", "/")):
            src = f"/charts/{src}"
        return f'<img alt="{alt}" src="{src}"'

    html_content = re.sub(
        r'<img alt="([^"]*)" src="([^"]*)"',
        _replace_img_src,
        html_content,
    )

    return templates.TemplateResponse(request, "report.html", {
        "title": report_name,
        "content": html_content,
        "report_name": report_name,
    })


@app.get("/charts", response_class=HTMLResponse)
async def view_charts(request: Request):
    """图表库页面"""
    charts = _list_charts()
    return templates.TemplateResponse(request, "charts.html", {
        "charts": charts,
    })


# ─── API 路由 ───────────────────────────────────────────────


@app.post("/api/search")
async def api_search(
    query: str = Form(...),
    use_arxiv: bool = Form(True),
    use_zhihu: bool = Form(True),
    use_llm: bool = Form(True),
):
    """
    执行搜索并生成报告

    表单参数:
        query:      搜索关键词
        use_arxiv:  是否搜索 arXiv
        use_zhihu:  是否搜索知乎
        use_llm:    是否使用 LLM 生成搜索参数
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import subprocess

    logger.info(f"[Web] 搜索: {query}")

    # Step 1: LLM 分析
    search_params = smart_search(query, use_llm=use_llm)

    # Step 2: 并行搜索
    arxiv_data = []
    zhihu_data = []

    def run_arxiv(url: str) -> list:
        output_file = OUTPUT_DIR / "arxiv_data.json"
        if output_file.exists():
            output_file.unlink()
        scrapy_dir = BASE_DIR / "knowledge_hub"
        cmd = [
            sys.executable, "-m", "scrapy", "crawl", "arxiv",
            "-a", f"url={url}",
            "-o", str(output_file),
        ]
        try:
            result = subprocess.run(cmd, cwd=str(scrapy_dir), capture_output=True, text=True, timeout=180)
            if result.returncode == 0 and output_file.exists():
                with open(output_file) as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"[Web] arXiv 失败: {e}")
        return []

    def run_zhihu(q: str, count: int) -> list:
        try:
            return zhihu_search(q, limit=count)
        except Exception as e:
            logger.error(f"[Web] 知乎失败: {e}")
        return []

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}
        if use_arxiv:
            futures[executor.submit(run_arxiv, search_params["arxiv"]["url"])] = "arxiv"
        if use_zhihu:
            futures[executor.submit(run_zhihu, search_params["zhihu"]["query"], search_params["zhihu"]["count"])] = "zhihu"

        for future in as_completed(futures):
            source = futures[future]
            try:
                result = future.result()
                if source == "arxiv":
                    arxiv_data = result
                else:
                    zhihu_data = result
            except Exception as e:
                logger.error(f"[{source}] 异常: {e}")

    # Step 3: 可视化
    charts = generate_charts(arxiv_data, zhihu_data, CHARTS_DIR)

    # Step 4: 生成报告
    report = generate_report(query, arxiv_data, zhihu_data, charts=charts)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = query[:20].replace(" ", "_")
    report_file = OUTPUT_DIR / f"report_{safe_query}_{timestamp}.md"
    report_file.write_text(report, encoding="utf-8")

    # Step 5: PDF
    pdf_path = report_file.with_suffix(".pdf")
    try:
        export_pdf(report, pdf_path, charts_dir=CHARTS_DIR)
    except Exception as e:
        logger.warning(f"[Web] PDF 导出失败: {e}")

    return {
        "success": True,
        "query": query,
        "arxiv_count": len(arxiv_data),
        "zhihu_count": len(zhihu_data),
        "report_name": report_file.stem,
        "pdf_ready": pdf_path.exists(),
    }


@app.get("/api/reports")
async def api_reports():
    """获取报告列表 JSON"""
    return {"reports": _list_reports()}


@app.get("/api/download/{report_name}")
async def download_pdf(report_name: str):
    """下载 PDF 报告"""
    pdf_file = OUTPUT_DIR / f"{report_name}.pdf"
    if not pdf_file.exists():
        return {"error": "PDF 不存在"}
    return FileResponse(str(pdf_file), media_type="application/pdf", filename=f"{report_name}.pdf")


@app.get("/api/download/md/{report_name}")
async def download_md(report_name: str):
    """下载 Markdown 报告"""
    md_file = OUTPUT_DIR / f"{report_name}.md"
    if not md_file.exists():
        return {"error": "Markdown 不存在"}
    return FileResponse(str(md_file), media_type="text/markdown", filename=f"{report_name}.md")


@app.get("/api/download/zip/{report_name}")
async def download_zip(report_name: str):
    """下载 ZIP 报告（Markdown + 图片）"""
    md_file = OUTPUT_DIR / f"{report_name}.md"
    if not md_file.exists():
        return {"error": "报告不存在"}

    md_text = md_file.read_text(encoding="utf-8")
    images = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", md_text)

    tmp_dir = tempfile.mkdtemp()
    zip_path = Path(tmp_dir) / f"{report_name}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        md_in_zip = re.sub(
            r"!\[([^\]]*)\]\(([^)]+)\)",
            lambda m: f'![{m.group(1)}](img/{m.group(2)})',
            md_text,
        )
        zf.writestr(f"{report_name}/{report_name}.md", md_in_zip.encode("utf-8"))

        for _, img_name in images:
            img_path = CHARTS_DIR / img_name
            if img_path.exists():
                zf.write(str(img_path), f"{report_name}/img/{img_name}")

    def cleanup():
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename=f"{report_name}.zip",
        background=cleanup,
    )
