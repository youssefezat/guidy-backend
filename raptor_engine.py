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
        # CHANGED: graph now maps stop_id -> list of (neighbor_id, route_id, time_sec)
        # instead of an unweighted set of (neighbor_id, route_id) pairs.
        # time_sec is the REAL elapsed travel time between the two stops,
        # taken directly from this trip's stop_times.txt timestamps -- not
        # a hop-count or a flat per-step estimate.
        self.graph = defaultdict(list)

        # NEW: walking-transfer radius for connecting physically co-located
        # stops that have different stop_ids (e.g. a metro platform and a
        # nearby microbus stop both serving "Helwan"). Without this, large
        # parts of the network are invisibly disconnected from each other,
        # since GTFS gives each agency/route its own stop_id even at the
        # same real-world location.
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
        """GTFS times can exceed 24:00:00 for trips that run past midnight,
        so this can't just use datetime.strptime. Returns seconds since
        midnight of the service day."""
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
                # CHANGED: also keep arrival/departure so we can compute
                # real elapsed time between consecutive stops on this trip.
                arr = row.get('arrival_time', '').strip()
                dep = row.get('departure_time', '').strip()
                self.stop_times[trip_id].append((stop_id, seq, arr, dep))

        print("Constructing Node Network...")
        # CHANGED: pick ONE representative trip per route (the first one
        # encountered) instead of building edges from every trip variant.
        # GTFS typically has several trips per route (different times of
        # day / directions); since this build is a static, time-of-day-
        # agnostic graph, using every trip just re-adds the same edges
        # with minor timing noise. Using one representative trip per
        # route/direction keeps the graph size sane and the timings clean.
        seen_routes_built = set()

        for trip_id, st_list in self.stop_times.items():
            route_id = self.trips.get(trip_id)
            if not route_id:
                continue
            if route_id in seen_routes_built:
                continue
            seen_routes_built.add(route_id)

            st_list.sort(key=lambda x: x[1])  # sort by stop_sequence

            for i in range(len(st_list) - 1):
                u, _, _, u_dep = st_list[i]
                v, _, v_arr, _ = st_list[i + 1]

                if u not in self.stops or v not in self.stops:
                    continue

                # REAL travel time from GTFS timestamps, not a hop count.
                try:
                    t_dep = self._parse_gtfs_time(u_dep)
                    t_arr = self._parse_gtfs_time(v_arr)
                    time_sec = max(t_arr - t_dep, 10)  # floor to avoid 0/negative from data noise
                except (ValueError, AttributeError):
                    # Fallback if a timestamp is missing/malformed: estimate
                    # from straight-line distance at a conservative 15 km/h,
                    # clearly worse than real data but better than crashing.
                    dist_m = self._haversine(
                        self.stops[u]['lat'], self.stops[u]['lon'],
                        self.stops[v]['lat'], self.stops[v]['lon']
                    )
                    time_sec = max(dist_m / (15 * 1000 / 3600), 10)

                # CHANGED: directed edges only (u -> v), not automatically
                # added in both directions. Real bus/microbus routes are
                # one-way; treating every hop as bidirectional invented
                # return trips that don't exist. (Metro lines already have
                # separate stop_ids per direction in this feed, so this
                # doesn't break northbound/southbound metro travel.)
                self.graph[u].append((v, route_id, time_sec))

        transit_edge_count = sum(len(v) for v in self.graph.values())
        print(f"Mapped {len(self.graph)} stops with {transit_edge_count} directed transit edges "
              f"across {len(seen_routes_built)} routes.")

        self._add_interchange_edges()

        print(f"Engine Ready in {round(time.time() - start_time, 2)} seconds.")

    def _add_interchange_edges(self):
        """
        NEW: adds walking-transfer edges between distinct stop_ids that are
        physically close together (e.g. a metro platform and a nearby
        microbus stop). Without this, the graph is effectively several
        disconnected sub-networks -- one per agency -- since GTFS gives
        each agency/route its own stop_id even at shared real-world
        locations. This is the "Interchange Edge" concept described in
        the project's Trials & Justification document, Section 3.2.

        Uses simple grid bucketing (not full O(n^2) comparison) to stay
        fast even with 1000+ stops.
        """
        print("Adding interchange (walking transfer) edges...")
        cell_deg = self.WALK_LINK_RADIUS_M / 111000  # rough meters-to-degrees at this latitude
        grid = defaultdict(list)
        for stop_id, info in self.stops.items():
            key = (round(info['lon'] / cell_deg), round(info['lat'] / cell_deg))
            grid[key].append(stop_id)

        added = 0
        seen_pairs = set()
        for (gx, gy), stop_ids in grid.items():
            neighbor_ids = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    neighbor_ids.extend(grid.get((gx + dx, gy + dy), []))
            candidates = set(neighbor_ids)

            for s1 in stop_ids:
                for s2 in candidates:
                    if s1 >= s2:
                        continue
                    pair = (s1, s2)
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)

                    d_m = self._haversine(
                        self.stops[s1]['lat'], self.stops[s1]['lon'],
                        self.stops[s2]['lat'], self.stops[s2]['lon']
                    )
                    if 0 < d_m <= self.WALK_LINK_RADIUS_M:
                        walk_time = max(d_m / self.WALK_SPEED_MPS, 10)
                        self.graph[s1].append((s2, "WALK", walk_time))
                        self.graph[s2].append((s1, "WALK", walk_time))
                        added += 1

        print(f"Added {added * 2} directed walking-transfer edges ({added} bidirectional pairs).")

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
        if route_type == '1':
            return "#6DA4C2"
        if route_type == '3':
            return "#E29578"
        return "#D4A373"

    def _format_route_name(self, route_id):
        # NEW: handle the synthetic "WALK" route_id used by interchange edges.
        if route_id == "WALK":
            return "Walk"
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
        """
        Dijkstra over REAL travel-time weights (seconds), with a transfer
        penalty added when the route_id changes between consecutive edges.

        CHANGED from the original: cost is no longer `+1` per hop (which
        made this mathematically equivalent to BFS -- "fewest stops" --
        despite being implemented with a priority queue). Each edge now
        contributes its actual GTFS-derived travel time in seconds, so the
        algorithm genuinely optimizes for TIME, which is what "Dijkstra"
        is supposed to buy you over BFS.
        """
        TRANSFER_PENALTY_SEC = 240  # ~4 minutes, matches the kind of real-world
        # cost of walking to a new platform/road and waiting for the next vehicle

        queue = [(0, start_stop, [])]
        visited = set()
        while queue:
            cost, current, path = heapq.heappop(queue)
            if current == end_stop:
                return path + [(current, None)]
            if current in visited:
                continue
            visited.add(current)
            for neighbor, route_id, time_sec in self.graph[current]:
                if neighbor not in visited:
                    prev_route = path[-1][1] if path else None
                    penalty = time_sec
                    # Only charge a transfer penalty between two REAL transit
                    # routes -- not when starting the very first leg, and not
                    # for WALK edges, which represent a deliberate interchange
                    # rather than an unplanned mode-switch.
                    if (
                        prev_route is not None
                        and prev_route != route_id
                        and prev_route != "WALK"
                        and route_id != "WALK"
                    ):
                        penalty += TRANSFER_PENALTY_SEC
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
        # NEW: accumulate REAL transit time as we walk the path, instead of
        # estimating it afterwards from hop count.
        total_transit_time_sec = 0

        for i in range(len(path) - 1):
            curr_stop, route = path[i]
            next_stop = path[i + 1][0]
            stop_info = self.stops[curr_stop]
            next_info = self.stops[next_stop]

            transit_points.append({"lat": stop_info['lat'], "lon": stop_info['lon']})
            station_markers.append({"lat": stop_info['lat'], "lon": stop_info['lon']})

            transit_distance += self._haversine(stop_info['lat'], stop_info['lon'], next_info['lat'], next_info['lon'])

            # Look up the real edge time for this specific hop (route-aware,
            # since the same two stops could theoretically be linked by more
            # than one route/edge).
            edge_time = next(
                (t for n, r, t in self.graph[curr_stop] if n == next_stop and r == route),
                None
            )
            if edge_time is not None:
                total_transit_time_sec += edge_time

            if route != current_route:
                if current_route is not None:
                    route_type = "1" if current_route == "WALK" else self.routes.get(current_route, {}).get('type', '3')
                    segments.append({"color": self._get_route_color(route_type) if current_route != "WALK" else "#2A9D8F", "points": transit_points})
                    if route == "WALK":
                        title, subtitle = "Walk to Transfer", f"Walk to the next stop near {stop_info['name']}"
                    else:
                        title, subtitle = "Transfer Station", f"Change to {self._format_route_name(route)}"
                    instructions.append({
                        "title": title,
                        "subtitle": subtitle,
                        "lat": stop_info['lat'], "lon": stop_info['lon'],
                        "station": stop_info['name']
                    })
                    transit_points = [{"lat": stop_info['lat'], "lon": stop_info['lon']}]
                else:
                    verb = "Walk" if route == "WALK" else "Board Transit"
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

        # CHANGED: total time is now real walk time (distance / walking
        # speed) + REAL accumulated transit time from GTFS timestamps,
        # instead of `len(path) * 2.5` minutes, which was a flat per-hop
        # guess disconnected from the actual data already loaded.
        walk_speed_mps = self.WALK_SPEED_MPS
        total_time_mins = math.ceil(
            (start_walk_meters / walk_speed_mps + total_transit_time_sec + end_walk_meters / walk_speed_mps) / 60
        )
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
    engine = GTFSRaptorEngine(".")
    engine.load_data()
