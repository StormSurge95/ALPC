import logging
import math
import sys
import asyncio
import igraph

class Tools:

    logger = logging.getLogger('Tools')
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(fmt='%(levelname)s - %(name)s - %(asctime)s - %(funcName)s: %(message)s', datefmt='%H:%M:%S'))
    logger.addHandler(handler)

    @staticmethod
    def damage_multiplier(a: float):
        return min(1.32, max(.05, 1 - (.001 * max(0, min(100, a)) + .001 * max(0, min(100, a - 100)) + .00095 * max(0, min(100, a - 200)) + .0009 * max(0, min(100, a - 300)) + .00082 * max(0, min(100, a - 400)) + .0007 * max(0, min(100, a - 500)) + .0006 * max(0, min(100, a - 600)) + .0005 * max(0, min(100, a - 700)) + .0004 * max(0, a - 800)) + .001 * max(0, min(50, 0 - a)) + .00075 * max(0, min(50, -50 - a)) + .0005 * max(0, min(50, -100 - a)) + .00025 * max(0, -150 - a)))

    @staticmethod
    def distance(a, b):
        try:
            mapA = a.map if hasattr(a, 'map') else a['map']
        except Exception:
            mapA = None
        xA = a.x if hasattr(a, 'x') else a['x']
        yA = a.y if hasattr(a, 'y') else a['y']
        try:
            mapB = b.map if hasattr(b, 'map') else b['map']
        except Exception:
            mapB = None
        xB = b.x if hasattr(b, 'x') else b['x']
        yB = b.y if hasattr(b, 'y') else b['y']
        
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
    
    @staticmethod
    def tryExcept(func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            Tools.logger.exception(e)
            return

    @staticmethod
    async def tryExceptA(func, *args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            Tools.logger.exception(e)
            return