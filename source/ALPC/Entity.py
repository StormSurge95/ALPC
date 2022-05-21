from .Tools import Tools

class Entity:
    def __init__(self, data: dict, map: str, instance: str, G: dict):
        setattr(self, '1hp', False)
        self.G = G
        self.aa: int = 0
        self.abs: bool = False
        self.achievements: list = []
        self.aggro: int = 0
        self.angle: float = 0
        self.apiercing: int = 0
        self.armor: int = 0
        self.attack: int = 0
        self.avoidance: int = 0
        self.blast: int = 0
        self.breaks: int = 0
        self.cid: int = 0
        self.cooperative: bool = False
        self.crit: int = 0
        self.critdamage: int = 0
        self.cute: bool = False
        self.damage_type: str = ''
        self.drop_on_hit: bool = False
        self.escapist: bool = False
        self.evasion: int = 0
        self.frequency: float = 0
        setattr(self, 'global', False)
        self.going_x: float = 0
        self.going_y: float = 0
        self.goldsteal = 0
        self.hp: int = 0
        self.humanoid: bool = False
        self.id: str = None
        setattr(self, 'in', instance)
        self.level: int = 1
        self.lifesteal: int = 0
        self.map: str = map
        self.max_hp: int = G['monsters'][data['type']]['hp']
        self.max_mp: float = G['monsters'][data['type']]['mp']
        self.mcourage: int = 0
        self.move_num: int = 0
        self.moving: bool = False
        self.mp: int = 0
        self.name: str = ''
        self.passive: bool = False
        self.peaceful: bool = False
        self.poisonous: bool = False
        self.prefix: str = ''
        self.rage: float = 0
        self.range: int = 0
        self.reflection: int = 0
        self.resistance: int = 0
        self.respawn: int = 0
        self.roam: bool = False
        self.rpiercing: int = 0
        self.s: dict[str, dict] = {}
        self.spawns: list = []
        self.special: bool = False
        self.speed: int = 0
        self.stationary: bool = False
        self.supporter: bool = False
        self.trap: bool = False
        self.type: str = ''
        self.unlist: bool = False
        self.x: float = 0
        self.xp: int = 0
        self.y: float = 0

        for gKey in G['monsters'][data['type']]:
            setattr(self, gKey, G['monsters'][data['type']][gKey])

        self.updateData(data)

    def updateData(self, data: dict):
        if (self.id != None and self.id != data['id']):
            print("The entity's ID does not match")
            raise Exception("The entity's ID does not match")
        for key in data:
            setattr(self, key, data[key])

    def __getitem__(self, key: str):
        return getattr(self, key)

    def get(self, key, default = None):
        if hasattr(self, key):
            return getattr(self, key)
        else:
            return default

    def calculateDamageRange(self, defender) -> list:
        if getattr(defender, '1hp', False):
            return [1, 1]

        baseDamage = getattr(self, 'attack', 0)
        
        if hasattr(defender, 's') and hasattr(defender.s, 'cursed'):
            baseDamage *= 1.2
        if hasattr(defender, 's') and hasattr(defender.s, 'marked'):
            baseDamage *= 1.1

        if getattr(self, 'damage_type') == 'physical':
            baseDamage *= Tools.damage_multiplier(getattr(defender, 'armor') - getattr(self, 'apiercing'))
        elif getattr(self, 'damage_type') == 'magical':
            baseDamage *= Tools.damage_multiplier(getattr(defender, 'resistance') - getattr(self, 'rpiercing'))

        if hasattr(self, 'crit'):
            if self.crit >= 100:
                return [baseDamage * 0.9 * (2 + (self.critDamage / 100)), baseDamage * 1.1 * (2 + (self.critDamage / 100))]
            else:
                return [baseDamage * 0.9, baseDamage * 1.1 * (2 + (self.critDamage / 100))]
        else:
            return [baseDamage * 0.9, baseDamage * 1.1]

    def couldDieToProjectiles(self, character, projectiles: dict, players: dict, entities: dict) -> bool:
        if self.avoidance >= 100:
            return False
        incomingProjectileDamage = 0
        for projectile in projectiles.values():
            if not projectile.get('damage', False):
                continue
            if projectile['target'] != self.id:
                continue

            attacker = None
            if (not bool(attacker)) and (character.id == projectile['attacker']):
                attacker = character
            if (not bool(attacker)):
                attacker = players.get(projectile['attacker'])
            if (not bool(attacker)):
                attacker = entities.get(projectile['attacker'])
            if (not bool(attacker)):
                incomingProjectileDamage += projectile['damage'] * 2.2
                if incomingProjectileDamage >= self.hp:
                    return True
                continue

            if attacker.damage_type == 'physical' and hasattr(self, 'evasion') and self.evasion >= 100:
                continue
            if attacker.damage_type == 'magical' and hasattr(self, 'reflection') and self.reflection >= 100:
                continue

            maximumDamage = attacker.calculateDamageRange(self, projectile['type'])[1]

            incomingProjectileDamage += maximumDamage
            if incomingProjectileDamage >= self.hp:
                return True
        return False

    def couldGiveCreditForKill(self, player) -> bool:
        if not hasattr(self, 'target'):
            return True
        if self.cooperative:
            return True
        if self.isAttackingPartyMember(player):
            return True
        return False

    def isAttackingPartyMember(self, player) -> bool:
        if not hasattr(self, 'target'):
            return False
        if self.isAttackingUs(player):
            return True
        if hasattr(player, 'partyData') and hasattr(player.partyData, 'list') and (self.target in player.partyData.list):
            return True
        return False

    def isAttackingUs(self, player) -> bool:
        if hasattr(self, 'target'):
            return self.target == player.id
        return False

    def isTauntable(self, by) -> bool:
        if not hasattr(self, 'target'):
            return True
        if self.isAttackingPartyMember(by):
            return True
        targeting = by.players.get(self.target, False)
        if targeting != False and targeting.owner == by.owner:
            return True
        return False

    def willBurnToDeath(self) -> bool:
        if hasattr(self, '1hp'):
            return False
        if hasattr(self, 'lifesteal'):
            return False
        if hasattr(self, 'abilities') and self.abilities.get('self_healing', False):
            return False
        if hasattr(self, 's') and not self.s.get('burned', False):
            return False

        burnTime = max(0, (self.s['burned']['ms'] - (self.G['conditions']['burned']['interval'] * 2))) / 1000
        burnDamage = burnTime * self.s['burned']['intensity']

        return burnDamage > self.hp

    def willDieToProjectiles(self, character, projectiles: dict, players: dict, entities: dict) -> bool:
        if hasattr(self, 'avoidance'):
            return False
        incomingProjectileDamage = 0
        for projectile in projectiles.values():
            if not projectile.get('damage', False):
                continue
            if projectile['target'] != self.id:
                continue

            attacker = None
            if (not bool(attacker)) and (character.id == projectile['attacker']):
                attacker = character
            if (not bool(attacker)):
                attacker = players.get(projectile['attacker'])
            if (not bool(attacker)):
                attacker = entities.get(projectile['attacker'])
            if (not bool(attacker)):
                continue

            if attacker.damage_type == 'physical' and hasattr(self, 'evasion'):
                continue
            if attacker.damage_type == 'magical' and hasattr(self, 'reflection'):
                continue

            minimumDamage = attacker.calculateDamageRange(self, projectile['type'])[0]

            incomingProjectileDamage += minimumDamage
            if incomingProjectileDamage >= self.hp:
                return True
        return False