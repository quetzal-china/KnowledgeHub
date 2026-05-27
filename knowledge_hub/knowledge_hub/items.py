# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ArxivItem(scrapy.Item):
    """arXiv 论文数据结构"""
    title = scrapy.Field()          # 标题
    authors = scrapy.Field()        # 作者列表
    abstract = scrapy.Field()       # 摘要
    categories = scrapy.Field()     # 分类（如 cs.AI, cs.LG）
    submitted_date = scrapy.Field() # 提交时间
    paper_url = scrapy.Field()      # 论文链接
    pdf_url = scrapy.Field()        # PDF 链接


class ZhihuItem(scrapy.Item):
    """知乎回答数据结构"""
    question_title = scrapy.Field() # 问题标题
    answer_content = scrapy.Field() # 回答内容
    author = scrapy.Field()         # 作者
    voteup_count = scrapy.Field()   # 点赞数
    comment_count = scrapy.Field()  # 评论数
    created_time = scrapy.Field()   # 创建时间
    answer_url = scrapy.Field()     # 回答链接
