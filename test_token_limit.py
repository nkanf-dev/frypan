import asyncio
import os
import sys
sys.path.append('.')
from sharkagent import run_tshark

async def test_large_output():
    # Test with a command that might produce large output
    result = await run_tshark(None, '-h')
    print('Help command output length:', len(result))
    print('First 200 chars:', result[:200])
    print('Last 200 chars:', result[-200:])

if __name__ == '__main__':
    asyncio.run(test_large_output())