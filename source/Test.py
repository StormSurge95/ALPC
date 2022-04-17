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
        #await Game.startObserver(session, 'US', 'III')
        char = await Game.startCharacter(session, 'StormSurge', 'US', 'III')
        #print(char.speed)
        #pprint(await Pathfinder.getPath(char, { 'map': 'halloween', 'x': 0, 'y': 0 }))
        #print('distance:', Pathfinder.doorDistance({'x': char.x, 'y': char.y}, Game.G['maps']['main']['doors'][9]))
        #pprint(Pathfinder.graph.vs[0].attributes())
        await asyncio.sleep(10)
        await char.smartMove('halloween')
        await asyncio.sleep(5)
        await char.smartMove('main')
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