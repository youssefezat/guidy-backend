from fastapi import FastAPI
from routing import get_route_data, get_station_list

app = FastAPI(title="Guidy Full Stack Engine")

@app.get("/api/stations")
def fetch_stations():
    return {"stations": get_station_list()}

@app.get("/api/route")
def calculate_route(start: str, end: str):
    return get_route_data(start, end)