# Model Providers

本项目所有模型调用都必须从 FastAPI 后端发起。Next.js 前端只能调用后端 API，不能直接持有或调用任何模型密钥。

## Environment

```env
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_FALLBACK_MODEL=deepseek-v4-flash
DEEPSEEK_REASONING_EFFORT=high
DEEPSEEK_THINKING_TYPE=enabled

MODELSCOPE_API_KEY=...
MODELSCOPE_BASE_URL=https://api-inference.modelscope.cn/v1
MODELSCOPE_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
```

真实密钥只允许存在于本地 `.env` 或部署环境变量中，不写入 PRD、代码、前端 bundle、日志、测试快照或提交记录。

## DeepSeek Chat Models

来源：

- DeepSeek API Docs: https://api-docs.deepseek.com/zh-cn/
- Model and pricing page: https://api-docs.deepseek.com/zh-cn/quick_start/pricing
- Thinking mode: https://api-docs.deepseek.com/zh-cn/guides/thinking_mode
- JSON Output: https://api-docs.deepseek.com/zh-cn/guides/json_mode

模型选择：

- `deepseek-v4-pro`: 主模型。用于知识图谱抽取、跨教材整合判断、教师对话意图解析、结构化图操作生成、精华版生成和报告生成。
- `deepseek-v4-flash`: 备用小模型。用于主模型失败后的降级重试、低风险摘要、进度解释、轻量分类、快速草稿等任务。重要整合决策默认仍走 `deepseek-v4-pro`。

文档确认的关键点：

- OpenAI 兼容 Base URL 是 `https://api.deepseek.com`。
- 当前模型名包括 `deepseek-v4-pro` 和 `deepseek-v4-flash`。
- 两个模型都支持思考模式、JSON Output 和 Tool Calls。
- 上下文长度为 `1M`，最大输出长度为 `384K`。
- 思考模式默认开启；OpenAI SDK 中 `thinking` 需要放到 `extra_body`。
- 思考模式下 `reasoning_effort` 支持 `high` 和 `max`；本项目默认 `high`。
- 思考模式下 `temperature`、`top_p`、`presence_penalty`、`frequency_penalty` 不生效，因此后端不要依赖这些参数控制稳定性。
- 使用 Tool Calls 且发生工具调用时，后续轮次必须完整回传 `reasoning_content`，否则可能触发 400 错误。

### Basic Chat Call

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

response = client.chat.completions.create(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
    messages=[
        {"role": "system", "content": "You are a knowledge integration assistant."},
        {"role": "user", "content": "Extract knowledge points from this textbook section."},
    ],
    stream=False,
    reasoning_effort=os.getenv("DEEPSEEK_REASONING_EFFORT", "high"),
    extra_body={
        "thinking": {"type": os.getenv("DEEPSEEK_THINKING_TYPE", "enabled")}
    },
)

answer = response.choices[0].message.content
```

### Structured JSON Call

用于知识点抽取、关系抽取、整合建议、图操作生成。Prompt 中必须明确包含 `json` 字样，并给出目标结构，避免只设置 `response_format` 而没有格式约束。

```python
import json
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

messages = [
    {
        "role": "system",
        "content": (
            "Output valid json only. Schema: "
            "{\"nodes\": [{\"name\": string, \"definition\": string}], "
            "\"edges\": [{\"source\": string, \"target\": string, \"relation\": string}]}"
        ),
    },
    {"role": "user", "content": "Section text: ..."},
]

response = client.chat.completions.create(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
    messages=messages,
    response_format={"type": "json_object"},
    max_tokens=8192,
    reasoning_effort=os.getenv("DEEPSEEK_REASONING_EFFORT", "high"),
    extra_body={
        "thinking": {"type": os.getenv("DEEPSEEK_THINKING_TYPE", "enabled")}
    },
)

payload = json.loads(response.choices[0].message.content)
```

### Tool Call Pattern

Agent 只能提出结构化工具调用，不能直接修改图状态。后端确定性工具负责执行、记录日志、持久化 NetworkX/JSON，并通过 WebSocket 推送新图。

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "merge_nodes",
            "description": "Merge duplicate knowledge nodes and preserve provenance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_ids": {"type": "array", "items": {"type": "string"}},
                    "canonical_name": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["node_ids", "canonical_name", "reason"],
            },
        },
    }
]

response = client.chat.completions.create(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
    messages=messages,
    tools=tools,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
)
```

### Fallback Policy

后端模型网关应封装统一重试逻辑：

1. 默认调用 `DEEPSEEK_MODEL=deepseek-v4-pro`。
2. 网络错误、限流、临时服务错误时，可对幂等任务重试。
3. 重试仍失败时，允许切换到 `DEEPSEEK_FALLBACK_MODEL=deepseek-v4-flash`。
4. 对跨教材合并、冲突判断、最终报告等高影响任务，fallback 结果必须标记 `modelUsed` 和 `requiresReview=true`。
5. 所有模型调用日志只能记录模型名、耗时、token 用量、错误类型和 request id，不记录密钥或完整教材原文。

## ModelScope Qwen Embedding

来源：

- ModelScope model page: https://www.modelscope.cn/models/Qwen/Qwen3-Embedding-8B
- ModelScope API-Inference docs: https://www.modelscope.cn/docs/model-service/API-Inference/intro
- Qwen model card reference: https://huggingface.co/Qwen/Qwen3-Embedding-8B

模型选择：

- `Qwen/Qwen3-Embedding-8B`: 向量化模型。只用于教材 chunk、查询文本、知识点候选匹配的 embedding，不用于回答生成、不用于图谱关系判断的最终裁决。

模型特点：

- 模型类型是 text embedding。
- 支持 100+ 语言，适合中文教材和跨语言检索场景。
- 上下文长度为 `32K`。
- 默认最大向量维度为 `4096`；本地连通性测试返回维度 `4096`。
- 支持 instruction-aware retrieval。查询侧可以追加任务说明，文档 chunk 侧保持原文更利于引用。

### Embedding Call

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["MODELSCOPE_API_KEY"],
    base_url=os.getenv("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1"),
)

response = client.embeddings.create(
    model=os.getenv("MODELSCOPE_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
    input="你好",
    encoding_format="float",
)

embedding = response.data[0].embedding
```

### Batch Embedding Call

```python
texts = [
    "炎症是机体对致炎因子的防御性反应。",
    "动作电位由膜电位快速去极化和复极化构成。",
]

response = client.embeddings.create(
    model=os.getenv("MODELSCOPE_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
    input=texts,
    encoding_format="float",
)

vectors = [item.embedding for item in response.data]
```

### Usage Policy

- RAG 索引：章节内 chunk -> ModelScope embedding -> ChromaDB。
- 语义去重候选：知识点定义或短摘要 -> embedding similarity -> DeepSeek 复判。
- 查询检索：教师问题 -> query embedding -> ChromaDB top-k -> DeepSeek 引用式回答。
- embedding 调用可以批量并发，但必须保留 chunk 元数据：`chunk_id`、`textbook`、`chapter`、`page_start`、`page_end`、`text`。
- 不允许把 embedding 结果当成最终语义裁决；它只负责召回候选。
