import asyncio
import re
from .PingCompensatedCharacter import PingCompensatedCharacter
from .Constants import Constants
from .Tools import Tools

class Rogue(PingCompensatedCharacter):
    ctype = 'rogue'

    async def invis(self):
        async def invisFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [invis].")
            await self.socket.emit('skill', { 'name': 'invis' })
        return await Tools.tryExcept(invisFn)
    
    async def mentalBurst(self, target: str):
        async def mbFn():
            nonlocal self, target
            if not self.ready: raise Exception("We aren't ready yet [mentalBurst].")
            bursted = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, bursted
                if not bursted.done():
                    self.socket.off('eval', cooldownCheck)
                    self.socket.off('death', deathCheck)
                    self.socket.off('game_response', failCheck)
                    bursted.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, bursted
                if not bursted.done():
                    self.socket.off('eval', cooldownCheck)
                    self.socket.off('death', deathCheck)
                    self.socket.off('game_response', failCheck)
                    bursted.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]mentalburst[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            def deathCheck(data):
                if data['id'] == target:
                    reject(f"Entity {target} not found")
            def failCheck(data):
                if isinstance(data, dict):
                    if data['response'] == 'cooldown' and data['skill'] == 'mentalburst':
                        reject(f"mentalBurst on {target} failed due to cooldown (ms: {data['ms']}).")
                    elif data['response'] == 'too_far' and data['place'] == 'mentalburst':
                        reject(f"{target} is too far away to mentalBurst (dist: {data['dist']}).")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"mentalBurst timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            self.socket.on('death', deathCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'mentalburst' })
            while not bursted.done():
                await asyncio.sleep(Constants.SLEEP)
            return bursted.result()
        return await Tools.tryExcept(mbFn)

    async def poisonCoat(self):
        async def pcFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [poisonCoat].")
            coated = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, coated
                if not coated.done():
                    self.socket.off('eval', cooldownCheck)
                    coated.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, coated
                if not coated.done():
                    self.socket.off('eval', cooldownCheck)
                    coated.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]pcoat[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"poisonCoat timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'pcoat' })
            while not coated.done():
                await asyncio.sleep(Constants.SLEEP)
            return coated.result()
        return await Tools.tryExcept(pcFn)
    
    async def quickPunch(self, target: str):
        async def qpFn():
            nonlocal self, target
            if not self.ready: raise Exception("We aren't ready yet [quickPunch].")
            punched = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, punched
                if not punched.done():
                    self.socket.off('eval', cooldownCheck)
                    punched.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, punched
                if not punched.done():
                    self.socket.off('eval', cooldownCheck)
                    punched.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]quickpunch[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"quickPunch timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'quickpunch' })
            while not punched.done():
                await asyncio.sleep(Constants.SLEEP)
            return punched.result()
        return await Tools.tryExcept(qpFn)

    async def quickStab(self, target: str):
        async def qsFn():
            nonlocal self, target
            if not self.ready: raise Exception("We aren't ready yet [quickStab].")
            stabbed = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, stabbed
                if not stabbed.done():
                    self.socket.off('eval', cooldownCheck)
                    self.socket.off('death', deathCheck)
                    self.socket.off('game_response', failCheck)
                    stabbed.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, stabbed
                if not stabbed.done():
                    self.socket.off('eval', cooldownCheck)
                    self.socket.off('death', deathCheck)
                    self.socket.off('game_response', failCheck)
                    stabbed.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]quickstab[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            def failCheck(data):
                if isinstance(data, dict):
                    if data['response'] == 'cooldown' and data['skill'] == 'quickstab':
                        reject(f"quickStab on {target} failed due to cooldown (ms: {data['ms']}).")
                    elif data['response'] == 'too_far' and data['place'] == 'quickstab':
                        reject(f"{target} is too far away to quickStab (dist: {data['dist']}")
            def deathCheck(data):
                if data['id'] == target:
                    reject(f"Entity {target} not found")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"quickStab timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            self.socket.on('death', deathCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'quickstab' })
            while not stabbed.done():
                await asyncio.sleep(Constants.SLEEP)
            return stabbed.result()
        return await Tools.tryExcept(qsFn)
    
    async def rspeed(self, target: str):
        async def rsFn():
            nonlocal self, target
            if not self.ready: raise Exception("We aren't ready yet [rspeed].")
            rSpeedApplied = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, rSpeedApplied
                if not rSpeedApplied.done():
                    self.socket.off('eval', cooldownCheck)
                    rSpeedApplied.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, rSpeedApplied
                if not rSpeedApplied.done():
                    self.socket.off('eval', cooldownCheck)
                    rSpeedApplied.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]rspeed[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"rspeed timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'rspeed' })
            while not rSpeedApplied.done():
                await asyncio.sleep(Constants.SLEEP)
            return rSpeedApplied.result()
        return await Tools.tryExcept(rsFn)
    
    async def shadowStrike(self, shadowStone: int = None):
        if shadowStone == None:
            shadowStone = self.locateItem('shadowstone')
        async def ssFn():
            nonlocal self, shadowStone
            if not self.ready: raise Exception("We aren't ready yet [shadowStrike].")
            if shadowStone == None: raise Exception("We need a shadowstone in order to shadowstrike.")
            shadowStruck = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, shadowStruck
                if not shadowStruck.done():
                    self.socket.off('eval', cooldownCheck)
                    shadowStruck.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, shadowStruck
                if not shadowStruck.done():
                    self.socket.off('eval', cooldownCheck)
                    shadowStruck.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]shadowstrike[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"rspeed timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'shadowstrike', 'num': shadowStone })
            while not shadowStruck.done():
                await asyncio.sleep(Constants.SLEEP)
            return shadowStruck.result()
        return await Tools.tryExcept(ssFn)

    async def stopInvis(self):
        async def stopFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [stopInvis].")
            await self.socket.emit('stop', { 'action': 'invis' })
        return await Tools.tryExcept(stopFn)