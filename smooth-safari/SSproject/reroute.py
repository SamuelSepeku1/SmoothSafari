"""
reroute.py - Phase 4: Tier 2 rerouting with Dijkstra's shortest path

Both routes go from A to B and are found with Dijkstra's algorithm
(networkx.dijkstra_path) on a real OpenStreetMap road graph:

  NOT congested -> Dijkstra on plain road lengths. A and B are chosen so that
                   this shortest path passes through the intersection.
  CONGESTED     -> Dijkstra again, but every road around the intersection
                   costs 1000x more, so the algorithm picks another path.

Used by liveserver.py:   reroute.get_route(congested)
Command line:
    python reroute.py --build-graph    download the road map (first run / new coordinates)
    python reroute.py                  print both routes as a check
"""

import sys
import math
import argparse
from pathlib import Path
from functools import lru_cache

import osmnx as ox
import networkx as nx

from site_config import INTERSECTION_LAT, INTERSECTION_LNG, INTERSECTION_NAME

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Intersection name and coordinates come from site_config.py (single source of truth)

GRAPH_RADIUS_METERS = 1500       # road network downloaded around the intersection
ZONE_RADIUS_METERS = 300         # roads this close to the junction are "the intersection"
CONGESTION_PENALTY = 1000.0      # cost multiplier for those roads when congested
THROUGH_TOLERANCE_METERS = 100   # normal route must pass this close to the junction point
ENDPOINT_MIN_METERS = 500        # A and B are 500-1000 m (by road) from the junction
ENDPOINT_MAX_METERS = 1000
MAX_DETOUR_RATIO = 3.0           # prefer detours at most 3x the normal length
MAX_SNAP_METERS = 100            # marker must be this close to a road node in the saved map
MAX_PAIR_TRIES = 800

# Free map servers, tried in order if one refuses the connection
OVERPASS_SERVERS = [
    "https://overpass-api.de/api",
    "https://overpass.kumi.systems/api",
    "https://overpass.private.coffee/api",
]

GRAPH_FILE = "ubungo_graph.graphml"


# ---------------------------------------------------------------------------
# Map download / load
# ---------------------------------------------------------------------------

