from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from app.db import Database, DatabaseError
from app.api import fetch_city_forecast, suggest_cities, WeatherAPIError

db = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Plasma 6 Weather Backend Bridge", lifespan=lifespan)


@app.get("/api/suggest")
def get_city_suggestions(q: str = Query(..., min_length=2)):
    return {"suggestions": suggest_cities(q)}


@app.post("/api/sync")
def sync_city_weather(
    city: str = Query(..., min_length=1),
    lat: float | None = Query(None),
    lon: float | None = Query(None),
    state: str | None = Query(None)
):
    try:
        parsed_data = fetch_city_forecast(city, lat=lat, lon=lon, state=state)
        db.save_weather_data(parsed_data)
        city_id = parsed_data["city"]["city_id"]
        forecasts = db.get_forecasts_by_city(city_id)
        return {
            "status": "ok",
            "city": parsed_data["city"],
            "forecasts": forecasts
        }
    except WeatherAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cities")
def get_saved_cities():
    try:
        return {"cities": db.get_all_cities()}
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/forecasts/{city_id}")
def get_city_forecasts(city_id: int):
    try:
        return {"forecasts": db.get_forecasts_by_city(city_id)}
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
