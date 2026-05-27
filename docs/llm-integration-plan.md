# LLM 接入（DeepSeek API）- 任务规划

---

## 📋 总体目标

将 `smart_search.py` 中的**模拟 LLM 输出**替换为 **DeepSeek API 真实调用**，实现智能搜索参数生成。

---

## 🎯 核心任务清单

### Phase 1: 环境准备与配置

#### 任务 1.1: 学习 DeepSeek API 文档

**你需要了解的内容：**

| 序号 | 学习主题 | 重要程度 | 说明 |
|------|---------|---------|------|
| 1 | API 认证方式 | ⭐⭐⭐ | API Key 获取、Header 配置 |
| 2 | Chat Completions 接口 | ⭐⭐⭐ | 核心接口，发送 Prompt → 返回回答 |
| 3 | 请求参数格式 | ⭐⭐⭐ | model, messages, temperature, max_tokens |
| 4 | 响应解析 | ⭐⭐⭐ | 如何从 JSON 响应中提取文本 |
| 5 | 错误处理 | ⭐⭐ | Rate limit、认证失败、超时等 |
| 6 | Token 计费 | ⭐ | 了解成本，避免超支 |

**官方文档地址：**
- DeepSeek API 文档: https://platform.deepseek.com/api-docs
- OpenAI 兼容格式说明: https://platform.deepseek.com/docs/

**关键知识点预览：**
```python
# DeepSeek 使用 OpenAI 兼容的 API 格式
from openai import OpenAI

client = OpenAI(
    api_key="your-api-key",
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "user", "content": "Hello"}
    ],
    temperature=0.7,
    max_tokens=1000
)

answer = response.choices[0].message.content
```

---

#### 任务 1.2: 安装依赖包

```bash
# 方案 A：使用 OpenAI SDK（推荐，DeepSeek 兼容）
pip install openai

# 方案 B：使用 requests 手动调用
pip install requests

# 方案 C：使用 httpx（异步支持）
pip install httpx
```

**推荐选择**: **方案 A (OpenAI SDK)**
- 原因：DeepSeek 官方兼容 OpenAI 格式，SDK 成熟稳定

---

#### 任务 1.3: 创建环境变量配置文件

**新建文件**: `.env`

```
# DeepSeek API 配置
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 可选：模型参数默认值
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=2000
```

**新建文件**: `config.py`（读取环境变量）

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", 0.7))
    DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", 2000)
```

**需要安装**:
```bash
pip install python-dotenv
```

---

### Phase 2: 核心 LLM 客户端开发

#### 任务 2.1: 创建 LLM 客户端封装类

**新建文件**: `llm_client.py`

**功能设计：**

```
llm_client.py
├── class DeepSeekClient
│   ├── __init__(api_key, base_url, model)
│   ├── chat(prompt, temperature, max_tokens)  ← 核心方法
│   └── _parse_response(response)              ← 解析响应
│
└── 辅助函数
    ├── create_client()                        ← 工厂函数
    └── test_connection()                      ← 连接测试
```

**核心代码骨架：**
```python
from openai import OpenAI
import json
from typing import Optional

class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", model: str = "deepseek-chat"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    def chat(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        调用 DeepSeek Chat API
        
        参数:
            prompt: 用户输入的 Prompt
            temperature: 温度参数（0-2，越高越随机）
            max_tokens: 最大输出 token 数
            system_prompt: 系统提示词（可选）
        
        返回:
            LLM 的文本回复
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def chat_json(self, prompt: str, **kwargs) -> dict:
        """
        调用 LLM 并返回 JSON 结果（自动解析）
        
        用于需要结构化输出的场景（如搜索参数生成）
        """
        # 在 Prompt 中强调 JSON 输出
        enhanced_prompt = prompt + "\n\n请确保只输出有效的 JSON，不要包含其他文字。"
        
        raw_response = self.chat(enhanced_prompt, **kwargs)
        
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            print(f"❌ LLM 返回的不是有效 JSON: {raw_response[:200]}...")
            raise ValueError("LLM response is not valid JSON")


def create_client() -> DeepSeekClient:
    """工厂函数：根据配置创建客户端"""
    from config import Config
    return DeepSeekClient(
        api_key=Config.DEEPSEEK_API_KEY,
        base_url=Config.DEEPSEEK_BASE_URL,
        model=Config.DEEPSEEK_MODEL
    )
