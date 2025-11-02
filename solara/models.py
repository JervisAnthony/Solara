from pydantic import BaseModel
from typing import List, Optional

class WeatherSummary(BaseModel):
    month: int
    mean_temp_c: float
    precip_mm: float
    wind_kph: Optional[float] = None

class POI(BaseModel):
    name: str
    category: str = "tourist_attraction"
    rating: Optional[float] = None
    review_count: Optional[int] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    source: Optional[str] = None

class ScoredPOI(POI):
    weather_fit: float
    popularity: float
    seasonality: float
    bonus: float
    score: float
    rationale: str

class AppAnswer(BaseModel):
    location: str
    target_month: int
    top_spots: List[ScoredPOI]
    summary_md: str
