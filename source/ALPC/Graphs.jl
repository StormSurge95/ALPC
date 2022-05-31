module Graphs

struct LinkTypes
    walk::Bool
    town::Bool
    transport::Bool
    enter::Bool

    function LinkTypes(walk, town, transport, enter)
        return new(walk, town, transport, enter)
    end
end

function Types(walk, town, transport, enter)
    return LinkTypes(walk, town, transport, enter)
end

mutable struct GraphLink
    id::String
    sourceID::String
    destID::String
    key::Union{Nothing, String}
    map::String
    types::LinkTypes
    x::Int64
    y::Int64
    spawn::Union{Nothing, Int64}
    
    function GraphLink(id::String, sourceID::String, destID::String, key::Union{Nothing, String},
                       map::String, types::LinkTypes, x::Int64, y::Int64, spawn::Union{Nothing, Int64})
        return new(id, sourceID, destID, key, map, types, x, y, spawn)
    end
end

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
end

function Link(id::String, sourceID::String, destID::String, key::Union{Nothing, String},
              map::String, types::LinkTypes, x::Int64, y::Int64, spawn::Union{Nothing, Int64})
    return GraphLink(id, sourceID, destID, key, map, types, x, y, spawn)
end
function Link(id::String, source::GraphNode, dest::GraphNode, key::Union{Nothing, String},
              map::String, types::LinkTypes, x::Int64, y::Int64, spawn::Union{Nothing, Int64})
    return GraphLink(id, source.name, dest.name, key, map, types, x, y, spawn)
end

function makeLinkID(sourceID::String, destID::String)
    return "$sourceID->$destID"
end

mutable struct Graph
    nodes::Dict{String,GraphNode}
    links::Dict{String,GraphLink}

    function Graph()
        g = new()
        g.nodes = Dict()
        g.links = Dict()
        return g
    end
end
function createGraph()
    return Graph()
end

function addLinkToNode!(node::GraphNode, link::GraphLink)
    if node.links === nothing
        node.links = [link]
    else
        append!(node.links, [link])
    end
end
function addLinkToNode!(graph::Graph, node::String, link::GraphLink)
    n = graph.nodes[node]
    if n.links === nothing
        n.links = [link]
    else
        append!(n.links, [link])
    end
end

function getNode(graph::Graph, name::String)
    return graph.nodes[name]
end

function addNode!(graph::Graph, map::String, x::Int64, y::Int64)
    name = makeNodeID(map, x, y)
    if haskey(graph.nodes, name)
        return getNode(graph, name)
    else
        node = Node(name, map, x, y)
        graph.nodes[name] = node
        return node
    end
end

function addNode!(graph::Graph, name::String)
    if haskey(graph.nodes, name)
        return getNode(graph, name)
    else
        n::Vector{SubString{String}} = split(name, ':')
        n = cat(n[1], split(n[2], ','), dims=1)
        nMap::String = String(n[1])
        nX::Int64 = parse(Int64, String(n[2]))
        nY::Int64 = parse(Int64, String(n[3]))
        node::GraphNode = Node(name, nMap, nX, nY)
        graph.nodes[name] = node
        return node
    end
end

function getLink(graph::Graph, name::String)
    return graph.links[name]
end

function getLink(from::GraphNode, to::GraphNode)
    if from.links === nothing
        return nothing
    end
    for link in from.links
        if link.destID == to.name
            return link
        end
    end
    return nothing
end

function removeLink!(graph::Graph, link::GraphLink)
    delete!(graph.links, link.name)

    from::GraphNode = getNode(graph, link.sourceID)
    to::String = getNode(graph, link.destID).name

    for i in 1:length(from.links)
        frLink = from.links[i]
        if frLink.destID == to
            deleteat!(from.links, i)
            break
        end
    end

    return nothing
end

function addLink!(graph::Graph, source::String, dest::String, data::Dict{String})
    name::String = makeLinkID(source, dest)
    if haskey(graph.links, name)
        return getLink(graph, name)
    else
        link::GraphLink = Link(name, source, dest, data["key"], data["map"], data["types"], data["x"], data["y"], data["spawn"])
        graph.links[name] = link
        sNode::GraphNode = addNode!(graph, source)
        addNode!(graph, dest)
        addLinkToNode!(sNode, link)
        return link
    end
end

function getNodesCount(graph::Graph)
    return length(graph.nodes)
end

function getLinksCount(graph::Graph)
    return length(graph.links)
end

function hasNode(graph::Graph, map::String, x::Int64, y::Int64)
    name = "$map:$x,$y"
    return haskey(graph.nodes, name)
end
function hasNode(graph::Graph, name::String)
    return haskey(graph.nodes, name)
end

function getLinks(node::GraphNode)
    return node.links
end

function forEachNode(graph::Graph, f::Function)
    nodes = collect(values(graph.nodes))
    for node in nodes
        f(node)
    end
    return nothing
end

function forEachLink(graph::Graph, f::Function)
    links = collect(values(graph.links))
    for link in links
        f(link)
    end
    return nothing
end

function forEachLinkedNode(graph::Graph, nodeID::String, f::Function)
    node::GraphNode = getNode(graph, nodeID)
    links::Vector{GraphLink} = node.links

    if links === nothing
        return nothing
    end

    for link in links
        dst::GraphNode = getNode(graph, link.destID)
        f(dst)
    end
    return nothing
end

function removeNode!(graph::Graph, node::GraphNode)
    links = getLinks(node)

    if links !== nothing
        for link in links
            removeLink!(graph, link)
        end
    end

    delete!(graph.nodes, node.name)

    return nothing
end

end