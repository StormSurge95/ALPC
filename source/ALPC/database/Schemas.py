AchievementSchema = {
    '__v': {
        'select': False,
        'type': int
    },
    'date': { 'type': int, 'required': True },
    'name': { 'type': str, 'required': True },
    'monsters': { 'type': dict, 'required': True },
    'max': { 'type': dict, 'required': True }
}

BankSchema = {
    '__v': {
        'select': False,
        'type': int
    },
    'gold': int,
    'items0': { 'required': False, 'type': list },
    'items1': { 'required': False, 'type': list },
    'items2': { 'required': False, 'type': list },
    'items3': { 'required': False, 'type': list },
    'items4': { 'required': False, 'type': list },
    'items5': { 'required': False, 'type': list },
    'items6': { 'required': False, 'type': list },
    'items7': { 'required': False, 'type': list },
    'items8': { 'required': False, 'type': list },
    'items9': { 'required': False, 'type': list },
    'items10': { 'required': False, 'type': list },
    'items11': { 'required': False, 'type': list },
    'items12': { 'required': False, 'type': list },
    'items13': { 'required': False, 'type': list },
    'items14': { 'required': False, 'type': list },
    'items15': { 'required': False, 'type': list },
    'items16': { 'required': False, 'type': list },
    'items17': { 'required': False, 'type': list },
    'items18': { 'required': False, 'type': list },
    'items19': { 'required': False, 'type': list },
    'items20': { 'required': False, 'type': list },
    'items21': { 'required': False, 'type': list },
    'items22': { 'required': False, 'type': list },
    'items23': { 'required': False, 'type': list },
    'items24': { 'required': False, 'type': list },
    'items25': { 'required': False, 'type': list },
    'items26': { 'required': False, 'type': list },
    'items27': { 'required': False, 'type': list },
    'items28': { 'required': False, 'type': list },
    'items29': { 'required': False, 'type': list },
    'items30': { 'required': False, 'type': list },
    'items31': { 'required': False, 'type': list },
    'items32': { 'required': False, 'type': list },
    'items33': { 'required': False, 'type': list },
    'items34': { 'required': False, 'type': list },
    'items35': { 'required': False, 'type': list },
    'items36': { 'required': False, 'type': list },
    'items37': { 'required': False, 'type': list },
    'items38': { 'required': False, 'type': list },
    'items39': { 'required': False, 'type': list },
    'items40': { 'required': False, 'type': list },
    'items41': { 'required': False, 'type': list },
    'items42': { 'required': False, 'type': list },
    'items43': { 'required': False, 'type': list },
    'items44': { 'required': False, 'type': list },
    'items45': { 'required': False, 'type': list },
    'items46': { 'required': False, 'type': list },
    'items47': { 'required': False, 'type': list },
    'lastUpdated': { 'required': False, 'type': int },
    'owner': str
}

DeathSchema = {
    '__v': {
        'select': False,
        'type': int
    },
    'name': str,
    'cause': str,
    'map': str,
    'x': float,
    'y': float,
    'serverRegion': str,
    'serverIdentifier': str,
    'time': float
}

EntitySchema = {
    '__v': {
        'select': False,
        'type': int
    },
    'hp': { 'required': False, 'type': int },
    'in': str,
    'lastSeen': { 'required': False, 'type': float },
    'level': { 'required': False, 'type': int },
    'map': str,
    'name': { 'required': False, 'type': str },
    'serverIdentifier': str,
    'serverRegion': str,
    'target': { 'required': False, 'type': str },
    'type': str,
    'x': float,
    'y': float
}

NPCSchema = {
    '__v': {
        'select': False,
        'type': int
    },
    'name': str,
    'map': str,
    'x': float,
    'y': float,
    'serverRegion': str,
    'serverIdentifier': str,
    'lastSeen': { 'type': float, 'required': False }
}

PlayerSchema = {
    '__v': {
        'select': False,
        'type': int
    },
    ### Key for use with ALData
    'aldata': { 'required': False, 'type': str },
    ### Discord ID for contacting the player
    'discord': { 'required': False, 'type': str },
    'in': str,
    'items': { 'required': False, 'type': list },
    'lastSeen': { 'type': float },
    'map': str,
    'name': { 'required': True, 'type': str },
    'owner': str,
    'rip': { 'required': False, 'type': bool },
    's': { 'required': False, 'type': dict },
    'serverIdentifier': str,
    'serverRegion': str,
    'slots': { 'type': dict },
    'type': { 'type': str },
    'x': float,
    'y': float
}

RespawnSchema = {
    '__v': {
        'select': False,
        'type': int
    },
    'estimatedRespawn': float,
    'serverIdentifier': str,
    'serverRegion': str,
    'type': str
}