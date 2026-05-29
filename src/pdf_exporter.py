"""
pdf_exporter.py — PDF 导出模块

将 Markdown 报告转为带样式的 PDF 文件

转换链路:
    Markdown → HTML (markdown 库) → PDF (weasyprint)

对外接口:
    export_pdf(markdown_text, output_path, charts_dir) → str
    返回 PDF 文件绝对路径
"""

import logging
from pathlib import Path

import markdown
from weasyprint import HTML

logger = logging.getLogger(__name__)

PDF_CSS = """
@page {
    size: A4;
    margin: 2cm 2.5cm;
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-size: 9px;
        color: #999;
    }
}

body {
    font-family: "WenQuanYi Zen Hei", "WenQuanYi Micro Hei", "SimHei", "Noto Sans CJK SC",
                 "Microsoft YaHei", "DejaVu Sans", sans-serif;
    font-size: 11pt;
    line-height: 1.7;
    color: #333;
}

h1 {
    font-size: 20pt;
    color: #1a1a2e;
    border-bottom: 2px solid #16213e;
    padding-bottom: 6px;
    margin-top: 0;
}

h2 {
    font-size: 15pt;
    color: #16213e;
    border-bottom: 1px solid #ddd;
    padding-bottom: 4px;
    margin-top: 1.5em;
}

h3 {
    font-size: 12pt;
    color: #0f3460;
    margin-top: 1.2em;
}

a {
    color: #2196F3;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
    font-size: 10pt;
}

th, td {
    border: 1px solid #ddd;
    padding: 8px 12px;
    text-align: left;
}

th {
    background-color: #16213e;
    color: white;
    font-weight: bold;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

code {
    background-color: #f4f4f4;
    padding: 2px 5px;
    border-radius: 3px;
    font-size: 10pt;
}

pre {
    background-color: #f4f4f4;
    padding: 12px;
    border-radius: 5px;
    overflow-x: auto;
    font-size: 9pt;
}

blockquote {
    border-left: 4px solid #2196F3;
    margin: 1em 0;
    padding: 0.5em 1em;
    background-color: #f8f9fa;
    color: #555;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
    border: 1px solid #eee;
    border-radius: 4px;
}

hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 2em 0;
}

ul, ol {
    padding-left: 1.5em;
}

li {
    margin-bottom: 0.3em;
}
"""


def _md_to_html(md_text: str, charts_dir: str | Path | None = None) -> str:
    """
    Markdown 转 HTML，注入 CSS 样式

    参数:
        md_text:    Markdown 文本
        charts_dir: 图表目录路径，用于将相对路径图片转为绝对路径

    返回:
        完整 HTML 字符串
    """
    extensions = ["tables", "fenced_code", "toc"]
    html_body = markdown.markdown(md_text, extensions=extensions)

    if charts_dir:
        import re
        charts_path = Path(charts_dir).resolve()

        def _replace_img_src(match):
            alt = match.group(1)
            src = match.group(2)
            if not src.startswith(("http://", "https://", "file://")):
                abs_path = (charts_path / src).resolve()
                src = abs_path.as_uri()
            return f'<img alt="{alt}" src="{src}"'

        html_body = re.sub(
            r'<img alt="([^"]*)" src="([^"]*)"',
            _replace_img_src,
            html_body,
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>{PDF_CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""


def export_pdf(
    markdown_text: str,
    output_path: str | Path,
    charts_dir: str | Path | None = None,
) -> str:
    """
    将 Markdown 报告导出为 PDF

    参数:
        markdown_text: Markdown 格式的报告文本
        output_path:   PDF 输出路径
        charts_dir:    图表目录，用于解析图片相对路径

    返回:
        PDF 文件绝对路径
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(exist_ok=True)

    html_content = _md_to_html(markdown_text, charts_dir)

    try:
        HTML(string=html_content).write_pdf(str(output_path))
        logger.info(f"[PDF] 导出成功: {output_path}")
        return str(output_path)
    except Exception as e:
        logger.error(f"[PDF] 导出失败: {e}")
        raise


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    base = Path(__file__).parent.parent / "output"

    md_files = sorted(base.glob("report_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not md_files:
        print("未找到报告文件")
        sys.exit(1)

    latest = md_files[0]
    print(f"转换: {latest}")

    md_text = latest.read_text(encoding="utf-8")
    pdf_path = latest.with_suffix(".pdf")

    charts_dir = base / "charts"

    result = export_pdf(md_text, pdf_path, charts_dir)
    print(f"PDF 已生成: {result}")
