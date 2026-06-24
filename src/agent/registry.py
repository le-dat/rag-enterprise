"""
Tool registry — auto-discovers all LangChain tools defined in src.agent.tools.

Adding a new tool:
    1. Create a new file under src/agent/tools/ (e.g. finance.py)
    2. Define and export a @tool-decorated function
    3. Add the function name to __all__ in src/agent/tools/__init__.py
    4. Done — no changes needed in graph.py or here.
"""
import logging
import importlib
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

_TOOLS_MODULE = "src.agent.tools"


def get_tools() -> list[BaseTool]:
    """
    Import the tools package and return all exported tool instances.

    Tools are defined by the __all__ list in src/agent/tools/__init__.py.
    """
    module = importlib.import_module(_TOOLS_MODULE)
    exported: list[str] = getattr(module, "__all__", [])

    tools: list[BaseTool] = []
    for name in exported:
        obj = getattr(module, name, None)
        if obj is None:
            logger.warning("registry: '%s' listed in __all__ but not found in module", name)
            continue
        if not isinstance(obj, BaseTool):
            logger.warning("registry: '%s' is not a BaseTool instance, skipping", name)
            continue
        tools.append(obj)

    logger.info("registry: loaded %d tools: %s", len(tools), [t.name for t in tools])
    return tools
