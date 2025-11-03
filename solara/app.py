from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from .nodes.places import fetch_pois_google
from .nodes.weather import get_monthly_weather_norms
from .nodes.scoring import compute_scores
from .nodes.writer import normalize_with_mixtral, write_summary
from .config import GOOGLE_MAPS_API_KEY
import pandas as pd

class State(TypedDict):
    location_text: str
    month: int
    lat: float
    lon: float
    weather_df: pd.DataFrame
    pois: list[dict]
    scored: list
    summary: str

def n_pois(state: State):
    (lat, lon), pois = fetch_pois_google(state["location_text"], GOOGLE_MAPS_API_KEY)
    norm = normalize_with_mixtral([p.model_dump() if hasattr(p, "model_dump") else p for p in pois])
    return {"lat": lat, "lon": lon, "pois": norm}

def n_weather(state: State):
    df = get_monthly_weather_norms(state["lat"], state["lon"])
    return {"weather_df": df}

def n_score(state: State):
    from .models import POI
    scored = compute_scores([POI(**p) for p in state["pois"]], state["weather_df"], state["month"])
    return {"scored": scored}

def n_write(state: State):
    summary = write_summary(state["location_text"], state["month"], [s.model_dump() for s in state["scored"]])
    return {"summary": summary}

graph = StateGraph(State)
graph.add_node("pois", n_pois)
graph.add_node("weather", n_weather)
graph.add_node("score", n_score)
graph.add_node("write", n_write)
graph.add_edge(START, "pois")
graph.add_edge("pois", "weather")
graph.add_edge("weather", "score")
graph.add_edge("score", "write")
graph.add_edge("write", END)

app = graph.compile()
