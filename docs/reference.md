arxiv.org目前提供的curl搜索format
```curl
# Announcement date (oldest first)
https://arxiv.org/search/?searchtype=all&query=transformer&abstracts=show&size=50&order=announced_date_first
# Announcement date (newest first)
https://arxiv.org/search/?searchtype=all&query=transformer&abstracts=show&size=50&order=-announced_date_first
# Relevance
https://arxiv.org/search/?searchtype=all&query=transformer&abstracts=show&size=50&order=
```
可见,格式为:
https://arxiv.org/search/?searchtype=all&query={key_words}&abstracts=show&size=50&order={order}

对应关系
- `时间顺序` -> `announced_date_first`
- `时间倒序` -> `-announced_date_first`
- `相关性` -> ` `(空)
