from .Tools import Tools

class Entity:
    def __init__(self, data: dict, map: str, instance: str, G: dict):
        self.G = G
        self.max_hp = G['monsters'][data['type']]['hp']
        self.max_mp = G['monsters'][data['type']]['mp']
        self.map = map
        setattr(self, 'in', instance)
        self.moving = False
        self.cooperative = False
        
        self.apiercing = 0
        self.armor = 0
        self.avoidance = 0
        self.blast = 0
        self.breaks = 0
        self.crit = 0
        self.critdamage = 0
        self.evasion = 0
        self.lifesteal = 0
        self.mcourage = 0
        self.reflection = 0
        self.resistance = 0
        self.rpiercing = 0

        setattr(self, '1hp', False)
        self.aa = 0
        self.achievements = []
        self.cute = False
        self.drop_on_hit = False
        self.escapist = False
        setattr(self, 'global', False)
        self.goldsteal = 0
        self.humanoid = False
        self.passive = False
        self.peaceful = False
        self.poisonous = False
        self.prefix = ""
        self.roam = False
        self.spawns = []
        self.special = False
        self.stationary = False
        self.supporter = False
        self.trap = False
        self.unlist = False

        self.level = 1
        self.s = {}

        for gKey in G['monsters'][data['type']]:
            setattr(self, gKey, G['monsters'][data['type']][gKey])

        self.updateData(data)

    def updateData(self, data: dict):
        if (hasattr(self, 'id') and getattr(self, 'id') != data['id']):
            print("The entity's ID does not match")
            raise Exception()
        for key in data:
            setattr(self, key, data[key])

    def __getitem__(self, key: str):
        return getattr(self, key)

    def get(self, key):
        try:
            return getattr(self, key)
        except:
            return None

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