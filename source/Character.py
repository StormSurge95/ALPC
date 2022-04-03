import Observer
from Entity import Entity
from Tools import Tools
from Constants import Constants
from datetime import datetime
import asyncio
import logging
import re
import sys
import math

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(fmt='%(levelname)s - %(name)s - %(asctime)s - %(funcName)s: %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(handler)

class Character(Observer.Observer):

    def __init__(self, userID: str, userAuth: str, characterID: str, g: dict, serverData: dict):
        self.owner = userID
        self.userAuth = userAuth
        self.characterID = characterID
        self.ready = False
        self.partyData = None
        self.nextSkill = {}
        self.chests = {}
        self.bank = {'gold': 0}
        self.achievements = {}
        self.timeouts = {}
        Observer.Observer.__init__(self, serverData, g)
        return

    async def updateLoopFn(self):
        return await self.updateLoop()

    async def updateLoop(self):
        if (not bool(self.socket)) or (not self.socket.connected) or (not self.ready):
            self.timeouts['updateLoop'] = Tools.setTimeout(self.updateLoopFn, Constants.UPDATE_POSITIONS_EVERY_S)
            return

        if (not hasattr(self, 'lastPositionUpdate')):
            self.updatePositions()
            self.timeouts['updateLoop'] = Tools.setTimeout(self.updateLoopFn, Constants.UPDATE_POSITIONS_EVERY_M)
            return

        if (hasattr(self, 'lastAllEntities')) and (((datetime.now() - self.lastAllEntities).total_seconds()) > Constants.STALE_MONSTER_S):
            await self.requestEntitiesData()

        msSinceLastUpdate = ((datetime.now() - self.lastPositionUpdate).total_seconds())
        if msSinceLastUpdate > Constants.UPDATE_POSITIONS_EVERY_S:
            self.updatePositions()
            self.timeouts['updateLoop'] = Tools.setTimeout(self.updateLoopFn, Constants.UPDATE_POSITIONS_EVERY_S)
            return
        else:
            self.timeouts['updateLoop'] = Tools.setTimeout(self.updateLoopFn, Constants.UPDATE_POSITIONS_EVERY_S - msSinceLastUpdate)
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
            elif datum == 'user':
                self.bank = data['user']
            else:
                setattr(self, datum, data[datum])
        self.name = data['id']
        if not hasattr(self, 'party'):
            self.partyData = None
        if (not hasattr(self, 'damage_type')) and hasattr(self, 'ctype'):
            self.damage_type = self.G['classes'][self.ctype]['damage_type']
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
                cooldown = float(skillReg.group(2))
            if cooldown is not None:
                next = datetime.now() + math.ceil(cooldown)
                self.setNextSkill(skill, next)
            return
        
        potReg = re.search("^pot_timeout\s*\(\s*(\d*\.?\d+)\s*\)", data['code'])
        if potReg is not None:
            cooldown = float(potReg.group(1))
            next = datetime.now() + math.ceil(cooldown)
            self.setNextSkill('regen_hp', next)
            self.setNextSkill('regen_mp', next)
            self.setNextSkill('use_hp', next)
            self.setNextSkill('use_mp', next)
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
        if type(data) == dict:
            if data['response'] == 'cooldown':
                skill = data.get('skill', data.get('place', None))
                if skill is not None:
                    cooldown = data['ms']
                    self.setNextSkill(skill, datetime.now() + math.ceil(cooldown))
            elif data['response'] == 'defeated_by_a_monster':
                pass # we died lol
            elif data['response'] == 'ex_condition':
                del self.s[data['name']]
            elif data['response'] == 'skill_success':
                cooldown = self.G['skills'][data['name']]['cooldown']
                if cooldown is not None:
                    self.setNextSkill(data['name'], datetime.now() + cooldown)
        elif type(data) == str:
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

    def parseQData(self, data):
        if data.get('q', None).get('upgrade', False):
            self.q['upgrade'] = data['q']['upgrade']
        if data.get('q', None).get('compound', False):
            self.q['compound'] = data['q']['compound']
        return

    def setNextSkill(self, skill: str, next: datetime):
        self.nextSkill[skill] = next
        if self.G['skills'][skill].get('share', False):
            self.nextSkill[self.G['skills'][skill]['share']] = next
        return

    def updatePositions(self):
        if getattr(self, 'lastPositionUpdate'):
            msSinceLastUpdate = (datetime.now() - self.lastPositionUpdate).total_seconds()
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

    def disconnectHandler(self):
        self.ready = False
        return

    def disconnectReasonHandler(self):
        self.ready = False
        return

    def friendHandler(self, data):
        if data['event'] in ['lost', 'new', 'update']:
            self.friends = data['friends']
        return

    def startHandler(self, data):
        self.going_x = data['x']
        self.going_y = data['y']
        self.moving = False
        self.damage_type = self.G['classes'][data['ctype']]['damage_type']
        self.parseCharacter(data)
        if data.get('entities', False):
            self.parseEntities(data['entities'])
        self.S = data['s_info']
        self.ready = True
        return

    def achievementProgressHandler(self, data):
        self.achievements[data['name']] = data
        return

    def chestOpenedHandler(self, data):
        del self.chests[data['id']]
        return

    def dropHandler(self, data):
        self.chests[data['id']] = data
        return

    def evalHandler(self, data):
        self.parseEval(data)
        return

    def gameErrorHandler(self, data):
        if type(data) == str:
            print(f'Game Error:\n{data}')
        else:
            print('Game Error:')
            print(str(data))
        return

    def gameResponseHandler(self, data):
        self.parseGameResponse(data)
        return

    def partyUpdateHandler(self, data):
        self.partyData = data
        return

    def playerHandler(self, data):
        self.parseCharacter(data)
        return

    def qDataHandler(self, data):
        self.parseQData(data)
        return

    def upgradeHandler(self, data):
        if data['type'] == 'compound' and getattr(self, 'q', {}).get('compound', False):
            del self.q['compound']
        elif data['type'] == 'upgrade' and getattr(self, 'q', {}).get('upgrade', False):
            del self.q['upgrade']
        return

    async def welcomeHandler(self, data):
        await self.socket.emit('loaded', {'height': 1080, 'scale': 2, 'success': 1, 'width': 1920})
        await self.socket.emit('auth', {'auth': self.userAuth, 'character': self.characterID, 'height': 1080, 'no_graphics': 'True', 'no_html': '1', 'passphrase': '', 'scale': 2, 'user': self.owner, 'width': 1920})
        self.welcomeHandler(data)
        return

    async def connect(self):
        await super().connect(False, False)

        self.socket.on('disconnect', self.disconnectHandler)
        self.socket.on('disconnect_reason', self.disconnectReasonHandler)
        self.socket.on('friend', self.friendHandler)
        self.socket.on('start', self.startHandler)
        self.socket.on('achievement_progress', self.achievementProgressHandler)
        self.socket.on('chest_opened', self.chestOpenedHandler)
        self.socket.on('drop', self.dropHandler)
        self.socket.on('eval', self.evalHandler)
        self.socket.on('game_error', self.gameErrorHandler)
        self.socket.on('game_response', self.gameResponseHandler)
        self.socket.on('party_update', self.partyUpdateHandler)
        self.socket.on('player', self.playerHandler)
        self.socket.on('q_data', self.qDataHandler)
        self.socket.on('upgrade', self.upgradeHandler)
        self.socket.on('welcome', self.welcomeHandler)

        async def connectedFn():
            connected = asyncio.get_event_loop().create_future()
            async def failCheck(data):
                if type(data) == str:
                    connected.set_exception(Exception(f'Failed to connect: {data}'))
                else:
                    connected.set_exception(Exception(f'Failed to connect: {data["message"]}'))
                self.socket.on('start', self.startHandler)
                self.socket.on('game_error', self.gameErrorHandler)
                self.socket.on('disconnect_reason', self.disconnectReasonHandler)
            async def failCheck2(data):
                connected.set_exception(Exception(f'Failed to connect: {data}'))

            async def startCheck(data):
                self.socket.on('game_error', self.gameErrorHandler)
                self.socket.on('disconnect_reason', self.disconnectHandler)
                self.startHandler(data)
                self.socket.on('start', self.startHandler)
                await self.updateLoop()
                connected.set_result(None)

            self.socket.on('start', startCheck)
            self.socket.on('game_error', failCheck)
            self.socket.on('disconnect_reason', failCheck2)
            def reject(reason):
                if not connected.done():
                    connected.set_exception(Exception(reason))
            Tools.setTimeout(reject, Constants.CONNECT_TIMEOUT_S, f'Failed to start within {Constants.CONNECT_TIMEOUT_S}s.')
            while not connected.done():
                await asyncio.sleep(0.25)
            return connected.result()

        return await connectedFn()

    async def disconnect(self):
        print('Disconnecting!')

        if self.socket:
            await self.socket.disconnect()

        self.ready = False

        for timer in self.timeouts.values():
            Tools.clearTimeout(timer)
        return

    async def requestEntitiesData(self):
        print('requestEntitiesData called...')
        if not self.ready:
            raise Exception("We aren't ready yet [requestEntitiesData]")

        async def entitiesDataFn():
            entitiesData = asyncio.get_event_loop().create_future()
            async def checkEntitiesEvent(data):
                if data['type'] == 'all':
                    entitiesData.set_result(data)

            def reject(reason):
                if not entitiesData.done():
                    entitiesData.set_exception(Exception(reason))
            Tools.setTimeout(reject, Constants.TIMEOUT, f'requestEntitiesData timeout ({Constants.TIMEOUT}s)')
            self.socket.on('entities', checkEntitiesEvent)

            await self.socket.emit('send_updates', {})
            while not entitiesData.done():
                await asyncio.sleep(0.25)
            return entitiesData.result()

        self.parseEntities(await entitiesDataFn())
        return

    async def requestPlayerData(self):
        if not self.ready:
            raise Exception("We aren't ready yet [requestPlayerData]")

        async def playerDataFn():
            playerData = asyncio.get_event_loop().create_future()
            def checkPlayerEvent(data):
                if data.get('s', {}).get('typing', False):
                    playerData.set_result(data)
                    self.socket.on('player', self.playerHandler)

            def reject(reason):
                if not playerData.done():
                    playerData.set_exception(Exception(reason))
            Tools.setTimeout(reject, Constants.TIMEOUT, f'requestPlayerData timeout ({Constants.TIMEOUT}s)')
            self.socket.on('player', checkPlayerEvent)

            await self.socket.emit('property', {'typing': True})
            while not playerData.done():
                await asyncio.sleep(0.25)
            return playerData.result()

        self.parseCharacter(await playerDataFn())
        return

    async def acceptFriendRequest(self, id: str):
        if not self.ready:
            raise Exception("We aren't ready yet [acceptFriendRequest].")

        async def friendReqFn():
            friended = asyncio.get_event_loop().create_future()
            def successCheck(data):
                if data['event'] == 'new':
                    self.socket.on('game_response', self.gameResponseHandler)
                    friended.set_result(data)

            def failCheck(data):
                if type(data) == str:
                    if data == 'friend_expired':
                        reject('Friend request expired.')

            def reject(reason):
                if not friended.done():
                    self.socket.on('game_response', self.gameResponseHandler)
                    friended.set_exception(Exception(reason))

            Tools.setTimeout(reject, Constants.TIMEOUT, f'acceptFriendRequest timeout ({Constants.TIMEOUT}s)')
            self.socket.on('friend', successCheck)
            self.socket.on('game_response', failCheck)
            
            await self.socket.emit('friend', { 'event': 'accept', 'name': id })
            while not friended.done():
                await asyncio.sleep(0.25)
            return friended.result()

        await friendReqFn()
        return

    async def acceptMagiport(self, name: str):
        if not self.ready:
            raise Exception("We aren't ready yet [acceptMagiport].")

        async def magiportFn():
            acceptedMagiport = asyncio.get_event_loop().create_future()
            def magiportCheck(data):
                if data.get('effect', "") == 'magiport':
                    self.socket.on('new_map', self.newMapHandler)
                    acceptedMagiport.set_result({'map': data['name'], 'x': data['x'], 'y': data['y'] })

            def reject(reason):
                if not acceptedMagiport.done():
                    self.socket.on('new_map', self.newMapHandler)
                    acceptedMagiport.set_exception(Exception(reason))

            Tools.setTimeout(reject, Constants.TIMEOUT, f'acceptMagiport timeout ({Constants.TIMEOUT}s)')
            self.socket.on('new_map', magiportCheck)
            await self.socket.emit('magiport', { 'name': name })
            while not acceptedMagiport.done():
                await asyncio.sleep(0.25)
            return acceptedMagiport.result()

        await magiportFn()
        return
       
    async def acceptPartyInvite(self, id: str):
        if not self.ready:
            raise Exception("We aren't ready yet [acceptPartyInvite].")

        async def partyInvFn():
            acceptedInvite = asyncio.get_event_loop().create_future()
            def partyCheck(data):
                if ('list' in data.keys()) and (self.id in data['list']) and (id in data['list']):
                    self.socket.on('party_update', self.defaultHandler)
                    self.socket.on('game_log', self.defaultHandler)
                    acceptedInvite.set_result(data)
            
            def unableCheck(data):
                if data == 'Invitation expired':
                    reject(data)
                elif type(data) == str and re.match('^.+? is not found$', data):
                    reject(data)
                elif data == 'Already partying':
                    if (self.id in self.partyData['list']) and (id in self.partyData['list']):
                        self.socket.on('party_update', self.defaultHandler)
                        self.socket.on('game_log', self.defaultHandler)
                        acceptedInvite.set_result(self.partyData)
                    else:
                        reject(data)
            
            def reject(reason):
                if not acceptedInvite.done():
                    self.socket.on('party_update', self.defaultHandler)
                    self.socket.on('game_log', self.defaultHandler)
                    acceptedInvite.set_exception(Exception(reason))
            
            Tools.setTimeout(reject, Constants.Timeout, f'acceptPartyInvite timeout ({Constants.TIMEOUT}s)')
            self.socket.on('party_update', partyCheck)
            self.socket.on('game_log', unableCheck)
            await self.socket.emit('party', { 'event': 'accept', 'name': id })
            while not acceptedInvite.done():
                await asyncio.sleep(0.25)
            return acceptedInvite.result()

        await partyInvFn()
        return

    async def acceptPartyRequest(self, id: str):
        if not self.ready:
            raise Exception("We aren't ready yet [acceptPartyRequest].")
        
        async def partyReqFn():
            acceptedRequest = asyncio.get_event_loop().create_future()
            def partyCheck(data):
                if (data.get('list', False)) and (self.id in data['list']) and (id in data['list']):
                    self.socket.on('party_update', self.defaultHandler)
                    acceptedRequest.set_result(data)
                
            def reject(reason):
                if not acceptedRequest.done():
                    self.socket.on('party_update', self.defaultHandler)
                    acceptedRequest.set_exception(Exception(reason))
            
            Tools.setTimeout(reject, Constants.TIMEOUT, f'acceptPartyRequest timeout {Constants.TIMEOUT}s)')
            self.socket.on('party_update', partyCheck)
            await self.socket.emit('party', { 'event': 'raccept', 'name': id })
            while not acceptedRequest.done():
                await asyncio.sleep(0.25)
            return acceptedRequest.result()
        
        await partyReqFn()
        return

    async def basicAttack(self, id: str):
        if not self.ready:
            raise Exception("We aren't ready yet [basicAttack].")
        async def attackFn():
            attackStarted = asyncio.get_event_loop().create_future()
            def reject(reason):
                if not attackStarted.done():
                    self.socket.on('action', self.defaultHandler)
                    self.socket.on('game_response', self.gameResponseHandler)
                    self.socket.on('notthere', self.defaultHandler)
                    self.socket.on('death', self.defaultHandler)
                    attackStarted.set_exception(Exception(reason))
            def resolve(value):
                if not attackStarted.done():
                    self.socket.on('action', self.defaultHandler)
                    self.socket.on('game_response', self.gameResponseHandler)
                    self.socket.on('notthere', self.defaultHandler)
                    self.socket.on('death', self.defaultHandler)
                    attackStarted.set_result(value)
            def deathCheck(data):
                if data['id'] == id:
                    reject(f'Entity {id} not found')
                return
            def failCheck(data):
                if type(data) == dict:
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
            while not attackStarted.done():
                await asyncio.sleep(0.25)
            return attackStarted.result()
        return await attackFn()

    