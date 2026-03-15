import asyncio
import json
from typing import Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def discover_mcp_tools(config: dict) -> Dict[str, Any]:
    """
    מגלה את כל הכלים הזמינים ב-MCP server.
    מחזיר מילון: {tool_name: {description, schema, server_config}}
    """
    server_params = StdioServerParameters(
        command=config.get('command', ''),
        args=config.get('args', []),
        env=config.get('env', {})
    )
    
    tools = {}
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 🔥 גילוי כל הכלים הזמינים
                tools_response = await session.list_tools()
                
                for tool in tools_response.tools:
                    tools[tool.name] = {
                        "description": tool.description,
                        "schema": tool.inputSchema,
                        "server_config": config
                    }
                    
    except Exception as e:
        print(f"Error discovering MCP tools: {e}")
        # אם לא הצלחנו לגלות, נחזיר כלי דיפולטיבי אחד
        if config.get('main_tool'):
            tools[config['main_tool']] = {
                "description": f"Main tool: {config['main_tool']}",
                "schema": {"type": "object", "properties": {}},
                "server_config": config
            }
    
    return tools


async def run_mcp_tool(command: str, args: list, env: dict, tool_name: str, tool_args: dict):
    # הגדרת השרת לפי ה-JSON שהתקבל מהמשתמש
    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=env
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # קריאה לכלי הספציפי שהסוכן בחר
            result = await session.call_tool(tool_name, tool_args)
            return result.content