module Delaunator

EPSILON = 2 ^ -52
EDGE_STACK = Vector(undef, 512)
fill!(EDGE_STACK, -1)

mutable struct Delaunay
    coords::Vector{Int64}
    _triangles::Vector{Int64}
    _halfedges::Vector{Int64}
    hashSize::Int64
    hullPrev::Vector{Int64}
    hullNext::Vector{Int64}
    hullTri::Vector{Int64}
    hullHash::Vector{Int64}
    _ids::Vector{Int64}
    _dists::Vector{Int64}
    triangles::Vector{Int64}
    halfedges::Vector{Int64}
    _cx::Int64
    _cy::Int64
    _hullStart::Int64
    trianglesLen::Int64
    hull::Vector{Int64}

    function Delaunay(points::Vector{Vector{Int64}})
        d::Delaunay = new()
        n::Int64 = length(points)

        if (n < 3)
            throw(DomainError(n, "Need at least 3 points"))
        end

        coords::Vector{Int64} = Vector(undef, n * 2)

        for i in 1:n
            p::Vector{Int64} = points[i]
            coords[2 * i - 1] = p[1]
            coords[2 * i] = p[2]
        end
        triangles::Vector{Int64} = constructor(d, coords)
        return d
    end

    function Delaunay(points::Matrix)
        vPoints::Vertex{Vertex{Int64}} = [c[:] for c in eachrow(points)]

        return Delaunay(vPoints)
    end
end

function constructor(d::Delaunay, coords)
    n::Int64 = length(coords) >> 1

    d.coords = coords

    # arrays that will store the triangulation graph
    maxTriangles::Int64 = max(2 * n - 5, 0)
    d._triangles = Vector(undef, maxTriangles * 3)
    d._halfedges = Vector(undef, maxTriangles * 3)

    # temporary arrays for tracking the edges of the advancing convex hull
    d.hashSize = ceil(sqrt(n))
    d.hullPrev = Vector(undef, n) # edge to prev edge
    d.hullNext = Vector(undef, n) # edge to next edge
    d.hullTri = Vector(undef, n) # edge to adjacent triangle
    d.hullHash = Vector(undef, d.hashSize) # angular edge hash
    fill!(d.hullHash, -1)

    # temporary arrays for sorting points
    d._ids = Vector(undef, n)
    d._dists = Vector(undef, n)
    triangles::Vector{Int64} = update(d, coords)

    return triangles
end

