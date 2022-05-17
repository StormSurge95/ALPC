import asyncio
import re
from unittest.result import failfast
from .PingCompensatedCharacter import PingCompensatedCharacter
from .Constants import Constants
from .Tools import Tools

class Warrior(PingCompensatedCharacter):
    ctype = "warrior"

    async def agitate(self):
        async def agitateFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [agitate].")
            agitated = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, agitated
                if not agitated.done():
                    self.socket.off('eval', cooldownCheck)
                    self.socket.off('game_response', failCheck)
                    agitated.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, agitated
                if not agitated.done():
                    self.socket.off('eval', cooldownCheck)
                    self.socket.off('game_response', failCheck)
                    agitated.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]agitate[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            def failCheck(data):
                if isinstance(data, dict) and data['response'] == 'cooldown' and data['skill'] == 'agitate':
                    reject(f"Agitate failed due to cooldown (ms: {data['ms']})")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"agitate timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('skill', { 'name': 'agitate' })
            while not agitated.done():
                await asyncio.sleep(Constants.SLEEP)
            return agitated.result()
        return await Tools.tryExcept(agitateFn)

    async def charge(self):
        async def chargeFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [charge].")
            charged = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, charged
                if not charged.done():
                    self.socket.off('player', successCheck)
                    self.socket.off('game_response', failCheck)
                    charged.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, charged
                if not charged.done():
                    self.socket.off('player', successCheck)
                    self.socket.off('game_response', failCheck)
                    charged.set_result(value)
            def successCheck(data):
                if data.get('hitchhikers') == None: return
                for (event, datum) in data['hitchhikers'].items():
                    if event == 'game_response' and datum['response'] == 'skill_success' and datum['name'] == 'charge':
                        resolve(True)
                        return
            def failCheck(data):
                if isinstance(data, dict) and data['response'] == 'cooldown' and data['skill'] == 'charge':
                    reject(f"Charge failed due to cooldown (ms: {data['ms']})")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"charge timeout ({Constants.TIMEOUT}s)")
            self.socket.on('player', successCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('skill', { 'name': 'charge' })
            while not charged.done():
                await asyncio.sleep(Constants.SLEEP)
            return charged.result()
        return await Tools.tryExcept(chargeFn)

    async def cleave(self):
        async def cleaveFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [cleave].")
            cleaved = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, cleaved
                if not cleaved.done():
                    self.socket.off('eval', cooldownCheck)
                    self.socket.off('game_response', failCheck)
                    cleaved.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, cleaved
                if not cleaved.done():
                    self.socket.off('eval', cooldownCheck)
                    self.socket.off('game_response', failCheck)
                    cleaved.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]cleave[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            def failCheck(data):
                if isinstance(data, dict) and data['response'] == 'cooldown' and data['skill'] == 'cleave':
                    reject(f"Cleave failed due to cooldown (ms: {data['ms']})")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"cleave timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('skill', { 'name': 'cleave' })
            while not cleaved.done():
                await asyncio.sleep(Constants.SLEEP)
            return cleaved.result()
        return await Tools.tryExcept(cleaveFn)

    async def dash(self, to: dict):
        async def dashFn():
            nonlocal self, to
            if not self.ready: raise Exception("We aren't ready yet [dash].")
            if to.get('map') != None and to['map'] != self.map: raise Exception("We cannot dash across maps.")
            dashed = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not dashed.done():
                    self.socket.off('eval', dashedCheck)
                    self.socket.off('game_response', failCheck)
                    dashed.set_exception(Exception(reason))
            def resolve(value = None):
                if not dashed.done():
                    self.socket.off('eval', dashedCheck)
                    self.socket.off('game_response', failCheck)
                    dashed.set_result(value)
            def dashedCheck(data):
                match = re.search('^ui_move', data['code'])
                if match != None:
                    resolve(True)
            def failCheck(data):
                if isinstance(data, str) and data == 'dash_failed':
                    reject('Dash failed')
            Tools.setTimeout(reject, Constants.TIMEOUT, f"dash timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', dashedCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('skill', { 'name': 'dash', 'x': to['x'], 'y': to['y'] })
            while not dashed.done():
                await asyncio.sleep(Constants.SLEEP)
            return dashed.result()
        return await Tools.tryExcept(dashFn)

    async def hardshell(self):
        async def hsFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [hardshell].")
            hardshelled = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not hardshelled.done():
                    self.socket.off('player', successCheck)
                    self.socket.off('eval', cooldownCheck)
                    self.socket.off('game_response', responseCheck)
                    hardshelled.set_exception(Exception(reason))
            def resolve(value = None):
                if not hardshelled.done():
                    self.socket.off('player', successCheck)
                    self.socket.off('eval', cooldownCheck)
                    self.socket.off('game_response', responseCheck)
                    hardshelled.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]hardshell[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            def successCheck(data):
                if data.get('hitchhikers') == None: return
                for (event, datum) in data['hitchhikers'].items():
                    if event == 'game_response' and datum['response'] == 'skill_success' and datum['name'] == 'hardshell':
                        resolve(True)
                        return
            def responseCheck(data):
                if isinstance(data, dict):
                    if data['response'] == 'cooldown' and data['skill'] == 'hardshell':
                        reject(f"Hardshell failed due to cooldown (ms: {data['ms']})")
                    elif data['response'] == 'skill_success' and data['name'] == 'hardshell':
                        resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"hardshell timeout ({Constants.TIMEOUT}s)")
            self.socket.on('player', successCheck)
            self.socket.on('eval', cooldownCheck)
            self.socket.on('game_response', responseCheck)
            await self.socket.emit('skill', { 'name': 'hardshell' })
            while not hardshelled.done():
                await asyncio.sleep(Constants.SLEEP)
            return hardshelled.result()
        return await Tools.tryExcept(hsFn)

    async def stomp(self):
        async def stompFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [stomp].")
            stomped = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                if not stomped.done():
                    self.socket.off('eval', cooldownCheck)
                    self.socket.off('game_response', failCheck)
                    stomped.set_exception(Exception(reason))
            def resolve(value = None):
                if not stomped.done():
                    self.socket.off('eval', cooldownCheck)
                    self.socket.off('game_response', failCheck)
                    stomped.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]stomp[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            def failCheck(data):
                if isinstance(data, dict) and data['response'] == 'cooldown' and data['skill'] == 'stomp':
                    reject(f"Stomp failed due to cooldown (ms: {data['ms']})")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"stomp timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('skill', { 'name': 'stomp' })
            while not stomped.done():
                await asyncio.sleep(Constants.SLEEP)
            return stomped.result()
        return await Tools.tryExcept(stompFn)

    async def taunt(self, target: str):
        async def tauntFn():
            nonlocal self, target
            if not self.ready: raise Exception("We aren't ready yet [taunt].")
            taunted = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                self.socket.off('action', tauntCheck)
                self.socket.off('game_response', failCheck)
                taunted.set_exception(Exception(reason))
            def resolve(value = None):
                self.socket.off('action', tauntCheck)
                self.socket.off('game_response', failCheck)
                taunted.set_result(value)
            def tauntCheck(data):
                if data['attacker'] == self.id and data['type'] == 'taunt' and data['target'] == target:
                    resolve(data['pid'])
            def failCheck(data):
                if isinstance(data, dict):
                    if data['response'] == 'no_target':
                        reject(f"Taunt on {target} failed (no target).")
                    elif data['response'] == 'too_far' and data['id'] == target:
                        reject(f"{target} is too far away to taunt (dist: {data['dist']})")
                    elif data['response'] == 'cooldown' and data['id'] == target and data['skill'] == 'taunt':
                        reject(f"Taunt on {target} failed due to cooldown (ms: {data['ms']}).")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"taunt timeout ({Constants.TIMEOUT}s)")
            self.socket.on('action', tauntCheck)
            self.socket.on('game_response', failCheck)
            await self.socket.emit('skill', { 'name': 'taunt', 'id': target })
            while not taunted.done():
                await asyncio.sleep(Constants.SLEEP)
            return taunted.result()
        return await Tools.tryExcept(tauntFn)

    async def warcry(self):
        async def wcFn():
            nonlocal self
            if not self.ready: raise Exception("We aren't ready yet [warcry].")
            warcried = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                self.socket.off('eval', cooldownCheck)
                warcried.set_exception(Exception(reason))
            def resolve(value = None):
                self.socket.off('eval', cooldownCheck)
                warcried.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*\(\s*[\'"]warcry[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"warcry timeout ({Constants.TIMEOUT}s)")
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'name': 'warcry' })
            while not warcried.done():
                await asyncio.sleep(Constants.SLEEP)
            return warcried.result()
        return await Tools.tryExcept(wcFn)