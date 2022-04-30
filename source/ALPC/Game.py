import aiohttp
import ujson
import re
import logging
import logging.config
import sys
from .Observer import Observer
from .Character import Character
from .PingCompensatedCharacter import PingCompensatedCharacter

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(fmt='%(levelname)s - %(name)s - %(asctime)s - %(funcName)s: %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(handler)

class Game:
    loggedIn: bool = False

    servers: dict = {}
    characters: dict = {}

    G: dict = {}
    version: int = 0

    @staticmethod
    async def deleteMail(session: aiohttp.ClientSession, mailID: str):
        if not Game.loggedIn:
            logger.error('You must login first.')
            raise Exception()
        params = {}
        params['method'] = 'delete_mail'
        params['arguments'] = ujson.encode({'mid': mailID}, ensure_ascii=False, encode_html_chars=True, escape_forward_slashes=False)
        async with session.post('http://adventure.land/api/delete_mail', data=params) as response:
            data = ujson.loads(await response.text())[0]
            if data['message'] == 'Mail deleted.':
                return True
            return False

    @staticmethod
    async def getGData(session: aiohttp.ClientSession, cache: bool = False, optimize: bool = False):
        if Game.G:
            return Game.G
        if not Game.version:
            await Game.getVersion(session)
        gFile = f'G_{Game.version}.json'
        try:
            file = open(gFile, mode='r', encoding='utf-8')
            content = file.read()
            Game.G = ujson.loads(content)
            file.close()
            return Game.G
        except Exception:
            logger.info("Updating 'G' data...")
            async with session.get('http://adventure.land/data.js') as response:
                if response.status == 200:
                    data = await response.text()
                    matches = re.match('var\s+G\s*=\s*(\{.+\});', data)
                    Game.G = ujson.loads(matches.group(1))
                    if optimize:
                        Game.G = Game.optimizeG(Game.G)
                    logger.info("Updated 'G' data!")
                    if cache:
                        file = open(gFile, mode='w')
                        file.write(ujson.dumps(Game.G))
                        file.close()
                    return Game.G
                else:
                    logger.error('Error fetching https://adventure.land/data.js')
                    logger.error(response)
                    raise Exception()

    @staticmethod
    async def getMail(session: aiohttp.ClientSession, all: bool = True):
        if not Game.loggedIn:
            logger.error('You must login first.')
            raise Exception()
        params = {}
        params['method'] = 'pull_mail'
        params['arguments'] = {}
        mail = []
        async with session.post('http://adventure.land/api/pull_mail', data=params) as response:
            while len(ujson.loads(await response.text())) > 0:
                mail.extend(ujson.loads(await response.text())[0]['mail'])
                if all and ujson.loads(await response.text())[0]['more']:
                    params['arguments'] = {"cursor": f"{ujson.loads(await response.text())[0].cursor}"}
                    response = await session.post('http://adventure.land/api/pull_mail', data=params)
                else:
                    break
        return mail

    @staticmethod
    async def getMerchants(session: aiohttp.ClientSession):
        pass

    @staticmethod
    async def getVersion(session: aiohttp.ClientSession):
        async with session.get('http://adventure.land/comm') as response:
            if response.status == 200:
                matches = re.search("\s*var\s+VERSION\s*=\s*'(\d+)", await response.text())
                Game.version = int(matches.group(1))
                return Game.version
            else:
                logger.error('Error fetching http://adventure.land/comm')
                logger.error(response)

    @staticmethod
    async def markMailAsRead(session: aiohttp.ClientSession, mailID: str):
        if not Game.loggedIn:
            logger.error('You must login first.')
            raise Exception()
        params = {}
        params['method'] = 'read_mail'
        params['arguments'] = ujson.encode({'mail': mailID}, ensure_ascii=False, encode_html_chars=True, escape_forward_slashes=False)
        async with session.post('http://adventure.land/api/read_mail', data=params) as response:
            data = ujson.loads(await response.text())
            print(data)

    @staticmethod
    async def login(session: aiohttp.ClientSession, email: str, password: str, mongo: str = ''):
        #if bool(mongo) and (not Database.connection):
            #await Database.connect(mongo)
        if not Game.loggedIn:
            logger.info('Logging in...')
            params = {}
            params['method'] = 'signup_or_login'
            params['arguments'] = ujson.encode({'email': email, 'only_login': True, 'password': password}, ensure_ascii=False, encode_html_chars=True, escape_forward_slashes=False)
            async with session.post('https://adventure.land/api/signup_or_login', data=params) as response:
                data = ujson.loads(await response.text())
                loginResult = None
                for datum in data:
                    if datum.get('message'):
                        loginResult = datum
                        break
                if loginResult and loginResult['message'] == 'Logged In!':
                    Game.loggedIn = True
                    logger.info('Logged in!')
                elif loginResult and loginResult.get('message'):
                    logger.error(str(loginResult['message']))
                    raise Exception(loginResult['message'])
                else:
                    logger.error(data)
        return await Game.updateServersAndCharacters(session)

    @staticmethod
    async def loginJSONFile(session: aiohttp.ClientSession, path: str):
        fileData = ''
        try:
            file = open(path, mode='r', encoding='utf-8')
            fileData = file.read()
            file.close()
        except Exception:
            logger.error(f'Could not locate \'{path}\'.')
        data = ujson.loads(fileData)

        try:
            await Game.login(session, data['email'], data['password'])
        except Exception:
            return False
        return True

    @staticmethod
    async def logoutEverywhere(session: aiohttp.ClientSession):
        if not Game.loggedIn:
            logger.error('You must login first.')
            raise Exception()
        params = {}
        params['method'] = 'logout_everywhere'
        response = await session.post('http://adventure.land/api/logout_everywhere', data=params)
        Game.loggedIn = False
        return await response.text()

    @staticmethod
    def optimizeG(g):
        del g['animations']
        del g['docs']
        del g['images']
        del g['imagesets']
        del g['sprites']
        del g['positions']
        del g['tilesets']

        for itemName in g['items']:
            gItem = g['items'][itemName]
            if 'cx' in gItem:
                del gItem['cx']
            if 'explanation' in gItem:
                del gItem['explanation']
            if 'trex' in gItem:
                del gItem['trex']
            if 'skin' in gItem:
                del gItem['skin']
            if 'skin_a' in gItem:
                del gItem['skin_a']
            if 'skin_c' in gItem:
                del gItem['skin_c']
            if 'skin_r' in gItem:
                del gItem['skin_r']
            if 'xcx' in gItem:
                del gItem['xcx']
            g['items'][itemName] = gItem

        for mapName in g['geometry']:
            gGeo = g['geometry'][mapName]
            if 'groups' in gGeo:
                del gGeo['groups']
            if 'placements' in gGeo:
                del gGeo['placements']
            if 'points' in gGeo:
                del gGeo['points']
            if 'rectangles' in gGeo:
                del gGeo['rectangles']
            if not 'x_lines' in gGeo or not 'y_lines' in gGeo:
                continue
            newMinX = sys.maxsize
            newMinY = sys.maxsize
            newMaxX = sys.maxsize * -1
            newMaxY = sys.maxsize * -1
            for [x, y1, y2] in gGeo['x_lines']:
                if x-1 < newMinX:
                    newMinX = x-1
                if y1-1 < newMinY:
                    newMinY = y1-1
                if y2-1 < newMinY:
                    newMinY = y2-1
                if x+1 > newMaxX:
                    newMaxX = x+1
                if y1+1 > newMaxY:
                    newMaxY = y1+1
                if y2+1 > newMaxY:
                    newMaxY = y2+1
            for [y, x1, x2] in gGeo['y_lines']:
                if x1-1 < newMinX:
                    newMinX = x1-1
                if x2-1 < newMinX:
                    newMinX = x2-1
                if y-1 < newMinY:
                    newMinY = y-1
                if x1+1 > newMaxX:
                    newMaxX = x1+1
                if x2+1 > newMaxX:
                    newMaxX = x2+1
                if y+1 > newMaxY:
                    newMaxY = y+1
            gGeo['min_x'] = newMinX
            gGeo['min_y'] = newMinY
            gGeo['max_x'] = newMaxX
            gGeo['max_y'] = newMaxY
            g['geometry'][mapName] = gGeo

        for monsterName in g['monsters']:
            gMonster = g['monsters'][monsterName]
            if 'explanation' in gMonster:
                del gMonster['explanation']
            if 'skin' in gMonster:
                del gMonster['skin']
            g['monsters'][monsterName] = gMonster

        return g

    @staticmethod
    async def startCharacter(session: aiohttp.ClientSession, cName: str, sRegion: str, sID: str, log: bool = False):
        if not Game.loggedIn:
            logger.error('You must login first.')
            raise Exception()
        if not bool(getattr(Game, 'characters', False)):
            await Game.updateServersAndCharacters(session)
        if not bool(getattr(Game, 'G')):
            await Game.getGData(session, True, True)
        userInfo = str(session.cookie_jar.filter_cookies('https://adventure.land')['auth'].value)
        userID = userInfo.split('-')[0]
        userAuth = userInfo.split('-')[1]
        if not Game.characters.get(cName):
            logger.error(f"You don't have a character with the name '{cName}'")
            raise Exception()
        characterID = Game.characters[cName]['id']

        player = None
        player = PingCompensatedCharacter(userID, userAuth, characterID, Game.G, Game.servers[sRegion][sID], log)
        await player.connect()
        return player
        #ctype = self.characters[cName].type
        #if ctype == 'mage':
        #    pass
        #elif ctype == 'merchant':
        #    pass
        #elif ctype == 'paladin':
        #    pass
        #elif ctype == 'priest':
        #    pass
        #elif ctype == 'ranger':
        #    pass
        #elif ctype == 'rogue':
        #    pass
        #elif ctype == 'warrior':
        #    pass
        #else:
        #    pass

    @staticmethod
    async def startMage(session: aiohttp.ClientSession, cName: str, sRegion: str, sID: str):
        pass

    @staticmethod
    async def startMerchant(session: aiohttp.ClientSession, cName: str, sRegion: str, sID: str):
        pass

    @staticmethod
    async def startPaladin(session: aiohttp.ClientSession, cName: str, sRegion: str, sID: str):
        pass

    @staticmethod
    async def startPriest(session: aiohttp.ClientSession, cName: str, sRegion: str, sID: str):
        pass

    @staticmethod
    async def startRanger(session: aiohttp.ClientSession, cName: str, sRegion: str, sID: str):
        pass

    @staticmethod
    async def startRogue(session: aiohttp.ClientSession, cName: str, sRegion: str, sID: str):
        pass

    @staticmethod
    async def startWarrior(session: aiohttp.ClientSession, cName: str, sRegion: str, sID: str):
        pass

    @staticmethod
    async def startObserver(session: aiohttp.ClientSession, region: str, id: str):
        if not Game.loggedIn:
            Game.logger.error('You must login first.')
            raise Exception()
        if not bool(Game.characters):
            await Game.updateServersAndCharacters(session)
        if not bool(Game.G):
            await Game.getGData()

        observer = Observer(Game.servers[region][id], Game.G)
        await observer.connect(True)
        return observer

    @staticmethod
    async def updateServersAndCharacters(session: aiohttp.ClientSession):
        if not Game.loggedIn:
            logger.error('You must login first.')
            raise Exception()
        params = {}
        params['method'] = 'servers_and_characters'
        params['arguments'] = {}
        async with session.post('http://adventure.land/api/servers_and_characters', data=params) as response:
            if response.status == 200:
                result = ujson.loads(await response.text())
                data = result[0]
                for serverData in data['servers']:
                    if not Game.servers.get(serverData['region']):
                        Game.servers[serverData['region']] = {}
                    Game.servers[serverData['region']][serverData['name']] = serverData
                for characterData in data['characters']:
                    Game.characters[characterData['name']] = characterData
                return True
            else:
                logger.error(response)
                return False