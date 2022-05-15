import asyncio
from asyncio.log import logger
from pprint import pprint
import re
import sys
from . import psSocketIO
from .database import Database
from datetime import datetime
from .Entity import Entity
from .Player import Player
from .Tools import Tools
from .Constants import Constants
import pymongo
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
        self.map = ''
        self.pingIndex = 0
        self.pingMap = {}
        self.pingNum = 1
        self.pings = {}
        self.players: dict[str, Player] = {}
        self.projectiles = {}
        self.S = {}
        self.server = None
        self.x: float = 0
        self.y: float = 0
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
            return float(0)
        else:
            return min(self.pings.values())

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

        self.projectiles[data['pid']] = { **data, 'date': datetime.utcnow().timestamp()}
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

        if Database.connection == None or data['reason'] == 'disconnect' or data['reason'] == 'invis': return
        if data.get('effect') != None and (data.get('effect') == 'blink' or data.get('effect') == 'magiport') and data.get('to') != None and self.G['maps'].get(data['to']) != None and data.get('s') != None and not data['id'].isnumeric():
            updateData = {
                'lastSeen': datetime.utcnow().timestamp(),
                'map': data['to'],
                'serverIdentifier': self.serverData['name'],
                'serverRegion': self.serverData['region'],
                'x': data['s'][0],
                'y': data['s'][1]
            }
            key = f"{self.serverData['name']}{self.serverData['region']}{data['id']}"
            nextUpdate = Database.nextUpdate.get(key)
            if nextUpdate == None or datetime.utcnow().timestamp() >= nextUpdate:
                Database.connection.ALPC.players.update_one({ 'name': data['id'] },  { "$set": updateData }, True)
                Database.nextUpdate[key] = datetime.utcnow().timestamp() + Constants.MONGO_UPDATE_S
        elif data.get('to') != None and data.get('effect') == 1:
            s = 0
            if data.get('s') != None: s = data['s']
            spawnLocation = self.G['maps'].get(data['to'], {}).get('spawns', [None])[s]
            if spawnLocation == None: return
            updateData = {
                'lastSeen': datetime.utcnow().timestamp(),
                'map': data['to'],
                'serverIdentifier': self.serverData['name'],
                'serverRegion': self.serverData['region'],
                'x': spawnLocation[0],
                'y': spawnLocation[1]
            }
            key = f"{self.serverData['name']}{self.serverData['region']}{data['id']}"
            nextUpdate = Database.nextUpdate.get(key)
            if nextUpdate == None or datetime.utcnow().timestamp() >= nextUpdate:
                Database.connection.ALPC.players.update_one({ 'name': data['id'] }, { "$set": updateData }, True)
                Database.nextUpdate[key] = datetime.utcnow().timestamp() + Constants.MONGO_UPDATE_S
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
            monsterData = { 'hp': self.G['monsters'][data['name']]['hp'], 'lastSeen': datetime.utcnow().timestamp(), 'level': 1, 'map': data['map'], 'x': data['x'], 'y': data['y'] }
            self.S[data['name']] = {**monsterData, 'live': True, 'max_hp': monsterData['hp']}
        if Database.connection != None:
            Database.connection.ALPC.entities.update_one({ 'serverIdentifier': self.serverData['name'], 'serverRegion': self.serverData['region'], 'type': data['name'] }, { "$set": monsterData }, True)
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
            time = (datetime.utcnow().timestamp() - ping['time'])
            self.pings[self.pingIndex] = time
            self.pingIndex += 1
            self.pingIndex = self.pingIndex % Constants.MAX_PINGS
            if ping.get('log', False):
                print(f"Ping: {time}s")
            del self.pingMap[data['id']]
        return

    def serverInfoHandler(self, data: dict):
        databaseEntityUpdates = []
        databaseRespawnUpdates = []
        databaseDeletes = set()
        now = datetime.utcnow().timestamp()

        if Database.connection != None:
            for type in Constants.SERVER_INFO_MONSTERS:
                if data.get(type) == None or data[type]['live'] == False: databaseDeletes.add(type)
            
            for mtype in data:
                mData: dict = data[mtype]
                if not isinstance(mData, dict): continue # event info, not monster info
                if mData.get('live') != True:
                    databaseDeletes.add(mtype)
                    nextSpawn = datetime(mData['spawn']).timestamp()
                    databaseRespawnUpdates.append(pymongo.UpdateOne(
                        filter={
                            'serverIdentifier': self.serverData['name'],
                            'serverRegion': self.serverData['region'],
                            'type': mtype
                        },
                        update={
                            "$set": { 'estimatedRespawn': nextSpawn }
                        },
                        upsert=True
                    ))
                    continue
                if mData.get('x') == None or mData.get('y') == None: continue # No location data

                if mData.get('hp') == None: mData['hp'] = self.G['monsters'][mtype]['hp']
                if mData.get('max_hp') == None: mData['max_hp'] = self.G['monsters'][mtype]['hp']

                data[mtype] = mData

                if mtype in Constants.SPECIAL_MONSTERS:
                    databaseEntityUpdates.append(pymongo.UpdateOne(
                        filter={
                            'serverIdentifier': self.serverData['name'],
                            'serverRegion': self.serverData['region'],
                            'type': mtype
                        },
                        update={ "$set": {
                            'hp': mData.get('hp'),
                            'lastSeen': now,
                            'map': mData.get('map'),
                            'target': mData.get('target'),
                            'x': mData.get('x'),
                            'y': mData.get('y')
                        } },
                        upsert=True
                    ))
                    databaseRespawnUpdates.append(pymongo.DeleteOne(
                        filter= {
                            'serverIdentifier': self.serverData['name'],
                            'serverRegion': self.serverData['region'],
                            'type': mtype
                        }
                    ))
            
            for type in Constants.MONSTER_RESPAWN_TIMES:
                if data.get(type) != None: continue # It's still alive
                if self.S.get(type) == None: continue # It wasn't alive before

                # This special monster just died
                nextSpawn = datetime.utcnow().timestamp() + Constants.MONSTER_RESPAWN_TIMES[type]
                databaseRespawnUpdates.append(pymongo.UpdateOne(
                    filter={
                        'serverIdentifier': self.serverData['name'],
                        'serverRegion': self.serverData['region'],
                        'type': type
                    },
                    update={
                        "$set": { 'estimatedRespawn': nextSpawn }
                    },
                    upsert=True
                ))
            
            if len(databaseDeletes) > 0: Database.connection.ALPC.entities.delete_many(
                filter={
                    'serverIdentifier': self.serverData['name'],
                    'serverRegion': self.serverData['region'],
                    'type': { '$in': [*databaseDeletes] }
                }
            )
            if len(databaseEntityUpdates) > 0: Database.connection.ALPC.entities.bulk_write(databaseEntityUpdates)
            if len(databaseRespawnUpdates) > 0: Database.connection.ALPC.respawns.bulk_write(databaseRespawnUpdates)

        self.S = data
        return

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
        self.socket.on('server_info', self.serverInfoHandler)
        self.socket.on('welcome', self.welcomeHandler)
        
        if start:
            async def connectedFn():
                connected = asyncio.get_event_loop().create_future()
                async def welcomeFn(data):
                    if (data['region'] != self.serverData['region']) or (data['name'] != self.serverData['name']):
                        connected.set_exception(Exception(f"We wanted the server {self.serverData['region']}{self.serverData['name']}, but we are on {data['region']}{data['name']}."))
                    else:
                        await self.socket.emit('loaded', {'height':1080, 'scale':2, 'success':1, 'width':1920})
                        connected.set_result(True)
                def reject(reason):
                    if not connected.done():
                        connected.set_exception(Exception(reason))
                self.socket.on('welcome', welcomeFn)
                Tools.setTimeout(reject, Constants.CONNECT_TIMEOUT_S, f'Failed to start within {Constants.CONNECT_TIMEOUT_S}s.')
                while not connected.done():
                    await asyncio.sleep(Constants.SLEEP)
                return connected.result()
            return await Tools.tryExcept(connectedFn)
        return

    def deleteEntity(self, id: str, death: bool=False) -> bool:
        entity: Entity = self.entities.get(id, None)
        if entity:
            if self.S.get(entity.type, None) and death:
                del self.S[entity.type]

            if Database.connection != None and entity.type in Constants.SPECIAL_MONSTERS:
                key = f"{self.serverData['name']}{self.serverData['region']}{entity.id}"
                nextUpdate: float = Database.nextUpdate.get(key)
                if death and nextUpdate != sys.maxsize:
                    Database.connection.ALPC.entities.delete_one({ 'name': id, 'serverIdentifier': self.serverData['name'], 'serverRegion': self.serverData['region'] })
                    Database.nextUpdate[key] = nextUpdate

            del self.entities[id]
            return True
        return False

    def parseEntities(self, data):
        if data['type'] == 'all':
            self.lastAllEntities = datetime.utcnow().timestamp()
            
            self.entities.clear()
            self.players.clear()
            self.lastPositionUpdate = datetime.utcnow().timestamp()
        else:
            self.updatePositions()
        visibleIDs = []
        entityUpdates = []
        npcUpdates = []
        playerUpdates = []
        for monster in data['monsters']:
            e = None
            if self.entities.get(monster['id']) == None:
                e = Entity(monster, data['map'], data['in'], self.G)
                self.entities[monster['id']] = e
            else:
                e = self.entities[monster['id']]
                e.updateData(monster)
            visibleIDs.append(e.id)
        
            if Database.connection != None:
                if e.type in Constants.SPECIAL_MONSTERS:
                    key = f"{self.serverData['name']}{self.serverData['region']}{e.id}"
                    nextUpdate = Database.nextUpdate.get(key)
                    if nextUpdate == None or datetime.utcnow().timestamp() >= nextUpdate:
                        updateData = {
                            'hp': e.hp,
                            'in': e.inst,
                            'lastSeen': datetime.utcnow().timestamp(),
                            'level': e.level,
                            'map': e.map,
                            'name': e.id,
                            'x': e.x,
                            'y': e.y
                        }
                        if hasattr(e, 'target'): updateData['target'] = e.target
                        if e.type in Constants.ONE_SPAWN_MONSTERS:
                            # Don't include id in filter, so it overwrites last one
                            entityUpdates.append(pymongo.UpdateOne(
                                filter={
                                    'serverIdentifier': self.serverData['name'],
                                    'serverRegion': self.serverData['region'],
                                    'type': e.type
                                },
                                update={ "$set": updateData },
                                upsert=True
                            ))
                        else:
                            # Include the id in the filter
                            entityUpdates.append(pymongo.UpdateOne(
                                filter={
                                    'name': e.id,
                                    'serverIdentifier': self.serverData['name'],
                                    'serverRegion': self.serverData['region'],
                                    'type': e.type 
                                },
                                update={ "$set": updateData },
                                upsert=True
                            ))
                        Database.nextUpdate[key] = datetime.utcnow().timestamp() + Constants.MONGO_UPDATE_S
        for player in data['players']:
            p: Player = None
            if not self.players.get(player['id'], None):
                p = Player(player, data['map'], data['in'], self.G)
                self.players[player['id']] = p
            else:
                p = self.players[player['id']]
                p.updateData(player)
        
            if Database.connection != None:
                key = f"{self.serverData['name']}{self.serverData['region']}{p.id}"
                nextUpdate = Database.nextUpdate.get(key)
                if nextUpdate == None or datetime.utcnow().timestamp() >= nextUpdate:
                    if p.isNPC():
                        npcUpdates.append(pymongo.UpdateOne(
                            filter={
                                'name': p.id,
                                'serverIdentifier': self.serverData['name'],
                                'serverRegion': self.serverData['region']
                            },
                            update={ "$set": {
                                'lastSeen': datetime.utcnow().timestamp(),
                                'map': p.map,
                                'x': p.x,
                                'y': p.y
                            } },
                            upsert=True
                        ))
                    else:
                        updateData = {
                            'in': p.inst,
                            'lastSeen': datetime.utcnow().timestamp(),
                            'map': p.map,
                            'rip': p.rip,
                            's': p.s,
                            'serverIdentifier': self.serverData['name'],
                            'serverRegion': self.serverData['region'],
                            'slots': p.slots,
                            'type': p.ctype,
                            'x': p.x,
                            'y': p.y
                        }
                        if hasattr(p, 'owner'): updateData['owner'] = p.owner
                        playerUpdates.append(pymongo.UpdateOne(
                            filter={ 'name': p.id },
                            update={ "$set": updateData },
                            upsert=True
                        ))
                    Database.nextUpdate[key] = datetime.utcnow().timestamp() + Constants.MONGO_UPDATE_S
        if Database.connection != None:
            if len(entityUpdates) > 0: Database.connection.ALPC.entities.bulk_write(entityUpdates)
            if len(npcUpdates) > 0: Database.connection.ALPC.npcs.bulk_write(npcUpdates)
            if len(playerUpdates) > 0: Database.connection.ALPC.players.bulk_write(playerUpdates)

            if data['type'] == 'all':
                results = Database.connection.ALPC.entities.aggregate([
                    {
                        "$match": {
                            'map': self.map,
                            'name': { "$nin": visibleIDs },
                            'serverIdentifier': self.serverData['name'],
                            'serverRegion': self.serverData['region']
                        }
                    },
                    {
                        "$project": {
                            'distance': {
                                "$sqrt": {
                                    "$add": [
                                        { "$pow": [{ "$subtract": [self.y, "$y"] }, 2] },
                                        { "$pow": [{ "$subtract": [self.x, "$x"] }, 2] } 
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "$match": {
                            'distance': {
                                "$lt": Constants.MAX_VISIBLE_RANGE / 2
                            }
                        }
                    }
                ])
                try:
                    ids = []
                    for doc in results: ids.append(doc['_id'])
                    if len(ids) > 0: Database.connection.ALPC.entities.delete_many({
                        '_id': { "$in": ids },
                        'serverIdentifier': self.serverData['name'],
                        'serverRegion': self.serverData['region']
                    })
                except Exception as e:
                    logger.exception(e)
                    logger.debug("results of aggregation:")
                    logger.debug(results)
        return

    def parseNewMap(self, data):
        self.projectiles.clear()
        self.x = data['x']
        self.y = data['y']
        self.map = data['name']
        self.parseEntities(data['entities'])
        return

    def updatePositions(self):
        if getattr(self, 'lastPositionUpdate') != None:
            msSinceLastUpdate = (datetime.utcnow().timestamp() - self.lastPositionUpdate) * 1000
            if msSinceLastUpdate == 0: return
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
            if (datetime.utcnow().timestamp() - self.projectiles[id]['date']) > Constants.STALE_PROJECTILE_S:
                del self.projectiles[id]
        self.lastPositionUpdate = datetime.utcnow().timestamp()
        return

    async def sendPing(self, log: bool=True):
        async def pingFn():
            pingID = str(self.pingNum)
            self.pingNum += 1
            self.pingMap[pingID] = { 'log': log, 'time': datetime.utcnow().timestamp() }
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