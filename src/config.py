"""
config.py — 全局配置管理

加载 .env 环境变量，为各模块提供统一配置入口

配置分组:
    MiMoConfig     — 小米 MiMo LLM 配置
    DeepSeekConfig — DeepSeek LLM 配置
    ZhihuConfig    — 知乎开发者 API 配置
    Config         — 通用配置 + LLM Provider 路由
"""

import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)


class MiMoConfig:
    API_KEY = os.getenv("MIMO_API_KEY")
    BASE_URL = os.getenv("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
    MODEL = os.getenv("MIMO_MODEL", "mimo-v2.5-pro")
    SYSTEM_PROMPT = (
        f"You are MiMo, an AI assistant developed by Xiaomi. "
        f"Today is date: {datetime.now().strftime('%A, %B %d, %Y')}. "
        f"Your knowledge cutoff date is December 2024."
    )


class DeepSeekConfig:
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    SYSTEM_PROMPT = "You are a helpful assistant"


class ZhihuConfig:
    BASE_URL = os.getenv(
        "ZHIHU_BASE_URL",
        "https://developer.zhihu.com/api/v1/content/zhihu_search",
    )
    ACCESS_KEY = os.getenv("ZHIHU_ACCESS_KEY")


PROVIDERS = {
    "mimo": MiMoConfig,
    "deepseek": DeepSeekConfig,
}


class Config:
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mimo")

    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.5"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))

    ARXIV_MAX_PAGES = int(os.getenv("ARXIV_MAX_PAGES", "5"))
    ZHIHU_MAX_ANSWERS = int(os.getenv("ZHIHU_MAX_ANSWERS", "10"))

    @classmethod
    def get_llm_config(cls):
        """根据 LLM_PROVIDER 返回对应配置类"""
        provider = cls.LLM_PROVIDER.lower()
        if provider not in PROVIDERS:
            raise ValueError(
                f"未知的 LLM_PROVIDER: '{provider}'\n"
                f"可选值: {list(PROVIDERS.keys())}"
            )
        return PROVIDERS[provider]

    @classmethod
    def validate(cls):
        """校验当前 LLM Provider 的 API_KEY 是否已设置"""
        llm = cls.get_llm_config()
        if not llm.API_KEY:
            raise ValueError(
                f"当前 provider '{cls.LLM_PROVIDER}' 的 API_KEY 未设置！\n"
                f"请在 .env 中添加对应的 Key"
            )
