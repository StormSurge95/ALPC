import asyncio
import re
from .Constants import Constants
from .Pathfinder import Pathfinder
from .PingCompensatedCharacter import PingCompensatedCharacter
from .Tools import Tools

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
                match = re.search('skill_timeout\s*\(\s*[\'"]alchemy[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"alchemy timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'alchemy' })
            while not performedAlchemy.done():
                await asyncio.sleep(Constants.SLEEP)
            return performedAlchemy.result()
        return await Tools.tryExcept(alcFn)
    
    async def blink(self, x: int, y: int):
        async def blinkFn():
            nonlocal self, x, y
            if not self.ready:
                raise Exception("We aren't ready yet [blink].")
            roundedX = round(x / 10) * 10
            roundedY = round(y / 10) * 10
            if x != roundedX or y != roundedY:
                self.logger.info(f"Blink position changed from ({x}, {y}) to ({roundedX}, {roundedY}).")
                x = roundedX
                y = roundedY
            if not Pathfinder.canStand({ 'map': self.map, 'x': x, 'y': y }): raise Exception(f"We cannot blink to {{ {self.map}: {x}, {y} }}")
            blinked = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, blinked
                if not blinked.done():
                    self.socket.off('new_map', successCheck)
                    self.socket.off('game_response', failCheck)
                    blinked.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, blinked
                if not blinked.done():
                    self.socket.off('new_map', successCheck)
                    self.socket.off('game_response', failCheck)
                    blinked.set_result(value)
            def successCheck(data):
                if data['effect'] == 'blink' and x == data['x'] and y == data['y']:
                    resolve()
            def failCheck(data):
                if isinstance(data, str):
                    if data == 'blink_failed':
                        reject(f"Blink from {{ {self.map}: {self.x}, {self.y} }} to {{ {self.map}: {x}, {y} }} failed.")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"blink timeout ({Constants.TIMEOUT}s)")
            self.socket.on('new_map', successCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('skill', { 'name': 'blink', 'x': x, 'y': y })
            while not blinked.done():
                await asyncio.sleep(Constants.SLEEP)
            return blinked.result()
        return await Tools.tryExcept(blinkFn)

    async def burst(self, target: str):
        async def burstFn():
            nonlocal self, target
            if not self.ready:
                raise Exception("We aren't ready yet [burst].")
            bursted = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, bursted
                if not bursted.done():
                    self.socket.off('eval', cooldownCheck)
                    bursted.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, bursted
                if not bursted.done():
                    self.socket.off('eval', cooldownCheck)
                    bursted.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]burst[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"burst timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'burst', 'id': target })
            while not bursted.done():
                await asyncio.sleep(Constants.SLEEP)
            return bursted.result()
        return await Tools.tryExcept(burstFn)

    async def cburst(self, targets: str):
        async def cBurstFn():
            nonlocal self, targets
            if not self.ready:
                raise Exception("We aren't ready yet [cburst].")
            if len(targets) == 0:
                raise Exception("No targets were given to cburst.")
            cbursted = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, cbursted
                if not cbursted.done():
                    self.socket.off('game_response', failCheck)
                    self.socket.off('disappearing_text', failCheck2)
                    self.socket.off('eval', cooldownCheck)
                    cbursted.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, cbursted
                if not cbursted.done():
                    self.socket.off('game_response', failCheck)
                    self.socket.off('disappearing_text', failCheck2)
                    self.socket.off('eval', cooldownCheck)
                    cbursted.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]cburst[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve()
            def failCheck(data):
                if isinstance(data, dict):
                    if data['response'] == 'cooldown' and data['skill'] == 'cburst':
                        reject(f"cburst failed due to cooldown (ms: {data['ms']}).")
                    elif data['response'] == 'no_mp' and data['place'] == 'cburst':
                        reject(f"cburst failed due to insufficient MP.")
                    elif data['response'] == 'too_far' and data['place'] == 'cburst':
                        # TODO: separate promises?
                        reject(f"{data['id']} is too far away to cburst (dist: {data['dist']}).")
                elif isinstance(data, str):
                    if data == 'skill_cant_incapacitated':
                        reject("We can't cburst, we are incapacitated.")
            def failCheck2(data):
                if data['message'] == 'NO HITS' and data['id'] == self.id:
                    resolve() # cbursted successfully; but didn't hit anything
            self.socket.on('eval', cooldownCheck)
            self.socket.on('game_response', failCheck)
            self.socket.on('disappearing_text', failCheck2)
            await self.socket.emit('skill', { 'name': 'cburst', 'targets': targets })
            Tools.setTimeout(reject, Constants.TIMEOUT, f"cburst timeout ({Constants.TIMEOUT}s)")
            while not cbursted.done():
                await asyncio.sleep(Constants.SLEEP)
            return cbursted.result()
        return await Tools.tryExcept(cBurstFn)

    async def energize(self, target: str, mp: int = None):
        async def enFn():
            nonlocal self, target, mp
            if not self.ready:
                raise Exception("We aren't ready yet [energize].")
            energized = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, energized
                if not energized.done():
                    self.socket.off('eval', cooldownCheck)
                    energized.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, energized
                if not energized.done():
                    self.socket.off('eval', cooldownCheck)
                    energized.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]energize[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"energize timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            if mp != None:
                await self.socket.emit('skill', { 'id': target, 'mp': mp, 'name': 'energize' })
            else:
                await self.socket.emit('skill', { 'id': target, 'name': 'energize' })
            while not energized.done():
                await asyncio.sleep(Constants.SLEEP)
            return energized.result()
        return await Tools.tryExcept(enFn)

    async def entangle(self, target: str, essenceOfNature: int = None):
        async def entFn():
            nonlocal self, target, essenceOfNature
            if not self.ready:
                raise Exception("We aren't ready yet [entangle].")
            if essenceOfNature == None:
                essenceOfNature = self.locateItem('essenceofnature')
            if essenceOfNature == None:
                raise Exception("We need an essenceofnature in order to entangle.")
            tangled = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, tangled
                if not tangled.done():
                    self.socket.off('eval', cooldownCheck)
                    tangled.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, tangled
                if not tangled.done():
                    self.socket.off('eval', cooldownCheck)
                    tangled.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]entangle[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"entangle timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'entangle', 'id': target, 'num': essenceOfNature })
            while not tangled.done():
                await asyncio.sleep(Constants.SLEEP)
            return tangled.result()
        return await Tools.tryExcept(entFn)

    async def light(self):
        async def lightFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [light].")
            lit = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, lit
                if not lit.done():
                    self.socket.off('eval', cooldownCheck)
                    lit.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, lit
                if not lit.done():
                    self.socket.off('eval', cooldownCheck)
                    lit.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]light[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"light timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'light' })
            while not lit.done():
                await asyncio.sleep(Constants.SLEEP)
            return lit.result()
        return await Tools.tryExcept(lightFn)

    async def magiport(self, target: str):
        async def magiFn():
            nonlocal self, target
            if not self.ready:
                raise Exception("We aren't ready yet [magiport].")
            magiportOfferSent = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, magiportOfferSent
                if not magiportOfferSent.done():
                    self.socket.off('game_response', magiportCheck)
                    magiportOfferSent.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, magiportOfferSent
                if not magiportOfferSent.done():
                    self.socket.off('game_response', magiportCheck)
                    magiportOfferSent.set_result(value)
            def magiportCheck(data):
                if isinstance(data, dict):
                    if data['response'] == 'magiport_failed' and data['id'] == target:
                        reject(f"Magiport for {target} failed.")
                    elif data['response'] == 'magiport_sent' and data['id'] == target:
                        resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT, f"magiport timeout ({Constants.TIMEOUT}s)")
            self.socket.on('game_response', magiportCheck)
            await self.socket.emit('skill', { 'name': 'magiport', 'id': target })
            while not magiportOfferSent.done():
                await asyncio.sleep(Constants.SLEEP)
            return magiportOfferSent.result()
        return await Tools.tryExcept(magiFn)

    async def applyReflection(self, target: str):
        async def reFn():
            nonlocal self, target
            if not self.ready:
                raise Exception("We aren't ready yet [applyReflection].")
            reflectioned = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, reflectioned
                if not reflectioned.done():
                    self.socket.off('eval', cooldownCheck)
                    reflectioned.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, reflectioned
                if not reflectioned.done():
                    self.socket.off('eval', cooldownCheck)
                    reflectioned.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]reflection[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve()
            Tools.setTimeout(reject, Constants.TIMEOUT)
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'reflection', 'id': target })
            while not reflectioned.done():
                await asyncio.sleep(Constants.SLEEP)
            return reflectioned.result()
        return await Tools.tryExcept(reFn)