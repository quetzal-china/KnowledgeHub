import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "knowledge_hub"))

from unittest.mock import MagicMock

import pytest

from src.smart_search import _mock_search, build_arxiv_url, _validate_arxiv_url
from src.report_generator import _format_arxiv_section, _format_zhihu_section, _truncate_text
from src.visualizer import _parse_arxiv_date
from src.zhihu_client import _parse_response
from src.pdf_exporter import _md_to_html
from knowledge_hub.items import ArxivItem
from knowledge_hub.pipelines import KnowledgeHubPipeline


# ─── smart_search ────────────────────────────────────────────


class TestMockSearch:
    def test_latest_keyword(self):
        result = _mock_search("Transformer最新进展")
        assert result["intent"] == "追踪最新动态"
        assert result["arxiv"]["keywords"] == "Transformer optimization"
        assert result["arxiv"]["size"] == 50
        assert result["arxiv"]["order"] == "-announced_date_first"
        assert "arxiv.org/search/" in result["arxiv"]["url"]

    def test_recent_keyword(self):
        result = _mock_search("recent advances in NLP")
        assert result["intent"] == "追踪最新动态"
        assert result["arxiv"]["size"] == 50

    def test_learn_keyword(self):
        result = _mock_search("深度学习入门指南")
        assert result["intent"] == "入门学习"
        assert result["arxiv"]["keywords"] == "Transformer attention mechanism"
        assert result["arxiv"]["size"] == 25
        assert result["arxiv"]["order"] == ""

    def test_beginner_keyword(self):
        result = _mock_search("learn machine learning")
        assert result["intent"] == "入门学习"

    def test_default_fallback(self):
        result = _mock_search("GPT系列模型发展历程")
        assert result["intent"] == "通用搜索"
        assert result["arxiv"]["size"] == 25
        assert result["zhihu"]["count"] == 10

    def test_default_uses_first_word(self):
        result = _mock_search("quantum computing overview")
        assert result["arxiv"]["keywords"] == "quantum"

    def test_zhihu_always_present(self):
        result = _mock_search("anything")
        assert "query" in result["zhihu"]
        assert result["zhihu"]["count"] == 10

    def test_arxiv_url_is_built(self):
        result = _mock_search("最新")
        assert result["arxiv"]["url"].startswith("https://arxiv.org/search/")


class TestBuildArxivUrl:
    def test_basic_url(self):
        url = build_arxiv_url("Transformer")
        assert "searchtype=all" in url
        assert "query=Transformer" in url
        assert "size=50" in url
        assert "abstracts=show" in url

    def test_with_order(self):
        url = build_arxiv_url("NLP", order="-announced_date_first")
        assert "order=-announced_date_first" in url

    def test_without_order(self):
        url = build_arxiv_url("NLP")
        assert "order=" not in url

    def test_custom_size(self):
        url = build_arxiv_url("NLP", size=25)
        assert "size=25" in url

    def test_space_encoding(self):
        url = build_arxiv_url("deep learning")
        assert "%20" in url
        assert "+" not in url.split("query=")[1].split("&")[0]

    def test_special_chars_safe(self):
        url = build_arxiv_url('key:"value"')
        assert "key" in url


class TestValidateArxivUrl:
    def test_plus_to_percent20(self):
        url = "https://arxiv.org/search/?searchtype=all&query=deep+learning&size=50"
        result = _validate_arxiv_url(url)
        assert "+" not in result
        assert "%20" in result

    def test_fix_size_too_small(self):
        url = "https://arxiv.org/search/?searchtype=all&query=test&size=10"
        result = _validate_arxiv_url(url)
        assert "size=25" in result

    def test_fix_size_too_large(self):
        url = "https://arxiv.org/search/?searchtype=all&query=test&size=100"
        result = _validate_arxiv_url(url)
        assert "size=50" in result

    def test_valid_size_25(self):
        url = "https://arxiv.org/search/?searchtype=all&query=test&size=25"
        result = _validate_arxiv_url(url)
        assert "size=25" in result

    def test_valid_size_50(self):
        url = "https://arxiv.org/search/?searchtype=all&query=test&size=50"
        result = _validate_arxiv_url(url)
        assert "size=50" in result

    def test_non_numeric_size(self):
        url = "https://arxiv.org/search/?searchtype=all&query=test&size=abc"
        result = _validate_arxiv_url(url)
        assert "size=25" in result

    def test_no_size_param(self):
        url = "https://arxiv.org/search/?searchtype=all&query=test"
        result = _validate_arxiv_url(url)
        assert "size=" not in result