def haversine_m(lat1, lng1, lat2, lng2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _use_server(base):
    if hasattr(ox.settings, "overpass_url"):          # osmnx 2.x
        ox.settings.overpass_url = base + "/interpreter"
    elif hasattr(ox.settings, "overpass_endpoint"):   # osmnx 1.x
        ox.settings.overpass_endpoint = base
    try:
        ox.settings.requests_timeout = 60
    except Exception:
        pass


def build_graph():
    print(f"Downloading road network around {INTERSECTION_NAME} ...")
    last_error = None
    for base in OVERPASS_SERVERS:
        try:
            _use_server(base)
            print(f"  trying {base} ...")
            G = ox.graph_from_point(
                (INTERSECTION_LAT, INTERSECTION_LNG),
                dist=GRAPH_RADIUS_METERS,
                network_type="drive",
            )
            ox.save_graphml(G, GRAPH_FILE)
            print(f"Saved graph to {GRAPH_FILE} ({len(G.nodes)} nodes, {len(G.edges)} edges)")
            return G
        except Exception as e:
            last_error = e
            print(f"  failed: {type(e).__name__}")
    raise RuntimeError(
        "Could not download the map from any server (connection blocked). "
        f"Try a phone hotspot or another network. Last error: {type(last_error).__name__}")


def load_graph():
    if not Path(GRAPH_FILE).exists():
        raise RuntimeError(f"{GRAPH_FILE} not found. Run: python reroute.py --build-graph")
    return ox.load_graphml(GRAPH_FILE)


# ---------------------------------------------------------------------------
# Dijkstra weights
# ---------------------------------------------------------------------------

def _edge_length(edges):
    # MultiDiGraph: `edges` maps edge-key -> attributes; use the shortest parallel edge
    return min(d.get("length", 1.0) for d in edges.values())


def make_penalized_weight(zone):
    """Edge cost for the CONGESTED case: roads touching the junction zone cost 1000x."""
    def weight(u, v, edges):
        cost = _edge_length(edges)
        return cost * CONGESTION_PENALTY if (u in zone or v in zone) else cost
    return weight


def path_length(G, nodes):
    return sum(_edge_length(G[u][v]) for u, v in zip(nodes[:-1], nodes[1:]))


# ---------------------------------------------------------------------------
# Choose A and B so that the plain shortest path goes THROUGH the junction
# ---------------------------------------------------------------------------

def build_plan(G, center):
    clat, clng = G.nodes[center]["y"], G.nodes[center]["x"]
    dist = {n: haversine_m(clat, clng, d["y"], d["x"]) for n, d in G.nodes(data=True)}
    zone = {n for n, m in dist.items() if m <= ZONE_RADIUS_METERS}
    penalized = make_penalized_weight(zone)

    forward = nx.single_source_dijkstra_path_length(
        G, center, cutoff=ENDPOINT_MAX_METERS, weight="length")
    backward = nx.single_source_dijkstra_path_length(
        G.reverse(copy=False), center, cutoff=ENDPOINT_MAX_METERS, weight="length")
    origins = [n for n, d in backward.items() if d >= ENDPOINT_MIN_METERS and n not in zone]
    dests = [n for n, d in forward.items() if d >= ENDPOINT_MIN_METERS and n not in zone]
    if not origins or not dests:
        raise RuntimeError("No roads found 500-1000 m from the junction. "
                           "Check the coordinates, then run: python reroute.py --build-graph")

    k = math.cos(math.radians(clat))

    def xy(n):
        return ((G.nodes[n]["x"] - clng) * k, G.nodes[n]["y"] - clat)

    pairs = []
    for o in origins:
        ax, ay = xy(o)
        for d in dests:
            if o != d:
                bx, by = xy(d)
                pairs.append((math.hypot(ax - bx, ay - by), o, d))
    pairs.sort(reverse=True)   # widest apart first = opposite sides of the junction

    fallback = None
    for _, o, d in pairs[:MAX_PAIR_TRIES]:
        try:
            normal = nx.dijkstra_path(G, o, d, weight="length")
            detour = nx.dijkstra_path(G, o, d, weight=penalized)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
        if min(dist[n] for n in normal) > THROUGH_TOLERANCE_METERS:
            continue                      # the junction is not on the natural route A->B
        if any(n in zone for n in detour):
            continue                      # no way around the junction for this pair
        if path_length(G, detour) <= MAX_DETOUR_RATIO * path_length(G, normal):
            return {"G": G, "center": center, "zone": zone, "dist": dist,
                    "origin": o, "dest": d, "penalized": penalized}
        if fallback is None:
            fallback = {"G": G, "center": center, "zone": zone, "dist": dist,
                        "origin": o, "dest": d, "penalized": penalized}

    if fallback:
        return fallback
    raise RuntimeError(
        "Could not find a start and end point where the shortest path goes through the junction "
        "AND a detour around it exists. The saved map may not be centred on your marker. "
        "Run: python reroute.py --build-graph")


@lru_cache(maxsize=1)
def get_plan():
    G = load_graph()
    center = ox.distance.nearest_nodes(G, INTERSECTION_LNG, INTERSECTION_LAT)
    snapped = haversine_m(INTERSECTION_LAT, INTERSECTION_LNG,
                          G.nodes[center]["y"], G.nodes[center]["x"])
    if snapped > MAX_SNAP_METERS:
        raise RuntimeError(
            f"The saved map has no road within {MAX_SNAP_METERS} m of your marker "
            f"(closest is {snapped:.0f} m). It was built around a different point. "
            "Run: python reroute.py --build-graph")
    return build_plan(G, center)


# ---------------------------------------------------------------------------
# The route for the current congestion state
# ---------------------------------------------------------------------------

def route_for(plan, congested):
    G = plan["G"]
    weight = plan["penalized"] if congested else "length"
    nodes = nx.dijkstra_path(G, plan["origin"], plan["dest"], weight=weight)   # Dijkstra
    closest = min(plan["dist"][n] for n in nodes)
    pt = lambda n: {"lat": G.nodes[n]["y"], "lng": G.nodes[n]["x"]}
    return {
        "algorithm": "dijkstra",
        "intersection": {"name": INTERSECTION_NAME, "lat": INTERSECTION_LAT, "lng": INTERSECTION_LNG},
        "congested": bool(congested),
        "route": [pt(n) for n in nodes],
        "origin": pt(plan["origin"]),
        "destination": pt(plan["dest"]),
        "length_m": round(path_length(G, nodes)),
        "closest_approach_m": round(closest),
        "passes_through_intersection": closest <= THROUGH_TOLERANCE_METERS,
    }


def get_route(congested=False):
    """Called by liveserver.py for GET /api/route?congested=true|false"""
    return route_for(get_plan(), congested)


# ---------------------------------------------------------------------------
# Command line check
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Smooth Safari Phase 4 - Dijkstra rerouting")
    parser.add_argument("--build-graph", action="store_true",
                        help="Download the road map (first run, or after changing coordinates)")
    args = parser.parse_args()
    try:
        if args.build_graph:
            build_graph()
        plan = get_plan()
        free = route_for(plan, False)
        busy = route_for(plan, True)
    except RuntimeError as e:
        sys.exit(f"\nSTOPPED: {e}")

    print(f"\nNot congested: {free['length_m']} m, passes through the intersection: "
          f"{free['passes_through_intersection']} (closest approach {free['closest_approach_m']} m)")
    print(f"Congested    : {busy['length_m']} m, passes through the intersection: "
          f"{busy['passes_through_intersection']} (closest approach {busy['closest_approach_m']} m)")


if __name__ == "__main__":
    main()
