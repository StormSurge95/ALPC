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
            return absorbed.result()
        return await Tools.tryExcept(absorbFn)
    
    async def curse(self, target):
        async def curseFn():
            nonlocal self, target
            if not self.ready: raise Exception("We aren't ready yet [curse].")
            cursed = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, cursed
                if not cursed.done():
                    self.socket.off('eval', cooldownCheck)
                    cursed.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, cursed
                if not cursed.done():
                    cursed.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*[\'"]curse[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"curse timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'curse' })
            while not cursed.done():
                await asyncio.sleep(Constants.SLEEP)
            return cursed.result()
        return await Tools.tryExcept(curseFn)
    
    async def darkBlessing(self):
        async def dbFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [darkBlessing].")
            blessed = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, blessed
                if not blessed.done():
                    self.socket.off('eval', cooldownCheck)
                    blessed.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, blessed
                if not blessed.done():
                    self.socket.off('eval', cooldownCheck)
                    blessed.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*[\'"]darkblessing[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"darkBlessing timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'darkblessing' })
            while not blessed.done():
                await asyncio.sleep(Constants.SLEEP)
            return blessed.result()
        return await Tools.tryExcept(dbFn)
    
    async def heal(self, id):
        async def healFn():
            nonlocal self, id
            if not self.ready: raise Exception("We aren't ready yet [heal].")
            healed = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, healed
                if not healed.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('game_response', failCheck)
                    self.socket.off('notthere', failCheck2)
                    self.socket.off('death', deathCheck)
                    healed.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, healed
                if not healed.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('game_response', failCheck)
                    self.socket.off('notthere', failCheck2)
                    self.socket.off('death', deathCheck)
                    healed.set_result(value)
            def deathCheck(data):
                nonlocal id
                if data['id'] == id:
                    reject(f"Entity {id} not found.")
            def failCheck(data):
                nonlocal id
                if isinstance(data, dict):
                    if data['response'] == 'disabled':
                        reject(f"Heal on {id} failed (disabled).")
                    elif data['response'] == 'attack_failed' and data['id'] == id:
                        reject(f"Heal on {id} failed.")
                    elif data['response'] == 'too_far' and data['id'] == id:
                        reject(f"{id} is too far away to heal (dist: {data['dist']}).")
                    elif data['response'] == 'cooldown' and data['id'] == id:
                        reject(f"Heal on {id} failed due to cooldown (ms: {data['ms']}).")
            def failCheck2(data):
                if data['place'] == 'attack':
                    reject(f"{id} could not be found to attack.")
            def attackCheck(data):
                if data['attacker'] == self.id and data['target'] == id and data['type'] == 'heal':
                    resolve(data['pid'])
            Tools.setTimeout(reject, Constants.TIMEOUT, f"heal timeout ({Constants.TIMEOUT}s)")
            self.socket.on('action', attackCheck)
            self.socket.on('game_response', failCheck)
            self.socket.on('notthere', failCheck2)
            self.socket.on('death', deathCheck)
            await self.socket.emit('heal', { 'id': id })
            while not healed.done():
                await asyncio.sleep(Constants.SLEEP)
            return healed.result()
        return Tools.tryExcept(healFn)
    
    async def partyHeal(self):
        async def partyHealFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [partyHeal].")
            partyHealed = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, partyHealed
                if not partyHealed.done():
                    self.socket.off('eval', cooldownCheck)
                    partyHealed.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, partyHealed
                if not partyHealed.done():
                    self.socket.off('eval', cooldownCheck)
                    partyHealed.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*[\'"]partyheal[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"partyHeal timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'partyheal' })
            while not partyHealed.done():
                await asyncio.sleep(Constants.SLEEP)
            return partyHealed.result()
        return await Tools.tryExcept(partyHealFn)
    
    async def revive(self, target, essenceOfLife = None):
        if essenceOfLife == None:
            essenceOfLife = self.locateItem('essenceoflife')
        async def reviveFn():
            nonlocal self, target, essenceOfLife
            if not self.ready:
                raise Exception("We aren't ready yet [revive].")
            if essenceOfLife == None:
                raise Exception("We don't have any essenceoflife in our inventory.")
            revived = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, revived
                if not revived.done():
                    self.socket.off('eval', cooldownCheck)
                    revived.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, revived
                if not revived.done():
                    self.socket.off('eval', cooldownCheck)
                    revived.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*[\'"]revive[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"revive timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'revive', 'num': essenceOfLife })
            while not revived.done():
                await asyncio.sleep(Constants.SLEEP)
            return revived.result()
        return await Tools.tryExcept(reviveFn)