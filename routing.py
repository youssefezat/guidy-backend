import networkx as nx

# Initialize our transit network graph
transit_graph = nx.Graph()

# 1. Add Nodes (Metro Stations with exact Lat/Lon coordinates)
transit_graph.add_node("Sadat", lat=30.0444, lon=31.2357)
transit_graph.add_node("Al Shohadaa", lat=30.0611, lon=31.2464)
transit_graph.add_node("Attaba", lat=30.0531, lon=31.2475)
transit_graph.add_node("Opera", lat=30.0416, lon=31.2238)

# 2. Add Edges (Connections between stations, weight = travel time in minutes)
transit_graph.add_edge("Sadat", "Al Shohadaa", weight=5)
transit_graph.add_edge("Sadat", "Opera", weight=2)
transit_graph.add_edge("Al Shohadaa", "Attaba", weight=3)
transit_graph.add_edge("Sadat", "Attaba", weight=4) 

def get_shortest_path(start_station: str, end_station: str):
    """Calculates the fastest route using Dijkstra's algorithm (built into NetworkX)."""
    try:
        # Find the path
        path = nx.shortest_path(transit_graph, source=start_station, target=end_station, weight="weight")
        # Calculate total travel time
        total_time = nx.shortest_path_length(transit_graph, source=start_station, target=end_station, weight="weight")
        
        # Package the result with coordinates for the Flutter map
        route_details = []
        for station in path:
            node_data = transit_graph.nodes[station]
            route_details.append({
                "station": station,
                "lat": node_data["lat"],
                "lon": node_data["lon"]
            })
            
        return {"success": True, "path": route_details, "total_time_minutes": total_time}
        
    except nx.NetworkXNoPath:
        return {"success": False, "error": "No path found."}
    except nx.NodeNotFound:
        return {"success": False, "error": "Station not found in network."}