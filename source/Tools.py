import math
import sys
import asyncio

class Tools:
    @staticmethod
    def damage_multiplier(a: float):
        return min(1.32, max(.05, 1 - (.001 * max(0, min(100, a)) + .001 * max(0, min(100, a - 100)) + .00095 * max(0, min(100, a - 200)) + .0009 * max(0, min(100, a - 300)) + .00082 * max(0, min(100, a - 400)) + .0007 * max(0, min(100, a - 500)) + .0006 * max(0, min(100, a - 600)) + .0005 * max(0, min(100, a - 700)) + .0004 * max(0, a - 800)) + .001 * max(0, min(50, 0 - a)) + .00075 * max(0, min(50, -50 - a)) + .0005 * max(0, min(50, -100 - a)) + .00025 * max(0, -150 - a)))

    @staticmethod
    def distance(a, b):
        try:
            mapA = a['map']
        except Exception:
            try:
                mapA = a.map
            except Exception:
                mapA = None
        try:
            xA = a['x']
        except Exception:
            xA = a.x
        try:
            yA = a['y']
        except Exception:
            yA = a.y
        try:
            mapB = b['map']
        except Exception:
            try:
                mapB = b.map
            except Exception:
                mapB = None
        try:
            xB = b['x']
        except Exception:
            xB = b.x
        try:
            yB = b['y']
        except Exception:
            yB = b.y
        
        if (mapA != None) and (mapB != None) and (mapA != mapB):
            return sys.maxsize
        return math.hypot(xA - xB, yA - yB)

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