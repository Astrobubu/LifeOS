import aiohttp
import asyncio
import os
from .base_tool import BaseTool, ToolResult


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for information"
    
    def __init__(self):
        self.serper_key = os.getenv("SERPER_API_KEY")
    
    def get_function_schemas(self) -> list[dict]:
        return [
            self._make_schema(
                name="web_search",
                description="Search the web for information about companies, people, contact details, websites, etc. Returns titles, URLs, and snippets.",
                parameters={
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Maximum number of results (default 5)"}
                },
                required=["query"]
            ),
        ]
    
    async def execute(self, function_name: str, arguments: dict) -> ToolResult:
        try:
            if function_name == "web_search":
                return await self._web_search(**arguments)
            else:
                return ToolResult(success=False, error=f"Unknown function: {function_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _web_search(self, query: str, max_results: int = 5) -> ToolResult:
        """Search using Serper.dev API (free tier: 2500/month)"""
        
        if not self.serper_key:
            return ToolResult(
                success=False, 
                error="Web search unavailable. Ask user for contact info directly, or set SERPER_API_KEY in .env (free at serper.dev)"
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://google.serper.dev/search",
                    json={"q": query, "num": max_results},
                    headers={
                        "X-API-KEY": self.serper_key,
                        "Content-Type": "application/json"
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 401:
                        return ToolResult(success=False, error="Invalid SERPER_API_KEY")
                    if resp.status != 200:
                        return ToolResult(success=False, error=f"Search failed: {resp.status}")
                    
                    data = await resp.json()
            
            # Parse organic results
            results = data.get("organic", [])[:max_results]
            
            if not results:
                return ToolResult(success=True, data="No results found for this query")
            
            # Format results nicely
            formatted = []
            for r in results:
                title = r.get("title", "")
                url = r.get("link", "")
                snippet = r.get("snippet", "")
                formatted.append(f"**{title}**\n{url}\n{snippet}\n")
            
            return ToolResult(success=True, data="\n".join(formatted))
            
        except asyncio.TimeoutError:
            return ToolResult(success=False, error="Search timed out")
        except Exception as e:
            return ToolResult(success=False, error=f"Search error: {str(e)}")