function update(d::Delaunay, coords)
    n::Int64 = length(coords) >> 1

    # populate an array of point indices; calculate input data bbox
    minX::Int64 = typemax(Int64)
    minY::Int64 = typemax(Int64)
    maxX::Int64 = typemin(Int64)
    maxY::Int64 = typemin(Int64)

    for i in 1:n
        x::Int64 = coords[2 * i - 1]
        y::Int64 = coords[2 * i]
        if (x < minX)
            minX = x
        end
        if (y < minY)
            minY = y
        end
        if (x > maxX)
            maxX = x
        end
        if (y > maxY)
            maxY = y
        end
        d._ids[i] = i
    end

    cx::Int64 = trunc((minX + maxX) / 2)
    cy::Int64 = trunc((minY + maxY) / 2)

    minDist::Int64 = typemax(Int64)
    i0::Int64 = 1
    i1::Int64 = 1
    i2::Int64 = 1

    # pick a seed point close to the center_pt
    for i in 1:n
        di::Int64 = dist(cx, cy, coords[2 * i - 1], coords[2 * i])

        if (di < minDist)
            i0 = i
            minDist = di
        end
    end

    i0x::Int64 = coords[2 * i0]
    i0y::Int64 = coords[2 * i0 + 1]
    minDist = typemax(Int64)

    # find the point closest to the seed
    for i in 1:n
        if (i == i0)
            continue
        end
        di::Int64 = dist(i0x, i0y, coords[2 * i - 1], coords[2 * i])

        if (di < minDist && di > 0)
            i1 = i
            minDist = di
        end
    end

    i1x::Int64 = coords[2 * i1]
    i1y::Int64 = coords[2 * i1 + 1]

    minRadius::Int64 = typemax(Int64)

    # find the third point which forms the smallest circumcircle with the first two
    for i in 1:n
        if (i == i0 || i == i1)
            continue
        end
        r::Int64 = circumradius(i0x, i0y, i1x, i1y, coords[2 * i - 1], coords[2 * i])

        if (r < minRadius)
            i2 = i
            minRadius = r
        end
    end

    i2x::Int64 = coords[2 * i2]
    i2y::Int64 = coords[2 * i2 + 1]

    if (minRadius == typemax(Int64))
        # order collinear points by dx (or dy if all x are identical)
        # and return the list as a hull
        for i in 1:n
            d._dists[i] = (coords[2 * i - 1] - coords[1]) || (coords[2 * i] - coords[2])
        end

        quicksort(d._ids, d._dists, 1, n)
        hull::Vector{Int64} = Vector(undef, n)
        j::Int64 = 0
        d0::Int64 = typemin(Int64)

        for i in 1:n
            id = d._ids[i]

            if d._dists[id] > d0
                hull[j] = id
                j+=1
                d0 = d._dists[id]
            end
        end

        d.hull = hull[1:j]
        d.triangles = Vector()
        d.halfedges = Vector()
    end

    # swap the order of the seed points for counter-clockwise orientation
    if (orient(i0x, i0y, i1x, i1y, i2x, i2y))
        i_::Int64 = i1
        x_::Int64 = i1x
        y_::Int64 = i1y
        i1 = i2
        i1x = i2x
        i1y = i2y
        i2 = i_
        i2x = x_
        i2y = y_
    end

    center::Tuple{Int64, Int64} = circumcenter(i0x, i0y, i1x, i1y, i2x, i2y)
    d._cx = center[1]
    d._cy = center[2]

    for i in 1:n
        d._dists[i] = dist(coords[2 * i - 1], coords[2 * i], center[1], center[2])
    end

    # sort the points by distance from the seed triangle circumcenter
    quicksort(d._ids, d._dists, 1, n)

    # set up the seed triangle as the starting hull
    d._hullStart = i0
    hullSize::Int64 = 3

    d.hullNext[i0] = d.hullPrev[i2] = i1
    d.hullNext[i1] = d.hullPrev[i0] = i2
    d.hullNext[i2] = d.hullPrev[i1] = i0

    d.hullTri[i0] = 0
    d.hullTri[i1] = 1
    d.hullTri[i2] = 2

    d.hullHash[_hashKey(d, i0x, i0y)] = i0
    d.hullHash[_hashKey(d, i1x, i1y)] = i1
    d.hullHash[_hashKey(d, i2x, i2y)] = i2

    d.trianglesLen = 0
    _addTriangle(d, i0, i1, i2, -1, -1, -1)

    xp = 0
    yp = 0

    for k in 1:length(d._ids)
        i = d._ids[k]
        x = coords[2 * i - 1]
        y = coords[2 * i]

        # skip near-duplicate points
        if (k > 0 && abs(x - xp) <= EPSILON && abs(y - yp) <= EPSILON)
            continue
        end

        xp = x
        yp = y

        # skip seed triangle points
        if (i == i0 || i == i1 || i == i2)
            continue
        end

        # find a viable edge on the convex hull using edge hashSize
        start = 0
        key = _hashKey(d, x, y)

        for j in 1: d.hashSize
            start = d.hullHash[((key + j) % d.hashSize) + 1]
            if (start != -1 && start != d.hullNext[start])
                break
            end
        end

        start = d.hullPrev[start]
        e = start

        while true
            q = d.hullNext[e]
            if orient(x, y, coords[2 * e - 1], coords[2 * e], coords[2 * q - 1], coords[2 * q])
                break
            end
            e = q
            if (e == start)
                e = -1
                break
            end
        end

        if (e == -1)
            continue # likely a near-duplicate point; skip it
        end

        # add the first triangle from the point
        t = _addTriangle(d, e, i, d.hullNext[e], -1, -1, d.hullTri[e])

        # recursively flip triangles from the point until they satisfy the Delaunay condition
        d.hullTri[i] = _legalize(d, t + 2, coords)
        d.hullTri[e] = t # keep track of boundary triangles on the hull
        hullSize += 1

        # walk forward through the hull, adding more triangles and flipping recursively
        n = d.hullNext[e]

        while true
            q = d.hullNext[n]
            if !(orient(x, y, coords[2 * n - 1], coords[2 * n], coords[2 * q - 1], coords[2 * q]))
                break
            end
            t = _addTriangle(d, n, i, q, d.hullTri[i], -1, d.hullTri[n])
            d.hullTri[i] = _legalize(d, t + 2, coords)
            d.hullNext[n] = n # mark as removed
            hullSize -= 1
            n = q
        end

        # walk backward from the other side, adding more triangles and flipping
        if (e == start)
            while true
                q = d.hullPrev[e]
                if !(orient(x, y, coords[2 * q - 1], coords[2 * q], coords[2 * e - 1], coords[2 * e]))
                    break
                end
                t = _addTriangle(d, q, i, e, -1, d.hullTri[e], d.hullTri[q])
                _legalize(d, t + 2, coords)
                d.hullTri[q] = t
                d.hullNext[e] = e # mark as removed
                hullSize -= 1
                e = q
            end
        end

        # update the hull indices
        d._hullStart = d.hullPrev[i] = e
        d.hullNext[e] = d.hullPrev[n] = i
        d.hullNext[i] = n

        # save the two new edges in the hash table
        d.hullHash[_hashKey(d, x, y)] = i
        d.hullHash[_hashKey(d, coords[2 * e - 1], coords[2 * e])] = e
    end

    d.hull = Vector(undef, hullSize)
    e = d._hullStart
    for i in 1:hullSize
        d.hull[i] = e
        e = d.hullNext[e]
    end

    # trim typed triangle mesh arrays
    d.triangles = d._triangles[1:d.trianglesLen]
    d.halfedges = d._halfedges[1:d.trianglesLen]

    return d.triangles
