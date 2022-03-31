from Tools import Tools
from Entity import Entity
import typing

class Player:
    def __init__(self, data, map, instance, g):
        self.G = g
        self.map = map
        self.inst = instance
        if not data.get('npc', False):
            self.damage_type = self.G['classes'][data['ctype']]['damage_type']

        self.updateData(data)

    def updateData(self, data):
        if hasattr(self, 'id') and self.id != data['id']:
            raise Exception('The entity\'s ID does not match')

        for key in data.keys():
            setattr(self, key, data[key])