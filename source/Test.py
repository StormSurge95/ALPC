from datetime import datetime
from pprint import pprint
import aiohttp
import asyncio
import logging
import sys
import ALPC as AL
logging.root.setLevel(logging.DEBUG)

async def main():
    def intFn():
        print(datetime.utcnow().timestamp())
    inter = AL.Tools.setInterval(intFn, 2.5)
    await asyncio.sleep(10)
    AL.Tools.clearTimeout(inter)
    # async with aiohttp.ClientSession() as session:
    #     await AL.Game.loginJSONFile(session, '.\credentials.json')
    #     await AL.Game.getGData(session, True, True)
    #     AL.Pathfinder.G = AL.Game.G
    #     await AL.Pathfinder.prepare(AL.Game.G)
    #     observers = [await AL.Game.startObserver(session, 'US', 'I'), await AL.Game.startObserver(session, 'US', 'II'), await AL.Game.startObserver(session, 'US', 'III'), 
    #                 await AL.Game.startObserver(session, 'EU', 'I'), await AL.Game.startObserver(session, 'EU', 'II'), await AL.Game.startObserver(session, 'ASIA', 'I')]
    #     char = await AL.Game.startCharacter(session, 'StormSurge', 'US', 'III', False)
    #     # await asyncio.sleep(10)
    #     # print('smart moving to main...')
    #     # await char.smartMove('main')
    #     # print('smart moving to halloween...')
    #     # await char.smartMove('halloween')
    #     # print('smart moving to desertland...')
    #     # await char.smartMove('desertland')
    #     # print('smart moving to winterland...')
    #     # await char.smartMove('winterland')
    #     # print('smart moving back to main...')
    #     # await char.smartMove('main')
    #     # for p in char.players:
    #     #     player = char.players[p]
    #     #     if player.isNPC(): continue
    #     #     pprint(dir(player))
    #     #     break
    #     for obs in observers:
    #         await obs.socket.disconnect()
    #     await char.disconnect()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())