from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from raptor_engine import GTFSRaptorEngine

app = FastAPI(title="Guidy Transit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GTFS_PATH = r"C:\Users\Joeyyy\Downloads\Transit---GCR-Digital-Cairo-2017--master\GTFS\20180906_GTFSfullworking_Bus_Metro"

print("Booting up Guidy Backend...")
transit_engine = GTFSRaptorEngine(GTFS_PATH)
transit_engine.load_data()
print("Backend ready to receive coordinates!")

@app.get("/api/route")
def get_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float):
    """
    Calculates the fastest multi-modal route using GPS coordinates.
    The RAPTOR engine automatically handles the First/Last mile snapping.
    """
    try:
        result = transit_engine.run_raptor_by_coords(start_lat, start_lon, end_lat, end_lon)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Route calculation failed"))
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/health")
def health_check():
    return {"status": "ok"}