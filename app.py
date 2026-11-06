import os
import time
from typing import Optional

import requests
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

API_BASE = "https://v3.football.api-sports.io"
API_KEY = os.getenv("API_FOOTBALL_KEY", "")
BRIDGE_KEY = os.getenv("BRIDGE_API_KEY", "")

app = FastAPI(title="Football Live Data Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

_cache = {}

def check_access(x_bridge_key: Optional[str]):
    if BRIDGE_KEY and x_bridge_key != BRIDGE_KEY:
        raise HTTPException(status_code=401, detail="Invalid bridge key")

def api_get(endpoint: str, params: dict):
    if not API_KEY:
        raise HTTPException(status_code=503, detail="API_FOOTBALL_KEY is not configured")
    try:
        response = requests.get(
            f"{API_BASE}/{endpoint}",
            headers={"x-apisports-key": API_KEY},
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errors"):
            raise HTTPException(status_code=502, detail=data["errors"])
        return data
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"API-Football request failed: {exc}")

def cached_get(key: str, endpoint: str, params: dict, ttl: int = 30):
    now = time.time()
    if key in _cache and now - _cache[key]["time"] < ttl:
        return _cache[key]["data"]
    data = api_get(endpoint, params)
    _cache[key] = {"time": now, "data": data}
    return data

@app.get("/")
def root():
    return {"service": "Football Live Data Bridge", "status": "online"}

@app.get("/health")
def health():
    return {"status": "ok", "api_key_configured": bool(API_KEY), "bridge_key_required": bool(BRIDGE_KEY)}

@app.get("/live")
def live(x_bridge_key: Optional[str] = Header(default=None)):
    check_access(x_bridge_key)
    return cached_get("live_all", "fixtures", {"live": "all"}, ttl=20)

@app.get("/fixtures")
def fixtures(date: str, x_bridge_key: Optional[str] = Header(default=None)):
    check_access(x_bridge_key)
    return cached_get(f"fixtures_{date}", "fixtures", {"date": date}, ttl=120)

@app.get("/match/{fixture_id}")
def match(fixture_id: int, x_bridge_key: Optional[str] = Header(default=None)):
    check_access(x_bridge_key)
    return {
        "fixture": api_get("fixtures", {"id": fixture_id}),
        "statistics": api_get("fixtures/statistics", {"fixture": fixture_id}),
        "events": api_get("fixtures/events", {"fixture": fixture_id}),
    }

@app.get("/odds/live")
def live_odds(fixture: Optional[int] = None, x_bridge_key: Optional[str] = Header(default=None)):
    check_access(x_bridge_key)
    params = {"live": "all"}
    if fixture is not None:
        params = {"fixture": fixture}
    return cached_get(f"odds_{params}", "odds", params, ttl=60)
