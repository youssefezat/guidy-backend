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
        
        # The true network graph for routing
        self.graph = defaultdict(set)

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
                self.stop_times[trip_id].append((stop_id, seq))

        print("Constructing Node Network...")
        for trip_id, st_list in self.stop_times.items():
            # Ensure stops are in the correct physical order
            st_list.sort(key=lambda x: x[1]) 
            route_id = self.trips.get(trip_id)
            if not route_id:
                continue
                
            for i in range(len(st_list) - 1):
                u = st_list[i][0]
                v = st_list[i+1][0]
                # Bidirectional edge mapping: (Neighbor_ID, Route_ID)
                self.graph[u].add((v, route_id))
                self.graph[v].add((u, route_id))

        print(f"Engine Ready. Mapped {len(self.graph)} interconnected transit nodes in {round(time.time() - start_time, 2)} seconds.")

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
        """Translates GTFS route types to UI hex colors."""
        if route_type == '1': return "#6DA4C2" # Metro Blue
        if route_type == '3': return "#E29578" # Bus Orange
        return "#D4A373"

    def _format_route_name(self, route_id):
        """Adds context and prioritizes descriptive route names over arbitrary numbers."""
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

    def _find_shortest_path(self, start_stop, end_stop):
        """Dijkstra Algorithm to find exact sequence of stations."""
        queue = [(0, start_stop, [])]
        visited = set()
        
        while queue:
            cost, current, path = heapq.heappop(queue)
            
            if current == end_stop:
                return path + [(current, None)]
                
            if current in visited:
                continue
            visited.add(current)
            
            for neighbor, route_id in self.graph[current]:
                if neighbor not in visited:
                    prev_route = path[-1][1] if path else None
                    penalty = 1 
                    
                    if prev_route and prev_route != route_id:
                        penalty += 10 
                    
                    heapq.heappush(queue, (cost + penalty, neighbor, path + [(current, route_id)]))
        return None

    def run_raptor_by_coords(self, start_lat, start_lon, end_lat, end_lon):
        calc_start_time = time.time()
        
        start_stop_id, start_walk_meters = self.find_nearest_stop(start_lat, start_lon)
        end_stop_id, end_walk_meters = self.find_nearest_stop(end_lat, end_lon)

        path = self._find_shortest_path(start_stop_id, end_stop_id)
        
        if not path:
            return {"success": False, "error": "No viable transit route found between these locations."}

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
        
        for i in range(len(path) - 1):
            curr_stop, route = path[i]
            next_stop = path[i+1][0]
            stop_info = self.stops[curr_stop]
            
            transit_points.append({"lat": stop_info['lat'], "lon": stop_info['lon']})
            station_markers.append({"lat": stop_info['lat'], "lon": stop_info['lon']})
            
            transit_distance += self._haversine(stop_info['lat'], stop_info['lon'], self.stops[next_stop]['lat'], self.stops[next_stop]['lon'])
            
            if route != current_route:
                if current_route is not None:
                    segments.append({"color": self._get_route_color(self.routes[current_route]['type']), "points": transit_points})
                    
                    instructions.append({
                        "title": "Transfer Station",
                        "subtitle": f"Change to {self._format_route_name(route)}",
                        "lat": stop_info['lat'], "lon": stop_info['lon'],
                        "station": stop_info['name']
                    })
                    transit_points = [{"lat": stop_info['lat'], "lon": stop_info['lon']}]
                else:
                    instructions.append({
                        "title": "Board Transit",
                        "subtitle": f"Take {self._format_route_name(route)}",
                        "lat": stop_info['lat'], "lon": stop_info['lon'],
                        "station": stop_info['name']
                    })
                current_route = route

        last_stop = path[-1][0]
        transit_points.append({"lat": self.stops[last_stop]['lat'], "lon": self.stops[last_stop]['lon']})
        station_markers.append({"lat": self.stops[last_stop]['lat'], "lon": self.stops[last_stop]['lon']})
        segments.append({"color": self._get_route_color(self.routes[current_route]['type']), "points": transit_points})
        
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

        total_time_mins = math.ceil((start_walk_meters / 80) + (len(path) * 2.5) + (end_walk_meters / 80))
        total_distance = round(start_walk_meters + transit_distance + end_walk_meters)

        return {
            "success": True,
            "backend_compute_time_ms": round((time.time() - calc_start_time) * 1000, 2),
            "options": [
                {
                    "type": "Optimal Route",
                    "desc": f"Transit via {self.stops[start_stop_id]['name']} to {self.stops[last_stop]['name']}",
                    "time": str(total_time_mins),
                    "traffic": "Medium",
                    "distance_m": total_distance
                }
            ],
            "segments": segments,
            "instructions": instructions,
            "station_markers": station_markers
        }

if __name__ == "__main__":
    engine = GTFSRaptorEngine(r"C:\Users\Joeyyy\Downloads\Transit---GCR-Digital-Cairo-2017--master\GTFS\20180906_GTFSfullworking_Bus_Metro") 
    engine.load_data()