"""Actual MCP stdio handshake, tool discovery, and safe missing-auth call."""
import asyncio
import os
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    for key in ('LEETCODE_SESSION','LEETCODE_CSRF_TOKEN','LEETCODE_USERNAME'):
        env.pop(key, None)
    params = StdioServerParameters(command=sys.executable, args=[str(root / 'server.py')], cwd=str(root), env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            assert len(listed.tools) == 6
            result = await session.call_tool('account_status', {})
            assert result.isError
            assert 'Set LEETCODE_SESSION locally' in result.content[0].text
            print('PASS: stdio handshake, 6 tool schemas, missing-auth error')
asyncio.run(main())
