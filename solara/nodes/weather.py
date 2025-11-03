from meteostat import Monthly, Point
from datetime import datetime
import pandas as pd

def get_monthly_weather_norms(lat: float, lon: float, years_back: int = 10) -> pd.DataFrame:
    end = datetime.now()
    start = datetime(end.year - years_back, 1, 1)
    p = Point(lat, lon)
    df = Monthly(p, start, end).fetch()
    return df.rename(columns={"tavg": "mean_temp_c", "prcp": "precip_mm", "wspd": "wind_kph"})
