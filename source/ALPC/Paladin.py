from .Tools import Tools
from .Constants import Constants
from .PingCompensatedCharacter import PingCompensatedCharacter
import asyncio
import re

class Paladin(PingCompensatedCharacter):
    ctype = 'paladin'

    async def manaShieldOff(self):
        async def msOffFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [manaShieldOff].")
            if self.s.get('mshield') == None: return False # it's already off

            unshield = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, unshield
                if not unshield.done():
                    self.socket.off('player', successCheck)
                    unshield.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, unshield
                if not unshield.done():
                    self.socket.off('player', successCheck)
                    unshield.set_result(value)
            def successCheck(data):
                if data.get('s') == None or data['s'].get('mshield') == None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"manaShieldOff timeout ({Constants.TIMEOUT}s)")
            self.socket.on('player', successCheck)
            await self.socket.emit('skill', { 'name': 'mshield' })
            while not unshield.done():
                await asyncio.sleep(Constants.SLEEP)
            return unshield.result()
        return await Tools.tryExcept(msOffFn)
    
    async def manaShieldOn(self):
        async def msOnFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [manaShieldOn].")
            if self.s.get('mshield') != None: return False

            shielded = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, shielded
                if not shielded.done():
                    self.socket.off('player', successCheck)
                    shielded.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, shielded
                if not shielded.done():
                    self.socket.off('player', successCheck)
                    shielded.set_result(value)
            def successCheck(data):
                if data.get('s', {}).get('mshield') != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"manaShieldOn timeout ({Constants.TIMEOUT}s)")
            self.socket.on('player', successCheck)
            await self.socket.emit('skill', { 'name': 'mshield' })
            while not shielded.done():
                await asyncio.sleep(Constants.SLEEP)
            return shielded.result()
        return await Tools.tryExcept(msOnFn)
    
    async def selfHeal(self):
        async def healFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [selfHeal].")
            healed = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, healed
                if not healed.done():
                    self.socket.off('eval', cooldownCheck)
                    healed.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, healed
                if not healed.done():
                    self.socket.off('eval', cooldownCheck)
                    healed.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]selfheal[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"selfheal timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'selfheal' })
            while not healed.done():
                await asyncio.sleep(Constants.SLEEP)
            return healed.result()
        return await Tools.tryExcept(healFn)