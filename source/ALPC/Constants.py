

class Constants:
    ## Various client related things ##
    PATHFINDER_FIRST_MAP: str = 'main'
    MAX_PINGS: int = 50
    PING_EVERY_S: int = 30
    CONNECT_TIMEOUT_S: int = 10
    RECONNECT_TIMEOUT_S: int = 40
    STALE_MONSTER_S: int = 60
    STALE_PROJECTILE_S: int = 10
    TIMEOUT: int = 1
    UPDATE_POSITIONS_EVERY_S: float = 0.025
    SLEEP: float = 0.1

    ## Various distance related things ##
    MAX_VISIBLE_RANGE: int = 800
    NPC_INTERACTION_DISTANCE: int = 400
    DASH_DISTANCE: int = 40
    DOOR_REACH_DISTANCE: int = 39
    TRANSPORTER_REACH_DISTANCE: int = 159
    BASE: dict = {
        'h': 8,
        'v': 7,
        'vn': 2
    }

    ## Miscellaneous game related things ##
    BANK_PACK_SIZE: int = 42
    MAX_PARTY_SIZE: int = 9
    PONTY_MARKUP: float = 1.2

    ## Mongo related things ##
    MONGO_UPDATE_S: int = 5

    ## Monsters that are worth tracking in our database ##
    MONSTER_RESPAWN_TIMES: dict = {
        'franky': 20 * 60 * 60,
        'icegolem': 22 * 60 * 60,
        'snowman': 20 * 60 * 60
    }
    ONE_SPAWN_MONSTERS: list = ['dragold', 'fvampire', 'franky', 'greenjr', 'grinch', 'icegolem', 'jr', 'mrgreen', 'mrpumpkin', 'mvampire', 'phoenix', 'pinkgoo', 'rudolph', 'skeletor', 'slenderman', 'snowman', 'stompy', 'tiger', 'wabbit']
    SERVER_INFO_MONSTERS: list = ['dragold', 'franky', 'grinch', 'icegolem', 'pinkgoo', 'slenderman', 'snowman', 'tiger', 'wabbit']
    SPECIAL_MONSTERS: list = [
        # Normal Monsters
        'cutebee', 'dragold', 'fvampire', 'franky', 'goldenbat', 'greenjr', 'grinch', 'icegolem', 'jr', 'mrgreen', 'mrpumpkin', 'mvampire', 'phoenix', 'pinkgoo', 'rudolph', 'skeletor', 'slenderman', 'snowman', 'stompy', 'tiger', 'tinyp', 'wabbit',
        # Crypt monsters
        'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8', 'xmagefi', 'xmagefz', 'xmagen', 'xmagex'
    ]