# ─── KnowledgeHubPipeline ────────────────────────────────────


class TestKnowledgeHubPipeline:
    def setup_method(self):
        self.pipeline = KnowledgeHubPipeline()
        self.spider = MagicMock()

    def _make_item(self, **kwargs):
        item = ArxivItem()
        for key, value in kwargs.items():
            item[key] = value
        return item

    def test_title_whitespace_normalization(self):
        item = self._make_item(title="  Hello   World  ")
        result = self.pipeline.process_item(item, self.spider)
        assert result["title"] == "Hello World"

    def test_title_non_string_converted(self):
        item = self._make_item(title=12345)
        result = self.pipeline.process_item(item, self.spider)
        assert result["title"] == "12345"

    def test_authors_list_cleaned(self):
        item = self._make_item(authors=["  Alice  ", "Bob", "", None, "  Charlie  "])
        result = self.pipeline.process_item(item, self.spider)
        assert result["authors"] == ["Alice", "Bob", "Charlie"]

    def test_authors_non_list_becomes_empty(self):
        item = self._make_item(authors="not a list")
        result = self.pipeline.process_item(item, self.spider)
        assert result["authors"] == []

    def test_authors_missing_becomes_empty(self):
        item = self._make_item(title="test")
        result = self.pipeline.process_item(item, self.spider)
        assert result["authors"] == []

    def test_abstract_truncated_over_500(self):
        long_text = "a" * 600
        item = self._make_item(abstract=long_text)
        result = self.pipeline.process_item(item, self.spider)
        assert len(result["abstract"]) == 500
        assert result["abstract"].endswith("...")

    def test_abstract_under_500(self):
        short_text = "a" * 300
        item = self._make_item(abstract=short_text)
        result = self.pipeline.process_item(item, self.spider)
        assert result["abstract"] == short_text

    def test_abstract_non_string_becomes_empty(self):
        item = self._make_item(abstract=42)
        result = self.pipeline.process_item(item, self.spider)
        assert result["abstract"] == ""

    def test_abstract_missing_becomes_empty(self):
        item = self._make_item(title="test")
        result = self.pipeline.process_item(item, self.spider)
        assert result["abstract"] == ""

    def test_categories_cleaned_and_deduped(self):
        item = self._make_item(categories=["cs.AI", " cs.AI ", "cs.LG", "invalid", "", None])
        result = self.pipeline.process_item(item, self.spider)
        assert set(result["categories"]) == {"cs.AI", "cs.LG"}

    def test_categories_non_list_becomes_empty(self):
        item = self._make_item(categories="cs.AI")
        result = self.pipeline.process_item(item, self.spider)
        assert result["categories"] == []

    def test_categories_missing_becomes_empty(self):
        item = self._make_item(title="test")
        result = self.pipeline.process_item(item, self.spider)
        assert result["categories"] == []

    def test_submitted_date_empty_becomes_none(self):
        item = self._make_item(submitted_date="  ")
        result = self.pipeline.process_item(item, self.spider)
        assert result["submitted_date"] is None

    def test_submitted_date_missing_becomes_none(self):
        item = self._make_item(title="test")
        result = self.pipeline.process_item(item, self.spider)
        assert result["submitted_date"] is None

    def test_paper_url_non_arxiv_cleared(self):
        item = self._make_item(paper_url="https://example.com/paper")
        result = self.pipeline.process_item(item, self.spider)
        assert result["paper_url"] == ""

    def test_paper_url_arxiv_kept(self):
        item = self._make_item(paper_url="https://arxiv.org/abs/2307.08691")
        result = self.pipeline.process_item(item, self.spider)
        assert result["paper_url"] == "https://arxiv.org/abs/2307.08691"

    def test_pdf_url_non_pdf_path_cleared(self):
        item = self._make_item(pdf_url="https://example.com/file.html")
        result = self.pipeline.process_item(item, self.spider)
        assert result["pdf_url"] == ""

    def test_pdf_url_valid_kept(self):
        item = self._make_item(pdf_url="https://arxiv.org/pdf/2307.08691")
        result = self.pipeline.process_item(item, self.spider)
        assert result["pdf_url"] == "https://arxiv.org/pdf/2307.08691"

    def test_paper_url_missing_becomes_empty(self):
        item = self._make_item(title="test")
        result = self.pipeline.process_item(item, self.spider)
        assert result["paper_url"] == ""

    def test_pdf_url_missing_becomes_empty(self):
        item = self._make_item(title="test")
        result = self.pipeline.process_item(item, self.spider)
        assert result["pdf_url"] == ""


