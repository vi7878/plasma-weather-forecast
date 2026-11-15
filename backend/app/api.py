import requests
from app.config import Config


class WeatherAPIError(Exception):
    pass


def suggest_cities(query: str) -> list:
    Config.validate()
    query = query.strip()
    if len(query) < 2:
        return []

    params = {
        "q": query,
        "limit": 5,
        "appid": Config.API_KEY
    }

    try:
        response = requests.get(Config.GEO_URL, params=params, timeout=5)
        if response.status_code != 200:
            return []
        items = response.json()
    except (requests.exceptions.RequestException, ValueError):
        return []

    results = []
    for item in items:
        local_names = item.get("local_names", {})
        name = local_names.get("uk") or item.get("name", "")
        state = item.get("state", "")
        country = item.get("country", "")
        lat = item.get("lat")
        lon = item.get("lon")
        label = f"{name}, {state}, {country}" if state else f"{name}, {country}"
        results.append({
            "name": name,
            "state": state,
            "country": country,
            "lat": lat,
            "lon": lon,
            "label": label
        })
    return results


def fetch_city_forecast(
    city_name: str,
    lat: float | None = None,
    lon: float | None = None,
    state: str | None = None
) -> dict:
    Config.validate()

    city_name = city_name.strip()
    if not city_name and (lat is None or lon is None):
        raise WeatherAPIError("Назва міста не може бути порожньою.")

    if (lat is None or lon is None) and "," in city_name:
        parts = [p.strip() for p in city_name.split(",") if p.strip()]
        base_name = parts[0]
        target_state = parts[1].lower() if len(parts) > 1 else ""
        candidates = suggest_cities(base_name)
        for c in candidates:
            if target_state and target_state in c["state"].lower():
                lat, lon, state = c["lat"], c["lon"], c["state"]
                break
        if (lat is None or lon is None) and candidates:
            lat, lon, state = candidates[0]["lat"], candidates[0]["lon"], candidates[0]["state"]

    params = {
        "appid": Config.API_KEY,
        "units": "metric",
        "lang": "uk"
    }
    if lat is not None and lon is not None:
        params["lat"] = lat
        params["lon"] = lon
    else:
        params["q"] = city_name

    try:
        response = requests.get(Config.API_URL, params=params, timeout=10)
    except requests.exceptions.ConnectionError:
        raise WeatherAPIError("Помилка мережі: відсутнє підключення до Інтернету або сервер недоступний.")
    except requests.exceptions.Timeout:
        raise WeatherAPIError("Перевищено час очікування відповіді від сервера (Timeout).")
    except requests.exceptions.RequestException as e:
        raise WeatherAPIError(f"Помилка під час виконання HTTP-запиту: {e}")

    if response.status_code != 200:
        if response.status_code == 401:
            raise WeatherAPIError("Помилка 401: Невалідний або ще не активований API-ключ.")
        elif response.status_code == 404:
            raise WeatherAPIError(f"Помилка 404: Місто '{city_name}' не знайдено.")
        elif response.status_code == 429:
            raise WeatherAPIError("Помилка 429: Перевищено ліміт запитів до API.")
        else:
            raise WeatherAPIError(f"Помилка API: отримано статус-код {response.status_code}.")

    if not response.text or not response.text.strip():
        raise WeatherAPIError("Отримано порожню відповідь від сервера.")

    try:
        data = response.json()
    except ValueError:
        raise WeatherAPIError("Помилка парсингу: відповідь сервера не є коректним JSON.")

    if not data or "city" not in data or "list" not in data or not data["list"]:
        raise WeatherAPIError("Відповідь API не містить очікуваних даних про місто або прогноз.")

    return parse_forecast_data(data, state=state)


def parse_forecast_data(raw_data: dict, state: str | None = None) -> dict:
    city_info = raw_data["city"]
    city_name = city_info["name"]
    if state and state.lower() not in city_name.lower():
        city_name = f"{city_name} ({state})"

    parsed_city = {
        "city_id": city_info["id"],
        "name": city_name,
        "country": city_info.get("country", "N/A"),
        "population": city_info.get("population", 0),
        "timezone": city_info.get("timezone", 0)
    }

    forecasts = []
    for item in raw_data["list"]:
        main = item.get("main", {})
        weather_list = item.get("weather", [{}])
        wind = item.get("wind", {})

        forecasts.append({
            "dt_txt": item["dt_txt"],
            "temp": main.get("temp", 0.0),
            "feels_like": main.get("feels_like", 0.0),
            "humidity": main.get("humidity", 0),
            "description": weather_list[0].get("description", "Невідомо"),
            "wind_speed": wind.get("speed", 0.0)
        })

    return {
        "city": parsed_city,
        "forecasts": forecasts
    }
