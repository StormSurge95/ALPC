from copy import deepcopy
from datetime import datetime
import logging
import math
import multiprocessing
import sys
from .Delaunator import Delaunator
import igraph
from .Constants import Constants
from .Tools import Tools

UNKNOWN = 1
UNWALKABLE = 2
WALKABLE = 3

class Pathfinder(object):
    G = None
    FIRST_MAP = 'main'
    TRANSPORT_COST = 50
    TOWN_COST = 450
    ENTER_COST = 1000

    grids = {}
    graph = igraph.Graph(directed = True)

    logger = None

    @staticmethod
    def doorDistance(a: dict, b: list) -> float:
        b_x = b[0]
        b_y = b[1]
        halfWidth = b[2] / 2
        height = b[3]

        if (a['x'] >= b_x):
            if a['y'] >= b_y:
                # Check inside door
                if a['x'] <= b_x + halfWidth and a['y'] <= b_y: return 0
                # Check top-right
                return math.hypot(a['x'] - (b_x + halfWidth), a['y'] - b_y)
            else:
                # Check inside door
                if a['x'] <= b_x + halfWidth and a['y'] >= b_y: return 0
                # Check bottom-right
                return math.hypot(a['x'] - (b_x + halfWidth), a['y'] - (b_y - height))
        else:
            if a['y'] >= b_y:
                # Check inside door
                if a['x'] >= b_x - halfWidth and a['y'] <= b_y: return 0
                # Check top-left
                return math.hypot(a['x'] - (b_x + halfWidth), a['y'] - b_y)
            else:
                # Check inside door
                if a['x'] >= b_x - halfWidth and a['y'] >= b_y: return 0
                # Check bottom-left
                return math.hypot(a['x'] - (b_x - halfWidth), a['y'] - (b_y - height))

    @staticmethod
    def addLinkToGraph(fr, to, data=None):
        return Pathfinder.graph.add_edge(fr, to, data=data)
    
    @staticmethod
    def addNodeToGraph(_map: str, _x: int, _y: int):
        try:
            return Pathfinder.graph.vs.find(name=f"{_map}:{_x},{_y}")
        except Exception:
            return Pathfinder.graph.add_vertex(f"{_map}:{_x},{_y}", map=_map, x=_x, y=_y)

    @staticmethod
    def canStand(location: dict) -> bool:
        if Pathfinder.G == None:
            raise Exception("Prepare pathfinding before querying canStand()!")
        
        y = math.trunc(location['y']) - Pathfinder.G['geometry'][location['map']]['min_y']
        x = math.trunc(location['x']) - Pathfinder.G['geometry'][location['map']]['min_x']
        width = Pathfinder.G['geometry'][location['map']]['max_x'] - Pathfinder.G['geometry'][location['map']]['min_x']

        try:
            grid = Pathfinder.getGrid(location['map'])
            if grid[y * width + x] == WALKABLE:
                return True
        except Exception:
            return False
        return False

    @staticmethod
    def canWalkPath(fr: dict, to: dict) -> bool:
        if Pathfinder.G == None:
            raise Exception("Prepare pathfinding before querying canWalkPath()!")
        frMap = fr['map'] if isinstance(fr, dict) else fr.map
        frX = fr['x'] if isinstance(fr, dict) else fr.x
        frY = fr['y'] if isinstance(fr, dict) else fr.y
        if frMap != to['map']:
            return False # We can't walk across maps
        
        grid = Pathfinder.getGrid(frMap)
        width = Pathfinder.G['geometry'][frMap]['max_x'] - Pathfinder.G['geometry'][frMap]['min_x']

        error = 0
        errorPrev = 0
        x = math.trunc(frX) - Pathfinder.G['geometry'][frMap]['min_x']
        y = math.trunc(frY) - Pathfinder.G['geometry'][frMap]['min_y']
        dx = math.trunc(to['x']) - math.trunc(frX)
        dy = math.trunc(to['y']) - math.trunc(frY)

        if grid[y * width + x] != WALKABLE:
            return False
        
        yStep = Tools.sign(dy)
        xStep = Tools.sign(dx)
        dy *= yStep
        dx *= xStep
        ddy = 2 * dy
        ddx = 2 * dx

        if ddx >= ddy:
            errorPrev = error = dx
            for i in range(0, dx):
                x += xStep
                error += ddy
                if error > ddx:
                    y += yStep
                    error -= ddx
                    if error + errorPrev < ddx and grid[(y - yStep) * width + x] != WALKABLE:
                        return False
                    elif error + errorPrev > ddx and grid[y * width + x - xStep] != WALKABLE:
                        return False
                    elif grid[(y - yStep) * width + x] != WALKABLE or grid[y * width + x - xStep] != WALKABLE:
                        return False
                if grid[y * width + x] != WALKABLE:
                    return False
                errorPrev = error
        else:
            errorPrev = error = dy
            for i in range(0, dy):
                y += yStep
                error += ddx
                if error > ddy:
                    x += xStep
                    error -= ddy
                    if error + errorPrev < ddy and grid[y * width + x - xStep] != WALKABLE:
                        return False
                    elif error + errorPrev > ddy and grid[(y - yStep) * width + x] != WALKABLE:
                        return False
                    elif grid[y * width + x - xStep] != WALKABLE or grid[(y - yStep) * width + x] != WALKABLE:
                            return False
                if grid[y * width + x] != WALKABLE:
                    return False
                errorPrev = error
        
        return True
    
    @staticmethod
    def computeLinkCost(fr, to, link, *, avoidTownWarps: bool = None, costs: dict[str, int] = {}) -> int:
        if ((link['data']['type'] == 'leave') or (link['data']['type'] == 'transport')):
            return 1000 if link['data']['map'] == 'bank' else costs.get('transport', Pathfinder.TRANSPORT_COST)
        elif link['data']['type'] == 'enter':
            return costs.get('enter', Pathfinder.ENTER_COST)
        elif link['data']['type'] == 'town':
            return sys.maxsize if avoidTownWarps else costs.get('town', Pathfinder.TOWN_COST)
        
        if fr['map'] == to['map']:
            return Tools.distance(fr, to)

    @staticmethod
    def computePathCost(path: list, *, avoidTownWarps: bool = False, costs: dict[str, int] = {}) -> int:
        cost = 0
        current = path[0]
        for i in range(1, len(path)):
            next = path[i]
            link = { 'data': { **next } }
            cost += Pathfinder.computeLinkCost(current, next, link, avoidTownWarps=avoidTownWarps, costs=costs)
            current = next
        return cost
    
    @staticmethod
    def getGrid(map: str, base = Constants.BASE):
        if Pathfinder.grids.get(map):
            return Pathfinder.grids[map]
        else:
            return Pathfinder.createGrid(map, base)

    @staticmethod
    def createGrid(map: str, base = Constants.BASE):
        if Pathfinder.G == None:
            raise Exception("Prepare pathfinding before querying getGrid()!")

        minX = Pathfinder.G['geometry'][map]['min_x']
        minY = Pathfinder.G['geometry'][map]['min_y']
        width = Pathfinder.G['geometry'][map]['max_x'] - minX
        height = Pathfinder.G['geometry'][map]['max_y'] - minY

        grid = [UNKNOWN] * (height * width)
        for yLine in Pathfinder.G['geometry'][map]['y_lines']:
            lowerY = max(0, yLine[0] - minY - base['vn'])
            upperY = min(yLine[0] - minY + base['v'] + 1, height)
            lowerX = max(0, yLine[1] - minX - base['h'])
            upperX = min(yLine[2] - minX + base['h'] + 1, width)
            for y in range(lowerY, upperY):
                for x in range(lowerX, upperX):
                    grid[y * width + x] = UNWALKABLE
        
        for xLine in Pathfinder.G['geometry'][map]['x_lines']:
            lowerX = max(0, xLine[0] - minX - base['h'])
            upperX = min(xLine[0] - minX + base['h'] + 1, width)
            lowerY = max(0, xLine[1] - minY - base['vn'])
            upperY = min(xLine[2] - minY + base['v'] + 1, height)
            for x in range(lowerX, upperX):
                for y in range(lowerY, upperY):
                    grid[y * width + x] = UNWALKABLE
        
        for spawn in Pathfinder.G['maps'][map]['spawns']:
            x = math.trunc(spawn[0]) - minX
            y = math.trunc(spawn[1]) - minY
            if grid[y * width + x] != WALKABLE:
                stack = [[y,x]]
                while len(stack) > 0:
                    ny, nx = stack.pop()
                    while nx >= 0 and grid[ny * width + nx] == UNKNOWN:
                        nx -= 1
                    nx += 1
                    spanAbove = 0
                    spanBelow = 0
                    while nx < width and grid[ny * width + nx] == UNKNOWN:
                        grid[ny * width + nx] = WALKABLE
                        if not spanAbove and ny > 0 and grid[(ny - 1) * width + nx] == UNKNOWN:
                            stack.append([ny - 1, nx])
                            spanAbove = 1
                        elif spanAbove and ny > 0 and grid[(ny - 1) * width + nx] != UNKNOWN:
                            spanAbove = 0
                        
                        if not spanBelow and ny < (height - 1) and grid[(ny + 1) * width + nx] == UNKNOWN:
                            stack.append([ny + 1, nx])
                            spanBelow = 1
                        elif spanBelow and ny < (height - 1) and grid[(ny + 1) * width + nx] != UNKNOWN:
                            spanBelow = 0
                        nx += 1
        Pathfinder.grids[map] = grid
        return grid

    @staticmethod
    def createVertexData(map: str, grid: list[int], vertexNames: list[str], vertexAttrs: dict[str, str | int]):
        minX = Pathfinder.G['geometry'][map]['min_x']
        minY = Pathfinder.G['geometry'][map]['min_y']
        width = Pathfinder.G['geometry'][map]['max_x'] - minX
        height = Pathfinder.G['geometry'][map]['max_y'] - minY

        points = set()         # list of points for delaunay
        
        # add nodes at corners
        for y in range(1, height - 1):
            for x in range(1, width):
                # for each walkable x/y position...
                if grid[y * width + x] != WALKABLE:
                    continue
                
                # get surrounding positions
                bL = grid[(y - 1) * width + x - 1]
                bC = grid[(y - 1) * width + x]
                bR = grid[(y - 1) * width + x + 1]
                mL = grid[y * width + x - 1]
                mR = grid[y * width + x + 1]
                uL = grid[(y + 1) * width + x - 1]
                uC = grid[(y + 1) * width + x]
                uR = grid[(y + 1) * width + x + 1]

                # check corner locations for walkability
                if (((WALKABLE not in [uL, mL, bL, bC, bR]))                # inside-1
                 or ((WALKABLE not in [uR, mR, bL, bC, bR]))                # inside-2
                 or ((WALKABLE not in [uL, uC, uR, mR, bR]))                # inside-3
                 or ((WALKABLE not in [uL, uC, uR, mL, bL]))                # inside-4
                 or ((bL == UNWALKABLE) and (UNWALKABLE not in [mL, bC]))   # outside-1
                 or ((bR == UNWALKABLE) and (UNWALKABLE not in [mR, bC]))   # outside-2
                 or ((uR == UNWALKABLE) and (UNWALKABLE not in [uC, mR]))   # outside-3
                 or ((uL == UNWALKABLE) and (UNWALKABLE not in [uC, mL]))): # outside-4
                    points.add((x + minX, y + minY))
        
        # add nodes at transporters (we'll look for close nodes to transporters later)
        transporters = [npc for npc in Pathfinder.G['maps'][map]['npcs'] if npc['id'] == 'transporter']
        if len(transporters) > 0:
            pos = transporters[0]['position']
            closest = Pathfinder.findClosestSpawn(map, pos[0], pos[1])
            points.add((closest['x'], closest['y']))

            # make more points around transporter
            for angle in Tools.arange(0, math.pi * 2, math.pi / 32):
                x = math.trunc(pos[0] + math.cos(angle) * (Constants.TRANSPORTER_REACH_DISTANCE - 10))
                y = math.trunc(pos[1] + math.sin(angle) * (Constants.TRANSPORTER_REACH_DISTANCE - 10))
                if Pathfinder.canStand({'map': map, 'x': x, 'y': y}):
                    points.add((x, y))
        
        # add nodes at doors (we'll look for close nodes to doors later)
        doors = [door for door in Pathfinder.G['maps'][map]['doors'] if len(door) <= 7 or door[7] != 'complicated']
        for door in doors:
            # From
            spawn = Pathfinder.G['maps'][map]['spawns'][door[6]]
            points.add((spawn[0], spawn[1]))

            # make more points around the door
            doorX = door[0]
            doorY = door[1]
            doorWidth = door[2]
            doorHeight = door[3]
            doorCorners = [
                { 'x': doorX - (doorWidth / 2), 'y': doorY - (doorHeight / 2) }, # Top left
                { 'x': doorX + (doorWidth / 2), 'y': doorY - (doorHeight / 2) }, # Top right
                { 'x': doorX - (doorWidth / 2), 'y': doorY + (doorHeight / 2) }, # Bottom right
                { 'x': doorX + (doorWidth / 2), 'y': doorY + (doorHeight / 2) }  # Bottom left
            ]
            for point in doorCorners:
                for angle in Tools.arange(0, math.pi * 2, math.pi / 32):
                    x = math.trunc(point['x'] + math.cos(angle) * (Constants.DOOR_REACH_DISTANCE - 10))
                    y = math.trunc(point['y'] + math.sin(angle) * (Constants.DOOR_REACH_DISTANCE - 10))
                    if Pathfinder.canStand({ 'map': map, 'x': x, 'y': y }):
                        points.add((x, y))
         
        # Add nodes at spawns
        for spawn in Pathfinder.G['maps'][map]['spawns']:
            points.add((spawn[0], spawn[1]))
        
        vertexNames += [f"{map}:{x},{y}" for (x, y) in points]
        vertexAttrs['map'] += [map] * len(points)
        vertexAttrs['x'] += [p[0] for p in points]
        vertexAttrs['y'] += [p[1] for p in points]

    @staticmethod
    def createLinkData(maps):
        links = []
        linkData = []
        linkAttr = {}

        for map in maps:
            walkableNodes = Pathfinder.graph.vs.select(map_eq=map)

            doors = [door for door in Pathfinder.G['maps'][map]['doors'] if len(door) <= 7 or door[7] != 'complicated']
            transporters = [npc for npc in Pathfinder.G['maps'][map]['npcs'] if npc['id'] == 'transporter']
            
            for fromNode in walkableNodes:
                # add destination nodes and links to maps that are reachable through the door(s)
                doors = [door for door in doors if Pathfinder.doorDistance(fromNode, door) < Constants.DOOR_REACH_DISTANCE]
                for door in doors:
                    # To:
                    spawn2 = Pathfinder.G['maps'][door[4]]['spawns'][door[5]]
                    toDoor = Pathfinder.addNodeToGraph(door[4], spawn2[0], spawn2[1])
                    links.append([fromNode, toDoor])
                    # instance door (requires 'enter' function)
                    if len(door) > 7 and door[7] == 'key':
                        linkData.append({ 'key': door[8], 'map': toDoor['map'], 'type': 'enter', 'x': toDoor['x'], 'y': toDoor['y'], 'spawn': None })
                    # map door (requires 'transport' function)
                    else:
                        linkData.append({ 'key': None, 'map': toDoor['map'], 'type': 'transport', 'x': toDoor['x'], 'y': toDoor['y'], 'spawn': door[5] })
                # add destination nodes and links to maps that are reachable through the transporter(s)
                if len(transporters) > 0:
                    pos = transporters[0]['position']
                    if Tools.distance(fromNode, { 'x': pos[0], 'y': pos[1] }) > Constants.TRANSPORTER_REACH_DISTANCE:
                        continue # transporter is too far away
                    for toMap in Pathfinder.G['npcs']['transporter']['places']:
                        if map == toMap:
                            continue # don't add links to ourself

                        spawnID = Pathfinder.G['npcs']['transporter']['places'][toMap]
                        spawn = Pathfinder.G['maps'][toMap]['spawns'][spawnID]
                        toNode = Pathfinder.addNodeToGraph(toMap, spawn[0], spawn[1])

                        links.append([fromNode, toNode])
                        linkData.append({ 'key': None, 'map': toMap, 'type': 'transport', 'x': toNode['x'], 'y': toNode['y'], 'spawn': spawnID})
            
            leaveLink = Pathfinder.addNodeToGraph('main', Pathfinder.G['maps']['main']['spawns'][0][0], Pathfinder.G['maps']['main']['spawns'][0][1])
            leaveLinkData = { 'map': leaveLink['map'], 'type': 'leave', 'x': leaveLink['x'], 'y': leaveLink['y'], 'key': None, 'spawn': None }
            townNode = Pathfinder.graph.vs.find(name=f"{map}:{Pathfinder.G['maps'][map]['spawns'][0][0]},{Pathfinder.G['maps'][map]['spawns'][0][1]}")
            townLinkData = { 'map': map, 'type': 'town', 'x': Pathfinder.G['maps'][map]['spawns'][0][0], 'y': Pathfinder.G['maps'][map]['spawns'][0][1], 'spawn': None, 'key': None }
            for node in walkableNodes:
                # create town links
                if node != townNode:
                    links.append([node, townNode])
                    linkData.append({ 'key': townLinkData['key'], 'map': townLinkData['map'], 'type': townLinkData['type'], 'x': townLinkData['x'], 'y': townLinkData['y'], 'spawn': townLinkData['spawn'] })
                
                # create leave links
                if map == 'cyberland' or map == 'jail':
                    links.append([node, leaveLink])
                    linkData.append({ 'key': leaveLinkData['key'], 'map': leaveLinkData['map'], 'type': leaveLinkData['type'], 'x': leaveLinkData['x'], 'y': leaveLinkData['y'], 'spawn': leaveLinkData['spawn'] })

            points = [(node['x'], node['y']) for node in walkableNodes]
            # check if we can walk to other nodes
            delaunay = Delaunator(list(points))
            
            for i in range(0, len(delaunay.halfedges)):
                halfedge = delaunay.halfedges[i]
                if halfedge < i:
                    continue

                name1 = f"{map}:{delaunay.coords[delaunay.triangles[i] * 2]},{delaunay.coords[delaunay.triangles[i] * 2 + 1]}"
                name2 = f"{map}:{delaunay.coords[delaunay.triangles[delaunay.halfedges[i]] * 2]},{delaunay.coords[delaunay.triangles[delaunay.halfedges[i]] * 2 + 1]}"
                node1 = Pathfinder.graph.vs.find(name_eq=name1)
                node2 = Pathfinder.graph.vs.find(name_eq=name2)
                if Pathfinder.canWalkPath({ 'map': map, 'x': delaunay.coords[delaunay.triangles[i] * 2], 'y': delaunay.coords[delaunay.triangles[i] * 2 + 1] }, { 'map': map, 'x': delaunay.coords[delaunay.triangles[delaunay.halfedges[i]] * 2], 'y': delaunay.coords[delaunay.triangles[delaunay.halfedges[i]] * 2 + 1] }):
                    links.append([node1, node2])
                    linkData.append({ 'key': None, 'map': map, 'type': 'move', 'x': delaunay.coords[delaunay.triangles[delaunay.halfedges[i]] * 2], 'y': delaunay.coords[delaunay.triangles[delaunay.halfedges[i]] * 2 + 1], 'spawn': None })
                    links.append([node2, node1])
                    linkData.append({ 'key': None, 'map': map, 'type': 'move', 'x': delaunay.coords[delaunay.triangles[i] * 2], 'y': delaunay.coords[delaunay.triangles[i] * 2 + 1], 'spawn': None })
        linkAttr['data'] = linkData
        return links, linkAttr
    
    @staticmethod
    def findClosestNode(map: str, x: int, y: int):
        closest = { 'distance': sys.maxsize, 'node': None }
        closestWalkable = { 'distance': sys.maxsize, 'node': None }
        _from = { 'map': map, 'x': x, 'y': y}
        for node in Pathfinder.graph.vs:
            if node['map'] == map:
                distance = Tools.distance(_from, node)

                if distance > closest['distance']:
                    continue

                walkable = Pathfinder.canWalkPath(_from, node)

                if distance < closest['distance']:
                    closest['distance'] = distance
                    closest['node'] = node
                if walkable and distance < closestWalkable['distance']:
                    closestWalkable['distance'] = distance
                    closestWalkable['node'] = node
                if distance < 1:
                    break
        
        if closestWalkable['node'] != None:
            return closestWalkable['node']
        else:
            return closest['node']
    
    @staticmethod
    def findClosestSpawn(map: str, x: int, y: int):
        closest = { 'distance': sys.maxsize, 'map': map, 'x': sys.maxsize, 'y': sys.maxsize }
        for spawn in Pathfinder.G['maps'][map]['spawns']:
            distance = Tools.distance({ 'x': x, 'y': y }, { 'x': spawn[0], 'y': spawn[1] })
            if distance < closest['distance']:
                closest['x'] = spawn[0]
                closest['y'] = spawn[1]
                closest['distance'] = distance
        
        return closest

    @staticmethod
    async def getPath(fr, to, *, avoidTownWarps: bool = False, getWithin: int = None, useBlink: bool = False, costs = {}):
        if not Pathfinder.G:
            raise Exception("Prepare pathfinding before querying getPath()!")
        frMap = fr['map'] if isinstance(fr, dict) else fr.map
        frX = fr['x'] if isinstance(fr, dict) else fr.x
        frY = fr['y'] if isinstance(fr, dict) else fr.y
        if (frMap == to['map']) and (Pathfinder.canWalkPath(fr, to)) and (Tools.distance(fr, to) < Pathfinder.TOWN_COST):
            return [{ 'map': frMap, 'type': 'move', 'x': frX, 'y': frY }, { 'map': to['map'], 'type': 'move', 'x': to['x'], 'y': to['y'] }]
        
        fromNode = Pathfinder.findClosestNode(frMap, frX, frY)
        toNode = Pathfinder.findClosestNode(to['map'], to['x'], to['y'])

        path = []

        rawPath = Pathfinder.graph.get_shortest_paths(fromNode, to=toNode, mode='out', output='vpath')[0]
        if len(rawPath) == 0:
            raise Exception("We did not find a path...")

        path.append({ 'map': fromNode['map'], 'type': 'move', 'x': fromNode['x'], 'y': fromNode['y'] })
        for i in range(0, (len(rawPath) - 1)):
            currentNode = Pathfinder.graph.vs[rawPath[i]]
            nextNode = Pathfinder.graph.vs[rawPath[i + 1]]

            lowestCostLinkData = None
            lowestCost = sys.maxsize
            for link in Pathfinder.graph.es.select(_source = currentNode.index, _target = nextNode.index):
                cost = Pathfinder.computeLinkCost(currentNode, nextNode, link=link, avoidTownWarps=avoidTownWarps, costs=costs)
                if (cost < lowestCost) or ((cost == lowestCost) and ((link['data']['type'] == 'move'))):
                    lowestCost = cost
                    lowestCostLinkData = link['data']
            
            if lowestCostLinkData != None:
                path.append(lowestCostLinkData)
                if lowestCostLinkData['type'] == 'town':
                    path.append({ 'map': lowestCostLinkData['map'], 'type': 'move', 'x': nextNode['x'], 'y': nextNode['y'] })
            else:
                path.append({ 'map': nextNode['map'], 'type': 'move', 'x': nextNode['x'], 'y': nextNode['y'] })
        path.append({ 'map': toNode['map'], 'type': 'move', 'x': toNode['x'], 'y': toNode['y'] })

        i = 0
        while i < len(path) - 1:
            current = path[i]
            next = path[i + 1]

            if current['type'] != next['type']:
                i+=1
                continue
            if current['map'] != next['map']:
                i+=1
                continue
            if current['x'] != next['x']:
                i+=1
                continue
            if current['y'] != next['y']:
                i+=1
                continue

            path.pop(i)

        return path
    
    @staticmethod
    def getSafeWalkTo(fr, to):
        frMap = fr['map'] if isinstance(fr, dict) else fr.map
        frX = fr['x'] if isinstance(fr, dict) else fr.x
        frY = fr['y'] if isinstance(fr, dict) else fr.y
        if frMap != to['map']:
            raise Exception("We can't walk across maps.")
        if not Pathfinder.G:
            raise Exception("Prepare pathfinding beofre querying getSafeWalkTo()!")

        grid = Pathfinder.getGrid(frMap)
        width = Pathfinder.G['geometry'][frMap]['max_x'] - Pathfinder.G['geometry'][frMap]['min_x']

        xStep = 0
        yStep = 0
        error = 0
        errorPrev = 0

        x = math.trunc(frX) - Pathfinder.G['geometry'][frMap]['min_x']
        y = math.trunc(frY) - Pathfinder.G['geometry'][frMap]['min_y']
        dx = math.trunc(to['x']) - math.trunc(frX)
        dy = math.trunc(to['y']) - math.trunc(frY)

        if grid[y * width + x] != WALKABLE:
            print(f"We shouldn't be able to be where we are in from ({frMap}:{frX},{frY}).")
            return Pathfinder.findClosestNode(frMap, frX, frY)
        
        if dy < 0:
            yStep = -1
            dy = -dy
        else:
            yStep = 1
        if dx < 0:
            xStep = -1
            dx = -dx
        else:
            xStep = 1
        ddy = 2 * dy
        ddx = 2 * dx

        if ddx >= ddy:
            errorPrev = error = dx
            for i in range(0, dx):
                x += xStep
                error += ddy
                if error > ddx:
                    y += yStep
                    error -= ddx
                    if error + errorPrev < ddx and grid[(y - yStep) * width + x] != WALKABLE:
                        return { 'map': frMap, 'x': x - xStep + Pathfinder.G['geometry'][frMap]['min_x'], 'y': y - yStep + Pathfinder.G['geometry'][frMap]['min_y'] }
                    elif error + errorPrev > ddx and grid[y * width + x - xStep] != WALKABLE:
                        return { 'map': frMap, 'x': x - xStep + Pathfinder.G['geometry'][frMap]['min_x'], 'y': y - yStep + Pathfinder.G['geometry'][frMap]['min_y'] }
                    else:
                        if grid[(y - yStep) * width + x] != WALKABLE:
                            return { 'map': frMap, 'x': x - xStep + Pathfinder.G['geometry'][frMap]['min_x'], 'y': y - yStep + Pathfinder.G['geometry'][frMap]['min_y'] }
                        if grid[y * width + x - xStep] != WALKABLE:
                            return { 'map': frMap, 'x': x - xStep + Pathfinder.G['geometry'][frMap]['min_x'], 'y': y - yStep + Pathfinder.G['geometry'][frMap]['min_y'] }
                if grid[y * width + x] != WALKABLE:
                    return { 'map': frMap, 'x': x - xStep + Pathfinder.G['geometry'][frMap]['min_x'], 'y': y + Pathfinder.G['geometry'][frMap]['min_y'] }
                errorPrev = error
        else:
            errorPrev = error = dy
            for i in range(0, dy):
                y += yStep
                error += ddx
                if error > ddy:
                    x += xStep
                    error -= ddy
                    if error + errorPrev < ddy and grid[y * width + x - xStep] != WALKABLE:
                        return { 'map': frMap, 'x': x - xStep + Pathfinder.G['geometry'][frMap]['min_x'], 'y': y - yStep + Pathfinder.G['geometry'][frMap]['min_y'] }
                    elif error + errorPrev > ddy and grid[(y - yStep) * width + x] != WALKABLE:
                        return { 'map': frMap, 'x': x - xStep + Pathfinder.G['geometry'][frMap]['min_x'], 'y': y - yStep + Pathfinder.G['geometry'][frMap]['min_y'] }
                    else:
                        if grid[y * width + x - xStep] != WALKABLE:
                            return { 'map': frMap, 'x': x - xStep + Pathfinder.G['geometry'][frMap]['min_x'], 'y': y - yStep + Pathfinder.G['geometry'][frMap]['min_y'] }
                        if grid[(y - yStep) * width + x] != WALKABLE:
                            return { 'map': frMap, 'x': x - xStep + Pathfinder.G['geometry'][frMap]['min_x'], 'y': y - yStep + Pathfinder.G['geometry'][frMap]['min_y'] }
                if grid[y * width + x] != WALKABLE:
                    return { 'map': frMap, 'x': x + Pathfinder.G['geometry'][frMap]['min_x'], 'y': y - yStep + Pathfinder.G['geometry'][frMap]['min_y'] }
                errorPrev = error
        
        return to

    @staticmethod
    def init(g):
        Pathfinder.G = g

    @staticmethod
    async def prepare(g, *, base = Constants.BASE, cheat = False, include_bank_b = False, include_bank_u = False, include_test = False):
        Pathfinder.G = g

        Pathfinder.logger = logging.getLogger('Pathfinder')
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(fmt='%(levelname)s - %(name)s - %(asctime)s - %(funcName)s: %(message)s', datefmt='%H:%M:%S'))
        Pathfinder.logger.addHandler(handler)

        start = datetime.utcnow().timestamp()
        start2 = datetime.utcnow().timestamp()
        NOTMAPS = ['d_b1', 'd2', 'batcave', 'resort', 'd_a2', 'dungeon0', 'cgallery', 'd_a1', 'ship0', 'd_g', 'abtesting', 'old_bank', 'old_main', 'original_main', 'duelland', 'test', 'bank_u', 'shellsisland', 'goobrawl', 'bank_b']

        # add every 'key' in G.maps if it's not in NOTMAPS
        maps = [key for key in Pathfinder.G['maps'] if key not in NOTMAPS]

        # add various maps if they are included via arguments
        if include_bank_b:
            maps.append('bank_b')
        if include_bank_u:
            maps.append('bank_u')
        if include_test:
            maps.append('test')
        
        maps.append('jail')

        Pathfinder.logger.debug(f"Map list creation: {datetime.utcnow().timestamp() - start2}")
        start2 = datetime.utcnow().timestamp()

        vertexNames = []
        vertexAttrs = { 'map': [], 'x': [], 'y': [] }
        
        with multiprocessing.Manager() as m:
            ml = m.list(vertexNames)
            md = m.dict(vertexAttrs)
            with multiprocessing.Pool(processes=4, initializer=Pathfinder.init, initargs=(g,)) as p:
                results = [p.apply_async(Pathfinder.createVertexData, args=(map, Pathfinder.createGrid(map, base), ml, md)) for map in maps]
                for r in results:
                    r.wait()
            vertexNames = deepcopy(ml)
            vertexAttrs = deepcopy(md)
        
        Pathfinder.graph.add_vertices(vertexNames, vertexAttrs)

        Pathfinder.logger.debug(f"Vertex creation: {datetime.utcnow().timestamp() - start2}")
        start2 = datetime.utcnow().timestamp()

        links, linkAttr = Pathfinder.createLinkData(maps)
        Pathfinder.graph.add_edges(links, linkAttr)

        Pathfinder.logger.debug(f"Edge creation: {datetime.utcnow().timestamp() - start2}")
        
        if cheat and 'winterland' in maps:
            fr = Pathfinder.findClosestNode('winterland', 721, 277)
            to = Pathfinder.findClosestNode('winterland', 737, 352)
            if fr != None and to != None and fr != to:
                Pathfinder.addLinkToGraph(fr, to)
            else:
                print('The winterland map has changed, cheat to walk to icegolem is not enabled.')

        Pathfinder.logger.debug(f"Pathfinding prepared! ({(datetime.utcnow().timestamp() - start)}s)")
        Pathfinder.logger.debug(f"  # Nodes: {len(Pathfinder.graph.vs)}")
        Pathfinder.logger.debug(f"  # Links: {len(Pathfinder.graph.es)}")