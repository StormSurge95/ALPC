from pymongo import MongoClient, ASCENDING
from .Schemas import AchievementSchema, BankSchema, DeathSchema, EntitySchema, NPCSchema, PlayerSchema, RespawnSchema

class Database:
    nextUpdate = {}
    connection = None

    @staticmethod
    def connect(uri):
        if Database.connection != None:
            MongoClient.close()
        
        Database.connection = MongoClient(host=uri, connect=True)

        Database._setup()

    @staticmethod
    def _setup():
        db = Database.connection.get_database('ALPC')
        try:
            achievements = db.create_collection('achievements', validator=AchievementSchema)
        except:
            achievements = db.achievements
        achievements.create_index([( 'name', ASCENDING ), ( 'date', ASCENDING )], unique=True)
        try:
            db.create_collection('banks', validator=BankSchema)
        except:
            pass
        try:
            deaths = db.create_collection('deaths', validator=DeathSchema)
        except:
            deaths = db.deaths
        deaths.create_index([( 'serverRegion', ASCENDING ), ( 'serverIdentifier', ASCENDING )])
        deaths.create_index([( 'name', ASCENDING )])
        deaths.create_index([( 'time', ASCENDING )])
        try:
            entities = db.create_collection('entities', validator=EntitySchema)
        except:
            entities = db.entities
        entities.create_index([( 'type', ASCENDING )])
        entities.create_index([( 'name', ASCENDING ), ( 'serverIdentifier', ASCENDING ), ( 'serverRegion', ASCENDING ), ( 'type', ASCENDING )], unique=True)
        entities.create_index([( 'lastSeen', ASCENDING )])
        try:
            npcs = db.create_collection('npcs', validator=NPCSchema)
        except:
            npcs = db.npcs
        npcs.create_index([( 'serverRegion', ASCENDING ), ( 'serverIdentifier', ASCENDING ), ( 'name', ASCENDING )], unique=True)
        npcs.create_index([( 'lastSeen', ASCENDING )])
        try:
            players = db.create_collection('players', validator=PlayerSchema)
        except:
            players = db.players
        players.create_index([( 'name', ASCENDING )], unique=True)
        players.create_index([( 'serverIdentifier', ASCENDING ), ( 'serverRegion', ASCENDING )])
        players.create_index([( 'lastSeen', ASCENDING )])
        players.create_index([( 'owner', ASCENDING )])
        try:
            respawns = db.create_collection('respawns', validator=RespawnSchema)
        except:
            respawns = db.respawns
        respawns.create_index([( 'type', ASCENDING )])
        respawns.create_index([( 'serverIdentifier', ASCENDING ), ( 'serverRegion', ASCENDING ), ( 'type', ASCENDING )], unique=True)
        respawns.create_index([( 'estimatedRespawn', ASCENDING )])

    def disconnect():
        if connection == None: return

        connection.close()

        connection = None