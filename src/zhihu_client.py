"""
zhihu_client.py — 知乎搜索 API 客户端

封装知乎开发者搜索 API (zhihu_search)，根据关键词搜索知乎内容
API 文档: https://developer.zhihu.com/docs?key=authorization

数据流:
    keywords → GET /api/v1/content/zhihu_search → 摘要 + 元数据列表

对外接口:
    zhihu_search(query, limit) → list[dict]
    zhihu_search_top(query, top_n) → list[dict]  (按赞排序精选)
"""

import sys
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from src.config import Config, ZhihuConfig

logger = logging.getLogger(__name__)


# ─── API 请求规范 ───────────────────────────────────────────
#
# 接口: GET /api/v1/content/zhihu_search
#
# 认证 (Header):
#   Authorization:      Bearer <access_secret>
#   X-Request-Timestamp: 秒级 Unix 时间戳
#   Content-Type:        application/json
#
# 请求参数 (Query String):
#   Query:  String, 必填, 搜索关键词
#   Count:  Int32,  选填, 返回数量, 默认 10, 最大 10
#           - Count <= 0 → 服务端回退为 10
#           - Count > 10 → 服务端自动截断为 10
#
# ─── API 响应规范 ───────────────────────────────────────────
#
# 响应结构:
#   {
#       "Code":    Int32,   0=成功
#       "Message": String,  状态描述
#       "Data": {
#           "HasMore":      Bool,   当前实现固定返回 false
#           "SearchHashId": String, 搜索请求标识
#           "EmptyReason":  String, 无结果原因 (非必返)
#           "Items": [ Item, ... ]  搜索结果列表
#       }
#   }
#
# Item 字段:
#   Title:           String,  内容标题
#   ContentType:     String,  内容类型 (Article / Answer / ...)
#   ContentID:       String,  内容标识
#   ContentText:     String,  内容摘要
#   Url:             String,  内容链接 (带 utm 溯源参数)
#   CommentCount:    Int32,   评论数
#   VoteUpCount:     Int32,   赞同数
#   AuthorName:      String,  作者昵称
#   AuthorAvatar:    String,  作者头像 URL
#   AuthorBadge:     String,  作者认证图标
#   AuthorBadgeText: String,  作者认证文案
#   EditTime:        Int32,   发布/更新时间戳
#   CommentInfoList: Array,   精选评论 (非必返)
#   AuthorityLevel:  String,  权威等级
#   RankingScore:    Float32, 排序分数
#
# CommentInfo 字段:
#   Content:         String,  评论内容
#
# ────────────────────────────────────────────────────────────


def _build_headers() -> dict:
    """构建知乎 API 请求头 (Bearer 鉴权 + 时间戳)"""
    return {
        "Authorization": f"Bearer {ZhihuConfig.ACCESS_KEY}",
        "X-Request-Timestamp": str(int(time.time())),
        "Content-Type": "application/json",
        "User-Agent": "KnowledgeHub/1.0",
    }


def _parse_response(data: dict) -> list[dict]:
    """
    解析知乎搜索 API 响应，提取关键字段为标准化结构

    原始路径: data["Data"]["Items"] → list[Item]
    标准化映射: Item.PascalCase → result.snake_case

    参数:
        data: API 返回的原始 JSON dict

    返回:
        标准化结果列表，每条:
        {
            "title":           Item.Title,
            "excerpt":         Item.ContentText,
            "url":             Item.Url,
            "voteup_count":    Item.VoteUpCount,
            "comment_count":   Item.CommentCount,
            "author_name":     Item.AuthorName,
            "authority_level": Item.AuthorityLevel,
            "ranking_score":   Item.RankingScore,
        }
    """
    items = data.get("Data", {}).get("Items", [])

    results = []
    for item in items:
        results.append({
            "title": item.get("Title", ""),
            "excerpt": item.get("ContentText", ""),
            "url": item.get("Url", ""),
            "voteup_count": item.get("VoteUpCount", 0),
            "comment_count": item.get("CommentCount", 0),
            "author_name": item.get("AuthorName", ""),
            "authority_level": item.get("AuthorityLevel", ""),
            "ranking_score": item.get("RankingScore", 0),
        })

    return results