# ─── report_generator ────────────────────────────────────────


class TestTruncateText:
    def test_short_text_unchanged(self):
        assert _truncate_text("hello", 10) == "hello"

    def test_exact_length_unchanged(self):
        text = "a" * 200
        assert _truncate_text(text, 200) == text

    def test_long_text_truncated(self):
        text = "a" * 300
        result = _truncate_text(text, 200)
        assert len(result) == 203
        assert result.endswith("...")

    def test_none_returns_none(self):
        assert _truncate_text(None, 10) is None

    def test_empty_string_returns_empty(self):
        assert _truncate_text("", 10) == ""


class TestFormatArxivSection:
    def test_empty_data(self):
        assert _format_arxiv_section([]) == "（无 arXiv 数据）"

    def test_single_paper(self):
        data = [{"title": "Test Paper", "abstract": "Short abstract", "paper_url": "https://arxiv.org/abs/1234", "authors": ["Alice"]}]
        result = _format_arxiv_section(data)
        assert "**Test Paper**" in result
        assert "Short abstract" in result
        assert "Alice" in result
        assert "https://arxiv.org/abs/1234" in result

    def test_authors_et_al(self):
        data = [{"title": "T", "abstract": "A", "authors": ["A", "B", "C", "D", "E"]}]
        result = _format_arxiv_section(data)
        assert "et al." in result

    def test_no_url_no_link_line(self):
        data = [{"title": "T", "abstract": "A", "authors": []}]
        result = _format_arxiv_section(data)
        assert "链接:" not in result

    def test_truncation_notice(self):
        data = [{"title": f"Paper {i}", "abstract": "A", "authors": []} for i in range(30)]
        result = _format_arxiv_section(data)
        assert "已截取前 25 条" in result


class TestFormatZhihuSection:
    def test_empty_data(self):
        assert _format_zhihu_section([]) == "（无知乎数据）"

    def test_single_item(self):
        data = [{"title": "知乎讨论", "excerpt": "摘要内容", "url": "https://zhuanlan.zhihu.com/p/1", "voteup_count": 100, "author_name": "张三", "comment_count": 5}]
        result = _format_zhihu_section(data)
        assert "**知乎讨论**" in result
        assert "摘要内容" in result
        assert "100赞" in result
        assert "5评论" in result
        assert "张三" in result

    def test_truncation_notice(self):
        data = [{"title": f"Item {i}", "excerpt": "E", "voteup_count": 0, "comment_count": 0, "author_name": "A"} for i in range(15)]
        result = _format_zhihu_section(data)
        assert "已截取前 10 条" in result

    def test_no_url_no_link_line(self):
        data = [{"title": "T", "excerpt": "E", "voteup_count": 0, "comment_count": 0, "author_name": "A"}]
        result = _format_zhihu_section(data)
        assert "链接:" not in result


# ─── visualizer ──────────────────────────────────────────────


