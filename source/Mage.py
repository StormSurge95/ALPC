import asyncio
import re
from Constants import Constants
from Pathfinder import Pathfinder
from PingCompensatedCharacter import PingCompensatedCharacter
from Tools import Tools

class Mage(PingCompensatedCharacter):
    ctype = 'mage'

    async def alchemy(self):
        async def alcFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [alchemy].")
            performedAlchemy = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self
                nonlocal performedAlchemy
                if not performedAlchemy.done():
                    self.socket.off('eval', cooldownCheck)
                    performedAlchemy.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self
                nonlocal performedAlchemy
                if not performedAlchemy.done():
                    self.socket.off('eval', cooldownCheck)
                    performedAlchemy.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]scare[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"alchemy timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'alchemy' })
            while not performedAlchemy.done():
                await asyncio.sleep(Constants.WAIT)
            return performedAlchemy.result()
        return await Tools.tryExcept(alcFn)
    
    async def blink(self, x, y):
        async def blinkFn():
            pass
        pass

    async def burst(self, target):
        async def burstFn():
            pass
        pass

    async def cburst(self, targets):
        async def cBurstFn():
            pass
        pass

    async def energize(self, target, mp = None):
        async def enFn():
            pass
        pass

    async def entangle(self, target, essenceOfNature = None):
        if essenceOfNature == None:
            essenceOfNature = self.locateItem('essenceofnature')
        async def entFn():
            pass
        pass

    async def light(self):
        async def lightFn():
            pass
        pass

    async def magiport(self, target):
        async def magiFn():
            pass
        pass

    async def applyReflection(self, target):
        async def reFn():
            pass
        pass