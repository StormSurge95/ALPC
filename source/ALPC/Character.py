from ctypes import Union
from functools import reduce
import logging
from pprint import pprint
from urllib.parse import _NetlocResultMixinBytes
import pymongo
from .database import Database
from .Observer import Observer
from .Entity import Entity
from .Tools import Tools
from .Constants import Constants
from .Pathfinder import Pathfinder
from datetime import datetime
import asyncio
import re
import sys
import math

class Character(Observer):

    def __init__(self, userID, userAuth, characterID, g, serverData, log = False):
        self.achievements: dict = {}
        self.acx: dict = {}
        self.afk: str = ''
        self.age: int = 0
        self.apiercing: int = 0
        self.armor: int = 0
        self.attack: int = 0
        self.base_gold: dict[str, dict[str, int]] = {}
        self.blast: int = 0
        self.c: dict = {}
        self.cash: int = 0
        self.cc: int = 0
        self.characterID: str = characterID
        self.chests: dict = {}
        self.cid: int = 0
        self.controller: str = ''
        self.courage: int = 0
        self.crit: int = 0
        self.critdamage: int = 0
        self.ctype: str = ''
        self.cx: dict[str, str] = {}
        self.damage_type: str = ''
        self.dex: int = 0
        self.dreturn: int = 0
        self.emx: dict = {}
        self.esize: int = 0
        self.evasion: int = 0
        self.explosion: int = 0
        self.fear: int = 0
        self.firesistance: int = 0
        setattr(self, 'for', 0)
        self.frequency: float = 0.0
        self.friends: list = []
        self.fzresistance: int = 0
        self.going_x: int = 0
        self.going_y: int = 0
        self.gold: int = 0
        self.goldm: float = 0.0
        self.hp: int = 0
        self.id: str = ''
        setattr(self, 'in', '')
        self.info: dict = {}
        self.int: int = 0
        self.ipass: str = ''
        self.isize: int = 0
        self.items: list = []
        self.lastSmartMove: float = datetime.utcnow().timestamp()
        self.level: int = 0
        self.lifesteal: int = 0
        self.luckm: float = 0.0
        self.m: int = 0
        self.manasteal: int = 0
        self.map: str = ''
        self.max_hp: int = 0
        self.max_mp: int = 0
        self.max_xp: int = 0
        self.mcourage: int = 0
        self.moving: bool = False
        self.mp: int = 0
        self.mp_cost: int = 0
        self.mp_reduction: int = 0
        self.name: str = ''
        self.nextSkill: dict[str, float] = {}
        self.owner: str = userID
        self.partyData: dict = {}
        self.pcourage: int = 0
        self.pdps: int = 0
        self.pnresistance: int = 0
        self.q: dict = {}
        self.range: int = 0
        self.ready: bool = False
        self.reflection: int = 0
        self.resistance: int = 0
        self.rip: bool = False
        self.rpiercing: int = 0
        self.s: dict[str, dict[str, str | int | float]] = {}
        self.s_info: dict[str, dict[str, int | float | str | bool]] = {}
        self.skin: str = ''
        self.slots: dict[str, dict[str, str | int] | None] = {}
        self.smartMoving: dict = {}
        self.speed: int = 0
        self.stand: bool = False
        self.str: int = 0
        self.stun: int = 0
        self.targets: int = 0
        self.tax: float = 0.0
        self.timeouts: dict[str, asyncio.Task] = {}
        self.user: dict[str, int | list] = {'gold': 0}
        self.userAuth: str = userAuth
        self.vit: int = 0
        self.xcx: list = []
        self.xp: int = 0
        self.xpm: float = 0.0
        self.xrange: int = 0
        super().__init__(serverData, g, log=log)
        self.logger = logging.getLogger(self.name)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(fmt='%(levelname)s - %(name)s - %(asctime)s - %(funcName)s: %(message)s', datefmt='%H:%M:%S'))
        self.logger.addHandler(handler)
        return

    @property
    def bank(self) -> dict[str, int | list]:
        return self.user

    def __dir__(self):
        attNames = super().__dir__()
        attTypes = [type(getattr(self, name)) for name in attNames]
        ret = list(zip(attNames, attTypes))
        return ret

    async def updateLoop(self):
        if (not bool(self.socket)) or (not self.socket.connected) or (not self.ready):
            self.timeouts['updateLoop'] = Tools.setTimeout(self.updateLoop, Constants.UPDATE_POSITIONS_EVERY_S)
            return

        if (not hasattr(self, 'lastPositionUpdate')):
            self.updatePositions()
            self.timeouts['updateLoop'] = Tools.setTimeout(self.updateLoop, Constants.UPDATE_POSITIONS_EVERY_S)
            return

        if (hasattr(self, 'lastAllEntities')) and ((datetime.utcnow().timestamp() - self.lastAllEntities) > Constants.STALE_MONSTER_S):
            await self.requestEntitiesData()

        sSinceLastUpdate = (datetime.utcnow().timestamp() - self.lastPositionUpdate)
        if sSinceLastUpdate > Constants.UPDATE_POSITIONS_EVERY_S:
            self.updatePositions()
            self.timeouts['updateLoop'] = Tools.setTimeout(self.updateLoop, Constants.UPDATE_POSITIONS_EVERY_S)
            return
        else:
            self.timeouts['updateLoop'] = Tools.setTimeout(self.updateLoop, Constants.UPDATE_POSITIONS_EVERY_S - sSinceLastUpdate)
            return

    def parseCharacter(self, data):
        self.updatePositions()
        for datum in list(data):
            if datum == 'hitchhikers':
                for [event, dat] in data['hitchhikers'].items():
                    if event == 'game_response':
                        self.parseGameResponse(dat)
                    elif event == 'eval':
                        self.parseEval(dat)
            elif datum == 'entities':
                self.parseEntities(data[datum])
            elif datum == 'owner':
                pass
            elif datum == 'tp':
                pass
            elif datum == 'user' and data['user'] != None:
                self.user = data['user']

                if Database.connection != None:
                    updateData = {
                        'lastUpdated': datetime.utcnow().timestamp(),
                        'owner': self.owner,
                        **data['user']
                    }
                    Database.connection.ALPC.banks.update_one({ 'owner': self.owner }, { "$set": updateData }, upsert=True)
            else:
                setattr(self, datum, data[datum])
        self.name = data['id']
        if not hasattr(self, 'party'):
            self.partyData = None
        if self.damage_type == '' and hasattr(self, 'ctype'):
            self.damage_type = self.G['classes'][self.ctype]['damage_type']
        if Database.connection != None:
            key = f"{self.serverData['name']}{self.serverData['region']}{self.id}"
            nextUpdate = Database.nextUpdate.get(key)
            if nextUpdate == None or datetime.utcnow().timestamp() >= nextUpdate:
                updateData = {
                    'items': self.items,
                    'lastSeen': datetime.utcnow().timestamp(),
                    'map': self.map,
                    'name': self.id,
                    's': self.s,
                    'serverIdentifier': self.serverData['name'],
                    'serverRegion': self.serverData['region'],
                    'slots': self.slots,
                    'type': self.ctype,
                    'x': self.x,
                    'y': self.y
                }
                if hasattr(self, 'owner'): updateData['owner'] = self.owner
                Database.connection.ALPC.players.update_one({ 'name': self.id }, { "$set": updateData }, True)
                Database.nextUpdate[key] = datetime.utcnow().timestamp() + Constants.MONGO_UPDATE_S
        return

    def parseEntities(self, data):
        if hasattr(self, 'party'):
            for i in range(0, len(data['players'])):
                player = data['players'][i]
                partyPlayer = getattr(self, 'partyData', None).get('party', None).get(player.id, None)
                if not partyPlayer:
                    continue

                for key in partyPlayer.keys():
                    if key in player.keys():
                        partyPlayer[key] = player[key]
        for i in range(0, len(data['players'])):
            player = data['players'][i]
            if player['id'] == getattr(self, 'id', None):
                self.parseCharacter(player)
                data['players'] = data['players'][0:i] + data['players'][i+1:]
                break

        super().parseEntities(data)
        return

    def parseEval(self, data):
        skillReg = re.search("^skill_timeout\s*\(\s*['\"](.+?)['\"]\s*,?\s*(\d+\.?\d+?)?\s*\)", data['code'])
        if skillReg is not None:
            skill = skillReg.group(1)
            cooldown = None
            if skillReg.group(2):
                cooldown = float(skillReg.group(2)) / 1000
            if cooldown is not None:
                next = datetime.utcnow().timestamp() + cooldown
                self.setNextSkill(skill, next)
            return
        
        potReg = re.search("^pot_timeout\s*\(\s*(\d*\.?\d+)\s*\)", data['code'])
        if potReg is not None:
            cooldown = float(potReg.group(1)) / 1000
            next = datetime.utcnow().timestamp() + cooldown
            self.setNextSkill('regen_hp', next)
            self.setNextSkill('regen_mp', next)
            return

        uiMoveReg = re.search("^ui_move\s*\(\s*(-?\d*\.{0,1}\d+)\s*,\s*(-?\d*\.{0,1}\d+)\s*\)", data['code'])
        if uiMoveReg is not None:
            x = float(uiMoveReg.group(1))
            y = float(uiMoveReg.group(2))
            self.x = x
            self.y = y
            return

        print(f'Unhandled \'eval\': {str(data)}')
        return

    def parseGameResponse(self, data):
        if isinstance(data, dict):
            if data['response'] == 'cooldown':
                skill = data.get('skill', data.get('place', None))
                if skill is not None:
                    cooldown = data['ms']
                    self.setNextSkill(skill, datetime.utcnow().timestamp() + cooldown)
            elif Database.connection != None and data['response'] == 'defeated_by_a_monster':
                # we died lol
                Database.connection.ALPC.deaths.insert_one({
                    'cause': data['monster'],
                    'map': self.map,
                    'name': self.id,
                    'serverIdentifier': self.server['name'],
                    'serverRegion': self.server['region'],
                    'time': datetime.utcnow().timestamp(),
                    'x': self.x,
                    'y': self.y
                })
            elif data['response'] == 'ex_condition' and data['name'] in self.s:
                del self.s[data['name']]
            elif data['response'] == 'skill_success':
                cooldown = self.G['skills'][data['name']]['cooldown']
                if cooldown is not None:
                    self.setNextSkill(data['name'], datetime.utcnow().timestamp() + cooldown)
        elif isinstance(data, str):
            if data == 'resolve_skill':
                pass # ignore. We resolve our skills a different way than the vanilla client
        return

    def parseNewMap(self, data):
        setattr(self, 'going_x', data['x'])
        setattr(self, 'going_y', data['y'])
        setattr(self, 'in', data['in'])
        setattr(self, 'm', data['m'])
        setattr(self, 'moving', False)

        super().parseNewMap(data)
        return

    def parseQData(self, data: dict):
        if data.get('q', {}).get('upgrade') != None:
            self.q['upgrade'] = data['q']['upgrade']
        if data.get('q', {}).get('compound') != None:
            self.q['compound'] = data['q']['compound']
        return

    def setNextSkill(self, skill, next):
        self.nextSkill[skill] = next
        if self.G['skills'][skill].get('share') != None:
            self.nextSkill[self.G['skills'][skill]['share']] = next
        return

    def updatePositions(self):
        if getattr(self, 'lastPositionUpdate'):
            msSinceLastUpdate = (datetime.utcnow().timestamp() - self.lastPositionUpdate) * 1000
            if msSinceLastUpdate == 0:
                return

            if getattr(self, 'moving', False):
                distanceTravelled = self.speed * (msSinceLastUpdate)
                angle = math.atan2(self.going_y - self.y, self.going_x - self.x)
                distanceToGoal = Tools.distance({'x': self.x, 'y': self.y}, {'x': self.going_x, 'y': self.going_y})
                if distanceTravelled > distanceToGoal:
                    self.moving = False
                    self.x = self.going_x
                    self.y = self.going_y
                else:
                    self.x = self.x + math.cos(angle) * distanceTravelled
                    self.y = self.y + math.sin(angle) * distanceTravelled

            for condition in list(getattr(self, 's', [])):
                newCooldown = self.s[condition]['ms'] - msSinceLastUpdate
                if newCooldown <= 0:
                    del self.s[condition]
                else:
                    self.s[condition]['ms'] = newCooldown

        super().updatePositions()
        return

    def disconnectHandlerC(self):
        self.ready = False
        return

    def disconnectReasonHandlerC(self, data = None):
        self.ready = False
        return

    def friendHandlerC(self, data):
        if data['event'] in ['lost', 'new', 'update']:
            self.friends = data['friends']
        return

    def startHandlerC(self, data: dict):
        self.going_x = data['x']
        self.going_y = data['y']
        self.moving = False
        self.damage_type = self.G['classes'][data['ctype']]['damage_type']
        self.parseCharacter(data)
        if data.get('entities') != None:
            self.parseEntities(data['entities'])
        self.S = data['s_info']
        self.ready = True
        return

    def achievementProgressHandlerC(self, data):
        self.achievements[data['name']] = data
        return

    def chestOpenedHandlerC(self, data):
        del self.chests[data['id']]
        return

    def dropHandlerC(self, data):
        self.chests[data['id']] = data
        return

    def evalHandlerC(self, data):
        self.parseEval(data)
        return

    def gameErrorHandlerC(self, data):
        if isinstance(data, str):
            print(f'Game Error:\n{data}')
        else:
            print('Game Error:')
            print(str(data))
        return

    def gameLogHandlerC(self, data):
        if not isinstance(data, dict): return
        match = re.search('^Slain by (.+)$', data['message'])
        if match != None:
            Database.connection.ALPC.deaths.insert_one({
                'cause': match[1],
                'map': self.map,
                'name': self.id,
                'serverIdentifier': self.server['name'],
                'serverRegion': self.server['region'],
                'time': datetime.utcnow().timestamp(),
                'x': self.x,
                'y': self.y
            })

    def gameResponseHandlerC(self, data):
        self.parseGameResponse(data)
        return

    def partyUpdateHandlerC(self, data = None):
        self.partyData = data

        if data != None and Database.connection != None:
            playerUpdates = []
            for id in data['party']:
                cData = data['party'][id]
                updateData = {
                    'in': cData['in'],
                    'lastSeen': datetime.utcnow().timestamp(),
                    'map': cData['map'],
                    'name': id,
                    'serverIdentifier': self.serverData['name'],
                    'serverRegion': self.serverData['region'],
                    'type': cData['type'],
                    'x': cData['x'],
                    'y': cData['y']
                }
                playerUpdates.append(pymongo.UpdateOne(
                    filter={ 'name': id },
                    update={ "$set": updateData },
                    upsert=True
                ))
            if len(playerUpdates) > 0:
                Database.connection.ALPC.players.bulk_write(playerUpdates)
        return

    def playerHandlerC(self, data):
        self.parseCharacter(data)
        return

    def qDataHandlerC(self, data):
        self.parseQData(data)
        return

    def trackerHandlerC(self, data):
        for monsterName in data['max']['monsters']:
            characterKills = data['monsters'].get(monsterName, 0)
            maxData = data['max']['monsters'][monsterName]

            if characterKills > maxData[0]:
                maxData[0] = characterKills
                maxData[1] = self.id
        
        Database.connection.ALPC.achievements.insert_one({
            'date': datetime.utcnow().timestamp(),
            'max': data['max'],
            'monsters': data['monsters'],
            'name': self.id
        })

    def upgradeHandlerC(self, data):
        if data['type'] == 'compound' and getattr(self, 'q', {}).get('compound', False):
            del self.q['compound']
        elif data['type'] == 'upgrade' and getattr(self, 'q', {}).get('upgrade', False):
            del self.q['upgrade']
        return

    async def welcomeHandlerC(self, data):
        await self.socket.emit('loaded', {'height': 1080, 'scale': 2, 'success': 1, 'width': 1920})
        await self.socket.emit('auth', {'auth': self.userAuth, 'character': self.characterID, 'height': 1080, 'no_graphics': 'True', 'no_html': '1', 'passphrase': '', 'scale': 2, 'user': self.owner, 'width': 1920})
        return

    async def connect(self):
        await super(Character, self).connect(False, False)

        self.socket.on('disconnect', self.disconnectHandlerC)
        self.socket.on('disconnect_reason', self.disconnectReasonHandlerC)
        self.socket.on('friend', self.friendHandlerC)
        self.socket.on('start', self.startHandlerC)
        self.socket.on('achievement_progress', self.achievementProgressHandlerC)
        self.socket.on('chest_opened', self.chestOpenedHandlerC)
        self.socket.on('drop', self.dropHandlerC)
        self.socket.on('eval', self.evalHandlerC)
        self.socket.on('game_error', self.gameErrorHandlerC)
        self.socket.on('game_response', self.gameResponseHandlerC)
        self.socket.on('party_update', self.partyUpdateHandlerC)
        self.socket.on('player', self.playerHandlerC)
        self.socket.on('q_data', self.qDataHandlerC)
        self.socket.on('upgrade', self.upgradeHandlerC)
        self.socket.on('welcome', self.welcomeHandlerC)
        if Database.connection != None:
            self.socket.on('game_log', self.gameLogHandlerC)
            self.socket.on('tracker', self.trackerHandlerC)

        async def connectedFn():
            connected = asyncio.get_event_loop().create_future()
            def reject(reason):
                if not connected.done():
                    self.socket.off('start', startCheck)
                    self.socket.off('game_error', failCheck)
                    self.socket.off('disconnect_reason', failCheck2)
                    connected.set_exception(Exception(reason))
            def resolve(value):
                if not connected.done():
                    self.socket.off('start', startCheck)
                    self.socket.off('game_error', failCheck)
                    self.socket.off('disconnect_reason', failCheck2)
                    connected.set_result(value)
            async def failCheck(data):
                if isinstance(data, str):
                    reject(f'Failed to connect: {data}')
                else:
                    reject(f'Failed to connect: {data["message"]}')
            async def failCheck2(data):
                reject(f'Failed to connect: {data}')
            async def startCheck(data):
                await self.updateLoop()
                resolve(True)

            self.socket.on('start', startCheck)
            self.socket.on('game_error', failCheck)
            self.socket.on('disconnect_reason', failCheck2)
            
            Tools.setTimeout(reject, Constants.CONNECT_TIMEOUT_S, f'Failed to start within {Constants.CONNECT_TIMEOUT_S}s.')
            while not connected.done():
                await asyncio.sleep(Constants.SLEEP)
            return connected.result()

        return await Tools.tryExcept(connectedFn)

    async def disconnect(self):
        self.logger.debug('Disconnecting!')

        if self.socket:
            await self.socket.disconnect()

        self.ready = False

        for timer in self.timeouts.values():
            Tools.clearTimeout(timer)
        return

    async def requestEntitiesData(self):
        async def entitiesDataFn():
            if not self.ready:
                raise Exception("We aren't ready yet [requestEntitiesData]")
            entitiesData = asyncio.get_event_loop().create_future()
            def reject(reason):
                if not entitiesData.done():
                    self.socket.off('entities', checkEntitiesEvent)
                    entitiesData.set_exception(Exception(reason))
            def resolve(value):
                if not entitiesData.done():
                    self.socket.off('entities', checkEntitiesEvent)
                    entitiesData.set_result(value)
            def checkEntitiesEvent(data):
                if data['type'] == 'all':
                    resolve(data)

            
            Tools.setTimeout(reject, Constants.TIMEOUT, f'requestEntitiesData timeout ({Constants.TIMEOUT}s)')
            self.socket.on('entities', checkEntitiesEvent)

            await self.socket.emit('send_updates')
            while not entitiesData.done():
                await asyncio.sleep(Constants.SLEEP)
            return entitiesData.result()
        return await Tools.tryExcept(entitiesDataFn)

    async def requestPlayerData(self):
        async def playerDataFn():
            if not self.ready:
                raise Exception("We aren't ready yet [requestPlayerData]")
            playerData = asyncio.get_event_loop().create_future()
            def resolve(value):
                if not playerData.done():
                    self.socket.off('player', checkPlayerEvent)
                    playerData.set_result(value)
            def checkPlayerEvent(data: dict):
                if data.get('s', {}).get('typing', False):
                    resolve(data)

            def reject(reason):
                if not playerData.done():
                    self.socket.off('player', checkPlayerEvent)
                    playerData.set_exception(Exception(reason))
            Tools.setTimeout(reject, Constants.TIMEOUT, f'requestPlayerData timeout ({Constants.TIMEOUT}s)')
            self.socket.on('player', checkPlayerEvent)

            await self.socket.emit('property', {'typing': True})
            while not playerData.done():
                await asyncio.sleep(Constants.SLEEP)
            return playerData.result()

        return await Tools.tryExcept(playerDataFn)

    async def acceptFriendRequest(self, id):
        async def friendReqFn():
            if not self.ready:
                raise Exception("We aren't ready yet [acceptFriendRequest].")
            friended = asyncio.get_event_loop().create_future()
            def resolve(value):
                if not friended.done():
                    self.socket.off('game_response', failCheck)
                    self.socket.off('friend', successCheck)
                    friended.set_result(value)
            def successCheck(data):
                if data['event'] == 'new':
                    resolve(data)

            def failCheck(data):
                if isinstance(data, str):
                    if data == 'friend_expired':
                        reject('Friend request expired.')

            def reject(reason):
                if not friended.done():
                    self.socket.off('game_response', failCheck)
                    self.socket.off('friend', successCheck)
                    friended.set_exception(Exception(reason))

            Tools.setTimeout(reject, Constants.TIMEOUT, f'acceptFriendRequest timeout ({Constants.TIMEOUT}s)')
            self.socket.on('friend', successCheck)
            self.socket.on('game_response', failCheck)
            
            await self.socket.emit('friend', { 'event': 'accept', 'name': id })
            while not friended.done():
                await asyncio.sleep(Constants.SLEEP)
            return friended.result()

        return await Tools.tryExcept(friendReqFn)

    async def acceptMagiport(self, name):
        async def magiportFn():
            if not self.ready:
                raise Exception("We aren't ready yet [acceptMagiport].")
            acceptedMagiport = asyncio.get_event_loop().create_future()
            def reject(reason=None):
                if not acceptedMagiport.done():
                    self.socket.off('new_map', magiportCheck)
                    acceptedMagiport.set_exception(Exception(reason))
            def resolve(value=None):
                if not acceptedMagiport.done():
                    self.socket.off('new_map', magiportCheck)
                    acceptedMagiport.set_result(value)
            def magiportCheck(data):
                if data.get('effect', "") == 'magiport':
                    resolve({'map': data['name'], 'x': data['x'], 'y': data['y'] })

            Tools.setTimeout(reject, Constants.TIMEOUT, f'acceptMagiport timeout ({Constants.TIMEOUT}s)')
            self.socket.on('new_map', magiportCheck)
            await self.socket.emit('magiport', { 'name': name })
            while not acceptedMagiport.done():
                await asyncio.sleep(Constants.SLEEP)
            return acceptedMagiport.result()

        return await Tools.tryExcept(magiportFn)
       
    async def acceptPartyInvite(self, id):
        async def partyInvFn():
            if not self.ready:
                raise Exception("We aren't ready yet [acceptPartyInvite].")
            acceptedInvite = asyncio.get_event_loop().create_future()
            def partyCheck(data: dict[str, dict]):
                if data.get('list') != None and data['list'].get(self.id) != None and data['list'].get(id) != None:
                    resolve(data)
            
            def unableCheck(data):
                if data == 'Invitation expired':
                    reject(data)
                elif isinstance(data, str) and re.match('^.+? is not found$', data):
                    reject(data)
                elif data == 'Already partying':
                    if (self.id in self.partyData['list']) and (id in self.partyData['list']):
                        resolve(self.partyData)
                    else:
                        reject(data)
            
            def reject(reason):
                if not acceptedInvite.done():
                    self.socket.off('party_update', partyCheck)
                    self.socket.off('game_log', unableCheck)
                    acceptedInvite.set_exception(Exception(reason))
            def resolve(value = None):
                if not acceptedInvite.done():
                    self.socket.off('party_update', partyCheck)
                    self.socket.off('game_log', unableCheck)
                    acceptedInvite.set_result(value)
            
            Tools.setTimeout(reject, Constants.TIMEOUT, f'acceptPartyInvite timeout ({Constants.TIMEOUT}s)')
            self.socket.on('party_update', partyCheck)
            self.socket.on('game_log', unableCheck)
            await self.socket.emit('party', { 'event': 'accept', 'name': id })
            while not acceptedInvite.done():
                await asyncio.sleep(Constants.SLEEP)
            return acceptedInvite.result()

        return await Tools.tryExcept(partyInvFn)

    async def acceptPartyRequest(self, id):
        async def partyReqFn():
            if not self.ready:
                raise Exception("We aren't ready yet [acceptPartyRequest].")
            acceptedRequest = asyncio.get_event_loop().create_future()
            def partyCheck(data: dict):
                if (data.get('list') != None) and (self.id in data['list']) and (id in data['list']):
                    resolve(data)
                
            def reject(reason):
                if not acceptedRequest.done():
                    self.socket.off('party_update', partyCheck)
                    acceptedRequest.set_exception(Exception(reason))
            def resolve(value=None):
                if not acceptedRequest.done():
                    self.socket.off('party_update', partyCheck)
                    acceptedRequest.set_result(value)
            
            Tools.setTimeout(reject, Constants.TIMEOUT, f'acceptPartyRequest timeout {Constants.TIMEOUT}s)')
            self.socket.on('party_update', partyCheck)
            await self.socket.emit('party', { 'event': 'raccept', 'name': id })
            while not acceptedRequest.done():
                await asyncio.sleep(Constants.SLEEP)
            return acceptedRequest.result()
        
        return await Tools.tryExcept(partyReqFn)

    async def basicAttack(self, id):
        async def attackFn():
            if not self.ready:
                raise Exception("We aren't ready yet [basicAttack].")
            attackStarted = asyncio.get_event_loop().create_future()
            def reject(reason):
                if not attackStarted.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('game_response', failCheck)
                    self.socket.off('notthere', failCheck2)
                    self.socket.off('death', deathCheck)
                    attackStarted.set_exception(Exception(reason))
            def resolve(value):
                if not attackStarted.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('game_response', failCheck)
                    self.socket.off('notthere', failCheck2)
                    self.socket.off('death', deathCheck)
                    attackStarted.set_result(value)
            def deathCheck(data):
                if data['id'] == id:
                    reject(f'Entity {id} not found')
                return
            def failCheck(data):
                if isinstance(data, dict):
                    if data.get('response', None) == 'disabled':
                        reject(f'Attack on {id} failed (disabled).')
                    elif (data.get('response', None) == 'attack_failed') and (data.get('id', None) == id):
                        reject(f'Attack on {id} failed.')
                    elif (data.get('response', None) == 'too_far') and (data.get('place', None) == 'attack') and (data.get('id', None) == id):
                        dist = data.get('dist')
                        reject(f'{id} is too far away to attack (dist: {dist}).')
                    elif (data.get('response', None) == 'cooldown') and (data.get('place', None) == 'attack') and (data.get('id', None) == id):
                        ms = data.get('ms')
                        reject(f'Attack on {id} failed due to cooldown (ms: {ms}).')
                    elif (data.get('response', None) == 'no_mp') and (data.get('place', None) == 'attack'):
                        reject(f'Attack on {id} failed due to insufficient MP.')
                return
            def failCheck2(data):
                if data.get('place', None) == 'attack':
                    reject(f'{id} could not be found to attack.')
            def attackCheck(data):
                if (data.get('attacker') == self.id) and (data.get('target') == id) and (data.get('type', None) == 'attack'):
                    resolve(data['pid'])
            Tools.setTimeout(reject, Constants.TIMEOUT, f'attack timeout ({Constants.TIMEOUT}s)')
            self.socket.on('action', attackCheck)
            self.socket.on('game_response', failCheck)
            self.socket.on('notthere', failCheck2)
            self.socket.on('death', deathCheck)
            await self.socket.emit('attack', { 'id': id })
            while not attackStarted.done():
                await asyncio.sleep(Constants.SLEEP)
            return attackStarted.result()
        return await Tools.tryExcept(attackFn)

    async def buy(self, itemName, quantity = 1):
        async def buyFn():
            if not self.ready:
                raise Exception("We aren't ready yet [buy]")
            if self.gold < self.G['items'][itemName]['g']:
                raise Exception(f"Insufficient gold. We only have {self.gold}, but the item costs {self.G['itsms'][itemName]['g']}")
            itemReceived = asyncio.get_event_loop().create_future()
            def reject(reason):
                if not itemReceived.done():
                    self.socket.off('player', buyCheck1)
                    self.socket.off('game_response', buyCheck2)
                    itemReceived.set_exception(Exception(reason))
            def resolve(value):
                if not itemReceived.done():
                    self.socket.off('player', buyCheck1)
                    self.socket.off('game_response', buyCheck2)
                    itemReceived.set_result(value)
            def buyCheck1(data: dict[str, dict]):
                if data.get('hitchhikers') == None:
                    return
                for hitchhiker in data['hitchhikers'].values():
                    if hitchhiker[0] == 'game_response':
                        data = hitchhiker[1]
                        if (isinstance(data, dict)) and (data['response'] == 'buy_success') and (data['name'] == itemName) and (data['q'] == quantity):
                            resolve(data['num'])
                return
            def buyCheck2(data):
                if data == 'buy_cant_npc':
                    reject(f'Cannot buy {quantity} {itemName}(s) from an NPC')
                elif data == 'buy_cant_space':
                    reject(f'Not enough inventory space to buy {quantity} {itemName}(s)')
                elif data == 'buy_cost':
                    reject(f'Not enough gold to buy {quantity} {itemName}(s)')
                return
            Tools.setTimeout(reject, Constants.TIMEOUT, f'buy timeout ({Constants.TIMEOUT}s)')
            self.socket.on('player', buyCheck1)
            self.socket.on('game_response', buyCheck2)
            if self.G['items'][itemName].get('s', False):
                await self.socket.emit('buy', { 'name': itemName, 'quantity': quantity })
            else:
                await self.socket.emit('buy', { 'name': itemName })
            while not itemReceived.done():
                await asyncio.sleep(Constants.SLEEP)
            return itemReceived.result()
        return await Tools.tryExcept(buyFn)

    async def buyWithTokens(self, itemName):
        async def tokenBuyFn():
            numBefore = self.countItem(itemName)

            tokenTypeNeeded = ''
            numTokensNeeded = 0
            for t in self.G['tokens']:
                tokenType = t
                tokenTable = self.G['tokens'][tokenType].values()
                for item in tokenTable.keys():
                    if item != itemName:
                        continue
                    tokenTypeNeeded = tokenType
                    numTokensNeeded = tokenTable[item]
                    break
                if tokenTypeNeeded != '':
                    break
            if tokenTypeNeeded == '':
                raise Exception(f'{itemName} is not purchasable with tokens.')
            numTokens = self.countItem(tokenTypeNeeded)
            if numTokens < numTokensNeeded:
                raise Exception(f'We need {numTokensNeeded} to buy {itemName}, but we only have {numTokens}.')
            itemReceived = asyncio.get_event_loop().create_future()
            def reject(reason):
                if not itemReceived.done():
                    self.socket.off('player', buyCheck)
                    self.socket.off('game_response', failCheck)
                    itemReceived.set_exception(Exception(reason))
            def resolve(value):
                if not itemReceived.done():
                    self.socket.off('player', buyCheck)
                    self.socket.off('game_response', failCheck)
                    itemReceived.set_result(value)
            def buyCheck(data):
                numNow = self.countItem(itemName, data['items'])
                if numNow > numBefore:
                    resolve(None)
            def failCheck(data):
                if isinstance(data, str):
                    if data == 'exchange_notenough':
                        reject(f'Not enough tokens to buy {itemName}.')
            Tools.setTimeout(reject, Constants.TIMEOUT, f'buyWithTokens timeout ({Constants.TIMEOUT}s)')
            self.socket.on('player', buyCheck)
            self.socket.on('game_response', failCheck)
            invTokens = self.locateItem(tokenTypeNeeded)
            await self.socket.emit('exchange_buy', { 'name': itemName, 'num': invTokens, 'q': self.items[invTokens]['q'] })
            while not itemReceived.done():
                await asyncio.sleep(Constants.SLEEP)
            return itemReceived.result()
        return await Tools.tryExcept(tokenBuyFn)

    async def buyFromMerchant(self, id, slot, rid, quantity = 1):
        async def merchantBuyFn():
            if not self.ready:
                raise Exception("We aren't ready yet [buyFromMerchant].")
            if quantity <= 0:
                raise Exception(f"We can not buy a quantity of {quantity}.")
            merchant = self.players.get(id)
            if merchant == None:
                raise Exception(f"We can not see {id} nearby.")
            if Tools.distance(self, merchant) > Constants.NPC_INTERACTION_DISTANCE:
                raise Exception(f"We are too far away from {id} to buy from.")
            
            item: dict = merchant.slots.get(slot, False)
            if not item:
                raise Exception(f"We could not find an item in slot {slot} on {id}.")
            if item.get('b', False):
                raise Exception("The item is not for sale, this merchant is *buying* that item.")
            if item.get('rid', False) != rid:
                raise Exception(f"The RIDs do not match (item: {item.get('rid', None)}, supplied: {rid})")
            
            if (item.get('q', False)) and (quantity != 1):
                print("we are only going to buy 1, as there is only 1 available.")
                quantity = 1
            elif (item.get('q', False)) and (quantity > item['q']):
                print(f"We can't buy {quantity}, we can only buy {item['q']}, so we're doing that.")
                quantity = item['q']
            
            if self.gold < item['price'] * quantity:
                if self.gold < item['price']:
                    raise Exception(f"We don't have enough gold. It costs {item['price']}, but we only have {self.gold}")
                buyableQuantity = math.floor(self.gold / item['price'])
                print(f"We don't have enough gold to buy {quantity}, we can only buy {buyableQuantity}, so we're doing that.")
                quantity = buyableQuantity
            itemBought = asyncio.get_event_loop().create_future()
            def reject(reason):
                if not itemBought.done():
                    self.socket.off('ui', buyCheck)
                    itemBought.set_exception(Exception(reason))
            def resolve(value):
                if not itemBought.done():
                    self.socket.off('ui', buyCheck)
                    itemBought.set_result(value)
            def buyCheck(data):
                if (data['type'] == '+$$') and (data['seller'] == id) and (data['buyer'] == self.id) and (data['slot'] == slot):
                    resolve(data['item'])
            Tools.setTimeout(reject, Constants.TIMEOUT, f'buy timeout ({Constants.TIMEOUT}s)')
            self.socket.on('ui', buyCheck)
            await self.socket.emit('trade_buy', { 'id': id, 'q': str(quantity), 'rid': rid, 'slot': slot })
            while not itemBought.done():
                await asyncio.sleep(Constants.SLEEP)
            return itemBought.result()
        return await Tools.tryExcept(merchantBuyFn)

    async def buyFromPonty(self, item: dict):
        async def pontyBuyFn():
            if not self.ready:
                raise Exception("We aren't ready yet [buyFromPonty].")
            if not item.get('rid', False):
                raise Exception("This item does not have an 'rid'.")
            price = self.G['items'][item['name']]['g'] * Constants.PONTY_MARKUP
            if item.get('q', 1) > 1:
                price *= item['q']
            if price > self.gold:
                raise Exception(f"We don't have enough gold to buy {item['name']} from Ponty.")
            numBefore = self.countItem(item['name'], self.items)
            bought = asyncio.get_event_loop().create_future()
            def reject(reason):
                if not bought.done():
                    self.socket.off('game_log', failCheck)
                    self.socket.off('player', successCheck)
                    bought.set_exception(Exception(reason))
            def resolve(value):
                if not bought.done():
                    self.socket.off('game_log', failCheck)
                    self.socket.off('player', successCheck)
                    bought.set_result(value)
            def failCheck(message):
                if message == 'Item gone':
                    reject(f"{item['name']} is no longer available from Ponty.")
            def successCheck(data):
                numNow = self.countItem(item['name'], data['items'])
                if ((item.get('q') != None) and (numNow == numBefore + item['q'])) or (numNow == numBefore + 1):
                    resolve(None)
            Tools.setTimeout(reject, Constants.TIMEOUT * 5, f"buyFromPonty timeout ({Constants.TIMEOUT * 5}s)")
            self.socket.on('game_log', failCheck)
            self.socket.on('player', successCheck)
            await self.socket.emit('sbuy', { 'rid': item['rid'] })
            while not bought.done():
                await asyncio.sleep(Constants.SLEEP)
            return bought.result()
        return await Tools.tryExcept(pontyBuyFn)

    def calculateTargets(self):
        targets = {
            'magical': 0,
            'physical': 0,
            'pure': 0
        }

        for entity in self.getEntities({'targetingMe': True}):
            dtype = entity.damage_type
            if dtype == 'magical':
                targets['magical'] += 1
            elif dtype == 'physical':
                targets['physical'] += 1
            elif dtype == 'pure':
                targets['pure'] += 1
        
        total = targets['magical'] + targets['physical'] + targets['pure']
        if total < self.targets:
            difference = self.targets - total
            targets['magical'] += difference
            targets['physical'] += difference
            targets['pure'] += difference
        
        return targets
    
    def calculateDamageRange(self, defender, skill = 'attack'):
        gSkill: dict = self.G['skills'].get(skill)

        if gSkill == None:
            raise Exception(f"calculateDamageRange ERROR: '{skill}' isn't a skill!?")

        if hasattr(defender, 'immune') and (skill != 'attack') and (gSkill.get('pierces_immunity') == None):
            return [0, 0]
        
        if (hasattr(defender, '1hp')) or (skill == 'taunt'):
            if hasattr(self, 'crit'):
                return [1, 2]
            else:
                return [1, 1]
        
        baseDamage = self.attack
        if gSkill.get('damage') != None:
            baseDamage = gSkill['damage']
        
        if hasattr(defender, 's') and defender.s.get('cursed') != None:
            baseDamage *= 1.2
        if hasattr(defender, 's') and defender.s.get('marked') != None:
            baseDamage *= 1.1

        if self.ctype == 'priest':
            baseDamage *= 0.4
        
        damage_type = gSkill.get('damage_type', self.damage_type)

        additionalApiercing = 0
        if gSkill.get('apiercing') != None:
            additionalApiercing = gSkill['apiercing']
        if damage_type == 'physical':
            baseDamage *= Tools.damage_multiplier(defender.armor - self.apiercing - additionalApiercing)
        elif damage_type == 'magical':
            baseDamage *= Tools.damage_multiplier(defender.resistance - self.rpiercing)
        
        if gSkill.get('damage_multiplier') != None:
            baseDamage *= gSkill['damage_multiplier']
        
        lowerLimit = baseDamage * 0.9
        upperLimit = baseDamage * 1.1

        if hasattr(self, 'crit'):
            if self.crit >= 100:
                lowerLimit *= (2 + (self.critdamage / 100))
            upperLimit *= (2 + (self.critdamage / 100))
        
        if skill == 'cleave':
            lowerLimit *= 0.1
            upperLimit *= 0.9

        lowerLimit = math.floor(lowerLimit)
        upperLimit = math.floor(upperLimit)
        
        return [lowerLimit, upperLimit]

    def calculateItemCost(self, item):
        gInfo: dict = self.G['items'][item['name']]

        cost = gInfo['g']

        if gInfo.get('compound') != None:
            for i in range(0, int(item['level'])):
                cost *= 3
                scrollLevel = 0
                for grade in gInfo['grades']:
                    if i+1 < grade:
                        scrollInfo = self.G['items'][f'cscroll{scrollLevel}']
                        cost += scrollInfo['g']
                        break
                    scrollLevel += 1
        elif gInfo.get('upgrade') != None:
            for i in range(0, int(item['level'])):
                scrollLevel = 0
                for grade in gInfo['grades']:
                    if i+1 < grade:
                        scrollInfo = self.G['items'][f'scroll{scrollLevel}']
                        cost += scrollInfo['g']
                        break
                    scrollLevel += 1
        
        if item.get('gift') != None:
            cost -= (gInfo['g'] - 1)
        
        return cost

    def calculateItemGrade(self, item):
        gInfo: dict = self.G['items'][item['name']]
        if gInfo.get('grades') != None:
            return
        grade = 0
        for level in gInfo['grades']:
            if item['level'] < level:
                break
            grade += 1
        return grade

    def canBuy(self, item, ignoreLocation = False):
        if self.isFull():
            return False # Not enough inv space
        
        gInfo = self.G['items'][item]
        if self.gold < gInfo['g']:
            return False # Not enough money

        computerAvailable = self.hasItem('computer') or self.hasItem('supercomputer')

        buyable = False
        close = False
        for map in self.G['maps'].keys():
            if buyable == True:
                break
            if (not computerAvailable) and (map != self.map):
                continue # We aren't close, and we don't have a computer, so don't check this map
            if Tools.hasKey(self.G['maps'][map], 'ignore'):
                continue
            for npc in self.G['maps']['npcs'].keys():
                if buyable == True:
                    break
                if 'items' not in self.G['npcs'][npc['id']].keys():
                    continue
                for i in self.G['npcs'][npc['id']]['items'].keys():
                    if i == item:
                        buyable = True
                        if (Tools.distance(self, {'map': map, 'x': npc['position'][0], 'y': npc['position'][1]}) < Constants.NPC_INTERACTION_DISTANCE):
                            close = True
                        break
        if not buyable:
            return False
        
        return (computerAvailable or close or ignoreLocation)
    
    def canCraft(self, itemToCraft, ignoreLocation = False):
        gCraft = self.G['craft'].get(itemToCraft, False)
        if not gCraft:
            print('Item not craftable')
            return False # Item is not craftable
        if gCraft['cost'] > self.gold:
            print('Not enough gold')
            return False # We can't afford
        for i in range(0, len(gCraft['items'])):
            reqs = gCraft['items'][i]
            reqQuan = reqs[0]
            reqItem = reqs[1]
            reqLevl = None
            if len(reqs) == 3:
                reqLevl = reqs[2]
            fixedItemLevel = reqLevl
            if fixedItemLevel == None:
                gInfo = self.G['items'][reqItem]
                if gInfo.get('upgrade', False) or gInfo.get('compound', False):
                    fixedItemLevel = 0
            if fixedItemLevel == None:
                if not self.hasItem(reqItem, self.items, { 'quantityGreaterThan': reqQuan - 1 }):
                    print(f'Not enough of {reqItem}')
                    return False
            elif not self.hasItem(reqItem, self.items, { 'level': fixedItemLevel, 'quantityGreaterThan': reqQuan - 1 }):
                print(f'Not enough of {reqItem}')
                return False
            if self.G['maps'].get('mount', False):
                print('Can\'t craft in the bank')
                return False # Can't craft things in the bank
            
            if (not self.hasItem('computer')) and (not self.hasItem('supercomputer')) and (not ignoreLocation):
                craftableLocation = self.locateCraftNPC(itemToCraft)
                if Tools.distance(self, craftableLocation) > Constants.NPC_INTERACTION_DISTANCE:
                    print('Not close enough')
                    return False
            print('We can craft!')
            return True
    
    def canExchange(self, itemToExchange, ignoreLocation = False):
        gItem = self.G['items'][itemToExchange]
        if (Tools.hasKey(gItem, 'e')) and (self.countItem(itemToExchange) < gItem['e']):
            return False # Not enough of item
        if (not self.hasItem('computer')) and (not self.hasItem('supercomputer')) and (not ignoreLocation):
            exchangeLocation = self.locateExchangeNPC(itemToExchange)
            if Tools.distance(self, exchangeLocation) > Constants.NPC_INTERACTION_DISTANCE:
                return False # No close enough
        
        return True
    
    def canKillInOneShot(self, entity, skill = 'attack'):
        if Tools.hasKey(entity, 'lifesteal'):
            return False
        if Tools.hasKey(entity, 'abilities') and Tools.hasKey(entity['abilities'], 'self_healing'):
            return False
        if Tools.hasKey(entity, 'avoidance'):
            return False

        damage_type = self.G['skills'][skill].get('damage_type', self.damage_type)

        if damage_type == 'magical' and Tools.hasKey(entity, 'reflection'):
            return False
        if damage_type == 'physical' and Tools.hasKey(entity, 'evasion'):
            return False
        
        return self.calculateDamageRange(entity, skill)[0] >= entity.hp
    
    def canSell(self):
        if (self.map in ['bank', 'bank_b', 'bank_u']):
            return False # can't sell in the bank
        if (self.hasItem('computer')) or (self.hasItem('supercomputer')):
            return True # we can sell anywhere with a computer
        
        for npc in self.G['maps'][self.map]['npcs']:
            gNPC = self.G['npcs'][npc['id']]
            if not Tools.hasKey(gNPC, 'items'):
                continue # NPC is not a merchant
            if Tools.distance(self, { 'map': self.map, 'x': npc['position'][0], 'y': npc['position'][1] }) > Constants.NPC_INTERACTION_DISTANCE:
                continue # Too far away

            return True
        
        return False
    
    def canUpgrade(self, itemPos, scrollPos, offeringPos = -1):
        if self.map in ['bank', 'bank_b', 'bank_u']:
            return False # Can't upgrade in the bank
        if itemPos < 0 or itemPos > 42:
            raise Exception('Invalid itemPos value')
        if scrollPos < 0 or scrollPos > 42:
            raise Exception('Invalid scrollPos value')
        if itemPos == scrollPos:
            raise Exception('Invalid itemPos & scrollPos values; cannot be equivalent')
        
        itemInfo = self.items[itemPos]
        if itemInfo == None:
            raise Exception(f"No item in inventory position '{itemPos}'.")
        gItemInfo = self.G['items'][itemInfo['name']]
        if not Tools.hasKey(gItemInfo, 'upgrade'):
            return False # Item is not upgradable
        scrollInfo = self.items[scrollPos]
        if scrollInfo == None:
            raise Exception(f"No scroll in inventory position '{scrollPos}'.")
        gScrollInfo = self.G['items'][scrollInfo['name']]
        if gScrollInfo['type'] != 'uscroll':
            raise Exception("Scroll is compound, not upgrade.")
        offerringInfo = None
        if offeringPos >= 0:
            offerringInfo = self.items[offeringPos]
        
        if (not self.hasItem('computer')) and (not self.hasItem('supercomputer')) and (Tools.distance(self, {'map': 'main', 'x': self.G['maps']['main']['ref']['u_mid'][0], 'y': self.G['maps']['main']['ref']['u_mid'][1]}) > Constants.NPC_INTERACTION_DISTANCE):
            return False # No computer; too far away
        
        scrollLevel = gScrollInfo['grade']
        itemGrade = self.calculateItemGrade(itemInfo)
        if scrollLevel < itemGrade:
            return False # Scroll can't be used on this grade of item

        # TODO: offering compatibility check
        
        return True

    def canUse(self, skill, *, ignoreCooldown = False, ignoreEquipped = False):
        if self.rip:
            return False # We're dead lol
        for conditionName in self.s:
            gCondition = self.G['conditions'][conditionName]
            if Tools.hasKey(gCondition, 'blocked'):
                return False # We have a skill-preventing condition
        if (self.isOnCooldown(skill)) and (not ignoreCooldown):
            return False # Skill is on cooldown
        gInfoSkill = self.G['skills'][skill]
        if (Tools.hasKey(gInfoSkill, 'hostile')) and (Tools.hasKey(self.G['maps'][self.map], 'safe')):
            return False # can't use hostile skills in a safe zone
        if Tools.hasKey(gInfoSkill, 'mp') and self.mp < gInfoSkill['mp']:
            return False # Not enough mp
        if skill == 'attack' and self.mp < self.mp_cost:
            return False # Not enough mp (attack)
        if Tools.hasKey(gInfoSkill, 'level') and self.level < gInfoSkill['level']:
                return False # Not high enough level to use skill
        if Tools.hasKey(gInfoSkill, 'wtype') and (not ignoreEquipped):
            if self.slots['mainhand'] == None:
                return False # We don't have any weapon equipped
            gInfoWeapon = self.G['items'][self.slots['mainhand']['name']]
            if isinstance(gInfoSkill['wtype'], list):
                if gInfoWeapon['wtype'] not in gInfoSkill['wtype']:
                    return False
            elif gInfoWeapon['wtype'] != gInfoSkill['wtype']:
                return False
        if Tools.hasKey(gInfoSkill, 'consume') and (not ignoreEquipped):
            if not self.hasItem(gInfoSkill['consume']):
                return False
        if Tools.hasKey(gInfoSkill, 'inventory') and (not ignoreEquipped):
            for item in gInfoSkill['inventory']:
                if not self.hasItem(item):
                    return False
        if Tools.hasKey(gInfoSkill, 'slot') and (not ignoreEquipped):
            hasSlot = False
            for (slot, item) in gInfoSkill['slot'].items():
                if self.slots[slot] != None and self.slots[slot]['name'] == item:
                    hasSlot = True
                    break
            if not hasSlot:
                return False # We don't have anything equipped that lets us use this skill
        if Tools.hasKey(gInfoSkill, 'class'):
            if self.ctype not in gInfoSkill['class']:
                return False
        if Tools.hasKey(gInfoSkill, 'requirements'):
            for s in gInfoSkill['requirements'].keys():
                if getattr(self, s) < gInfoSkill['requirements'][s]:
                    return False
        if Tools.hasKey(self.s, 'dampened') and skill == 'blink':
            return False
        if self.ctype == 'merchant' and skill == 'attack':
            if self.slots['mainhand'] == None:
                return False
            if self.slots['mainhand']['name'] != 'dartgun':
                return False
            if self.gold < 100:
                return False
        return True

    async def closeMerchantStand(self):
        async def closeFn():
            if not self.ready:
                raise Exception("We aren't ready yet [closeMerchantStand].")
            if not hasattr(self, 'stand'):
                return # It's already closed
            closed = asyncio.get_event_loop().create_future()
            def reject(reason):
                if not closed.done():
                    self.socket.off('player', checkStand)
                    closed.set_exception(Exception(reason))
            def resolve(value):
                if not closed.done():
                    self.socket.off('player', checkStand)
                    closed.set_result(value)
            def checkStand(data):
                if not Tools.hasKey(data, 'stand'):
                    resolve(None)
            Tools.setTimeout(reject, Constants.TIMEOUT, f'closeMerchantStand timeout ({Constants.TIMEOUT}s)')
            self.socket.on('player', checkStand)
            await self.socket.emit('merchant', {'close': 1})
            while not closed.done():
                await asyncio.sleep(Constants.SLEEP)
            return closed.result()
        return await Tools.tryExcept(closeFn)

    async def compound(self, item1Pos, item2Pos, item3Pos, cscrollPos, offeringPos = None):
        async def compoundFn():
            if not self.ready:
                raise Exception("We aren't ready yet [compound].")
            item1Info = self.items[item1Pos]
            item2Info = self.items[item2Pos]
            item3Info = self.items[item3Pos]
            cscrollInfo = self.items[cscrollPos]
            if item1Info == None:
                raise Exception(f"There is no item in inventory slot {item1Pos} (item1).")
            if item2Info == None:
                raise Exception(f"There is no item in inventory slot {item2Pos} (item2).")
            if item3Info == None:
                raise Exception(f"There is no item in inventory slot {item3Pos} (item3).")
            if cscrollInfo == None:
                raise Exception(f"There is no item in inventory slot {cscrollPos} (cscroll).")
            if offeringPos != None:
                offeringInfo = self.items[offeringPos]
                if offeringInfo == None:
                    raise Exception(f"There is no item in inventory slot {offeringPos} (offering).")
            if not ((item1Info['name'] == item2Info['name']) and (item1Info['name'] == item3Info['name'])):
                raise Exception("You can only combine 3 of the same items.")
            if not ((item1Info['level'] == item2Info['level']) and (item1Info['level'] == item3Info['level'])):
                raise Exception("You can only combine 3 items of the same level.")
            compoundComplete = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not compoundComplete.done():
                    self.socket.off('game_response', gameResponseCheck)
                    self.socket.off('player', playerCheck)
                    compoundComplete.set_exception(Exception(reason))
                return
            def resolve(value = None):
                if not compoundComplete.done():
                    self.socket.off('game_response', gameResponseCheck)
                    self.socket.off('player', playerCheck)
                    compoundComplete.set_result(value)
                return
            def playerCheck(data):
                if not Tools.hasKey(data, 'hitchhikers'):
                    return
                for [event, datum] in data['hitchhikers'].items():
                    if event == 'game_response' and datum['response'] == 'compound_fail':
                        resolve(False)
                        break
                    elif event == 'game_response' and datum['response'] == 'compound_success':
                        resolve(True)
                        break
                return
            def gameResponseCheck(data):
                if isinstance(data, dict):
                    if data['response'] == 'bank_restrictions' and data['place'] == 'compound':
                        reject("You can't compound items in the gank.")
                elif isinstance(data, str):
                    if data == 'compound_no_item':
                        reject()
            Tools.setTimeout(reject, 60, "compound timeout (60s)")
            self.socket.on('game_response', gameResponseCheck)
            self.socket.on('player', playerCheck)
            if offeringPos == None:
                await self.socket.emit('compound', { 'clevel': item1Info['level'], 'items': [item1Pos, item2Pos, item3Pos], 'scroll_num': cscrollPos })
            else:
                await self.socket.emit('compound', { 'clevel': item1Info['level'], 'items': [item1Pos, item2Pos, item3Pos], 'offering_num': offeringPos, 'scroll_num': cscrollPos })
            while not compoundComplete.done():
                await asyncio.sleep(Constants.SLEEP)
            return compoundComplete.result()
        
        return await Tools.tryExcept(compoundFn)

    async def craft(self, item):
        async def craftedFn():
            if not self.ready:
                raise Exception("We aren't ready yet [craft].")
            gInfo = self.G['craft'].get(item, None)
            if gInfo == None:
                raise Exception(f"Can't find a recipe for {item}.")
            if gInfo['cose'] > self.gold:
                raise Exception(f"We don't have enough gold to craft {item}.")

            itemPositions = []
            for i in range(0, len(gInfo['items'])):
                requiredQuantity = gInfo['items'][i][0]
                requiredName = gInfo['items'][i][1]
                fixedItemLevel = None
                if len(gInfo['items'][i]) == 3:
                    fixedItemLevel = gInfo['items'][i][2]
                if fixedItemLevel == None:
                    gInfo = self.G['items'][requiredName]
                    if Tools.hasKey(gInfo, 'upgrade') or Tools.hasKey(gInfo, 'compound'):
                        fixedItemLevel = 0
                
                levelArg = fixedItemLevel
                quantityGreaterThanArg = requiredQuantity - 1 if requiredQuantity > 0 else None

                itemPos = self.locateItem(requiredName, self.items, level=levelArg, quantityGreaterThan=quantityGreaterThanArg)
                if itemPos == None:
                    raise Exception(f"We don't have {requiredQuantity} {requiredName} to craft {item}.")
                
                itemPositions.append([i, itemPos])
            crafted = asyncio.get_event_loop().create_future()
            def reject(reason):
                    if not crafted.done():
                        self.socket.off('game_response', successCheck)
                        crafted.set_exception(Exception(reason))
            def resolve(value = None):
                    if not crafted.done():
                        self.socket.off('game_response', successCheck)
                        crafted.set_result(value)
            def successCheck(data):
                    if isinstance(data, dict):
                        if data['response'] == 'craft' and data['name'] == item:
                            resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"craft timeout ({Constants.TIMEOUT}s)")
            self.socket.on('game_response', successCheck)
            await self.socket.emit('craft', { 'items': itemPositions })
            while not crafted.done():
                    await asyncio.sleep(Constants.SLEEP)
            return crafted.result()    
        return await Tools.tryExcept(craftedFn)

    async def depositGold(self, gold):
        async def goldFn():
            nonlocal self
            nonlocal gold
            if not self.ready:
                raise Exception("We aren't ready yet [depositGold].")
            if self.map != 'bank':
                raise Exception("We need to be in 'bank' to deposit gold.")
            if gold <= 0:
                raise Exception("We can't deposit 0 or less gold")
            
            if gold > self.gold:
                print(f"We only have {self.gold} gold, so we're depositing that instead of {gold}.")
                gold = self.gold
            
            await self.socket.emit('bank', { 'amount': gold, 'operation': 'deposit' })
        return await Tools.tryExcept(goldFn)
    
    async def depositItem(self, inventoryPos, bankPack = None, bankSlot = -1):
        async def swapFn():
            nonlocal self
            nonlocal inventoryPos
            nonlocal bankPack
            nonlocal bankSlot
            if not self.ready:
                raise Exception("We aren't ready yet [depositItem].")
            if self.map not in ['bank', 'bank_b', 'bank_u']:
                raise Exception(f"We're not in the bank (we're in '{self.map}')")

            for i in range(0, 20):
                if Tools.hasKey(self.bank, 'items0'):
                    break
                await asyncio.sleep(250)
            if not Tools.hasKey(self.bank, 'items0'):
                raise Exception("We don't have bank information yet. Please try again in a bit.")
            
            item = self.items[inventoryPos]
            if item == None:
                raise Exception(f"There is no item in inventory slot {inventoryPos}.")

            if bankPack:
                bankPackNum = int(bankPack[5:7])
                if (self.map == 'bank' and (bankPackNum < 0 or bankPackNum > 7)) or (self.map == 'bank_b' and (bankPackNum < 8 or bankPackNum > 23)) or (self.map == 'bank_u' and (bankPackNum < 24 or bankPackNum > 47)):
                    raise Exception(f"We can not access {bankPack} on {self.map}.")
            else:
                bankSlot = None
                packFrom = None
                packTo = None
                if self.map == 'bank':
                    packFrom = 0
                    packTo = 7
                elif self.map == 'bank_b':
                    packFrom = 8
                    packTo = 23
                elif self.map == 'bank_u':
                    packFrom = 24
                    packTo = 47
                
                numStackable = self.G['items'][item['name']].get('s', None)

                emptyPack = None
                emptySlot = None
                for packNum in range(packFrom, packTo):
                    packName = f'items{packNum}'
                    pack = self.bank.get(packName, None)
                    if not pack:
                        continue
                    for slotNum in range(0, len(pack)):
                        slot = pack[slotNum]
                        if slot == None:
                            if numStackable == None:
                                bankPack = packName
                                bankSlot = slotNum
                            elif emptyPack == None and emptySlot == None:
                                emptyPack = packName
                                emptySlot = slotNum
                        elif numStackable != None and slot['name'] == item['name'] and (slot['q'] + item['q'] <= numStackable):
                            bankPack = packName
                            bankSlot = -1
                            break
                    if bankPack != None and bankSlot != None:
                        break
                if bankPack == None and bankSlot == None and emptyPack != None and emptySlot != None:
                    bankPack = emptyPack
                    bankSlot = emptySlot
                elif bankPack == None and bankSlot == None and emptyPack == None and emptySlot == None:
                    raise Exception(f"Bank is full. There is nowhere to place {item['name']}")
            
            bankItemCount = self.countItem(item['name'], self.bank[bankPack])
            swapped = asyncio.get_event_loop().create_future()
            def reject(reason):
                if not swapped.done():
                    self.socket.off('player', checkDeposit)
                    swapped.set_exception(Exception(reason))
            def resolve(value = None):
                if not swapped.done():
                    self.socket.off('player', checkDeposit)
                    swapped.set_result(value)
            def checkDeposit(data):
                if Tools.hasKey(data, 'user'):
                    if data['map'] not in ['bank', 'bank_b', 'bank_u']:
                        reject(f"We're not in the bank (we're in '{data['map']}')")
                    else:
                        newBankItemCount = self.countItem(item['name'], data['user'][bankPack])
                        if ((Tools.hasKey(item, 'q') and newBankItemCount == (bankItemCount + item['q'])) or (not Tools.hasKey(item, 'q') and newBankItemCount == (bankItemCount +1))):
                            resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f'depositItem timeout ({Constants.TIMEOUT}s)')
            self.socket.on('player', checkDeposit)
            await self.socket.emit('bank', { 'inv': inventoryPos, 'operation': 'swap', 'pack': bankPack, 'str': bankSlot })
            while not swapped.done():
                await asyncio.sleep(Constants.SLEEP)
            return swapped.result()
        return await Tools.tryExcept(swapFn)

    async def emote(self, emotionName):
        async def emoteFn():
            nonlocal self
            nonlocal emotionName
            if not self.ready:
                raise Exception("We aren't ready yet [emote].")
            if not hasattr(self, 'emx') or not Tools.hasKey(self.emx, emotionName):
                raise Exception(f"We don't have the emotion '{emotionName}'")
            emoted = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not emoted.done():
                    self.socket.off('game_response', failCheck)
                    self.socket.off('emotion', successCheck)
                    emoted.set_exception(Exception(reason))
            def resolve(value = None):
                if not emoted.done():
                    self.socket.off('game_response', failCheck)
                    self.socket.off('emotion', successCheck)
                    emoted.set_result(value)
            def failCheck(data):
                if isinstance(data, str):
                    if data == 'emotion_cooldown':
                        reject('Emotion is on cooldown?')
                    elif data == 'emotion_cant':
                        reject('Emotion is...blocked..?')
            def successCheck(data):
                if data['name'] == emotionName and data['player'] == self.id:
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f'emote timeout ({Constants.TIMEOUT}s)')
            self.socket.on('game_response', failCheck)
            self.socket.on('emotion', successCheck)
            await self.socket.emit('emotion', { 'name': emotionName })
            while not emoted.done():
                await asyncio.sleep(Constants.SLEEP)
            return emoted.result()
        return await Tools.tryExcept(emoteFn)

    async def enter(self, map, instance = None):
        async def enterFn():
            nonlocal self
            nonlocal map
            nonlocal instance
            if not self.ready:
                raise Exception("We aren't ready yet [enter].")

            found = False
            distance = sys.maxsize
            for d in self.G['maps'][self.map]['doors']:
                if d[4] != map:
                    continue
                found = True
                distance = Pathfinder.doorDistance(self, d)
                if distance > Constants.DOOR_REACH_DISTANCE:
                    continue
                break
            if not found:
                raise Exception(f"There is no door to {map} from {self.map}.")
            if distance > Constants.DOOR_REACH_DISTANCE:
                raise Exception(f"We're too far ({distance}) from the door to {map}.")
            enterComplete = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not enterComplete.done():
                    self.socket.off('new_map', enterCheck)
                    self.socket.off('game_response', failCheck)
                    enterComplete.set_exception(Exception(reason))
            def resolve(value = None):
                if not enterComplete.done():
                    self.socket.off('new_map', enterCheck)
                    self.socket.off('game_response', failCheck)
                    enterComplete.set_result(value)
            def enterCheck(data):
                if data['name'] == map:
                    resolve()
                else:
                    reject(f"We are not in {data['name']}, but we should be in {map}.")
            def failCheck(data):
                if isinstance(data, str):
                    if data == 'transport_cant_item':
                        reject(f"We don't have the required item to enter {map}.")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"We don't have the required item to enter {map}.")
            self.socket.on('new_map', enterCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('enter', { 'name': instance, 'place': map })
            while not enterComplete.done():
                await asyncio.sleep(Constants.SLEEP)
            return enterComplete.result()
        return await Tools.tryExcept(enterFn)

    async def equip(self, inventoryPos, equipSlot = None):
        async def equipFn():
            nonlocal self
            nonlocal inventoryPos
            nonlocal equipSlot
            if not self.ready:
                raise Exception("We aren't ready yet [equip].")
            if self.items[inventoryPos] == None:
                raise Exception(f"No item in inventory slot {inventoryPos}.")
            iInfo = self.items[inventoryPos]
            equipFinished = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not equipFinished.done():
                    self.socket.off('player', equipCheck)
                    self.socket.off('disappearing_text', cantEquipCheck)
                    equipFinished.set_exception(Exception(reason))
            def resolve(value = None):
                if not equipFinished.done():
                    self.socket.off('player', equipCheck)
                    self.socket.off('disappearing_text', cantEquipCheck)
                    equipFinished.set_result(value)
            def equipCheck(data):
                if equipSlot != None:
                    item = data['slots'][equipSlot]
                    if (item != None) and (item['name'] == iInfo['name']) and (item['level'] == iInfo['level']) and (item['p'] == iInfo['p']):
                        resolve()
                else:
                    for slot in data['slots']:
                        item = data['slots'][slot]
                        if (item != None) and (item['name'] == iInfo['name']):
                            resolve()
            def cantEquipCheck(data):
                if data['id'] == self.id and data['message'] == "CAN'T EQUIP":
                    reject(f"Can't equip '{inventoryPos}' ({iInfo['name']})")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"equip timeout ({Constants.TIMEOUT}s)")
            self.socket.on('player', equipCheck)
            self.socket.on('disappearing_text', cantEquipCheck)
            await self.socket.emit('equip', { 'num': inventoryPos, 'slot': equipSlot })
            while not equipFinished.done():
                await asyncio.sleep(Constants.SLEEP)
            return equipFinished.result()
        
        return await Tools.tryExcept(equipFn)

    async def exchange(self, inventoryPos):
        async def exchangeFn():
            nonlocal self
            nonlocal inventoryPos
            if not self.ready:
                raise Exception("We aren't ready yet [exchange].")
            if self.items[inventoryPos] == None:
                raise Exception(f"No item in inventory slot {inventoryPos}.")
            if Tools.hasKey(self.G['maps'][self.map], 'mount'):
                raise Exception("We can't exchange things in the bank.")
            global startedExchange 
            startedExchange = False
            if Tools.hasKey(self.q, 'exchange'):
                startedExchange = True
            exchangeFinished = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not exchangeFinished.done():
                    self.socket.off('player', completeCheck)
                    self.socket.off('game_response', bankCheck)
                    exchangeFinished.set_exception(Exception(reason))
            def resolve(value = None):
                if not exchangeFinished.done():
                    self.socket.off('player', completeCheck)
                    self.socket.off('game_response', bankCheck)
                    exchangeFinished.set_result(value)
            def completeCheck(data):
                if (not startedExchange) and Tools.hasKey(data['q'], 'exchange'):
                    startedExchange = True
                    return
                if startedExchange and not Tools.hasKey(data['q'], 'exchange'):
                    resolve()
            def bankCheck(data):
                if isinstance(data, dict) and data['response'] == 'bank_restrictions' and data['place'] == 'upgrade':
                    reject("You can't exchange items in the bank.")
                elif isinstance(data, str):
                    if data == 'exchange_notenough':
                        reject("We don't have enough items to exchange.")
                    elif data == 'exchange_existing':
                        reject("We are already exchanging something.")
            Tools.setTimeout(reject, Constants.TIMEOUT * 60, f"exchange timeout ({Constants.TIMEOUT * 60}s)")
            self.socket.on('player', completeCheck)
            self.socket.on('game_response', bankCheck)
            q = self.items[inventoryPos]['q'] if Tools.hasKey(self.items[inventoryPos], 'q') else None
            await self.socket.emit('exchange', { 'item_num': inventoryPos, 'q': q })
            while not exchangeFinished.done():
                await asyncio.sleep(Constants.SLEEP)
            return exchangeFinished.result()
        return await Tools.tryExcept(exchangeFn)

    async def finishMonsterHuntQuest(self):
        async def questFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [finishMonsterHuntQuest].")
            if not Tools.hasKey(self.s, 'monsterhunt'):
                raise Exception("We don't have a monster hunt to turn in.")
            if self.s['monsterhunt']['c'] > 0:
                raise Exception(f"We still have to kill {self.s['monsterhunt']['c']} {self.s['monsterhunt']['id']}(s).")

            close = False
            for npc in self.G['maps'][self.map]['npcs'].values():
                if npc['id'] != 'monsterhunter': continue
                if Tools.distance(self, { 'x': npc['position'][0], 'y': npc['position'][1] }) > Constants.NPC_INTERACTION_DISTANCE: continue
                close = True
                break
            if not close: raise Exception("We are too far away from the Monster Hunter NPC.")
            questFinished = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not questFinished.done():
                    self.socket.off('player', successCheck)
                    questFinished.set_exception(Exception(reason))
            def resolve(value = None):
                if not questFinished.done():
                    self.socket.off('player', successCheck)
                    questFinished.set_result(value)
            def successCheck(data):
                if (not Tools.hasKey(data, 's')) or (not Tools.hasKey(data['s'], 'monsterhunt')):
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"finishMonsterHuntQuest timeout ({Constants.TIMEOUT}s)")
            self.socket.on('player', successCheck)
            await self.socket.emit('monsterhunt')
            while not questFinished.done():
                await asyncio.sleep(Constants.SLEEP)
            return questFinished.result()
        return await Tools.tryExcept(questFn)

    def getEntities(self, *, canDamage = None, canWalkTo = None, couldGiveCredit = None, withinRange = None, targetingMe = None, targetingPartyMember = None, targetingPlayer = None, type = None, typeList = None, level = None, levelGreaterThan = None, levelLessThan = None, willBurnToDeath = None, willDieToProjectiles = None):
        entities = []
        for entity in self.entities.values():
            if targetingMe != None:
                if targetingMe:
                    if entity.target != self.id: continue
                else:
                    if entity.target == self.id: continue
            if targetingPartyMember != None:
                attackingPartyMember = entity.isAttackingPartyMember(self)
                if targetingPartyMember:
                    if not attackingPartyMember: continue
                else:
                    if attackingPartyMember: continue
            if targetingPlayer != None and entity.target != targetingPlayer: continue
            if level != None and entity.level != level: continue
            if levelGreaterThan != None and levelGreaterThan <= entity.level: continue
            if levelLessThan != None and levelLessThan >= entity.level: continue
            if type != None and type != entity.type: continue
            if typeList != None and entity.type not in typeList: continue
            if withinRange != None and Tools.distance(self, entity) > withinRange: continue
            if canDamage != None:
                # We can't damage if avoidance >= 100
                if canDamage and entity.avoidance >= 100: continue
                if not canDamage and entity.avoidance < 100: continue
                # We can't damage if we do physical damage and evasion is >= 100
                if canDamage and self.damage_type == 'physical' and entity.evasion >= 100: continue
                if not canDamage and self.damage_type == 'physical' and entity.evasion < 100: continue
                # We can't damage if we do magical damage and reflection is >= 100
                if canDamage and self.damage_type == 'magical' and entity.reflection >= 100: continue
                if not canDamage and self.damage_type == 'magical' and entity.reflection < 100: continue
            if canWalkTo != None:
                canWalk = Pathfinder.canWalkPath(self, entity)
                if canWalkTo and not canWalk: continue
                if not canWalkTo and canWalk: continue
            if couldGiveCredit != None:
                couldCredit = entity.couldGiveCreditForKill(self)
                if couldGiveCredit and not couldCredit: continue
                if not couldGiveCredit and couldCredit: continue
            if willBurnToDeath != None:
                willBurn = entity.willBurnToDeath()
                if willBurnToDeath and not willBurn: continue
                if not willBurnToDeath and willBurn: continue
            if willDieToProjectiles != None:
                willDie = entity.willDieToProjectiles(self, self.projectiles, self.players, self.entities)
                if willDieToProjectiles and not willDie: continue
                if not willDieToProjectiles and willDie: continue
            
            entities.append(entity)
        return entities

    def getEntity(self, *, canDamage = None, canWalkTo = None, couldGiveCredit = None, withinRange = None, targetingMe = None, targetingPartyMember = None, targetingPlayer = None, type = None, typeList = None, level = None, levelGreaterThan = None, levelLessThan = None, willBurnToDeath = None, willDieToProjectiles = None, returnHighestHP = None, returnLowestHP = None, returnNearest = None):
        ents = self.getEntities(canDamage=canDamage, canWalkTo=canWalkTo, couldGiveCredit=couldGiveCredit, withinRange=withinRange, targetingMe=targetingMe, targetingPartyMember=targetingPartyMember, targetingPlayer=targetingPlayer, type=type, typeList=typeList, level=level, levelGreaterThan=levelGreaterThan, levelLessThan=levelLessThan, willBurnToDeath=willBurnToDeath, willDieToProjectiles=willDieToProjectiles)

        numReturnOptions = 0
        if returnHighestHP != None: numReturnOptions += 1
        if returnLowestHP != None: numReturnOptions += 1
        if returnNearest != None: numReturnOptions += 1
        if numReturnOptions > 1: self.logger.warn("You supplied getEntity with more than one returnX option. This function may not return the entity you want.")

        if len(ents) == 1 or numReturnOptions == 0: return ents[0]

        if returnHighestHP:
            highest = None
            highestHP = 0
            for ent in ents:
                if ent.hp > highestHP:
                    highest = ent
                    highestHP = ent.hp
            return highest
        
        if returnLowestHP:
            lowest = None
            lowestHP = sys.maxsize
            for ent in ents:
                if ent.hp < lowestHP:
                    lowest = ent
                    lowestHP = ent.hp
            return lowest
        
        if returnNearest:
            closest = None
            closestDistance = sys.maxsize
            for ent in ents:
                distance = Tools.distance(self, ent)
                if distance < closestDistance:
                    closest = ent
                    closestDistance = distance
            return closest
    
    def getFirstEmptyInventorySlot(self, items = None):
        if items == None:
            items = self.items
        
        for i in range(0, len(items)):
            item = items[i]
            if item == None:
                return i
        return None

    async def getMonsterHuntQuest(self):
        async def questFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [getMonsterHuntQuest].")
            if Tools.hasKey(self.s, 'monsterhunt') and self.s['monsterhunt']['c'] > 0:
                raise Exception(f"We can't get a new monsterhunt. We have {self.s['monsterhunt']['ms']}ms left to kill {self.s['monsterhunt']['c']} {self.s['monsterhunt']['id']}(s).")
            if self.ctype == 'merchant':
                raise Exception("Merchants can't do Monster Hunts.")
            
            close = False
            for npc in self.G['maps'][self.map]['npcs'].values():
                if npc['id'] != 'monsterhunter': continue
                if Tools.distance(self, { 'x': npc['position'][0], 'y': npc['position'][1] }) > Constants.NPC_INTERACTION_DISTANCE: continue
                close = True
                break
            if not close:
                raise Exception("We are too far away from the Monster Hunter NPC.")
            
            if Tools.hasKey(self.s, 'monsterhunt') and self.s['monsterhunt']['c'] == 0:
                print("We are going to finish the current monster quest first...")
                await self.finishMonsterHuntQuest()
            questGot = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not questGot.done():
                    self.socket.off('game_response', failCheck)
                    self.socket.off('player', successCheck)
                    questGot.set_exception(Exception(reason))
            def resolve(value = None):
                if not questGot.done():
                    self.socket.off('game_response', failCheck)
                    self.socket.off('player', successCheck)
                    questGot.set_result(Exception(value))
            def failCheck(data):
                if data == 'ecu_get_closer':
                    reject("Too far away from Monster Hunt NPC.")
                elif data == 'monsterhunt_merchant':
                    reject("Merchants can't do Monster Hunts.")
            def successCheck(data):
                if not Tools.hasKey(data, 'hitchhikers'): return
                for hitchhiker in data['hitchhikers'].values():
                    if hitchhiker[0] == 'game_response' and hitchhiker[1] == 'monsterhunt_started':
                        resolve()
                        return
            Tools.setTimeout(reject, Constants.TIMEOUT, f"getMonsterHuntQuest timeout ({Constants.TIMEOUT}s)")
            self.socket.on('game_response', failCheck)
            self.socket.on('player', successCheck)
            await self.socket.emit('monsterhunt')
            while not questGot.done():
                await asyncio.sleep(Constants.SLEEP)
            return questGot.result()
        return await Tools.tryExcept(questFn)

    async def getPlayers(self):
        async def playersFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [getPlayers].")
            playersData = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not playersData.done():
                    self.socket.off('players', dataCheck)
                    playersData.set_exception(Exception(reason))
            def resolve(value = None):
                if not playersData.done():
                    self.socket.off('players', dataCheck)
                    playersData.set_result(value)
            def dataCheck(data):
                resolve(data)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"getPlayers timeout ({Constants.TIMEOUT}s)")
            self.socket.on('players', dataCheck)
            await self.socket.emit('players')
            while not playersData.done():
                await asyncio.sleep(Constants.SLEEP)
            return playersData.result()
        return await Tools.tryExcept(playersFn)

    async def getPontyItems(self):
        async def pontyFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [getPontyItems].")
            pontyItems = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not pontyItems.done():
                    self.socket.off('game_response', distanceCheck)
                    self.socket.off('secondhands', secondhandsItems)
                    pontyItems.set_exception(Exception(reason))
            def resolve(value = None):
                if not pontyItems.done():
                    self.socket.off('game_response', distanceCheck)
                    self.socket.off('secondhands', secondhandsItems)
                    pontyItems.set_result(value)
            def distanceCheck(data):
                if data == 'buy_get_closer':
                    reject("Too far away from secondhands NPC.")
            def secondhandsItems(data):
                resolve(data)
            Tools.setTimeout(reject, Constants.TIMEOUT * 5, f"getPontyItems timeout ({Constants.TIMEOUT * 5}s)")
            self.socket.on('secondhands', secondhandsItems)
            self.socket.on('game_response', distanceCheck)
            await self.socket.emit('secondhands')
            while not pontyItems.done():
                await asyncio.sleep(Constants.SLEEP)
            return pontyItems.result()
        return await Tools.tryExcept(pontyFn)

    def getTargetEntity(self):
        return self.entities.get(self.target)

    async def getTrackerData(self):
        async def trackerFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [getTrackerData].")
            if not self.hasItem('tracker'):
                raise Exception("We need a tracker to obtain tracker data.")
            gotData = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not gotData.done():
                    self.socket.off('tracker', gotCheck)
                    gotData.set_exception(Exception(reason))
            def resolve(value = None):
                if not gotData.done():
                    self.socket.off('tracker', gotCheck)
                    gotData.set_result(value)
            def gotCheck(data):
                resolve(data)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"getTrackerData timeout ({Constants.TIMEOUT}s)")
            self.socket.on('tracker', gotCheck)
            await self.socket.emit('tracker')
            while not gotData.done():
                await asyncio.sleep(Constants.SLEEP)
            return gotData.result()
        return await Tools.tryExcept(trackerFn)

    def isFull(self):
        return self.esize == 0

    def isScared(self):
        return self.fear > 0

    async def kickPartyMember(self, toKick):
        async def kickFn():
            nonlocal self
            nonlocal toKick
            if not self.party: return
            if toKick not in self.partyData['list']: return
            if toKick == self.id: return await self.leaveParty()
            if self.partyData['list'].index(self.id) > self.partyData['list'].index(toKick): raise Exception(f"We can't kick {toKick}, they're higher on the party list.")
            kicked = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not kicked.done():
                    self.socket.off('party_update', kickedCheck)
                    kicked.set_exception(Exception(reason))
            def resolve(value = None):
                if not kicked.done():
                    self.socket.off('party_update', kickedCheck)
                    kicked.set_result(value)
            def kickedCheck(data):
                if (not Tools.hasKey(data, 'list')) or (toKick not in data['list']):
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"kickPartyMember timeout ({Constants.TIMEOUT}s)")
            self.socket.on('party_update', kickedCheck)
            await self.socket.emit('party', { 'event': 'kick', 'name': toKick })
            while not kicked.done():
                await asyncio.sleep(Constants.SLEEP)
            return kicked.result()
        return await Tools.tryExcept(kickFn)

    async def leaveMap(self):
        async def leaveFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [leaveMap].")
            leaveComplete = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                self.socket.off('new_map', leaveCheck)
                self.socket.off('game_response', failCheck)
                leaveComplete.set_exception(Exception(reason))
            def resolve(value = None):
                self.socket.off('new_map', leaveCheck)
                self.socket.off('game_response', failCheck)
                leaveComplete.set_result(value)
            def leaveCheck(data):
                if data['name'] == 'main':
                    resolve()
                else:
                    reject(f"We are now in {data['name']}, but we should be in main")
            def failCheck(data):
                if isinstance(data, str):
                    if data == 'cant_escape':
                        reject(f"Can't escape from current map {self.map}")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"leaveMap timeout ({Constants.TIMEOUT}s)")
            self.socket.on('new_map', leaveCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('leave')
            while not leaveComplete.done():
                await asyncio.sleep(Constants.SLEEP)
            return leaveComplete.result()
        return await Tools.tryExcept(leaveFn)

    async def leaveParty(self):
        async def leaveFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [leaveParty].")
            await self.socket.emit('party', { 'event': 'leave' })
            return
        return await Tools.tryExcept(leaveFn)
            
    async def move(self, x, y, *, disableSafetyCheck = False, resolveOnStart = False):
        async def moveFn():
            nonlocal self
            nonlocal x
            nonlocal y
            nonlocal disableSafetyCheck
            nonlocal resolveOnStart
            if not self.ready: raise Exception("We aren't ready yet [move].")
            if x == None or y == None: raise Exception("Please provide an x and y coordinate to move.")
            if not (isinstance(x, int) or isinstance(x, float)) or not (isinstance(y, int) or isinstance(y, float)): raise Exception("Please use a whole number for both x and y.")

            to = { 'map': self.map, 'x': x, 'y': y }
            if not disableSafetyCheck:
                to = Pathfinder.getSafeWalkTo({'map': self.map, 'x': self.x, 'y': self.y}, {'map': self.map, 'x': x, 'y': y})
                if to['x'] != x or to['y'] != y:
                    print(f"move: We can't move to ({x}, {y}) safely. We will move to ({to['x']}, {to['y']}) instead.")
            
            if self.x == to['x'] and self.y == to['y']: return { 'map': self.map, 'x': self.x, 'y': self.y }
            timeToFinishMove = 0.001 + self.ping + Tools.distance(self, { 'x': to['x'], 'y': to['y'] }) / self.speed
            moveFinished = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not moveFinished.done():
                    self.socket.off('player', checkPlayer)
                    moveFinished.set_exception(Exception(reason))
            def resolve(value = None):
                if not moveFinished.done():
                    self.socket.off('player', checkPlayer)
                    moveFinished.set_result(value)
            async def checkPlayer(data):
                nonlocal timeout
                nonlocal timeToFinishMove
                if resolveOnStart:
                    if data['going_x'] == to['x'] and data['going_y'] == to['y']:
                        Tools.clearTimeout(timeout)
                        resolve({ 'map': self.map, 'x': data['x'], 'y': data['y'] })
                    return
                if not data.get('moving') or data.get('going_x') != to['x'] or data.get('going_y') != to['y']:
                    try:
                        newData = await self.requestPlayerData()
                        if newData != None and (not newData['moving'] or newData['going_x'] != to['x'] or newData['going_y'] != to['y']):
                            Tools.clearTimeout(timeout)
                            reject(f"move to ({to['x']}, {to['y']}) failed")
                    except Exception as e:
                        print(e)
                else:
                    timeToFinishMove = 0.001 + self.ping + Tools.distance(self, { 'x': data['going_x'], 'y': data['going_y'] }) / data['speed']
                    Tools.clearTimeout(timeout)
                    timeout = Tools.setTimeout(checkPosition, timeToFinishMove)
            def checkPosition():
                nonlocal timeout
                nonlocal timeToFinishMove
                if resolveOnStart:
                    resolve({ 'map': self.map, 'x': self.x, 'y': self.y })
                    return
                self.updatePositions()
                if self.x == to['x'] and self.y == to['y']:
                    resolve({ 'map': self.map, 'x': to['x'], 'y': to['y'] })
                elif self.moving and self.going_x == to['x'] and self.going_y == to['y']:
                    timeToFinishMove = 0.001 + self.ping + Tools.distance(self, { 'x': to['x'], 'y': to['y'] }) / self.speed
                    timeout = Tools.setTimeout(checkPosition, timeToFinishMove)
                else:
                    reject(f"move to ({to['x']}, {to['y']}) failed (We're currently going from ({self.x}, {self.y}) to ({self.going_x}, {self.going_y}))")
            timeout = Tools.setTimeout(checkPosition, timeToFinishMove)
            self.socket.on('player', checkPlayer)
            if not self.moving or self.going_x != to['x'] or self.going_y != to['y']:
                await self.socket.emit('move', { 'going_x': to['x'], 'going_y': to['y'], 'm': self.m, 'x': self.x, 'y': self.y })
                self.updatePositions()
                self.going_x = to['x']
                self.going_y = to['y']
                self.moving = True
            while not moveFinished.done():
                await asyncio.sleep(Constants.SLEEP)
            return moveFinished.result()

        return await Tools.tryExcept(moveFn)

    async def openChest(self, id):
        async def chestFn():
            nonlocal self
            nonlocal id
            if not self.ready: raise Exception("We aren't ready yet [openChest].")
            chestOpened = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not chestOpened.done():
                    self.socket.off('chest_opened', openCheck)
                    chestOpened.set_exception(Exception(reason))
            def resolve(value = None):
                if not chestOpened.done():
                    self.socket.off('chest_opened', openCheck)
                    chestOpened.set_result(value)
            def openCheck(data):
                if data['id'] == id:
                    resolve(data)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"openChest timeout ({Constants.TIMEOUT}s)")
            self.socket.on('chest_opened', openCheck)
            await self.socket.emit('open_chest', { 'id': id })
            while not chestOpened.done():
                await asyncio.sleep(Constants.SLEEP)
            return chestOpened.result()
        return await Tools.tryExcept(chestFn)

    async def openMerchantStand(self):
        async def standFn():
            if not self.ready: raise Exception("We aren't ready yet [openMerchantStand].")
            if self.stand: return

            stand = None
            for item in ['supercomputer', 'computer', 'stand1', 'stand0']:
                stand = self.locateItem(item)
                if stand != None: break
            if stand == None: raise Exception("Could not find a suitable merchant stand in inventory.")
            opened = asyncio.get_event_loop().create_future()
            def reject(reason=None):
                if not opened.done():
                    self.socket.off('player', checkStand)
                    opened.set_exception(Exception(reason))
            def resolve(value=None):
                if not opened.done():
                    self.socket.off('player', checkStand)
                    opened.set_result(value)
            def checkStand(data):
                if Tools.hasKey(data, 'stand') and data['stand']:
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"openMerchantStand timeout ({Constants.TIMEOUT}s)")
            self.socket.on('player', checkStand)
            await self.socket.emit('merchant', { 'num': stand })
            while not opened.done():
                await asyncio.sleep(Constants.SLEEP)
            return opened.result()
        return await Tools.tryExcept(standFn)

    async def regenHP(self):
        async def regenHPFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [regenHP].")
            regenReceived = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not regenReceived.done():
                    self.socket.off('eval', regenCheck)
                    self.socket.off('disappearing_text', failCheck)
                    regenReceived.set_exception(Exception(reason))
            def resolve(value = None):
                if not regenReceived.done():
                    self.socket.off('eval', regenCheck)
                    self.socket.off('disappearing_text', failCheck)
                    regenReceived.set_result(value)
            def regenCheck(data):
                if Tools.hasKey(data, 'code') and ('pot_timeout' in data['code']):
                    resolve()
            def failCheck(data):
                if data['id'] == self.id and data['message'] == 'NOT READY':
                    reject("regenHP is on cooldown")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"regenHP timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', regenCheck)
            self.socket.on('disappearing_text', failCheck)
            await self.socket.emit('use', { 'item': 'hp' })
            while not regenReceived.done():
                await asyncio.sleep(Constants.SLEEP)
            return regenReceived.result()
        return await Tools.tryExcept(regenHPFn)

    async def regenMP(self):
        async def regenMPFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [regenHP].")
            regenReceived = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not regenReceived.done():
                    self.socket.off('eval', regenCheck)
                    self.socket.off('disappearing_text', failCheck)
                    regenReceived.set_exception(Exception(reason))
            def resolve(value = None):
                if not regenReceived.done():
                    self.socket.off('eval', regenCheck)
                    self.socket.off('disappearing_text', failCheck)
                    regenReceived.set_result(value)
            def regenCheck(data):
                if Tools.hasKey(data, 'code') and ('pot_timeout' in data['code']):
                    resolve()
            def failCheck(data):
                if data['id'] == self.id and data['message'] == 'NOT READY':
                    reject("regenHP is on cooldown")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"regenMP timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', regenCheck)
            self.socket.on('disappearing_text', failCheck)
            await self.socket.emit('use', { 'item': 'mp' })
            while not regenReceived.done():
                await asyncio.sleep(Constants.SLEEP)
            return regenReceived.result()
        return await Tools.tryExcept(regenMPFn)

    async def respawn(self, safe = False):
        async def respawnFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [respawn].")
            respawned = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not respawned.done():
                    self.socket.off('new_map', respawnCheck)
                    self.socket.off('game_log', failCheck)
                    respawned.set_exception(Exception(reason))
            def resolve(value = None):
                if not respawned.done():
                    self.socket.off('new_map', respawnCheck)
                    self.socket.off('game_log', failCheck)
                    respawned.set_result(value)
            def respawnCheck(data):
                if Tools.hasKey(data, 'effect') and data['effect'] == 1:
                    resolve({ 'map': data['name'], 'x': data['x'], 'y': data['y'] })
            def failCheck(data):
                if data == "Can't respawn yet.":
                    reject(data)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"respawn timeout ({Constants.TIMEOUT}s)")
            self.socket.on('new_map', respawnCheck)
            self.socket.on('game_log', failCheck)
            await self.socket.emit('respawn', { 'safe': safe })
            while not respawned.done():
                await asyncio.sleep(Constants.SLEEP)
            return respawned.result()
        return await Tools.tryExcept(respawnFn)

    async def scare(self):
        async def scareFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [scare].")
            
            equipped = self.isEquipped('jacko')
            inInventory = self.hasItem('jacko')
            if (not equipped) and (not inInventory):
                raise Exception('You need a jacko to use scare.')
            
            scared = asyncio.get_event_loop().create_future()
            ids = []
            def reject(reason = None):
                nonlocal scared
                if not scared.done():
                    self.socket.off('ui', idsCheck)
                    self.socket.off('eval', cooldownCheck)
                    scared.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal scared
                if not scared.done():
                    self.socket.off('ui', idsCheck)
                    self.socket.off('eval', cooldownCheck)
                    scared.set_result(value)
            def idsCheck(data):
                nonlocal ids
                if data['type'] == 'scare':
                    ids = data['ids']
                    self.socket.off('ui', idsCheck)
            def cooldownCheck(data):
                nonlocal ids
                match = re.search('skill_timeout\s*\(\s*[\'"]scare[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(ids)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"scare timeout ({Constants.TIMEOUT}s)")
            self.socket.on('ui', idsCheck)
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'scare' })
            while not scared.done():
                await asyncio.sleep(Constants.SLEEP)
            return scared.result()
        return await Tools.tryExcept(scareFn)

    async def sell(self, itemPos, quantity = 1):
        async def sellFn():
            nonlocal self
            nonlocal itemPos
            nonlocal quantity
            if not self.ready:
                raise Exception("We aren't ready yet [sell].")
            if self.map in ['bank', 'bank_b', 'bank_u']:
                raise Exception("We can't sell items in the bank.")
            item = self.items[itemPos]
            if item == None:
                raise Exception(f"We have no item in inventory slot {itemPos} to sell.")
            if Tools.hasKey(item, 'l'):
                raise Exception(f"We can't sell {item['name']}, because it is locked.")
            sold = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not sold.done():
                    self.socket.off('ui', soldCheck)
                    self.socket.off('game_response', failCheck)
                    sold.set_exception(Exception(reason))
            def resolve(value = None):
                if not sold.done():
                    self.socket.off('ui', soldCheck)
                    self.socket.off('game_response', failCheck)
                    sold.set_result(value)
            def soldCheck(data):
                if data.get('type', False) and data['name'] == self.id and int(data['num']) == itemPos:
                    if Tools.hasKey(data.get('item', {}), 'q') and quantity != data['item']['q']:
                        reject(f"Attempted to sell {quantity} {data['item']['name']}(s), but actually sold {data['item']['q']}.")
                    else:
                        resolve(True)
            def failCheck(data):
                if isinstance(data, str):
                    if data == 'item_locked':
                        reject(f"We can't sell {item['name']}, because it is locked.")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"sell timeout ({Constants.TIMEOUT}s)")
            self.socket.on('ui', soldCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('sell', { 'num': itemPos, 'quantity': quantity })
            while not sold.done():
                await asyncio.sleep(Constants.SLEEP)
            return sold.result()
        return Tools.tryExcept(sellFn)

    async def sellToMerchant(self, id, slot, rid, q):
        async def sellFn():
            nonlocal self
            nonlocal id
            nonlocal slot
            nonlocal rid
            nonlocal q
            if not self.ready:
                raise Exception("We aren't ready yet [sellToMerchant].")
            
            # Check if the player buying the item is still valid
            player = self.players.get(id, None)
            if player == None:
                raise Exception(f"{id} is not nearby.")
            
            item = player.slots[slot]
            if item == None:
                raise Exception(f"{id} has no item in slot {slot}")
            if not Tools.hasKey(item, 'b'):
                raise Exception(f"{id}'s slot {slot} is not a buy request.")
            
            ourItem = self.locateItem(item['name'], self.items, { 'level': item['level'], 'locked': False })
            if ourItem == None:
                raise Exception(f"We do not have a {item['name']} to sell to {id}")
        
            sold = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not sold.done():
                    self.socket.off('game_response', failCheck)
                    self.socket.off('ui', soldCheck)
                    sold.set_exception(Exception(reason))
            def resolve(value = None):
                if not sold.done():
                    self.socket.off('game_response', failCheck)
                    self.socket.off('ui', soldCheck)
                    sold.set_result(value)
            def soldCheck(data):
                if data['type'] == "+$$" and data['seller'] == self.id and data['buyer'] == id:
                    resolve()
            def failCheck(data):
                if isinstance(data, str):
                    if data == 'trade_bspace':
                        reject(f"{id} doesn't have enough space, so we can't sell items.")
            
            #TODO: Add a check that the merchant has enough money

            Tools.setTimeout(reject, Constants.TIMEOUT, f"sellToMerchant timeout ({Constants.TIMEOUT}s)")
            self.socket.on('ui', soldCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('trade_sell', { 'id': id, 'q': q, 'rid': rid, 'slot': slot })
            while not sold.done():
                await asyncio.sleep(Constants.SLEEP)
            return sold.result()
        return await Tools.tryExcept(sellFn)

    async def sendCM(self, to, message):
        async def cmFn():
            nonlocal self
            nonlocal to
            nonlocal message
            if not self.ready:
                raise Exception("We aren't ready yet [sendCM].")
            await self.socket.emit('cm', { 'message': message, 'to': to })
        return await Tools.tryExcept(cmFn)

    async def sendMail(self, to, subject, message, item = False):
        async def mailFn():
            nonlocal self
            nonlocal to
            nonlocal subject
            nonlocal message
            nonlocal item
            await self.socket.emit('mail', { 'item': item, 'message': message, 'subject': subject, 'to': to })
        return await Tools.tryExcept(mailFn)

    async def sendPM(self, to, message):
        async def sendFn():
            if not self.ready:
                raise Exception("We aren't ready yet [sendPM].")
            sent = asyncio.get_event_loop().create_future()
            isReceived = False
            def reject(reason = None):
                if not sent.done():
                    self.socket.off('pm', sentCheck)
                    sent.set_exception(Exception(reason))
            def resolve(value = None):
                if not sent.done():
                    self.socket.off('pm', sentCheck)
                    sent.set_result(value)
            def sentCheck(data):
                if data['message'] == message and data['owner'] == self.id and data['to'] == to:
                    nonlocal isReceived
                    isReceived = True
                if data['message'] == '(FAILED)' and data['owner'] == self.id and data['to'] == to:
                    reject(f'Failed sending a PM to {to}.')
            def timeoutFn():
                nonlocal isReceived
                if isReceived:
                    resolve(True)
                else:
                    reject('send timeout (5s)')
            Tools.setTimeout(timeoutFn, 5)
            self.socket.on('pm', sentCheck)
            await self.socket.emit('say', { 'message': message, 'name': to })
            while not sent.done():
                await asyncio.sleep(Constants.SLEEP)
            return sent.result()
        return await Tools.tryExcept(sendFn)

    async def say(self, message):
        async def sentFn():
            nonlocal self
            nonlocal message
            if not self.ready:
                raise Exception("We aren't ready yet [say].")
            sent = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not sent.done():
                    self.socket.off('chat_log', sentCheck)
                    self.socket.off('game_error', failCheck)
                    sent.set_exception(Exception(reason))
            def resolve(value = None):
                if not sent.done():
                    self.socket.off('chat_log', sentCheck)
                    self.socket.off('game_error', failCheck)
                    sent.set_result(value)
            def sentCheck(data):
                if data['message'] == message and data['owner'] == self.id:
                    resolve()
            def failCheck(data):
                if data == "You can't chat this fast.":
                    reject("You can't chat this fast.")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"say timeout ({Constants.TIMEOUT})")
            self.socket.on('chat_log', sentCheck)
            self.socket.on('game_error', failCheck)
            await self.socket.emit('say', { 'message': message })
            while not sent.done():
                await asyncio.sleep(Constants.SLEEP)
            return sent.result()
        return await Tools.tryExcept(sentFn)

    async def sendFriendRequest(self, id):
        async def friendRequestFn():
            nonlocal self
            nonlocal id
            if not self.ready:
                raise Exception("We aren't ready yet [sendFriendRequest].")
            requestSent = asyncio.get_event_loop().create_future()
            def reject(reason=None):
                nonlocal requestSent
                if not requestSent.done():
                    self.socket.off('game_response', check)
                    requestSent.set_exception(Exception(reason))
            def resolve(value=None):
                nonlocal requestSent
                if not requestSent.done():
                    self.socket.off('game_response', check)
                    requestSent.set_result(value)
            def check(data):
                if isinstance(data, str):
                    if data == 'friend_already' or data == 'friend_rsent':
                        resolve()
                    elif data == 'friend_rleft':
                        reject(f"{id} is not online on the same server.")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"sendFriendRequest timeout ({Constants.TIMEOUT}s)")
            self.socket.on('game_response', check)
            await self.socket.emit('friend', { 'event': 'request', 'name': id })
            while not requestSent.done():
                await asyncio.sleep(Constants.SLEEP)
            return requestSent.result()
        return await Tools.tryExcept(friendRequestFn)

    async def sendGold(self, to, amount):
        async def sendFn():
            nonlocal self
            nonlocal to
            nonlocal amount
            if not self.ready:
                raise Exception("We aren't ready yet [sendGold].")
            if self.gold == 0:
                raise Exception("We have no gold to send.")
            if not Tools.hasKey(self.players, to):
                raise Exception(f"We can't se {to} nearby to send gold.")
            if Tools.distance(self, self.players.get(to)) > Constants.NPC_INTERACTION_DISTANCE:
                raise Exception(f"We are too far away from {to} to send gold.")
            goldSent = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self
                nonlocal goldSent
                if not goldSent.done():
                    self.socket.off('game_response', sentCheck)
                    goldSent.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self
                nonlocal goldSent
                if not goldSent.done():
                    self.socket.off('game_response', sentCheck)
                    goldSent.set_result(value)
            def sentCheck(data):
                if data == 'trade_get_closer':
                    reject(f"We are too far away from {to} to send gold.")
                elif isinstance(data, dict) and data['response'] == 'gold_sent' and data['name'] == to:
                    if data['gold'] != amount:
                        print(f"We wanted to send {to} {amount} gold, but we sent {data['gold']}.")
                    resolve(data['gold'])
            Tools.setTimeout(reject, Constants.TIMEOUT, f"sendGold timeout ({Constants.TIMEOUT}s)")
            self.socket.on('game_response', sentCheck)
            await self.socket.emit('send', { 'gold': amount, 'name': to })
            while not goldSent.done():
                await asyncio.sleep(Constants.SLEEP)
            return goldSent.result()
        return await Tools.tryExcept(sendFn)

    async def sendItem(self, to, inventoryPos, quantity = 1):
        async def sendFn():
            nonlocal self
            nonlocal inventoryPos
            nonlocal quantity
            if not self.ready:
                raise Exception("We aren't ready yet [sendItem].")
            if not Tools.hasKey(self.players, to):
                raise Exception(f"{to} is not nearby.")
            item = self.items[inventoryPos]
            if item == None:
                raise Exception(f"No item in inventory slot {inventoryPos}.")
            if item['q'] < quantity:
                raise Exception(f"We only have a quantity of {item['q']}, not {quantity}.")
            itemSent = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not itemSent.done():
                    self.socket.off('game_response', sentCheck)
                    itemSent.set_exception(Exception(reason))
            def resolve(value = None):
                if not itemSent.done():
                    self.socket.off('game_response', sentCheck)
                    itemSent.set_result(value)
            def sentCheck(data):
                if data == 'trade_get_closer':
                    reject(f"sendItem failed, {to} is too far away")
                elif data == 'send_no_space':
                    reject(f"sendItem failed, {to} has no inventory space")
                elif isinstance(data, dict) and data['response'] == 'item_sent' and data['name'] == to and data['item'] == item['name'] and data['q'] == quantity:
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"sendItem timeout ({Constants.TIMEOUT}s)")
            self.socket.on('game_response', sentCheck)
            await self.socket.emit('send', { 'name': to, 'num': inventoryPos, 'q': quantity })
            while not itemSent.done():
                await asyncio.sleep(Constants.SLEEP)
            return itemSent.result()
        return await Tools.tryExcept(sendFn)

    async def sendPartyInvite(self, id):
        async def inviteFn():
            nonlocal self
            nonlocal id
            if not self.ready:
                raise Exception("We aren't ready yet [sendPartyInvite].")
            invited = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal invited
                if not invited.done():
                    self.socket.off('game_log', sentCheck)
                    invited.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal invited
                if not invited.done():
                    self.socket.off('game_log', sentCheck)
                    invited.set_result(value)
            def sentCheck(data):
                if data == f"Invited {id} to party":
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"sendPartyInvite timeout ({Constants.TIMEOUT}s)")
            self.socket.on('game_log', sentCheck)
            await self.socket.emit('party', { 'event': 'invite', 'name': id })
            while not invited.done():
                await asyncio.sleep(Constants.SLEEP)
            return invited.result()
        return await Tools.tryExcept(inviteFn)

    async def sendPartyRequest(self, id):
        async def sendFn():
            nonlocal self
            nonlocal id
            if not self.ready:
                raise Exception("We aren't ready yet [sendPartyRequest].")
            await self.socket.emit('party', { 'event': 'request', 'name': 'id' })
        return await Tools.tryExcept(sendFn)

    async def shiftBooster(self, booster, to):
        async def shiftFn():
            nonlocal self
            nonlocal booster
            nonlocal to
            if not self.ready:
                raise Exception("We aren't ready yet [shiftBooster].")
            if to not in ['goldbooster', 'luckbooster', 'xpbooster']:
                raise ValueError(f"'to' value must be 'goldbooster', 'luckbooster', or 'xpbooster' but is '{to}'")
            itemInfo = self.items[booster]
            if itemInfo == None:
                raise Exception(f"Inventory slot {booster} is empty.")
            if itemInfo['name'] not in ['goldbooster', 'luckbooster', 'xpbooster']:
                raise Exception(f"The given item is not a booster (it's a '{itemInfo['name']}')")
            await self.socket.emit('booster', { 'action': 'shift', 'num': booster, 'to': to })
        return await Tools.tryExcept(shiftFn)

    async def smartMove(self, to, *, avoidTownWarps = False, getWithin = 0, useBlink = False, costs = None):
        async def smartMoveFn():
            nonlocal self
            nonlocal to
            nonlocal avoidTownWarps
            nonlocal getWithin
            nonlocal useBlink
            nonlocal costs
            if not self.ready:
                raise Exception("We aren't ready yet [smartMove].")
            if self.rip:
                raise Exception("We can't smartMove; we are dead.")
            if costs == None:
                costs = {}
            if costs.get('blink') == None:
                costs['blink'] = self.speed * 3.2 + 250
            if costs.get('town') == None:
                costs['town'] = self.speed * (4 + (min(self.ping, 1) / 0.5))
            if costs.get('transport') == None:
                costs['transport'] = self.speed * (min(self.ping, 1) / 0.5)
            fixedTo = {}
            path = []
            if isinstance(to, str):
                # Check if destination is a map name
                gMap = self.G['maps'].get(to, None)
                if gMap != None:
                    mainSpawn = gMap['spawns'][0]
                    fixedTo = { 'map': to, 'x': mainSpawn[0], 'y': mainSpawn[1] }
                
                # Check if destination is a monster type
                if not fixedTo:
                    gMonster = self.G['monsters'].get(to, None)
                    if gMonster != None:
                        locations = self.locateMonster(to)
                        closestDistance = sys.maxsize
                        for location in locations:
                            potentialPath = await Pathfinder.getPath(self, location, avoidTownWarps=avoidTownWarps, getWithin=getWithin, useBlink=useBlink, costs=costs)
                            distance = Pathfinder.computePathCost(potentialPath)
                            if distance < closestDistance:
                                path = potentialPath
                                fixedTo = path[len(path) - 1]
                                closestDistance = distance

                # Check if destination is an npc role
                if not fixedTo:
                    locations = self.locateNPC(to)
                    closestDistance = sys.maxsize
                    for location in locations:
                        potentialPath = await Pathfinder.getPath(self, location, avoidTownWarps=avoidTownWarps, getWithin=getWithin, useBlink=useBlink, costs=costs)
                        distance = Pathfinder.computePathCost(potentialPath)
                        if distance < closestDistance:
                            path = potentialPath
                            fixedTo = path[len(path) - 1]
                            closestDistance = distance
                
                # Check if destination is an item name. If so, go to NPC that sells it.
                if not fixedTo:
                    gItem = self.G['items'].get(to, None)
                    if gItem != None:
                        for map in self.G['maps'].values():
                            if Tools.hasKey(map, 'ignore'): continue
                            for npc in map['npcs'].values():
                                if not Tools.hasKey(npc, 'items'): continue
                                for item in self.G['npcs'][npc['id']]['items'].values():
                                    if item == to:
                                        return self.smartMove(npc['id'], avoidTownWarps=avoidTownWarps, getWithin=getWithin, useBlink=useBlink, costs=costs)
                
                if not fixedTo:
                    raise Exception(f"Could not find a suitable destination for '{to}'")
            elif to.get('x') != None and to.get('y') != None:
                fixedTo = { 'map': to['map'] if Tools.hasKey(to, 'map') else self.map, 'x': to['x'], 'y': to['y'] }
            else:
                print(to)
                raise Exception("'to' is unsuitable for smartMove. We need a 'map', an 'x', and a 'y'.")
            distance = Tools.distance(self, fixedTo)
            if distance == 0: return fixedTo
            if getWithin >= distance: return { 'map': self.map, 'x': self.x, 'y': self.y }
            self.smartMoving = fixedTo
            try:
                if not path:
                    path = await Pathfinder.getPath(self, fixedTo, avoidTownWarps=avoidTownWarps, getWithin=getWithin, useBlink=useBlink, costs=costs)
            except Exception as e:
                self.smartMoving = None
                raise e
            started = datetime.utcnow().timestamp()
            self.lastSmartMove = started
            numAttempts = 0
            i = 0
            while i < len(path):
                currentMove = path[i]

                if started != self.lastSmartMove:
                    if isinstance(to, str):
                        raise Exception(f"smartMove to {to} cancelled (new smartMove started)")
                    else:
                        raise Exception(f"smartMove to {to['map']}:{to['x']},{to['y']} cancelled (new smartMove started)")
                
                if self.rip:
                    raise Exception("We died while smartMoving")
                
                if getWithin >= Tools.distance(self, fixedTo):
                    break # We're already close enough
                    
                # conditional?

                # 'getWithin' Check
                if currentMove['type'] == 'move' and self.map == fixedTo['map'] and getWithin > 0:
                    angle = math.atan2(self.y - fixedTo['y'], self.x - fixedTo['x'])
                    potentialMove = { 'map': self.map, 'type': 'move', 'x': fixedTo['x'] + math.cos(angle) * getWithin, 'y': fixedTo['y'] + math.sin(angle) * getWithin }
                    if Pathfinder.canWalkPath(self, potentialMove):
                        i = len(path)
                        currentMove = potentialMove
                
                # Shortcut Check
                if currentMove['type'] == 'move':
                    j = i + 1
                    while j < len(path):
                        potentialMove = path[j]
                        if potentialMove['map'] != currentMove['map']: break
                        if potentialMove['type'] == 'town': break
                        if potentialMove['type'] == 'move' and Pathfinder.canWalkPath(self, potentialMove):
                            i = j
                            currentMove = potentialMove
                        j += 1
                
                # Blink Check
                if useBlink and self.canUse('blink'):
                    blinked = False
                    j = len(path) - 1
                    while j > i:
                        potentialMove = path[j]
                        if potentialMove['map'] != self.map:
                            j -= 1
                            continue
                        if Tools.distance(currentMove, potentialMove) < costs['blink']: break

                        roundedMove = {}
                        for [dX, dY] in [[0, 0], [-10, 0], [10, 0], [0, -10], [0, 10], [-10, -10], [-10, 10], [10, -10], [10, 10]]:
                            roundedX = round((potentialMove['x'] + dX) / 10) * 10
                            roundedY = round((potentialMove['y'] + dY) / 10) * 10
                            if not Pathfinder.canStand({ 'map': potentialMove['map'], 'x': roundedX, 'y': roundedY }):
                                j -= 1
                                continue

                            roundedMove = { 'map': potentialMove['map'], 'x': roundedX, 'y': roundedY }
                            break
                        if not roundedMove:
                            j -= 1
                            continue

                        try:
                            await self.blink(roundedMove['x'], roundedMove['y'])
                        except Exception as e:
                            if not self.canUse('blink'): break
                            print(f"Error blinking while smartMoving: {e}, attempting 1 more time")
                            try:
                                await asyncio.sleep(Constants.TIMEOUT / 1000)
                                await self.blink(roundedMove['x'], roundedMove['y'])
                            except Exception as e2:
                                print(f"Failed blinking while smartMoving: {e2}")
                                break
                        await self.stopWarpToTown()
                        i = j - 1
                        blinked = True
                        break
                    if blinked:
                        i += 1
                        continue
                
                # Town Check
                # j = i + 1
                # while j < len(path):
                #     futureMove = path[j]
                #     if currentMove['map'] != futureMove['map']: break
                #     if futureMove['type'] == 'town':
                #         await self.warpToTown()
                #         i = j - 1
                #         break
                #     j += 1

                try:
                    if currentMove['type'] == 'enter':
                        pass
                    elif currentMove['type'] == 'leave':
                        await self.leaveMap()
                    elif currentMove['type'] == 'move':
                        if currentMove['map'] != self.map:
                            raise Exception(f"We are supposed to be in {currentMove['map']}, but we are in {self.map}")
                        await self.move(currentMove['x'], currentMove['y'], disableSafetyCheck=True)
                    elif currentMove['type'] == 'town':
                        await self.warpToTown()
                    elif currentMove['type'] == 'transport':
                        await self.transport(currentMove['map'], currentMove['spawn'])
                except Exception as e:
                    print(e)
                    numAttempts += 1
                    if numAttempts >= 3:
                        self.smartMoving = None
                        raise Exception("We are having some trouble smartMoving...")
                    
                    await self.stopWarpToTown()
                    await self.requestPlayerData()
                    path = await Pathfinder.getPath(self, fixedTo, avoidTownWarps=avoidTownWarps, getWithin=getWithin, useBlink=useBlink, costs=costs)
                    i = -1
                    await asyncio.sleep(Constants.TIMEOUT / 1000)
                i += 1
            self.smartMoving = None
            await self.stopWarpToTown()
            return { 'map': self.map, 'x': self.x, 'y': self.y }
        return await Tools.tryExcept(smartMoveFn)

    async def startKonami(self):
        async def startFn():
            started = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal started
                if not started.done():
                    self.socket.off('game_response', successCheck)
                    started.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal started
                if not started.done():
                    self.socket.off('game_response', successCheck)
                    started.set_result(value)
            def successCheck(data):
                if not isinstance(data, dict):
                    return
                if data['response'] != 'target_lock':
                    return
                resolve(data['monster'])
            Tools.setTimeout(reject, 5, "startKonami timeout (5s)")
            self.socket.on('game_response', successCheck)
            await self.socket.emit('move', { 'key': 'up' })
            await self.socket.emit('move', { 'key': 'up' })
            await self.socket.emit('move', { 'key': 'down' })
            await self.socket.emit('move', { 'key': 'down' })
            await self.socket.emit('move', { 'key': 'left' })
            await self.socket.emit('move', { 'key': 'right' })
            await self.socket.emit('move', { 'key': 'left' })
            await self.socket.emit('move', { 'key': 'right' })
            await self.socket.emit('interaction', { 'key': 'B' })
            await self.socket.emit('interaction', { 'key': 'A' })
            await self.socket.emit('interaction', { 'key': 'enter' })
            while not started.done():
                await asyncio.sleep(Constants.SLEEP)
            return started.result()
        return await Tools.tryExcept(startFn)

    async def stopSmartMove(self):
        async def stopMoveFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [stopSmartMove].")
            self.smartMoving = None
            self.lastSmartMove = datetime.utcnow().timestamp()
            if Tools.hasKey(self.c, 'town'):
                await self.stopWarpToTown()
            return await self.move(self.x, self.y)
        return await Tools.tryExcept(stopMoveFn)

    async def stopWarpToTown(self):
        async def stopWarpFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [stopWarpToTown].")
            await self.socket.emit('stop', { 'action': 'town' })
            return
        return await Tools.tryExcept(stopWarpFn)

    async def swapItems(self, itemPosA, itemPosB):
        async def swapFn():
            nonlocal self
            nonlocal itemPosA
            nonlocal itemPosB
            if not self.ready:
                raise Exception("We aren't ready yet [swapItems].")
            if itemPosA == itemPosB:
                return
            itemDataA = self.items[itemPosA]
            itemDataB = self.items[itemPosB]
            itemsSwapped = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal itemsSwapped
                if not itemsSwapped.done():
                    self.socket.off('player', successCheck)
                    itemsSwapped.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal itemsSwapped
                if not itemsSwapped.done():
                    self.socket.off('player', successCheck)
                    itemsSwapped.set_result(value)
            def successCheck(data):
                nonlocal itemDataA
                nonlocal itemDataB
                checkItemDataA = data['items'][itemPosA]
                checkItemDataB = data['items'][itemPosB]

                if checkItemDataB == itemDataA and checkItemDataA == itemDataB:
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"swapItems timeout ({Constants.TIMEOUT}s)")
            self.socket.on('player', successCheck)
            await self.socket.emit('imove', { 'a': itemPosA, 'b': itemPosB })
            while not itemsSwapped.done():
                await asyncio.sleep(Constants.SLEEP)
            return itemsSwapped.result()
        return await Tools.tryExcept(swapFn)

    async def takeMailItem(self, mailID):
        async def getItemFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [takeMailItem].")
            itemReceived = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal itemReceived
                if not itemReceived.done():
                    self.socket.off('game_response', successCheck)
                    itemReceived.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal itemReceived
                if not itemReceived.done():
                    self.socket.off('game_response', successCheck)
                    itemReceived.set_result(value)
            def successCheck(data):
                if isinstance(data, dict):
                    if data['response'] == 'mail_item_taken':
                        resolve()
            Tools.setTimeout(reject, 5, f"takeMailItem timeout (5s)")
            self.socket.on('game_response', successCheck)
            await self.socket.emit('mail_take_item', { 'id': mailID })
            while not itemReceived.done():
                await asyncio.sleep(Constants.SLEEP)
            return itemReceived.result()
        return await Tools.tryExcept(getItemFn)

    async def throwSnowball(self, target, snowball = None):
        async def throwFn():
            nonlocal self, target, snowball
            if not self.ready:
                raise Exception("We aren't ready yet [throwSnowball].")
            if snowball == None:
                snowball = self.locateItem('snowball')
            if self.G['skills']['snowball']['mp'] > self.mp:
                raise Exception("Not enough MP to throw a snowball.")
            if snowball == None:
                raise Exception("We don't have any snowballs in our inventory.")
            throwStarted = asyncio.get_event_loop().create_future()
            projectile = ''
            def reject(reason = None):
                nonlocal throwStarted
                if not throwStarted.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('eval', cooldownCheck)
                    throwStarted.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal throwStarted
                if not throwStarted.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('eval', cooldownCheck)
                    throwStarted.set_result(value)
            def attackCheck(data):
                nonlocal projectile
                if data['attacker'] == self.id and data['type'] == 'snowball' and data['target'] == target:
                    projectile = data['pid']
            def cooldownCheck(data):
                nonlocal projectile
                match = re.search('skill_timeout\s*\(\s*[\'"]snowball[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(projectile)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"throwSnowball timeout ({Constants.TIMEOUT}s)")
            self.socket.on('action', attackCheck)
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'snowball', 'num': snowball })
            while not throwStarted.done():
                await asyncio.sleep(Constants.SLEEP)
            return throwStarted.result()
        return await Tools.tryExcept(throwFn)

    async def transport(self, map, spawn):
        async def transportFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [transport].")
            transportComplete = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not transportComplete.done():
                    self.socket.off('game_response', failCheck)
                    self.socket.off('new_map', transportCheck)
                    transportComplete.set_exception(Exception(reason))
            def resolve(value = None):
                if not transportComplete.done():
                    self.socket.off('game_response', failCheck)
                    self.socket.off('new_map', transportCheck)
                    transportComplete.set_result(value)
            def transportCheck(data):
                if data['name'] == map:
                    resolve()
                else:
                    reject(f"We are now in {data['name']}, but we should be in {map}")
            def failCheck(data):
                if isinstance(data, dict):
                    if data['response'] == 'bank_opx' and data['reason'] == 'mounted':
                        reject(f"{data['name']} is currently in the bank, we can't enter.")
                elif isinstance(data, str):
                    if data == "cant_enter":
                        reject(f"The door to spawn {spawn} on {map} requires a key. Use 'enter' instead of 'transport'.")
                    elif data == 'transport_cant_locked':
                        reject(f"We haven't unlocked the door to spawn {spawn} on {map}.")
                    elif data == 'transport_cant_reach':
                        reject(f"We are too far away from the door to spawn {spawn} on {map}.")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"transport timeout ({Constants.TIMEOUT}s)")
            self.socket.on('game_response', failCheck)
            self.socket.on('new_map', transportCheck)
            await self.socket.emit('transport', { 's': spawn, 'to': map })
            while not transportComplete.done():
                await asyncio.sleep(Constants.SLEEP)
            return transportComplete.result()
        return await Tools.tryExcept(transportFn)

    async def unequip(self, slot):
        async def unequipFn():
            nonlocal self
            nonlocal slot
            if not self.ready:
                raise Exception("We aren't ready yet [unequip].")
            if not Tools.hasKey(self.slots, slot):
                raise Exception(f"Slot {slot} does not exist.")
            if self.slots[slot] == None:
                raise Exception(f"Slot {slot} is empty; nothing to unequip.")
            if self.esize == 0:
                raise Exception(f"Our inventory is full. We cannot unequip {slot}.")
            
            slotInfo = self.slots[slot]

            unequipped = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal unequipped
                if not unequipped.done():
                    self.socket.off('player', unequipCheck)
                    unequipped.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal unequipped
                if not unequipped.done():
                    self.socket.off('player', unequipCheck)
                    unequipped.set_result(value)
            def unequipCheck(data):
                nonlocal slot
                nonlocal slotInfo
                if data['slots'][slot] == None:
                    inventorySlot = None
                    for i in range(data['isize'] - 1, 0, -1):
                        item = data['items'][i]
                        if item == None:
                            continue
                        same = True
                        for key in slotInfo:
                            if key in ['b', 'grace', 'price', 'rid']:
                                continue
                            if item[key] != slotInfo[key]:
                                same = False
                                break
                        if same:
                            inventorySlot = i
                            break
                    if inventorySlot != None:
                        resolve(inventorySlot)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"unequip timeout ({Constants.TIMEOUT}s)")
            self.socket.on('player', unequipCheck)
            await self.socket.emit('unequip', { 'slot': slot })
            while not unequipped.done():
                await asyncio.sleep(Constants.SLEEP)
            return unequipped.result()
        return await Tools.tryExcept(unequipFn)

    async def unfriend(self, id):
        async def unfriendFn():
            nonlocal self
            nonlocal id
            if not self.ready:
                raise Exception("We aren't ready yet [unfriend].")
            unfriended = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal unfriended
                if not unfriended.done():
                    self.socket.off('friend', check)
                    self.socket.off('game_response', failCheck)
                    unfriended.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal unfriended
                if not unfriended.done():
                    self.socket.off('friend', check)
                    self.socket.off('game_response', failCheck)
                    unfriended.set_result(value)
            def failCheck(data):
                if isinstance(data, dict):
                    if data['response'] == 'unfriend_failed':
                        reject(f"unfriend failed ({data['reason']})")
            def check(data):
                if data['event'] == 'lost':
                    resolve(data)
            Tools.setTimeout(reject, 2.5, "unfriend timeout (2.5s)")
            self.socket.on('friend', check)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('friend', { 'event': 'unfriend', 'name': id })
            while not unfriended.done():
                await asyncio.sleep(Constants.SLEEP)
            return unfriended.result()
        return await Tools.tryExcept(unfriendFn)

    async def upgrade(self, itemPos, scrollPos, offeringPos = None):
        async def upgradeFn():
            nonlocal self
            nonlocal itemPos
            nonlocal scrollPos
            nonlocal offeringPos
            if not self.ready:
                raise Exception("We aren't ready yet [upgrade].")
            if Tools.hasKey(self.G['maps'][self.map], 'mount'):
                raise Exception("We can't upgrade things in the bank.")
            
            itemInfo = self.items[itemPos]
            scrollInfo = self.items[scrollPos]
            if itemInfo == None:
                raise Exception(f"There is no item in inventory slot {itemPos}.")
            if scrollInfo == None:
                raise Exception(f"There is no scroll in inventory slot {scrollPos}.")
            if not Tools.hasKey(itemInfo, 'upgrade'):
                raise Exception("This item is not upgradable.")
            offeringInfo = self.items[offeringPos] if offeringPos != None else None
            if offeringPos != None and offeringInfo == None:
                raise Exception(f"There is no item in inventory slot {offeringPos} (offering).")
            upgradeComplete = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal upgradeComplete
                if not upgradeComplete.done():
                    self.socket.off('game_response', gameResponseCheck)
                    self.socket.off('player', playerCheck)
                    upgradeComplete.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal upgradeComplete
                if not upgradeComplete.done():
                    self.socket.off('game_response', gameResponseCheck)
                    self.socket.off('player', playerCheck)
                    upgradeComplete.set_result(value)
            def playerCheck(data):
                if not Tools.hasKey(data, 'hitchhikers'):
                    return
                for event, datum in data['hitchhikers'].items():
                    if event == 'game_response' and datum['response'] == 'upgrade_fail' and datum['num'] == itemPos:
                        resolve(False)
                        return
                    elif event == 'game_response' and datum['response'] == 'upgrade_success' and datum['num'] == itemPos:
                        resolve(True)
                        return
            def gameResponseCheck(data):
                nonlocal scrollInfo
                if isinstance(data, dict):
                    if data['place'] == 'upgrade':
                        if data['response'] == 'bank_restriction':
                            reject("You can't upgrade items in the bank.")
                        elif data['response'] == 'item_locked':
                            reject("You can't upgrade locked items.")
                        elif data['response'] == 'get_closer':
                            reject("We are too far away to upgrade items.")
                elif isinstance(data, str):
                    if data == 'bank_restrictions':
                        reject("We can't upgrade things in the bank.")
                    elif data == 'upgrade_in_progress':
                        reject("We are already upgrading something.")
                    elif data == 'upgrade_incompatible_scroll':
                        reject(f"The scroll we are trying to use ({scrollInfo['name']}) isn't a high enough grade to upgrade this item.")
                    elif data == 'upgrade_fail':
                        resolve(False)
                    elif data == 'upgrade_success':
                        resolve(True)
            Tools.setTimeout(reject, 60, "upgrade timeout (60s)")
            self.socket.on('game_response', gameResponseCheck)
            self.socket.on('player', playerCheck)
            await self.socket.emit('upgrade', { 'clevel': self.items[itemPos]['level'], 'item_num': itemPos, 'offering_num': offeringPos, 'scroll_num': scrollPos })
            while not upgradeComplete.done():
                await asyncio.sleep(Constants.SLEEP)
            return upgradeComplete.result()
        return await Tools.tryExcept(upgradeFn)

    async def useHPPot(self, itemPos):
        async def healFn():
            nonlocal self
            nonlocal itemPos
            if not self.ready:
                raise Exception("We aren't ready yet [useHPPot].")
            item = self.items['itemPos']
            if item == None:
                raise Exception(f"There is no item in inventory slot {itemPos}.")
            if self.G['items'][item['name']]['type'] != 'pot':
                raise Exception(f"The item provided ({item['name']} [{itemPos}]) is not a potion.")
            if self.G['items'][item['name']]['gives'][0][0] != 'hp':
                raise Exception(f"The item provided ({item['name']} [{itemPos}]) is not an HP potion.")
            if self.G['items'][item['name']]['gives'][0][1] < 0:
                raise Exception(f"The item provided ({item['name']} [{itemPos}]) is not an HP potion.")
            healReceived = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal healReceived
                if not healReceived.done():
                    self.socket.off('eval', healCheck)
                    self.socket.off('disappearing_text', failCheck)
                    healReceived.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal healReceived
                if not healReceived.done():
                    self.socket.off('eval', healCheck)
                    self.socket.off('disappearing_text', failCheck)
                    healReceived.set_result(value)
            def healCheck(data):
                if Tools.hasKey(data, 'code') and 'pot_timeout' in data['code']:
                    resolve()
            def failCheck(data):
                if data['id'] == self.id and data['message'] == 'NOT READY':
                    reject('useHPPot is on cooldown')
            Tools.setTimeout(reject, Constants.TIMEOUT, f"useHPPot timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', healCheck)
            self.socket.on('disappearing_text', failCheck)
            await self.socket.emit('equip', { 'consume': True, 'num': itemPos })
            while not healReceived.done():
                await asyncio.sleep(Constants.SLEEP)
            return healReceived.result()
        return await Tools.tryExcept(healFn)

    async def useMPPot(self, itemPos):
        async def healFn():
            nonlocal self
            nonlocal itemPos
            if not self.ready:
                raise Exception("We aren't ready yet [useHPPot].")
            item = self.items['itemPos']
            if item == None:
                raise Exception(f"There is no item in inventory slot {itemPos}.")
            if self.G['items'][item['name']]['type'] != 'pot':
                raise Exception(f"The item provided ({item['name']} [{itemPos}]) is not a potion.")
            if self.G['items'][item['name']]['gives'][0][0] != 'mp':
                raise Exception(f"The item provided ({item['name']} [{itemPos}]) is not an MP potion.")
            if self.G['items'][item['name']]['gives'][0][1] < 0:
                raise Exception(f"The item provided ({item['name']} [{itemPos}]) is not an MP potion.")
            healReceived = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal healReceived
                if not healReceived.done():
                    self.socket.off('eval', healCheck)
                    self.socket.off('disappearing_text', failCheck)
                    healReceived.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal healReceived
                if not healReceived.done():
                    self.socket.off('eval', healCheck)
                    self.socket.off('disappearing_text', failCheck)
                    healReceived.set_result(value)
            def healCheck(data):
                if Tools.hasKey(data, 'code') and 'pot_timeout' in data['code']:
                    resolve()
            def failCheck(data):
                if data['id'] == self.id and data['message'] == 'NOT READY':
                    reject('useMPPot is on cooldown')
            Tools.setTimeout(reject, Constants.TIMEOUT, f"useMPPot timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', healCheck)
            self.socket.on('disappearing_text', failCheck)
            await self.socket.emit('equip', { 'consume': True, 'num': itemPos })
            while not healReceived.done():
                await asyncio.sleep(Constants.SLEEP)
            return healReceived.result()
        return await Tools.tryExcept(healFn)

    async def warpToJail(self):
        async def warpFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [warpToJail].")
            return await self.move(100_000, 100_000, disableSafetyCheck=True)
        return await Tools.tryExcept(warpFn)

    async def warpToTown(self):
        async def warpFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [warpToTown].")
            startedWarp = False
            if Tools.hasKey(self.c, 'town'):
                startedWarp = True
            warpComplete = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal warpComplete
                if not warpComplete.done():
                    self.socket.off('player', failCheck)
                    self.socket.off('new_map', warpedCheck)
                    warpComplete.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal warpComplete
                if not warpComplete.done():
                    self.socket.off('player', failCheck)
                    self.socket.off('new_map', warpedCheck)
                    warpComplete.set_result(value)
            def failCheck(data):
                nonlocal startedWarp
                if (not startedWarp) and (Tools.hasKey(data['c'], 'town')):
                    startedWarp = True
                    return
                if startedWarp and not Tools.hasKey(data['c'], 'town'):
                    reject('warpToTown failed.')
            def warpedCheck(data):
                if data['effect'] == 1:
                    resolve({ 'map': data['name'], 'x': data['x'], 'y': data['y'] })
            def startFail():
                nonlocal startedWarp
                if not startedWarp:
                    reject("warpToTown timeout (1s)")
            Tools.setTimeout(startFail, 1)
            Tools.setTimeout(reject, 5, "warpToTown timeout (5s)")
            self.socket.on('player', failCheck)
            self.socket.on('new_map', warpedCheck)
            if not startedWarp:
                await self.socket.emit('town')
            while not warpComplete.done():
                await asyncio.sleep(Constants.SLEEP)
            return warpComplete.result()
        return await Tools.tryExcept(warpFn)

    async def withdrawGold(self, gold):
        async def goldFn():
            nonlocal self
            nonlocal gold
            if not self.ready: raise Exception("We aren't ready yet [withdrawGold].")
            if self.map != 'bank': raise Exception("We need to be in 'bank' to withdraw gold.")
            if gold <= 0: raise Exception("We can't withdraw 0 or less gold.")
            if gold > self.bank['gold']:
                gold = self.bank['gold']
                self.logger.warn(f"We are only going to withdraw {gold} gold.")
            await self.socket.emit('bank', { 'amount': gold, 'operation': 'withdraw' })
        return await Tools.tryExcept(goldFn)

    async def withdrawItem(self, bankPack, bankPos, inventoryPos = -1):
        async def itemFn():
            nonlocal self
            nonlocal bankPack
            nonlocal bankPos
            nonlocal inventoryPos
            if not self.ready: raise Exception("We aren't ready yet [withdrawItem].")
            for i in range(0, 20):
                if Tools.hasKey(self.bank, 'items0'):
                    break
                await asyncio.sleep(250)
            if not Tools.hasKey(self.bank, 'items0'):
                raise Exception("We don't have bank information yet. Please try again later.")
            
            item = self.bank[bankPack][bankPos]
            if item == None:
                raise Exception(f"There is no item in bank {bankPack}[{bankPos}]")
            
            bankPackNum = int(bankPack[5:])
            if ((self.map == 'bank' and (bankPackNum < 0 or bankPackNum > 7))
                or (self.map == 'bank_b' and (bankPackNum < 8 or bankPackNum > 23))
                or (self.map == 'bank_u' and (bankPackNum < 24 or bankPackNum > 47))):
                raise Exception(f"We cannot access {bankPack} on {self.map}.")
            
            itemCount = self.countItem(item['name'])

            swapped = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self
                nonlocal swapped
                if not swapped.done():
                    self.socket.off('player', checkWithdrawal)
                    swapped.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self
                nonlocal swapped
                if not swapped.done():
                    self.socket.off('player', checkWithdrawal)
                    swapped.set_result(value)
            def checkWithdrawal(data):
                nonlocal itemCount
                newCount = self.countItem(item['name'], data['items'])
                if ((Tools.hasKey(item, 'q') and newCount == (itemCount + item['q']))
                    or (not Tools.hasKey(item, 'q') and newCount == (itemCount + 1))):
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"withdrawItem timeout ({Constants.TIMEOUT}s)")
            self.socket.on('player', checkWithdrawal)
            await self.socket.emit('bank', { 'inv': inventoryPos, 'operation': 'swap', 'pack': bankPack, 'str': bankPos })
            while not swapped.done():
                await asyncio.sleep(Constants.SLEEP)
            return swapped.result()
        return await Tools.tryExcept(itemFn)

    async def zapperZap(self, id):
        async def zapFn():
            nonlocal self
            nonlocal id
            if not self.ready: raise Exception("We aren't ready yet [zapperZap].")
            zapped = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self
                nonlocal zapped
                if not zapped.done():
                    self.socket.off('action', successCheck)
                    self.socket.off('game_response', failCheck)
                    zapped.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self
                nonlocal zapped
                if not zapped.done():
                    self.socket.off('action', successCheck)
                    self.socket.off('game_response', failCheck)
                    zapped.set_result(value)
            def successCheck(data):
                if data['attacker'] != self.id: return
                if data['target'] != id: return
                if data['source'] != 'zapperzap': return
                resolve(data['pid'])
            def failCheck(data):
                if isinstance(data, str):
                    if data == 'skill_cant_slot':
                        reject("We don't have a zapper equipped")
                elif isinstance(data, dict):
                    if data['response'] == 'cooldown' and data['skill'] == 'zapperzap':
                        reject(f"zapperzap is on cooldown ({data['ms']}ms remaining)")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"zapperZap timeout ({Constants.TIMEOUT}s)")
            self.socket.on('action', successCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('skill', { 'id': id, 'name': 'zapperzap' })
            while not zapped.done():
                await asyncio.sleep(Constants.SLEEP)
            self.nextSkill['zapperzap'] = datetime.utcnow().timestamp() + (self.G['skills']['zapperzap']['cooldown'] / 1000)
            return zapped.result()
        return await Tools.tryExcept(zapFn)

    def couldDieToProjectiles(self):
        incomingProjectileDamage = 0
        for projectile in self.projectiles.values():
            if not Tools.hasKey(projectile, 'damage'): continue
            if projectile['target'] != self.id: continue

            attacker = None
            if attacker == None and self.id == projectile['attacker']: attacker = self
            if attacker == None: attacker = self.players.get(projectile['attacker'])
            if attacker == None: attacker = self.entities.get(projectile['attacker'])
            if attacker == None:
                incomingProjectileDamage += projectile['damage'] * 2.2
                if incomingProjectileDamage >= self.hp: return True
                continue

            if attacker['damage_type'] == 'physical' and self.evasion >= 100: continue
            if attacker['damage_type'] == 'magical' and self.reflection >= 100: continue

            maximumDamage = attacker.calculateDamageRange(self, projectile['type'])[1]

            incomingProjectileDamage += maximumDamage
            if (incomingProjectileDamage >= self.hp): return True
        return False

    def countItem(self, item, inventory = None, *, level = None, levelGreaterThan = None, levelLessThan = None, locked = None, pvpMarked = None, quantityGreaterThan = None, special = None, statType = None):
        kwargs = { 'level': level, 'levelGreaterThan': levelGreaterThan, 'levelLessThan': levelLessThan, 'locked': locked, 'pvpMarked': pvpMarked, 'quantityGreaterThan': quantityGreaterThan, 'special': special, 'statType': statType }
        count = 0
        for index in self.locateItems(item, inventory, **kwargs):
            curr = inventory[index]
            count += curr['q'] if curr.get('q') != None else 1
        return count

    def getCooldown(self, skill):
        gSkill = self.G['skills'][skill]
        share = gSkill.get('share', None)
        nextSkill = self.nextSkill.get(share) if share != None else self.nextSkill.get(skill)
        if nextSkill == None:
            return 0

        cooldown = nextSkill - datetime.utcnow().timestamp()
        if cooldown <= 0: return 0
        return cooldown
    
    def getNearestAttackablePlayer(self):
        if not self.isPVP(): return None

        closest = None
        closestD = sys.maxsize
        for player in self.players.values():
            if player.s.get('invincible') != None: continue
            if hasattr(player, 'npc'): continue
            d = Tools.distance(self, player)
            if d < closestD:
                closest = player
                closestD = d
        if closest != None:
            return { 'distance': closestD, 'player': closest }
        return None
    
    def hasPvPMarkedItem(self, inv = None):
        if inv == None:
            inv = self.items
        for i in range(0, len(inv)):
            item = inv[i]
            if item != None:
                if item.get('v') != None:
                    return True
        return False

    def hasItem(self, itemName, inv = None, *, level = None, levelGreaterThan = None, levelLessThan = None, locked = None, pvpMarked = None, quantityGreaterThan = None, special = None, statType = None):
        kwargs = { 'level': level, 'levelGreaterThan': levelGreaterThan, 'levelLessThan': levelLessThan, 'locked': locked, 'pvpMarked': pvpMarked, 'quantityGreaterThan': quantityGreaterThan, 'special': special, 'statType': statType }
        return len(self.locateItems(itemName, inv, **kwargs)) > 0
    
    def isCompounding(self):
        return Tools.hasKey(self.q, 'compound')
    
    def isEquipped(self, itemName):
        for slot in self.slots:
            if self.slots[slot] == None: continue
            if self.slots[slot].get('price') != None: continue
            if self.slots[slot]['name'] == itemName: return True
        return False
    
    def isExchanging(self):
        return self.q.get('exchange') != None
    
    def isListedForPurchase(self, itemName):
        for slot in self.slots:
            if self.slots[slot] == None: continue
            if not Tools.hasKey(self.slots[slot], 'price'): continue
            if not Tools.hasKey(self.slots[slot], 'b'): continue
            if self.slots[slot]['name'] == itemName: return True
        return False
    
    def isListedForSale(self, itemName):
        for slot in self.slots:
            if self.slots[slot] == None: continue
            if not Tools.hasKey(self.slots[slot], 'price'): continue
            if Tools.hasKey(self.slots[slot], 'b'): continue
            if self.slots[slot]['name'] == itemName: return True
        return False

    def isOnCooldown(self, skill):
        return self.getCooldown(skill) != 0
    
    def isUpgrading(self):
        return Tools.hasKey(self.q, 'upgrade')
    
    def isPVP(self):
        if Tools.hasKey(self.G['maps'][self.map], 'pvp'): return True
        if Tools.hasKey(self.G['maps'][self.map], 'safe'): return False
        return self.server['pvp']

    def locateItem(self, itemName, inv = None, *, level = None, levelGreaterThan = None, levelLessThan = None, locked = None, pvpMarked = None, quantityGreaterThan = None, special = None, statType = None, returnHighestLevel = False, returnLowestLevel = False ):
        if inv == None:
            inv = self.items
        
        kwargs = { 'level': level, 'levelGreaterThan': levelGreaterThan, 'levelLessThan': levelLessThan, 'locked': locked, 'pvpMarked': pvpMarked, 'quantityGreaterThan': quantityGreaterThan, 'special': special, 'statType': statType }
        
        located = self.locateItems(itemName, inv, **kwargs)

        if len(located) == 0: return None

        if returnHighestLevel:
            if returnLowestLevel:
                raise Exception("Set either return HighestLevel or returnLowestLevel, not both.")
            highestLevel = -1
            highestLevelIndex = None
            for i in range(0, len(located)):
                j = located[i]
                item = inv[j]
                if item['level'] > highestLevel:
                    highestLevel = item['level']
                    highestLevelIndex = i
            return located[highestLevelIndex]
        
        if returnLowestLevel:
            lowestLevel = float('inf')
            lowestLevelIndex = None
            for i in range(0, len(located)):
                j = located[i]
                item = inv[j]
                if item['level'] < lowestLevel:
                    lowestLevel = item['level']
                    lowestLevelIndex = i
            return located[lowestLevelIndex]
        
        return located[0]
    
    def locateItems(self, itemName, inv = None, *, level = None, levelGreaterThan = None, levelLessThan = None, locked = None, pvpMarked = None, quantityGreaterThan = None, special = None, statType = None):
        if inv == None:
            inv = self.items
        
        if quantityGreaterThan == 0:
            quantityGreaterThan = None
        
        found = []
        for i in range(0, len(inv)):
            item = inv[i]
            if item == None: continue
            if item['name'] != itemName: continue

            if level != None:
                if item['level'] != level:
                    continue
            if levelGreaterThan != None:
                if item['level'] <= levelGreaterThan:
                    continue
            if levelLessThan != None:
                if item['level'] >= levelLessThan:
                    continue
            if locked != None:
                if locked and not Tools.hasKey(item, 'l'):
                    continue
                if not locked and Tools.hasKey(item, 'l'):
                    continue
            if pvpMarked != None:
                if pvpMarked and not Tools.hasKey(item, 'v'):
                    continue
                if not pvpMarked and Tools.hasKey(item, 'v'):
                    continue
            if quantityGreaterThan != None:
                if not Tools.hasKey(item, 'q'):
                    continue
                if item['q'] <= quantityGreaterThan:
                    continue
            if special != None:
                if special and not Tools.hasKey(item, 'p'):
                    continue
                if not special and Tools.hasKey(item, 'p'):
                    continue
            if statType != None:
                if item['stat_type'] != statType:
                    continue
            
            found.append(i)
        
        return found
    
    def locateItemsByLevel(self, inventory = None, *, excludeLockedItems = False, excludeSpecialItems = False, minAmount = None):
        def redFn(items, item):
            if item:
                print(item)
                print(inventory.index(item))
                if not Tools.hasKey(item, 'level'): return items
                name = item['name']
                level = item['level']
                if excludeSpecialItems and Tools.hasKey(item, 'p'): return items
                if excludeLockedItems and Tools.hasKey(item, 'l'): return items
                if not Tools.hasKey(items, name):
                    items[name] = {}
                if not Tools.hasKey(items[name], level):
                    items[name][level] = []
                items[name][level].append(inventory.index(item))
            return items
        itemsByLevel = reduce(redFn, inventory, {})

        if minAmount != None:
            for itemName in itemsByLevel:
                for itemLevel in itemsByLevel[itemName]:
                    if len(itemsByLevel[itemName][itemLevel]) < minAmount: del itemsByLevel[itemName][itemLevel]

                if len(itemsByLevel[itemName]) == 0: del itemsByLevel[itemName]
        
        return itemsByLevel

    def locateMonster(self, mType):
        locations = []

        if mType == 'goldenbat': mType = 'bat'
        elif mType == 'snowman': mType = 'arcticbee'

        for mapName in self.G['maps']:
            map = self.G['maps'][mapName]
            if Tools.hasKey(map, 'ignore'): continue
            if Tools.hasKey(map, 'instance') or not Tools.hasKey(map, 'monsters') or len(map['monsters']) == 0: continue

            for monsterSpawn in map['monsters']:
                if monsterSpawn['type'] != mType: continue
                if Tools.hasKey(monsterSpawn, 'boundary'):
                    locations.append({'map': mapName, 'x': (monsterSpawn['boundary'][0] + monsterSpawn['boundary'][2]) / 2, 'y': (monsterSpawn['boundary'][1] + monsterSpawn['boundary'][3]) / 2 })
                elif Tools.hasKey(monsterSpawn, 'boundaries'):
                    for boundary in monsterSpawn['boundaries']:
                        locations.append({'map': boundary[0], 'x': (boundary[1] + boundary[3]) / 2, 'y': (boundary[2] + boundary[4]) / 2})
        
        return locations
    
    def locateNPC(self, npcID):
        locations = []

        for mapName in self.G['maps']:
            map = self.G['maps'][mapName]
            if Tools.hasKey(map, 'ignore'): continue
            if Tools.hasKey(map, 'instance') or not Tools.hasKey(map, 'npcs') or len(map['npcs']) == 0: continue

            for npc in map['npcs']:
                if npc['id'] != npcID: continue

                if Tools.hasKey(npc, 'position'):
                    locations.append({ 'map': mapName, 'x': npc['position'][0], 'y': npc['position'][1] })
                elif Tools.hasKey(npc, 'positions'):
                    for position in npc['positions']:
                        locations.append({ 'map': mapName, 'x': position[0], 'y': position[1] })
        
        return locations
    
    def locateCraftNPC(self, itemName):
        try:
            gCraft = self.G['craft'][itemName]
            if gCraft != None:
                npcToLocate = gCraft['quest'] if Tools.hasKey(gCraft, 'quest') else 'craftsman'
                for mapName in self.G['maps']:
                    gMap = self.G['maps'][mapName]
                    if Tools.hasKey(gMap, 'ignore'): continue

                    for npc in gMap['npcs']:
                        if npc['id'] == npcToLocate:
                            return { 'map': mapName, 'x': npc['position'][0], 'y': npc['position'][1] }
        except:
            self.logger.exception(f"{itemName} is not craftable.")

    def locateExchangeNPC(self, itemName):
        try:
            gItem = self.G['items'][itemName]
            if Tools.hasKey(gItem, 'quest'):
                npcToLocate = None
                for npcName in self.G['npcs']:
                    gNPC = self.G['npcs'][npcName]
                    if Tools.hasKey(gNPC, 'ignore'): continue

                    if gNPC.get('quest', None) == gItem['quest']:
                        npcToLocate = gNPC['id']
                        break
                if npcToLocate != None:
                    for mapName in self.G['maps']:
                        gMap = self.G['maps'][mapName]
                        if Tools.hasKey(gMap, 'ignore'): continue

                        for npc in gMap['npcs']:
                            if npc['id'] == npcToLocate:
                                return { 'map': mapName, 'x': npc['position'][0], 'y': npc['position'][1] }
            
            if gItem['type'] == 'token':
                npcToLocate = None
                for npcName in self.G['npcs']:
                    gNPC = self.G['npcs'][npcName]
                    if Tools.hasKey(gNPC, 'ignore'): continue

                    if gNPC.get('token') == itemName:
                        npcToLocate = gNPC['id']
                        break
                if npcToLocate != None:
                    for mapName in self.G['maps']:
                        gMap = self.G['maps'][mapName]
                        if Tools.hasKey(gMap, 'ignore'): continue

                        for npc in gMap['npcs']:
                            if npc['id'] == npcToLocate:
                                return { 'map': mapName, 'x': npc['position'][0], 'y': npc['position'][1] }
            
            if Tools.hasKey(gItem, 'e'):
                for mapName in self.G['maps']:
                    gMap = self.G['maps'][mapName]
                    if Tools.hasKey(gMap, 'ignore'): continue

                    for npc in gMap['npcs']:
                        if npc['id'] == 'exchange':
                            return { 'map': mapName, 'x': npc['position'][0], 'y': npc['position'][1] }

            raise Exception()
        except:
            self.logger.exception(f"{itemName} is not exchangeable")