class TestParseArxivDate:
    def test_valid_date(self):
        assert _parse_arxiv_date("5 May, 2026") == "2026-05"

    def test_valid_date_two_digit_day(self):
        assert _parse_arxiv_date("26 May, 2026") == "2026-05"

    def test_other_month(self):
        assert _parse_arxiv_date("15 January, 2025") == "2025-01"

    def test_empty_string(self):
        assert _parse_arxiv_date("") is None

    def test_none(self):
        assert _parse_arxiv_date(None) is None

    def test_invalid_format(self):
        assert _parse_arxiv_date("2026-05-01") is None

    def test_whitespace_stripped(self):
        assert _parse_arxiv_date("  5 May, 2026  ") == "2026-05"


# ─── zhihu_client ────────────────────────────────────────────


class TestParseResponse:
    def test_normal_response(self):
        data = {
            "Code": 0,
            "Data": {
                "Items": [
                    {
                        "Title": "测试标题",
                        "ContentText": "测试摘要",
                        "Url": "https://zhuanlan.zhihu.com/p/1",
                        "VoteUpCount": 100,
                        "CommentCount": 10,
                        "AuthorName": "作者",
                        "AuthorityLevel": "L1",
                        "RankingScore": 0.95,
                    }
                ]
            },
        }
        results = _parse_response(data)
        assert len(results) == 1
        assert results[0]["title"] == "测试标题"
        assert results[0]["excerpt"] == "测试摘要"
        assert results[0]["url"] == "https://zhuanlan.zhihu.com/p/1"
        assert results[0]["voteup_count"] == 100
        assert results[0]["comment_count"] == 10
        assert results[0]["author_name"] == "作者"
        assert results[0]["authority_level"] == "L1"
        assert results[0]["ranking_score"] == 0.95

    def test_empty_items(self):
        data = {"Code": 0, "Data": {"Items": []}}
        results = _parse_response(data)
        assert results == []

    def test_missing_data_key(self):
        data = {"Code": 0}
        results = _parse_response(data)
        assert results == []

    def test_missing_items_key(self):
        data = {"Code": 0, "Data": {}}
        results = _parse_response(data)
        assert results == []

    def test_missing_fields_use_defaults(self):
        data = {"Data": {"Items": [{}]}}
        results = _parse_response(data)
        assert len(results) == 1
        assert results[0]["title"] == ""
        assert results[0]["excerpt"] == ""
        assert results[0]["url"] == ""
        assert results[0]["voteup_count"] == 0
        assert results[0]["comment_count"] == 0
        assert results[0]["author_name"] == ""
        assert results[0]["authority_level"] == ""
        assert results[0]["ranking_score"] == 0

    def test_multiple_items(self):
        data = {"Data": {"Items": [{"Title": f"Item {i}"} for i in range(3)]}}
        results = _parse_response(data)
        assert len(results) == 3


# ─── pdf_exporter ────────────────────────────────────────────


class TestMdToHtml:
    def test_basic_markdown(self):
        html = _md_to_html("# Hello World")
        assert "<h1" in html
        assert "Hello World" in html

    def test_contains_css(self):
        html = _md_to_html("# Test")
        assert "<style>" in html
        assert "font-family" in html

    def test_html_structure(self):
        html = _md_to_html("**bold**")
        assert "<!DOCTYPE html>" in html
        assert '<html lang="zh-CN">' in html
        assert "<body>" in html

    def test_table_extension(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = _md_to_html(md)
        assert "<table>" in html

    def test_charts_dir_replaces_img_src(self, tmp_path):
        chart_file = tmp_path / "chart.png"
        chart_file.write_bytes(b"\x89PNG")
        md = "![chart](chart.png)"
        html = _md_to_html(md, charts_dir=str(tmp_path))
        assert "file://" in html

    def test_charts_dir_http_unchanged(self, tmp_path):
        md = "![img](https://example.com/img.png)"
        html = _md_to_html(md, charts_dir=str(tmp_path))
        assert "https://example.com/img.png" in html
        assert "file://" not in html

    def test_no_charts_dir(self):
        html = _md_to_html("![img](chart.png)")
        assert "chart.png" in html
