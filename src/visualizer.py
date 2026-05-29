"""
visualizer.py — 数据可视化模块

基于 numpy + matplotlib 对采集数据生成图表，供报告嵌入和 PDF 导出

图表类型:
    1. arXiv 论文分类分布图 (水平条形图)
    2. arXiv 论文时间趋势图 (按月折线图)
    3. 知乎互动排行图 (水平条形图, 赞同数+评论数)
    4. 双数据源概览图 (分类分布 + 互动排行并排)

对外接口:
    generate_charts(arxiv_data, zhihu_data, output_dir) → dict[str, str]
    返回 {图表名: 图片绝对路径} 的映射
"""

import logging
from pathlib import Path
from collections import Counter
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

logger = logging.getLogger(__name__)

plt.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei", "WenQuanYi Micro Hei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

CHART_DPI = 150
CHART_FORMAT = "png"
TOP_N_CATEGORIES = 10
TOP_N_ZHIHU = 10


def _ensure_font():
    """尝试设置中文字体，若不可用则回退"""
    available = {f.name for f in fm.fontManager.ttflist}
    for font in ["WenQuanYi Zen Hei", "WenQuanYi Micro Hei", "SimHei", "Noto Sans CJK SC", "Microsoft YaHei"]:
        if font in available:
            plt.rcParams["font.sans-serif"] = [font, "DejaVu Sans"]
            return
    logger.warning("[Visualizer] 未找到中文字体，图表中文可能显示为方块")


_ensure_font()


def _parse_arxiv_date(date_str: str) -> str | None:
    """
    解析 arXiv 日期字符串为 YYYY-MM 格式

    输入格式: "5 May, 2026" 或 "26 May, 2026"
    返回: "2026-05" 或 None
    """
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%d %B, %Y")
        return dt.strftime("%Y-%m")
    except ValueError:
        return None


def plot_arxiv_categories(arxiv_data: list[dict], output_path: Path) -> str | None:
    """
    arXiv 论文分类分布图 (水平条形图)

    统计论文的 cs.XX 分类出现频次，取 Top N 绘制

    参数:
        arxiv_data:  arXiv 搜索结果列表
        output_path: 图片保存路径

    返回:
        图片路径字符串，无数据时返回 None
    """
    if not arxiv_data:
        return None

    cat_counter = Counter()
    for paper in arxiv_data:
        for cat in paper.get("categories", []):
            cat_counter[cat] += 1

    if not cat_counter:
        return None

    top = cat_counter.most_common(TOP_N_CATEGORIES)
    labels = [c for c, _ in reversed(top)]
    values = [v for _, v in reversed(top)]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(labels, values, color=plt.cm.Blues(np.linspace(0.4, 0.85, len(labels))))

    ax.set_xlabel("论文数量")
    ax.set_title(f"arXiv 论文分类分布 (Top {TOP_N_CATEGORIES})")

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9)

    ax.set_xlim(0, max(values) * 1.15)
    plt.tight_layout()

    fig.savefig(output_path, dpi=CHART_DPI, format=CHART_FORMAT)
    plt.close(fig)

    logger.info(f"[Visualizer] arXiv 分类分布图: {output_path}")
    return str(output_path)


def plot_arxiv_timeline(arxiv_data: list[dict], output_path: Path) -> str | None:
    """
    arXiv 论文时间趋势图 (按月折线图)

    按 submitted_date 统计每月论文数量

    参数:
        arxiv_data:  arXiv 搜索结果列表
        output_path: 图片保存路径

    返回:
        图片路径字符串，无数据时返回 None
    """
    if not arxiv_data:
        return None

    month_counter = Counter()
    for paper in arxiv_data:
        month = _parse_arxiv_date(paper.get("submitted_date", ""))
        if month:
            month_counter[month] += 1

    if not month_counter:
        return None

    months = sorted(month_counter.keys())
    counts = [month_counter[m] for m in months]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(months, counts, marker="o", linewidth=2, color="#2196F3", markersize=6)
    ax.fill_between(months, counts, alpha=0.15, color="#2196F3")

    ax.set_xlabel("月份")
    ax.set_ylabel("论文数量")
    ax.set_title("arXiv 论文发布时间趋势")

    if len(months) > 6:
        plt.xticks(rotation=45, ha="right")
    else:
        plt.xticks(rotation=0)

    for i, (m, c) in enumerate(zip(months, counts)):
        ax.annotate(str(c), (m, c), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8)

    ax.set_ylim(0, max(counts) * 1.2)
    plt.tight_layout()

    fig.savefig(output_path, dpi=CHART_DPI, format=CHART_FORMAT)
    plt.close(fig)

    logger.info(f"[Visualizer] arXiv 时间趋势图: {output_path}")
    return str(output_path)


def plot_zhihu_ranking(zhihu_data: list[dict], output_path: Path) -> str | None:
    """
    知乎互动排行图 (水平条形图)

    按赞同数降序排列，同时显示评论数

    参数:
        zhihu_data:  知乎搜索结果列表
        output_path: 图片保存路径

    返回:
        图片路径字符串，无数据时返回 None
    """
    if not zhihu_data:
        return None

    sorted_data = sorted(zhihu_data, key=lambda x: x.get("voteup_count", 0), reverse=True)
    top = sorted_data[:TOP_N_ZHIHU]

    titles = []
    for item in reversed(top):
        t = item.get("title", "")[:20]
        if len(item.get("title", "")) > 20:
            t += "..."
        titles.append(t)

    votes = [item.get("voteup_count", 0) for item in reversed(top)]
    comments = [item.get("comment_count", 0) for item in reversed(top)]

    y = np.arange(len(titles))
    height = 0.35

    fig, ax = plt.subplots(figsize=(9, max(4, len(top) * 0.7)))
    bars1 = ax.barh(y - height / 2, votes, height, label="赞同数", color="#FF6B35")
    bars2 = ax.barh(y + height / 2, comments, height, label="评论数", color="#4ECDC4")

    ax.set_yticks(y)
    ax.set_yticklabels(titles, fontsize=9)
    ax.set_xlabel("数量")
    ax.set_title("知乎讨论互动排行")
    ax.legend(loc="lower right")

    for bar, val in zip(bars1, votes):
        if val > 0:
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", fontsize=8)

    ax.set_xlim(0, max(max(votes), max(comments)) * 1.2 if votes else 10)
    plt.tight_layout()

    fig.savefig(output_path, dpi=CHART_DPI, format=CHART_FORMAT)
    plt.close(fig)

    logger.info(f"[Visualizer] 知乎互动排行图: {output_path}")
    return str(output_path)


