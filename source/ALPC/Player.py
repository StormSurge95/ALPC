from .Character import Character
from .Entity import Entity
from .Tools import Tools
import logging
import logging.config

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(fmt='%(levelname)s - %(name)s - %(asctime)s - %(funcName)s: %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(handler)

class Player(object):
    def __init__(self, data: dict, map: str, instance: str, g: dict):
        self.G = g
        self.map = map
        self.inst = instance
        self.logger = logging.getLogger('Player')
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(fmt='%(levelname)s - %(name)s - %(asctime)s - %(funcName)s: %(message)s', datefmt='%H:%M:%S'))
        self.logger.addHandler(handler)
        if not data.get('npc', False):
            self.damage_type = self.G['classes'][data['ctype']]['damage_type']

        self.updateData(data)

    def updateData(self, data: dict):
        if hasattr(self, 'id') and self.id != data['id']:
            raise Exception('The entity\'s ID does not match')

        for key in data.keys():
            setattr(self, key, data[key])

    def calculateDamageRange(self, defender: Character | Entity | 'Player', skill: str = 'attack') -> list:
        if hasattr(defender, 'immune') and (skill in ['3shot', '5shot', 'burst', 'cburst', 'supershot', 'taunt']):
            return [0, 0]

        if hasattr(defender, '1hp') or skill == 'taunt':
            return [1, 1]

        baseDamage = self.attack
        if not self.G['skills'].get(skill, False):
            logger.debug(f'{skill} isn\'t a skill!?')
        if self.G['skills'][skill].get('damage', False):
            baseDamage = self.G['skills'][skill]['damage']

        if defender.s.get('cursed', False):
            baseDamage *= 1.2
        if defender.s.get('marked', False):
            baseDamage *= 1.1

        if self.ctype == 'priest':
            baseDamage *= 0.4

        additionalApiercing = 0
        if self.G['skills'][skill].get('apiercing', False):
            additionalApiercing = self.G['skills'][skill]['apiercing']
        if self.damage_type == 'physical':
            baseDamage *= Tools.damage_multiplier(defender.armor - self.apiercing - additionalApiercing)
        elif self.damage_type == 'magical':
            baseDamage *= Tools.damage_multiplier(defender.resistance - self.rpiercing)

        if self.G['skills'][skill].get('damage_multiplier', False):
            baseDamage *= self.G['skills'][skill]['damage_multiplier']

        lowerLimit = baseDamage * 0.9
        upperLimit = baseDamage * 1.1

        if hasattr(self, 'crit'):
            if self.crit >= 100:
                lowerLimit *= (2 + (self.critdamage / 100))
            upperLimit *= (2 + (self.critdamage / 100))

        if skill == 'cleave':
            lowerLimit *= 0.1
            upperLimit *= 0.9

        return [lowerLimit, upperLimit]

    def isFriendly(self, bot: Character) -> bool:
        if hasattr(self, 'npc'):
            return True

        if bot.id == self.id:
            return True

        if hasattr(self, 'owner') and bot.owner == self.owner:
            return True

        if hasattr(self, 'party') and bot.party == self.party:
            return True

        return False

    def isNPC(self):
        return getattr(self, 'npc', False)