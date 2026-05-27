import sys
import time
import json
import logging
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from src.config import Config

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        Config.validate()
        llm = Config.get_llm_config()
        _client = OpenAI(
            api_key=llm.API_KEY,
            base_url=llm.BASE_URL,
        )
    return _client


def chat(
    user_message: str,
    system_message: str = None,
    temperature: float = None,
    max_tokens: int = None,
    max_retries: int = 3,
) -> dict:
    client = get_client()
    llm = Config.get_llm_config()

    full_system = llm.SYSTEM_PROMPT
    if system_message:
        full_system = f"{llm.SYSTEM_PROMPT}\n{system_message}"

    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": user_message},
    ]

    _temperature = temperature if temperature is not None else Config.LLM_TEMPERATURE
    _max_tokens = max_tokens if max_tokens is not None else Config.LLM_MAX_TOKENS

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            completion = client.chat.completions.create(
                model=llm.MODEL,
                messages=messages,
                temperature=_temperature,
                max_completion_tokens=_max_tokens,
            )

            content = completion.choices[0].message.content
            usage = completion.usage

            result = {
                "content": content,
                "model": completion.model,
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "reasoning_tokens": 0,
            }

            if usage and hasattr(usage, "completion_tokens_details") and usage.completion_tokens_details:
                result["reasoning_tokens"] = usage.completion_tokens_details.reasoning_tokens or 0

            output_tokens = result["completion_tokens"] - result["reasoning_tokens"]
            logger.info(
                f"[{llm.MODEL}] prompt={result['prompt_tokens']} "
                f"reasoning={result['reasoning_tokens']} "
                f"output={output_tokens} "
                f"total={result['completion_tokens']}"
            )

            return result

        except RateLimitError as e:
            wait = 2 ** attempt
            logger.warning(f"Rate limit hit, retry {attempt}/{max_retries} in {wait}s: {e}")
            last_error = e
            time.sleep(wait)

        except APIConnectionError as e:
            wait = 2 ** attempt
            logger.warning(f"Connection error, retry {attempt}/{max_retries} in {wait}s: {e}")
            last_error = e
            time.sleep(wait)

        except APIError as e:
            logger.error(f"API error (no retry): {e}")
            raise

    raise ConnectionError(f"Failed after {max_retries} retries: {last_error}")


def chat_text(
    user_message: str,
    system_message: str = None,
    temperature: float = None,
    max_tokens: int = None,
) -> str:
    result = chat(
        user_message=user_message,
        system_message=system_message,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return result["content"]


def chat_json(
    user_message: str,
    system_message: str = None,
    temperature: float = None,
    max_tokens: int = None,
) -> dict:
    result = chat(
        user_message=user_message,
        system_message=system_message,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = result["content"].strip()

    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    brace_start = content.find("{")
    brace_end = content.rfind("}")
    if brace_start != -1 and brace_end != -1:
        content = content[brace_start:brace_end + 1]

    return json.loads(content)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    llm = Config.get_llm_config()
    print(f"Provider: {Config.LLM_PROVIDER}")
    print(f"Model:    {llm.MODEL}")
    print(f"Base URL: {llm.BASE_URL}")
    print()

    result = chat("请用一句话介绍你自己")
    print(f"回复: {result['content']}")
    print(f"Token: prompt={result['prompt_tokens']} reasoning={result['reasoning_tokens']} output={result['completion_tokens'] - result['reasoning_tokens']}")