def plot_overview(
    arxiv_data: list[dict],
    zhihu_data: list[dict],
    output_path: Path,
) -> str | None:
    """
    双数据源概览图 (并排子图)

    左: arXiv 分类分布  右: 知乎互动排行

    参数:
        arxiv_data:  arXiv 搜索结果列表
        zhihu_data:  知乎搜索结果列表
        output_path: 图片保存路径

    返回:
        图片路径字符串，双源均无数据时返回 None
    """
    has_arxiv = bool(arxiv_data)
    has_zhihu = bool(zhihu_data)

    if not has_arxiv and not has_zhihu:
        return None

    if has_arxiv and not has_zhihu:
        return plot_arxiv_categories(arxiv_data, output_path)
    if has_zhihu and not has_arxiv:
        return plot_zhihu_ranking(zhihu_data, output_path)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    cat_counter = Counter()
    for paper in arxiv_data:
        for cat in paper.get("categories", []):
            cat_counter[cat] += 1

    if cat_counter:
        top = cat_counter.most_common(TOP_N_CATEGORIES)
        labels = [c for c, _ in reversed(top)]
        values = [v for _, v in reversed(top)]
        bars = ax1.barh(labels, values, color=plt.cm.Blues(np.linspace(0.4, 0.85, len(labels))))
        ax1.set_xlabel("论文数量")
        ax1.set_title(f"arXiv 分类分布 (Top {TOP_N_CATEGORIES})")
        for bar, val in zip(bars, values):
            ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                     str(val), va="center", fontsize=8)
        ax1.set_xlim(0, max(values) * 1.15)

    sorted_data = sorted(zhihu_data, key=lambda x: x.get("voteup_count", 0), reverse=True)
    top_zhihu = sorted_data[:TOP_N_ZHIHU]
    if top_zhihu:
        z_titles = []
        for item in reversed(top_zhihu):
            t = item.get("title", "")[:15]
            if len(item.get("title", "")) > 15:
                t += "..."
            z_titles.append(t)
        z_votes = [item.get("voteup_count", 0) for item in reversed(top_zhihu)]
        ax2.barh(z_titles, z_votes, color="#FF6B35")
        ax2.set_xlabel("赞同数")
        ax2.set_title("知乎互动排行")
        ax2.tick_params(axis="y", labelsize=8)

    fig.suptitle("数据源概览", fontsize=14, fontweight="bold")
    plt.tight_layout()

    fig.savefig(output_path, dpi=CHART_DPI, format=CHART_FORMAT)
    plt.close(fig)

    logger.info(f"[Visualizer] 双数据源概览图: {output_path}")
    return str(output_path)


def generate_charts(
    arxiv_data: list[dict],
    zhihu_data: list[dict],
    output_dir: str | Path,
) -> dict[str, str]:
    """
    生成所有图表

    参数:
        arxiv_data:  arXiv 搜索结果列表
        zhihu_data:  知乎搜索结果列表
        output_dir:  图片输出目录

    返回:
        图表名 → 图片绝对路径 的映射，如:
        {
            "arxiv_categories": "/path/to/arxiv_categories.png",
            "arxiv_timeline":   "/path/to/arxiv_timeline.png",
            "zhihu_ranking":    "/path/to/zhihu_ranking.png",
            "overview":         "/path/to/overview.png",
        }
    """
    out = Path(output_dir)
    out.mkdir(exist_ok=True)

    charts = {}

    path = plot_arxiv_categories(arxiv_data, out / "arxiv_categories.png")
    if path:
        charts["arxiv_categories"] = path

    path = plot_arxiv_timeline(arxiv_data, out / "arxiv_timeline.png")
    if path:
        charts["arxiv_timeline"] = path

    path = plot_zhihu_ranking(zhihu_data, out / "zhihu_ranking.png")
    if path:
        charts["zhihu_ranking"] = path

    path = plot_overview(arxiv_data, zhihu_data, out / "overview.png")
    if path:
        charts["overview"] = path

    logger.info(f"[Visualizer] 共生成 {len(charts)} 张图表")
    return charts


if __name__ == "__main__":
    import sys
    import json

    sys.path.insert(0, str(Path(__file__).parent.parent))
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    base = Path(__file__).parent.parent / "output"

    arxiv_path = base / "arxiv_data.json"
    zhihu_path = base / "zhihu_data.json"

    arxiv_data = []
    zhihu_data = []

    if arxiv_path.exists():
        with open(arxiv_path) as f:
            arxiv_data = json.load(f)
        print(f"加载 arXiv 数据: {len(arxiv_data)} 条")

    if zhihu_path.exists():
        with open(zhihu_path) as f:
            zhihu_data = json.load(f)
        print(f"加载知乎数据: {len(zhihu_data)} 条")

    charts = generate_charts(arxiv_data, zhihu_data, base / "charts")
    for name, path in charts.items():
        print(f"  {name}: {path}")
