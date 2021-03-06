import logging
import math
import sys
import asyncio

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
        except:
            mapA = None
        try:
            mapB = b.map if hasattr(b, 'map') else b['map']
        except:
            mapB = None
        if (mapA != None) and (mapB != None) and (mapA != mapB):
            return sys.maxsize
        
        xA = a.x if hasattr(a, 'x') else a['x']
        yA = a.y if hasattr(a, 'y') else a['y']
        xB = b.x if hasattr(b, 'x') else b['x']
        yB = b.y if hasattr(b, 'y') else b['y']
        return math.hypot(xA - xB, yA - yB)

    @staticmethod
    def setTimeout(fn, delay: float, *args, **kwargs):
        async def timeout():
            await asyncio.sleep(delay)

            if asyncio.iscoroutinefunction(fn):
                await fn(*args, **kwargs)
            else:
                fn(*args, **kwargs)
        fut = asyncio.ensure_future(timeout())
        return fut

    @staticmethod
    def setInterval(fn, delay, *args, **kwargs):
        async def interval():
            while True:
                await asyncio.sleep(delay)
                if asyncio.iscoroutinefunction(fn):
                    await fn(*args, **kwargs)
                else:
                    fn(*args, **kwargs)
        inter = asyncio.ensure_future(interval())
        return inter

    @staticmethod
    def clearTimeout(fut: asyncio.Task):
        fut.cancel()

    @staticmethod
    def hasKey(dic: dict, key: str):
        return (key in dic.keys())
    
    @staticmethod
    async def tryExcept(func, *args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            Tools.logger.exception(e)
            return False

    @staticmethod
    def arange(start = 0, stop = 2 * math.pi, step = math.pi):
        while start < stop:
            yield float(start)
            start += float(step)
    
    @staticmethod
    def sign(num: int | float) -> int:
        try:
            return int(num / abs(num))
        except:
            return 0