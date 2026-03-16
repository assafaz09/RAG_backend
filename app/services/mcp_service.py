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
    """
    הפעלת כלי MCP עם תמיכה ב-Windows
    """
    try:
        # בדיקה אם זו פקודת Windows פשוטה
        if command in ["cmd", "echo", "type"] or command.endswith(".exe"):
            # הפעלה ישירה של פקודות Windows
            import subprocess
            
            if command == "cmd" and "/c" in args:
                # פקודת cmd עם פרמטרים
                full_command = [command] + args
            elif command == "echo":
                # פקודת echo פשוטה
                message = tool_args.get("query", "") or tool_args.get("message", "")
                return [{"text": f"Echo: {message}"}]
            else:
                # פקודה אחרת
                full_command = [command] + args
            
            try:
                result = subprocess.run(
                    full_command,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env
                )
                return [{"text": result.stdout.strip()}]
            except subprocess.TimeoutExpired:
                return [{"text": "Command timed out"}]
            except Exception as e:
                return [{"text": f"Command error: {str(e)}"}]
        
        # הפעלה רגילה של MCP server
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
                
    except Exception as e:
        return [{"text": f"MCP Tool Error: {str(e)}"}]