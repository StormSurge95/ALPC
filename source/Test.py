from Game import Game
from database.Database import Database
from Tools import Tools
import asyncio
import aiohttp
import pymongo
import ujson
import logging
import logging.config
import sys

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(fmt='%(levelname)s - %(name)s - %(asctime)s - %(funcName)s: %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(handler)

async def main():
    async with aiohttp.ClientSession() as session:
        await Game.loginJSONFile(session, '..\credentials.json')
        await Game.getGData(session, True, True)
        logger.info('starting Observer')
        #await Game.startObserver(session, 'US', 'III')
        char = await Game.startCharacter(session, 'StormSurge', 'US', 'III')
        await asyncio.sleep(10)
        await char.disconnect()
        await session.close()
    print('Test Complete')

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())