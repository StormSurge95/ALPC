import asyncio
import re
from .Constants import Constants
from .PingCompensatedCharacter import PingCompensatedCharacter
from .Tools import Tools

class Ranger(PingCompensatedCharacter):
    ctype = 'ranger'

    async def fiveShot(self, target1: str, target2: str, target3: str, target4: str, target5: str):
        targets = [target1, target2, target3, target4, target5]
        async def fsFn():
            nonlocal self, targets
            if not self.ready: raise Exception("We aren't ready yet [fiveShot].")
            fsed = asyncio.get_event_loop().create_future()
            projectiles = []
            def reject(reason = None):
                nonlocal self, fsed
                if not fsed.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('game_response', failCheck)
                    self.socket.off('disappearing_text', failCheck2)
                    self.socket.off('eval', cooldownCheck)
                    fsed.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, fsed
                if not fsed.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('game_response', failCheck)
                    self.socket.off('disappearing_text', failCheck2)
                    self.socket.off('eval', cooldownCheck)
                    fsed.set_result(value)
            def attackCheck(data):
                nonlocal self, targets, projectiles
                if data['attacker'] == self.id and data['type'] == '5shot' and data['target'] in targets:
                    projectiles.append(data['pid'])
            def failCheck(data):
                if isinstance(data, dict):
                    if data['response'] == 'cooldown' and data['skill'] == '5shot':
                        reject(f"fiveShot failed due to cooldown (ms: {data['ms']}).")
                    elif data['response'] == 'no_mp' and data['place'] == '5shot':
                        reject("fiveShot failed due to insufficient MP.")
            def failCheck2(data):
                nonlocal self, projectiles
                if data['message'] == 'NO HITS' and data['id'] == self.id:
                    resolve(projectiles)
            def cooldownCheck(data):
                nonlocal projectiles
                match = re.search('skill_timeout\s*\(\s*[\'"]5shot[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(projectiles)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"fiveShot timeout ({Constants.TIMEOUT}s)")
            self.socket.on('action', attackCheck)
            self.socket.on('game_response', failCheck)
            self.socket.on('disappearing_text', failCheck2)
            self.socket.on('evail', cooldownCheck)
            await self.socket.emit('skill', { 'name': '5shot', 'ids': targets })
            while not fsed.done():
                await asyncio.sleep(Constants.SLEEP)
            return fsed.result()
        return await Tools.tryExcept(fsFn)

    async def fourFinger(self, target: str):
        async def ffFn():
            nonlocal self, target
            if not self.ready: raise Exception("We aren't ready yet [fourFinger].")
            fingered = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, fingered
                if not fingered.done():
                    self.socket.off('eval', cooldownCheck)
                    fingered.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, fingered
                if not fingered.done():
                    self.socket.off('eval', cooldownCheck)
                    fingered.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]4fingers[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"fourFinger timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'id': target, 'name': '4fingers' })
            while not fingered.done():
                await asyncio.sleep(Constants.SLEEP)
            return fingered.result()
        return await Tools.tryExcept(ffFn)
    
    async def huntersMark(self, target: str):
        async def hmFn():
            nonlocal self, target
            if not self.ready: raise Exception("We aren't ready yet [huntersMark].")
            marked = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, marked
                if not marked.done():
                    self.socket.off('eval', cooldownCheck)
                    marked.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, marked
                if not marked.done():
                    self.socket.off('eval', cooldownCheck)
                    marked.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]huntersmark[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"huntersMark timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'huntersmark' })
            while not marked.done():
                await asyncio.sleep(Constants.SLEEP)
            return marked.result()
        return await Tools.tryExcept(hmFn)
    
    async def piercingShot(self, target: str):
        async def psFn():
            nonlocal self, target
            if not self.ready: raise Exception("We aren't ready yet [piercingShot].")
            if self.G['skills']['piercingshot']['mp'] > self.mp: raise Exception("Not enough MP to use piercingShot")
            pierced = asyncio.get_event_loop().create_future()
            projectile = None
            def reject(reason = None):
                nonlocal self, pierced
                if not pierced.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('eval', cooldownCheck)
                    pierced.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, pierced
                if not pierced.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('eval', cooldownCheck)
                    pierced.set_result(value)
            def attackCheck(data):
                nonlocal projectile
                if data['attacker'] == self.id and data['type'] == 'piercingshot' and data['target'] == target:
                    projectile = data['pid']
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]piercingshot[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(projectile)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"piercingShot timeout ({Constants.TIMEOUT}s)")
            self.socket.on('action', attackCheck)
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'piercingshot' })
            while not pierced.done():
                await asyncio.sleep(Constants.SLEEP)
            return pierced.result()
        return await Tools.tryExcept(psFn)

    async def poisonArrow(self, target: str, poison: int = None):
        if poison == None:
            poison = self.locateItem('poison')
        async def paFn():
            nonlocal self, target, poison
            if not self.ready: raise Exception("We aren't ready yet [poisonArrow].")
            if poison == None: raise Exception("We need poison to use this skill")
            poisonArrowed = asyncio.get_event_loop().create_future()
            projectile: str = None
            def reject(reason = None):
                nonlocal self, poisonArrowed
                if not poisonArrowed.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('eval', cooldownCheck)
                    poisonArrowed.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, poisonArrowed
                if not poisonArrowed.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('eval', cooldownCheck)
                    poisonArrowed.set_result(value)
            def attackCheck(data):
                nonlocal self, projectile, target
                if data['attacker'] == self.id and data['type'] == 'poisonarrow' and data['target'] == target:
                    projectile = data['pid']
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]poisonarrow[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(projectile)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"poisonarrow timeout ({Constants.TIMEOUT}s)")
            self.socket.on('action', attackCheck)
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'poisonarrow', 'num': poison })
            while not poisonArrowed.done():
                await asyncio.sleep(Constants.SLEEP)
            return poisonArrowed.result()
        return await Tools.tryExcept(paFn)
    
    async def superShot(self, target: str):
        async def ssFn():
            nonlocal self, target
            if not self.ready: raise Exception("We aren't ready yet [superShot].")
            if self.G['skills']['supershot']['mp'] > self.mp: raise Exception("Not enough MP to use superShot")
            ssed = asyncio.get_event_loop().create_future()
            projectile: str = None
            def reject(reason = None):
                nonlocal self, ssed
                if not ssed.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('eval', cooldownCheck)
                    ssed.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, ssed
                if not ssed.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('eval', cooldownCheck)
                    ssed.set_result(value)
            def attackCheck(data):
                nonlocal self, projectile, target
                if data['attacker'] == self.id and data['type'] == 'supershot' and data['target'] == target:
                    projectile = data['pid']
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]supershot[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(projectile)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"supershot timeout ({Constants.TIMEOUT}s)")
            self.socket.on('action', attackCheck)
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'supershot' })
            while not ssed.done():
                await asyncio.sleep(Constants.SLEEP)
            return ssed.result()
        return await Tools.tryExcept(ssFn)

    async def threeShot(self, target1: str, target2: str, target3: str):
        targets = [target1, target2, target3]
        async def tsFn():
            nonlocal self, targets
            if not self.ready: raise Exception("We aren't ready yet [threeShot].")
            tsed = asyncio.get_event_loop().create_future()
            projectiles = []
            def reject(reason = None):
                nonlocal self, tsed
                if not tsed.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('game_response', failCheck)
                    self.socket.off('disappearing_text', failCheck2)
                    self.socket.off('eval', cooldownCheck)
                    tsed.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, tsed
                if not tsed.done():
                    self.socket.off('action', attackCheck)
                    self.socket.off('game_response', failCheck)
                    self.socket.off('disappearing_text', failCheck2)
                    self.socket.off('eval', cooldownCheck)
                    tsed.set_result(value)
            def attackCheck(data):
                nonlocal self, targets, projectiles
                if data['attacker'] == self.id and data['type'] == '3shot' and data['target'] in targets:
                    projectiles.append(data['pid'])
            def cooldownCheck(data):
                nonlocal projectiles
                match = re.search('skill_timeout\s*\(\s*[\'"]3shot[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(projectiles)
            def failCheck(data):
                if isinstance(data, dict):
                    if data['response'] == 'cooldown' and data['skill'] == '3shot':
                        reject(f"threeShot failed due to cooldown (ms: {data['ms']}).")
                    elif data['response'] == 'no_mp' and data['place'] == '3shot':
                        reject("threeShot failed due to insufficient MP.")
            def failCheck2(data):
                if data['message'] == 'NO HITS' and data['id'] == self.id:
                    resolve(projectiles)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"3shot timeout ({Constants.TIMEOUT}s)")
            self.socket.on('action', attackCheck)
            self.socket.on('game_response', failCheck)
            self.socket.on('disappearing_text', failCheck2)
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'ids': targets, 'name': '3shot' })
            while not tsed.done():
                await asyncio.sleep(Constants.SLEEP)
            return tsed.result()
        return await Tools.tryExcept(tsFn)