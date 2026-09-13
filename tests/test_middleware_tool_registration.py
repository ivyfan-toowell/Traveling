from app.core.middleware import StepConfigMiddleware
from app.agents.handoffs.travel_agent import _deduplicate_tools


class DummyTool:
    def __init__(self, name: str):
        self.name = name


def test_every_step_tool_can_be_registered_on_base_agent():
    shared = DummyTool("shared")
    first = DummyTool("first")
    second = DummyTool("second")
    middleware = StepConfigMiddleware({
        "step_one": {"tools": [first, shared]},
        "step_two": {"tools": [second, shared]},
    })

    tools = _deduplicate_tools([
        *middleware.get_configured_tools(),
        DummyTool("base"),
    ])

    assert [tool.name for tool in tools] == ["first", "shared", "second", "base"]
