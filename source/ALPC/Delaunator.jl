module ALGraph

mutable struct GraphNode
    name::String
    map::String
    x::Int64
    y::Int64
    links::Union{Vector{GraphLink}, Nothing}

    function GraphNode(name::String, map::String, x::Int64, y::Int64, links::Union{Vector{GraphLink}, Nothing}=nothing)
        return new(name, map, x, y, links)
    end
end

function Node(name::String, map::String, x::Int64, y::Int64, links::Union{Vector{GraphLink}, Nothing}=nothing)
    return GraphNode(name, map, x, y, links)
end

function makeNodeID(map::String, x::Int64, y::Int64)
    return string(map,":",x,",",y)

mutable struct GraphLink
    id::String
    sourceID::String
    destID::String
    key::Union{Nothing, String}
    map::String
    types::Dict{String, Bool}
    x::Int64
    y::Int64
    spawn::Union{Nothing, Int64}
    
    function GraphLink(id::String, source::GraphNode, dest::GraphNode, key::Union{Nothing, String},
                       map::String, types::Dict{String, Bool}, x::Int64, y::Int64, spawn::Union{Nothing, Int64})
        return new(id, source, dest, key, map, types, x, y, spawn)
    end
end

function Link(id::String, sourceID::String, destID::String, key::Union{Nothing, String},
              map::String, types::Dict{String, Bool}, x::Int64, y::Int64, spawn::Union{Nothing, Int64})
    return GraphLink(id, sourceID, destID, key, map, types, x, y, spawn)
end
function Link(id::String, source::GraphNode, dest::GraphNode, key::Union{Nothing, String},
              map::String, types::Dict{String, Bool}, x::Int64, y::Int64, spawn::Union{Nothing, Int64})
    return GraphLink(id, source.name, dest.name, key, map, types, x, y, spawn)
end

function makeLinkID(sourceID::String, destID::String)
    return sourceID * "->" * destID
end

function addLinkToNode(node::GraphNode, link::GraphLink)
    if node.links === nothing
        node.links = [link]
    else
        append!(node.links, [link])
    end
end

mutable struct Graph
    nodes::Dict{String,GraphNode}
    links::Dict{String,GraphLink}

    function Graph()
        return new(Dict{String,GraphNode}(), Dict{String,GraphLink}())
    end
end

function getNode(graph::Graph, name::String)
    return graph.nodes[name]
end

function addNode!(graph::Graph, map::String, x::Int64, y::Int64)
    try
        return getNode(graph, name)
    catch
        name::String = map * ":" * x * "," * y

    end