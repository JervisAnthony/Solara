from typing import Tuple, List
import googlemaps
from ..models import POI

def fetch_pois_google(place_text: str, api_key: str, limit: int = 30) -> Tuple[Tuple[float,float], List[POI]]:
    gmaps = googlemaps.Client(api_key=api_key)
    geoc = gmaps.geocode(place_text)[0]
    loc = geoc["geometry"]["location"]
    lat, lon = loc["lat"], loc["lng"]

    results = gmaps.places_nearby(
        location=(lat, lon), radius=20000, type="tourist_attraction"
    )["results"]

    pois = [
        POI(
            name=r.get("name"),
            category="tourist_attraction",
            rating=r.get("rating"),
            review_count=r.get("user_ratings_total"),
            address=r.get("vicinity"),
            lat=r["geometry"]["location"]["lat"],
            lon=r["geometry"]["location"]["lng"],
            source="google"
        )
        for r in results[:limit]
    ]
    return (lat, lon), pois
