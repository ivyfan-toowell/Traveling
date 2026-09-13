# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/1/6 14:24
@Author  : GGBOND
@File    : middleware.py
@Software: PyCharm
"""
import re
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from typing import Callable, Any
from app.core.state import TravelState
from app.core.store import get_user_memory_service
from app.utils.logger import app_logger


class StepConfigMiddleware(AgentMiddleware):
    """
    步骤配置中间件 - 根据 current_step 动态配置 Agent
    """

    def __init__(self, step_config: dict):
        """
        初始化中间件

        Args:
            step_config: 预加载的步骤配置字典
        """
        self._step_config = step_config

    def get_configured_tools(self) -> list[Any]:
        """Return every tool that a step may expose, de-duplicated by name.

        LangChain requires tools returned from middleware to be present in the
        tool list passed to ``create_agent``.  Keeping this list derived from
        the step configuration prevents the two registrations from drifting
        apart when a step gains a new tool.
        """
        tools_by_name: dict[str, Any] = {}
        for config in self._step_config.values():
            for tool in config.get("tools", []):
                name = getattr(tool, "name", None)
                if not name:
                    raise ValueError("步骤配置中存在没有 name 的工具")
                tools_by_name.setdefault(name, tool)
        return list(tools_by_name.values())

    @staticmethod
    def _render_prompt(prompt: str, state: dict[str, Any]) -> str:
        """Render the ``{state.path}`` placeholders used by step prompts."""
        placeholder = re.compile(r"\{([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\}")

        def replace(match: re.Match[str]) -> str:
            value: Any = state
            for part in match.group(1).split("."):
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = getattr(value, part, None)
                if value is None:
                    return "未设置"
            return str(value)

        return placeholder.sub(replace, prompt)


    async def awrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        """
        根据 current_step 动态配置 Agent
        """
        # 获取当前步骤
        state: TravelState = request.state
        state_dict = dict(state) if hasattr(state, "items") else {}
        current_step = state_dict.get("current_step", "requirement_collection")
        user_id = state_dict.get("user_id")

        app_logger.info(f"用户ID: {user_id}")
        app_logger.info(f"当前步骤: {current_step}")

        if current_step not in self._step_config:
            app_logger.error(f"❌ 未知步骤: {current_step}")
            raise ValueError(f"未知步骤: {current_step}")

        step_config = self._step_config[current_step]

        # ========== 验证前置依赖 ==========
        for required_field in step_config["requires"]:
            if required_field not in state_dict or state_dict[required_field] is None:
                error_msg = f"步骤 {current_step} 需要完整状态: {required_field} 未设置"
                app_logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)

        # ========== 动态填充提示词变量 ==========
        memory_prompt = ""
        if user_id:
            try:
                service = await get_user_memory_service()
                memory_prompt = await service.format_memory_for_prompt(user_id)
                if memory_prompt:
                    app_logger.info(f"已加载用户长期记忆：{user_id}")
                else:
                    app_logger.info(f"用户首次使用，暂无历史记忆：{user_id}")
            except Exception as e:
                app_logger.warning(f"⚠️ 加载长期记忆失败：{e}")

        try:
            state_dict["user_memory"] = memory_prompt
            system_prompt = self._render_prompt(step_config["prompt"], state_dict)

            if memory_prompt:
                system_prompt = f"{system_prompt}\n\n{memory_prompt}"

        except (KeyError, TypeError, ValueError) as e:
            app_logger.warning(f"提示词变量缺失: {e},使用原始模板")
            system_prompt = step_config["prompt"]

        # === 执行配置注入 ===
        modified_request = request.override(
            system_prompt=system_prompt,
            tools=step_config["tools"]
        )

        app_logger.info(f"✅已注入步骤配置: {len(step_config['tools'])} 个工具")

        return await handler(modified_request)


async def create_step_config_middleware() -> StepConfigMiddleware:
    """
    工厂函数：创建步骤配置中间件

    Returns:
        预加载配置的 StepConfigMiddleware 实例
    """
    from app.agents.handoffs.step_config import get_step_config

    step_config = await get_step_config()
    return StepConfigMiddleware(step_config)
