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
    
    def setNextSkill(self, skill, next):
        super().setNextSkill(skill, datetime(next.year, next.month, next.day, next.hour, next.minute, next.second - self.ping, next.microsecond, next.tzinfo, fold=next.fold))
    
    def parseCharacter(self, data) -> None:
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
        
        for condition in self.s:
            if Tools.hasKey(self.s[condition], 'ms'):
                self.s[condition]['ms'] -= pingCompensation * 1000
                if self.s[condition]['ms'] <= 0:
                    del self.s[condition]
        
        for process in self.q:
            if Tools.hasKey(self.q[process], 'ms'):
                self.q[process]['ms'] -= pingCompensation * 1000
                if self.q[process]['ms'] <= 0:
                    del self.q[process]
        
    def parseEntities(self, data):
        super().parseEntities(data)

        pingCompensation = self.ping

        for monster in data['monsters']:
            entity = self.entities.get(monster['id'])
            if entity == None or not hasattr(entity, 'moving'): continue
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
            
            for condition in entity.s:
                if Tools.hasKey(entity.s[condition], 'ms'):
                    entity.s[condition]['ms'] -= pingCompensation * 1000
                    if entity.s[condition]['ms'] <= 0:
                        del entity.s[condition]
        
        for player in data['players']:
            entity = self.players.get(player['id'])
            if entity == None or not hasattr(entity, 'moving'): continue
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
            
            for condition in entity.s:
                if Tools.hasKey(entity.s[condition], 'ms'):
                    entity.s[condition]['ms'] -= pingCompensation * 1000
                    if entity.s[condition]['ms'] <= 0:
                        del entity.s[condition]
    
    def parseQData(self, data):
        
        pingCompensation = self.ping

        if Tools.hasKey(data['q'], 'upgrade'):
            data['q']['upgrade']['ms'] -= pingCompensation * 1000
            if data['q']['upgrade']['ms'] <= 0:
                del self.q['upgrade']
            else:
                self.q['upgrade'] = data['q']['upgrade']
        if Tools.hasKey(data['q'], 'compound'):
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