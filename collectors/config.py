"""
Configuration management for the SPKLU data collection pipeline.

Loads environment variables from .env, defines API endpoints,
Yogyakarta region boundaries, rate-limiting defaults, and export paths.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from the project root (two levels up from this file)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# API keys & database URL
# ---------------------------------------------------------------------------
OCM_API_KEY: Optional[str] = os.getenv("OCM_API_KEY")
GMAPS_API_KEY: Optional[str] = os.getenv("GMAPS_API_KEY")
DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
PETASPKLU_API_URL: str = "https://petaspklu.id/api/v1/spklu/all"
OCM_API_URL: str = "https://api.openchargemap.io/v3/poi/"


# ---------------------------------------------------------------------------
# Rate-limiting defaults
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT_SECONDS: int = 120
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_BACKOFF_BASE: float = 2.0  # seconds – exponential backoff base
DEFAULT_REQUEST_DELAY: float = 1.0  # seconds between sequential requests


# ---------------------------------------------------------------------------
# HTTP client defaults
# ---------------------------------------------------------------------------
DEFAULT_USER_AGENT: str = (
    "SPKLU-DataCollector/1.0 "
    "(EV Charging Simulation Research; Python/httpx)"
)


# ---------------------------------------------------------------------------
# Yogyakarta region definitions
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RegionBoundingBox:
    """Axis-aligned bounding box for a geographic region."""

    name: str
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float
    center_lat: float
    center_lng: float

    def contains(self, lat: float, lng: float) -> bool:
        """Return True if the point falls inside this bounding box."""
        return (
            self.min_lat <= lat <= self.max_lat
            and self.min_lng <= lng <= self.max_lng
        )


# Five regencies/cities of the Special Region of Yogyakarta (DIY)
YOGYAKARTA_REGIONS: Dict[str, RegionBoundingBox] = {
    "Kota Yogyakarta": RegionBoundingBox(
        name="Kota Yogyakarta",
        min_lat=-7.8230, max_lat=-7.7520,
        min_lng=110.3400, max_lng=110.4100,
        center_lat=-7.7956, center_lng=110.3695,
    ),
    "Kab Sleman": RegionBoundingBox(
        name="Kab Sleman",
        min_lat=-7.7520, max_lat=-7.5500,
        min_lng=110.2500, max_lng=110.5500,
        center_lat=-7.6600, center_lng=110.3600,
    ),
    "Kab Bantul": RegionBoundingBox(
        name="Kab Bantul",
        min_lat=-8.0100, max_lat=-7.8230,
        min_lng=110.2500, max_lng=110.5000,
        center_lat=-7.8900, center_lng=110.3300,
    ),
    "Kab Gunungkidul": RegionBoundingBox(
        name="Kab Gunungkidul",
        min_lat=-8.2000, max_lat=-7.8000,
        min_lng=110.4500, max_lng=110.9000,
        center_lat=-7.9800, center_lng=110.6100,
    ),
    "Kab Kulon Progo": RegionBoundingBox(
        name="Kab Kulon Progo",
        min_lat=-7.9800, max_lat=-7.6500,
        min_lng=110.0500, max_lng=110.2600,
        center_lat=-7.8200, center_lng=110.1500,
    ),
}

# Combined centre & radius used for the OpenChargeMap query
YOGYAKARTA_CENTER_LAT: float = -7.7956
YOGYAKARTA_CENTER_LNG: float = 110.3695
YOGYAKARTA_SEARCH_RADIUS_KM: float = 60.0


# ---------------------------------------------------------------------------
# Export paths
# ---------------------------------------------------------------------------
DEFAULT_OUTPUT_DIR: Path = _PROJECT_ROOT / "dashboard" / "data"
EXPORT_GEOJSON_FILENAME: str = "spklu_yogyakarta.geojson"
EXPORT_CSV_FILENAME: str = "spklu_yogyakarta.csv"
EXPORT_JSON_FILENAME: str = "spklu_yogyakarta.json"


# ---------------------------------------------------------------------------
# OpenChargeMap field mappings
# ---------------------------------------------------------------------------
OCM_CONNECTION_TYPE_MAP: Dict[int, str] = {
    2: "CHAdeMO",
    25: "Type 2 (Socket Only)",
    33: "CCS2 (CCS/SAE)",
    1036: "Type 2 (Tethered Connector)",
    27: "Tesla Supercharger",
    0: "Unknown",
}

OCM_LEVEL_MAP: Dict[int, str] = {
    1: "standard",   # Level 1 – Low (< 2 kW)
    2: "medium",     # Level 2 – Medium (2–40 kW)
    3: "fast",       # Level 3 – High / DC Fast (> 40 kW)
}


@dataclass
class CollectorConfig:
    """Runtime configuration container – handy for dependency injection."""

    petaspklu_url: str = PETASPKLU_API_URL
    ocm_url: str = OCM_API_URL
    ocm_api_key: Optional[str] = field(default_factory=lambda: OCM_API_KEY)
    database_url: Optional[str] = field(default_factory=lambda: DATABASE_URL)
    timeout: int = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_base: float = DEFAULT_BACKOFF_BASE
    request_delay: float = DEFAULT_REQUEST_DELAY
    user_agent: str = DEFAULT_USER_AGENT
    output_dir: Path = DEFAULT_OUTPUT_DIR
