import Observer
from Entity import Entity
from Tools import Tools
from Constants import Constants
from datetime import datetime
import asyncio
import socketio
import logging
import ujson
import re
import sys
import math
import promisio

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

    @asyncio.coroutine
    async def updateLoopFn(self):
        return await self.updateLoop();

    @asyncio.coroutine
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
                for [event, datum] in data[hitchhikers].items():
                    if event == 'game_response':
                        self.parseGameResponse(datum)
                    elif event == 'eval':
                        self.parseEval(datum)
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
                partyPlayer = getattr(self, partyData, None).get('party', None).get(player.id, None)
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

    def parseGameResponse(self, data: 'GameResponseData'):
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

    def parseNewMap(self, data: 'NewMapData'):
        setattr(self, 'going_x', data['x'])
        setattr(self, 'going_y', data['y'])
        setattr(self, 'in', data['in'])
        setattr(self, 'm', data['m'])
        setattr(self, 'moving', False)

        super().parseNewMap(data)

    def parseQData(self, data: 'QData'):
        if data.get('q', None).get('upgrade', False):
            self.q['upgrade'] = data['q']['upgrade']
        if data.get('q', None).get('compound', False):
            self.q['compound'] = data['q']['compound']

    def setNextSkill(self, skill: str, next: datetime):
        self.nextSkill[skill] = next
        if self.G['skills'][skill].get('share', False):
            self.nextSkill[self.G['skills'][skill]['share']] = next

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

    async def connect(self):
        await super().connect(False, False)

        @self.socket.event
        def disconnect():
            self.ready = False

        @self.socket.event
        def disconnect_reason():
            self.ready = False

        @self.socket.event
        def friend(data):
            if data['event'] == 'lost' or data['event'] == 'new' or data['event'] == 'update':
                self.friends = data['friends']

        @self.socket.event
        def start(data):
            self.going_x = data['x']
            self.going_y = data['y']
            self.moving = False
            self.damage_type = self.G['classes'][data['ctype']]['damage_type']

            self.parseCharacter(data)
            if data.get('entities', False):
                self.parseEntities(data['entities'])
            self.S = data['s_info']
            self.ready = True

        @self.socket.event
        def achievement_progress(data):
            self.achievements[data['name']] = data

        @self.socket.event
        def chest_opened(data):
            del self.chests[data['id']]

        @self.socket.event
        def drop(data):
            self.chests[data['id']] = data

        @self.socket.event
        def eval(data):
            self.parseEval(data)

        @self.socket.event
        def game_error(data):
            if type(data) == str:
                print(f'Game Error: {data}')
            else:
                print('Game Error:')
                print(str(data))

        @self.socket.event
        def game_response(data):
            self.parseGameResponse(data)

        @self.socket.event
        def party_update(data):
            self.partyData = data

        @self.socket.event
        def player(data):
            self.parseCharacter(data)

        @self.socket.event
        def q_data(data):
            self.parseQData(data)

        @self.socket.event
        def upgrade(data):
            if data['type'] == 'compound' and getattr(self, 'q', {}).get('compound', False):
                del self.q['compound']
            elif data['type'] == 'upgrade' and getattr(self, 'q', {}).get('upgrade', False):
                del self.q['upgrade']

        @self.socket.event
        async def welcome(data):
            await self.socket.emit('loaded', {'height': 1080, 'scale': 2, 'success': 1, 'width': 1920})
            await self.socket.emit('auth', {'auth': self.userAuth, 'character': self.characterID, 'height': 1080, 'no_graphics': 'True', 'no_html': '1', 'passphrase': '', 'scale': 2, 'user': self.owner, 'width': 1920})

        async def connectedFn():
            connected = asyncio.get_event_loop().create_future()
            async def failCheck(data):
                if type(data) == str:
                    connected.set_exception(Exception(f'Failed to connect: {data}'))
                else:
                    connected.set_exception(Exception(f'Failed to connect: {data["message"]}'))
            async def failCheck2(data):
                connected.set_exception(Exception(f'Failed to connect: {data}'))

            async def startCheck(data):
                self.socket.on('game_error', game_error)
                self.socket.on('disconnect_reason', disconnect_reason)
                start(data)
                self.socket.on('start', start)
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