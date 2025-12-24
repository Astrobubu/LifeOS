"""
Web Research Sub-Agent - Autonomous agent for web search and browsing
"""
from .base_sub_agent import BaseSubAgent
from ..planning import AgentType
from tools.web_search_tool import WebSearchTool
from tools.browser_tool import BrowserTool


class WebResearchSubAgent(BaseSubAgent):
    """Autonomous web research agent with LLM reasoning + web tools."""
    
    agent_type = AgentType.WEB
    agent_name = "web"
    max_iterations = 8  # May need more for research
    
    def __init__(self):
        super().__init__()
        self.search_tool = WebSearchTool()
        self.browser_tool = BrowserTool()
    
    def get_system_prompt(self) -> str:
        return """You are the WEB RESEARCH sub-agent for LifeOS.

## Your Role
Search the web and gather information:
- Web search for queries
- Browse specific websites
- Summarize findings

## Research Strategy
1. Start with a search query
2. Review the results
3. Browse specific pages if needed
4. Synthesize findings

## Response Style
- Summarize findings concisely
- Cite sources when appropriate
- For weather/quick facts: Give direct answers
"""
    
    def get_tools(self) -> list[dict]:
        schemas = []
        schemas.extend(self.search_tool.get_function_schemas())
        schemas.extend(self.browser_tool.get_function_schemas())
        return schemas
    
    def get_tool_mapping(self) -> dict[str, str]:
        return {
            "web_search": "web_search",
            "browse_website": "browser",
        }
