from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import sys

# Add parent directory to path to import simulation modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from simulation.analytical import compute_metrics

app = FastAPI(title="SPKLU Simulation API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimulationParams(BaseModel):
    c: int  # Number of chargers
    K: int  # Max capacity (chargers + waiting)
    lambda_rate: float  # Arrival rate (vehicles/hour)
    mu_rate: float  # Service rate (vehicles/hour)

@app.post("/api/metrics")
async def get_theoretical_metrics(params: SimulationParams):
    """
    Computes the theoretical M/M/c/K metrics based on the provided parameters.
    lambda_rate and mu_rate are expected in per-hour units, 
    but compute_metrics expects per-minute units if aligned with DES.
    We convert them to per-minute here.
    """
    if params.c <= 0 or params.K <= 0 or params.lambda_rate <= 0 or params.mu_rate <= 0:
        raise HTTPException(status_code=400, detail="All parameters must be positive integers/floats")
    
    if params.K < params.c:
        raise HTTPException(status_code=400, detail="K (capacity) must be >= c (chargers)")

    try:
        # Convert rates to per minute
        lam_min = params.lambda_rate / 60.0
        mu_min = params.mu_rate / 60.0

        metrics = compute_metrics(
            c=params.c,
            K=params.K,
            lam=lam_min,
            mu=mu_min
        )
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount the dashboard static files
dashboard_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
if os.path.exists(dashboard_path):
    app.mount("/", StaticFiles(directory=dashboard_path, html=True), name="dashboard")
