import aiohttp
import asyncio
import logging
import sys
import ALPC as AL

logging.root.setLevel(logging.DEBUG)

async def main():
    async with aiohttp.ClientSession() as session:
        await AL.Game.loginJSONFile(session, '.\credentials.json')
        await AL.Game.getGData(session, True, True)
        #await AL.Pathfinder.prepare(AL.Game.G)
        priest = await AL.Game.startCharacter(session, 'PriestSurge', 'US', 'III', True)
        await asyncio.sleep(10)
        await priest.disconnect()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())