end

function _hashKey(d::Delaunay, x, y)
    return (trunc(Int64, floor(pseudoAngle(x - d._cx, y - d._cy) * d.hashSize) % d.hashSize)) + 1
end

function _legalize(d::Delaunay, a, coords)
    i = 1
    ar = 0

    # recursion eliminated with a fixed-size stack
    while true
        b = d._halfedges[a]
        # if the pair of triangles doesn't satisfy the Delaunay condition
        # (p1 is inside the circumcircle of [p0, pl, pr]), flip them,
        # then do the same check/flip recursively for the new pair of triangles
        # 
        #           pl                    pl
        #          /||\                  /  \ 
        #       al/ || \bl            al/    \a
        #        /  ||  \              /      \ 
        #       /  a||b  \    flip    /___ar___\ 
        #     p0\   ||   /p1   =>   p0\---bl---/p1
        #        \  ||  /              \      /
        #       ar\ || /br             b\    /br
        #          \||/                  \  /
        #           pr                    pr
        a0 = a - a % 3
        ar = (a0 + (a + 2) % 3) + 1

        if (b == 0) # convex hull edge
            if i == 1
                break
            end
            i -= 1
            a = EDGE_STACK[i]
            continue
        end

        b0 = (b - b % 3) + 1
        al = (a0 + (a + 1) % 3) + 1
        bl = (b0 + (b + 2) % 3) + 1

        p0 = d._triangles[ar]
        pr = d._triangles[a]
        pl = d._triangles[al]
        p1 = d._triangles[bl]

        illegal = inCircle(
            coords[2 * p0 - 1], coords[2 * p0],
            coords[2 * pr - 1], coords[2 * pr],
            coords[2 * pl - 1], coords[2 * pl],
            coords[2 * p1 - 1], coords[2 * p1])
        
        if (illegal)
            d._triangles[a] = p1
            d._triangles[b] = p0

            hbl = d._halfedges[bl]

            # edge swapped on the other side of the hull (rare); fix the halfedge reference
            if (hbl == -1)
                e = d._hullStart

                while true
                    if (d.hullTri[e] == bl)
                        d.hullTri[e] = a
                        break
                    end

                    e = d.hullPrev[e]
                    if (e == d._hullStart)
                        break
                    end
                end
            end

            _link(d, a, hbl)
            _link(d, b, d._halfedges[ar])
            _link(d, ar, bl)

            br = b0 + (b + 1) % 3

            # don't worry about hitting the cap: it can only happen on extremely degenerate input
            if (i <= length(EDGE_STACK))
                EDGE_STACK[i] = br
                i += 1
            end
        else
            if (i == 1)
                break
            end
            i -= 1
            a = EDGE_STACK[i]
        end
    end
    return ar
end

function _link(d::Delaunay, a, b)
    d._halfedges[a] = b
    if (b > 0)
        d._halfedges[b] = a
    end
    return nothing
end

