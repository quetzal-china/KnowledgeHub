"""
items.py — Scrapy 数据结构定义

当前仅定义 ArxivItem，知乎数据通过 API 直接获取，不经过 Scrapy
"""

import scrapy


class ArxivItem(scrapy.Item):
    """arXiv 论文数据结构"""
    title = scrapy.Field()
    authors = scrapy.Field()
    abstract = scrapy.Field()
    categories = scrapy.Field()
    submitted_date = scrapy.Field()
    paper_url = scrapy.Field()
    pdf_url = scrapy.Field()
