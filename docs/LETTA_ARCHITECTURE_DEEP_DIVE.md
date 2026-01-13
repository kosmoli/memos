# Letta 实现原理与架构深度解析

**日期**: 2026-01-13
**目的**: 深入理解 Letta 后端的实现原理和架构设计

---

## 目录

- [1. 整体架构概览](#1-整体架构概览)
- [2. 核心组件详解](#2-核心组件详解)
- [3. Provider 系统深度解析](#3-provider-系统深度解析)
- [4. Agent 执行流程](#4-agent-执行流程)
- [5. 数据流分析](#5-数据流分析)
- [6. LLM 客户端抽象](#6-llm-客户端抽象)
- [7. 工具系统](#7-工具系统)
- [8. 记忆管理](#8-记忆管理)
- [9. API 路由层](#9-api-路由层)

---

## 1. 整体架构概览

### 1.1 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                       API 层 (FastAPI)                        │
│  letta/server/rest_api/routers/v1/                          │
│  - agents.py, providers.py, tools.py, messages.py, etc.     │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                     Service 层 (业务逻辑)                     │
│  letta/services/                                            │
│  - agent_manager.py, provider_manager.py                    │
│  - message_manager.py, tool_manager.py, etc.                │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                     Schema 层 (数据模型)                      │
│  letta/schemas/                                              │
│  - agent.py, provider/, llm_config.py, message.py, etc.     │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                     ORM 层 (数据库映射)                       │
│  letta/orm/                                                  │
│  - providers.py, agents.py, tool.py, etc.                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    数据库层 (PostgreSQL)                      │
│  - providers, provider_models, agents, messages, tools...   │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 核心目录结构

```
letta/
├── agents/                  # Agent 核心实现
│   ├── base_agent.py       # Agent 基类
│   ├── letta_agent.py      # Letta Agent 实现
│   ├── agent_loop.py       # Agent 执行循环
│   └── ephemeral_agent.py  # 临时 Agent
│
├── schemas/                 # Pydantic 数据模型
│   ├── providers/          # Provider 模型
│   │   ├── base.py         # Provider 基类
│   │   ├── openai.py       # OpenAI Provider
│   │   ├── anthropic.py    # Anthropic Provider
│   │   └── ...
│   ├── llm_config.py       # LLM 配置模型
│   ├── embedding_config.py # Embedding 配置模型
│   ├── agent.py            # Agent 状态模型
│   └── message.py          # 消息模型
│
├── services/                # 业务逻辑服务
│   ├── agent_manager.py    # Agent 管理
│   ├── provider_manager.py # Provider 管理
│   ├── message_manager.py  # 消息管理
│   ├── tool_manager.py     # 工具管理
│   └── ...
│
├── llm_api/                 # LLM 客户端抽象
│   ├── llm_client.py       # LLM 客户端工厂
│   ├── llm_client_base.py  # LLM 客户端基类
│   ├── openai_client.py    # OpenAI 客户端
│   ├── anthropic_client.py # Anthropic 客户端
│   └── ...
│
├── functions/               # 工具系统
│   ├── functions.py        # 工具定义
│   ├── function_sets/      # 内置工具集
│   └── interface.py        # 工具接口
│
├── server/                  # Web 服务器
│   └── rest_api/
│       └── routers/
│           └── v1/         # API 路由
│
└── orm/                     # 数据库 ORM
    ├── provider.py         # Provider 表
    ├── provider_model.py   # ProviderModel 表
    ├── agents.py           # Agent 表
    └── ...
```

---

## 2. 核心组件详解

### 2.1 Agent 系统

#### 2.1.1 Agent 类层次结构

```python
# letta/agents/base_agent.py
class BaseAgent:
    """Agent 基类，定义核心接口"""
    - id: str
    - message_manager: MessageManager
    - agent_manager: AgentManager
    - actor: User

    async def step() -> LettaResponse
    async def step_stream() -> AsyncGenerator

# letta/agents/letta_agent.py
class LettaAgent(BaseAgent):
    """Letta Agent 的完整实现"""
    - block_manager: BlockManager      # 记忆块管理
    - job_manager: JobManager          # 任务管理
    - passage_manager: PassageManager  # 段落管理
    - step_manager: StepManager        # 步骤管理
    - summarizer: Summarizer           # 摘要器
```

#### 2.1.2 Agent 状态模型

```python
# letta/schemas/agent.py
class AgentState(LettaBase):
    """Agent 的完整状态"""
    id: str
    name: str
    agent_type: AgentType
    llm_config: LLMConfig          # LLM 配置
    embedding_config: EmbeddingConfig  # Embedding 配置
    memory: Memory                 # 记忆配置
    tools: list[Tool]              # 附加的工具
    system: str                    # 系统提示词
    tool_rules: list[ToolRule]     # 工具规则
    tool_exec_environment_variables: dict  # 工具执行环境变量
```

### 2.2 Provider 系统（详见第 3 节）

### 2.3 LLM 配置系统

```python
# letta/schemas/llm_config.py
class LLMConfig(BaseModel):
    """LLM 连接和生成参数配置"""
    # 模型标识
    model: str                          # 模型名称
    handle: Optional[str]               # 格式: "provider/model-name"
    display_name: Optional[str]

    # 端点配置
    model_endpoint_type: Literal[...]   # "openai", "anthropic", etc.
    model_endpoint: Optional[str]       # 实际的 API endpoint
    provider_name: Optional[str]        # Provider 名称
    provider_category: Optional[ProviderCategory]  # base 或 byok

    # 生成参数
    context_window: int                 # 上下文窗口大小
    temperature: float = 0.7
    max_tokens: Optional[int]

    # 推理控制
    enable_reasoner: bool = True
    reasoning_effort: Optional[Literal[...]]
    max_reasoning_tokens: int = 0
    put_inner_thoughts_in_kwargs: bool = False
```

---

## 3. Provider 系统深度解析

### 3.1 Provider 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Provider 抽象层                          │
│  Provider (base.py)                                          │
│  - name, provider_type, provider_category                   │
│  - base_url, api_key_enc, region, api_version               │
│  - list_llm_models_async()                                  │
│  - list_embedding_models_async()                            │
│  - get_handle(model_name, is_embedding, base_name)          │
│  - cast_to_subtype()                                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼───────┐  ┌───────▼────────┐
│ OpenAIProvider │  │AnthropicProv.│  │TogetherProvider│
│  - openai.py    │  │- anthropic.py│  │  - together.py │
└────────────────┘  └──────────────┘  └────────────────┘
```

### 3.2 Base vs BYOK 模式

#### 3.2.1 ProviderCategory 枚举

```python
# letta/schemas/enums.py
class ProviderCategory(str, Enum):
    base = "base"    # 基础 Provider：从环境变量读取 API Key
    byok = "byok"    # BYOK Provider：API Key 存储在数据库中
```

#### 3.2.2 关键区别

| 特性 | Base Provider | BYOK Provider |
|------|--------------|--------------|
| **API Key 来源** | 环境变量 | 数据库（加密存储） |
| **organization_id** | NULL（全局可用） | 用户组织 ID |
| **创建方式** | 系统启动时从环境变量同步 | 用户通过 API 创建 |
| **删除** | 不可删除 | 可以软删除 |
| **模型列表** | 启动时同步到数据库 | 创建时同步 |

#### 3.2.3 Base Provider 初始化流程

```python
# letta/services/provider_manager.py:sync_base_providers
async def sync_base_providers(self, base_providers: list[PydanticProvider], actor: PydanticUser):
    """
    1. 检查数据库中是否已存在同名 Provider
    2. 如果不存在，创建新记录
    3. Base Provider 不存储 API Key（api_key_enc 为空）
    4. Base Provider 的 organization_id 为 NULL
    """
    for provider in base_providers:
        # 检查是否已存在
        existing = await ProviderModel.list_async(
            name=provider.name,
            organization_id=None,  # Base providers are global
        )

        if not existing:
            # 创建但不存储 API key
            await self.create_provider_async(
                request=provider_create,
                actor=actor,
                is_byok=False  # Base provider
            )
```

#### 3.2.4 BYOK Provider 创建流程

```python
# letta/services/provider_manager.py:create_provider_async
async def create_provider_async(self, request: ProviderCreate, actor: PydanticUser, is_byok: bool = True):
    """
    1. 验证名称不与 Base Provider 冲突
    2. 检查是否有软删除的同名 Provider 可以恢复
    3. 加密 API Key 并存储
    4. 设置 organization_id 为用户的组织 ID
    5. 自动同步可用模型列表
    """
    # 名称冲突检查
    if is_byok:
        existing_base = await ProviderModel.list_async(
            name=request.name,
            organization_id=None,
        )
        if existing_base:
            raise ValueError(f"名称与 Base Provider 冲突")

    # 恢复软删除的 Provider
    deleted_provider = await session.execute(
        select(ProviderModel).where(
            ProviderModel.name == request.name,
            ProviderModel.organization_id == org_id,
            ProviderModel.is_deleted == True,
        )
    )

    # 创建新 Provider
    provider = PydanticProvider(
        **request.model_dump(),
        provider_category=ProviderCategory.byok if is_byok else ProviderCategory.base
    )

    # 加密 API Key
    if request.api_key:
        provider.api_key_enc = await Secret.from_plaintext_async(request.api_key)

    # BYOK Provider 自动同步模型
    if is_byok:
        await self._sync_default_models_for_provider(provider, actor)
```

### 3.3 Handle 生成机制

#### 3.3.1 `openai-proxy` 硬编码问题

```python
# letta/schemas/providers/openai.py:166-169
if self.base_url != "https://api.openai.com/v1":
    # 非 OpenAI 官方 API 强制使用 openai-proxy 前缀
    handle = self.get_handle(model_name, base_name="openai-proxy")
else:
    handle = self.get_handle(model_name)  # 使用 Provider 的 name
```

**示例**：
- 用户创建 Provider：name="MyProvider", base_url="https://api.custom.com/v1"
- 生成的 handle: `openai-proxy/gpt-4o`（而不是 `MyProvider/gpt-4o`）

#### 3.3.2 get_handle 方法

```python
# letta/schemas/providers/base.py:161-178
def get_handle(self, model_name: str, is_embedding: bool = False, base_name: str | None = None) -> str:
    """
    生成模型 handle，格式: {base_name}/{model_name}
    支持通过 LLM_HANDLE_OVERRIDES 进行名称覆盖
    """
    base_name = base_name if base_name else self.name

    # 应用 handle 覆盖规则
    overrides = EMBEDDING_HANDLE_OVERRIDES if is_embedding else LLM_HANDLE_OVERRIDES
    if base_name in overrides and model_name in overrides[base_name]:
        model_name = overrides[base_name][model_name]

    return f"{base_name}/{model_name}"
```

### 3.4 API Key 获取流程

```python
# letta/llm_api/llm_client_base.py:235-253
def get_byok_overrides(self, llm_config: LLMConfig) -> Tuple[Optional[str], ...]:
    """
    只有 BYOK Provider 从数据库获取 API Key
    Base Provider 直接使用环境变量
    """
    api_key = None

    # 只为 BYOK providers 从数据库获取
    if llm_config.provider_category == ProviderCategory.byok:
        api_key = ProviderManager().get_override_key(
            llm_config.provider_name,
            actor=self.actor
        )
        if api_key == "":
            api_key = None

    return api_key, None, None
```

### 3.5 Provider 数据库模型

```python
# letta/orm/provider.py
class Provider(SqlalchemyBase, OrganizationMixin):
    __tablename__ = "providers"
    __table_args__ = (
        UniqueConstraint("name", "organization_id", name="unique_name_organization_id"),
    )

    # organization_id 可以为 NULL（Base Provider）
    organization_id: Mapped[Optional[str]]

    name: Mapped[str]
    provider_type: Mapped[str]        # openai, anthropic, etc.
    provider_category: Mapped[str]    # base 或 byok
    base_url: Mapped[Optional[str]]

    # 加密字段
    api_key_enc: Mapped[Optional[str]]   # 加密的 API Key
    access_key_enc: Mapped[Optional[str]]
```

---

## 4. Agent 执行流程

### 4.1 完整执行流程

```
用户请求 → API 层 → AgentManager → LettaAgent.step()
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent 执行循环                              │
│                                                             │
│  1. 准备消息                                                 │
│     └─> 加载历史消息、记忆块、工具列表                         │
│                                                             │
│  2. LLM 请求                                                 │
│     └─> LLMClient.send_llm_request_async()                  │
│         └─> 构建 request_data                                │
│         └─> 调用 Provider API                                │
│         └─> 解析响应                                         │
│                                                             │
│  3. 处理工具调用                                             │
│     └─> ToolExecutionManager.execute_tools()                │
│         └─> 检查是否需要批准                                 │
│         └─> 执行工具                                         │
│         └─> 返回结果                                         │
│                                                             │
│  4. 更新状态                                                 │
│     └─> 保存消息、更新记忆块                                 │
│     └─> 检查是否需要总结                                     │
│                                                             │
│  5. 循环或退出                                               │
│     └─> 如果有工具调用，继续循环                              │
│     └─> 否则返回响应                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Step 方法详细流程

```python
# letta/agents/letta_agent.py:175-211
async def step(
    self,
    input_messages: list[MessageCreateBase],
    max_steps: int = DEFAULT_MAX_STEPS,
    ...
) -> Union[LettaResponse, dict]:

    # 1. 获取 Agent 状态
    agent_state = await self.agent_manager.get_agent_by_id_async(
        agent_id=self.agent_id,
        include_relationships=["tools", "memory", "tool_exec_environment_variables", "sources"],
        actor=self.actor,
    )

    # 2. 执行内部步骤
    result = await self._step(
        agent_state=agent_state,
        input_messages=input_messages,
        max_steps=max_steps,
        ...
    )

    # 3. 创建响应
    return _create_letta_response(
        new_in_context_messages=result.new_in_context_messages,
        use_assistant_message=use_assistant_message,
        stop_reason=result.stop_reason,
        usage=result.usage,
    )
```

---

## 5. 数据流分析

### 5.1 创建 Agent 的数据流

```
POST /v1/agents/
    │
    ▼
agents.py:create_agent()
    │
    ▼
AgentManager:create_agent_async()
    │
    ├─> 1. 验证 LLMConfig
    │       └─> ProviderManager.get_llm_config_from_handle(handle)
    │           └─> 查找 ProviderModel 或动态获取
    │
    ├─> 2. 创建 Agent 记录
    │       └─> AgentModel.create_async()
    │
    ├─> 3. 创建记忆块
    │       └─> BlockManager.create_blocks_from_memory()
    │
    ├─> 4. 附加工具
    │       └─> ToolManager.attach_tools_to_agent()
    │
    └─> 5. 返回 AgentState
```

### 5.2 发送消息的数据流

```
POST /v1/agents/{agent_id}/messages
    │
    ▼
agents.py:create_message()
    │
    ▼
AgentManager:step()
    │
    ▼
LettaAgent.step()
    │
    ├─> 获取 Agent 状态
    ├─> 准备上下文消息
    │
    ▼
LLMClient.send_llm_request_async()
    │
    ├─> get_byok_overrides_async()  # 获取 API Key
    ├─> build_request_data()        # 构建请求
    ├─> request_async()              # 发送到 Provider
    └─> convert_response_to_chat_completion()
    │
    ▼
处理工具调用（如果有）
    │
    ├─> 检查工具规则
    ├─> 执行工具
    └─> 保存结果
    │
    ▼
返回响应
```

---

## 6. LLM 客户端抽象

### 6.1 客户端工厂

```python
# letta/llm_api/llm_client.py
class LLMClient:
    @staticmethod
    def create(provider_type: ProviderType, ...) -> LLMClientBase:
        """根据 ProviderType 创建对应的客户端"""
        match provider_type:
            case ProviderType.anthropic:
                return AnthropicClient(...)
            case ProviderType.openai:
                return OpenAIClient(...)
            case _:
                return OpenAIClient(...)  # 默认使用 OpenAI 客户端
```

### 6.2 客户端基类

```python
# letta/llm_api/llm_client_base.py
class LLMClientBase:
    async def send_llm_request_async(
        self,
        agent_type: AgentType,
        messages: List[Message],
        llm_config: LLMConfig,
        tools: Optional[List[dict]] = None,
        ...
    ) -> Union[ChatCompletionResponse, AsyncStream[ChatCompletionChunk]]:
        # 1. 构建请求数据
        request_data = self.build_request_data(...)

        # 2. 发送请求
        response_data = await self.request_async(request_data, llm_config)

        # 3. 转换响应
        return await self.convert_response_to_chat_completion(response_data, ...)
```

### 6.3 OpenAI 客户端

```python
# letta/llm_api/openai_client.py
class OpenAIClient(LLMClientBase):
    def _prepare_client_kwargs(self, llm_config: LLMConfig) -> dict:
        """准备 AsyncOpenAI 客户端参数"""
        # 1. 获取 BYOK override（如果有）
        api_key, _, _ = self.get_byok_overrides(llm_config)

        # 2. 默认使用全局 OpenAI Key
        if not api_key:
            api_key = model_settings.openai_api_key or os.environ.get("OPENAI_API_KEY")

        return {
            "api_key": api_key or "DUMMY_API_KEY",
            "base_url": llm_config.model_endpoint,
        }
```

---

## 7. 工具系统

### 7.1 工具定义

```python
# letta/functions/interface.py
class Tool(BaseModel):
    """工具定义"""
    name: str
    description: str
    source_code: str
    json_schema: dict
    tags: list[str]           # e.g., ["letta_core", "custom"]
    default_requires_approval: bool
```

### 7.2 工具执行流程

```
Agent 接收 LLM 响应
    │
    ▼
检测到 tool_calls
    │
    ▼
ToolRulesSolver
    │
    ├─> 应用工具规则
    │   - run_first
    │   - exit_loop
    │   - requires_approval
    │   - max_count_per_step
    │
    ▼
ToolExecutionManager
    │
    ├─> 检查是否需要批准
    ├─> 执行工具函数
    ├─> 捕获返回值
    └─> 返回 ToolExecutionResult
    │
    ▼
将工具返回值添加到消息列表
    │
    ▼
继续下一轮对话
```

---

## 8. 记忆管理

### 8.1 记忆块（Core Memory）

```python
# letta/schemas/agent.py
class Memory(BaseModel):
    """Agent 记忆配置"""
    human: str = "Instructions on human"
    persona: str = "Agent persona"
    system: str = "System instructions"

    # 附加的记忆块
    custom_blocks: dict[str, Block] = {}
```

### 8.2 档案记忆（Archival Memory）

```
Archival Memory
    │
    ├─> PassageManager: 管理文档段落
    ├─> 向量数据库: Pinecone / Native
    └─> Embedding 服务: 语义搜索
```

### 8.3 摘要机制

```python
# letta/services/summarizer/summarizer.py
class Summarizer:
    """消息摘要管理"""
    mode: SummarizationMode
        - static_buffer: 保持固定大小的消息缓冲区
        - partial_evict: 部分淘汰旧消息

    async def summarize_if_needed(self, messages: list[Message]) -> list[Message]:
        """如果消息过多，触发摘要"""
        if len(messages) > self.message_buffer_limit:
            # 生成摘要
            summary = await self.summarization_agent.generate_summary(messages)

            # 更新摘要块
            await self.block_manager.update_block(...)

            # 返回压缩后的消息列表
            return [summary] + recent_messages
```

---

## 9. API 路由层

### 9.1 Agent API

```python
# letta/server/rest_api/routers/v1/agents.py
@router.post("/", response_model=AgentState)  # 创建 Agent
@router.get("/", response_model=List[AgentState])  # 列出 Agents
@router.get("/{agent_id}", response_model=AgentState)  # 获取 Agent
@router.patch("/{agent_id}", response_model=AgentState)  # 更新 Agent
@router.delete("/{agent_id}")  # 删除 Agent

@router.post("/{agent_id}/messages")  # 发送消息
@router.post("/{agent_id}/messages/stream")  # 流式发送
@router.post("/{agent_id}/messages/async")  # 异步发送
```

### 9.2 Provider API

```python
# letta/server/rest_api/routers/v1/providers.py
@router.get("/", response_model=List[Provider])  # 列出 Providers
    # 注意: 只返回 BYOK providers，base providers 需要单独查询

@router.post("/", response_model=Provider)  # 创建 Provider
    # API 创建的 Provider 强制为 BYOK 模式

@router.get("/{provider_id}", response_model=Provider)  # 获取 Provider
@router.patch("/{provider_id}", response_model=Provider)  # 更新 Provider
@router.delete("/{provider_id}")  # 删除 Provider（软删除）

@router.post("/check")  # 检查 Provider 配置
@router.post("/{provider_id}/check")  # 检查现有 Provider
```

### 9.3 Models API

```python
# letta/server/rest_api/routers/v1/llms.py
@router.get("/models/")  # 列出 LLM 模型
    # 返回: List[ProviderModel]

@router.get("/models/embedding")  # 列出 Embedding 模型
```

---

## 10. 关键发现总结

### 10.1 Provider 系统的核心问题

1. **`openai-proxy` 硬编码**
   - 所有非官方 OpenAI API 都被标记为 `openai-proxy`
   - 无法区分不同的第三方聚合平台
   - 用户自定义的 Provider 名称被忽略

2. **Base/BYOK 模式区分**
   - Base Provider: 从环境变量读取 API Key
   - BYOK Provider: API Key 存储在数据库
   - 这种区分增加了系统复杂度

3. **软删除问题**
   - Provider 使用软删除
   - 删除后 `is_deleted=True`，记录仍存在
   - 唯一约束阻止重用名称

### 10.2 API Key 获取流程

```
LLMConfig
    │
    ├─> provider_category == ProviderCategory.byok
    │       │
    │       └─> ProviderManager.get_override_key_async(provider_name)
    │           └─> 从数据库查询 Provider
    │           └─> 解密 api_key_enc
    │           └─> 返回明文 API Key
    │
    └─> provider_category == ProviderCategory.base
            │
            └─> 使用环境变量 (model_settings.{provider_type}_api_key)
```

---

**文档版本**: v1.0
**最后更新**: 2026-01-13
**作者**: Claude (Opus 4.5)
