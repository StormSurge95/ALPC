"Graph package based on ngraph by anvaka and modified heavily for use with ALPC"
module Graphs

    "Internal Structure to represent different types for graph links"
    struct LinkTypes
        walk::Bool
        town::Bool
        transport::Bool
        enter::Bool
        leave::Bool

        function LinkTypes(walk::Bool, town::Bool, transport::Bool, enter::Bool, leave::Bool)
            return new(walk, town, transport, enter, leave)
        end
    end

    "Constructor for LinkTypes objects"
    function Types(walk::Bool, town::Bool, transport::Bool, enter::Bool, leave::Bool)
        return LinkTypes(walk, town, transport, enter, leave)
    end

    "internal structure to represent links between graph nodes"
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

    "Internal Structure to represent individual graph nodes"
    mutable struct GraphNode
        name::String
        map::String
        x::Int64
        y::Int64
        linksTo::Union{Vector{GraphLink}, Nothing}
        linksFr::Union{Vector{GraphLink}, Nothing}

        function GraphNode(name::String, map::String, x::Int64, y::Int64, linksTo::Union{Vector{GraphLink}, Nothing}=nothing, linksFr::Union{Vector{GraphLink}, Nothing} = nothing)
            return new(name, map, x, y, linksTo, linksFr)
        end
    end

    "Constructor for GraphNode objects"
    function Node(name::String, map::String, x::Int64, y::Int64, links::Union{Vector{GraphLink}, Nothing}=nothing)
        return GraphNode(name, map, x, y, links)
    end

    "Creates the unique name id for GraphNode objects"
    function makeNodeID(map::String, x::Int64, y::Int64)
        return string(map,":",x,",",y)
    end

    "Constructor for GraphLink objects"
    function Link(id::String, sourceID::String, destID::String, key::Union{Nothing, String},
                map::String, types::LinkTypes, x::Int64, y::Int64, spawn::Union{Nothing, Int64})
        return GraphLink(id, sourceID, destID, key, map, types, x, y, spawn)
    end
    function Link(id::String, source::GraphNode, dest::GraphNode, key::Union{Nothing, String},
                map::String, types::LinkTypes, x::Int64, y::Int64, spawn::Union{Nothing, Int64})
        return GraphLink(id, source.name, dest.name, key, map, types, x, y, spawn)
    end

    "Creates the unique name id for GraphLink objects"
    function makeLinkID(sourceID::String, destID::String)
        return "$sourceID->$destID"
    end

    "Internal Structure representing entire Graph objects"
    mutable struct Graph
        nodes::Dict{String,GraphNode}
        links::Dict{String,GraphLink}

        function Graph()
            g::Graph = new()
            g.nodes = Dict{String, GraphNode}()
            g.links = Dict{String, GraphLink}()
            return g
        end
    end

    "Simple constructor to create an empty Graph object"
    function createGraph()
        return Graph()
    end

    "adds a provided `link` object to the provided `node` object"
    function addLinkToNode!(node::GraphNode, link::GraphLink)
        if node.linksTo === nothing
            node.linksTo = [link]
        else
            append!(node.linksTo, [link])
        end
    end
    "adds a provided `link` object to the node within the provided `graph` that has the provided `name`"
    function addLinkToNode!(graph::Graph, name::String, link::GraphLink)
        n::GraphNode = graph.nodes[name]
        addLinkToNode!(n, link)
    end

    function addLinkFrNode!(node::GraphNode, link::GraphLink)
        if node.linksFr === nothing
            node.linksFr = [link]
        else
            append!(node.linksFr, [link])
        end
    end

    function addlinkFrNode!(graph::Graph, name::String, link::GraphLink)
        n::GraphNode = getNode(graph, name)
        addLinkFrNode!(n, link)
    end

    "Gets the GraphNode object with the provided `name` from within the provided `graph`"
    function getNode(graph::Graph, name::String)
        return graph.nodes[name]
    end

    """
    Creates and adds a `node` object to the provided `graph` object\n
    if said graph does not already have a node with the created name;\n
    else it returns the pre-existing `node` object from within the graph\n
    Creates a `name` value using the provided `map`, `x`, and `y` values 
    """
    function addNode!(graph::Graph, map::String, x::Int64, y::Int64)
        name::String = makeNodeID(map, x, y)
        if haskey(graph.nodes, name)
            return getNode(graph, name)
        else
            node::GraphNode = Node(name, map, x, y)
            graph.nodes[name] = node
            return node
        end
    end
    """
    Adds a node to the provided `graph` object using the provided `name`

    *NOTE:* the `name` string ***must*** be in the format "{map}:{x},{y}" in order to be processed
    """
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

    "Gets a link from the provided `graph` object using the proviced `name`"
    function getLink(graph::Graph, name::String)
        return graph.links[name]
    end
    "Gets a link from the provided node `from` that leads to the provided node `to`"
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

    "Removes the provided `link` object from the provided `graph` object"
    function removeLink!(graph::Graph, link::GraphLink)
        from::GraphNode = getNode(graph, link.sourceID)
        to::String = getNode(graph, link.destID).name

        for i in 1:length(from.links)
            frLink = from.links[i]
            if frLink.destID == to
                deleteat!(from.links, i)
                break
            end
        end

        delete!(graph.links, link.name)

        return nothing
    end

    """
    Creates and adds a `link` object to the provided `graph` object using\n
    the provided `source`, `dest`, and `data` parameters.\n
    *NOTE:* the `data` parameter ***must*** have values for "key", "map",\n
    "types" (in the form of the LinkTypes object), "x", "y", and "spawn"
    """
    function addLink!(graph::Graph, source::String, dest::String, data::Dict{String, Any})
        name::String = makeLinkID(source, dest)
        if haskey(graph.links, name)
            local link::GraphLink = getLink(graph, name)
            if link.key != data["key"] && data["key"] !== nothing
                link.key = data["key"]
            end
            if link.spawn != data["spawn"] && data["spawn"] !== nothing
                link.spawn = data["spawn"]
            end
            if link.types != data["types"]
                newT = data["types"]
                link.types.walk = newT.walk ? newT.walk : link.types.walk
                link.types.town = newT.town ? newT.town : link.types.town
                link.types.transport = newT.transport ? newT.transport : link.types.transport
                link.types.enter = newT.enter ? newT.enter : link.types.enter
            end
            return link
        else
            link = Link(name, source, dest, data["key"], data["map"], data["types"], data["x"], data["y"], data["spawn"])
            graph.links[name] = link
            sNode::GraphNode = addNode!(graph, source)
            dNode::GraphNode = addNode!(graph, dest)
            addLinkToNode!(sNode, link)
            addLinkToNode!(dNode, link)
            return link
        end
    end
    function addLink!(graph::Graph, source::GraphNode, dest::GraphNode, data::Dict{String, Any})
        sourceID::String = source.name
        destID::String = dest.name
        addLink!(graph, sourceID, destID, data)
    end

    "gets the count of nodes within the provided `graph` object"
    function getNodesCount(graph::Graph)
        return length(graph.nodes)
    end

    "gets the count of links within the provided `graph` object"
    function getLinksCount(graph::Graph)
        return length(graph.links)
    end
    "gets the count of links within the provided `node` object"
    function getLinksCount(node::GraphNode)
        return length(node.links)
    end

    """
    returns whether or not the provided `graph` has a node with the\n
    provided `map`, `x`, and `y` attributes
    """
    function hasNode(graph::Graph, map::String, x::Int64, y::Int64)
        name = "$map:$x,$y"
        return haskey(graph.nodes, name)
    end

    """
    returns whether or not the provided `graph` object has a node\n
    with the provided `name` attribute
    """
    function hasNode(graph::Graph, name::String)
        return haskey(graph.nodes, name)
    end

    "returns the list of links connecting the provided `node` object to other nodes"
    function getLinks(node::GraphNode)
        return node.links
    end

    "performs the provided callback `f` on each `node` object within the provided `graph`"
    function forEachNode(graph::Graph, f::Function)
        nodes = collect(values(graph.nodes))
        for node in nodes
            f(node)
        end
        return nothing
    end

    "performs the provided callback `f` on each `link` object within the provided `graph`"
    function forEachLink(graph::Graph, f::Function)
        links = collect(values(graph.links))
        for link in links
            f(link)
        end
        return nothing
    end

    """
    performs the provided callback `f` on each `node` object connected to\n
    the `node` object with the provided `nodeID` within the provided `graph`
    """
    function forEachLinkedNode(graph::Graph, nodeID::String, mode::String, f::Function)
        node::GraphNode = getNode(graph, nodeID)
        local links::Union{Vector{GraphLink}, Nothing}
        if mode === "to"
            links = node.linksTo
        elseif mode === "from"
            links = node.linksFr
        else
            throw(Exception)
        end

        if links === nothing
            return
        end

        for link in links
            dst::GraphNode = getNode(graph, link.destID)
            f(dst, link)
        end
        return
    end

    "removes the provided `node` object and all associated links from the provided `graph`"
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

    mutable struct NodeSearchState
        node::GraphNode
        p1::Union{NodeSearchState, Nothing}
        p2::Union{NodeSearchState, Nothing}
        closed::Bool
        g1::Float64
        g2::Float64
        f1::Float64
        f2::Float64
        h1::Int
        h2::Int

        function NodeSearchState(node::GraphNode)
            new(node, nothing, nothing, false, Inf64, Inf64, Inf64, Inf64, -1, -1)
        end
    end
    
    function noop(var::Any = nothing)
        x = 0
        x += 1
    end

    mutable struct NodeHeap
        data::Vector{NodeSearchState}
        length::Int
        compare::Function
        setNodeId::Function

        function NodeHeap(data::Union{Nothing, Vector{NodeSearchState}} = nothing,
                        compare::Union{Nothing, Function} = nothing,
                        setNodeId::Union{Nothing, Function} = nothing)
            if data === nothing
                data = Vector{GraphNode}()
            end
            if compare === nothing
                compare = defaultCompare
            end
            if setNodeId === nothing
                setNodeId = noop
            end

            len = length(data)

            new(data, len, compare, setNodeId)
        end
    end

    function _up!(h::NodeHeap, pos::Int)
        data = h.data
        compare = h.compare
        setNodeId = h.setNodeId
        item = data[pos]

        while pos > 1
            if pos > 2
                parent = (pos - 1) >> 1
            else
                parent = pos >> 1
            end
            current = data[parent]
            if (compare(item, current) >= 0)
                break
            end
            data[pos] = current

            setNodeId(current, pos)
            pos = parent
        end

        data[pos] = item
        setNodeId(item, pos)
        nothing
    end

    function _down!(h::NodeHeap, pos::Int)
        data = h.data
        compare = h.compare
        halfLength = h.length >> 1
        item = data[pos]
        setNodeId = h.setNodeId

        while (pos < halfLength)
            left = (pos << 1) + 1
            right = left + 1
            best = data[left]

            if (right < h.length && compare(data[right], best) < 0)
                left = right
                best = data[right]
            end
            if (compare(best, item) >= 0)
                break
            end

            data[pos] = best
            setNodeId(best, pos)
            pos = left
        end

        data[pos] = item
        setNodeId(item, pos)
        nothing
    end

    function push!(h::NodeHeap, item::NodeSearchState)
        Base.push!(h.data, item)
        h.length += 1
        h.setNodeId(item, h.length)
        _up!(h, h.length)
        nothing
    end

    function pop!(h::NodeHeap)
        if h.length === 0
            return nothing
        end

        top = h.data[1]
        h.length -= 1

        if h.length > 1
            h.data[1] = h.data[h.length]
            h.setNodeId(h.data[1], 1)
            _down!(h, 1)
        end
        Base.pop!(h.data)

        return top
    end

    function peek(h::NodeHeap)
        return h.data[1]
    end

    function update_item(h::NodeHeap, pos::Int)
        _down!(h, pos)
        _up!(h, pos)
        nothing
    end

    function compareF1Score(a::NodeSearchState, b::NodeSearchState)
        return a.f1 - b.f1
    end

    function compareF2Score(a::NodeSearchState, b::NodeSearchState)
        return a.f2 - b.f2
    end

    function setH1(node::NodeSearchState, heapIndex::Int)
        node.h1 = heapIndex
    end

    function setH2(node::NodeSearchState, heapIndex::Int)
        node.h2 = heapIndex
    end

    mutable struct SearchStatePool
        length::Int
        nodeCache::Vector{NodeSearchState}

        function SearchStatePool()
            new(0, Vector{NodeSearchState}())
        end
    end

    function reset(pool::SearchStatePool)
        pool.length = 0
        empty!(pool.nodeCache)
    end

    function createNewState(pool::SearchStatePool, node::GraphNode)
        state::NodeSearchState = NodeSearchState(node)
        append!(pool.nodeCache, [state])
        pool.length+=1
        return state
    end

    function blindHeuristic(a::Any, b::Any, c::Any = nothing)
        return 0
    end

    function constantDistance(a::Any, b::Any, c::Any = nothing)
        return 1
    end

    struct Pathfinder
        graph::Graph
        oriented::Bool
        heuristic::Function
        distance::Function
        pool::SearchStatePool

        function Pathfinder(graph::Graph, options::Dict{String, Any})
            if haskey(options, "oriented")
                oriented = options["oriented"]
            else
                oriented = true
            end

            if haskey(options, "heuristic")
                heuristic = options["heuristic"]
            else
                heuristic = blindHeuristic
            end

            if haskey(options, "distance")
                distance = options["distance"]
            else
                distance = constantDistance
            end

            if haskey(options, "pool")
                pool = options["pool"]
            else
                pool = SearchStatePool()
            end

            new(graph, oriented, heuristic, distance, pool)
        end
    end

    function reconstructPath(searchState::Union{NodeSearchState, Nothing})
        if searchState === nothing
            return []
        end

        path = [searchState.node]
        parent = searchState.p1

        while parent !== nothing
            push!(path, [parent.node])
            parent = parent.p1
        end

        child = searchState.p2
        while child !== nothing
            insert!(path, 1, child.node)
            child = child.p2
        end

        return path
    end

    function findPath(pf::Pathfinder, fromID::String, toID::String)
        from = getNode(pf.graph, fromID)
        to = getNode(pf.graph, toID)

        reset(pf.pool)

        nodeState::Dict{String, NodeSearchState} = Dict{String, NodeSearchState}()
        
        open1Set::NodeHeap = NodeHeap(nothing, compareF1Score, setH1)
        open2Set::NodeHeap = NodeHeap(nothing, compareF2Score, setH2)

        local minNode

        lMin::Float64 = Inf64

        startNode::NodeSearchState = createNewState(pf.pool, from)
        nodeState[fromID] = startNode
        startNode.g1 = 0
        f1::Float64 = pf.heuristic(from, to)
        startNode.f1 = f1
        push!(open1Set, startNode)

        endNode::NodeSearchState = createNewState(pf.pool, to)
        nodeState[toID] = endNode
        endNode.g2 = 0
        f2::Float64 = f1
        endNode.f2 = f2
        push!(open2Set, endNode)

        local cameFrom

        function visitN1(otherNode, link)
            if link.destID === cameFrom.node.name
                local otherSearchState
                try
                    otherSearchState = nodeState[otherNode.name]
                catch
                    otherSearchState = createNewState(pf.pool, otherNode)
                    nodeState[otherNode.name] = otherSearchState
                end
                if otherSearchState.closed
                    return
                end
                tentativeDistance = cameFrom.g1 + pf.distance(cameFrom.node, otherNode, link)
                if tentativeDistance < otherSearchState.g1
                    otherSearchState.g1 = tentativeDistance
                    otherSearchState.f1 = tentativeDistance + pf.heuristic(otherSearchState.node, to)
                    otherSearchState.p1 = cameFrom
                    if (otherSearchState.h1 < 0)
                        push!(open1Set, otherSearchState)
                    else
                        update_item(open1Set, otherSearchState.h1)
                    end
                end
                potentialMin = otherSearchState.g1 + otherSearchState.g2
                if potentialMin < lMin
                    lMin = potentialMin
                    minNode = otherSearchState
                end
            end
        end

        function visitN2(otherNode, link)
            if link.sourceID === cameFrom.node.name
                local otherSearchState::NodeSearchState
                try
                    otherSearchState = nodeState[otherNode.name]
                catch
                    otherSearchState = createNewState(pf.pool, otherNode)
                    nodeState[otherNode.name] = otherSearchState
                end
                if otherSearchState.closed
                    return
                end
                tentativeDistance = cameFrom.g2 + pf.distance(cameFrom.node, otherNode, link)
                if tentativeDistance < otherSearchState.g2
                    otherSearchState.g2 = tentativeDistance
                    otherSearchState.f2 = tentativeDistance + pf.heuristic(from, otherSearchState.node)
                    otherSearchState.p2 = cameFrom
                    if otherSearchState.h2 < 0
                        push!(open2Set, otherSearchState)
                    else
                        update_item(open2Set, otherSearchState.h2)
                    end
                end
                potentialMin = otherSearchState.g1 + otherSearchState.g2
                if potentialMin < lMin
                    lMin = potentialMin
                    minNode = otherSearchState
                end
            end
        end

        function forwardSearch()
            cameFrom = pop!(open1Set)
            if cameFrom.closed
                return
            end

            cameFrom.closed = true

            if (cameFrom.f1 < lMin && (cameFrom.g1 + f2 - pf.heuristic(from, cameFrom.node)) < lMin)
                forEachLinkedNode(pf.graph, cameFrom.node.name, "from", visitN1)
            end

            if (open1Set.length > 0)
                f1 = peek(open1Set).f1
            end
        end

        function reverseSearch()
            cameFrom = pop!(open2Set)
            if cameFrom.closed
                return
            end
            cameFrom.closed = true

            if (cameFrom.f2 < lMin && (cameFrom.g2 + f1 - pf.heuristic(cameFrom.node, to)) < lMin)
                forEachLinkedNode(pf.graph, cameFrom.node.name, "to", visitN2)
            end

            if open2Set.length > 0
                f2 = peek(open2Set).f2
            end
        end

        while (open2Set.length > 0 && open1Set.length > 0)
            if (open1Set.length < open2Set.length)
                forwardSearch()
            else
                reverseSearch()
            end
        end

        path = reconstructPath(minNode)
        
        return path
    end

end