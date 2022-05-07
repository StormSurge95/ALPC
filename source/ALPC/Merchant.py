from datetime import datetime
import re
from .Constants import Constants
from .PingCompensatedCharacter import PingCompensatedCharacter
from .Tools import Tools
import asyncio

class Merchant(PingCompensatedCharacter):
    ctype = 'merchant'

    async def fish(self):
        async def fishFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [fish].")
            startedFishing = False
            if self.c.get('fishing'): startedFishing = True
            fished = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, fished
                if not fished.done():
                    self.socket.off('game_response', failCheck1)
                    self.socket.off('ui', failCheck2)
                    self.socket.off('eval', caughtCheck)
                    self.socket.off('player', failCheck3)
                    fished.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, fished
                if not fished.done():
                    self.socket.off('game_response', failCheck1)
                    self.socket.off('ui', failCheck2)
                    self.socket.off('eval', caughtCheck)
                    self.socket.off('player', failCheck3)
                    fished.set_result(value)
            def caughtCheck(data):
                match = re.search('skill_timeout\s*[\'"]fishing[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            def failCheck1(data):
                if isinstance(data, str):
                    if data == 'skill_cant_wtype':
                        reject("We don't have a fishing rod equipped.")
                elif isinstance(data, dict):
                    if data['response'] == 'cooldown' and data['place'] == 'fishing' and data['skill'] == 'fishing':
                        reject(f"Fishing is on cooldown ({data['ms']}ms remaining)")
            def failCheck2(data):
                if data['type'] == 'fishing_fail' and data['name'] == self.id:
                    reject("We failed to fish.")
                elif data['type'] == 'fishing_none':
                    resolve(False)
            def failCheck3(data):
                nonlocal startedFishing
                if not startedFishing and data.c.get('fishing'):
                    startedFishing = True
                elif startedFishing and not data.c.get('fishing'):
                    resolve(False)
            Tools.setTimeout(reject, 20, f"fish timeout (20s)")
            self.socket.on('game_response', failCheck1)
            self.socket.on('eval', caughtCheck)
            self.socket.on('ui', failCheck2)
            self.socket.on('player', failCheck3)
            await self.socket.emit('skill', { 'name': 'fishing' })
            while not fished.done():
                await asyncio.sleep(Constants.WAIT)
            return fished.result()
        return await Tools.tryExcept(fishFn)

    async def joinGiveaway(self, slot, id, rid):
        async def joinFn():
            nonlocal self, slot, id, rid
            if not self.ready:
                raise Exception("We aren't ready yet [joinGiveaway].")
            merchant = self.players.get(id)
            if merchant == None or Tools.distance(self, merchant) > Constants.NPC_INTERACTION_DISTANCE:
                raise Exception(f"{id} is too far away.")
            if merchant.slots[slot].get('giveaway') == None:
                raise Exception(f"{id}'s slot {slot} is not a giveaway.")
            if self.id in merchant.slots[slot].get('list', []):
                return
            
            await self.socket.emit('join_giveaway', { 'slot': slot, 'id': id, 'rid': rid })
        return await Tools.tryExcept(joinFn)

    async def listForSale(self, itemPos, price, tradeSlot = None, quantity = 1):
        async def listFn():
            nonlocal self, itemPos, price, tradeSlot, quantity
            if not self.ready:
                raise Exception("We aren't ready yet [listForSale].")
            itemInfo = self.items[itemPos]
            if itemInfo == None:
                raise Exception(f"We do not have an item in slot {itemPos}.")
            if price <= 0:
                raise Exception("The lowest you can set the price to is 1.")
            if quantity <= 0:
                raise Exception("The lowest you can set the quantity to is 1.")
            gInfo = self.G['items'][itemInfo['name']]
            if tradeSlot == None and itemInfo.get('q') != None:
                for slotName in self.slots:
                    if 'trade' not in slotName: continue
                    slotInfo = self.slots[slotName]
                    if slotInfo == None: continue

                    if slotInfo['name'] != itemInfo['name']: continue
                    if slotInfo['p'] != itemInfo['p']: continue

                    if quantity + slotInfo['q'] > gInfo['s']: continue

                    if price < slotInfo['price']: continue

                    tradeSlot = slotName
                    break
            if tradeSlot == None:
                for slotName in self.slots:
                    if 'trade' not in slotName: continue
                    slotInfo = self.slots[slotName]
                    if slotInfo != None: continue

                    tradeSlot = slotName
                    break
                if tradeSlot == None: raise Exception("We don't have an empty trade slot to list the item for sale.")
            slotInfo = self.slots[tradeSlot]
            if slotInfo != None:
                if itemInfo['name'] == slotInfo['name'] and price >= slotInfo['price'] and gInfo.get('s') != None and ((quantity + slotInfo['q']) <= gInfo['s']):
                    if itemPos != 0:
                        await self.swapItems(0, itemPos)
                    
                    await self.unequip(tradeSlot)
                    quantity += slotInfo['q']

                    if itemPos != 0:
                        await self.swapItems(0, itemPos)
                else:
                    raise Exception(f"We are already trading something in {tradeSlot}.")
            
            listed = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, listed
                if not listed.done():
                    self.socket.off('game_response', failCheck1)
                    self.socket.off('disappearing_text', failCheck2)
                    self.socket.off('player', successCheck)
                    listed.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, listed
                if not listed.done():
                    self.socket.off('game_response', failCheck1)
                    self.socket.off('disappearing_text', failCheck2)
                    self.socket.off('player', successCheck)
                    listed.set_result(value)
            def failCheck1(data):
                if isinstance(data, str):
                    if data == 'slot_occupied':
                        reject(f"We are already listing something in {tradeSlot}.")
            def failCheck2(data):
                if data['message'] == "CAN'T EQUIP" and data['id'] == self.id:
                    reject(f"We failed listed the item in {tradeSlot}.")
            def successCheck(data):
                newTradeSlot = data['slots'][tradeSlot]
                if newTradeSlot != None and newTradeSlot['name'] == itemInfo['name'] and newTradeSlot['q'] == quantity:
                    resolve(True)
            
            Tools.setTimeout(reject, Constants.TIMEOUT, f"listForSale timeout ({Constants.TIMEOUT}s)")
            self.socket.on('game_response', failCheck1)
            self.socket.on('disappearing_text', failCheck2)
            self.socket.on('player', successCheck)
            await self.socket.emit('equip', { 'num': itemPos, 'price': price, 'q': quantity, 'slot': tradeSlot })
            while not listed.done():
                await asyncio.sleep(Constants.WAIT)
            return listed.result()
        return await Tools.tryExcept(listFn)

    async def merchantCourage(self):
        async def courageFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [merchantCourage].")
            await self.socket.emit('skill', { 'name': 'mcourage' })
        return await Tools.tryExcept(courageFn)
    
    async def mine(self):
        async def mineFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [mine].")
            startedMining = False
            if self.c.get('mining') != None:
                startedMining = True
            mined = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, mined
                if not mined.done():
                    self.socket.off('game_response', failCheck1)
                    self.socket.off('ui', failCheck2)
                    self.socket.off('player', failCheck3)
                    self.socket.off('eval', caughtCheck)
                    mined.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, mined
                if not mined.done():
                    self.socket.off('game_response', failCheck1)
                    self.socket.off('ui', failCheck2)
                    self.socket.off('player', failCheck3)
                    self.socket.off('eval', caughtCheck)
                    mined.set_result(value)
            def caughtCheck(data):
                match = re.search('skill_timeout\s*[\'"]mining[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            def failCheck1(data):
                if isinstance(data, str):
                    if data == 'skill_cant_wtype':
                        reject("We don't have a pickaxe equipped.")
                elif isinstance(data, dict):
                    if data['response'] == 'cooldown' and data['place'] == 'mining' and data['skill'] == 'mining':
                        reject(f"Mining is on cooldown ({data['ms']}ms remaining).")
            def failCheck2(data):
                if data['type'] == 'mining_fail' and data['name'] == self.id:
                    reject("We failed to mine.")
                elif data['type'] == 'mining_none':
                    resolve(False)
            def failCheck3(data):
                nonlocal startedMining
                if not startedMining and data.c.get('mining') != None:
                    startedMining = True
                elif startedMining and data.c.get('mining') == None:
                    resolve(False)
            Tools.setTimeout(reject, 20, "mine timeout (20s)")
            self.socket.on('game_response', failCheck1)
            self.socket.on('ui', failCheck2)
            self.socket.on('player', failCheck3)
            self.socket.on('eval', caughtCheck)
            await self.socket.emit('skill', { 'name': 'mining' })
            while not mined.done():
                await asyncio.sleep(Constants.WAIT)
            return mined.result()
        return await Tools.tryExcept(mineFn)

    async def mluck(self, target):
        async def luckFn():
            nonlocal self, target
            if not self.ready:
                raise Exception("We aren't ready yet [mluck].")
            previousMs = 0
            if target != self.id:
                player = self.players.get(target)
                if player == None:
                    raise Exception(f"Could not find {target} to mluck.")
                if hasattr(player, 'npc'):
                    raise Exception(f"{target} is an NPC. You can't mluck NPCs.")
                if player.s.get('mluck', {}).get('s', False) and ((hasattr(player, 'owner') and player.owner != self.owner) or (player.s['mluck']['f'] != self.id)):
                    raise Exception(f"{target} has a strong mluck from {player.s['mluck']['f']}.")
                previousMs = player.s.get('mluck', {}).get('ms', 0)
            else:
                previousMs = self.s.get('mluck', {}).get('ms', 0)
            
            mlucked = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal self, mlucked
                if not mlucked.done():
                    self.socket.off('entities', mluckCheck)
                    self.socket.off('game_response', failCheck)
                    self.socket.off('player', selfMluckCheck)
                    self.socket.off('eval', cooldownCheck)
                    mlucked.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal self, mlucked
                if not mlucked.done():
                    self.socket.off('entities', mluckCheck)
                    self.socket.off('game_response', failCheck)
                    self.socket.off('player', selfMluckCheck)
                    self.socket.off('eval', cooldownCheck)
                    mlucked.set_result(value)
            def cooldownCheck(data):
                match = re.search('skill_timeout\s*[\'"]mluck[\'"]\s*,?\s*(\d+\.?\d+?)?\s*\)', data['code'])
                if match != None:
                    resolve(True)
            def mluckCheck(data):
                nonlocal previousMs
                for player in data['players']:
                    if player['id'] != target: continue
                    if player['s'].get('mluck', {}).get('f') != self.id: continue
                    if player['s'].get('mluck', {}).get('ms') < previousMs: continue
                    resolve(True)
            def selfMluckCheck(data):
                nonlocal previousMs
                if self.id == target and data.get('s', {}).get('mluck', {}).get('f') == self.id and data.get('s', {}).get('mluck', {}).get('ms') >= previousMs:
                    resolve(True)
            async def failCheck(data):
                if isinstance(data, str):
                    if data == 'skill_too_far':
                        await self.requestPlayerData()
                        reject(f"We are too far from {target} to mluck.")
                    elif data == 'no_level':
                        reject("We aren't a high enough level to use mluck.")
            Tools.setTimeout(reject, Constants.TIMEOUT, f"mluck timeout ({Constants.TIMEOUT}s).")
            self.socket.on('game_response', failCheck)
            self.socket.on('player', selfMluckCheck)
            self.socket.on('entities', mluckCheck)
            self.socket.on('eval', cooldownCheck)
            await self.socket.emit('skill', { 'id': target, 'name': 'mluck' })
            self.nextSkill['mluck'] = datetime.now() + self.G['skills']['mluck']['cooldown']
            while not mlucked.done():
                await asyncio.sleep(Constants.WAIT)
            return mlucked.result()
        return await Tools.tryExcept(luckFn)

    async def massProduction(self):
        async def mProdFn():
            nonlocal self
            if not self.ready:
                raise Exception("We aren't ready yet [massProduction].")
            massProductioned = asyncio.get_event_loop().create_future()
            def reject(reason = None):
                nonlocal massProductioned
                if not massProductioned.done():
                    self.socket.off('ui', productionedCheck)
                    massProductioned.set_exception(Exception(reason))
            def resolve(value = None):
                nonlocal massProductioned
                if not massProductioned.done():
                    self.socket.off('ui', productionedCheck)
                    massProductioned.set_result(value)
            def productionedCheck(data):
                nonlocal self
                if data['type'] == 'massproduction' and data['name'] == self.id:
                    resolve(True)
            Tools.setTimeout(reject, Constants.TIMEOUT, f"massProduction timeout ({Constants.TIMEOUT}s).")
            self.socket.on('ui', productionedCheck)
            await self.socket.emit('skill', { 'name': 'massproduction' })
            while not massProductioned.done():
                await asyncio.sleep(Constants.WAIT)
            return massProductioned.result()
        return await Tools.tryExcept(mProdFn)
    
    #TODO: massproductionpp