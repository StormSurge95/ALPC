from Game import Game
from database.Database import Database
import asyncio
import aiohttp
import pymongo
import ujson

async def main():
    async with aiohttp.ClientSession() as session:
        await Game.loginJSONFile(session, '.\credentials.json')
        await Game.getGData(session, True, True)
        await Game.startObserver(session, 'US', 'I')
    #file = open('.\credentials.json')
    #content = file.read()
    #file.close()
    #obj = ujson.loads(content)
    #uri = obj['mongo']
    #myclient = Database.connect(uri)
    #mydb = myclient['alclient']
    #print(await mydb.list_collection_names())

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())