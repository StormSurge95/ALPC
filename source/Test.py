# from datetime import datetime
# from pprint import pprint
# import aiohttp
# import asyncio
# import logging
# import sys
# import ALPC as AL
# logging.root.setLevel(logging.DEBUG)

# async def main():
#     if __name__ == '__main__':
#         async with aiohttp.ClientSession() as session:
#             await AL.Game.loginJSONFile(session, '.\credentials.json')
#             await AL.Game.getGData(session, True, True)
#             # start = datetime.utcnow().timestamp()
#             # await AL.Game.preparePathfinder()
#             # print("julia time:",datetime.utcnow().timestamp() - start)
#             start = datetime.utcnow().timestamp()
#             await AL.Pathfinder.prepare(AL.Game.G)
#             print("python time:",datetime.utcnow().timestamp() - start)
#             # observers = [await AL.Game.startObserver(session, 'US', 'I'), await AL.Game.startObserver(session, 'US', 'II'), await AL.Game.startObserver(session, 'US', 'III'), 
#             #             await AL.Game.startObserver(session, 'EU', 'I'), await AL.Game.startObserver(session, 'EU', 'II'), await AL.Game.startObserver(session, 'ASIA', 'I')]
#             # char = await AL.Game.startCharacter(session, 'StormSurge', 'US', 'III', False)
#             # await char.smartMove('main')
#             # await char.smartMove('halloween')
#             # await char.smartMove('winterland')
#             # await char.smartMove('desertland')
#             # await char.smartMove('main')
#             # await asyncio.sleep(30)
#             # for obs in observers:
#             #     await obs.socket.disconnect()
#             # await char.disconnect()

# if sys.platform == 'win32':
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# asyncio.run(main())

import numpy as np
from ALPC.Delaunator import Delaunator

points = np.random.randint(1, 1677.7215, size=(2000,2))
Delaunator(points)