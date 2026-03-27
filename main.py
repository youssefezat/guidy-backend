from fastapi import FastAPI

app = FastAPI(title="Guidy Routing Engine")

@app.get("/")
def read_root():
    return {"status": "Guidy Backend is Live!", "version": "1.0.0"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "transit_graph": "not_loaded"}