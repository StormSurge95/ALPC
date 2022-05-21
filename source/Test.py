from datetime import datetime
from pprint import pprint
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
        AL.Pathfinder.G = AL.Game.G
        await AL.Pathfinder.prepare(AL.Game.G)
        observers = [await AL.Game.startObserver(session, 'US', 'I'), await AL.Game.startObserver(session, 'US', 'II'), await AL.Game.startObserver(session, 'US', 'III'), 
                    await AL.Game.startObserver(session, 'EU', 'I'), await AL.Game.startObserver(session, 'EU', 'II'), await AL.Game.startObserver(session, 'ASIA', 'I')]
        char = await AL.Game.startCharacter(session, 'StormSurge', 'US', 'III', False)
        for obs in observers:
            await obs.socket.disconnect()
        await char.disconnect()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())