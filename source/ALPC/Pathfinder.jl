module Pathfinder

    const UNKNOWN = 1
    const UNWALKABLE = 2
    const WALKABLE = 3

    using Pkg

    using PyCall

    pushfirst!(PyVector(pyimport("sys")."path"), "./source/ALPC/")
    Constants = pyimport("Constants").Constants
    Tools = pyimport("Tools").Tools
    include("./Delaunator.jl")

    try
        using MetaGraphs
    catch
        Pkg.add("MetaGraphs")
        using MetaGraphs
    end

    try
        using JSON
    catch
        Pkg.add("JSON")
        using JSON
    end

    export doorDistance, prepare

    global G = nothing
    const FIRST_MAP = "main"
    const TRANSPORT_COST = 50
    const TOWN_COST = 450
    const ENTER_COST = 1000

    grids = Dict()
    graph = MetaDiGraph()

    function doorDistance(a::Dict, b::Vector)
        b_x = b[1]
        b_y = b[2]
        halfWidth = b[3] / 2
        height = b[4]

        if (a[:x] >= b_x)
            if (a[:y] >= b_y)
                if (a[:x] <= b_x + halfWidth && a[:y] <= b_y)
                    return 0
                else
                    return hypot(a[:x] - (b_x + halfWidth), a[:y] - b_y)
                end
            else
                if (a[:x] <= b_x + halfWidth && a[:y] >= b_y)
                    return 0
                else
                    return hypot(a[:x] - (b_x + halfWidth), a[:y] - (b_y - height))
                end
            end
        else
            if (a[:y] >= b_y)
                if (a[:x] >= b_x - halfWidth && a[:y] <= b_y)
                    return 0
                else
                    return hypot(a[:x] - (b_x + halfWidth), a[:y] - b_y)
                end
            else
                if (a[:x] >= b_x - halfWidth && a[:y] >= b_y)
                    return 0
                else
                    return hypot(a[:x] - (b_x - halfWidth), a[:y] - (b_y - height))
                end
            end
        end
    end

    function addNodeToGraph(map::String, x::Union{Int, Float16, Float32, Float64}, y::Union{Int, Float16, Float32, Float64})
        name = "$map:$x,$y"
        try
            return graph[name, :name]
        catch
            MetaGraphs.add_vertex!(graph, Dict(:map=>map, :x=>x, :y=>y))
            v = MetaGraphs.nv(graph)
            MetaGraphs.set_indexing_prop!(graph, v, :name, name)
            return v
        end
    end

    function addLinkToGraph(fr::Int, to::Int, data::Dict)
        if !MetaGraphs.set_prop!(graph, fr, to, :data, data)
            MetaGraphs.add_edge!(graph, fr, to, Dict(:data=>data))
            arr = collect(MetaGraphs.edges(graph))
            ind = MetaGraphs.ne(graph)
            return arr[ind]
        else
            edge = MetaGraphs.filter_edges(graph, (graph, e) -> (MetaGraphs.src(e) == fr && MetaGraphs.dst(e) == to))
            return only(edge)
        end
    end

    function canStand(location::Dict)
        if G === nothing
            throw(ErrorException("Prepare pathfinding before querying canStand()!"))
        end

        y = location["y"] - G["geometry"][location["map"]]["min_y"]
        x = location["x"] - G["geometry"][location["map"]]["min_x"]
        width = G["geometry"][location["map"]]["max_x"] - G["geometry"][location["map"]]["min_x"]

        try
            grid = getGrid(location["map"], Constants.BASE)
            if grid[y * width + x] == WALKABLE
                return true
            end
        catch
            return false
        end
        return false
    end

    function canWalkPath(fr::Dict, to::Dict)
        if G === nothing
            throw(ErrorException("Prepare pathfinding before querying canStand()!"))
        end
        frData = MetaGraphs.props(graph, fr)
        toData = MetaGraphs.props(graph, to)
        if frData["map"] != toData["map"]
            return False # We can't walk across maps
        end

        grid = getGrid(frData["map"])
        width = G["geometry"][frData["map"]]["max_x"] - G["geometry"][frData["map"]]["min_x"]

        xStep = Nothing
        yStep = Nothing
        error = Nothing
        errorPrev = Nothing
        x = frData["x"] - G["geometry"][frData["map"]]["min_x"]
        y = frData["y"] - G["geometry"][frData["map"]]["min_y"]
        dx = toData["x"] - frData["x"]
        dy = toData["x"] - frData["x"]

        if grid[y * width + x] != WALKABLE
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
            for i in 1:dx
                x += xStep
                error += ddy
                if error > ddx
                    y += yStep
                    error -= ddx
                    if error + errorPrev < ddx
                        if grid[(y - yStep) * width + x] != WALKABLE
                            return false
                        end
                    elseif error + errorPrev > ddx
                        if grid[y * width + x - xStep] != WALKABLE
                            return false
                        end
                    else
                        if grid[(y - yStep) * width + x] != WALKABLE
                            return false
                        end
                        if grid[y * width + x - xStep] != WALKABLE
                            return false
                        end
                    end
                end
                if grid[y * width + x] != WALKABLE
                    return false
                end
                errorPrev = error
            end
        else
            errorPrev = error = dy
            for i in 1:dy
                y += yStep
                error += ddx
                if error > ddy
                    x += xStep
                    error -= ddy
                    if error + errorPrev < ddy
                        if grid[y * width + x - xStep] != WALKABLE
                            return false
                        end
                    elseif error + errorPrev > ddy
                        if grid[(y - yStep) * width + x] != WALKABLE
                            return false
                        end
                    else
                        if grid[y * width + x - xStep] != WALKABLE
                            return false
                        end
                        if grid[(y - yStep) * width + x] != WALKABLE
                            return false
                        end
                    end
                end
                if grid[y * width + x] != WALKABLE
                    return false
                end
                errorPrev = error
            end
        end

        return true
    end

    function computeLinkCost(fr, to, link; avoidTownWarps = Nothing, costs = Dict())
        if ((link["data"]["type"]["leave"]) || (link["data"]["type"]["transport"]))
            if link["data"]["map"] == "bank"
                return 1000
            end
            if haskey(costs, "transport")
                return costs["transport"]
            else
                return TRANSPORT_COST
            end
        elseif link["data"]["type"]["enter"]
            if haskey(costs, "enter")
                return costs["enter"]
            else
                return ENTER_COST
            end
        elseif link["data"]["type"]["town"]
            if avoidTownWarps == true
                return typemax(Int)
            else
                if haskey(costs, "town")
                    return costs["town"]
                else
                    return TOWN_COST
                end
            end
        end

        if fr["map"] == to["map"]
            return Tools.distance(fr, to)
        end
    end

    function computePathCost(path; avoidTownWarps = false, costs = Dict())
        cost = 0
        current = path[1]
        for i in 2:length(path)
            next = path[i]
            link = Dict("data"=>next)
            cost += computeLinkcost(current, next, link, avoidTownWarps, costs)
            current = next
        end
        return cost
    end

    function getGrid(map::String, base = Constants.BASE)
        if haskey(grids, map)
            return grids[map]
        else
            return createGrid(map, base)
        end
    end

    function createGrid(map::String, base = Constants.BASE)
        if G === nothing
            throw(ErrorException("Prepare pathfinding before querying createGrid()!"))
        end

        minX = G["geometry"][map]["min_x"]
        minY = G["geometry"][map]["min_y"]
        width = G["geometry"][map]["max_x"] - minX
        height = G["geometry"][map]["max_y"] - minY

        grid = Array{Int8}(undef, (height * width))
        fill!(grid, UNKNOWN)
        Threads.@threads for yLine in G["geometry"][map]["y_lines"]
            lowerY = max(1, (yLine[1] - minY - base["vn"]))
            upperY = (min((yLine[1] - minY + base["v"] + 1), height)) - 1
            lowerX = max(1, (yLine[2] - minX - base["h"]))
            upperX = (min((yLine[3] - minX + base["h"] + 1), width)) - 1
            Threads.@threads for y in lowerY:upperY-1
                Threads.@threads for x in lowerX:upperX
                    grid[y * width + x] = UNWALKABLE
                end
            end
        end
        
        Threads.@threads for xLine in G["geometry"][map]["x_lines"]
            lowerX = max(1, (xLine[1] - minX - base["h"]))
            upperX = min((xLine[1] - minX + base["h"]), width)
            lowerY = max(1, (xLine[2] - minY - base["vn"]))
            upperY = min((xLine[3] - minY + base["v"]), height)
            Threads.@threads for x in lowerX:(upperX-1)
                Threads.@threads for y in lowerY:(upperY-1)
                    grid[y * width + x] = UNWALKABLE
                end
            end
        end
        
        Threads.@threads for spawn in G["maps"][map]["spawns"]
            x = trunc(Int, spawn[1]) - minX
            y = trunc(Int, spawn[2]) - minY
            if grid[y * width + x] != WALKABLE
                stack = [[y, x]]
                while length(stack) > 0
                    y, x = pop!(stack)
                    while x >= 0 && grid[y * width + x] == UNKNOWN
                        x -= 1
                    end
                    x += 1
                    spanAbove = 0
                    spanBelow = 0
                    while x < width && grid[y * width + x] == UNKNOWN
                        grid[y * width + x] = WALKABLE
                        if y > 0 && grid[(y - 1) * width + x] == UNKNOWN
                            if spanAbove == 0
                                append!(stack, [[y - 1, x]])
                                spanAbove = 1
                            else
                                spanAbove = 0
                            end
                        end

                        if y < (height - 1) && grid[(y + 1) * width + x] == UNKNOWN
                            if spanBelow == 0
                                append!(stack, [[y + 1, x]])
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
        return grid
    end

    function findClosestSpawn(map::String, x::Int, y::Int)
        closest = Dict("distance"=>typemax(Int), "map"=>map, "x"=>typemax(Int), "y"=>typemax(Int))
        for spawn in G["maps"][map]["spawns"]
            distance = Tools.distance(Dict("x"=>x, "y"=>y), Dict("x"=>spawn[1], "y"=>spawn[2]))
            if distance < closest["distance"]
                closest["x"] = spawn[1]
                closest["y"] = spawn[2]
                closest["distance"] = distance
            end
        end

        return closest
    end

    function updateGraph(map::String, grid::Vector{Int8})
        minX = G["geometry"][map]["min_x"]
        minY = G["geometry"][map]["min_y"]
        width = G["geometry"][map]["max_x"] - minX
        height = G["geometry"][map]["max_y"] - minY

        points = []
        walkableNodes = []
        
        Threads.@threads for y in 2:(height - 2)
            Threads.@threads for x in 2:(width - 1)
                mC = grid[y * width + x]

                if mC != WALKABLE
                    continue
                end

                bL = grid[(y - 1) * width + x - 1]
                bC = grid[(y - 1) * width + x]
                bR = grid[(y - 1) * width + x + 1]
                mL = grid[y * width + x - 1]
                mR = grid[y * width + x + 1]
                uL = grid[(y + 1) * width + x - 1]
                uC = grid[(y + 1) * width + x]
                uR = grid[(y + 1) * width + x + 1]

                mapX = x + minX
                mapY = y + minY

                if (!(WALKABLE in [uL, mL, bL, bC, bR])
                    || !(WALKABLE in [uR, mR, bL, bC, bR])
                    || !(WALKABLE in [uL, uC, uR, mR, bR])
                    || !(WALKABLE in [uL, uC, uR, mL, bL])
                    || ((bL == UNWALKABLE) && !(UNWALKABLE in [mL, bC]))
                    || ((bR == UNWALKABLE) && !(UNWALKABLE in [mR, bC]))
                    || ((uR == UNWALKABLE) && !(UNWALKABLE in [uC, mR]))
                    || ((uL == UNWALKABLE) && !(UNWALKABLE in [uC, mL])))
                    append!(points, [[mapX, mapY]])
                    append!(walkableNodes, [addNodeToGraph(map, mapX, mapY)])
                end
            end
        end

        transporters = [npc for npc in G["maps"][map]["npcs"] if npc["id"] == "transporter"]
        Threads.@threads for npc in transporters
            pos = npc["position"]
            closest = findClosestSpawn(map, pos[1], pos[2])
            append!(points, [[closest["x"], closest["y"]]])
            append!(walkableNodes, [addNodeToGraph(map, closest["x"], closest["y"])])

            angle = 0
            while angle < MathConstants.pi * 2
                x = trunc(Int, pos[1] + Base.Math.cos(angle) * (Constants.TRANSPORTER_REACH_DISTANCE - 10))
                y = trunc(Int, pos[2] + Base.Math.sin(angle) * (Constants.TRANSPORTER_REACH_DISTANCE - 10))
                if canStand(Dict("map"=>map, "x"=>x, "y"=>y))
                    append!(points, [[x, y]])
                    append!(walkableNodes, [addNodeToGraph(map, x, y)])
                end
                angle += MathConstants.pi / 32
            end
        end

        doors = [door for door in G["maps"][map]["doors"] if length(door) < 8 || door[8] != "complicated"]
        Threads.@threads for door in doors
            spawn = G["maps"][map]["spawns"][door[7] + 1]
            append!(points, [[spawn[1], spawn[2]]])
            append!(walkableNodes, [addNodeToGraph(map, spawn[1], spawn[2])])

            doorX = door[1]
            doorY = door[2]
            doorWidth = door[3]
            doorHeight = door[4]
            doorCorners = [
                Dict("x"=>(doorX - (doorWidth / 2)), "y"=>(doorY - (doorHeight / 2))),
                Dict("x"=>(doorX + (doorWidth / 2)), "y"=>(doorY - (doorHeight / 2))),
                Dict("x"=>(doorX - (doorWidth / 2)), "y"=>(doorY + (doorHeight / 2))),
                Dict("x"=>(doorX + (doorWidth / 2)), "y"=>(doorY + (doorHeight / 2)))
            ]
            Threads.@threads for point in doorCorners
                angle = 0
                while angle < MathConstants.pi * 2
                    x = trunc(Int, point["x"] + Base.Math.cos(angle) * (Constants.DOOR_REACH_DISTANCE - 10))
                    y = trunc(Int, point["y"] + Base.Math.sin(angle) * (Constants.DOOR_REACH_DISTANCE - 10))
                    if canStand(Dict("map"=>map, "x"=>x, "y"=>y))
                        append!(points, [[x, y]])
                        append!(walkableNodes, [addNodeToGraph(map, x, y)])
                    end
                    angle += MathConstants.pi / 32
                end
            end
        end

        spawns = G["maps"][map]["spawns"]
        townNode = addNodeToGraph(map, spawns[1][1], spawns[1][2])
        append!(walkableNodes, [townNode])
        Threads.@threads for spawn in spawns
            append!(points, [[spawn[1], spawn[2]]])
            append!(walkableNodes, [addNodeToGraph(map, spawn[1], spawn[2])])
        end

        links = []

        Threads.@threads for fromNode in walkableNodes
            Threads.@threads for door in doors
                if doorDistance(MetaGraphs.props(graph, fromNode), door) > Constants.DOOR_REACH_DISTANCE
                    continue
                end

                spawn2 = G["maps"][door[5]]["spawns"][door[6] + 1]
                toDoor = addNodeToGraph(door[5], spawn2[1], spawn2[2])
                if length(door) > 7 && door[8] == "key"
                    data = Dict("key"=>door[9], "map"=>door[5], "type"=>["enter"], "x"=>spawn2[1], "y"=>spawn2[2], "spawn"=>nothing)
                    append!(links, [addLinkToGraph(fromNode, toDoor, Dict("data"=>data))])
                else
                    data = Dict("key"=>nothing, "map"=>door[5], "type"=>["transport"], "x"=>spawn2[1], "y"=>spawn2[2], "spawn"=>door[6])
                    append!(links, [addLinkToGraph(fromNode, toDoor, Dict("data"=>data))])
                end
            end
            Threads.@threads for npc in transporters
                pos = npc["position"]
                if Tools.distance(MetaGraphs.props(graph, fromNode), Dict("x"=>pos[1], "y"=>pos[2])) > Constants.TRANSPORTER_REACH_DISTANCE
                    continue
                end
                Threads.@threads for toMap in collect(keys(G["npcs"]["transporter"]["places"]))
                    if map == toMap
                        continue
                    end
                    spawnID = G["npcs"]["transporter"]["places"][toMap] + 1
                    spawn = G["maps"][toMap]["spawns"][spawnID]
                    toNode = addNodeToGraph(toMap, spawn[1], spawn[2])

                    data = Dict("key"=>nothing, "map"=>toMap, "type"=>["transport"], "x"=>spawn[1], "y"=>spawn[2], "spawn"=>spawnID)
                    append!(links, [addLinkToGraph(fromNode, toNode, Dict("data"=>data))])
                end
            end
        end
        leaveX = G["maps"]["main"]["spawns"][1][1]
        leaveY = G["maps"]["main"]["spawns"][1][2]
        leaveNode = addNodeToGraph("main", leaveX, leaveY)
        leaveData = Dict("key"=>nothing, "map"=>"main", "type"=>["leave"], "x"=>leaveX, "y"=>leaveY, "spawn"=>nothing)
        townData = Dict("map"=>map, "type"=>["town"], "x"=>leaveX, "y"=>leaveY, "spawn"=>nothing, "key"=>nothing)
        for node in walkableNodes
            if node != townNode
                append!(links, [addLinkToGraph(node, townNode, Dict("data"=>townData))])
            end
            if map == "cyberland" || map == "jail"
                append!(links, [addLinkToGraph(node, leaveNode, Dict("data"=>leaveData))])
            end
        end


    end

    function prepare(g; base = Constants.BASE, cheat = false, include_bank_b = false, include_bank_u = false, include_test = false)
        global G = g

        NOTMAPS = ["d_b1", "d2", "batcave", "resort", "d_a2", "dungeon0", "cgallery", "d_a1", "ship0", "d_g", "abtesting", "old_bank", "old_main", "original_main", "duelland", "test", "bank_u", "shellsisland", "goobrawl", "bank_b"]

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

        append!(maps, ["jail"])

        # Threads.@threads for map in maps
        #     grid = createGrid(map)
        #     updateGraph(map, grid)
        # end
    end
end