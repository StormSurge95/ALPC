import asyncio
import socketio
import datetime
from Entity import Entity
from Player import Player
from database.Database import Database
from Tools import Tools
from Constants import Constants
import promisio
import math

class Observer:
    pingsPerServer: dict = {}

    def __init__(self, serverData: dict, g: dict):
        self.socket = socketio.AsyncClient()
        self.serverData = serverData
        self.G = g
        self.lastAllEntities = 0
        self.lastPositionUpdate = datetime.datetime.now()
        self.entities = {}
        self.pingIndex = 0
        self.pingMap = {}
        self.pingNum = 1
        self.pings = []
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

    async def connect(self, reconnect: bool = False, start: bool = True):
        addr = self.serverData['addr']
        port = self.serverData['port']
        url = f"ws://{addr}:{port}"
        await self.socket.connect(url)

        @self.socket.event
        def action(data):
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

        @self.socket.event
        def death(data):
            self.deleteEntity(data['id'], True)

        @self.socket.event
        def disappear(data):
            if self.players.get(data['id'], False):
                del self.players[data['id']]
            else:
                self.deleteEntity(data['id'])

            self.updatePositions()

            #if not Database.connection or data.reason == 'disconnect' or data.reason == 'invis':
            return
        #TODO: add database functions

        @self.socket.event
        def disconnect():
            if not self.serverData or not self.pings or len(self.pings) == 0:
                return
            key = f"{self.serverData['region']}{self.serverData['name']}"
            Observer.pingsPerServer[key] = self.pings

        @self.socket.event
        def entities(data):
            self.parseEntities(data)

        @self.socket.event
        def game_event(data):
            if self.G['monsters'][data['name']]:
                monsterData = {
                    'hp': self.G['monsters'][data['name']]['hp'],
                    'lastSeen': datetime.datetime.now(),
                    'level': 1,
                    'map': data['map'],
                    'x': data['x'],
                    'y': data['y']
                }

                self.S[data.name] = {
                    **monsterData,
                    'live': true,
                    'max_hp': monsterData['hp']
                }

        #TODO: Add database method

        @self.socket.event
        def hit(data):
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

        @self.socket.event
        def new_map(data):
            self.parseNewMap(data)

        @self.socket.event
        def ping_ack(data):
            ping = self.pingMap.get(data.id, None)
            if ping:
                time = datetime.datetime.now() - ping.time
                self.pings[self.pingIndex] = time
                self.pingIndex += 1
                self.pingIndex = self.pingIndex % Constants.MAX_PINGS
                if ping.log:
                    print(f"Ping: {time}")

                del self.pingMap[data['id']]

        #TODO: server_info event

        def welcomeFn(data):
            self.server = data
        self.socket.on('welcome', handler=welcomeFn)

        if start:
            def connectedFn(resolve, reject):
                async def welcome(data):
                    if (data['region'] != self.serverData['region']) or (data['name'] != self.serverData['name']):
                        reject(f"We wanted the server {self.serverdata['region']}{self.serverData['name']}, but we are on {data['region']}{data['name']}.")
                    else:
                        await self.socket.emit('loaded', {'height':1080, 'scale':2,'success':1,'width':1920})
                        resolve()
                self.socket.on('welcome', handler=welcome)
                Tools.setTimeout(reject, Constants.CONNECT_TIMEOUT_MS, f'Failed to start within {Constants.CONNECT_TIMEOUT_MS / 1000}s.')
            connected = promisio.Promise(connectedFn(lambda : None, lambda x: x))
            return await connected

    def deleteEntity(self, id: str, death: bool = False) -> bool:
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

    def parseNewMap(self, data):
        #print(str(data))
        self.projectiles.clear()

        self.x = data['x']
        self.y = data['y']
        self.map = data['name']

        self.parseEntities(data['entities'])

    def updatePositions(self):
        if self.lastPositionUpdate:
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
                #print(f'{entity.id}:', str(entity.s))
                eKeys = list(entity.s)
                for condition in eKeys:
                    newCooldown = entity.s[condition]['ms'] - msSinceLastUpdate
                    if newCooldown <= 0:
                        del entity.s[condition]
                    else:
                        entity.s[condition]['ms'] = newCooldown

            for player in self.players.values():
                #print(dir(player))
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
                #print(f'{player.id}:', str(player.s))
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
            if (datetime.datetime.now() - self.projectiles[id]['date']).total_seconds() > Constants.STALE_PROJECTILE_MS / 1000:
                del self.projectiles[id]

        self.lastPositionUpdate = datetime.datetime.now()

    async def sendPing(self, log: bool = True):
        pingID = str(self.pingNum)
        self.pingNum += 1

        self.pingMap[pingID] = {'log': log, 'time': datetime.datetime.now() }

        await self.socket.emit('ping_trig', { 'id': pingID })
        return pingID