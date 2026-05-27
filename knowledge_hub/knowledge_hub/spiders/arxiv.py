"""
arxiv.py — arXiv 论文爬虫

使用方式:
    # 通过 smart_search 生成 URL 后传给爬虫
    scrapy crawl arxiv -a url="https://arxiv.org/search/?searchtype=all&query=..."

    # 不传 url 则使用默认查询
    scrapy crawl arxiv
"""

import scrapy
import re
from knowledge_hub.items import ArxivItem


class ArxivSpider(scrapy.Spider):
    name = "arxiv"
    allowed_domains = ["arxiv.org"]

    # 默认搜索 URL，可通过 -a url=xxx 覆盖
    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, url=None, *args, **kwargs):
        """
        初始化爬虫

        参数:
            url: arXiv 搜索页 URL，由 smart_search() 生成
                 格式: https://arxiv.org/search/?searchtype=all&query=...&abstracts=show&size=50&order=...
        """
        super().__init__(*args, **kwargs)

        if url:
            self.start_urls = [url]
            self.logger.info(f"使用 LLM 生成的 URL: {url}")
        else:
            # 默认 URL，用于直接 scrapy crawl arxiv 的场景
            self.start_urls = [
                "https://arxiv.org/search/?searchtype=all&query=transformer+optimization&abstracts=show&size=50&order="
            ]
            self.logger.info("使用默认 URL（未指定 -a url 参数）")

    def parse(self, response):
        # 找到页面上所有的论文条目（每个论文都在一个 <li> 标签里）
        papers = response.xpath('//li[contains(@class, "arxiv-result")]')
        self.logger.info(f"本页找到 {len(papers)} 篇论文")

        # 遍历每一篇论文
        for paper in papers:
            # 创建一个数据容器，用来存储这篇论文的信息
            item = ArxivItem()

            # 1. 提取标题
            # 标题在 <p class="title is-5 mathjax"> 标签里面
            title_text = paper.xpath('.//p[@class="title is-5 mathjax"]//text()').get('')
            item['title'] = title_text.strip()

            # 2. 提取作者列表
            # 作者在 <p class="authors"> 里的多个 <a> 标签中
            authors_raw = paper.xpath('.//p[@class="authors"]/a/text()').getall()
            authors_list = []
            for author in authors_raw:
                author_clean = author.strip()
                if author_clean:
                    authors_list.append(author_clean)
            item['authors'] = authors_list

            # 3. 提取摘要
            # arXiv 的摘要有两种显示方式：完整版（abstract-full）和简短版（abstract-short）
            abstract_full = paper.xpath('.//span[contains(@class, "abstract-full")]/text()').get('')
            abstract_short = paper.xpath('.//span[contains(@class, "abstract-short")]/text()').get('')

            # 优先使用完整摘要，如果没有就用简短的
            if abstract_full:
                abstract = abstract_full.strip()
            else:
                abstract = abstract_short.strip()

            # 去掉末尾的"▽ Less"文字
            if abstract.endswith('▽ Less'):
                abstract = abstract[:-6].strip()

            item['abstract'] = abstract

            # 4. 提取分类标签（如 cs.AI, cs.LG）
            # 分类在 <div class="tags"> 里面
            categories_a = paper.xpath('.//div[contains(@class, "tags")]//a/text()').getall()
            categories_span = paper.xpath('.//div[contains(@class, "tags")]//span/text()').getall()

            categories_list = []
            # 先尝试从 <a> 标签获取分类
            for cat in categories_a:
                cat_clean = cat.strip()
                if cat_clean:
                    categories_list.append(cat_clean)

            # 如果 <a> 标签没有内容，就从 <span> 标签获取
            if len(categories_list) == 0:
                for cat in categories_span:
                    cat_clean = cat.strip()
                    if cat_clean:
                        categories_list.append(cat_clean)

            item['categories'] = categories_list

            # 5. 提取提交日期
            # 提交日期在 <p class="is-size-7"> 里，格式是 "Submitted 26 May, 2026"
            submitted_text = paper.xpath('string(./p[@class="is-size-7"])').get('')

            # 用正则表达式提取日期部分
            date_pattern = r'Submitted\s+(\d+\s+\w+,\s+\d{4})'
            match = re.search(date_pattern, submitted_text)

            if match:
                item['submitted_date'] = match.group(1)
            else:
                item['submitted_date'] = None

            # 6. 提取论文详情链接
            # 论文链接在标题的 <a> 标签中
            paper_link = paper.xpath('./div/p[@class="list-title is-inline-block"]/a/@href').get('')
            if paper_link:
                item['paper_url'] = response.urljoin(paper_link)
            else:
                item['paper_url'] = ''

            # 7. 提取 PDF 下载链接
            # PDF 链接在包含 "pdf" 文字的 <a> 标签中
            pdf_link = paper.xpath('.//a[contains(text(), "pdf")]/@href').get('')
            if pdf_link:
                item['pdf_url'] = response.urljoin(pdf_link)
            else:
                item['pdf_url'] = ''

            # 返回这条数据（yield 会把数据传给 pipeline 处理）
            yield item

        # 翻页：如果还有下一页则继续爬取
        next_page = response.xpath('//a[contains(@class, "pagination-next")]/@href').get()
        if next_page:
            self.logger.info(f"发现下一页: {next_page}")
            yield response.follow(next_page, callback=self.parse)
