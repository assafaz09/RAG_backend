import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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