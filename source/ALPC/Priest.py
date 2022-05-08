import asyncio
import re
from .Constants import Constants
from .Tools import Tools
from .PingCompensatedCharacter import PingCompensatedCharacter

class Priest(PingCompensatedCharacter):
    ctype = 'priest'

    async def absorbSins(self, target):
        async def absorbFn():
            nonlocal self, target
            if not self.ready: raise Exception("We aren't ready yet [absorbSins].")
            absorbed = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, absorbed
                if not absorbed.done():
                    self.socket.off('eval', cooldownCheck)
                    absorbed.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, absorbed
                if not absorbed.done():
                    self.socket.off('eval', cooldownCheck)
                    absorbed.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*[\'"]absorb[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"absorbSins timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'absorb' })
            while not absorbed.done():
                await asyncio.sleep(Constants.SLEEP)