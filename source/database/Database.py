#import motor.motor_asyncio as aiomongo
import typing

class Database:
    nextUpdate: dict = {'max': 1000}
    #connection: aiomongo.AsyncIOMotorClient = None
    connection = None

    #@staticmethod
    #def connect(uri: str):
        #if Database.connection:
            #connection.close()
        #conn = aiomongo.AsyncIOMotorClient(uri)

        #Database.connection = conn

        #return conn

    @staticmethod
    def disconnect():
        if not Database.connection:
            return
        #Database.connection.close()