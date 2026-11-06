
import os
import time
import copy
from typing import Optional

import requests
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

API_BASE = "https://v3.football.api-sports.io"
API_KEY = os.getenv("API_FOOTBALL_KEY", "")
BRIDGE_KEY = os.getenv("BRIDGE_API_KEY", "")

app = FastAPI(title="Football Live Data Bridge", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

_cache = {}

# API-Football league IDs
ALLOWED_LEAGUES = {
    39: "Premier League",
    140: "La Liga",
    78: "Bundesliga",
    135: "Serie A",
    61: "Ligue 1",
    2: "UEFA Champions League",
    3: "UEFA Europa League",
    848: "UEFA Conference League",
    94: "Primeira Liga",
    88: "Eredivisie",
    144: "Belgian Pro League",
}

def check_access(x_bridge_key: Optional[str]):
    if BRIDGE_KEY and x_bridge_key != BRIDGE_KEY:
        raise HTTPException(status_code=401, detail="Invalid bridge key")

def api_get(endpoint: str, params: dict):
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="API_FOOTBALL_KEY is not configured"
        )

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
        raise HTTPException(
            status_code=502,
            detail=f"API-Football request failed: {exc}"
        )

def cached_get(key: str, endpoint: str, params: dict, ttl: int = 30):
    now = time.time()

    if key in _cache and now - _cache[key]["time"] < ttl:
        return copy.deepcopy(_cache[key]["data"])

    data = api_get(endpoint, params)
    _cache[key] = {"time": now, "data": data}

    return copy.deepcopy(data)

def filter_fixtures(data: dict) -> dict:
    matches = data.get("response", [])

    if not isinstance(matches, list):
        return data

    accepted = []
    excluded = []

    for match in matches:
        league = match.get("league", {})
        league_id = league.get("id")

        home = match.get("teams", {}).get("home", {}).get("name", "")
        away = match.get("teams", {}).get("away", {}).get("name", "")

        team_names = f"{home} {away}".upper()

        youth_or_reserve = any(
            word in team_names
            for word in [
                " U19", " U20", " U21", " U23",
                "UNDER 19", "UNDER 20", "UNDER 21",
                "UNDER 23", "RESERVE", "ACADEMY"
            ]
        )

        if league_id in ALLOWED_LEAGUES and not youth_or_reserve:
            accepted.append(match)
        else:
            excluded.append({
                "league": league.get("name"),
                "league_id": league_id,
                "home": home,
                "away": away,
            })

    data["response"] = accepted
    data["results"] = len(accepted)
    data["filtering"] = {
        "allowed_competitions": ALLOWED_LEAGUES,
        "returned_matches": len(accepted),
        "excluded_matches": len(excluded),
        "excluded": excluded,
    }

    return data

@app.get("/")
def root():
    return {
        "service": "Football Live Data Bridge",
        "status": "online",
        "version": "1.2.0",
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "api_key_configured": bool(API_KEY),
        "bridge_key_required": bool(BRIDGE_KEY),
    }

@app.get("/competitions")
def competitions(x_bridge_key: Optional[str] = Header(default=None)):
    check_access(x_bridge_key)
    return {
        "count": len(ALLOWED_LEAGUES),
        "competitions": [
            {"id": league_id, "name": name}
            for league_id, name in ALLOWED_LEAGUES.items()
        ],
    }

@app.get("/live")
def live(x_bridge_key: Optional[str] = Header(default=None)):
    check_access(x_bridge_key)

    data = cached_get(
        "live_all",
        "fixtures",
        {"live": "all"},
        ttl=20,
    )

    return filter_fixtures(data)

@app.get("/fixtures")
def fixtures(
    date: str,
    x_bridge_key: Optional[str] = Header(default=None),
):
    check_access(x_bridge_key)

    data = cached_get(
        f"fixtures_{date}",
        "fixtures",
        {"date": date},
        ttl=120,
    )

    return filter_fixtures(data)

@app.get("/match/{fixture_id}")
def match(
    fixture_id: int,
    x_bridge_key: Optional[str] = Header(default=None),
):
    check_access(x_bridge_key)

    return {
        "fixture": api_get("fixtures", {"id": fixture_id}),
        "statistics": api_get(
            "fixtures/statistics",
            {"fixture": fixture_id},
        ),
        "events": api_get(
            "fixtures/events",
            {"fixture": fixture_id},
        ),
    }

@app.get("/odds/live")
def live_odds(
    fixture: Optional[int] = None,
    league: Optional[int] = None,
    date: Optional[str] = None,
    x_bridge_key: Optional[str] = Header(default=None),
):
    check_access(x_bridge_key)

    params = {}

    if fixture is not None:
        params["fixture"] = fixture

    if league is not None:
        params["league"] = league

    if date is not None:
        params["date"] = date

    if not params:
        raise HTTPException(
            status_code=400,
            detail="Provide a fixture ID, league ID, or date."
        )

    cache_key = f"odds_{sorted(params.items())}"

    return cached_get(
        cache_key,
        "odds",
        params,
        ttl=60,
    )
