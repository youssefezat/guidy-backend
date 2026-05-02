import requests

# 1. THE COMPLETE METRO DATABASE (Coords: [Longitude, Latitude])
STATIONS = {
    # LINE 1 (Red Line)
    "New El-Marg": {"coords": [31.3360, 30.1500], "lines": [1]},
    "El-Marg": {"coords": [31.3340, 30.1430], "lines": [1]},
    "Ain Shams": {"coords": [31.3250, 30.1330], "lines": [1]},
    "Saray El-Qobba": {"coords": [31.3090, 30.0980], "lines": [1]},
    "Ghamra": {"coords": [31.2720, 30.0670], "lines": [1]},
    "Al Shohadaa": {"coords": [31.2464, 30.0611], "lines": [1, 2]}, 
    "Orabi": {"coords": [31.2420, 30.0570], "lines": [1]},
    "Nasser": {"coords": [31.2398, 30.0524], "lines": [1, 3]},      
    "Sadat": {"coords": [31.2357, 30.0444], "lines": [1, 2]},       
    "Saad Zaghloul": {"coords": [31.2370, 30.0350], "lines": [1]},
    "Al-Sayeda Zeinab": {"coords": [31.2360, 30.0300], "lines": [1]},
    "Mar Girgis": {"coords": [31.2300, 30.0060], "lines": [1]},
    "Maadi": {"coords": [31.2585, 29.9602], "lines": [1]},
    "Tora El-Balad": {"coords": [31.2750, 29.9370], "lines": [1]},
    "Helwan University": {"coords": [31.3190, 29.8650], "lines": [1]},
    "Helwan": {"coords": [31.3341, 29.8488], "lines": [1]},

    # LINE 2 (Yellow Line)
    "Shubra El-Kheima": {"coords": [31.2440, 30.1220], "lines": [2]},
    "St. Teresa": {"coords": [31.2460, 30.0920], "lines": [2]},
    "Massara": {"coords": [31.2460, 30.0710], "lines": [2]},
    "Attaba": {"coords": [31.2475, 30.0531], "lines": [2, 3]},      
    "Mohamed Naguib": {"coords": [31.2430, 30.0450], "lines": [2]},
    "Opera": {"coords": [31.2238, 30.0416], "lines": [2]},
    "Dokki": {"coords": [31.2117, 30.0384], "lines": [2]},
    "El Bohoth": {"coords": [31.2010, 30.0360], "lines": [2]},
    "Cairo University": {"coords": [31.2089, 30.0276], "lines": [2, 3]}, 
    "Giza": {"coords": [31.2080, 30.0130], "lines": [2]},
    "El Mounib": {"coords": [31.2110, 29.9810], "lines": [2]},

    # LINE 3 (Green Line)
    "Adly Mansour": {"coords": [31.4200, 30.1460], "lines": [3]},
    "El-Nozha": {"coords": [31.3500, 30.1280], "lines": [3]},
    "Heliopolis": {"coords": [31.3256, 30.0911], "lines": [3]},
    "Stadium (Nasr City)": {"coords": [31.3142, 30.0736], "lines": [3]},
    "Fair Zone": {"coords": [31.3020, 30.0710], "lines": [3]},
    "Abbasiya": {"coords": [31.2820, 30.0650], "lines": [3]},
    "Maspero": {"coords": [31.2320, 30.0540], "lines": [3]},
    "Safaa Hegazy (Zamalek)": {"coords": [31.2217, 30.0626], "lines": [3]},
    "Kit Kat": {"coords": [31.2110, 30.0680], "lines": [3]},
    "Imbaba": {"coords": [31.2050, 30.0820], "lines": [3]},
}

# 2. THE METRO TUNNEL GRAPH (Mathematical connections)
GRAPH = {
    # Line 1 Connections
    "New El-Marg": ["El-Marg"],
    "El-Marg": ["New El-Marg", "Ain Shams"],
    "Ain Shams": ["El-Marg", "Saray El-Qobba"],
    "Saray El-Qobba": ["Ain Shams", "Ghamra"],
    "Ghamra": ["Saray El-Qobba", "Al Shohadaa"],
    "Al Shohadaa": ["Ghamra", "Orabi", "Massara", "Attaba"], 
    "Orabi": ["Al Shohadaa", "Nasser"],
    "Nasser": ["Orabi", "Sadat", "Attaba", "Maspero"],
    "Sadat": ["Nasser", "Saad Zaghloul", "Mohamed Naguib", "Opera"],
    "Saad Zaghloul": ["Sadat", "Al-Sayeda Zeinab"],
    "Al-Sayeda Zeinab": ["Saad Zaghloul", "Mar Girgis"],
    "Mar Girgis": ["Al-Sayeda Zeinab", "Maadi"],
    "Maadi": ["Mar Girgis", "Tora El-Balad"],
    "Tora El-Balad": ["Maadi", "Helwan University"],
    "Helwan University": ["Tora El-Balad", "Helwan"],
    "Helwan": ["Helwan University"],

    # Line 2 Connections
    "Shubra El-Kheima": ["St. Teresa"],
    "St. Teresa": ["Shubra El-Kheima", "Massara"],
    "Massara": ["St. Teresa", "Al Shohadaa"],
    "Attaba": ["Al Shohadaa", "Mohamed Naguib", "Abbasiya", "Nasser"],
    "Mohamed Naguib": ["Attaba", "Sadat"],
    "Opera": ["Sadat", "Dokki"],
    "Dokki": ["Opera", "El Bohoth"],
    "El Bohoth": ["Dokki", "Cairo University"],
    "Cairo University": ["El Bohoth", "Giza", "Kit Kat"],
    "Giza": ["Cairo University", "El Mounib"],
    "El Mounib": ["Giza"],

    # Line 3 Connections
    "Adly Mansour": ["El-Nozha"],
    "El-Nozha": ["Adly Mansour", "Heliopolis"],
    "Heliopolis": ["El-Nozha", "Stadium (Nasr City)"],
    "Stadium (Nasr City)": ["Heliopolis", "Fair Zone"],
    "Fair Zone": ["Stadium (Nasr City)", "Abbasiya"],
    "Abbasiya": ["Fair Zone", "Attaba"],
    "Maspero": ["Nasser", "Safaa Hegazy (Zamalek)"],
    "Safaa Hegazy (Zamalek)": ["Maspero", "Kit Kat"],
    "Kit Kat": ["Safaa Hegazy (Zamalek)", "Imbaba", "Cairo University"],
    "Imbaba": ["Kit Kat"],
}