def zhihu_search(
    query: str,
    limit: int = None,
    max_retries: int = 3,
) -> list[dict]:
    """
    知乎关键词搜索

    参数:
        query:       搜索关键词, 如 "Transformer优化"
        limit:       返回数量, 默认 Config.ZHIHU_MAX_ANSWERS, API 侧最大 10
        max_retries: 请求失败最大重试次数

    返回:
        标准化搜索结果列表 (见 _parse_response 返回值)

    异常:
        ValueError:       ACCESS_KEY 未设置 / 认证失败 (401)
        ConnectionError:  重试耗尽仍无法连接
    """
    if not ZhihuConfig.ACCESS_KEY:
        raise ValueError(
            "ZHIHU_ACCESS_KEY 未设置！\n"
            "请在 .env 中添加: ZHIHU_ACCESS_KEY=your_key"
        )

    if not query.strip():
        raise ValueError("搜索关键词不能为空")

    _limit = limit or Config.ZHIHU_MAX_ANSWERS

    url = ZhihuConfig.BASE_URL
    headers = _build_headers()
    params = {
        "Query": query,
        "Count": min(_limit, 10),
    }

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            results = _parse_response(data)

            logger.info(
                f"[Zhihu] query='{query}' "
                f"results={len(results)}/{_limit} "
                f"status={response.status_code}"
            )

            return results

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "N/A"

            if status_code == 401:
                raise ValueError(
                    f"知乎 API 认证失败 (HTTP {status_code})\n"
                    f"请检查 ZHIHU_ACCESS_KEY 是否正确"
                ) from e

            if status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limit hit, retry {attempt}/{max_retries} in {wait}s")
                last_error = e
                time.sleep(wait)
                continue

            logger.error(f"HTTP error (no retry): {e}")
            raise

        except requests.exceptions.ConnectionError as e:
            wait = 2 ** attempt
            logger.warning(f"Connection error, retry {attempt}/{max_retries} in {wait}s: {e}")
            last_error = e
            time.sleep(wait)

        except requests.exceptions.Timeout as e:
            wait = 2 ** attempt
            logger.warning(f"Timeout, retry {attempt}/{max_retries} in {wait}s: {e}")
            last_error = e
            time.sleep(wait)

        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw response: {response.text[:500]}")
            raise ValueError(f"知乎 API 返回了非 JSON 响应: {response.text[:200]}") from e

    raise ConnectionError(f"知乎 API 请求失败，重试 {max_retries} 次后仍无法连接: {last_error}")


def zhihu_search_top(query: str, top_n: int = 5) -> list[dict]:
    """
    搜索知乎并返回 Top N 高赞结果

    按 voteup_count 降序排列，用于报告生成时的精选推荐

    参数:
        query:  搜索关键词
        top_n:  返回前 N 条高赞结果

    返回:
        按赞同数降序排序的结果列表
    """
    results = zhihu_search(query, limit=10)
    results.sort(key=lambda x: x.get("voteup_count", 0), reverse=True)
    return results[:top_n]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print(f"Zhihu BASE_URL:   {ZhihuConfig.BASE_URL}")
    print(f"Zhihu ACCESS_KEY: {'✅ 已设置' if ZhihuConfig.ACCESS_KEY else '❌ 未设置'}")
    print(f"ZHIHU_MAX_ANSWERS: {Config.ZHIHU_MAX_ANSWERS}")
    print()

    try:
        results = zhihu_search("Transformer优化", limit=5)
        print(f"搜索到 {len(results)} 条结果:\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r['voteup_count']}赞] {r['title']}")
            print(f"   摘要: {r['excerpt'][:80]}...")
            print(f"   链接: {r['url']}")
            print()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