function _addTriangle(d::Delaunay, i0, i1, i2, a, b, c)
    t = d.trianglesLen

    d._triangles[t + 1] = i0
    d._triangles[t + 2] = i1
    d._triangles[t + 3] = i2

    _link(d, t + 1, a)
    _link(d, t + 2, b)
    _link(d, t + 3, c)

    d.trianglesLen += 3

    return t
end

function pseudoAngle(dx, dy)
    p = dx / (abs(dx) + abs(dy))

    if (dy > 0)
        return (3 - p) / 4
    else
        return (1 + p) / 4
    end
end

function dist(ax, ay, bx, by)
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy
end

function orientIfSure(px, py, rx, ry, qx, qy)
    l = (ry - py) * (qx - px)
    r = (rx - px) * (qy - py)

    if (abs(l - r) >= 3.3306690738754716e-16 * abs(l + r))
        return l - r
    else
        return 0
    end
end

function orient(rx, ry, qx, qy, px, py)
    b1 = orientIfSure(px, py, rx, ry, qx, qy) < 0
    b2 = orientIfSure(rx, ry, qx, qy, px, py) < 0
    b3 = orientIfSure(qx, qy, px, py, rx, ry) < 0
    return (b1 || b2 || b3)
end

function inCircle(ax, ay, bx, by, cx, cy, px, py)
    dx = ax - px
    dy = ay - py
    ex = bx - px
    ey = by - py
    fx = cx - px
    fy = cy - py

    ap = dx * dx + dy * dy
    bp = ex * ex + dy * dy
    cp = fx * fx + fy * fy

    return dx * (ey * cp - bp * fy) - dy * (ex * cp - bp * fx) + ap * (ex * fy - ey * fx) < 0
end

function circumradius(ax::Int64, ay::Int64, bx::Int64, by::Int64, cx::Int64, cy::Int64)
    dx::Int64 = bx - ax
    dy::Int64 = by - ay
    ex::Int64 = cx - ax
    ey::Int64 = cy - ay

    bl::Int64 = dx * dx + dy * dy
    cl::Int64 = ex * ex + ey * ey
    d = 0
    try
        d = 0.5 / (dx * ey - dy * ex)
    catch
        d = Inf
    end
    x::Int64 = trunc((ey * bl - dy * cl) * d)
    y::Int64 = trunc((dx * cl - ex * bl) * d)
    return x*x + y*y
end

function circumcenter(ax::Int64, ay::Int64, bx::Int64, by::Int64, cx::Int64, cy::Int64)
    dx::Int64 = bx - ax
    dy::Int64 = by - ay
    ex::Int64 = cx - ax
    ey::Int64 = cy - ay

    bl::Int64 = dx * dx + dy * dy
    cl::Int64 = ex * ex + ey * ey
    d = 0.0
    try
        d = 0.5 / (dx * ey - dy * ex)
    catch
        d = Inf
    end

    x::Int64 = trunc(ax + (ey * bl - dy * cl) * d)
    y::Int64 = trunc(ay + (dx * cl - ex * bl) * d)

    return x, y
end

function swap(arr, i, j)
    tmp = arr[i]
    arr[i] = arr[j]
    arr[j] = tmp
end

function quicksort(ids, dists, left, right)
    if (right - left <= 20)
        for i in (left+1):right
            temp = ids[i]
            tempDist = dists[temp]
            j = i - 1
            while (j >= left && dists[ids[j]] > tempDist)
                ids[j + 1] = ids[j]
                j-=1
            end
            ids[j + 1] = temp
        end
    else
        median = (left + right) >> 1
        i = left + 1
        j = right
        swap(ids, median, i)

        if (dists[ids[left]] > dists[ids[right]])
            swap(ids, left, right)
        end

        if (dists[ids[i]] > dists[ids[right]])
            swap(ids, i, right)
        end

        if (dists[ids[left]] > dists[ids[i]])
            swap(ids, left, i)
        end

        temp = ids[i]
        tempDist = dists[temp]

        while true
            while true
                i += 1
                if (dists[ids[i]] >= tempDist)
                    break
                end
            end
            
            while true
                j -= 1
                if (dists[ids[j]] <= tempDist)
                    break
                end
            end

            if (j < i)
                break
            end
            swap(ids, i, j)
        end

        ids[left + 1] = ids[j]
        ids[j] = temp

        if (right - i + 1 >= j - left)
            quicksort(ids, dists, i, right)
            quicksort(ids, dists, left, j - 1)
        else
            quicksort(ids, dists, left, j - 1)
            quicksort(ids, dists, i, right)
        end
    end
end

end