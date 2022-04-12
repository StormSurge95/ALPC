from Game import Game
from Pathfinder import Pathfinder
#from database.Database import Database
#from Tools import Tools
import asyncio
import aiohttp
#import ujson
import logging
import sys
from pprint import pprint

#logger = logging.getLogger(__name__)
#handler = logging.StreamHandler(sys.stdout)
#handler.setLevel(logging.DEBUG)
#handler.setFormatter(logging.Formatter(fmt='%(levelname)s - %(name)s - %(asctime)s - %(funcName)s: %(message)s', datefmt='%H:%M:%S'))
#logger.addHandler(handler)

async def main():
    async with aiohttp.ClientSession() as session:
        await Game.loginJSONFile(session, '..\credentials.json')
        await Game.getGData(session, True, True)
        await Pathfinder.prepare(Game.G)
        #pprint(Pathfinder.getPath({'map': 'main', 'x': 0, 'y': 0}, {'map': 'halloween', 'x': 0, 'y': 0}))
        #await Game.startObserver(session, 'US', 'III')
        char = await Game.startCharacter(session, 'StormSurge', 'US', 'III')
        await asyncio.sleep(10)
        await char.move(10, 10)
        await asyncio.sleep(2)
        await char.move(10, -10)
        await asyncio.sleep(2)
        await char.move(-10, -10)
        await asyncio.sleep(2)
        await char.move(-10, 10)
        await asyncio.sleep(2)
        await char.move(0, 0)
        #await asyncio.sleep(5)
        #await char.enter('bank')
        # print('armorring?')
        # char.canCraft('armorring')
        # print('basketofeggs?')
        # char.canCraft('basketofeggs')
        # print('pickaxe?')
        # char.canCraft('pickaxe', True)
        # print('computer?')
        # char.canCraft('computer', True)
        await asyncio.sleep(10)
        await char.disconnect()
        await session.close()
    await session.close()
    pprint('Test Complete')

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())