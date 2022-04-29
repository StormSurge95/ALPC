from datetime import datetime, timedelta
from Game import Game
from Pathfinder import Pathfinder
#from database.Database import Database
#from Tools import Tools
import asyncio
import aiohttp
#import ujson
import logging
from pprint import pprint

#logger = logging.getLogger(__name__)
#handler = logging.StreamHandler()
#handler.setLevel(logging.DEBUG)
#handler.setFormatter(logging.Formatter(fmt='%(levelname)s - %(name)s - %(asctime)s - %(funcName)s: %(message)s', datefmt='%H:%M:%S'))
#logger.addHandler(handler)
logging.root.setLevel(logging.DEBUG)

async def main():
    async with aiohttp.ClientSession() as session:
        #pprint(datetime.now())
        #pprint(datetime.now() + timedelta(milliseconds=1000))
        await Game.loginJSONFile(session, '..\credentials.json')
        await Game.getGData(session, True, True)
        #await Pathfinder.prepare(Game.G)
        #await Game.startObserver(session, 'US', 'III')
        warrior = await Game.startCharacter(session, 'WarriorSurge', 'US', 'I', False)
        #ranger = await Game.startCharacter(session, 'RangerSurge', 'US', 'III')
        #priest = await Game.startCharacter(session, 'PriestSurge', 'US', 'III')
        await asyncio.sleep(10)
        #await warrior.smartMove('bank')
        #await asyncio.sleep(5)
        pprint('Test Running...')
        #pprint(warrior.bank)
        #await ranger.smartMove('main')
        #await priest.smartMove('main')
        await asyncio.sleep(10)
        await warrior.disconnect()
        #await ranger.disconnect()
        #await priest.disconnect()
    pprint('Test Complete')

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())