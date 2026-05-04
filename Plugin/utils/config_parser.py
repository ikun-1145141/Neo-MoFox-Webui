"""配置解析器工具类。

提供 TOML 配置文件读写、Schema 提取、数据合并等功能。
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal, get_args, get_origin

from pydantic_core import PydanticUndefined

from src.kernel.config import ConfigBase, SectionBase
from src.kernel.config.core import _render_toml_with_signature
from src.app.plugin_system.api.log_api import get_logger

from .config_types import (
    FieldSchema,
    SectionSchema,
    EnhancedConfigResponse,
)

logger = get_logger("config_parser")


class ConfigParser:
    """配置解析器工具类。

    提供静态方法进行配置文件的读取、写入、Schema 提取和数据合并。
    """

    @staticmethod
    def read_toml(path: str | Path) -> dict[str, Any]:
        """读取 TOML 文件。

        Args:
            path: 文件路径

        Returns:
            TOML 数据字典

        Raises:
            FileNotFoundError: 文件不存在
            tomllib.TOMLDecodeError: TOML 解析失败
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")

        with path.open("rb") as f:
            return tomllib.load(f)

    @staticmethod
    def write_toml(
        path: str | Path,
        config_class: type[ConfigBase],
        data: dict[str, Any],
    ) -> None:
        """将配置数据写入 TOML 文件。

        使用 ConfigBase.load(auto_update=True) 触发签名回写以保留注释。

        Args:
            path: 文件路径
            config_class: 配置类
            data: 配置数据字典

        Raises:
            ValueError: 数据验证失败
            OSError: 文件写入失败
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # 先验证数据
        try:
            config_class.model_validate(data)
        except Exception as e:
            raise ValueError(f"配置数据验证失败: {e}")

        # 使用 Neo-MoFox 内置的 TOML 渲染函数生成带注释的配置文件
        try:
            toml_content = _render_toml_with_signature(config_class, data)
            path.write_text(toml_content, encoding="utf-8")
            logger.info(f"配置文件已写入: {path}")
        except Exception as e:
            raise OSError(f"写入配置文件失败: {e}")

    @staticmethod
    def extract_schema(config_class: type[ConfigBase]) -> list[SectionSchema]:
        """从配置类提取 Schema。

        Args:
            config_class: 配置类（ConfigBase 子类）

        Returns:
            配置节 Schema 列表（按 order 排序）
        """
        sections: list[SectionSchema] = []

        for field_name, model_field in config_class.model_fields.items():
            # 获取节模型
            section_model, is_list = ConfigParser._get_section_model(model_field.annotation)
            if section_model is None:
                continue

            # 获取节元数据
            section_name = getattr(
                section_model, "__config_section_name__", field_name
            )
            section_title = getattr(section_model, "__config_section_title__", None)
            section_description = getattr(
                section_model, "__config_section_description__", None
            )
            section_tag = getattr(section_model, "__config_section_tag__", None)

            # 提取字段 Schema
            fields: list[FieldSchema] = []
            for sub_field_name, sub_model_field in section_model.model_fields.items():
                field_schema = ConfigParser._extract_field_schema(
                    sub_field_name, sub_model_field
                )
                fields.append(field_schema)

            sections.append(
                SectionSchema(
                    name=section_name,
                    title=section_title,
                    description=section_description,
                    tag=section_tag,
                    fields=fields,
                )
            )

        return sections

    @staticmethod
    def _get_section_model(
        annotation: Any,
    ) -> tuple[type[SectionBase] | None, bool]:
        """从类型注解提取节模型。

        Returns:
            (节模型, 是否为列表)
        """
        if isinstance(annotation, type) and issubclass(annotation, SectionBase):
            return annotation, False

        origin = get_origin(annotation)
        if origin is list:
            args = get_args(annotation)
            if args:
                item = args[0]
                if isinstance(item, type) and issubclass(item, SectionBase):
                    return item, True

        return None, False

    @staticmethod
    def _extract_field_schema(
        field_name: str,
        model_field: Any,
    ) -> FieldSchema:
        """从 Pydantic 字段提取 Schema。

        Args:
            field_name: 字段名
            model_field: Pydantic FieldInfo

        Returns:
            字段 Schema
        """
        # 获取字段类型
        field_type = ConfigParser._get_type_string(model_field.annotation)

        # 获取默认值
        default_value = None
        if model_field.default is not PydanticUndefined:
            default_value = model_field.default
        elif model_field.default_factory:
            try:
                default_value = model_field.default_factory()
            except Exception:
                pass

        # 获取 json_schema_extra 中的 UI 属性
        extra = model_field.json_schema_extra or {}
        literal_choices = ConfigParser._get_literal_choices(model_field.annotation)
        choices = extra.get("choices") or literal_choices
        input_type = extra.get("input_type") or ("select" if choices else "text")

        # 构建 FieldSchema
        return FieldSchema(
            key=field_name,
            label=extra.get("label") or field_name,
            description=model_field.description or "",
            type=field_type,
            default=default_value,
            input_type=input_type,
            tag=extra.get("tag"),
            placeholder=extra.get("placeholder"),
            hint=extra.get("hint"),
            hidden=extra.get("hidden", False),
            disabled=extra.get("disabled", False),
            # 验证约束
            ge=getattr(model_field, "ge", None),
            le=getattr(model_field, "le", None),
            gt=getattr(model_field, "gt", None),
            lt=getattr(model_field, "lt", None),
            min_length=getattr(model_field, "min_length", None),
            max_length=getattr(model_field, "max_length", None),
            pattern=getattr(model_field, "pattern", None),
            # 控件特定
            choices=choices,
            rows=extra.get("rows"),
            step=extra.get("step"),
            # 列表配置
            item_type=extra.get("item_type"),
            item_fields=extra.get("item_fields"),
            min_items=extra.get("min_items"),
            max_items=extra.get("max_items"),
            # 条件显示
            depends_on=extra.get("depends_on"),
            depends_value=extra.get("depends_value"),
        )

    @staticmethod
    def _get_literal_choices(annotation: Any) -> list[Any] | None:
        """Extract select choices from Literal annotations."""
        if get_origin(annotation) is Literal:
            return list(get_args(annotation))
        return None

    @staticmethod
    def _get_type_string(annotation: Any) -> str:
        """获取类型字符串表示。

        Args:
            annotation: 类型注解

        Returns:
            类型字符串，如 "str", "int", "list[str]"
        """
        if hasattr(annotation, "__name__"):
            return annotation.__name__

        origin = get_origin(annotation)
        if origin is not None:
            args = get_args(annotation)
            if args:
                arg_strs = [ConfigParser._get_type_string(arg) for arg in args]
                origin_name = getattr(origin, "__name__", str(origin))
                return f"{origin_name}[{', '.join(arg_strs)}]"
            return getattr(origin, "__name__", str(origin))

        return str(annotation)

    @staticmethod
    def build_enhanced_response(
        config_type: str,
        config_class: type[ConfigBase],
        data: dict[str, Any],
        config_path: str,
        config_name: str | None = None,
        plugin_name: str | None = None,
    ) -> EnhancedConfigResponse:
        """构建增强配置响应。

        Args:
            config_type: 配置类型（"bot", "model", "plugin"）
            config_class: 配置类
            data: 配置数据
            config_path: 配置文件路径
            config_name: 配置名称（不填则使用 config_type 生成）
            plugin_name: 插件名（仅 plugin 类型）

        Returns:
            增强配置响应
        """
        sections = ConfigParser.extract_schema(config_class)

        # 生成默认 config_name
        if not config_name:
            name_map = {"bot": "机器人配置", "model": "模型配置", "plugin": "插件配置"}
            config_name = name_map.get(config_type, config_type)

        return EnhancedConfigResponse(
            config_type=config_type,  # type: ignore
            config_name=config_name,
            config_path=config_path,
            plugin_name=plugin_name,
            schema=sections,
            data=data,
        )

    @staticmethod
    def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        """深度合并两个字典。

        patch 中的值会覆盖 base 中的值，支持嵌套字典的递归合并。

        Args:
            base: 基础字典
            patch: 要合并的补丁字典

        Returns:
            合并后的字典
        """
        result = base.copy()

        for key, value in patch.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                result[key] = ConfigParser.deep_merge(result[key], value)
            else:
                # 直接覆盖
                result[key] = value

        return result