LINE_COLORS = { 1: "#E53935", 2: "#FBC02D", 3: "#43A047" }
TOMTOM_API_KEY = "TGdfupFh9oOJH4XQj2uAfBTh4hmEsyis"

def get_station_list():
    return list(STATIONS.keys())

def find_shortest_path(start, end):
    queue = [[start]]
    visited = set()
    
    while queue:
        path = queue.pop(0)
        node = path[-1]
        if node == end:
            return path
        if node not in visited:
            for adjacent in GRAPH.get(node, []):
                new_path = list(path)
                new_path.append(adjacent)
                queue.append(new_path)
            visited.add(node)
    return []

def get_route_data(start_name: str, end_name: str):
    if start_name not in STATIONS or end_name not in STATIONS:
        return {"success": False, "error": "Station not found."}

    station_path = find_shortest_path(start_name, end_name)
    if not station_path:
        return {"success": False, "error": "No route possible."}

    station_markers = [{"lat": STATIONS[s]["coords"][1], "lon": STATIONS[s]["coords"][0], "name": s} for s in station_path]

    instructions = []
    current_line = None
    transfers = 0
    
    # NEW: We need to track the specific line for every single step between stations
    step_lines = []

    for i in range(len(station_path) - 1):
        station1 = station_path[i]
        station2 = station_path[i+1]
        
        lines1 = set(STATIONS[station1]["lines"])
        lines2 = set(STATIONS[station2]["lines"])
        common_lines = list(lines1.intersection(lines2))
        best_line = common_lines[0] 
        
        # Save the line for this specific segment of the journey
        step_lines.append(best_line)
        
        if current_line is None:
            current_line = best_line
            instructions.append({
                "title": f"Board Line {current_line}", 
                "subtitle": f"Start at {station1}", 
                "station": station1,
                "lat": STATIONS[station1]["coords"][1],
                "lon": STATIONS[station1]["coords"][0]
            })
        elif current_line not in common_lines:
            current_line = common_lines[0]
            transfers += 1
            instructions.append({
                "title": f"Transfer to Line {current_line}", 
                "subtitle": f"Get off at {station1}", 
                "station": station1,
                "lat": STATIONS[station1]["coords"][1],
                "lon": STATIONS[station1]["coords"][0]
            })

    end_station = station_path[-1]
    instructions.append({
        "title": "Arrive at Destination", 
        "subtitle": f"Exit at {end_station}", 
        "station": end_station,
        "lat": STATIONS[end_station]["coords"][1],
        "lon": STATIONS[end_station]["coords"][0]
    })

    main_color = LINE_COLORS.get(STATIONS[start_name]["lines"][0], "#6DA4C2")
    estimated_time = len(station_path) * 3 

    waypoint_str = ":".join([f"{STATIONS[s]['coords'][1]},{STATIONS[s]['coords'][0]}" for s in station_path])
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{waypoint_str}/json"
    
    params = {
        "key": TOMTOM_API_KEY,
        "routeType": "fastest",
        "traffic": "false" 
    }

    # NEW: We are replacing a single path with a list of multi-colored segments
    segments = []
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "routes" in data and len(data["routes"]) > 0:
            # TomTom returns a "leg" for every waypoint interval. 
            # We map leg[0] to step_lines[0], leg[1] to step_lines[1], etc.
            for i, leg in enumerate(data["routes"][0]["legs"]):
                leg_line = step_lines[i]
                leg_color = LINE_COLORS.get(leg_line, "#6DA4C2")
                leg_points = [{"lat": p["latitude"], "lon": p["longitude"]} for p in leg["points"]]
                segments.append({
                    "color": leg_color,
                    "points": leg_points
                })
        else:
            raise Exception("No TomTom routes found.")
            
    except Exception as e:
        # Fallback to straight lines, but STILL keep the multi-colors!
        for i in range(len(station_path) - 1):
            s1 = station_path[i]
            s2 = station_path[i+1]
            leg_line = step_lines[i]
            leg_color = LINE_COLORS.get(leg_line, "#6DA4C2")
            leg_points = [
                {"lat": STATIONS[s1]["coords"][1], "lon": STATIONS[s1]["coords"][0]},
                {"lat": STATIONS[s2]["coords"][1], "lon": STATIONS[s2]["coords"][0]}
            ]
            segments.append({
                "color": leg_color,
                "points": leg_points
            })

    return {
        "success": True,
        "segments": segments, # Sending the colored chunks to Flutter
        "station_markers": station_markers, 
        "color": main_color,  # Keep main color for UI elements
        "instructions": instructions,
        "options": [
            {
                "type": "Fastest Metro Path", 
                "time": estimated_time, 
                "traffic": "Low", 
                "desc": f"{len(station_path)-1} stops • {transfers} transfers"
            }
        ]
    }