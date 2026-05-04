"""配置管理数据类型定义。

定义配置管理模块使用的所有 Pydantic 模型。
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class FieldSchema(BaseModel):
    """单个配置字段的 Schema 描述。

    用于前端动态渲染表单控件。

    Attributes:
        key: 字段名（Python 属性名）
        label: 显示标签（来自 Field.label，不填则用 key）
        description: 字段描述
        type: 类型字符串，如 "str"、"int"、"bool"、"float"、"list[str]"
        default: 默认值
        input_type: 控件类型：
            - "text": 单行文本输入
            - "password": 密码输入
            - "number": 数字输入
            - "switch": 开关
            - "slider": 滑块
            - "select": 下拉选择
            - "list": 列表编辑器
            - "textarea": 多行文本
            - "json": JSON 编辑器
            - "color": 颜色选择器
            - "file": 文件选择器
        tag: 预设标签（映射图标）
        placeholder: 占位符文本
        hint: 帮助提示
        order: 显示顺序
        hidden: 是否隐藏
        disabled: 是否只读
        ge: 大于等于约束（数字类型）
        le: 小于等于约束（数字类型）
        gt: 大于约束（数字类型）
        lt: 小于约束（数字类型）
        min_length: 最小长度约束（字符串/列表类型）
        max_length: 最大长度约束（字符串/列表类型）
        pattern: 正则表达式约束（字符串类型）
        choices: select 选项列表
        rows: textarea 行数
        step: number/slider 步进值
        item_type: 列表项类型（list 类型）
        item_fields: 列表项字段定义（复杂列表项）
        min_items: 列表最小项数
        max_items: 列表最大项数
        depends_on: 条件显示：依赖的字段名
        depends_value: 条件显示：依赖字段的值
    """

    key: str = Field(..., description="字段名")
    label: str = Field(..., description="显示标签")
    description: str = Field(default="", description="字段描述")
    type: str = Field(..., description="字段类型")
    default: Any = Field(default=None, description="默认值")
    input_type: str = Field(default="text", description="控件类型")
    tag: str | None = Field(default=None, description="预设标签")
    placeholder: str | None = Field(default=None, description="占位符")
    hint: str | None = Field(default=None, description="帮助提示")
    hidden: bool = Field(default=False, description="是否隐藏")
    disabled: bool = Field(default=False, description="是否只读")

    # 验证约束
    ge: float | None = Field(default=None, description="大于等于")
    le: float | None = Field(default=None, description="小于等于")
    gt: float | None = Field(default=None, description="大于")
    lt: float | None = Field(default=None, description="小于")
    min_length: int | None = Field(default=None, description="最小长度")
    max_length: int | None = Field(default=None, description="最大长度")
    pattern: str | None = Field(default=None, description="正则模式")

    # 控件特定
    choices: list[Any] | None = Field(default=None, description="选择项")
    rows: int | None = Field(default=None, description="文本行数")
    step: float | None = Field(default=None, description="步进值")

    # 列表配置
    item_type: str | None = Field(default=None, description="列表项类型")
    item_fields: dict[str, Any] | None = Field(default=None, description="列表项字段定义")
    min_items: int | None = Field(default=None, description="最小项数")
    max_items: int | None = Field(default=None, description="最大项数")

    # 条件显示
    depends_on: str | None = Field(default=None, description="依赖字段")
    depends_value: Any = Field(default=None, description="依赖值")


class SectionSchema(BaseModel):
    """一个配置节（[section]）的 Schema。

    Attributes:
        name: 节名称（TOML table key，如 "bot"、"chat"）
        title: 显示标题（来自 config_section(title=...)）
        description: 节描述
        tag: 预设标签
        order: 显示顺序
        is_list: 是否为列表类型（如 models、api_providers）
        fields: 本节包含的字段 Schema 列表
    """

    name: str = Field(..., description="节名称")
    title: str | None = Field(default=None, description="显示标题")
    description: str | None = Field(default=None, description="节描述")
    tag: str | None = Field(default=None, description="预设标签")
    is_list: bool = Field(default=False, description="是否为列表类型")
    fields: list[FieldSchema] = Field(default_factory=list, description="字段列表")


class EnhancedConfigResponse(BaseModel):
    """增强配置响应。

    包含配置的当前值（data）和渲染编辑器所需的 Schema（schema）。
    前端根据 schema 渲染表单，根据 data 填充初始值，
    编辑完成后将修改后的 data 通过写入接口回写。

    Attributes:
        config_type: 配置类型（"bot"、"model"、"plugin"）
        config_name: 配置名称（用于显示，如 "机器人配置"、"模型配置"）
        config_path: 配置文件路径（相对路径，如 "config/core.toml"）
        plugin_name: 插件名（仅 plugin 类型时有值）
        schema: 有序的配置节列表（含 Schema）
        data: 当前配置值（与 TOML 文件内容一致的字典）
    """

    config_type: Literal["bot", "model", "plugin"] = Field(..., description="配置类型")
    config_name: str = Field(..., description="配置名称")
    config_path: str = Field(..., description="配置文件路径")
    plugin_name: str | None = Field(default=None, description="插件名")
    schema: list[SectionSchema] = Field(default_factory=list, description="配置节列表")
    data: dict[str, Any] = Field(default_factory=dict, description="配置数据")


class FullWriteRequest(BaseModel):
    """全量写入请求（PUT）。

    用 data 完全替换配置文件的所有值。
    data 格式与 EnhancedConfigResponse.data 一致。

    Attributes:
        data: 完整的配置数据字典
    """

    data: dict[str, Any] = Field(..., description="完整配置数据")


class PatchWriteRequest(BaseModel):
    """增量写入请求（PATCH）。

    仅更新 data 中包含的字段，未出现的字段保持原值不变。
    data 格式与 EnhancedConfigResponse.data 一致，支持嵌套 dict 的深度合并。

    Attributes:
        data: 要更新的配置数据字典（部分）
    """

    data: dict[str, Any] = Field(..., description="部分配置数据")


# ===== 模型测试相关结构 =====


class ModelTestRequest(BaseModel):
    """模型测试请求。

    Attributes:
        provider_name: 提供商名称（对应 model.toml 中 api_providers[].name）
        model_name: 模型 name 字段（model.toml 中 models[].name）
        test_prompt: 测试用的提示词
        timeout: 超时时间（秒）
    """

    provider_name: str = Field(..., description="提供商名称")
    model_name: str = Field(..., description="模型名称")
    test_prompt: str = Field(default="你好", description="测试提示词")
    timeout: int = Field(default=15, description="超时时间")


class ModelTestResult(BaseModel):
    """模型测试结果。

    Attributes:
        success: 是否成功
        response_text: 模型返回的文本（成功时）
        latency_ms: 请求耗时（毫秒）
        error_message: 错误信息（失败时）
        model_identifier: 实际使用的 model_identifier
        provider_base_url: 使用的 base_url
    """

    success: bool = Field(..., description="是否成功")
    response_text: str | None = Field(default=None, description="响应文本")
    latency_ms: float | None = Field(default=None, description="耗时（毫秒）")
    error_message: str | None = Field(default=None, description="错误信息")
    model_identifier: str = Field(..., description="模型标识符")
    provider_base_url: str = Field(..., description="提供商 URL")


# ===== 插件配置相关结构 =====


class PluginConfigEntry(BaseModel):
    """可配置插件的摘要信息。

    Attributes:
        plugin_name: 插件名（config_api 中的 plugin_name）
        config_name: 配置文件名（不含 .toml）
        config_path: 配置文件路径（相对路径）
        config_description: 配置描述（来自 BaseConfig.config_description）
        is_loaded: 是否已被 ConfigManager 加载（运行时可用）
    """

    plugin_name: str = Field(..., description="插件名")
    config_name: str = Field(..., description="配置文件名")
    config_path: str = Field(..., description="配置文件路径")
    config_description: str = Field(default="", description="配置描述")
    is_loaded: bool = Field(default=False, description="是否已加载")
