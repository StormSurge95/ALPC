from Observer import Observer
from Player import Player
from Entity import Entity
from Tools import Tools
from Constants import Constants
from Pathfinder import Pathfinder
from datetime import datetime
import asyncio
import logging
import re
import sys
import math

class Character(Observer):

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
        super().__init__(serverData, g)
        return

    async def updateLoop(self) -> None:
        if (not bool(self.socket)) or (not self.socket.connected) or (not self.ready):
            self.timeouts['updateLoop'] = Tools.setTimeout(self.updateLoop, Constants.UPDATE_POSITIONS_EVERY_S)
            return

        if (not hasattr(self, 'lastPositionUpdate')):
            self.updatePositions()
            self.timeouts['updateLoop'] = Tools.setTimeout(self.updateLoop, Constants.UPDATE_POSITIONS_EVERY_S)
            return

        if (hasattr(self, 'lastAllEntities')) and (((datetime.now() - self.lastAllEntities).total_seconds()) > Constants.STALE_MONSTER_S):
            await self.requestEntitiesData()

        sSinceLastUpdate = ((datetime.now() - self.lastPositionUpdate).total_seconds())
        if sSinceLastUpdate > Constants.UPDATE_POSITIONS_EVERY_S:
            self.updatePositions()
            self.timeouts['updateLoop'] = Tools.setTimeout(self.updateLoop, Constants.UPDATE_POSITIONS_EVERY_S)
            return
        else:
            self.timeouts['updateLoop'] = Tools.setTimeout(self.updateLoop, Constants.UPDATE_POSITIONS_EVERY_S - sSinceLastUpdate)
            return

    def parseCharacter(self, data) -> None:
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

    def parseEntities(self, data) -> None:
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

    def parseEval(self, data) -> None:
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

    def parseGameResponse(self, data) -> None:
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

    def parseNewMap(self, data) -> None:
        setattr(self, 'going_x', data['x'])
        setattr(self, 'going_y', data['y'])
        setattr(self, 'in', data['in'])
        setattr(self, 'm', data['m'])
        setattr(self, 'moving', False)

        super().parseNewMap(data)
        return

    def parseQData(self, data) -> None:
        if data.get('q', None).get('upgrade', False):
            self.q['upgrade'] = data['q']['upgrade']
        if data.get('q', None).get('compound', False):
            self.q['compound'] = data['q']['compound']
        return

    def setNextSkill(self, skill: str, next: datetime) -> None:
        self.nextSkill[skill] = next
        if self.G['skills'][skill].get('share', False):
            self.nextSkill[self.G['skills'][skill]['share']] = next
        return

    def updatePositions(self) -> None:
        if getattr(self, 'lastPositionUpdate'):
            msSinceLastUpdate = (datetime.now() - self.lastPositionUpdate).total_seconds() * 1000
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

    def disconnectHandler(self) -> None:
        self.ready = False
        return

    def disconnectReasonHandler(self, data = None) -> None:
        self.ready = False
        return

    def friendHandler(self, data) -> None:
        if data['event'] in ['lost', 'new', 'update']:
            self.friends = data['friends']
        return

    def startHandler(self, data) -> None:
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

    def achievementProgressHandler(self, data) -> None:
        self.achievements[data['name']] = data
        return

    def chestOpenedHandler(self, data) -> None:
        del self.chests[data['id']]
        return

    def dropHandler(self, data) -> None:
        self.chests[data['id']] = data
        return

    def evalHandler(self, data) -> None:
        self.parseEval(data)
        return

    def gameErrorHandler(self, data) -> None:
        if type(data) == str:
            print(f'Game Error:\n{data}')
        else:
            print('Game Error:')
            print(str(data))
        return

    def gameResponseHandler(self, data) -> None:
        self.parseGameResponse(data)
        return

    def partyUpdateHandler(self, data) -> None:
        self.partyData = data
        return

    def playerHandler(self, data) -> None:
        self.parseCharacter(data)
        return

    def qDataHandler(self, data) -> None:
        self.parseQData(data)
        return

    def upgradeHandler(self, data) -> None:
        if data['type'] == 'compound' and getattr(self, 'q', {}).get('compound', False):
            del self.q['compound']
        elif data['type'] == 'upgrade' and getattr(self, 'q', {}).get('upgrade', False):
            del self.q['upgrade']
        return

    async def welcomeHandler(self, data) -> None:
        self.server = data
        await self.socket.emit('loaded', {'height': 1080, 'scale': 2, 'success': 1, 'width': 1920})
        await self.socket.emit('auth', {'auth': self.userAuth, 'character': self.characterID, 'height': 1080, 'no_graphics': 'True', 'no_html': '1', 'passphrase': '', 'scale': 2, 'user': self.owner, 'width': 1920})
        return

    async def connect(self) -> bool | None:
        await super(Character, self).connect(False, False)

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
                if type(data) == str:
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
                await asyncio.sleep(Constants.WAIT)
            return connected.result()

        return await Character.tryExcept(connectedFn)

    async def disconnect(self) -> None:
        print('Disconnecting!')

        if self.socket:
            await self.socket.disconnect()
            await self.socket.eio.http.close()

        self.ready = False

        for timer in self.timeouts.values():
            Tools.clearTimeout(timer)
        return

    async def requestEntitiesData(self) -> dict | None:
        if not self.ready:
            raise Exception("We aren't ready yet [requestEntitiesData]")

        async def entitiesDataFn():
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
                await asyncio.sleep(Constants.WAIT)
            return entitiesData.result()

        return await Character.tryExcept(entitiesDataFn)

    async def requestPlayerData(self) -> dict | None:
        if not self.ready:
            raise Exception("We aren't ready yet [requestPlayerData]")

        async def playerDataFn():
            playerData = asyncio.get_event_loop().create_future()
            def resolve(value):
                if not playerData.done():
                    self.socket.off('player', checkPlayerEvent)
                    playerData.set_result(value)
            def checkPlayerEvent(data):
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
                await asyncio.sleep(Constants.WAIT)
            return playerData.result()

        return await Character.tryExcept(playerDataFn)

    async def acceptFriendRequest(self, id: str) -> dict | None:
        if not self.ready:
            raise Exception("We aren't ready yet [acceptFriendRequest].")

        async def friendReqFn():
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
                if type(data) == str:
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
                await asyncio.sleep(Constants.WAIT)
            return friended.result()

        return await Character.tryExcept(friendReqFn)

    async def acceptMagiport(self, name: str) -> dict | None:
        if not self.ready:
            raise Exception("We aren't ready yet [acceptMagiport].")

        async def magiportFn():
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
                await asyncio.sleep(Constants.WAIT)
            return acceptedMagiport.result()

        return await Character.tryExcept(magiportFn)
       
    async def acceptPartyInvite(self, id: str) -> dict | None:
        if not self.ready:
            raise Exception("We aren't ready yet [acceptPartyInvite].")

        async def partyInvFn():
            acceptedInvite = asyncio.get_event_loop().create_future()
            def partyCheck(data):
                if (Tools.hasKey(data, 'list')) and (Tools.hasKey(data['list'], self.id)) and (Tools.hasKey(data['list'], id)):
                    resolve(data)
            
            def unableCheck(data):
                if data == 'Invitation expired':
                    reject(data)
                elif type(data) == str and re.match('^.+? is not found$', data):
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
            
            Tools.setTimeout(reject, Constants.Timeout, f'acceptPartyInvite timeout ({Constants.TIMEOUT}s)')
            self.socket.on('party_update', partyCheck)
            self.socket.on('game_log', unableCheck)
            await self.socket.emit('party', { 'event': 'accept', 'name': id })
            while not acceptedInvite.done():
                await asyncio.sleep(Constants.WAIT)
            return acceptedInvite.result()

        return await Character.tryExcept(partyInvFn)

    async def acceptPartyRequest(self, id: str) -> dict | None:
        if not self.ready:
            raise Exception("We aren't ready yet [acceptPartyRequest].")
        
        async def partyReqFn():
            acceptedRequest = asyncio.get_event_loop().create_future()
            def partyCheck(data):
                if (data.get('list', False)) and (self.id in data['list']) and (id in data['list']):
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
                await asyncio.sleep(Constants.WAIT)
            return acceptedRequest.result()
        
        return await Character.tryExcept(partyReqFn)

    async def basicAttack(self, id: str) -> str | None:
        if not self.ready:
            raise Exception("We aren't ready yet [basicAttack].")
        async def attackFn():
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
            await self.socket.emit('attack', { 'id': id })
            while not attackStarted.done():
                await asyncio.sleep(Constants.WAIT)
            return attackStarted.result()
        return await Character.tryExcept(attackFn)

    async def buy(self, itemName: str, quantity: int = 1) -> int | None:
        if not self.ready:
            raise Exception("We aren't ready yet [buy]")
        if self.gold < self.G['items'][itemName]['g']:
            raise Exception(f"Insufficient gold. We only have {self.gold}, but the item costs {self.G['itsms'][itemName]['g']}")
        
        async def buyFn():
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
            def buyCheck1(data):
                if not data.get('hitchhikers', False):
                    return
                for hitchhiker in data['hitchhikers'].values():
                    if hitchhiker[0] == 'game_response':
                        data = hitchhiker[1]
                        if (type(data) == dict) and (data['response'] == 'buy_success') and (data['name'] == itemName) and (data['q'] == quantity):
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
                await asyncio.sleep(Constants.WAIT)
            return itemReceived.result()
        return await Character.tryExcept(buyFn)

    async def buyWithTokens(self, itemName: str) -> None:
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
        
        async def tokenBuyFn():
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
                if type(data) == str:
                    if data == 'exchange_notenough':
                        reject(f'Not enough tokens to buy {itemName}.')
            Tools.setTimeout(reject, Constants.TIMEOUT, f'buyWithTokens timeout ({Constants.TIMEOUT}s)')
            self.socket.on('player', buyCheck)
            self.socket.on('game_response', failCheck)
            invTokens = self.locateItem(tokenTypeNeeded)
            await self.socket.emit('exchange_buy', { 'name': itemName, 'num': invTokens, 'q': self.items[invTokens]['q'] })
            while not itemReceived.done():
                await asyncio.sleep(Constants.WAIT)
            return itemReceived.result()
        return await Character.tryExcept(tokenBuyFn)

    async def buyFromMerchant(self, id: str, slot: str, rid: str, quantity: int = 1) -> dict | None:
        if not self.ready:
            raise Exception("We aren't ready yet [buyFromMerchant].")
        if quantity <= 0:
            raise Exception(f"We can not buy a quantity of {quantity}.")
        merchant = self.players.get(id, False)
        if not merchant:
            raise Exception(f"We can not see {id} nearby.")
        if Tools.distance(self, merchant) > Constants.NPC_INTERACTION_DISTANCE:
            raise Exception(f"We are too far away from {id} to buy from.")
        
        item = merchant.slots.get(slot, False)
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
        
        async def merchantBuyFn():
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
                await asyncio.sleep(Constants.WAIT)
            return itemBought.result()
        return await Character.tryExcept(merchantBuyFn)

    async def buyFromPonty(self, item: dict) -> None:
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

        async def pontyBuyFn():
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
                if ((Tools.hasKey(item, 'q')) and (numNow == numBefore + item['q'])) or (numNow == numBefore + 1):
                    resolve(None)
            Tools.setTimeout(reject, Constants.TIMEOUT * 5, f"buyFromPonty timeout ({Constants.TIMEOUT * 5}s)")
            self.socket.on('game_log', failCheck)
            self.socket.on('player', successCheck)
            await self.socket.emit('sbuy', { 'rid': item['rid'] })
            while not bought.done():
                await asyncio.sleep(Constants.WAIT)
            return bought.result()
        return await Character.tryExcept(pontyBuyFn)

    def calculateTargets(self) -> dict[str, int]:
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
    
    def calculateDamageRange(self, defender: 'Character' or Entity or Player, skill: str = 'attack') -> list[int]:
        gSkill = self.G['skills'].get(skill, None)

        if gSkill == None:
            raise Exception(f"calculateDamageRange ERROR: '{skill}' isn't a skill!?")

        if hasattr(defender, 'immune') and (skill != 'attack') and (not (Tools.hasKey(gSkill, 'pierces_immunity'))):
            return [0, 0]
        
        if (hasattr(defender, '1hp')) or (skill == 'taunt'):
            if hasattr(self, 'crit'):
                return [1, 2]
            else:
                return [1, 1]
        
        baseDamage = self.attack
        if Tools.hasKey(gSkill, 'damage'):
            baseDamage = gSkill['damage']
        
        if hasattr(defender, 's') and Tools.hasKey(defender.s, 'cursed'):
            baseDamage *= 1.2
        if hasattr(defender, 's') and Tools.hasKey(defender.s, 'marked'):
            baseDamage *= 1.1

        if self.ctype == 'priest':
            baseDamage *= 0.4
        
        damage_type = gSkill.get('damage_type', self.damage_type)

        additionalApiercing = 0
        if Tools.hasKey(gSkill, 'apiercing'):
            additionalApiercing = gSkill['apiercing']
        if damage_type == 'physical':
            baseDamage *= Tools.damage_multiplier(defender.armor - self.apiercing - additionalApiercing)
        elif damage_type == 'magical':
            baseDamage *= Tools.damage_multiplier(defender.resistance - self.rpiercing)
        
        if Tools.hasKey(gSkill, 'damage_multiplier'):
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

    def calculateItemCost(self, item: dict) -> int:
        gInfo = self.G['items'][item['name']]

        cost = gInfo['g']

        if Tools.hasKey(gInfo, 'compound'):
            for i in range(0, int(item['level'])):
                cost *= 3
                scrollLevel = 0
                for grade in gInfo['grades']:
                    if i+1 < grade:
                        scrollInfo = self.G['items'][f'cscroll{scrollLevel}']
                        cost += scrollInfo['g']
                        break
                    scrollLevel += 1
        elif Tools.hasKey(gInfo, 'upgrade'):
            for i in range(0, int(item['level'])):
                scrollLevel = 0
                for grade in gInfo['grades']:
                    if i+1 < grade:
                        scrollInfo = self.G['items'][f'scroll{scrollLevel}']
                        cost += scrollInfo['g']
                        break
                    scrollLevel += 1
        
        if Tools.hasKey(item, 'gift'):
            cost -= (gInfo['g'] - 1)
        
        return cost

    def calculateItemGrade(self, item: dict) -> int:
        gInfo = self.G['items'][item['name']]
        if not Tools.hasKey(gInfo, 'grades'):
            return
        grade = 0
        for level in gInfo['grades']:
            if item['level'] < level:
                break
            grade += 1
        return grade

    def canBuy(self, item: str, ignoreLocation: bool = False) -> bool:
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
    
    def canCraft(self, itemToCraft: str, ignoreLocation: bool = False) -> bool:
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
    
    def canExchange(self, itemToExchange: str, ignoreLocation: bool = False) -> bool:
        gItem = self.G['items'][itemToExchange]
        if (Tools.hasKey(gItem, 'e')) and (self.countItem(itemToExchange) < gItem['e']):
            return False # Not enough of item
        if (not self.hasItem('computer')) and (not self.hasItem('supercomputer')) and (not ignoreLocation):
            exchangeLocation = self.locateExchangeNPC(itemToExchange)
            if Tools.distance(self, exchangeLocation) > Constants.NPC_INTERACTION_DISTANCE:
                return False # No close enough
        
        return True
    
    def canKillInOneShot(self, entity: Entity, skill: str = 'attack') -> bool:
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
    
    def canSell(self) -> bool:
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
    
    def canUpgrade(self, itemPos: int, scrollPos: int, offeringPos: int = -1) -> bool:
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

    def canUse(self, skill: str, *, ignoreCooldown: bool = False, ignoreEquipped: bool = False) -> bool:
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
            if type(gInfoSkill['wtype']) == list:
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
        if not self.ready:
            raise Exception("We aren't ready yet [closeMerchantStand].")
        if not hasattr(self, 'stand'):
            return # It's already closed
        
        async def closeFn():
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
                await asyncio.sleep(Constants.WAIT)
            return closed.result()
        return await Character.tryExcept(closeFn)

    async def compound(self, item1Pos: int, item2Pos: int, item3Pos: int, cscrollPos: int, offeringPos: int = None) -> bool | None:
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
        
        async def compoundFn():
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
                if type(data) == dict:
                    if data['response'] == 'bank_restrictions' and data['place'] == 'compound':
                        reject("You can't compound items in the gank.")
                elif type(data) == str:
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
                await asyncio.sleep(Constants.WAIT)
            return compoundComplete.result()
        
        return await Character.tryExcept(compoundFn)

    async def craft(self, item: str) -> None:
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
            
            # TODO: searchArgs
            searchArgs = {}

            itemPos = self.locateItem(requiredName, self.items, searchArgs)
            if itemPos == None:
                raise Exception(f"We don't have {requiredQuantity} {requiredName} to craft {item}.")
            
            itemPositions.append([i, itemPos])

        async def craftedFn():
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
                    if type(data) == dict:
                        if data['response'] == 'craft' and data['name'] == item:
                            resolve()
                Tools.setTimeout(reject, Constants.TIMEOUT, f"craft timeout ({Constants.TIMEOUT}s)")
                self.socket.on('game_response', successCheck)
                await self.socket.emit('craft', { 'items': itemPositions })
                while not crafted.done():
                    await asyncio.sleep(Constants.WAIT)
                return crafted.result()
            
        return await Character.tryExcept(craftedFn)

    async def depositGold(self, gold: int) -> None:
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
    
    async def depositItem(self, inventoryPos: int, bankPack: str = None, bankSlot: int = -1) -> None:
        if not self.ready:
            raise Exception("We aren't ready yet [depositItem].")
        if self.map not in ['bank', 'bank_b', 'bank_u']:
            raise Exception(f"We're not in the bank (we're in '{self.map}')")

        for i in range(0, 20):
            if self.bank:
                break
            await asyncio.sleep(250)
        if not self.bank:
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
                raise Exception(f"Bank if sull. There is nowhere to place {item['name']}")
        
        bankItemCount = self.countItem(item['name'], self.bank[bankPack])
        async def swapFn():
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
                await asyncio.sleep(Constants.WAIT)
            return swapped.result()
        return await Character.tryExcept(swapFn)

    async def emote(self, emotionName) -> None:
        if not self.ready:
            raise Exception("We aren't ready yet [emote].")
        if not hasattr(self, 'emx') or not Tools.hasKey(self.emx, emotionName):
            raise Exception(f"We don't have the emotion '{emotionName}'")
        
        async def emoteFn():
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
                if type(data) == str:
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
                await asyncio.sleep(Constants.WAIT)
            return emoted.result()
        return await Character.tryExcept(emoteFn)

    async def enter(self, map: str, instance: str = None):
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

        async def enterFn():
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
                if type(data) == str:
                    if data == 'transport_cant_item':
                        reject(f"We don't have the required item to enter {map}.")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"We don't have the required item to enter {map}.")
            self.socket.on('new_map', enterCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('enter', { 'name': instance, 'place': map })
            while not enterComplete.done():
                await asyncio.sleep(Constants.WAIT)
            return enterComplete.result()
        
        return await Character.tryExcept(enterFn)

    async def equip(self, inventoryPos, equipSlot = None) -> None:
        if not self.ready:
            raise Exception("We aren't ready yet [equip].")
        if self.items[inventoryPos] == None:
            raise Exception(f"No item in inventory slot {inventoryPos}.")
        
        iInfo = self.items[inventoryPos]
        async def equipFn():
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
                await asyncio.sleep(Constants.WAIT)
            return equipFinished.result()
        
        return await Character.tryExcept(equipFn)

    async def exchange(self, inventoryPos: int) -> None:
        if not self.ready:
            raise Exception("We aren't ready yet [exchange].")
        if self.items[inventoryPos] == None:
            raise Exception(f"No item in inventory slot {inventoryPos}.")
        if Tools.hasKey(self.G['maps'][self.map], 'mount'):
            raise Exception("We can't exchange things in the bank.")
        
        async def exchangeFn():
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
                if type(data) == dict and data['response'] == 'bank_restrictions' and data['place'] == 'upgrade':
                    reject("You can't exchange items in the bank.")
                elif type(data) == str:
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
                await asyncio.sleep(Constants.WAIT)
            return exchangeFinished.result()
        
        return await Character.tryExcept(exchangeFn)

    async def finishMonsterHuntQuest(self):
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

        async def questFn():
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
                await asyncio.sleep(Constants.WAIT)
            return questFinished.result()
        return await Character.tryExcept(questFn)

    def getEntities(self, *, canDamage: bool = None, canWalkTo: bool = None, couldGiveCredit: bool = None, withinRange: bool = None, targetingMe: bool = None, targetingPartyMember: bool = None, targetingPlayer: str = None, type: str = None, typeList: list[str] = None, level: int = None, levelGreaterThan: int = None, levelLessThan: int = None, willBurnToDeath: bool = None, willDieToProjectiles: bool = None) -> list[Entity]:
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

    def getEntity(self, *, canDamage: bool = None, canWalkTo: bool = None, couldGiveCredit: bool = None, withinRange: bool = None, targetingMe: bool = None, targetingPartyMember: bool = None, targetingPlayer: str = None, type: str = None, typeList: list[str] = None, level: int = None, levelGreaterThan: int = None, levelLessThan: int = None, willBurnToDeath: bool = None, willDieToProjectiles: bool = None, returnHighestHP: bool = None, returnLowestHP: bool = None, returnNearest: bool = None) -> Entity:
        ents = self.getEntities(canDamage=canDamage, canWalkTo=canWalkTo, couldGiveCredit=couldGiveCredit, withinRange=withinRange, targetingMe=targetingMe, targetingPartyMember=targetingPartyMember, targetingPlayer=targetingPlayer, type=type, typeList=typeList, level=level, levelGreaterThan=levelGreaterThan, levelLessThan=levelLessThan, willBurnToDeath=willBurnToDeath, willDieToProjectiles=willDieToProjectiles)

        numReturnOptions = 0
        if returnHighestHP != None: numReturnOptions += 1
        if returnLowestHP != None: numReturnOptions += 1
        if returnNearest != None: numReturnOptions += 1
        if numReturnOptions > 1: print("You supplied getEntity with more than one returnX option. This function may not return the entity you want.")

        if len(ents) == 1 or numReturnOptions == 0: return ents[0]

        if returnHighestHP:
            highest = []
            highestHP = 0
            for ent in ents:
                if ent.hp > highestHP:
                    highest = ent
                    highestHP = ent.hp
            return highest
        
        if returnLowestHP:
            lowest = []
            lowestHP = sys.maxsize
            for ent in ents:
                if ent.hp < lowestHP:
                    lowest = ent
                    lowestHP = ent.hp
            return lowest
        
        if returnNearest:
            closest = []
            closestDistance = sys.maxsize
            for ent in ents:
                distance = Tools.distance(self, ent)
                if distance < closestDistance:
                    closest = ent
                    closestDistance = distance
            return closest
    
    def getFirstEmptyInventorySlot(self, items = None) -> int:
        if items == None:
            items = self.items
        
        for i in range(0, len(items)):
            item = items[i]
            if item == None:
                return i
        return None

    async def getMonsterHuntQuest(self) -> None:
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
        
        async def questFn():
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
                await asyncio.sleep(Constants.WAIT)
            return questGot.result()
        return await Character.tryExcept(questFn)

    async def getPlayers(self) -> dict:
        if not self.ready:
            raise Exception("We aren't ready yet [getPlayers].")
        
        async def playersFn():
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
                await asyncio.sleep(Constants.WAIT)
            return playersData.result()
        return await Character.tryExcept(playersFn)

    async def getPontyItems(self) -> list[dict]:
        if not self.ready:
            raise Exception("We aren't ready yet [getPontyItems].")
        async def pontyFn():
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
                await asyncio.sleep(Constants.WAIT)
            return pontyItems.result()
        return await Character.tryExcept(pontyFn)

    def getTargetEntity(self) -> Entity:
        return self.entities.get(self.target)

    async def getTrackerData(self) -> dict:
        if not self.ready:
            raise Exception("We aren't ready yet [getTrackerData].")
        if not self.hasItem('tracker'):
            raise Exception("We need a tracker to obtain tracker data.")
        
        async def trackerFn():
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
                await asyncio.sleep(Constants.WAIT)
            return gotData.result()
        return await Character.tryExcept(trackerFn)

    def isFull(self) -> bool:
        return self.esize == 0

    def isScared(self) -> bool:
        return self.fear > 0

    async def kickPartyMember(self, toKick: str) -> None:
        if not self.party: return
        if toKick not in self.partyData['list']: return
        if toKick == self.id: return await self.leaveParty()
        if self.partyData['list'].index(self.id) > self.partyData['list'].index(toKick): raise Exception(f"We can't kick {toKick}, they're higher on the party list.")

        async def kickFn():
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
                await asyncio.sleep(Constants.WAIT)
            return kicked.result()
        return await Character.tryExcept(kickFn)

    async def leaveMap(self) -> None:
        if not self.ready: raise Exception("We aren't ready yet [leaveMap].")
        async def leaveFn():
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
                if type(data) == str:
                    if data == 'cant_escape':
                        reject(f"Can't escape from current map {self.map}")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"leaveMap timeout ({Constants.TIMEOUT}s)")
            self.socket.on('new_map', leaveCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('leave')
            while not leaveComplete.done():
                await asyncio.sleep(Constants.WAIT)
            return leaveComplete.result()
        return await Character.tryExcept(leaveFn)

    async def leaveParty(self) -> None:
        if not self.ready: raise Exception("We aren't ready yet [leaveParty].")
        await self.socket.emit('party', { 'event': 'leave' })
        return

    async def move(self, x: int, y: int, *, disableSafetyCheck: bool = False, resolveOnStart: bool = False) -> dict[str, int|str]:
        if not self.ready: raise Exception("We aren't ready yet [move].")
        if x == None or y == None: raise Exception("Please provide an x and y coordinate to move.")
        if not (type(x) == int or type(x) == float) or not (type(y) == int or type(y) == float): raise Exception("Please use a whole number for both x and y.")

        to = { 'map': self.map, 'x': x, 'y': y }
        if not disableSafetyCheck:
            to = Pathfinder.getSafeWalkTo({'map': self.map, 'x': self.x, 'y': self.y}, {'map': self.map, 'x': x, 'y': y})
            if to['x'] != x or to['y'] != y:
                print(f"move: We can't move to ({x}, {y}) safely. We will move to ({to['x']}, {to['y']}) instead.")
        
        if self.x == to['x'] and self.y == to['y']: return { 'map': self.map, 'x': self.x, 'y': self.y }

        async def moveFn():
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
                if not data['moving'] or data['going_x'] != to['x'] or data['going_y'] != to['y']:
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
            while not moveFinished.done():
                await asyncio.sleep(Constants.WAIT)
            return moveFinished.result()
        if not self.moving or self.going_x != to['x'] or self.going_y != to['y']:
            await self.socket.emit('move', { 'going_x': to['x'], 'going_y': to['y'], 'm': self.m, 'x': self.x, 'y': self.y })
            self.updatePositions()
            self.going_x = to['x']
            self.going_y = to['y']
            self.moving = True

        return await Character.tryExcept(moveFn)

    async def openChest(self, id: str) -> dict:
        if not self.ready: raise Exception("We aren't ready yet [openChest].")
        async def chestFn():
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
                await asyncio.sleep(Constants.WAIT)
            return chestOpened.result()
        return await Character.tryExcept(chestFn)

    async def openMerchantStand(self) -> None:
        if not self.ready: raise Exception("We aren't ready yet [openMerchantStand].")
        if self.stand: return

        stand = None
        for item in ['supercomputer', 'computer', 'stand1', 'stand0']:
            stand = self.locateItem(item)
            if stand != None: break
        if stand == None: raise Exception("Could not find a suitable merchant stand in inventory.")

        async def standFn():
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
                await asyncio.sleep(Constants.WAIT)
            return opened.result()
        return await Character.tryExcept(standFn)

    async def regenHP(self) -> None:
        if not self.ready:
            raise Exception("We aren't ready yet [regenHP].")
        async def regenHPFn():
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
                await asyncio.sleep(Constants.WAIT)
            return regenReceived.result()
        return await Character.tryExcept(regenHPFn)

    async def regenMP(self) -> None:
        if not self.ready:
            raise Exception("We aren't ready yet [regenHP].")
        async def regenMPFn():
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
                await asyncio.sleep(Constants.WAIT)
            return regenReceived.result()
        return await Character.tryExcept(regenMPFn)

    async def respawn(self, safe: bool = False):
        if not self.ready:
            raise Exception("We aren't ready yet [respawn].")
        
        async def respawnFn():
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
                await asyncio.sleep(Constants.WAIT)
            return respawned.result()
        return await Character.tryExcept(respawnFn)

    async def scare(self) -> list[str]:
        if not self.ready:
            raise Exception("We aren't ready yet [scare].")
        
        equipped = self.isEquipped('jacko')
        inInventory = self.hasItem('jacko')
        if (not equipped) and (not inInventory):
            raise Exception('You need a jacko to use scare.')
        
        async def scareFn():
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
                await asyncio.sleep(Constants.WAIT)
            return scared.result()
        return await Character.tryExcept(scareFn)

    async def sell(self, itemPos: int, quantity: int = 1) -> bool:
        if not self.ready:
            raise Exception("We aren't ready yet [sell].")
        if self.map in ['bank', 'bank_b', 'bank_u']:
            raise Exception("We can't sell items in the bank.")
        item = self.items[itemPos]
        if item == None:
            raise Exception(f"We have no item in inventory slot {itemPos} to sell.")
        if Tools.hasKey(item, 'l'):
            raise Exception(f"We can't sell {item['name']}, because it is locked.")
        
        async def sellFn():
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
                if type(data) == str:
                    if data == 'item_locked':
                        reject(f"We can't sell {item['name']}, because it is locked.")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"sell timeout ({Constants.TIMEOUT}s)")
            self.socket.on('ui', soldCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('sell', { 'num': itemPos, 'quantity': quantity })
            while not sold.done():
                await asyncio.sleep(Constants.WAIT)
            return sold.result()
        return Character.tryExcept(sellFn)

    async def sellToMerchant(self, id: str, slot: str, rid: str, q: int) -> None:
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
        
        async def sellFn():
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
                if type(data) == str:
                    if data == 'trade_bspace':
                        reject(f"{id} doesn't have enough space, so we can't sell items.")
            
            #TODO: Add a check that the merchant has enough money

            Tools.setTimeout(reject, Constants.TIMEOUT, f"sellToMerchant timeout ({Constants.TIMEOUT}s)")
            self.socket.on('ui', soldCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('trade_sell', { 'id': id, 'q': q, 'rid': rid, 'slot': slot })
            while not sold.done():
                await asyncio.sleep(Constants.WAIT)
            return sold.result()
        return await Character.tryExcept(sellFn)

    async def sendCM(self, to: list[str], message: str) -> None:
        if not self.ready:
            raise Exception("We aren't ready yet [sendCM].")
        
        await self.socket.emit('cm', { 'message': message, 'to': to })

    async def sendMail(self, to: str, subject: str, message: str, item = False) -> None:
        self.socket.emit('mail', { 'item': item, 'message': message, 'subject': subject, 'to': to })

    async def sendPM(self, to: str, message: str) -> bool:
        if not self.ready:
            raise Exception("We aren't ready yet [sendPM].")
        
        async def sendFn():
            sent = asyncio.get_event_loop().create_future()
            isReceived = False
            def reject(reason: str = None):
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
                await asyncio.sleep(Constants.WAIT)
            return sent.result()
        return await Character.tryExcept(sendFn)

    async def say(self, message: str) -> None:
        if not self.ready:
            raise Exception("We aren't ready yet [say].")
        
        async def sentFn():
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
                await asyncio.sleep(Constants.WAIT)
            return sent.result()
        return await Character.tryExcept(sentFn)

    async def sendFriendRequest(self, id: str) -> None:
        if not self.ready:
            raise Exception("We aren't ready yet [sendFriendRequest].")
        
        async def friendRequestFn():
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
                if type(data) == str:
                    if data == 'friend_already' or data == 'friend_rsent':
                        resolve()
                    elif data == 'friend_rleft':
                        reject(f"{id} is not online on the same server.")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"sendFriendRequest timeout ({Constants.TIMEOUT}s)")
            self.socket.on('game_response', check)
            await self.socket.emit('friend', { 'event': 'request', 'name': id })
            while not requestSent.done():
                await asyncio.sleep(Constants.WAIT)
            return requestSent.result()
        return await Character.tryExcept(friendRequestFn)

    async def sendGold(self, to: str, amount: int) -> int:
        if not self.ready:
            raise Exception("We aren't ready yet [sendGold].")
        if self.gold == 0:
            raise Exception("We have no gold to send.")
        if not Tools.hasKey(self.players, to):
            raise Exception(f"We can't se {to} nearby to send gold.")
        if Tools.distance(self, self.players.get(to)) > Constants.NPC_INTERACTION_DISTANCE:
            raise Exception(f"We are too far away from {to} to send gold.")

        async def sendFn():
            goldSent = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not goldSent.done():
                    self.socket.off('game_response', sentCheck)
                    goldSent.set_exception(Exception(reason))
            def resolve(value = None):
                if not goldSent.done():
                    self.socket.off('game_response', sentCheck)
                    goldSent.set_result(value)
            def sentCheck(data):
                if data == 'trade_get_closer':
                    reject(f"We are too far away from {to} to send gold.")
                elif type(data) == dict and data['response'] == 'gold_sent' and data['name'] == to:
                    if data['gold'] != amount:
                        print(f"We wanted to send {to} {amount} gold, but we sent {data['gold']}.")
                    resolve(data['gold'])
            Tools.setTimeout(reject, Constants.TIMEOUT, f"sendGold timeout ({Constants.TIMEOUT}s)")
            self.socket.on('game_response', sentCheck)
            await self.socket.emit('send', { 'gold': amount, 'name': to })
            while not goldSent.done():
                await asyncio.sleep(Constants.WAIT)
            return goldSent.result()
        return await Character.tryExcept(sendFn)

    async def sendItem(self, to: str, inventoryPos: int, quantity: int = 1) -> None:
        pass

    async def sendPartyInvite(self, id: str) -> None:
        pass

    async def sendPartyRequest(self, id: str) -> None:
        pass

    async def shiftBooster(booster: int, to: str) -> None:
        pass

    lastSmartMove = datetime.now()
    smartMoving = None
    async def smartMove(self, to, *, avoidTownWarps: bool = False, getWithin: int = 0, useBlink: bool = False, costs: dict = None) -> dict[str, int | str]:
        if not self.ready:
            raise Exception("We aren't ready yet [smartMove].")
        
        if self.rip:
            raise Exception("We can't smartMove; we are dead.")

        if costs == None:
            costs = {}
        if (not Tools.hasKey(costs, 'blink')) or costs['blink'] == None:
            costs['blink'] = self.speed * 3.2 + 250
        if (not Tools.hasKey(costs, 'town')) or costs['town'] == None:
            costs['town'] = self.speed * (4 + (min(self.ping, 1) / 0.5))
        if (not Tools.hasKey(costs, 'transport')) or costs['transport'] == None:
            costs['transport'] = self.speed * (min(self.ping, 1) / 0.5)
        
        fixedTo = {}
        path = []
        if type(to) == str:
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
        elif Tools.hasKey(to, 'x') and Tools.hasKey(to, 'y'):
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
        
        started = datetime.now()
        self.lastSmartMove = started
        numAttempts = 0
        i = 0
        while i < len(path):
            currentMove = path[i]

            if started != self.lastSmartMove:
                if type(to) == str:
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
            j = i + 1
            while j < len(path):
                futureMove = path[j]
                if currentMove['map'] != futureMove['map']: break
                if futureMove['type'] == 'town':
                    await self.warpToTown()
                    i = j - 1
                    break
                j += 1
            
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

    async def startKonami(self) -> str:
        pass

    async def stopSmartMove(self) -> dict[str, int|str]:
        pass

    async def stopWarpToTown(self) -> None:
        pass

    async def swapItems(self, itemPosA: int, itemPosB: int) -> None:
        pass

    async def takeMailItem(self, mailID: str) -> None:
        pass

    async def throwSnowball(self, target: str, snowball: int = None) -> str:
        if snowball == None:
            snowball = self.locateItem('snowball')
        pass

    async def transport(self, map: str, spawn: int):
        if not self.ready:
            raise Exception("We aren't ready yet [transport].")
        
        async def transportFn():
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
                if type(data) == dict:
                    if data['response'] == 'bank_opx' and data['reason'] == 'mounted':
                        reject(f"{data['name']} is currently in the bank, we can't enter.")
                elif type(data) == str:
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
                await asyncio.sleep(Constants.WAIT)
            return transportComplete.result()
        return await Character.tryExcept(transportFn)

    async def unequip(self, slot: str):
        pass

    async def unfriend(self, id: str):
        pass

    async def upgrade(self, itemPos: int, scrollPos: int, offerPos: int = None):
        pass

    async def useHPPot(self, itemPos: int):
        pass

    async def useMPPot(self, itemPos: int):
        pass

    async def warpToJail(self):
        pass

    async def warpToTown(self):
        if not self.ready:
            raise Exception("We aren't ready yet [warpToTown].")
        startedWarp = False
        if Tools.hasKey(self.c, 'town'):
            startedWarp = True
        async def warpFn():
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
                await asyncio.sleep(Constants.WAIT)
            return warpComplete.result()
        return await Character.tryExcept(warpFn)

    async def withdrawGold(self, gold: int):
        pass

    async def withdrawItem(self, bankPack: str, bankPos: int, inventoryPos: int = -1):
        pass

    async def zapperZap(self, id: str):
        pass

    def couldDieToProjectiles(self):
        pass

    def countItem(self, item: str, inventory: dict = None, filters: dict = {}):
        pass