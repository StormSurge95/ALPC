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

    global G = missing
    const FIRST_MAP = "main"
    const TRANSPORT_COST = 50
    const TOWN_COST = 450
    const ENTER_COST = 1000

    grids = Dict{String, Vector{Int}}()
    graph = Graphs.createGraph()

    function getGrid(map::String, base::Dict{String, Int} = Constants.BASE)
        global G
        if G === missing
            throw(MissingException("Prepare pathfinding before querying getGrid()!"))
        end

        if haskey(grids, map)
            return grids[map]
        end

        minX::Int64 = G["geometry"][map]["min_x"]
        minY::Int64 = G["geometry"][map]["min_y"]
        width::Int64 = G["geometry"][map]["max_x"] - minX
        height::Int64 = G["geometry"][map]["max_y"] - minY

        grid::Vector{Int} = Vector{Int}(undef, (width * height))
        fill!(grid, UNKNOWN)

        for yLine in G["geometry"][map]["y_lines"]
            lowerY::Int64 = max(1, (yLine[1] - minY - base["vn"]))
            upperY::Int64 = min((yLine[1] - minY + base["v"] + 1), height)
            lowerX::Int64 = max(1, (yLine[2] - minX - base["h"]))
            upperX::Int64 = min((yLine[3] - minX + base["h"] + 1), width)
            for y::Int64 in lowerY:upperY
                for x::Int64 in lowerX:upperX
                    grid[y * width + x]::Int64 = UNWALKABLE
                end
            end
        end

        for xLine in G["geometry"][map]["x_lines"]
            lowerX::Int64 = max(1, (xLine[1] - minX - base["h"]))
            upperX::Int64 = min((xLine[1] - minX + base["h"] + 1), width)
            lowerY::Int64 = max(1, (xLine[2] - minY - base["vn"]))
            upperY::Int64 = min((xLine[3] - minY + base["v"] + 1), height)
            for x in lowerX:upperX
                for y in lowerY:upperX
                    grid[y * width + x] = UNWALKABLE
                end
            end
        end
    end

    function prepare(g::Dict; cheat::Bool = false, include_bank_b::Bool = false,
                     include_bank_u::Bool = false, include_test::Bool = false)
        
        global G = g
        
        NOTMAPS = [ "d_b1", "d2", "batcave", "resort", "d_a2", "dungeon0", "cgallery",
                    "d_a1", "ship0", "d_g", "abtesting", "old_bank", "old_main",
                    "original_main", "duelland", "test", "bank_u", "shellsisland",
                    "goobrawl", "bank_b" ]
        maps = [key for key in G["maps"] if !(key in NOTMAPS)]

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

        for map in maps
            getGrid(map)
        end
    end
end