import csv
from collections import defaultdict
import time
import math
import heapq

class GTFSRaptorEngine:
    def __init__(self, gtfs_folder_path):
        self.folder = gtfs_folder_path
        self.stops = {}
        self.routes = {}
        self.trips = {}
        self.stop_times = defaultdict(list)
        self.graph = defaultdict(list)

        self.WALK_LINK_RADIUS_M = 350
        self.WALK_SPEED_MPS = 1.25  # ~4.5 km/h

    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def _parse_gtfs_time(t):
        h, m, s = (int(x) for x in t.strip().split(':'))
        return h * 3600 + m * 60 + s

    def load_data(self):
        print("Ingesting GTFS Data & Building Network Graph...")
        start_time = time.time()

        with open(f"{self.folder}/stops.txt", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.stops[row['stop_id']] = {
                    'name': row['stop_name'],
                    'lat': float(row['stop_lat']),
                    'lon': float(row['stop_lon'])
                }

        with open(f"{self.folder}/routes.txt", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.routes[row['route_id']] = {
                    'short_name': row.get('route_short_name', ''),
                    'long_name': row.get('route_long_name', ''),
                    'type': str(row['route_type']).strip()
                }

        with open(f"{self.folder}/trips.txt", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.trips[row['trip_id']] = row['route_id']

        with open(f"{self.folder}/stop_times.txt", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trip_id = row['trip_id']
                stop_id = row['stop_id']
                seq = int(row['stop_sequence'])
                arr = row.get('arrival_time', '').strip()
                dep = row.get('departure_time', '').strip()
                self.stop_times[trip_id].append((stop_id, seq, arr, dep))

        seen_edges = set()
        for trip_id, st_list in self.stop_times.items():
            route_id = self.trips.get(trip_id)
            if not route_id: continue
            st_list.sort(key=lambda x: x[1])

            for i in range(len(st_list) - 1):
                u, _, _, u_dep = st_list[i]
                v, _, v_arr, _ = st_list[i + 1]

                if u not in self.stops or v not in self.stops: continue

                edge_key = (u, v, route_id)
                if edge_key in seen_edges: continue
                
                try:
                    t_dep = self._parse_gtfs_time(u_dep)
                    t_arr = self._parse_gtfs_time(v_arr)
                    time_sec = max(t_arr - t_dep, 10) 
                except (ValueError, AttributeError):
                    dist_m = self._haversine(
                        self.stops[u]['lat'], self.stops[u]['lon'],
                        self.stops[v]['lat'], self.stops[v]['lon']
                    )
                    time_sec = max(dist_m / (15 * 1000 / 3600), 10)

                seen_edges.add(edge_key)
                self.graph[u].append((v, route_id, time_sec))
                
                edge_key_rev = (v, u, route_id)
                if edge_key_rev not in seen_edges:
                    seen_edges.add(edge_key_rev)
                    self.graph[v].append((u, route_id, time_sec))

        self._add_interchange_edges()
        print(f"Engine Ready in {round(time.time() - start_time, 2)} seconds.")

    def _add_interchange_edges(self):
        cell_deg = self.WALK_LINK_RADIUS_M / 111000 
        grid = defaultdict(list)
        for stop_id, info in self.stops.items():
            key = (round(info['lon'] / cell_deg), round(info['lat'] / cell_deg))
            grid[key].append(stop_id)

        seen_pairs = set()
        for (gx, gy), stop_ids in grid.items():
            neighbor_ids = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    neighbor_ids.extend(grid.get((gx + dx, gy + dy), []))
            candidates = set(neighbor_ids)

            for s1 in stop_ids:
                for s2 in candidates:
                    if s1 >= s2: continue
                    pair = (s1, s2)
                    if pair in seen_pairs: continue
                    seen_pairs.add(pair)

                    d_m = self._haversine(
                        self.stops[s1]['lat'], self.stops[s1]['lon'],
                        self.stops[s2]['lat'], self.stops[s2]['lon']
                    )
                    if 0 < d_m <= self.WALK_LINK_RADIUS_M:
                        walk_time = max(d_m / self.WALK_SPEED_MPS, 10)
                        self.graph[s1].append((s2, "WALK", walk_time))
                        self.graph[s2].append((s1, "WALK", walk_time))

    def find_nearest_stop(self, lat, lon):
        min_distance = float('inf')
        nearest_stop_id = None
        for stop_id, data in self.stops.items():
            dist = self._haversine(lat, lon, data['lat'], data['lon'])
            if dist < min_distance:
                min_distance = dist
                nearest_stop_id = stop_id
        return nearest_stop_id, min_distance

    def _get_route_color(self, route_type):
        if route_type == '1': return "#6DA4C2"
        if route_type == '3': return "#E29578"
        return "#D4A373"

    def _format_route_name(self, route_id):
        if route_id == "WALK": return "Walk"
        route = self.routes[route_id]
        short_name = route['short_name']
        long_name = route['long_name']
        rtype = route['type']
        if rtype == '1':
            name_to_use = short_name if short_name else long_name
            if "Line" not in name_to_use and "line" not in name_to_use.lower():
                return f"Metro Line {name_to_use}"
            return f"Metro {name_to_use}"
        elif rtype == '3':
            if long_name and len(long_name) > 3:
                return f"Bus towards {long_name.replace('-', ' to ')}"
            elif short_name:
                return f"Bus Route {short_name}"
        return long_name if long_name else short_name

    # THE FIX: MULTI-CRITERIA PATHFINDING
    def _find_shortest_path(self, start_stop, end_stop, profile="fastest"):
        # Default Weights
        TRANSFER_PENALTY_SEC = 240 
        WALK_PENALTY_MULT = 1.0
        METRO_PENALTY_SEC = 0
        
        # Adjust weights to force the algorithm down different physical paths
        if profile == "regular":
            TRANSFER_PENALTY_SEC = 900 # Heavily penalize transfers to force single-seat bus rides
            WALK_PENALTY_MULT = 1.5 
        elif profile == "cheapest":
            METRO_PENALTY_SEC = 1200 # Add artificial 20-min delay to Metro to force surface transport

        queue = [(0, start_stop, [])]
        visited = set()
        
        while queue:
            cost, current, path = heapq.heappop(queue)
            if current == end_stop:
                return path + [(current, None)], cost
            
            if current in visited: continue
            visited.add(current)
            
            for neighbor, route_id, time_sec in self.graph[current]:
                if neighbor not in visited:
                    prev_route = path[-1][1] if path else None
                    
                    actual_time = time_sec
                    if route_id == "WALK":
                        actual_time *= WALK_PENALTY_MULT
                    
                    penalty = actual_time
                    
                    if route_id != "WALK":
                        rtype = self.routes.get(route_id, {}).get('type', '3')
                        if rtype == '1':
                            penalty += METRO_PENALTY_SEC

                    if (prev_route is not None and prev_route != route_id 
                        and prev_route != "WALK" and route_id != "WALK"):
                        penalty += TRANSFER_PENALTY_SEC
                        
                    heapq.heappush(queue, (cost + penalty, neighbor, path + [(current, route_id)]))
        return None, 0

    def _build_option_data(self, path, profile_type, start_stop_id, start_lat, start_lon, end_lat, end_lon, start_walk_meters, end_walk_meters):
        segments = []
        instructions = []
        station_markers = []

        segments.append({
            "color": "#83C5BE",
            "points": [{"lat": start_lat, "lon": start_lon}, {"lat": self.stops[start_stop_id]['lat'], "lon": self.stops[start_stop_id]['lon']}]
        })
        instructions.append({
            "title": "Walk to Station",
            "subtitle": f"Walk {round(start_walk_meters)}m to {self.stops[start_stop_id]['name']}",
            "lat": start_lat, "lon": start_lon,
            "station": self.stops[start_stop_id]['name']
        })

        current_route = None
        transit_points = []
        transit_distance = 0
        total_transit_time_sec = 0
        
        metro_stops = 0
        bus_boardings = 0
        boarded_routes = set()

        for i in range(len(path) - 1):
            curr_stop, route = path[i]
            next_stop = path[i + 1][0]
            stop_info = self.stops[curr_stop]
            next_info = self.stops[next_stop]

            transit_points.append({"lat": stop_info['lat'], "lon": stop_info['lon']})
            station_markers.append({"lat": stop_info['lat'], "lon": stop_info['lon']})

            transit_distance += self._haversine(stop_info['lat'], stop_info['lon'], next_info['lat'], next_info['lon'])

            edge_time = next((t for n, r, t in self.graph[curr_stop] if n == next_stop and r == route), 10)
            total_transit_time_sec += edge_time

            if route != "WALK":
                route_type = self.routes.get(route, {}).get('type', '3')
                if route_type == '1': metro_stops += 1
                elif route not in boarded_routes:
                    bus_boardings += 1
                    boarded_routes.add(route)

            if route != current_route:
                if current_route is not None:
                    route_type = "1" if current_route == "WALK" else self.routes.get(current_route, {}).get('type', '3')
                    segments.append({"color": self._get_route_color(route_type) if current_route != "WALK" else "#2A9D8F", "points": transit_points})
                    if route == "WALK":
                        title, subtitle = "Walk to Transfer", f"Walk to the next stop near {stop_info['name']}"
                    else:
                        title, subtitle = "Transfer Station", f"Change to {self._format_route_name(route)}"
                    instructions.append({
                        "title": title, "subtitle": subtitle,
                        "lat": stop_info['lat'], "lon": stop_info['lon'],
                        "station": stop_info['name']
                    })
                    transit_points = [{"lat": stop_info['lat'], "lon": stop_info['lon']}]
                else:
                    action = self._format_route_name(route) if route != "WALK" else "to the next stop"
                    instructions.append({
                        "title": "Walk" if route == "WALK" else "Board Transit",
                        "subtitle": f"Continue {action}" if route == "WALK" else f"Take {action}",
                        "lat": stop_info['lat'], "lon": stop_info['lon'],
                        "station": stop_info['name']
                    })
                current_route = route

        last_stop = path[-1][0]
        transit_points.append({"lat": self.stops[last_stop]['lat'], "lon": self.stops[last_stop]['lon']})
        station_markers.append({"lat": self.stops[last_stop]['lat'], "lon": self.stops[last_stop]['lon']})
        last_route_type = "1" if current_route == "WALK" else self.routes.get(current_route, {}).get('type', '3')
        segments.append({"color": self._get_route_color(last_route_type) if current_route != "WALK" else "#2A9D8F", "points": transit_points})
        
        instructions.append({
            "title": "Arrive & Disembark",
            "subtitle": f"Get off at {self.stops[last_stop]['name']}",
            "lat": self.stops[last_stop]['lat'], "lon": self.stops[last_stop]['lon'],
            "station": self.stops[last_stop]['name']
        })

        segments.append({
            "color": "#83C5BE",
            "points": [{"lat": self.stops[last_stop]['lat'], "lon": self.stops[last_stop]['lon']}, {"lat": end_lat, "lon": end_lon}]
        })
        instructions.append({
            "title": "Walk to Destination",
            "subtitle": f"Walk {round(end_walk_meters)}m to your destination",
            "lat": end_lat, "lon": end_lon,
            "station": "Destination"
        })

        total_time_mins = math.ceil((start_walk_meters / self.WALK_SPEED_MPS + total_transit_time_sec + end_walk_meters / self.WALK_SPEED_MPS) / 60)
        total_distance = round(start_walk_meters + transit_distance + end_walk_meters)

        metro_fare = 0
        if metro_stops > 0:
            if metro_stops <= 9: metro_fare = 10
            elif metro_stops <= 16: metro_fare = 12
            elif metro_stops <= 23: metro_fare = 15
            else: metro_fare = 20

        bus_fare = bus_boardings * 14
        base_price = max(10, metro_fare + bus_fare)
        
        traffic = "Low"
        if bus_boardings > 0: traffic = "Medium"
        if bus_boardings > 1 and metro_stops == 0: traffic = "High"

        # Tiers Formatting
        if profile_type == "fastest":
            price_str = f"{base_price + 5} EGP"
            desc = f"Premium via {self.stops[start_stop_id]['name']}"
        elif profile_type == "regular":
            total_time_mins = math.ceil(total_time_mins * 1.15)
            price_str = f"{base_price} EGP"
            desc = f"Standard via {self.stops[start_stop_id]['name']}"
        else: 
            total_time_mins = math.ceil(total_time_mins * 1.3)
            price_str = f"{max(10, base_price - 5)} EGP"
            desc = f"Economy via {self.stops[start_stop_id]['name']}"

        return {
            "type": profile_type.capitalize(),
            "desc": desc,
            "time": str(total_time_mins),
            "price": price_str,
            "traffic": traffic,
            "distance_m": total_distance,
            "segments": segments,
            "instructions": instructions,
            "station_markers": station_markers
        }

    def run_raptor_by_coords(self, start_lat, start_lon, end_lat, end_lon):
        calc_start_time = time.time()
        start_stop_id, start_walk_meters = self.find_nearest_stop(start_lat, start_lon)
        end_stop_id, end_walk_meters = self.find_nearest_stop(end_lat, end_lon)

        # Run Dijkstra 3 times with different weights
        profiles = ["fastest", "regular", "cheapest"]
        options = []
        
        for p in profiles:
            path, _ = self._find_shortest_path(start_stop_id, end_stop_id, profile=p)
            if path:
                opt = self._build_option_data(path, p, start_stop_id, start_lat, start_lon, end_lat, end_lon, start_walk_meters, end_walk_meters)
                options.append(opt)

        if not options:
            return {"success": False, "error": "No viable transit route found between these locations."}
            
        return {
            "success": True,
            "backend_compute_time_ms": round((time.time() - calc_start_time) * 1000, 2),
            "options": options
        }

if __name__ == "__main__":
    engine = GTFSRaptorEngine(".")
    engine.load_data()