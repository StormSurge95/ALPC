from datetime import datetime
import math
from .Constants import Constants
from .Character import Character
from .Tools import Tools

class PingCompensatedCharacter(Character):
    
    def __init__(self, userID: str, userAuth: str, characterID: str, g: dict, serverData: dict, log: bool = False):
        super().__init__(userID, userAuth, characterID, g, serverData, log)
    
    async def connect(self):
        try:
            await super().connect()
            await self.pingLoop()
        except Exception as e:
            await self.disconnect()
            raise e
    
    def setNextSkill(self, skill: str, next: float):
        next -= self.ping
        super().setNextSkill(skill, next)
    
    def parseCharacter(self, data: dict) -> None:
        super().parseCharacter(data)

        pingCompensation = self.ping

        if self.moving:
            distanceTravelled = self.speed * pingCompensation
            angle = math.atan2(self.going_y - self.y, self.going_x - self.x)
            distanceToGoal = Tools.distance({ 'x': self.x, 'y': self.y }, { 'x': self.going_x, 'y': self.going_y })
            if distanceTravelled > distanceToGoal:
                self.moving = False
                self.x = self.going_x
                self.y = self.going_y
            else:
                self.x = self.x + math.cos(angle) * distanceTravelled
                self.y = self.y + math.sin(angle) * distanceTravelled
        
        for condition in list(self.s):
            if self.s[condition].get('ms') != None:
                self.s[condition]['ms'] -= pingCompensation * 1000
                if self.s[condition]['ms'] <= 0:
                    del self.s[condition]
        
        for process in list(self.q):
            if self.q[process].get('ms') != None:
                self.q[process]['ms'] -= pingCompensation * 1000
                if self.q[process]['ms'] <= 0:
                    del self.q[process]
        
    def parseEntities(self, data: dict):
        super().parseEntities(data)

        pingCompensation = self.ping

        for monster in data['monsters']:
            entity = self.entities.get(monster['id'])
            if entity == None or not hasattr(entity, 'moving'): continue
            if not hasattr(entity, 'speed') or entity.speed == None: continue
            if not hasattr(entity, 'going_x') or not hasattr(entity, 'going_y'): continue
            distanceTravelled = entity.speed * pingCompensation
            angle = math.atan2(entity.going_y - entity.y, entity.going_x - entity.x)
            distanceToGoal = Tools.distance({ 'x': entity.x, 'y': entity.y }, { 'x': entity.going_x, 'y': entity.going_y })
            if distanceTravelled > distanceToGoal:
                entity.moving = False
                entity.x = entity.going_x
                entity.y = entity.going_y
            else:
                entity.x = entity.x + math.cos(angle) * distanceTravelled
                entity.y = entity.y + math.sin(angle) * distanceTravelled
            
            for condition in list(entity.s):
                if entity.s[condition].get('ms') != None:
                    entity.s[condition]['ms'] -= pingCompensation * 1000
                    if entity.s[condition]['ms'] <= 0:
                        del entity.s[condition]
        
        for player in data['players']:
            entity = self.players.get(player['id'])
            if entity == None or not hasattr(entity, 'moving'): continue
            if not hasattr(entity, 'speed') or entity.speed == None: continue
            if not hasattr(entity, 'going_x') or not hasattr(entity, 'going_y'): continue
            distanceTravelled = entity.speed * pingCompensation
            angle = math.atan2(entity.going_y - entity.y, entity.going_x - entity.x)
            distanceToGoal = Tools.distance({ 'x': entity.x, 'y': entity.y }, { 'x': entity.going_x, 'y': entity.going_y })
            if distanceTravelled > distanceToGoal:
                entity.moving = False
                entity.x = entity.going_x
                entity.y = entity.going_y
            else:
                entity.x = entity.x + math.cos(angle) * distanceTravelled
                entity.y = entity.y + math.sin(angle) * distanceTravelled
            
            for condition in list(entity.s):
                if entity.s[condition].get('ms') != None:
                    entity.s[condition]['ms'] -= pingCompensation * 1000
                    if entity.s[condition]['ms'] <= 0:
                        del entity.s[condition]
    
    def parseQData(self, data: dict):
        
        pingCompensation = self.ping

        if data['q'].get('upgrade') != None:
            data['q']['upgrade']['ms'] -= pingCompensation * 1000
            if data['q']['upgrade']['ms'] <= 0:
                del self.q['upgrade']
            else:
                self.q['upgrade'] = data['q']['upgrade']
        if data['q'].get('compound') != None:
            data['q']['compound']['ms'] -= pingCompensation * 1000
            if data['q']['compound']['ms'] <= 0:
                del self.q['compound']
            else:
                self.q['compound'] = data['q']['compound']
    
    async def pingLoop(self):
        if not self.socket or not self.socket.connected:
            self.timeouts['pingLoop'] = Tools.setTimeout(self.pingLoop, 1)
            return
        
        await self.sendPing(False)
        if len(self.pings) > math.ceil(Constants.MAX_PINGS / 10):
            self.timeouts['pingLoop'] = Tools.setTimeout(self.pingLoop, Constants.PING_EVERY_S)
        else:
            self.timeouts['pingLoop'] = Tools.setTimeout(self.pingLoop, 1)