```

---

#### 任务 2.2: 错误处理与重试机制

**需要处理的异常情况：**

| 异常类型 | 触发场景 | 处理策略 |
|---------|---------|---------|
| `AuthenticationError` | API Key 无效/过期 | 提示用户检查配置 |
| `RateLimitError` | 请求过于频繁 | 自动重试（指数退避） |
| `APIConnectionError` | 网络问题 | 重试 3 次，间隔递增 |
| `APITimeoutError` | 响应超时 | 增加超时时间或重试 |
| `JSONDecodeError` | LLM 未返回 JSON | 尝试修复或重新调用 |

**重试装饰器示例：**
```python
import time
from functools import wraps

def retry_on_error(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = delay * (2 ** attempt)
                    print(f"⚠️  第 {attempt+1} 次失败: {e}")
                    print(f"   等待 {wait_time}s 后重试...")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator

@retry_on_error(max_retries=3, delay=2)
def call_llm_with_retry(client, prompt):
    return client.chat(prompt)
```

---

### Phase 3: 集成到 smart_search.py

#### 任务 3.1: 修改 generate_search_params 函数

**当前代码（模拟版）：**
```python
def generate_search_params(user_query: str, llm_client=None) -> dict:
    if llm_client is None:
        print("⚠️  未提供 LLM 客户端，使用模拟数据")
        return get_mock_params(user_query)
    
    # TODO: 实际调用 LLM 的代码
```

**目标代码（真实版）：**
```python
def generate_search_params(user_query: str, llm_client=None) -> dict:
    # 1. 构建 Prompt
    prompt = build_llm_prompt(user_query)
    print("📝 已构建 Prompt（前200字符）:")
    print(prompt[:200] + "...\n")

    # 2. 如果没有传入客户端，自动创建
    if llm_client is None:
        from llm_client import create_client
        llm_client = create_client()
        print("✅ 已自动创建 DeepSeek 客户端")

    # 3. 调用真实 LLM
    print("🤖 正在调用 DeepSeek API...")
    try:
        params = llm_client.chat_json(
            prompt=prompt,
            temperature=0.3,          # 低温度，保证输出稳定
            max_tokens=1000,
            system_prompt="你是一个专业的学术搜索引擎优化器，总是返回有效的 JSON。"
        )
        
        print("✅ LLM 返回成功！")
        print(f"   意图: {params.get('intent', 'N/A')}")
        print(f"   关键词: {params.get('keywords', [])}")
        print(f"   排序: {params.get('sortBy', 'N/A')}")
        
        return params
        
    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
        print("   回退到模拟数据...")
        return get_mock_params(user_query)
```

---

#### 任务 3.2: 添加命令行测试入口

**在 smart_search.py 底部添加：**
```python
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = input("请输入你的查询需求: ")
    
    print("="*60)
    print(f"🔍 用户查询: {user_query}")
    print("="*60 + "\n")
    
    params = generate_search_params(user_query)
    
    print("\n" + "="*60)
    print("📊 生成的搜索参数:")
    print("="*60)
    print(json.dumps(params, indent=2, ensure_ascii=False))
```

**使用方式：**
```bash
# 交互式
python smart_search.py

# 命令行传参
python smart_search.py "我想了解 Transformer 优化的最新进展"

# 批量测试
python smart_search.py "最近有什么关于 LLM 的新论文？"
python smart_search.py "如何入门学习 强化学习"
```

---

### Phase 4: 测试与验证

#### 任务 4.1: 单元测试

**新建文件**: `tests/test_llm_client.py`

**测试用例：**

```python
import pytest
from llm_client import DeepSeekClient

class TestDeepSeekClient:
    def test_client_creation(self):
        client = DeepSeekClient(api_key="test-key")
        assert client.model == "deepseek-chat"
    
    def test_chat_returns_string(self):
        # Mock API 调用
        pass
    
    def test_chat_json_parses_correctly(self):
        # 测试 JSON 解析
        pass
    
    def test_error_handling(self):
        # 测试错误情况
        pass
```

---

#### 任务 4.2: 集成测试场景

| 场景 | 输入 | 预期输出 |
|------|------|---------|
| **最新研究** | "最近有什么关于 LLM 的新论文？" | sortBy=submittedDate, 关键词包含 LLM |
| **入门学习** | "我是初学者，想学 Transformer" | sortBy=relevance, max_results=20 |
| **找作者** | "找 Geoffrey Hinton 的论文" | search_query 包含 au:Hinton |
| **特定领域** | "计算机视觉的最新进展" | cat 包含 cv.CV |
| **中文查询** | "大模型优化方法" | 关键词为中英混合 |

---

#### 任务 4.3: 性能基准测试

**需要记录的指标：**

| 指标 | 目标值 | 说明 |
|------|--------|------|
| API 响应时间 | < 5s | 单次调用的延迟 |
| Token 消耗 | ~500 tokens/次 | 平均每次调用的 token 数 |
| 成功率 | > 95% | JSON 解析成功率 |
| 成本 | < ¥0.01/次 | 单次调用成本估算 |

---

## 📝 实施顺序建议

### 第一步：学习与准备（1-2 小时）

- [ ] 阅读 DeepSeek API 文档
- [ ] 注册账号并获取 API Key
- [ ] 用 curl 或 Postman 测试一次简单调用
- [ ] 理解请求/响应格式

---

### 第二步：搭建基础框架（30 分钟）

- [ ] 创建 `.env` 文件，填入 API Key
- [ ] 安装依赖：`openai`, `python-dotenv`
- [ ] 创建 `config.py` 读取配置
- [ ] 创建 `llm_client.py` 基础结构

---

### 第三步：核心功能开发（1-2 小时）

- [ ] 实现 `DeepSeekClient.chat()` 方法
- [ ] 实现 `chat_json()` 方法（带 JSON 解析）
- [ ] 添加错误处理和重试逻辑
- [ ] 编写简单的连接测试脚本

---

### 第四步：集成到现有系统（30 分钟）

- [ ] 修改 `smart_search.py` 的 `generate_search_params()`
- [ ] 替换模拟数据为真实 API 调用
- [ ] 添加回退机制（API 失败时用模拟数据）
- [ ] 更新命令行测试入口

---

### 第五步：测试与优化（1 小时）

- [ ] 用 5 个不同场景测试
- [ ] 验证输出 JSON 格式正确性
- [ ] 测试错误处理是否正常工作
- [ ] 记录性能指标和成本

---

## 🔧 可能遇到的问题及解决方案

### 问题 1: API Key 泄露风险

**解决方案：**
- ✅ 使用 `.env` 文件存储 Key（不提交到 Git）
- ✅ 将 `.env` 加入 `.gitignore`
- ✅ 代码中通过环境变量读取

---

### 问题 2: LLM 不返回纯 JSON

**解决方案：**
- ✅ 在 Prompt 中明确要求："只输出 JSON"
- ✅ 使用低 temperature（0.3-0.5）
- ✅ 添加后处理逻辑清理多余字符
- ✅ 失败时自动重试 1-2 次

---

### 问题 3: API 调用太慢影响体验

**解决方案：**
- ✅ 显示进度提示："正在调用 AI..."
- ✅ 设置合理超时时间（10-15s）
- ✅ 缓存相同查询的结果（可选）
- ✅ 异步调用（未来优化）

---

### 问题 4: Token 成本控制

**解决方案：**
- ✅ 设置合理的 max_tokens（1000-2000）
- ✅ 优化 Prompt 长度（避免过长）
- ✅ 监控每日用量
- ✅ 考虑使用更便宜的模型（如 deepseek-lite）

---

## 📚 参考资源

### 官方文档

- DeepSeek 平台: https://platform.deepseek.com/
- API 文档: https://platform.deepseek.com/api-docs/
- 定价说明: https://platform.deepseek.com/pricing

### 示例代码库

- DeepSeek 官方 GitHub: （如有）
- OpenAI Python SDK: https://github.com/openai/openai-python

### 相关工具

- Postman / curl: 测试 API 调用
- JWT.io: 调试认证（如需要）
- VS Code REST Client 插件: 直接在编辑器中测试 API

---

## ✅ 完成标准

当以下所有条件满足时，视为完成：

- [ ] 能成功调用 DeepSeek API 并获得响应
- [ ] `smart_search.py` 可以使用真实 LLM 生成参数
- [ ] 输出的 JSON 格式正确且可被后续流程使用
- [ ] 错误处理完善，不会因 API 问题导致程序崩溃
- [ ] 有完整的测试记录（至少 5 个场景）
- [ ] API Key 安全存储在 `.env` 中
- [ ] 代码有适当的注释和文档字符串

---

## 🚀 下一步行动

**你现在需要做的：**

1. **打开 DeepSeek API 文档**，重点看：
   - Chat Completions 接口
   - 认证方式
   - 请求/响应示例

2. **获取 API Key**：
   - 登录 https://platform.deepseek.com/
   - 进入 API Keys 页面
   - 创建新的 Key 并复制

3. **准备好后告诉我**，我们开始编码！

---

*规划日期: 2026-05-27*
*预计总工时: 4-6 小时*
