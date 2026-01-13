# Ketta Provider 统一方案规划

**日期**: 2026-01-13
**目的**: 规划如何统一 Letta 的 Provider 系统，取消 Base/BYOK 模式区分

---

## 目录

- [1. 目标概述](#1-目标概述)
- [2. 当前问题分析](#2-当前问题分析)
- [3. 改造目标](#3-改造目标)
- [4. 改造方案](#4-改造方案)
- [5. 实施计划](#5-实施计划)
- [6. 模块化设计](#6-模块化设计)
- [7. 合并策略](#7-合并策略)

---

## 1. 目标概述

### 1.1 核心目标

将 Letta 的 Provider 系统从**双模式**（Base + BYOK）改造为**统一模式**，所有 Provider（包括官方 API 和第三方聚合平台）都通过前端 Klui 创建并存储在数据库中。

### 1.2 设计原则

1. **数据统一**: 所有 Provider 数据存储在数据库中
2. **配置灵活**: 支持任意 OpenAI 兼容的 API
3. **模块化**: 修改集中在最小范围，便于合并上游更新
4. **向后兼容**: 尽量保持 API 接口兼容
5. **可维护**: 清晰的代码结构，易于理解和修改

---

## 2. 当前问题分析

### 2.1 Base vs BYOK 模式对比

| 特性 | Base Provider | BYOK Provider |
|------|--------------|---------------|
| **API Key 来源** | 环境变量 (e.g., `OPENAI_API_KEY`) | 数据库（加密存储） |
| **创建方式** | 系统启动时从环境变量同步 | 用户通过 API 创建 |
| **organization_id** | NULL（全局可用） | 用户的组织 ID |
| **可删除性** | 不可删除 | 可软删除 |
| **Handle 格式** | `openai/gpt-4o` 或 `openai-proxy/gpt-4o` | `{provider_name}/gpt-4o` |

### 2.2 关键代码位置

| 文件 | 行号 | 功能 |
|------|------|------|
| `letta/schemas/enums.py` | 90-92 | `ProviderCategory` 定义 |
| `letta/schemas/providers/base.py` | 23-34 | `Provider` 基类 |
| `letta/schemas/providers/openai.py` | 153-157 | `openai-proxy` 硬编码 |
| `letta/orm/provider.py` | 28-29 | `organization_id` 可空 |
| `letta/services/provider_manager.py` | 27-144 | `create_provider_async` |
| `letta/services/provider_manager.py` | 241-303 | `list_providers_async` |
| `letta/services/provider_manager.py` | 553-614 | `sync_base_providers` |
| `letta/llm_api/llm_client_base.py` | 235-273 | `get_byok_overrides_async` |
| `letta/server/rest_api/routers/v1/providers.py` | 40-50 | `list_providers` API |

### 2.3 数据流分析

```
当前 API Key 获取流程:

LLMConfig
    │
    ├─> provider_category == ProviderCategory.byok
    │       │
    │       └─> ProviderManager.get_override_key_async(provider_name)
    │           └─> 查询数据库 (WHERE name = provider_name AND organization_id = org_id)
    │           └─> 解密 api_key_enc
    │           └─> 返回 API Key
    │
    └─> provider_category == ProviderCategory.base
            │
            └─> model_settings.openai_api_key / os.environ["OPENAI_API_KEY"]
```

---

## 3. 改造目标

### 3.1 功能目标

1. **取消 Base Provider 概念**
   - 所有 Provider 都是 BYOK 类型
   - 不再从环境变量同步 Provider

2. **统一 API Key 管理**
   - 所有 API Key 都存储在数据库
   - 前端 Klui 提供统一的 Provider 管理界面

3. **修复 `openai-proxy` 问题**
   - 使用用户自定义的 Provider 名称
   - 不再强制使用 `openai-proxy` 前缀

4. **硬删除 Provider**
   - Provider 删除时从数据库彻底移除
   - 允许重用 Provider 名称

### 3.2 非目标（暂不修改）

- Agent 执行流程
- 工具系统
- 记忆管理
- 其他 API 端点

---

## 4. 改造方案

### 4.1 架构变更

#### 4.1.1 取消 ProviderCategory

**修改前**:
```python
class ProviderCategory(str, Enum):
    base = "base"
    byok = "byok"
```

**修改后**:
```python
# 保留枚举但废弃 base 值，保持向后兼容
class ProviderCategory(str, Enum):
    byok = "byok"  # 所有 Provider 都是 BYOK 类型
    # base = "base"  # DEPRECATED - 不再使用
```

#### 4.1.2 统一 Provider 创建流程

**修改前**:
```python
# Base Provider: 从环境变量同步
await provider_manager.sync_base_providers(base_providers, actor)

# BYOK Provider: 用户创建
await provider_manager.create_provider_async(request, actor, is_byok=True)
```

**修改后**:
```python
# 所有 Provider 都通过 API 创建
await provider_manager.create_provider_async(request, actor)
```

### 4.2 核心修改清单

#### 4.2.1 Schema 层修改

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `schemas/enums.py` | 废弃 `ProviderCategory.base` | P1 |
| `schemas/providers/base.py` | 移除 `provider_category` 字段 | P2 |
| `schemas/providers/openai.py` | 移除 `openai-proxy` 硬编码 | P1 |

**示例修改** (`schemas/providers/openai.py`):

```python
# 修改前 (第 153-157 行)
if self.base_url != "https://api.openai.com/v1":
    handle = self.get_handle(model_name, base_name="openai-proxy")
else:
    handle = self.get_handle(model_name)

# 修改后
# 始终使用 Provider 的名称，不再有特殊处理
handle = self.get_handle(model_name)
```

#### 4.2.2 Service 层修改

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `services/provider_manager.py` | 简化 `create_provider_async` | P1 |
| `services/provider_manager.py` | 移除 `sync_base_providers` | P1 |
| `services/provider_manager.py` | 修改 `delete_provider_by_id_async` 为硬删除 | P1 |
| `services/provider_manager.py` | 简化 `list_providers_async` | P2 |
| `services/provider_manager.py` | 简化 `get_llm_config_from_handle` | P2 |

**示例修改** (`services/provider_manager.py`):

```python
# 修改前
async def create_provider_async(
    self,
    request: ProviderCreate,
    actor: PydanticUser,
    is_byok: bool = True  # 有区分
) -> PydanticProvider:
    # 复杂的 Base/BYOK 逻辑...

# 修改后
async def create_provider_async(
    self,
    request: ProviderCreate,
    actor: PydanticUser
) -> PydanticProvider:
    """创建 Provider - 所有 Provider 都是 BYOK 类型"""
    async with db_registry.async_session() as session:
        # 检查同名 Provider（包括软删除的）
        stmt = select(ProviderModel).where(
            and_(
                ProviderModel.name == request.name,
                ProviderModel.organization_id == actor.organization_id,
            )
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            if existing.is_deleted:
                # 恢复软删除的 Provider
                existing.is_deleted = False
            else:
                raise UniqueConstraintViolationError(...)

        # 创建新的 Provider
        provider_data = request.model_dump()
        provider_data["provider_category"] = ProviderCategory.byok
        provider_data["organization_id"] = actor.organization_id

        # 加密 API Key
        if request.api_key:
            provider_data["api_key_enc"] = await Secret.from_plaintext_async(request.api_key)

        provider = PydanticProvider(**provider_data)
        new_provider = ProviderModel(**provider.model_dump(to_orm=True))
        await new_provider.create_async(session, actor=actor)

        # 同步模型列表
        await self._sync_default_models_for_provider(new_provider.to_pydantic(), actor)

        return new_provider.to_pydantic()
```

#### 4.2.3 LLM Client 层修改

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `llm_api/llm_client_base.py` | 简化 `get_byok_overrides_async` | P1 |

**示例修改** (`llm_api/llm_client_base.py`):

```python
# 修改前
async def get_byok_overrides_async(self, llm_config: LLMConfig):
    api_key = None
    if llm_config.provider_category == ProviderCategory.byok:
        api_key = await ProviderManager().get_override_key_async(...)
    return api_key, None, None

# 修改后
async def get_api_key_async(self, llm_config: LLMConfig):
    """获取 API Key - 所有 Provider 都从数据库获取"""
    api_key = await ProviderManager().get_override_key_async(
        llm_config.provider_name,
        actor=self.actor
    )
    # 如果数据库中没有，尝试使用环境变量作为后备
    if not api_key:
        api_key = os.environ.get(f"{llm_config.provider_name.upper()}_API_KEY")
    return api_key, None, None
```

#### 4.2.4 API 层修改

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `server/rest_api/routers/v1/providers.py` | 简化 `list_providers` | P2 |

**示例修改** (`server/rest_api/routers/v1/providers.py`):

```python
# 修改前
@router.get("/", response_model=List[Provider])
async def list_providers(...):
    providers = await server.provider_manager.list_providers_async(
        provider_category=[ProviderCategory.byok],  # 只返回 BYOK
        ...
    )

# 修改后
@router.get("/", response_model=List[Provider])
async def list_providers(...):
    providers = await server.provider_manager.list_providers_async(
        actor=actor,
        ...
    )
    # 返回所有 Provider（不再有 Base/BYOK 区分）
```

### 4.3 数据库迁移

```sql
-- 迁移 1: 删除所有 Base Provider（如果有的话）
DELETE FROM providers WHERE provider_category = 'base';

-- 迁移 2: 确保所有记录的 organization_id 都有值
UPDATE providers SET organization_id = 'default-org-id'
WHERE organization_id IS NULL;

-- 迁移 3: 移除 provider_category 约束（可选，如果完全废弃）
-- ALTER TABLE providers DROP COLUMN provider_category;
```

---

## 5. 实施计划

### 5.1 Phase 1: 核心改造（Week 1）

**目标**: 实现最基本的统一 Provider 功能

1. **移除 `openai-proxy` 硬编码**
   - 文件: `schemas/providers/openai.py`
   - 修改: 使用 `self.name` 而不是 `"openai-proxy"`

2. **修改 Provider 创建逻辑**
   - 文件: `services/provider_manager.py`
   - 修改: 简化 `create_provider_async`

3. **修改 Provider 删除为硬删除**
   - 文件: `services/provider_manager.py`
   - 修改: `delete_provider_by_id_async`

4. **简化 API Key 获取**
   - 文件: `llm_api/llm_client_base.py`
   - 修改: `get_byok_overrides_async`

### 5.2 Phase 2: 完善功能（Week 2）

**目标**: 完善细节，确保功能完整

1. **移除 Base Provider 同步逻辑**
   - 文件: `services/provider_manager.py`
   - 修改: 移除 `sync_base_providers`

2. **更新 API 端点**
   - 文件: `server/rest_api/routers/v1/providers.py`
   - 修改: 简化 `list_providers`

3. **前端适配**
   - 文件: Klui 前端
   - 修改: 移除 handle 转换逻辑

### 5.3 Phase 3: 清理和优化（Week 3）

**目标**: 代码清理和性能优化

1. **移除废弃代码**
   - 删除 `ProviderCategory.base` 相关代码
   - 清理注释和文档

2. **数据库迁移**
   - 创建迁移脚本
   - 清理旧数据

3. **测试和文档**
   - 单元测试
   - 集成测试
   - 更新文档

---

## 6. 模块化设计

### 6.1 修改隔离策略

为了便于合并上游更新，将修改集中在以下模块：

```
ketta/  (自定义修改)
├── letta_modifications/        # 所有 Letta 修改集中在这里
│   ├── __init__.py
│   ├── providers/              # Provider 相关修改
│   │   ├── __init__.py
│   │   ├── openai_proxy_fix.py # openai-proxy 修复
│   │   └── unified_provider.py # 统一 Provider 逻辑
│   ├── llm_api/                # LLM API 修改
│   │   ├── __init__.py
│   │   └── api_key_override.py # API Key 获取修改
│   └── services/               # Service 修改
│       ├── __init__.py
│       └── provider_manager.py # Provider Manager 修改
│
└── letta/                      # 原始 Letta 代码（尽量不修改）
```

### 6.2 Monkey Patch 策略

对于无法通过继承解决的修改，使用 Monkey Patch：

```python
# ketta/letta_modifications/providers/openai_proxy_fix.py
from letta.schemas.providers import openai as letta_openai

def patched_list_llm_models_async(self):
    """修复 openai-proxy 硬编码问题"""
    # ... 原始逻辑 ...

    # 修改部分：始终使用 self.name
    handle = self.get_handle(model_name)

    # ... 其余逻辑 ...

def apply_patch():
    """应用补丁"""
    letta_openai.OpenAIProvider.list_llm_models_async = patched_list_llm_models_async
```

```python
# ketta/app.py (启动入口)
from ketta.letta_modifications.providers import openai_proxy_fix
from ketta.letta_modifications.services import provider_manager_patch

# 应用所有补丁
openai_proxy_fix.apply_patch()
provider_manager_patch.apply_patch()
```

### 6.3 配置驱动

通过配置文件控制行为，而不是硬编码修改：

```python
# ketta/config.py
class KettaConfig:
    """Ketta 特定配置"""

    # Provider 配置
    USE_UNIFIED_PROVIDER = True      # 是否使用统一 Provider 模式
    DELETE_PROVIDER_HARD = True      # 是否使用硬删除
    DISABLE_OPENAI_PROXY = True      # 是否禁用 openai-proxy

    # 后备配置
    FALLBACK_TO_ENV_VARS = True      # 是否允许环境变量后备
```

---

## 7. 合并策略

### 7.1 合并流程

```bash
# 1. 添加 Letta 作为 upstream remote
git remote add letta https://github.com/letta-ai/letta.git

# 2. 获取 Letta 最新代码
git fetch letta main

# 3. 查看差异
git log HEAD..letta/main --oneline

# 4. 选择性合并 Bug 修复
git cherry-pick <commit-hash>

# 5. 解决冲突
# - 保留 ketta/letta_modifications/ 的修改
# - 应用 letta/ 的更新

# 6. 测试
# - 运行测试套件
# - 手动测试核心功能
```

### 7.2 合并检查清单

- [ ] 检查 `letta/schemas/providers/` 的变更
  - [ ] `base.py` - 确保 Provider 基类兼容
  - [ ] `openai.py` - 确保补丁仍然有效

- [ ] 检查 `letta/services/provider_manager.py` 的变更
  - [ ] `create_provider_async` - 确保逻辑正确
  - [ ] `list_providers_async` - 确保返回正确

- [ ] 检查 `letta/llm_api/` 的变更
  - [ ] `llm_client_base.py` - 确保 API Key 获取正确

- [ ] 运行测试
  - [ ] 单元测试
  - [ ] 集成测试

### 7.3 冲突解决指南

**原则**: 优先保留 Ketta 的修改，Letta 的功能性更新通过 cherry-pick 合并

**示例冲突**:

```python
# Letta 上游更新
async def create_provider_async(
    self,
    request: ProviderCreate,
    actor: PydanticUser,
    is_byok: bool = True,  # 新增参数
) -> PydanticProvider:
    # 新功能...

# Ketta 修改
async def create_provider_async(
    self,
    request: ProviderCreate,
    actor: PydanticUser,  # 移除 is_byok 参数
) -> PydanticProvider:
    # 统一逻辑...

# 解决方案: 保留 Ketta 逻辑，审查 Letta 的新功能是否需要
```

---

## 8. 测试策略

### 8.1 单元测试

```python
# tests/test_unified_provider.py
class TestUnifiedProvider:
    """测试统一 Provider 功能"""

    async def test_create_provider_with_custom_name(self):
        """测试创建自定义名称的 Provider"""
        provider = await provider_manager.create_provider_async(
            ProviderCreate(
                name="MyCustomProvider",
                provider_type=ProviderType.openai,
                api_key="sk-test",
                base_url="https://api.custom.com/v1",
            ),
            actor=test_user,
        )

        assert provider.name == "MyCustomProvider"
        assert provider.provider_category == ProviderCategory.byok

    async def test_handle_uses_provider_name(self):
        """测试 Handle 使用 Provider 名称"""
        models = await provider.list_llm_models_async()
        assert models[0].handle == "MyCustomProvider/gpt-4o"

    async def test_hard_delete_provider(self):
        """测试硬删除 Provider"""
        await provider_manager.delete_provider_by_id_async(
            provider_id=provider.id,
            actor=test_user,
        )

        # 验证已完全删除
        with pytest.raises(NoResultFound):
            await provider_manager.get_provider_async(
                provider_id=provider.id,
                actor=test_user,
            )

    async def test_reuse_provider_name_after_deletion(self):
        """测试删除后可重用名称"""
        # 创建 Provider
        p1 = await provider_manager.create_provider_async(..., name="TestProvider")

        # 删除
        await provider_manager.delete_provider_by_id_async(p1.id, ...)

        # 重用名称创建
        p2 = await provider_manager.create_provider_async(..., name="TestProvider")

        assert p2.id != p1.id
```

### 8.2 集成测试

```python
# tests/integration/test_agent_with_custom_provider.py
class TestAgentWithCustomProvider:
    """测试使用自定义 Provider 的 Agent"""

    async def test_create_agent_with_custom_provider(self):
        """测试使用自定义 Provider 创建 Agent"""
        # 1. 创建自定义 Provider
        provider = await provider_manager.create_provider_async(
            ProviderCreate(
                name="CustomOpenAI",
                provider_type=ProviderType.openai,
                api_key=os.environ["OPENAI_API_KEY"],
                base_url="https://api.openai.com/v1",
            ),
            actor=test_user,
        )

        # 2. 创建 Agent
        agent = await agent_manager.create_agent_async(
            AgentCreate(
                name="TestAgent",
                model="CustomOpenAI/gpt-4o",  # 使用自定义 Provider
                ...
            ),
            actor=test_user,
        )

        # 3. 发送消息
        response = await agent.step(
            input_messages=[MessageCreate(role="user", content="Hello")],
            actor=test_user,
        )

        assert response.messages
```

---

## 9. 前端适配

### 9.1 Klui 修改

**文件**: `klui/lib/core/models/create_agent_request.dart`

**修改前**:
```dart
String _getCorrectLLMHandle() {
  // OpenAI-compatible API with custom base URL
  if (llmModel.providerType == 'openai' &&
      llmModel.modelEndpoint != 'https://api.openai.com/v1') {
    return 'openai-proxy/${modelName}';
  }
  return llmModel.handle;
}
```

**修改后**:
```dart
String _getCorrectLLMHandle() {
  // Ketta: 直接使用原始 handle，不再需要转换
  return llmModel.handle;
}
```

### 9.2 Provider 管理 UI

Klui 的 Provider 管理界面需要支持：

1. **创建任意 Provider**
   - 支持所有 Provider 类型
   - 自定义 base_url
   - API Key 加密存储

2. **删除 Provider**
   - 硬删除
   - 立即生效

3. **测试 Provider**
   - 验证 API Key
   - 查看可用模型

---

## 10. 风险和缓解措施

### 10.1 风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 上游 API 变化导致冲突 | 高 | 中 | 定期同步，及时适配 |
| 破坏现有功能 | 中 | 低 | 完整测试套件 |
| 性能下降 | 低 | 低 | 性能基准测试 |
| 数据迁移失败 | 高 | 中 | 迁移脚本，回滚方案 |

### 10.2 回滚方案

```bash
# 如果改造失败，回滚到 Letta 原始版本
git checkout letta-main
git apply ketta_patches.diff  # 重新应用补丁
```

---

## 11. 总结

本方案通过以下核心修改实现 Provider 系统统一：

1. **取消 Base/BYOK 区分** - 所有 Provider 都通过 API 创建并存储在数据库
2. **修复 `openai-proxy` 问题** - 使用用户自定义的 Provider 名称
3. **硬删除 Provider** - 允许重用名称，保持数据库清洁
4. **模块化修改** - 修改集中在最小范围，便于合并上游更新

这些修改将使 Ketta 成为一个真正的开源 AI Agent 平台，没有平台锁定，完全由用户控制。

---

**文档版本**: v1.0
**最后更新**: 2026-01-13
**作者**: Claude (Opus 4.5)
**状态**: 待评审
