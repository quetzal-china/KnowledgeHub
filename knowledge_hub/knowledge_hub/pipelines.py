# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class KnowledgeHubPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # 清洗标题
        if adapter.get('title'):
            title = adapter['title']
            if isinstance(title, str):
                adapter['title'] = ' '.join(title.split())
            else:
                adapter['title'] = ' '.join(str(title).split()) if title else ''

        # 清洗作者列表
        if adapter.get('authors'):
            authors = adapter['authors']
            if isinstance(authors, list):
                cleaned_authors = []
                for author in authors:
                    if author and isinstance(author, str):
                        cleaned_author = ' '.join(author.split())
                        if cleaned_author:
                            cleaned_authors.append(cleaned_author)
                adapter['authors'] = cleaned_authors
            else:
                adapter['authors'] = []
        else:
            adapter['authors'] = []

        # 清洗摘要
        if adapter.get('abstract'):
            abstract = adapter['abstract']
            if isinstance(abstract, str):
                abstract = ' '.join(abstract.split())
                if len(abstract) > 500:
                    abstract = abstract[:497] + '...'
                adapter['abstract'] = abstract
            else:
                adapter['abstract'] = ''
        else:
            adapter['abstract'] = ''

        # 清洗分类标签
        if adapter.get('categories'):
            categories = adapter['categories']
            if isinstance(categories, list):
                cleaned_categories = []
                for cat in categories:
                    if cat and isinstance(cat, str):
                        cat_clean = cat.strip()
                        if cat_clean and '.' in cat_clean:
                            cleaned_categories.append(cat_clean)
                adapter['categories'] = list(set(cleaned_categories))
            else:
                adapter['categories'] = []
        else:
            adapter['categories'] = []

        # 处理日期
        if not adapter.get('submitted_date') or not adapter['submitted_date'].strip():
            adapter['submitted_date'] = None

        # PDF 链接验证
        if adapter.get('paper_url'):
            paper_url = adapter['paper_url']
            if paper_url and 'arxiv.org' not in str(paper_url):
                adapter['paper_url'] = ''
        else:
            adapter['paper_url'] = ''

        if adapter.get('pdf_url'):
            pdf_url = adapter['pdf_url']
            if pdf_url and '/pdf/' not in str(pdf_url):
                adapter['pdf_url'] = ''
        else:
            adapter['pdf_url'] = ''

        return item
