# Memos API 变更文档

**日期**: 2026-01-14
**版本**: v1.0
**状态**: 已实施

---

## 目录

- [1. 概述](#1-概述)
- [2. Provider API 变更](#2-provider-api-变更)
- [3. LLM API 变更](#3-llm-api-变更)
- [4. 兼容性说明](#4-兼容性说明)
- [5. 迁移指南](#5-迁移指南)

---

## 1. 概述

Memos 相比 Letta 做了以下核心架构变更：

| 变更项 | Letta | Memos |
|--------|-------|-------|
| **Provider 类型** | Base + BYOK 双模式 | 统一 BYOK 模式 |
| **Provider 创建** | 环境变量 + API | 仅 API |
| **organization_id** | 可为 NULL（全局 Provider） | 必须有值 |
| **provider_category** | 有此字段 | 已移除 |
| **删除方式** | 软删除 | 硬删除 |

---

## 2. Provider API 变更

### 2.1 `GET /v1/providers` - 列出 Providers

#### Letta (原始)

```http
GET /v1/providers?provider_category=byok&provider_name=openai
```

**请求参数**:
- `provider_category`: `Optional[List[ProviderCategory]]` - 可按 `base` 或 `byok` 筛选

#### Memos (变更后)

```http
GET /v1/providers?provider_name=openai
```

**请求参数**:
- ~~`provider_category`~~ - 已移除

**响应示例**:
```json
{
  "providers": [
    {
      "id": "provider-xxx",
      "name": "openai",
      "provider_type": "openai",
      "organization_id": "org-xxx",
      "base_url": "https://api.openai.com/v1",
      "created_at": "2026-01-14T00:00:00Z"
    }
  ]
}
```

---

### 2.2 `POST /v1/providers` - 创建 Provider

#### Letta (原始)

**内部实现**:
```python
provider = await server.provider_manager.create_provider_async(
    request,
    actor=actor,
    is_byok=True  # 区分 Base/BYOK
)
```

#### Memos (变更后)

**内部实现**:
```python
# Memos: 所有 Provider 都是 BYOK 类型，无 is_byok 参数
provider = await server.provider_manager.create_provider_async(
    request,
    actor=actor
)
```

**请求体** (无变化):
```json
{
  "name": "openai",
  "provider_type": "openai",
  "api_key": "sk-xxx",
  "base_url": "https://api.openai.com/v1"
}
```

**响应** (无变化):
```json
{
  "id": "provider-xxx",
  "name": "openai",
  "provider_type": "openai",
  "organization_id": "org-xxx",
  "created_at": "2026-01-14T00:00:00Z"
}
```

---

### 2.3 `DELETE /v1/providers` - 删除 Provider

#### Letta (原始)

- 软删除：设置 `is_deleted = True`
- Provider 名称不可重用

#### Memos (变更后)

- 硬删除：从数据库完全移除记录
- Provider 名称可立即重用

**请求** (无变化):
```http
DELETE /v1/providers?provider_id=provider-xxx
```

---

## 3. LLM API 变更

### 3.1 `GET /v1/llms` - 列出 LLM 模型

#### Letta (原始)

```http
GET /v1/llms?provider_category=byok&provider_name=openai
```

**请求参数**:
- `provider_category`: `Optional[List[ProviderCategory]]` - 可按 `base` 或 `byok` 筛选

#### Memos (变更后)

```http
GET /v1/llms?provider_name=openai
```

**请求参数**:
- ~~`provider_category`~~ - 已移除

**响应示例**:
```json
{
  "models": [
    {
      "id": "model-xxx",
      "model": "gpt-4o",
      "provider_name": "openai",
      "handle": "openai/gpt-4o",
      "context_window": 128000
    }
  ]
}
```

---

## 4. 兼容性说明

### 4.1 破坏性变更

| API | 变更 | 影响 |
|-----|------|------|
| `GET /v1/providers` | 移除 `provider_category` 查询参数 | 使用此参数的客户端会收到 422 错误 |
| `GET /v1/llms` | 移除 `provider_category` 查询参数 | 使用此参数的客户端会收到 422 错误 |

### 4.2 非破坏性变更

| API | 变更 | 说明 |
|-----|------|------|
| `POST /v1/providers` | 移除内部 `is_byok` 参数 | 请求/响应格式无变化 |
| `DELETE /v1/providers` | 软删除 → 硬删除 | API 调用方式无变化 |

---

## 5. 迁移指南

### 5.1 客户端代码适配

#### Letta 客户端 (旧代码)

```python
# 按类别筛选 Provider
response = await client.get_providers(
    provider_category=[ProviderCategory.byok],
    provider_name="openai"
)
```

#### Memos 客户端 (新代码)

```python
# 移除 provider_category 参数
response = await client.get_providers(
    provider_name="openai"
)
```

---

### 5.2 LLM 模型列表获取

#### Letta 客户端 (旧代码)

```python
models = await server.list_llm_models_async(
    provider_category=[ProviderCategory.byok],
    provider_name="openai",
    actor=actor
)
```

#### Memos 客户端 (新代码)

```python
# 移除 provider_category 参数
models = await server.list_llm_models_async(
    provider_name="openai",
    actor=actor
)
```

---

### 5.3 Provider 创建

无需变更，API 调用方式保持一致：

```python
# Letta 和 Memos 都使用相同的 API
provider = await server.provider_manager.create_provider_async(
    request=ProviderCreate(
        name="openai",
        provider_type=ProviderType.openai,
        api_key="sk-xxx",
        base_url="https://api.openai.com/v1"
    ),
    actor=actor
)
```

---

### 5.4 环境变量迁移

#### Letta (环境变量驱动)

```bash
# 设置环境变量后，Letta 自动创建 Base Provider
export OPENAI_API_KEY=sk-xxx
export ANTHROPIC_API_KEY=sk-ant-xxx
```

#### Memos (API 驱动)

```bash
# Memos 不再从环境变量创建 Provider
# 需要通过 API 创建：
curl -X POST http://localhost:8283/v1/providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "openai",
    "provider_type": "openai",
    "api_key": "sk-xxx"
  }'
```

---

## 6. Embedding 模型获取变更

### 6.1 变更说明

#### Letta (原始)

OpenAI 类型 Provider 的 embedding 模型列表是**硬编码**的：

```python
async def list_embedding_models_async(self) -> list[EmbeddingConfig]:
    return [
        text-embedding-ada-002,
        text-embedding-3-small,
        text-embedding-3-large,
    ]
```

**问题**：
- 所有 `provider_type=openai` 的 Provider 都返回相同的 3 个 embedding 模型
- 即使 Provider 实际上不提供 embedding 功能，也会显示这些"幽灵模型"
- 用户创建两个 OpenAI 类型的 Provider（一个仅 LLM，一个 LLM+Embedding）会看到 6 个 embedding 模型

#### Memos (变更后)

Embedding 模型列表改为**动态获取**：

```python
async def list_embedding_models_async(self) -> list[EmbeddingConfig]:
    # 1. 调用 /models API 获取实际可用模型列表
    # 2. 通过名称模式匹配 (text-embedding-, embedding-)
    # 3. 只返回实际存在的 embedding 模型
    # 4. 如果没有，返回空列表
```

**改进**：
- 只有 Provider 实际支持的 embedding 模型才会被返回
- 不提供 embedding 的 Provider 返回空列表
- 避免用户看到无效的 embedding 模型

### 6.2 行为对比

| 场景 | Letta | Memos |
|------|-------|-------|
| Provider A（仅 LLM） | 返回 3 个硬编码模型 ❌ | 返回空列表 ✅ |
| Provider B（LLM + Embedding） | 返回 3 个硬编码模型 | 返回实际可用的模型 |
| 两个 Provider 合计 | 6 个模型（有重复/幽灵） | 仅实际可用的模型 |

### 6.3 Embedding 模型识别规则

Memos 通过以下模式识别 embedding 模型：

```python
EMBEDDING_PATTERNS = [
    "text-embedding-",  # OpenAI 官方格式
    "embedding-",       # 通用格式
]
```

**支持扩展**：可以添加更多模式以支持第三方 embedding 模型：
```python
EMBEDDING_PATTERNS = [
    "text-embedding-",
    "embedding-",
    "bge-",           # FlagEmbedding
    "e5-",            # E5 embeddings
    "voyage-",        # Voyage AI
]
```

### 6.4 API 影响

此变更**不影响 API 接口**，仅影响返回结果：

```http
GET /v1/embeddings?provider_name=openai-llm
# Letta: 返回 3 个硬编码模型
# Memos: 返回空列表（如果 Provider 不支持 embedding）

GET /v1/embeddings?provider_name=openai-full
# Letta: 返回 3 个硬编码模型
# Memos: 返回实际可用的 embedding 模型
```

---

## 7. Bug 修复

### 7.1 Provider 模型同步后未提交到数据库

**问题**：创建 Provider 时同步的模型没有被正确保存到数据库。

**根本原因**：`provider_manager.py` 中的 `sync_provider_models_async` 方法在添加新模型后缺少 `session.commit()` 调用。

```python
# 修复前（原始 Letta 代码）
async def sync_provider_models_async(...):
    async with db_registry.async_session() as session:
        # 删除旧模型后有 commit
        await session.commit()

        # 添加新模型...但没有 commit!
        for llm_config in llm_models:
            model = ProviderModelORM(...)
            await model.create_async(session)  # 创建但没有提交

        # 方法结束，所有新模型丢失！
```

**修复**：在方法末尾添加 commit：
```python
# 修复后
async def sync_provider_models_async(...):
    async with db_registry.async_session() as session:
        # 删除旧模型
        await session.commit()

        # 添加新模型
        for llm_config in llm_models:
            model = ProviderModelORM(...)
            await model.create_async(session)

        # 提交所有新模型
        await session.commit()
        logger.info(f"=== Successfully synced models for provider '{provider.name}' ===")
```

**影响**：
- 原始 Letta 和 Memos 都受影响
- 创建 Provider 后无法通过 API 查询到同步的模型
- 模型在日志中显示"创建成功"但数据库中不存在

---

### 7.2 模型同步时 API 认证失败 (401)

**问题**：Provider 模型同步时调用 `/models` API 返回 401 Unauthorized。

**根本原因**：`_sync_default_models_for_provider` 方法传递明文 `api_key` 给 `OpenAIProvider`，但 `OpenAIProvider._get_models_async()` 使用 `api_key_enc.get_plaintext_async()`，导致没有发送 Authorization header。

```python
# 修复前
api_key = await provider.api_key_enc.get_plaintext_async()
kwargs = {"name": provider.name, "api_key": api_key}  # 明文 api_key
provider_instance = provider_class(**kwargs)
# 此时 api_key_enc 为 None，_get_models_async 无法获取 API key
```

**修复**：直接设置加密字段
```python
# 修复后
kwargs = {"name": provider.name}
provider_instance = provider_class(**kwargs)
provider_instance.api_key_enc = provider.api_key_enc  # 直接设置加密字段
```

**影响**：
- 原始 Letta 和 Memos 都受影响
- 导致所有 Provider 的模型同步失败（使用需要认证的 API 时）

---

## 8. 总结

| 变更类型 | 数量 | 说明 |
|----------|------|------|
| 移除的查询参数 | 2 | `provider_category` 在 providers 和 llms API |
| 移除的内部参数 | 1 | `is_byok` 在 create_provider_async |
| 移除的方法 | 3 | `sync_base_providers`, `_sync_provider_models_async`, `get_enabled_providers_async` |
| 移除的常量 | 1 | `PROVIDER_ORDER` |
| Embedding 获取方式 | 1 | 硬编码 → 动态获取（API 接口无变化） |
| **Bug 修复** | 2 | **模型同步未提交、API 认证失败** |

**影响评估**:
- 破坏性变更仅影响使用 `provider_category` 参数的客户端
- 核心功能（创建、删除、查询 Provider）的 API 调用方式保持不变
- 前端只需移除 `provider_category` 相关的筛选逻辑
- Embedding 模型列表更准确，不会显示幽灵模型
- **Bug 修复确保了模型同步功能正常工作**

---

**文档版本**: v1.2
**最后更新**: 2026-01-14
**作者**: Claude (Opus 4.5)
**状态**: 已实施 + Bug 修复
