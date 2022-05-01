import aiohttp
import asyncio
import logging
import sys
import ALPC as AL

logging.root.setLevel(logging.INFO)

async def main():
    async with aiohttp.ClientSession() as session:
        print('Logging in...')
        await AL.Game.loginJSONFile(session, '..\credentials.json')
        print('Successfully logged in!')
        print('Getting G Data...')
        await AL.Game.getGData(session, True, True)
        print('Obtained G Data!')
        print('Preparing pathfinder...')
        await AL.Pathfinder.prepare(AL.Game.G)
        print('Pathfinder prepared!')
        print('Starting character...')
        char = await AL.Game.startCharacter(session, 'WarriorSurge', 'US', 'I')
        print('Moving to main...')
        await char.smartMove('main')
        print('Moving to halloween...')
        await char.smartMove('halloween')
        print('Moving to desertland...')
        await char.smartMove('desertland')
        print('Returning to main...')
        await char.smartMove('main')
        print('Disconnecting...')
        await char.disconnect()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())