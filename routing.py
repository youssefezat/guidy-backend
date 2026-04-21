import requests

# Source of Truth: Station/Location coordinates [Longitude, Latitude]
STATIONS = {
    # Original Metro Stations
    "Opera": {"coords": [31.2238, 30.0416], "line": 2},
    "Sadat": {"coords": [31.2357, 30.0444], "line": 2}, 
    "Attaba": {"coords": [31.2475, 30.0531], "line": 2},
    "Al Shohadaa": {"coords": [31.2464, 30.0611], "line": 2},
    "Dokki": {"coords": [31.2117, 30.0384], "line": 2},
    "Helwan": {"coords": [31.3341, 29.8488], "line": 1},
    
    # New Locations added from Frontend Recent Searches & Autocomplete
    "Zamalek": {"coords": [31.2217, 30.0626], "line": 3},
    "Nasr City": {"coords": [31.3283, 30.0626], "line": 3},
    "Downtown Cairo": {"coords": [31.2353, 30.0478], "line": 2},
    "Heliopolis": {"coords": [31.3198, 30.0911], "line": 3},
    "Maadi": {"coords": [31.2585, 29.9602], "line": 1},
    "New Cairo": {"coords": [31.4700, 30.0300], "line": 0}, # 0 represents standard road/bus
    "Ramses Station": {"coords": [31.2474, 30.0636], "line": 1},
    "Cairo University": {"coords": [31.2089, 30.0276], "line": 2},
    "October City": {"coords": [29.9245, 29.9717], "line": 0},
    "Sheikh Zayed": {"coords": [29.9863, 30.0321], "line": 0},
}

# Branding colors based on the Metro Lines
LINE_COLORS = {
    0: "#808080", # Grey for areas without Metro
    1: "#FF0000", # Red Line
    2: "#FFD700", # Yellow Line
    3: "#00FF00", # Green Line
}

def get_station_list():
    return list(STATIONS.keys())

def get_route_data(start_name: str, end_name: str):
    if start_name not in STATIONS or end_name not in STATIONS:
        return {"success": False, "error": f"Backend Error: {start_name} or {end_name} not found in database."}

    start_data = STATIONS[start_name]
    end_data = STATIONS[end_name]
    
    # Logic to determine line color based on start/end points
    line_id = 1 if (start_data["line"] == 1 or end_data["line"] == 1) else 2
    if start_data["line"] == 0 or end_data["line"] == 0:
        line_id = 0
    elif start_data["line"] == 3 or end_data["line"] == 3:
        line_id = 3
        
    route_color = LINE_COLORS.get(line_id, "#6DA4C2")

    # OSRM API Call for the real road/track geometry
    url = f"http://router.project-osrm.org/route/v1/driving/{start_data['coords'][0]},{start_data['coords'][1]};{end_data['coords'][0]},{end_data['coords'][1]}?overview=full&geometries=geojson"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data["code"] != "Ok":
            return {"success": False, "error": "OSRM Routing Error."}

        raw_coords = data["routes"][0]["geometry"]["coordinates"]
        full_path = [{"lat": c[1], "lon": c[0]} for c in raw_coords]
        
        # Calculate duration
        duration = data["routes"][0]["duration"]
        
        return {
            "success": True,
            "path": full_path,
            "color": route_color,
            "options": [
                {"type": "Fastest", "time": round(duration/60), "price": "7 EGP", "desc": "Optimized by ACO"},
                {"type": "Cheapest", "time": round((duration/60)*1.2), "price": "5 EGP", "desc": "Standard Route"},
                {"type": "Regular", "time": round((duration/60)*1.1), "price": "7 EGP", "desc": "Most Common"}
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}