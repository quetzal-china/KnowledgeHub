"""
main.py — KnowledgeHub 统一调度入口

完整流程:
    用户查询 → LLM 分析意图 → arXiv + 知乎并行搜索 → 数据可视化 → LLM 综合分析 → Markdown 报告 → PDF 导出

用法:
    python main.py "Transformer优化的最新进展"
    python main.py "RAG评测方法" --no-arxiv
    python main.py "深度学习入门" --no-zhihu
    python main.py "快速测试" --mock
    python main.py "RAG评测" --no-pdf
"""

import sys
import json
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.smart_search import smart_search
from src.zhihu_client import zhihu_search
from src.report_generator import generate_report
from src.visualizer import generate_charts
from src.pdf_exporter import export_pdf

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"
SCRAPY_PROJECT_DIR = Path(__file__).parent / "knowledge_hub"


def run_arxiv_search(url: str) -> list[dict]:
    """
    运行 arXiv 爬虫，返回论文数据列表

    通过 subprocess 调用 Scrapy，cwd 指向 scrapy.cfg 所在目录
    """
    output_file = OUTPUT_DIR / "arxiv_data.json"

    if output_file.exists():
        output_file.unlink()

    cmd = [
        sys.executable, "-m", "scrapy", "crawl", "arxiv",
        "-a", f"url={url}",
        "-o", str(output_file),
    ]

    logger.info(f"[arXiv] 启动 Scrapy 爬虫: {url}")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(SCRAPY_PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            logger.error(f"[arXiv] Scrapy 错误: {result.stderr[-500:]}")
            return []

        if not output_file.exists():
            logger.warning("[arXiv] 未生成输出文件")
            return []

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"[arXiv] 爬取完成: {len(data)} 条论文")
        return data

    except subprocess.TimeoutExpired:
        logger.error("[arXiv] Scrapy 超时 (180s)")
        return []
    except Exception as e:
        logger.error(f"[arXiv] 执行失败: {e}")
        return []


def run_zhihu_search(query: str, count: int = 10) -> list[dict]:
    """运行知乎搜索，返回结果列表"""
    logger.info(f"[知乎] 搜索: {query}")

    try:
        results = zhihu_search(query, limit=count)
        logger.info(f"[知乎] 搜索完成: {len(results)} 条结果")
        return results
    except Exception as e:
        logger.error(f"[知乎] 搜索失败: {e}")
        return []


def _save_json(data, filename: str) -> Path:
    """保存 JSON 数据到 output 目录"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    filepath = OUTPUT_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def run(
    query: str,
    use_arxiv: bool = True,
    use_zhihu: bool = True,
    use_llm: bool = True,
    export_pdf_flag: bool = True,
) -> str:
    """
    核心调度: 用户查询 → 搜索 → 可视化 → 报告 → PDF

    参数:
        query:           用户自然语言查询
        use_arxiv:       是否搜索 arXiv
        use_zhihu:       是否搜索知乎
        use_llm:         是否使用 LLM 生成搜索参数 (False 则用 mock)
        export_pdf_flag: 是否导出 PDF

    返回:
        Markdown 报告字符串
    """
    logger.info(f"{'='*60}")
    logger.info(f"用户查询: {query}")
    logger.info(f"数据源: arXiv={'✅' if use_arxiv else '❌'} 知乎={'✅' if use_zhihu else '❌'}")
    logger.info(f"{'='*60}")

    # Step 1: LLM 智能分析
    logger.info("\n--- Step 1: LLM 智能分析 ---")
    search_params = smart_search(query, use_llm=use_llm)
    logger.info(f"意图: {search_params['intent']}")
    if use_arxiv:
        logger.info(f"arXiv: {search_params['arxiv']['keywords']} | size={search_params['arxiv']['size']} | order={search_params['arxiv'].get('order', '')}")
    if use_zhihu:
        logger.info(f"知乎: {search_params['zhihu']['query']} | count={search_params['zhihu']['count']}")

    # Step 2: 并行搜索
    logger.info("\n--- Step 2: 数据采集 ---")
    arxiv_data = []
    zhihu_data = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}

        if use_arxiv:
            futures[executor.submit(run_arxiv_search, search_params["arxiv"]["url"])] = "arxiv"
        if use_zhihu:
            futures[executor.submit(
                run_zhihu_search,
                search_params["zhihu"]["query"],
                search_params["zhihu"]["count"],
            )] = "zhihu"

        for future in as_completed(futures):
            source = futures[future]
            try:
                result = future.result()
                if source == "arxiv":
                    arxiv_data = result
                else:
                    zhihu_data = result
            except Exception as e:
                logger.error(f"[{source}] 执行异常: {e}")

    # Step 3: 保存原始数据
    if arxiv_data:
        filepath = _save_json(arxiv_data, "arxiv_data.json")
        logger.info(f"[arXiv] 数据已保存: {filepath}")

    if zhihu_data:
        filepath = _save_json(zhihu_data, "zhihu_data.json")
        logger.info(f"[知乎] 数据已保存: {filepath}")

    # Step 4: 确定报告名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = query[:20].replace(" ", "_")
    report_name = f"report_{safe_query}_{timestamp}"

    # Step 5: 数据可视化（保存到报告专属目录）
    logger.info("\n--- Step 5: 数据可视化 ---")
    charts_dir = OUTPUT_DIR / "charts" / report_name
    charts = generate_charts(arxiv_data, zhihu_data, charts_dir)
    if charts:
        for name, path in charts.items():
            logger.info(f"  {name}: {path}")

    # Step 6: 生成报告
    logger.info("\n--- Step 6: LLM 综合分析 ---")
    report = generate_report(query, arxiv_data, zhihu_data, charts=charts)

    report_file = OUTPUT_DIR / f"{report_name}.md"

    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"[报告] 已保存: {report_file}")

    # Step 7: PDF 导出
    if export_pdf_flag:
        logger.info("\n--- Step 7: PDF 导出 ---")
        try:
            pdf_path = report_file.with_suffix(".pdf")
            export_pdf(report, pdf_path, charts_dir=charts_dir)
            logger.info(f"[PDF] 已保存: {pdf_path}")
        except Exception as e:
            logger.warning(f"[PDF] 导出失败（不影响报告）: {e}")

    return report


def main():
    parser = argparse.ArgumentParser(description="KnowledgeHub — 多源技术调研工具")
    parser.add_argument("query", help="搜索查询，如 'Transformer优化的最新进展'")
    parser.add_argument("--no-arxiv", action="store_true", help="跳过 arXiv 搜索")
    parser.add_argument("--no-zhihu", action="store_true", help="跳过知乎搜索")
    parser.add_argument("--mock", action="store_true", help="使用 mock 模式（不调用 LLM 生成搜索参数）")
    parser.add_argument("--no-pdf", action="store_true", help="跳过 PDF 导出")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s")

    Config.validate()

    report = run(
        query=args.query,
        use_arxiv=not args.no_arxiv,
        use_zhihu=not args.no_zhihu,
        use_llm=not args.mock,
        export_pdf_flag=not args.no_pdf,
    )

    print(f"\n{'='*60}")
    print(report[:500])
    if len(report) > 500:
        print(f"\n... (共 {len(report)} 字符，完整报告见 output/ 目录)")


if __name__ == "__main__":
    main()
