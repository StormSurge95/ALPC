import math
import sys
import asyncio

class Tools:
    @staticmethod
    def damage_multiplier(a: float):
        return min(1.32, max(.05, 1 - (.001 * max(0, min(100, a)) + .001 * max(0, min(100, a - 100)) + .00095 * max(0, min(100, a - 200)) + .0009 * max(0, min(100, a - 300)) + .00082 * max(0, min(100, a - 400)) + .0007 * max(0, min(100, a - 500)) + .0006 * max(0, min(100, a - 600)) + .0005 * max(0, min(100, a - 700)) + .0004 * max(0, a - 800)) + .001 * max(0, min(50, 0 - a)) + .00075 * max(0, min(50, -50 - a)) + .0005 * max(0, min(50, -100 - a)) + .00025 * max(0, -150 - a)))

    @staticmethod
    def distance(a, b):
        if (a is None) or (b is None):
            return sys.maxsize
        if type(a) != dict and type(b) != dict:
            if (hasattr(a, 'map') and hasattr(b, 'map')) and (getattr(a, 'map') != getattr(b, 'map')):
                return sys.maxsize
            return math.hypot(getattr(a, 'x') - getattr(b, 'x'), getattr(a, 'y') - getattr(b, 'y'))
        elif type(a) != dict and type(b) == dict:
            if (hasattr(a, 'map') and b.get('map', False)) and (getattr(a, 'map') != b['map']):
                return sys.maxsize
            return math.hypot(getattr(a, 'x') - b['x'], getattr(a, 'y') - b['y'])
        elif type(a) == dict and type(b) != dict:
            if (a.get('map', False) and hasattr(b, 'map')) and (a['map'] != getattr(b, 'map')):
                return sys.maxsize
            return math.hypot(a['x'] - getattr(b, 'x'), a['y'] - getattr(b, 'y'))
        else:
            if (a.get('map', False) and b.get('map', False)) and a['map'] != b['map']:
                return sys.maxsize
            return math.hypot(a['x'] - b['x'], a['y'] - b['y'])

    @staticmethod
    def setTimeout(fn, delay, *args, **kwargs):
        async def schedule():
            await asyncio.sleep(delay)

            if asyncio.iscoroutinefunction(fn):
                await fn(*args, **kwargs)
            else:
                fn(*args, **kwargs)
        fut = asyncio.ensure_future(schedule())
        return fut

    @staticmethod
    def clearTimeout(fut):
        fut.cancel()

    @staticmethod
    def hasKey(dic: dict, key: str):
        return (key in dic.keys())