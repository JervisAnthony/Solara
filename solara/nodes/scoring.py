import math
import pandas as pd
from ..models import POI, ScoredPOI

def weather_fit_for_month(df: pd.DataFrame, month: int) -> float:
    row = df[df.index.month == month]
    if row.empty: return 0.5
    r = row.iloc[0]
    temp = r.get("mean_temp_c", 23.0)
    precip = r.get("precip_mm", 0.0)
    wind = r.get("wind_kph", 10.0)

    temp_score = max(0, 1 - abs((temp - 23) / 12))
    precip_penalty = max(0, 1 - min(precip / 200.0, 1))
    wind_penalty = max(0, 1 - min(wind / 40.0, 1))

    return float(max(0, min(1, 0.6 * temp_score + 0.3 * precip_penalty + 0.1 * wind_penalty)))

def norm_popularity(rating, reviews) -> float:
    if rating is None and reviews is None: return 0.4
    r = (rating or 4.0) / 5.0
    v = math.log10((reviews or 50) + 10) / 4.0
    return float(max(0, min(1, 0.6 * r + 0.4 * v)))

def compute_scores(pois: list[POI], df: pd.DataFrame, month: int) -> list[ScoredPOI]:
    results = []
    for p in pois:
        wf = weather_fit_for_month(df, month)
        pop = norm_popularity(p.rating, p.review_count)
        seas = 0.5
        bonus = 0.1 if (p.category or "").lower() in {"museum", "art_gallery", "aquarium"} else 0.0
        score = 0.35 * wf + 0.35 * pop + 0.20 * seas + 0.10 * bonus
        results.append(
            ScoredPOI(**p.model_dump(), weather_fit=wf, popularity=pop,
                      seasonality=seas, bonus=bonus, score=round(score, 4),
                      rationale="weighted weather, popularity, and seasonal fit")
        )
    return sorted(results, key=lambda x: x.score, reverse=True)
