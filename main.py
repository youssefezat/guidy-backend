from fastapi import FastAPI
from routing import get_shortest_path

app = FastAPI(title="Guidy Routing Engine")

@app.get("/")
def read_root():
    return {"status": "Guidy Backend is Live!", "version": "1.0.0"}

@app.get("/api/route")
def calculate_route(start: str, end: str):
    """
    Example usage: /api/route?start=Opera&end=Al Shohadaa
    """
    result = get_shortest_path(start, end)
    return result