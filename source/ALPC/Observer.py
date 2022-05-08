import asyncio
from . import psSocketIO
import datetime
from .Entity import Entity
from .Player import Player
from .Tools import Tools
from .Constants import Constants
import math

class Observer(object):
    pingsPerServer : dict = {}

    def __init__(self, serverData: dict, g: dict, log: bool = False):
        self.socket = psSocketIO.AsyncClient(reconnection=False, logger=log)
        self.serverData = serverData
        self.G = g
        self.lastAllEntities = 0
        self.lastPositionUpdate = None
        self.entities: dict[str, Entity] = {}
        self.pingIndex = 0
        self.pingMap = {}
        self.pingNum = 1
        self.pings = {}
        self.players = {}
        self.projectiles = {}
        self.S = {}
        self.server = None
        self.x = 0
        self.y = 0
        if serverData:
            region = serverData['region']
            name = serverData['name']
            key = f'{region}{name}'
            pings = Observer.pingsPerServer.get(key, False)
            if (pings != False):
                self.pings = pings
        return

    @property
    def ping(self):
        if len(self.pings.values()) == 0:
            return 0
        else:
            return min(self.pings.values())

    def defaultHandler(self, data = None):
        return
    
    def anyHandler(self, event, data = None):
        print(f"Event: {event}\nData: {data}")

    def actionHandler(self, data):
        if data.get('instant', False):
            return

        attacker = self.players.get(data['attacker'], self.entities.get(data['attacker'], None))
        target = self.entities.get(data['attacker'], self.players.get(data['attacker'], None))
        projectileSpeed = self.G['projectiles'].get(data['projectile'], None).get('speed', None)
        if attacker and target and projectileSpeed:
            distance = Tools.distance(attacker, target)
            fixedETA = (distance / projectileSpeed) * 1000
            data['eta'] = fixedETA

        self.projectiles[data['pid']] = { **data, 'date': datetime.datetime.now()}
        return

    def deathHandler(self, data):
        self.deleteEntity(data['id'], True)
        return

    def disappearHandler(self, data):
        if self.players.get(data['id'], False):
            del self.players[data['id']]
        else:
            self.deleteEntity(data['id'])
        self.updatePositions()
        #TODO: Add database functions
        return

    def disconnectHandler(self):
        if (not self.serverData) or (not self.pings) or (len(self.pings) == 0):
            return
        key = f"{self.serverData['region']}{self.serverData['name']}"
        Observer.pingsPerServer[key] = self.pings
        return

    def entitiesHandler(self, data):
        self.parseEntities(data)
        return

    def gameEventHandler(self, data):
        if (self.G.get('monsters', {}).get(data['name'], False)):
            monsterData = { 'hp': self.G['monsters'][data['name']]['hp'], 'lastSeen': datetime.datetime.now(), 'level': 1, 'map': data['map'], 'x': data['x'], 'y': data['y'] }
            self.S[data['name']] = {**monsterData, 'live': True, 'max_hp': monsterData['hp']}
        #TODO: Add database methods
        return

    def hitHandler(self, data):
        if data.get('pid', False) == False:
            return
        if data.get('miss', False) or data.get('evade', False):
            if self.projectiles.get(data['pid'], False):
                del self.projectiles[data['pid']]
            return
        if data.get('reflect', False):
            p = self.projectiles.get(data['pid'], None)
            if p:
                p['damage'] = data['reflect']
                p['target'] = data['hid']
                p['x'] = self.x
                p['y'] = self.y
        if data.get('kill', False):
            if self.projectiles.get(data['pid'], False):
                del self.projectiles[data['pid']]
            self.deleteEntity(data['id'], True)
        elif data.get('damage', False):
            if self.projectiles.get(data['pid'], False):
                del self.projectiles[data['pid']]
            e = self.entities.get(data['id'], None)
            if e:
                e.hp = e.hp - data['damage']
        else:
            if self.projectiles.get(data['pid'], False):
                del self.projectiles[data['pid']]
        return

    def newMapHandler(self, data):
        self.parseNewMap(data)
        return

    def pingAckHandler(self, data):
        ping = self.pingMap.get(data['id'], None)
        if ping:
            time = (datetime.datetime.now() - ping['time']).total_seconds()
            self.pings[self.pingIndex] = time
            self.pingIndex += 1
            self.pingIndex = self.pingIndex % Constants.MAX_PINGS
            if ping.get('log', False):
                print(f"Ping: {time}s")
            del self.pingMap[data['id']]
        return

    #TODO: server_info event handler

    def welcomeHandler(self, data):
        self.server = data
        return

    async def connect(self, reconnect: bool=False, start: bool=True):
        addr = self.serverData['addr']
        port = self.serverData['port']
        url = f"ws://{addr}:{port}"
        await self.socket.connect(url)
        self.socket.reconnection = reconnect

        self.socket.on('action', self.actionHandler)
        self.socket.on('death', self.deathHandler)
        self.socket.on('disappear', self.disappearHandler)
        self.socket.on('disconnect', self.disconnectHandler)
        self.socket.on('entities', self.entitiesHandler)
        self.socket.on('game_event', self.gameEventHandler)
        self.socket.on('hit', self.hitHandler)
        self.socket.on('new_map', self.newMapHandler)
        self.socket.on('ping_ack', self.pingAckHandler)
        self.socket.on('welcome', self.welcomeHandler, )
        
        if start:
            async def connectedFn():
                connected = asyncio.get_event_loop().create_future()
                async def welcomeFn(data):
                    if (data['region'] != self.serverData['region']) or (data['name'] != self.serverData['name']):
                        connected.set_exception(Exception(f"We wanted the server {self.serverData['region']}{self.serverData['name']}, but we are on {data['region']}{data['name']}."))
                    else:
                        await self.socket.emit('loaded', {'height':1080, 'scale':2, 'success':1, 'width':1920})
                        connected.set_result(True)
                    self.welcomeHandler(data)
                def reject(reason):
                    if not connected.done():
                        connected.set_exception(Exception(reason))
                self.socket.on('welcome', welcomeFn)
                Tools.setTimeout(reject, Constants.CONNECT_TIMEOUT_S, f'Failed to start within {Constants.CONNECT_TIMEOUT_S}s.')
                while not connected.done():
                    await asyncio.sleep(0.25)
                return connected.result()
            try:
                await connectedFn()
            except Exception as e:
                print('Error:', e)
                return
        return

    def deleteEntity(self, id: str, death: bool=False) -> bool:
        entity = self.entities.get(id, None)
        if entity:
            if self.S.get(entity.type, None) and death:
                del self.S[entity.type]

            #TODO: database stuff

            del self.entities[id]
            return True
        return False

    def parseEntities(self, data):
        if data['type'] == 'all':
            self.lastAllEntities = datetime.datetime.now()
            
            self.entities.clear()
            self.players.clear()
            self.lastPositionUpdate = datetime.datetime.now()
        else:
            self.updatePositions()
        visibleIDs = []
        entityUpdates = []
        npcUpdates = []
        playerUpdates = []
        for monster in data['monsters']:
            e = None
            if not self.entities.get(monster['id'], None):
                e = Entity(monster, data['map'], data['in'], self.G)
                self.entities[monster['id']] = e
            else:
                e = self.entities[monster['id']]
                e.updateData(monster)
            visibleIDs.append(e.id)
        #TODO: database stuff
        for player in data['players']:
            p = None
            if not self.players.get(player['id'], None):
                p = Player(player, data['map'], data['in'], self.G)
                self.players[player['id']] = p
            else:
                p = self.players[player['id']]
                p.updateData(player)
        #TODO: database stuff
        return

    def parseNewMap(self, data):
        self.projectiles.clear()
        self.x = data['x']
        self.y = data['y']
        self.map = data['name']
        self.parseEntities(data['entities'])
        return

    def updatePositions(self):
        if getattr(self, 'lastPositionUpdate'):
            msSinceLastUpdate = (datetime.datetime.now() - self.lastPositionUpdate).total_seconds() * 1000
            if msSinceLastUpdate == 0:
                return
            for entity in self.entities.values():
                if not getattr(entity, 'moving', False):
                    continue

                distanceTravelled = entity.speed * msSinceLastUpdate / 1000
                angle = math.atan2(entity.going_y - entity.y, entity.going_x - entity.x)
                distanceToGoal = Tools.distance({'x': entity.x, 'y': entity.y}, {'x': entity.going_x, 'y': entity.going_y})
                if distanceTravelled > distanceToGoal:
                    entity.moving = False
                    entity.x = entity.going_x
                    entity.y = entity.going_y
                else:
                    entity.x = entity.x + math.cos(angle) * distanceTravelled
                    entity.y = entity.y + math.sin(angle) * distanceTravelled
                eKeys = list(entity.s)
                for condition in eKeys:
                    newCooldown = entity.s[condition]['ms'] - msSinceLastUpdate
                    if newCooldown <= 0:
                        del entity.s[condition]
                    else:
                        entity.s[condition]['ms'] = newCooldown
            for player in self.players.values():
                if not getattr(player, 'moving', False):
                    continue

                distanceTravelled = player.speed * msSinceLastUpdate / 1000
                angle = math.atan2(player.going_y - player.y, player.going_x - player.x)
                distanceToGoal = Tools.distance({'x': player.x, 'y': player.y}, {'x': player.going_x, 'y': player.going_y})
                if distanceTravelled > distanceToGoal:
                    player.moving = False
                    player.x = player.going_x
                    player.y = player.going_y
                else:
                    player.x = player.x + math.cos(angle) * distanceTravelled
                    player.y = player.y + math.sin(angle) * distanceTravelled
                pKeys = list(player.s)
                for condition in pKeys:
                    newCooldown = player.s[condition]['ms'] - msSinceLastUpdate
                    if newCooldown <= 0:
                        del player.s[condition]
                    else:
                        player.s[condition]['ms'] = newCooldown
        toDelete = []
        for id in self.entities.keys():
            if Tools.distance(self, self.entities[id]) < Constants.MAX_VISIBLE_RANGE:
                continue
            toDelete.append(id)
        for id in toDelete:
            self.deleteEntity(id)
        toDelete.clear()
        for id in self.players.keys():
            if Tools.distance(self, self.players[id]) < Constants.MAX_VISIBLE_RANGE:
                continue
            toDelete.append(id)
        for id in toDelete:
            del self.players[id]
        for id in list(self.projectiles):
            if (datetime.datetime.now() - self.projectiles[id]['date']).total_seconds() > Constants.STALE_PROJECTILE_S:
                del self.projectiles[id]
        self.lastPositionUpdate = datetime.datetime.now()
        return

    async def sendPing(self, log: bool=True):
        async def pingFn():
            pingID = str(self.pingNum)
            self.pingNum += 1
            self.pingMap[pingID] = { 'log': log, 'time': datetime.datetime.now() }
            pinged = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal pinged
                if not pinged.done():
                    self.socket.off('ping_ack', successCheck)
                    pinged.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal pinged
                if not pinged.done():
                    self.socket.off('ping_ack', successCheck)
                    pinged.set_result(value)
            def successCheck(data):
                resolve(data['id'])
            Tools.setTimeout(reject, Constants.TIMEOUT, f"sendPing timeout ({Constants.TIMEOUT}s)")
            self.socket.on('ping_ack', successCheck)
            await self.socket.emit('ping_trig', { 'id': pingID })
            while not pinged.done():
                await asyncio.sleep(Constants.SLEEP)
            return pinged.result()
        return await Tools.tryExcept(pingFn)