module Pathfinder

    const UNKNOWN = 1
    const UNWALKABLE = 2
    const WALKABLE = 3

    using Pkg

    using PyCall

    pushfirst!(PyVector(pyimport("sys")."path"), "./source/ALPC/")
    Constants = pyimport("Constants").Constants
    Tools = pyimport("Tools").Tools
    include("./graphing/Delaunator.jl")
    include("./graphing/Graphs.jl")

    try
        using MetaGraphs
    catch
        Pkg.add("MetaGraphs")
        using MetaGraphs
    end

    export doorDistance, prepare

    G = missing
    const FIRST_MAP = "main"
    const TRANSPORT_COST = 50
    const TOWN_COST = 450
    const ENTER_COST = 1000

    grids = Dict{String, Vector{Int}}()
    graph = Graphs.createGraph()

    function getGrid(map::String)
        global grids
        return grids[map]
    end

    function doorDistance(a::Any, b::Vector{Any})
        b_x = b[1]
        b_y = b[2]
        halfWidth = b[3] / 2
        height = b[4]

        local a_x, a_y
        if typeof(a) === Graphs.GraphNode
            a_x = a.x
            a_y = a.y
        else
            a_x = a["x"]
            a_y = a["y"]
        end

        if a.x >= b_x
            if a.y >= b_y - height / 2
                if a.x <= b_x + halfWidth && a.y <= b_y
                    return 0
                end

                return ((a.x - (b_x + halfWidth)) * (a.x - (b_x + halfWidth))) + ((a.y - b_y) * (a.y - b_y))
            else
                if a.x <= b_x + halfWidth && a.y >= b_y
                    return 0
                end

                return ((a.x - (b_x + halfWidth)) * (a.x - (b_x + halfWidth))) + ((a.y - (b_y - height)) * (a.y - (b_y - height)))
            end
        else
            if a.y >= b_y - height / 2
                if a.x >= b_x - halfWidth && a.y <= b_y
                    return 0
                end

                return ((a.x - (b_x - halfWidth)) * (a.x - (b_x - halfWidth))) + ((a.y - b_y) * (a.y - b_y))
            else
                if a.x >= b_x - halfWidth && a.y >= b_y
                    return 0
                end

                return ((a.x - (b_x - halfWidth)) * (a.x - (b_x - halfWidth))) + ((a.y - (b_y - height)) * (a.y - (b_y - height)))
            end
        end
    end

    function addNodeToGraph(map::String, x::Union{Int, Float32, Float64}, y::Union{Int, Float32, Float64})
        global graph
        x = trunc(Int, x)
        y = trunc(Int, y)
        n::Graphs.GraphNode = Graphs.addNode!(graph, map, x, y)
        return n
    end

    function addLinkToGraph(from::Graphs.GraphNode, to::Graphs.GraphNode, data::Dict{String, Any})
        global graph
        return Graphs.addLink!(graph, from.name, to.name, data)
    end

    function canStand(location::Union{Dict{String, Any}, Graphs.GraphNode, Graphs.GraphLink})
        global G
        if G === missing
            throw(MissingException("Prepare pathfinding before querying canStand()!"))
        end

        y = trunc(Int, location["y"]) - G["geometry"][location["map"]]["min_y"]
        x = trunc(Int, location["x"]) - G["geometry"][location["map"]]["min_x"]
        width = G["geometry"][location["map"]]["max_x"] - G["geometry"][location["map"]]["min_x"]

        try
            grid = getGrid(location["map"])
            if grid[y * width + x] == WALKABLE
                return true
            else
                return false
            end
        catch
            return false
        end
    end

    function canWalkPath(from::Union{Dict{String, Any}, Graphs.GraphNode, Graphs.GraphLink}, to::Union{Dict{String, Any}, Graphs.GraphNode, Graphs.GraphLink})
        global G
        if G === missing
            throw(MissingException("Prepare pathfinding before querying canWalkPath()!"))
        end

        local frMap, toMap, frX, toX, frY, toY
        if typeof(from) === Graphs.GraphNode || typeof(from) === Graphs.GraphLink
            frMap = from.map
            frX = from.x
            frY = from.y
        else
            frMap = from["map"]
            frX = from["x"]
            frY = from["y"]
        end
        if typeof(to) === Graphs.GraphNode || typeof(to) === Graphs.GraphLink
            toMap = to.map
            toX = to.x
            toY = to.y
        else
            toMap = to["map"]
            toX = to["x"]
            toY = to["y"]
        end

        if frMap !== toMap
            return false
        end

        grid = getGrid(frMap)
        width = G["geometry"][frMap]["max_x"] - G["geometry"][frMap]["min_x"]

        local xStep
        local yStep
        local error
        local errorPrev
        x = trunc(Int, frX) - G["geometry"][frMap]["min_x"]
        y = trunc(Int, frY) - G["geometry"][frMap]["min_y"]
        dx = trunc(Int, toX) - trunc(Int, frX)
        dy = trunc(Int, toY) - trunc(Int, frY)

        if grid[y * width + x] !== WALKABLE
            return false
        end

        if dy < 0
            yStep = -1
            dy = -dy
        else
            yStep = 1
        end

        if dx < 0
            xStep = -1
            dx = -dx
        else
            xStep = 1
        end

        ddy = 2 * dy
        ddx = 2 * dx

        if ddx >= ddy
            errorPrev = error = dx
            for i in 0:dx
                x += xStep
                error += ddy
                if error > ddx
                    y += yStep
                    error -= ddx
                    if error + errorPrev < ddx
                        if grid[(y - yStep) * width + x] !== WALKABLE
                            return false
                        end
                    elseif error + errorPrev > ddx
                        if grid[y * width + x - xStep] !== WALKABLE
                            return false
                        end
                    else
                        if grid[(y - yStep) * width + x] !== WALKABLE
                            return false
                        end
                        if grid[y * width + x - xStep] !== WALKABLE
                            return false
                        end
                    end
                end
                if grid[y * width + x] !== WALKABLE
                    return false
                end
                errorPrev = error
            end
        else
            errorPrev = error = dy
            for i in 0:dy
                y += yStep
                error += ddx
                if error > ddy
                    x += xStep
                    error -= ddy
                    if error + errorPrev < ddy
                        if grid[y * width + x - xStep] !== WALKABLE
                            return false
                        end
                    elseif error + errorPrev > ddy
                        if grid[(y - yStep) * width + x] !== WALKABLE
                            return false
                        end
                    else
                        if grid[y * width + x - xStep] !== WALKABLE
                            return false
                        end
                        if grid[(y - yStep) * width + x] !== WALKABLE
                            return false
                        end
                    end
                end
                if grid[y * width + x] !== WALKABLE
                    return false
                end
                errorPrev = error
            end
        end
        
        return true
    end

    function computeLinkCost(from::Union{Graphs.GraphNode, Graphs.GraphLink}, to::Union{Graphs.GraphNode, Graphs.GraphLink},
                             link::Union{Graphs.GraphLink, Nothing} = nothing; costs::Dict = Dict(), avoidTownWarps::Bool = false)
        if link !== nothing
            if link.types.leave || link.types.transport
                # We are using the transporter
                if link.map == "bank"
                    return 1000 # The bank only lets one character in at a time, add a higher cost for it so we don't try to use it as a shortcut
                end
                return haskey(costs, "transport") ? costs["transport"] : TRANSPORT_COST
            elseif link.types.enter
                return haskey(costs, "enter") ? costs["enter"] : ENTER_COST
            elseif link.types.town
                if avoidTownWarps
                    return 999999
                else
                    return haskey(costs, "town") ? costs["town"] : TOWN_COST
                end
            end
        end

        if from.map == to.map
            return hypot(from.x - to.x, from.y - to.y)
        end

        return 999999
    end

    function computePathCost(path::Vector{Graphs.GraphLink}; costs::Dict = Dict(), avoidTownWarps::Bool = false)
        local cost = 0
        local current::Graph.GraphLink = path[1]
        for i in 2:length(path)
            local next = path[i]
            cost += computeLinkCost(current, next, next, costs=costs, avoidTownWarps=avoidTownWarps)
            current = next
        end
        return cost
    end

    function findClosestNode(map::String, x::Union{Int, Float32, Float64}, y::Union{Int, Float32, Float64})
        local closest = Dict("distance"=>typemax(Int), "node"=>missing)
        local closestWalkable = Dict("distance"=>typemax(Int), "node"=>missing)
        local from = Dict("map"=>map, "x"=>x, "y"=>y)
        Graphs.forEachNode(graph,
            function (node)
                if node.map !== map
                    return
                end
                distance = ((from.x - node.x) * (from.x - node.x)) + ((from.y - node.y) * (from.y - node.y))

                if distance > closest["distance"]
                    return
                end

                walkable = canWalkPath(from, node)
                if distance < closest["distance"]
                    closest["distance"] = distance
                    closest["node"] = node
                end
                if walkable && distance < closestWalkable["distance"]
                    closestWalkable["distance"] = distance
                    closestWalkable["node"] = node
                end
                if distance < 1
                    return true
                end
            end
        )

        return closestWalkableNode["node"] !== missing ? closestWalkable["node"] : closest["node"]
    end

    function findClosestSpawn(map::String, x::Union{Int, Float32, Float64}, y::Union{Int, Float32, Float64})
        closest::Dict{String, Any} = Dict(
            "distance"=>typemax(Int),
            "map"=>map,
            "x"=>typemax(Int),
            "y"=>typemax(Int)
        )

        # Look through all the spawns, and find the closest one
        spawns = G["maps"][map]["spawns"]
        if typeof(spawns) <: Matrix
            spawns = [c[:] for c in eachrow(spawns)]
        end
        for spawn in spawns
            distance = ((x - spawn[1]) * (x - spawn[1])) + ((y - spawn[2]) * (y - spawn[2]))
            if distance < closest["distance"]
                closest["x"] = spawn[1]
                closest["y"] = spawn[2]
                closest["distance"] = distance
            end
        end

        return closest
    end

    function updateGraph(map::String, grid::Vector{Int})
        global G
        local width = G["geometry"][map]["max_x"] - G["geometry"][map]["min_x"]
        local height = G["geometry"][map]["max_y"] - G["geometry"][map]["min_y"]

        local walkableNodes::Vector{Graphs.GraphNode} = []
        local points::Vector{Vector{Int}} = []

        local gDoors = G["maps"][map]["doors"]
        if typeof(gDoors) <: Matrix
            gDoors = [c[:] for c in eachrow(gDoors)]
        end
        local gSpawns = G["maps"][map]["spawns"]
        if typeof(gSpawns) <: Matrix
            gSpawns = [c[:] for c in eachrow(gSpawns)]
        end

        for y in 1:(height - 1)
            for x in 1:width
                mc = grid[y * width + x]
                if mc != WALKABLE
                    continue
                end

                bl = grid[(y - 1) * width + x - 1]
                bc = grid[(y - 1) * width + x]
                br = grid[(y - 1) * width + x + 1]
                ml = grid[y * width + x - 1]
                mr = grid[y * width + x + 1]
                ul = grid[(y + 1) * width + x - 1]
                uc = grid[(y + 1) * width + x]
                ur = grid[(y + 1) * width + x + 1]

                mapX = x + G["geometry"][map]["min_x"]
                mapY = y + G["geometry"][map]["min_y"]

                if ((bl === UNWALKABLE
                    && bc === UNWALKABLE
                    && br === UNWALKABLE
                    && ml === UNWALKABLE
                    && ul === UNWALKABLE)
                    || (bl === UNWALKABLE
                    && bc === UNWALKABLE
                    && br === UNWALKABLE
                    && mr === UNWALKABLE
                    && ur === UNWALKABLE)
                    || (br === UNWALKABLE
                    && mr === UNWALKABLE
                    && ul === UNWALKABLE
                    && uc === UNWALKABLE
                    && ur === UNWALKABLE)
                    || (bl === UNWALKABLE
                    && ml === UNWALKABLE
                    && ul === UNWALKABLE
                    && uc === UNWALKABLE
                    && ur === UNWALKABLE)
                    || (bl === UNWALKABLE
                    && bc === WALKABLE
                    && ml === WALKABLE)
                    || (bc === WALKABLE
                    && br === UNWALKABLE
                    && mr === WALKABLE)
                    || (mr === WALKABLE
                    && uc === WALKABLE
                    && ur === UNWALKABLE)
                    || (ml === WALKABLE
                    && ul === UNWALKABLE
                    && uc === WALKABLE))
                    push!(walkableNodes, addNodeToGraph(map, mapX, mapY))
                    push!(points, [mapX, mapY])
                end
            end
        end

        transporters = []
        for npc in G["maps"][map]["npcs"]
            if npc["id"] !== "transporter"
                continue
            end
            closest = findClosestSpawn(map, npc["position"][1], npc["position"][2])
            cX = trunc(Int64, closest["x"])
            cY = trunc(Int64, closest["y"])
            fromNode = addNodeToGraph(map, cX, cY)
            push!(points, [cX, cY])
            push!(walkableNodes, fromNode)
            push!(transporters, npc)

            for angle in range(0, pi * 2, step = pi / 32)
                x = trunc(Int, npc["position"][1] + cos(angle) * (Constants.TRANSPORTER_REACH_DISTANCE - 10))
                y = trunc(Int, npc["position"][2] + sin(angle) * (Constants.TRANSPORTER_REACH_DISTANCE - 10))
                if canStand(Dict("map"=>map, "x"=>x, "y"=>y))
                    push!(walkableNodes, addNodeToGraph(map, x, y))
                    push!(points, [x, y])
                end
            end
        end

        doors = []
        for door in gDoors
            if length(door) > 7 && door[8] === "complicated"
                continue
            end
            
            spawn = gSpawns[door[7] + 1]
            sX = trunc(Int, spawn[1])
            sY = trunc(Int, spawn[2])
            push!(walkableNodes, addNodeToGraph(map, sX, sY))
            push!(points, [sX, sY])
            push!(doors, door)

            doorX = door[1]
            doorY = door[2]
            doorWidth = door[3]
            doorHeight = door[4]
            doorCorners = [
                Dict("x"=>(doorX - doorWidth / 2), "y"=>(doorY - doorHeight / 2)),
                Dict("x"=>(doorX + doorWidth / 2), "y"=>(doorY - doorHeight / 2)),
                Dict("x"=>(doorX - doorWidth / 2), "y"=>(doorY + doorHeight / 2)),
                Dict("x"=>(doorX + doorWidth / 2), "y"=>(doorY + doorHeight / 2))
            ]
            for point in doorCorners
                for angle in range(0.0, pi * 2, step=pi / 32)
                    x = trunc(Int, point["x"] + cos(angle) * (Constants.DOOR_REACH_DISTANCE - 10))
                    y = trunc(Int, point["y"] + sin(angle) * (Constants.DOOR_REACH_DISTANCE - 10))
                    if canStand(Dict("map"=>map, "x"=>x, "y"=>y))
                        push!(points, [x, y])
                        push!(walkableNodes, addNodeToGraph(map, x, y))
                    end
                end
            end
        end

        townNode = addNodeToGraph(map, gSpawns[1][1], gSpawns[1][2])
        push!(walkableNodes, townNode)
        push!(points, [townNode.x, townNode.y])
        townLinkData = Dict("key"=>nothing, "map"=>map, "types"=>Graphs.Types(false, true, false, false, false), "x"=>townNode.x, "y"=>townNode.y, "spawn"=>nothing)
        for i in 2:length(gSpawns)
            spawn = gSpawns[i]
            push!(walkableNodes, addNodeToGraph(map, spawn[1], spawn[2]))
            sX::Int64 = trunc(Int64, spawn[1])
            sY::Int64 = trunc(Int64, spawn[2])
            push!(points, [sX, sY])
        end

        for fromNode in walkableNodes
            for door in doors
                if doorDistance(fromNode, door) >= Constants.DOOR_REACH_DISTANCE_2
                    continue
                end

                spawns2 = G["maps"][door[5]]["spawns"]
                if typeof(spawns2) <: Matrix
                    spawns2 = [c[:] for c in eachrow(spawns2)]
                end
                spawn2 = spawns2[door[6] + 1]
                toDoor = addNodeToGraph(door[5], spawn2[1], spawn2[2])
                if length(door) > 7 && door[8] == "key"
                    addLinkToGraph(fromNode, toDoor, Dict("key"=>door[9], "map"=>toDoor.map, "types"=>Graphs.LinkTypes(false, false, false, true, false), "x"=>toDoor.x, "y"=>toDoor.y, "spawn"=>nothing))
                else
                    addLinkToGraph(fromNode, toDoor, Dict("key"=>nothing, "map"=>toDoor.map, "types"=>Graphs.LinkTypes(false, false, true, false, false), "x"=>toDoor.x, "y"=>toDoor.y, "spawn"=>door[6]))
                end
            end

            for npc in transporters
                if (((fromNode.x - npc["position"][1]) * (fromNode.x - npc["position"][1])) + ((fromNode.y - npc["position"][2]) * (fromNode.y - npc["position"][2])) > Constants.TRANSPORTER_REACH_DISTANCE_2)
                    continue
                end
                for toMap in keys(G["npcs"]["transporter"]["places"])
                    if map == toMap
                        continue
                    end

                    spawnID = G["npcs"]["transporter"]["places"][toMap] + 1
                    tSpawns = G["maps"][toMap]["spawns"]
                    if typeof(tSpawns) <: Matrix
                        tSpawns = [c[:] for c in eachrow(tSpawns)]
                    end
                    spawn = tSpawns[spawnID]
                    toNode = addNodeToGraph(toMap, spawn[1], spawn[2])
                    t = Graphs.Types(false, false, true, false, false)
                    addLinkToGraph(fromNode, toNode, Dict("key"=>nothing, "map"=>toMap, "types"=>t, "x"=>toNode.x, "y"=>toNode.y, "spawn"=>spawnID))
                end
            end
        end

        leaveNode = addNodeToGraph("main", G["maps"]["main"]["spawns"][1][1], G["maps"]["main"]["spawns"][1][2])
        leaveLinkData = Dict("key"=>nothing, "map"=>leaveNode.map, "types"=>Graphs.Types(false, false, false, false, true), "x"=>leaveNode.x, "y"=>leaveNode.y, "spawn"=>nothing)
        for node in walkableNodes
            if node.name !== townNode.name
                addLinkToGraph(node, townNode, townLinkData)
            end

            if map == "cyberland" || map == "jail"
                addLinkToGraph(node, leaveNode, leaveLinkData)
            end
        end

        delaunay = Delaunator.Delaunay(points)

        for i in 1:length(delaunay.halfedges)
            halfedge = delaunay.halfedges[i]
            if halfedge < i
                continue
            end
            ti = delaunay.triangles[i] + 1
            tj = delaunay.triangles[halfedge] + 1

            x1 = delaunay.coords[ti * 2 - 1]
            y1 = delaunay.coords[ti * 2]
            x2 = delaunay.coords[tj * 2 - 1]
            y2 = delaunay.coords[tj * 2]

            walkLinkDataFr = Dict("key"=>nothing, "map"=>map, "types"=>Graphs.Types(true, false, false, false, false),
                                 "x"=>x1, "y"=>y1, "spawn"=>nothing)
            walkLinkDataTo = Dict("key"=>nothing, "map"=>map, "types"=>Graphs.Types(true, false, false, false, false),
                                 "x"=>x2, "y"=>y2, "spawn"=>nothing)

            if canWalkPath(Dict("map"=>map, "x"=>x1, "y"=>y1), Dict("map"=>map, "x"=>x2, "y"=>y2))
                Graphs.addLink!(graph, "$map:$x1,$y1", "$map:$x2,$y2", walkLinkDataTo)
                Graphs.addLink!(graph, "$map:$x2,$y2", "$map:$x1,$y1", walkLinkDataFr)
            end
        end
    end

    function createGrid(map::String, base::Dict = Constants.BASE)
        global G
        global grids
        if G === missing
            throw(MissingException("Prepare pathfinding before querying getGrid()!"))
        end

        if haskey(grids, map)
            return 
        end

        minX::Int64 = G["geometry"][map]["min_x"]
        minY::Int64 = G["geometry"][map]["min_y"]
        width::Int64 = G["geometry"][map]["max_x"] - minX
        height::Int64 = G["geometry"][map]["max_y"] - minY

        grid::Vector{Int} = Vector{Int}(undef, (width * height))
        fill!(grid, UNKNOWN)

        yLines = G["geometry"][map]["y_lines"]
        if typeof(yLines) <: Matrix
            yLines = [c[:] for c in eachrow(yLines)]
        end
        for yLine in yLines
            lowerY::Int64 = max(1, (yLine[1] - minY - base["vn"]))
            upperY::Int64 = min((yLine[1] - minY + base["v"] + 1), height - 1)
            lowerX::Int64 = max(1, (yLine[2] - minX - base["h"]))
            upperX::Int64 = min((yLine[3] - minX + base["h"] + 1), width)
            for y::Int64 in lowerY:upperY
                for x::Int64 in lowerX:upperX
                    grid[y * width + x]::Int64 = UNWALKABLE
                end
            end
        end

        xLines = G["geometry"][map]["x_lines"]
        if typeof(xLines) <: Matrix
            xLines = [c[:] for c in eachrow(xLines)]
        end
        for xLine in xLines
            lowerX::Int64 = max(1, (xLine[1] - minX - base["h"]))
            upperX::Int64 = min((xLine[1] - minX + base["h"] + 1), width)
            lowerY::Int64 = max(1, (xLine[2] - minY - base["vn"]))
            upperY::Int64 = min((xLine[3] - minY + base["v"] + 1), height - 1)
            for x in lowerX:upperX
                for y in lowerY:upperY
                    grid[y * width + x] = UNWALKABLE
                end
            end
        end

        spawns = G["maps"][map]["spawns"]
        if (typeof(spawns) <: Matrix)
            spawns = [c[:] for c in eachrow(spawns)]
        end
        for spawn in spawns
            x::Int = trunc(Int, spawn[1]) - minX
            y::Int = trunc(Int, spawn[2]) - minY
            if grid[y * width + x] != WALKABLE
                stack = [(y,x)]
                while length(stack) > 0
                    (nY, nX) = pop!(stack)
                    while nX >= 1 && grid[nY * width + nX] == UNKNOWN
                        nX -= 1
                    end
                    nX += 1
                    spanAbove = 0
                    spanBelow = 0
                    while nX < width && grid[nY * width + nX] == UNKNOWN
                        grid[nY * width + nX] = WALKABLE
                        if nY > 1 && grid[(nY - 1) * width + nX] == UNKNOWN
                            if spanAbove == 0
                                push!(stack, (nY - 1, nX))
                                spanAbove = 1
                            else
                                spanAbove = 0
                            end
                        end

                        if nY < height - 1 && grid[(nY + 1) * width + nX] == UNKNOWN
                            if spanBelow == 0
                                push!(stack, (nY + 1, nX))
                                spanBelow = 1
                            else
                                spanBelow = 0
                            end
                        end
                        
                        x += 1
                    end
                end
            end
        end
        grids[map] = grid
        updateGraph(map, grid)
        return grid
    end

    function prepare(g::Dict; cheat::Bool = false, include_bank_b::Bool = false,
                     include_bank_u::Bool = false, include_test::Bool = false)
        
        global G = g
        global graph
        
        NOTMAPS = [ "d_b1", "d2", "batcave", "resort", "d_a2", "dungeon0", "cgallery",
                    "d_a1", "ship0", "d_g", "abtesting", "old_bank", "old_main",
                    "original_main", "duelland", "test", "bank_u", "shellsisland",
                    "goobrawl", "bank_b" ]
        maps = [key for key in keys(G["maps"]) if !(key in NOTMAPS)]

        if include_bank_b
            append!(maps, ["bank_b"])
        end
        if include_bank_u
            append!(maps, ["bank_u"])
        end
        if include_test
            append!(maps, ["test"])
        end

        for map in maps
            createGrid(map)
        end

        println("Pathfinding prepared!")
        println("  # Nodes: ", length(graph.nodes))
        println("  # Links: ", length(graph.links))
    end
end